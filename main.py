import asyncio
import logging
import sys
import os
from aiohttp import web

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')

from aiogram import Bot
import config
import database
from bot import get_bot_and_dp, register_handlers, setup_bot_commands
from scheduler import setup_scheduler
from scraper import create_telethon_client, start_scraper

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - [%(levelname)s] - %(name)s - %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("bot.log", encoding="utf-8")
    ]
)
logger = logging.getLogger("MAIN")

async def main():
    logger.info("Logistika YM tizimi ishga tushirilmoqda...")

    # 1. Konfiguratsiyani tekshirish
    if not config.BOT_TOKEN:
        logger.error("BOT_TOKEN ko'rsatilmagan! Iltimos .env faylini to'ldiring.")
        return

    # 2. Ma'lumotlar bazasini ishga tushirish
    await database.init_db()
    logger.info("Ma'lumotlar bazasi muvaffaqiyatli initsializatsiya qilindi.")

    # 3. Aiogram Bot va Dispatcherni sozlash
    bot, dp = get_bot_and_dp()
    register_handlers(dp)
    await setup_bot_commands(bot)
    logger.info("Aiogram 3.x bot handlerlari va doimiy menyusi sozlandi.")

    # 4. APScheduler ni ishga tushirish (obunani kuzatish va avto-kick)
    scheduler = setup_scheduler(bot)
    scheduler.start()
    logger.info("APScheduler obunalarni nazorat qilish uchun ishga tushirildi.")

    # 5. Telethon Scraper ni sozlash
    telethon_client = None
    if config.API_ID and config.API_HASH:
        try:
            telethon_client = create_telethon_client()
            await telethon_client.start()
            await start_scraper(telethon_client, bot)
            logger.info("Telethon Scraper ochiq guruhlarni kuzatish uchun muvaffaqiyatli ulandi.")
        except Exception as e:
            logger.error(f"Telethon ulanishida xatolik yuz berdi: {e}")
            logger.warning("Bot Telethonsiz faqat obuna va boshqaruv rejimida ishlashni davom ettiradi.")
    else:
        logger.warning("API_ID yoki API_HASH ko'rsatilmagan. Scraper faollashtirilmadi.")

    # 6. Aiogram bot polling va Telethon ni bir vaqtda ishga tushirish
    try:
        logger.info("Tizim to'liq ishchi holatda! Polling boshlanmoqda...")
        # Eski kutilmagan webhook/update larni tozalash (tarmoq xatosi bo'lsa bot to'xtab qolmasligi uchun)
        try:
            await bot.delete_webhook(drop_pending_updates=True)
        except Exception as e:
            logger.warning(f"Webhook tozalashda xatolik (e'tiborsiz qoldirildi): {e}")
        
        # Telethon Scraper doimiy avto-ulanish bilan fonda ishlaydi
        async def telethon_runner():
            if not telethon_client:
                return
            while True:
                try:
                    if not telethon_client.is_connected():
                        await telethon_client.connect()
                    await telethon_client.run_until_disconnected()
                except asyncio.CancelledError:
                    break
                except Exception as e:
                    logger.warning(f"Telethon uzildi ({e}), 5 soniyada qayta ulanadi...")
                    await asyncio.sleep(5)

        asyncio.create_task(telethon_runner())

        # Render.com yoki boshqa bulut platformalari uchun Health Check veb-serveri
        web_runner = None
        if os.getenv("PORT"):
            try:
                async def handle_ping(request):
                    return web.Response(text="OK - Logistika Bot is running", status=200)

                app = web.Application()
                app.router.add_get("/", handle_ping)
                app.router.add_get("/health", handle_ping)
                web_runner = web.AppRunner(app)
                await web_runner.setup()
                port = int(os.getenv("PORT", "10000"))
                site = web.TCPSite(web_runner, "0.0.0.0", port)
                await site.start()
                logger.info(f"Health-check veb-serveri {port}-portda ishga tushirildi (Render.com uchun).")
            except Exception as e:
                logger.warning(f"Veb-serverni ishga tushirishda xatolik: {e}")

        # Aiogram bot cheksiz polling sikli
        while True:
            try:
                await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())
                break
            except (KeyboardInterrupt, SystemExit):
                break
            except Exception as e:
                logger.error(f"Kutilmagan tarmoq xatoligi: {e}. 5 soniyadan so'ng qayta ulanadi...")
                await asyncio.sleep(5)

    except (KeyboardInterrupt, SystemExit):
        logger.info("Tizim to'xtatilmoqda...")
    finally:
        if web_runner:
            try:
                await web_runner.cleanup()
            except Exception:
                pass
        if scheduler.running:
            scheduler.shutdown()
        if telethon_client and telethon_client.is_connected():
            await telethon_client.disconnect()
        await database.close_db()
        await bot.session.close()
        logger.info("Tizim xavfsiz to'xtatildi.")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        pass
