import re
import unicodedata
from typing import Tuple, Optional, Dict, Any, List

# O'zbekiston viloyatlari, yirik shaharlari, sanoat tumanlari, dehqon bozorlari va bojxona postlari
REGIONS_MAP: Dict[str, str] = {
    # --- TOSHKENT VA TOSHKENT VILOYATI ---
    "toshkent": "Toshkent", "тошкент": "Toshkent", "ташкент": "Toshkent", "toshket": "Toshkent", "toshken": "Toshkent", "тошкет": "Toshkent", "тошкен": "Toshkent",
    "angren": "Angren", "ангрен": "Angren", 
    "olmaliq": "Olmaliq", "алмалык": "Olmaliq",
    "chirchiq": "Chirchiq", "чирчик": "Chirchiq", "чирчиқ": "Chirchiq", 
    "bekobod": "Bekobod", "бекабад": "Bekobod",
    "yangiyo'l": "Yangiyo'l", "янгийул": "Yangiyo'l", "янгиюль": "Yangiyo'l",
    "chinoz": "Chinoz", "чиноз": "Chinoz", "чиноздан": "Chinoz",
    "zangiota": "Zangiota", "зангиота": "Zangiota", "зангиата": "Zangiota",
    "parkent": "Parkent", "паркент": "Parkent", "zarkent": "Parkent", "заркент": "Parkent",
    "bo'ka": "Bo'ka", "бўка": "Bo'ka", "бука": "Bo'ka", "boka": "Bo'ka",
    "piskent": "Piskent", "пискент": "Piskent",
    "oqqo'rg'on": "Oqqo'rg'on", "оққўрғон": "Oqqo'rg'on", "аккурган": "Oqqo'rg'on", "oqqorgon": "Oqqo'rg'on", "okqorgon": "Oqqo'rg'on", "okkorgon": "Oqqo'rg'on",
    "qibray": "Qibray", "қибрай": "Qibray", "кибрай": "Qibray",
    "bo'stonliq": "Bo'stonliq", "бўстонлиқ": "Bo'stonliq", "бостанлык": "Bo'stonliq", "bostonliq": "Bo'stonliq", "bostonlik": "Bo'stonliq",
    "g'azalkent": "G'azalkent", "ғазалкент": "G'azalkent", "газалкент": "G'azalkent",
    "keles": "Keles", "келес": "Keles", "nazarbek": "Nazarbek", "назарбек": "Nazarbek",
    "yallama": "Yallama (Bojxona)", "яллама": "Yallama (Bojxona)",
    "g'ishtko'prik": "G'ishtko'prik (Chernyayevka)", "ғишткўприк": "G'ishtko'prik (Chernyayevka)", "черняевка": "G'ishtko'prik (Chernyayevka)",
    "ohangaron": "Ohangaron", "оҳангарон": "Ohangaron", "охангарон": "Ohangaron", "ахангаран": "Ohangaron", "begavot": "Bekobod", "бегавот": "Bekobod",
    "qo'yliq": "Toshkent (Qo'yliq)", "қўйлиқ": "Toshkent (Qo'yliq)", "quyliq": "Toshkent (Qo'yliq)", "куйлюк": "Toshkent (Qo'yliq)", "kuylyuk": "Toshkent (Qo'yliq)", "койлик": "Toshkent (Qo'yliq)",
    "sergeli": "Toshkent (Sergeli)", "сергели": "Toshkent (Sergeli)", "sergili": "Toshkent (Sergeli)", "сергили": "Toshkent (Sergeli)",
    "izza": "Toshkent (Izza)", "изза": "Toshkent (Izza)",
    "abu saxiy": "Toshkent (Abu Saxiy)", "abusaxiy": "Toshkent (Abu Saxiy)", "абу сахий": "Toshkent (Abu Saxiy)", "абусахий": "Toshkent (Abu Saxiy)",
    "o'rikzor": "Toshkent (O'rikzor)", "ўрикзор": "Toshkent (O'rikzor)", "urikzor": "Toshkent (O'rikzor)", "урикзор": "Toshkent (O'rikzor)",
    "bekbaraka": "Toshkent (Bekbaraka)", "бекбарака": "Toshkent (Bekbaraka)", "бек барака": "Toshkent (Bekbaraka)",
    "chorsu": "Toshkent (Chorsu)", "чорсу": "Toshkent (Chorsu)",
    "chilonzor": "Toshkent (Chilonzor)", "чилонзор": "Toshkent (Chilonzor)",
    "yunusobod": "Toshkent (Yunusobod)", "юнусобод": "Toshkent (Yunusobod)", "юнусабад": "Toshkent (Yunusobod)",
    "yashnobod": "Toshkent (Yashnobod)", "яшнобод": "Toshkent (Yashnobod)",
    "algoritm": "Toshkent (Algoritm)", "алгоритм": "Toshkent (Algoritm)",
    "motabar": "Toshkent (Mo'tabar)", "mo'tabar": "Toshkent (Mo'tabar)", "мотабар": "Toshkent (Mo'tabar)", "мўътабар": "Toshkent (Mo'tabar)",
    "erkin": "Toshkent (Erkin)", "эркин": "Toshkent (Erkin)",
    "toytepa": "To'ytepa", "тўйтепа": "To'ytepa", "тойтепа": "To'ytepa", "nurafshon": "To'ytepa", "нурафшон": "To'ytepa",

    # --- SAMARQAND VILOYATI ---
    "samarqand": "Samarqand", "самарқанд": "Samarqand", "самарканд": "Samarqand", "samatqan": "Samarqand", "samarqant": "Samarqand", "самарқант": "Samarqand", "samarkan": "Samarqand", "самаркан": "Samarqand", "samrqand": "Samarqand", "самрқанд": "Samarqand", "samrqan": "Samarqand",
    "urgut": "Urgut", "ургут": "Urgut", 
    "kattaqo'rg'on": "Kattaqo'rg'on", "каттақўрғон": "Kattaqo'rg'on", "каттакурган": "Kattaqo'rg'on", "kattaqorgon": "Kattaqo'rg'on", "kattakorgan": "Kattaqo'rg'on", "kattakurgan": "Kattaqo'rg'on",
    "payariq": "Payariq", "паяриқ": "Payariq", "пайарык": "Payariq", "payarik": "Payariq",
    "chelak": "Chelak", "челак": "Chelak",
    "jomboy": "Jomboy", "жомбой": "Jomboy", "джамбай": "Jomboy",
    "bulung'ur": "Bulung'ur", "булунғур": "Bulung'ur", "булунгур": "Bulung'ur", "bulungur": "Bulung'ur",
    "ishtixon": "Ishtixon", "иштихон": "Ishtixon",
    "oqdaryo": "Oqdaryo", "оқдарё": "Oqdaryo", "акдарья": "Oqdaryo", "loyish": "Loyish", "лойиш": "Loyish", "okdaryo": "Oqdaryo",
    "pastdarg'om": "Pastdarg'om", "пастдарғом": "Pastdarg'om", "juma": "Juma", "жума": "Juma", "pastdargom": "Pastdarg'om",
    "paxtachi": "Paxtachi", "пахтачи": "Paxtachi", "ziyovuddin": "Ziyovuddin", "зиёвуддин": "Ziyovuddin",
    "oqtosh": "Oqtosh", "оқтош": "Oqtosh", "акташ": "Oqtosh",
    "toyloq": "Toyloq", "тойлоқ": "Toyloq", "тайлак": "Toyloq",
    "mirbozor": "Mirbozor", "мирбозор": "Mirbozor",
    "qo'shrabot": "Qo'shrabot", "қўшработ": "Qo'shrabot", "qoshrabot": "Qo'shrabot", "koshrobot": "Qo'shrabot",

    # --- FARG'ONA VILOYATI ---
    "farg'ona": "Farg'ona", "fargʻona": "Farg'ona", "fargona": "Farg'ona", "фарғона": "Farg'ona", "фаргона": "Farg'ona",
    "qo'qon": "Qo'qon", "qoqon": "Qo'qon", "қўқон": "Qo'qon", "кукон": "Qo'qon", "коканд": "Qo'qon", "qokon": "Qo'qon", "quqon": "Qo'qon", "қуқон": "Qo'qon",
    "marg'ilon": "Marg'ilon", "марғилон": "Marg'ilon", "маргилан": "Marg'ilon", 
    "quva": "Quva", "қува": "Quva", "кува": "Quva",
    "quvasoy": "Quvasoy", "қувасой": "Quvasoy", "кувасай": "Quvasoy",
    "oltiariq": "Oltiariq", "олтиариқ": "Oltiariq", "алтыарык": "Oltiariq", "oltiarik": "Oltiariq", "олтиарик": "Oltiariq", "алтыарик": "Oltiariq",
    "rishton": "Rishton", "риштон": "Rishton",
    "uchko'prik": "Uchko'prik", "учкўприк": "Uchko'prik", "учкоприк": "Uchko'prik", "uchkoprik": "Uchko'prik", "uchkuprik": "Uchko'prik",
    "beshariq": "Beshariq", "бешариқ": "Beshariq", "бешарык": "Beshariq", "besharik": "Beshariq",
    "yaypan": "Yaypan", "яйпан": "Yaypan",
    "bog'dod": "Bog'dod", "боғдод": "Bog'dod", "багдад": "Bog'dod", "bogdod": "Bog'dod",
    "buvayda": "Buvayda", "бувайда": "Buvayda",
    "yozyovon": "Yozyovon", "ёзёвон": "Yozyovon", "язяван": "Yozyovon",
    "toshloq": "Toshloq", "тошлоқ": "Toshloq", "ташлак": "Toshloq",
    "vodil": "Vodil", "водил": "Vodil", "shohimardon": "Shohimardon", "шоҳимардон": "Shohimardon",

    # --- ANDIJON VILOYATI ---
    "andijon": "Andijon", "андижон": "Andijon", "андижан": "Andijon",
    "asaka": "Asaka", "асака": "Asaka", 
    "shahrixon": "Shahrixon", "шахрихон": "Shahrixon", "шаҳрихон": "Shahrixon",
    "xo'jaobod": "Xo'jaobod", "хўжаобод": "Xo'jaobod", "ходжаабад": "Xo'jaobod", "xojaobod": "Xo'jaobod", "xujaobod": "Xo'jaobod",
    "qorasuv": "Qorasuv", "қорасув": "Qorasuv", "карасу": "Qorasuv",
    "paxtaobod": "Paxtaobod", "пахтаобод": "Paxtaobod", "пахтаабад": "Paxtaobod",
    "oltinko'l": "Oltinko'l", "олтинкўл": "Oltinko'l", "алтынкуль": "Oltinko'l", "oltinkol": "Oltinko'l",
    "baliqchi": "Baliqchi", "балиқчи": "Baliqchi", "балыкчи": "Baliqchi", "balikch": "Baliqchi", "баликч": "Baliqchi",
    "buloqboshi": "Buloqboshi", "булоқбоши": "Buloqboshi",
    "izboskan": "Izboskan", "избоскан": "Izboskan", "poytug'": "Poytug'", "пойтуғ": "Poytug'", "paytug": "Poytug'", "пайтуг": "Poytug'", "paytig": "Poytug'", "пайтиг": "Poytug'",
    "jalaquduq": "Jalaquduq", "жалақудуқ": "Jalaquduq", "джалакудук": "Jalaquduq",
    "marhamat": "Marhamat", "марҳамат": "Marhamat", "мархамат": "Marhamat",
    "xonobod": "Xonobod", "хонобод": "Xonobod", "ханабад": "Xonobod", "honobod": "Xonobod",

    # --- NAMANGAN VILOYATI ---
    "namangan": "Namangan", "наманган": "Namangan", 
    "chust": "Chust", "чуст": "Chust", "olmos": "Chust", "олмос": "Chust",
    "pop": "Pop", "поп": "Pop",
    "kosonsoy": "Kosonsoy", "косонсой": "Kosonsoy", "касансай": "Kosonsoy",
    "uchqo'rg'on": "Uchqo'rg'on", "учқўрғон": "Uchqo'rg'on", "учкурган": "Uchqo'rg'on", "uchkorgon": "Uchqo'rg'on", "uchqorgon": "Uchqo'rg'on", "uchkurgan": "Uchqo'rg'on",
    "chortoq": "Chortoq", "чортоқ": "Chortoq", "чартак": "Chortoq",
    "to'raqo'rg'on": "To'raqo'rg'on", "тўрақўрғон": "To'raqo'rg'on", "туракурган": "To'raqo'rg'on", "toraqorgon": "To'raqo'rg'on", "torakorgan": "To'raqo'rg'on", "toraqo'rg'on": "To'raqo'rg'on", "turakurgan": "To'raqo'rg'on",
    "yangiqo'rg'on": "Yangiqo'rg'on", "янгиқўрғон": "Yangiqo'rg'on", "yangiqorgon": "Yangiqo'rg'on", "yangikorgan": "Yangiqo'rg'on", "yangikurgan": "Yangiqo'rg'on",
    "uychi": "Uychi", "уйчи": "Uychi",
    "haqqulobod": "Haqqulobod", "ҳаққулобод": "Haqqulobod", "norin": "Norin", "норин": "Norin",
    "mingbuloq": "Mingbuloq", "мингбулоқ": "Mingbuloq", "mingbulok": "Mingbuloq",

    # --- VODIY (Umumiy) ---
    "vodiy": "Vodiy", "водий": "Vodiy",

    # --- BUXORO VILOYATI ---
    "buxoro": "Buxoro", "бухоро": "Buxoro", "бухара": "Buxoro", "buxora": "Buxoro", "бухора": "Buxoro",
    "g'ijduvon": "G'ijduvon", "ғиждувон": "G'ijduvon", "гиждуван": "G'ijduvon", "gijduvaon": "G'ijduvon", "гиждуваон": "G'ijduvon",
    "vobkent": "Vobkent", "вобкент": "Vobkent", "вабкент": "Vobkent",
    "shofirkon": "Shofirkon", "шофиркон": "Shofirkon", "шафиркан": "Shofirkon",
    "kogon": "Kogon", "когон": "Kogon", "каган": "Kogon",
    "qorako'l": "Qorako'l", "қоракўл": "Qorako'l", "каракуль": "Qorako'l", "qorakol": "Qorako'l", "korakol": "Qorako'l",
    "olot": "Olot (Bojxona)", "олот": "Olot (Bojxona)", "алат": "Olot (Bojxona)",
    "jondor": "Jondor", "жондор": "Jondor",
    "romitan": "Romitan", "ромитан": "Romitan",
    "peshku": "Peshku", "пешку": "Peshku",
    "qorovulbozor": "Qorovulbozor", "қоровулбозор": "Qorovulbozor", "korovulbozor": "Qorovulbozor",

    # --- QASHQADARYO VILOYATI ---
    "qashqadaryo": "Qashqadaryo", "қашқадарё": "Qashqadaryo", "кашкадарё": "Qashqadaryo", "qashqadryo": "Qashqadaryo", "кашкадарйо": "Qashqadaryo", "qashqadaryoga": "Qashqadaryo",
    "qarshi": "Qarshi", "қарши": "Qarshi", "карши": "Qarshi", 
    "shahrisabz": "Shahrisabz", "шахрисабз": "Shahrisabz", "шаҳрисабз": "Shahrisabz",
    "kitob": "Kitob", "китоб": "Kitob", "varganza": "Kitob", "варганза": "Kitob",
    "yakkabog'": "Yakkabog'", "яккабоғ": "Yakkabog'", "яккабаг": "Yakkabog'", "yakkabag": "Yakkabog'",
    "koson": "Koson", "косон": "Koson", "касан": "Koson",
    "muborak": "Muborak", "муборак": "Muborak", "мубарек": "Muborak",
    "dehqonobod": "Dehqonobod", "деҳқонобод": "Dehqonobod", "дехконобод": "Dehqonobod", "dehkanabad": "Dehqonobod",
    "g'uzor": "G'uzor", "ғўзор": "G'uzor", "гузар": "G'uzor",
    "nishon": "Nishon", "нишон": "Nishon",
    "dexqanabod": "Dehqonobod", "дехканабад": "Dehqonobod", "dehqonobod": "Dehqonobod", "деҳқонобод": "Dehqonobod",
    "kasbi": "Kasbi", "касби": "Kasbi", "mug'lon": "Mug'lon", "муғлон": "Mug'lon",
    "chiroqchi": "Chiroqchi", "чироқчи": "Chiroqchi", "чиракчи": "Chiroqchi",
    "ko'kdala": "Ko'kdala", "кўкдала": "Ko'kdala", "кукдала": "Ko'kdala", "kokdala": "Ko'kdala",
    "mirishkor": "Mirishkor", "миришкор": "Mirishkor",

    # --- SURXONDARYO VILOYATI ---
    "surxondaryo": "Surxondaryo", "сурхондарё": "Surxondaryo", "сурхандарья": "Surxondaryo", "surxon": "Surxondaryo", "сурхон": "Surxondaryo", "сўрхон": "Surxondaryo", "surxandaryo": "Surxondaryo", "сурхандарё": "Surxondaryo", "surxendaryo": "Surxondaryo", "сурхендарйо": "Surxondaryo",
    "termiz": "Termiz", "термиз": "Termiz", "термез": "Termiz", 
    "denov": "Denov", "денов": "Denov", "денау": "Denov",
    "sho'rchi": "Sho'rchi", "шўрчи": "Sho'rchi", "шурчи": "Sho'rchi", "shorchi": "Sho'rchi", "shurchi": "Sho'rchi",
    "qumqo'rg'on": "Qumqo'rg'on", "қумқўрғон": "Qumqo'rg'on", "кумкурган": "Qumqo'rg'on", "qumqorgon": "Qumqo'rg'on", "qumkorgan": "Qumqo'rg'on", "qumkurgan": "Qumqo'rg'on", "qumqurgan": "Qumqo'rg'on",
    "oltinsoy": "Oltinsoy", "олтинсой": "Oltinsoy",
    "sariosiyo": "Sariosiyo", "сариосиё": "Sariosiyo", "сариасия": "Sariosiyo",
    "uzun": "Uzun", "узун": "Uzun",
    "boysun": "Boysun", "бойсун": "Boysun", "байсун": "Boysun",
    "sherobod": "Sherobod", "шеробод": "Sherobod", "ширабад": "Sherobod", "sherob": "Sherobod", "шероб": "Sherobod", "sherabot": "Sherobod", "шеработ": "Sherobod",
    "jarqo'rg'on": "Jarqo'rg'on", "жарқўрғон": "Jarqo'rg'on", "джаркурган": "Jarqo'rg'on", "jarqorgon": "Jarqo'rg'on", "jarkorgan": "Jarqo'rg'on", "jarkurgan": "Jarqo'rg'on",
    "muzrabot": "Muzrabot", "музработ": "Muzrabot",
    "bandixon": "Bandixon", "бандихон": "Bandixon",

    # --- NAVOIY VILOYATI ---
    "navoiy": "Navoiy", "навоий": "Navoiy", "навои": "Navoiy", 
    "karmana": "Karmana", "кармана": "Karmana",
    "qiziltepa": "Qiziltepa", "қизилтепа": "Qiziltepa", "кызылтепа": "Qiziltepa",
    "xatirchi": "Xatirchi", "хатирчи": "Xatirchi",
    "zarafshon": "Zarafshon", "зарафшон": "Zarafshon", "заравшан": "Zarafshon",
    "uchquduq": "Uchquduq", "учқудуқ": "Uchquduq", "учкудук": "Uchquduq", "uchkuduk": "Uchquduq",
    "konimex": "Konimex", "конимех": "Konimex", "канимех": "Konimex",
    "nurota": "Nurota", "нурота": "Nurota", "нурата": "Nurota",
    "gazgon": "Gazgon", "газгон": "Gazgon", "газган": "Gazgon",

    # --- JIZZAX VILOYATI ---
    "jizzax": "Jizzax", "жиззах": "Jizzax", "джизак": "Jizzax", 
    "zomin": "Zomin", "зомин": "Zomin", "заамин": "Zomin",
    "zarbdor": "Zarbdor", "зарбдор": "Zarbdor", "zaribdor": "Zarbdor", "зарибдор": "Zarbdor",
    "do'stlik": "Do'stlik", "дўстлик": "Do'stlik", "дустлик": "Do'stlik", "doʻslik": "Do'stlik", "doslik": "Do'stlik", "дослик": "Do'stlik",
    "paxtakor": "Paxtakor", "пахтакор": "Paxtakor",
    "g'allaorol": "G'allaorol", "ғаллаорол": "G'allaorol", "галлаарал": "G'allaorol",
    "baxmal": "Baxmal", "бахмал": "Baxmal", "o'smat": "O'smat", "ўсмат": "O'smat",
    "mirzacho'l": "Mirzacho'l", "мирзачўл": "Mirzacho'l", "gagarin": "Gagarin", "гагарин": "Gagarin",
    "forish": "Forish", "фориш": "Forish",

    # --- SIRDARYO VILOYATI ---
    "sirdaryo": "Sirdaryo", "сирдарё": "Sirdaryo", "сырдарья": "Sirdaryo", 
    "guliston": "Guliston", "гулистон": "Guliston", "гулистан": "Guliston", "guloston": "Guliston", "гулостон": "Guliston",
    "yangiyer": "Yangiyer", "янгиер": "Yangiyer",
    "shirin": "Shirin", "ширин": "Shirin",
    "baxt": "Baxt", "бахт": "Baxt",
    "boyovut": "Boyovut", "боёвут": "Boyovut", "баяут": "Boyovut",
    "sardoba": "Sardoba", "сардоба": "Sardoba",
    "oqoltin": "Oqoltin", "оқолтин": "Oqoltin",
    "sayxunobod": "Sayxunobod", "сайхунобод": "Sayxunobod",
    "xovos": "Xovos", "ховос": "Xovos", "хаваст": "Xovos",
    "dashtobod": "Dashtobod", "даштобод": "Dashtobod",

    # --- XORAZM VILOYATI ---
    "xorazm": "Xorazm", "хоразм": "Xorazm", "хорезм": "Xorazm", "xorazim": "Xorazm", "хоразим": "Xorazm",
    "urganch": "Urganch", "урганч": "Urganch", "ургенч": "Urganch", 
    "xiva": "Xiva", "хива": "Xiva",
    "xonqa": "Xonqa", "хонқа": "Xonqa", "ханка": "Xonqa", "xanqa": "Xonqa", "ханқа": "Xonqa", "xanqo": "Xonqa", "ханқо": "Xonqa", "ханко": "Xonqa",
    "shovot": "Shovot", "шовот": "Shovot", "шават": "Shovot",
    "bog'ot": "Bog'ot", "боғот": "Bog'ot", "багат": "Bog'ot",
    "gurlan": "Gurlan", "гурлан": "Gurlan",
    "hazorasp": "Hazorasp", "ҳазорасп": "Hazorasp", "хазарасп": "Hazorasp",
    "qo'shko'pir": "Qo'shko'pir", "қўшкўпир": "Qo'shko'pir", "кошкупыр": "Qo'shko'pir",
    "yangiariq": "Yangiariq", "янгиариқ": "Yangiariq",
    "tuproqqal'a": "Tuproqqal'a", "тупроққалъа": "Tuproqqal'a", "пити": "Tuproqqal'a",

    # --- QORAQALPOG'ISTON RESPUBLIKASI ---
    "qoraqalpog'iston": "Qoraqalpog'iston", "qoraqalpogiston": "Qoraqalpog'iston", "каракалпакстан": "Qoraqalpog'iston",
    "nukus": "Nukus", "нукус": "Nukus", "shortanboy": "Nukus", "шўртанбой": "Nukus", "шуртанбой": "Nukus", "шуртанбай": "Nukus",
    "xo'jayli": "Xo'jayli", "хўжайли": "Xo'jayli", "ходжейли": "Xo'jayli",
    "qo'ng'irot": "Qo'ng'irot", "қўнғирот": "Qo'ng'irot", "кунград": "Qo'ng'irot", "кунгирот": "Qo'ng'irot", "кунгирод": "Qo'ng'irot", "кунгират": "Qo'ng'irot", "qungirot": "Qo'ng'irot", "qungirod": "Qo'ng'irot",
    "to'rtko'l": "To'rtko'l", "тўрткўл": "To'rtko'l", "турткуль": "To'rtko'l", "turtkul": "To'rtko'l", "турткул": "To'rtko'l", "турткулдан": "To'rtko'l", "tortkol": "To'rtko'l",
    "beruniy": "Beruniy", "беруний": "Beruniy", "бируни": "Beruniy",
    "mang'it": "Mang'it", "манғит": "Mang'it", "мангит": "Mang'it", "amudaryo": "Amudaryo", "амударё": "Amudaryo",
    "chimboy": "Chimboy", "чимбой": "Chimboy", "чимбай": "Chimboy",
    "ellikqala": "Ellikqala", "элликқалъа": "Ellikqala", "элликкала": "Ellikqala",
    "taxtako'pir": "Taxtako'pir", "тахтакўпир": "Taxtako'pir",
    "mo'ynoq": "Mo'ynoq", "мўйноқ": "Mo'ynoq", "муйнак": "Mo'ynoq",

    # ========================================================
    # XALQARO YO'NALISHLAR (MDH, Rossiya, Qozog'iston, Turkiya, Xitoy va h.k.)
    # ========================================================
    # --- ROSSIYA ---
    "rossiya": "Rossiya", "россия": "Rossiya", "рф": "Rossiya", "rf": "Rossiya", "russia": "Rossiya",
    "moskva": "Moskva", "москва": "Moskva", "moscow": "Moskva",
    "piter": "Sankt-Peterburg", "питер": "Sankt-Peterburg", "sankt-peterburg": "Sankt-Peterburg", "санкт-петербург": "Sankt-Peterburg", "spb": "Sankt-Peterburg", "спб": "Sankt-Peterburg",
    "krasnodar": "Krasnodar", "краснодар": "Krasnodar",
    "rostov": "Rostov", "ростов": "Rostov",
    "samara": "Samara", "самара": "Samara",
    "qozon": "Qozon", "қозон": "Qozon", "kazan": "Qozon", "казань": "Qozon", "казан": "Qozon",
    "yekaterinburg": "Yekaterinburg", "екатеринбург": "Yekaterinburg", "ekaterinburg": "Yekaterinburg",
    "novosibirsk": "Novosibirsk", "новосибирск": "Novosibirsk", "sibir": "Sibir", "сибирь": "Sibir",
    "barnaul": "Barnaul", "барнаул": "Barnaul",
    "chelyabinsk": "Chelyabinsk", "челябинск": "Chelyabinsk",
    "ufa": "Ufa", "уфа": "Ufa",
    "saratov": "Saratov", "саратов": "Saratov",
    "volgograd": "Volgograd", "волгоград": "Volgograd",
    "voronej": "Voronej", "воронеж": "Voronej",
    "omsk": "Omsk", "омск": "Omsk",
    "perm": "Perm", "пермь": "Perm",
    "tyumen": "Tyumen", "тюмень": "Tyumen",
    "orenburg": "Orenburg", "оренбург": "Orenburg",
    "astraxan": "Astraxan", "астрахань": "Astraxan",
    "krasnoyarsk": "Krasnoyarsk", "красноярск": "Krasnoyarsk",
    "irkutsk": "Irkutsk", "иркутск": "Irkutsk",
    "vladivostok": "Vladivostok", "владивосток": "Vladivostok",
    "rubtsovsk": "Rubtsovsk", "рубцовск": "Rubtsovsk",
    "самары": "Samara", "москвы": "Moskva", "питера": "Sankt-Peterburg", "казани": "Qozon", "уфы": "Ufa",
    "челябинска": "Chelyabinsk", "екатеринбурга": "Yekaterinburg", "ростова": "Rostov", "краснодара": "Krasnodar",
    "nijniy novgorod": "Nijniy Novgorod", "нижний новгород": "Nijniy Novgorod",

    # --- QOZOG'ISTON ---
    "qozog'iston": "Qozog'iston", "qozogiston": "Qozog'iston", "қазоғистон": "Qozog'iston", "казахстан": "Qozog'iston", "kz": "Qozog'iston", "kazaxstan": "Qozog'iston",
    "sarag'ash": "Sarag'ash", "saragʻash": "Sarag'ash", "saragash": "Sarag'ash", "сарагаш": "Sarag'ash", "сарыагаш": "Sarag'ash",
    "almati": "Almati", "алматы": "Almati", "almaty": "Almati", "olmaota": "Almati", "олмаота": "Almati", "алмата": "Almati",
    "astana": "Astana", "астана": "Astana", "nursulton": "Astana", "нурсултан": "Astana",
    "chimkent": "Chimkent", "чимкент": "Chimkent", "shymkent": "Chimkent", "шымкент": "Chimkent",
    "aqtau": "Aqtau", "актау": "Aqtau", "aktau": "Aqtau",
    "aqtobe": "Aqtobe", "актобе": "Aqtobe", "aktobe": "Aqtobe",
    "qarag'anda": "Qarag'anda", "караганда": "Qarag'anda", "karaganda": "Qarag'anda",
    "taraz": "Taraz", "тараз": "Taraz",
    "turkiston": "Turkiston", "туркестан": "Turkiston", "туркистон": "Turkiston",
    "atirov": "Atirau", "атырау": "Atirau", "atyrau": "Atirau",
    "qostanay": "Qostanay", "костанай": "Qostanay", "kostanay": "Qostanay",
    "qizilo'rda": "Qizilo'rda", "кызылорда": "Qizilo'rda", "kzo": "Qizilo'rda",

    # --- QIRG'IZISTON ---
    "qirg'iziston": "Qirg'iziston", "қирғизистон": "Qirg'iziston", "кыргызстан": "Qirg'iziston", "киргизия": "Qirg'iziston",
    "bishkek": "Bishkek", "бишкек": "Bishkek",
    "o'sh": "O'sh", "ўш": "O'sh", "ош": "O'sh", "osh": "O'sh",
    "jalolobod": "Jalolobod", "жалалабад": "Jalolobod",

    # --- TOJIKISTON ---
    "tojikiston": "Tojikiston", "тожикистон": "Tojikiston", "таджикистан": "Tojikiston",
    "dushanbe": "Dushanbe", "душанбе": "Dushanbe",
    "xo'jand": "Xo'jand", "худжанд": "Xo'jand", "leninobod": "Xo'jand", "sug'd": "Sug'd", "сугд": "Sug'd",

    # --- TURKIYA ---
    "turkiya": "Turkiya", "турция": "Turkiya", "turkey": "Turkiya",
    "istanbul": "Istanbul", "истанбул": "Istanbul", "истамбул": "Istanbul",
    "mersin": "Mersin", "мерсин": "Mersin",
    "bursa": "Bursa", "бурса": "Bursa",
    "izmir": "Izmir", "измир": "Izmir",
    "antaliya": "Antaliya", "анталья": "Antaliya", "antalya": "Antaliya",
    "anqara": "Anqara", "анкара": "Anqara",

    # --- XITOY ---
    "xitoy": "Xitoy", "хитой": "Xitoy", "китай": "Xitoy", "china": "Xitoy",
    "urumchi": "Urumchi", "урумчи": "Urumchi", "urumqi": "Urumchi",
    "yivu": "Yiwu", "yiwu": "Yiwu", "иу": "Yiwu",
    "xorgos": "Xorgos", "хоргос": "Xorgos", "khorgos": "Xorgos",
    "guanchjou": "Guanchjou", "гуанчжоу": "Guanchjou", "guangzhou": "Guanchjou",
    "pekin": "Pekin", "пекин": "Pekin", "beijing": "Pekin",
    "qashqar": "Qashqar", "кашгар": "Qashqar",

    # --- BELARUS, KAVKAZ, EFRAT/ERON, AFG'ONISTON ---
    "belarus": "Belarus", "беларусь": "Belarus", "belorussiya": "Belarus", "белоруссия": "Belarus",
    "minsk": "Minsk", "минск": "Minsk",
    "gruziya": "Gruziya", "грузия": "Gruziya", "tbilisi": "Tbilisi", "тбилиси": "Tbilisi", "poti": "Poti", "поти": "Poti",
    "ozarbayjon": "Ozarbayjon", "озарбайжон": "Ozarbayjon", "азербайджан": "Ozarbayjon", "boku": "Baku", "баку": "Baku",
    "eron": "Eron", "эрон": "Eron", "иран": "Eron", "tehron": "Tehron", "тегеран": "Tehron",
    "afg'oniston": "Afg'oniston", "афғонистон": "Afg'oniston", "афганистан": "Afg'oniston", "hayraton": "Hayraton", "хайратон": "Hayraton",
    "turkmaniston": "Turkmaniston", "туркманистон": "Turkmaniston", "туркменистан": "Turkmaniston", "ashxobod": "Ashxobod", "ашхабад": "Ashxobod",

    # --- UMUMIY UZBEKISTON ---
    "o'zbekiston": "O'zbekiston", "узбекистон": "O'zbekiston", "узбекистан": "O'zbekiston", "uzbekistan": "O'zbekiston", "uzb": "O'zbekiston", "узб": "O'zbekiston"
}

# Davlat va ularga tegishli asosiy shaharlar (Yo'nalish normalizatsiyasi uchun)
COUNTRY_TO_CITIES = {
    "Rossiya": {"Moskva", "Sankt-Peterburg", "Krasnodar", "Rostov", "Samara", "Qozon", "Yekaterinburg", "Novosibirsk", "Barnaul", "Chelyabinsk", "Ufa", "Saratov", "Tyumen", "Omsk", "Perm", "Voronej", "Volgograd", "Orenburg", "Astraxan", "Krasnoyarsk", "Irkutsk", "Vladivostok", "Nijniy Novgorod", "Sibir"},
    "Qozog'iston": {"Almati", "Astana", "Chimkent", "Aqtau", "Aqtobe", "Qarag'anda", "Taraz", "Turkiston", "Atirau", "Qostanay", "Qizilo'rda"},
    "Qirg'iziston": {"Bishkek", "O'sh", "Jalolobod"},
    "Tojikiston": {"Dushanbe", "Xo'jand", "Sug'd"},
    "Turkiya": {"Istanbul", "Mersin", "Bursa", "Izmir", "Antaliya", "Anqara"},
    "Xitoy": {"Urumchi", "Yiwu", "Xorgos", "Guanchjou", "Pekin", "Qashqar"},
    "Belarus": {"Minsk"},
    "Gruziya": {"Tbilisi", "Poti"},
    "Ozarbayjon": {"Baku"},
    "Eron": {"Tehron"},
    "Afg'oniston": {"Hayraton"},
    "Turkmaniston": {"Ashxobod"}
}

# O'zbekiston shaharlari va viloyatlari to'plami
UZBEKISTAN_DESTINATIONS = {
    "Toshkent", "Samarqand", "Farg'ona", "Andijon", "Namangan", "Buxoro", 
    "Qashqadaryo", "Surxondaryo", "Navoiy", "Jizzax", "Sirdaryo", "Xorazm", 
    "Qoraqalpog'iston", "Vodiy", "O'zbekiston",
    "Angren", "Olmaliq", "Chirchiq", "Bekobod", "Yangiyo'l", "Chinoz", "Zangiota", "Parkent", "Bo'ka", "Piskent", "Oqqo'rg'on", "Qibray", "Bo'stonliq", "G'azalkent", "Keles", "Nazarbek", "Yallama (Bojxona)", "G'ishtko'prik (Chernyayevka)",
    "Urgut", "Kattaqo'rg'on", "Payariq", "Chelak", "Jomboy", "Bulung'ur", "Ishtixon", "Oqdaryo", "Loyish", "Pastdarg'om", "Juma", "Paxtachi", "Ziyovuddin", "Oqtosh", "Toyloq", "Qo'shrabot",
    "Qo'qon", "Marg'ilon", "Quva", "Quvasoy", "Oltiariq", "Rishton", "Uchko'prik", "Beshariq", "Yaypan", "Bog'dod", "Buvayda", "Yozyovon", "Toshloq",
    "Asaka", "Shahrixon", "Xo'jaobod", "Qorasuv", "Paxtaobod", "Oltinko'l", "Baliqchi", "Buloqboshi", "Izboskan", "Poytug'", "Jalaquduq", "Marhamat",
    "Chust", "Pop", "Kosonsoy", "Uchqo'rg'on", "Chortoq", "To'raqo'rg'on", "Yangiqo'rg'on", "Uychi", "Haqqulobod", "Norin", "Mingbuloq",
    "G'ijduvon", "Vobkent", "Shofirkon", "Kogon", "Qorako'l", "Olot (Bojxona)", "Jondor", "Romitan", "Peshku", "Qorovulbozor",
    "Qarshi", "Shahrisabz", "Kitob", "Yakkabog'", "Koson", "Muborak", "G'uzor", "Nishon", "Dehqonobod", "Kasbi", "Mug'lon", "Chiroqchi", "Ko'kdala", "Mirishkor",
    "Termiz", "Denov", "Sho'rchi", "Qumqo'rg'on", "Oltinsoy", "Sariosiyo", "Uzun", "Boysun", "Sherobod", "Jarqo'rg'on", "Muzrabot", "Bandixon",
    "Karmana", "Qiziltepa", "Xatirchi", "Zarafshon", "Uchquduq", "Konimex", "Nurota", "Gazgon",
    "Zomin", "Zarbdor", "Do'stlik", "Paxtakor", "G'allaorol", "Baxmal", "O'smat", "Mirzacho'l", "Gagarin", "Forish",
    "Guliston", "Yangiyer", "Shirin", "Baxt", "Boyovut", "Sardoba", "Oqoltin", "Sayxunobod", "Xovos",
    "Urganch", "Xiva", "Xonqa", "Shovot", "Bog'ot", "Gurlan", "Hazorasp", "Qo'shko'pir", "Yangiariq", "Tuproqqal'a",
    "Nukus", "Xo'jayli", "Qo'ng'irot", "To'rtko'l", "Beruniy", "Mang'it", "Amudaryo", "Chimboy", "Ellikqala", "Taxtako'pir", "Mo'ynoq"
}

def normalize_destinations(destinations: List[str]) -> List[str]:
    """Bitta xabarda davlat va uning shahri kelsa (masalan Rossiya va Moskva), davlatni qisqartirib aniq shaharni qoldirish."""
    dest_set = set(destinations)
    to_remove = set()
    for country, cities in COUNTRY_TO_CITIES.items():
        if country in dest_set:
            if any(c in dest_set for c in cities):
                to_remove.add(country)
    
    # O'zbekiston va uning biror viloyati bo'lsa ham
    if "O'zbekiston" in dest_set:
        if any(d in dest_set for d in UZBEKISTAN_DESTINATIONS if d != "O'zbekiston"):
            to_remove.add("O'zbekiston")

    res = [d for d in destinations if d not in to_remove]
    return res if res else destinations

def is_relevant_to_uzbekistan(destinations: List[str], phone: Optional[str]) -> bool:
    """Xabar O'zbekiston ichki yuki yoki O'zbekiston bilan bog'liq xalqaro yuk (Chet el <-> UZB) ekanligini tekshirish."""
    if any(d in UZBEKISTAN_DESTINATIONS for d in destinations):
        return True
    if phone and phone.startswith("+998"):
        return True
    return False

# Mashina turlari (Zakazchi so'raydigan mashina turlari)
TRUCK_TYPES = [
    "fura", "фура", "isuzu", "isuzi", "isuziy", "исузу", "исузи", "исузий", "usuzi", "усузи",
    "labo", "лабо", "zil", "зил", "gazel", "газел", "gazelli", "газелли",
    "tent", "тент", "tentfura", "тентфура", "tent fura", "тент фура", "tentli fura", "тентли фура", "tentli", "тентли",
    "bort", "борт", "bortli", "бортли", "usti ochiq", "усти очик", "ochiqlab",
    "ref", "реф", "reflajator", "рефлажатор", "refrijerator", "рефрижератор", 
    "megatent", "мегатент", "mega", "мега", "автовоз", "avtovoz",
    "сцепка", "ssepka", "изотерм", "izoterm", "площадка", "plashatka", "плашатка", "ploshadka", "плошадка", "tir", "тир",
    "kamaz", "камаз", "chakman", "чакман", "shacman", "шакман", "chacman", "choqmon", "чоқмон", "chokman", "чокман",
    "tonar", "тонар", "traller", "траллер", "traler", "тралер",
    "sprinter", "спринтер", "changan", "чанган", "porter", "портер", "kia", "киа", "hyundai", "хундай", "hunday",
    "shlanda", "шланда",
    "howo", "хово", 
    "atego", "атего", "man", "ман", "daf", "даф", "scania", "скания", "volvo", "вольво",
    "samosval", "самосвал", "furgon", "фургон", "bortovoy", "бортовой",
    "prsep", "pritsep", "прицеп", "prtsep", "tirkama", "тиркама",
    "mashina", "машина", "105 kub", "105 куб", "96 kub", "96 куб", "120 kub", "120 куб", "90 kub", "90 куб"
]

# Ehtiyoj yoki so'rov so'zlari
NEED_WORDS = [
    "kerak", "керак", "kerag", "kere", "кере", "kerey", "керей", "keray", "керай", "karak", "карак",
    "kk", "кк", "k.k", "к.к", "k-k", "к-к", 
    "keremas", "керемас", "kkmas", "ккмас", "kerakmas", "керакмас",
    "zarur", "зарур", "lozim", "лозим", "darhol", "дарҳол", "дархол",
    "srochna", "срочно", "срочна", "srochno", "srochne", "tez", "тез", "tezkor", "shoshilinch", "шошилинч",
    "bormi", "борми", "bor", "бор", "yuk bor", "юк бор", "yukimiz bor", "юкимиз бор",
    "yuklanadi", "юкланади", "bosishga", "босишга",
    "yuklash", "юклаш", "ortish", "ортиш", "ortiladi", "ортилади",
    "yuklaymiz", "юклаймиз", "ertalabga", "эрталабга", "ertamanga", "эртаманга", "ertaga", "эртага",
    "mesniy", "местный", "ichki", "ички", "tashishga", "ташишга",
    "нужна", "нужен", "требуется", "ищем", "ищу", "надо", "загрузка", "погрузка", "есть груз"
]

# Yuk haqidagi batafsil tovar/mahsulot nomlari (dehqon, zavod va ombor yuklari)
CARGO_GOODS_KEYWORDS = [
    # Meva-sabzavot va dehqonchilik
    "olma", "олма", "anor", "анор", "uzum", "узум", "shaftoli", "шафтоли",
    "kartoshka", "картошка", "piyoz", "пиёз", "sabzi", "сабзи", "tarvuz", "тарвуз", "toruz", "торуз",
    "qovun", "қовун", "kovun", "ковун", "karam", "карам", "pomidor", "помидор", "bodring", "бодринг", "bodirin", "бодирин", "bodiring",
    "sholi", "шоли",
    "meva", "мева", "sabzavot", "сабзавот", "ko'kat", "кўкат", "poliz", "полиз",
    # Chorva va hayvonlar
    "mol", "мол", "mollar", "моллар", "qo'y", "қўй", "qoy", "кой",
    # Qurilish mollari
    "sement", "цемент", "ohak", "оҳак", "охак", "g'isht", "ғишт", "гишт",
    "taxta", "тахта", "shlakablok", "шлакаблок", "penoblok", "пеноблок",
    "armatura", "арматура", "truba", "труба", "qum", "қум", "shag'al", "шағал",
    "marmar", "мармар", "miramir", "мирамир", "kafel", "кафель", "shifer", "шифер", "panel", "панель",
    # Oziq-ovqat va qishloq xo'jaligi
    "un", "ун", "shakar", "шакар", "guruch", "гуруч", "yog'", "ёғ", "moy", "мой",
    "makaron", "макарон", "tuxum", "тухум", "go'sht", "гўшт", "sut", "сут", "tuz", "туз",
    "paxta", "пахта", "bug'doy", "буғдой", "arpa", "арпа", "somon", "сомон", "beda", "беда", "xashak", "хашак",
    "pres", "пресс", "press", "em", "ем", "kunjara", "кунжара", "ko'mir", "кўмир",
    "chigit", "чигит", "cigit", "цигит",
    "profil", "профиль", "gazoblok", "газоблок", "terak", "терак", "poddon", "поддон",
    "selitra", "селитра", "o'g'it", "ўғит", "угит", "gipsokarton", "гипсокартон", "penoplast", "пенопласт",
    # Sanoat, maishiy va xomashyo
    "pampers", "памперс", "ko'ch", "коч", "куч",
    "karobka", "каробка", "quti", "қути", "idish", "идиш", "baklashka", "баклашка",
    "mebel", "мебель", "matras", "матрас", "gilam", "гилам", "kiyim", "кийим",
    "trikotaj", "трикотаж", "mato", "мато", "texnika", "техника", "stanok", "станок",
    "zapchast", "запчаст", "xomashyo", "хомашё", "tovar", "товар", "traktor", "трактор",
    # O'lchov birliklari
    "tonna", "тонна", "tn", "тн", "tona", "тона", "kub", "куб", "kublik", "кублик", "qop", "қоп", "dona", "дона",
    "kg", "кг", "кило", "kilo", "metr", "метр", "metrli", "метрли"
]

# Mashina turi ko'rsatilmagan, lekin to'g'ridan-to'g'ri yuk mavjudligini bildiruvchi kalit so'zlar
CARGO_AVAILABLE_KEYWORDS = [
    "yuk bor", "юк бор", "yukbor", "юкбор",
    "yukimiz bor", "юкимиз бор", "yukimizbor", "юкимизбор",
    "yuk bor edi", "юк бор эди",
    "yuk mavjud", "юк мавжуд",
    "yuk chiqdi", "юк чиқди",
    "yuk tayyor", "юк тайёр",
    "gruz bor", "груз бор",
    # Ertaga, ertalabga yuk e'lonlari
    "ertaga yuk bor", "эртага yuk bor",
    "ertalabga yuk bor", "эрталабга юк бор",
    "ertamanga yuk bor", "эртаманга юк бор",
    "ertalab yuk bor", "эрталаб юк бор",
    "ertaga yuk", "эртага юк",
    "ertalabga yuk", "эрталабга юк",
    "ertamanga yuk", "эртаманга юк",
    "ertalab yuklanadi", "эрталаб юкланади",
    "ertaga yuklanadi", "эртага юкланади",
    "ertaga yukimiz bor", "эртага юкимиз бор",
    "ertalabga yukimiz bor", "эрталабга юкимиз бор",
    "ertaga ertalab", "эртага эрталаб",
    "ertaga chiqadi", "эртага чиқади",
    "ertalab chiqadi", "эрталаб чиқади"
]

# Dispetcher STOP-SO'ZLARI (AGENTS.md bo'yicha to'liq)
DISPATCHER_STOP_WORDS = frozenset([
    # 1. Keshbek / Otkat (darhol chetlatiladi)
    "keshbek", "keshbek bor", "keshbek beramiz", "keshbekli", "keshbekka",
    "кешбек", "кешбек бор", "кешбек берамиз",
    "otkad", "otkat", "otkat bor", "otkad bor", "откат", "откад",
    # 2. Dispetcherlik / Vositachilik so'zlari
    "baza", "база", "dispetcher", "dispecher", "dispatcher", "logist",
    "диспетчер", "диспечер", "диспечир", "диспичир", "диспеч", "диспич", "dispetchir", "dispechir",
    "логист", "xizmati", "хизмати", "potolki xizmati",
    "kanalimizga", "gruppaga", "kanalga kiring", "obuna bo'ling", "kanalga",
    "каналга", "группага", "обуна",
    "диспечир керакмас", "диспечер керакмас", "диспетчер керакмас", "dispetcher kerakmas", "dispetcherlar bezovta qilmasin",
    "lagistla", "лагистла",
    # 3. Chetlatilgan mezonlar (faqat soxta to'lov va rasmiy vositachilik)
    "fraxt", "фрахт", "perechislenie", "перечисление", "beznal", "безнал",
    # 4. Dispetcherlarning texnik terminlari (vositachilar shabloni)
    "догруз", "dogruz", "попутка", "poputka", "сборный", "паллет", "паллетах", "паллета", 
    "паллетлар", "pallet", "боковая", "верхняя", "санпаспорт", "чистый тент", 
    "договорная", "dogovor", "dogovornaya", "договор", "пустой карубка", "пустой коробка",
    # 5. Doimiylik va Reklama belgilari
    "har kuni", "ҳар куни", "doimiy", "доимий", "kunlik", "кунлик",
    "hamkorlik", "ҳамкорлик", "kamyob", "kamob",
    # 7. Vositachilik yuklash / avans / bozor shablonlari
    "avans", "аванс", "avans beriladi", "аванс берилади", "avans beramiz", "аванс берамиз",
    "ortamiz", "ортамиз", "tola ortamiz", "тола ортамиз", "sim ortamiz", "сим ортамиз",
    "yuklaymiz", "юклаймиз", "ortib beramiz", "ортиб берамиз", "yuklab beramiz", "юклаб берамиз",
    "bozor kutaradi", "bozorda turadi", "kun bozor", "кун бозор",
    "kartaga tashlaymiz", "kartaga tashlab beramiz", "картага ташлаймиз",
    # 8. Shafyorlar aloqaga va vositachilik chaqiriqlari (AGENTS.md 13-band)
    "shafyorlar aloqaga", "шафёрлар алокага", "шафёрлар алоқага",
    "shofirlar aloqaga", "шофёрлар алокага", "шофирлар алоқага", "шофирлар алокага", "шоферлар алокага",
    "shafyor aloqaga", "shofir aloqaga", "шофир алокага", "шафёр алокага",
    "haydovchilar aloqaga", "хайдовчилар алокага", "ҳайдовчилар алоқага",
    "haydovchi aloqaga", "хайдовчи алокага", "ҳайдовчи алоқага",
    "voditellar aloqaga", "водителлар алокага", "водители на связь",
    "wafyorla aloqaga", "вафёрла алокага", "wafyorlar aloqaga", "shofirla aloqaga", "шофирла алокага",
    "wafyorla", "wafyorlar",
    "aloqaga chiqing", "aloqaga chiqinglar", "алокага чикинг", "алоқага чиқинг",
    "aloqaga chiqsin", "aloqaga chiqilsin", "алокага чиксин", "алоқага чиқсин",
    "aloqaga chiqilar", "алокага чикилар", "алоқага чиқинглар",
    "aloqaga", "алокага", "алоқага", "на связь",
    # 9. "Shafyor kerak" / "Haydovchi kerak" filtri (AGENTS.md 14-band)
    "shafyor kerak", "shofir kerak", "shofyor kerak", "haydovchi kerak", "haydovchilar kerak", 
    "shafyorlar kerak", "shofirlar kerak", "voditel kerak", "voditellar kerak",
    "водитель нужен", "водители нужны", "нужен водитель", "нужны водители",
    "шофер керак", "шофёр керак", "шафёр керак", "хайдовчи керак", "ҳайдовчи керак",
    "хайдовчилар керак", "ҳайдовчилар керак", "шафёрлар керак", "шофёрлар керак",
    "shafyor zarur", "haydovchi zarur", "shofir zarur", "ҳайдовчи зарур", "шафёр зарур",
    "shafyor izlaymiz", "haydovchi izlaymiz", "haydovchi qidirilmoqda", "shafyor qidirilmoqda",
    "хайдовчи кидирилмокда", "шафёр кидирилмокда", "haydovchilikka", "shafyorlikka"
])

# Ayol ismlari, so'zlari va qo'shimchalari (Faqat erkaklar qabul qilinadi - AGENTS.md 7-band)
_FEMALE_NAMES = frozenset([
    "adeliya", "adiba", "adolat", "afifa", "afruza", "afsona", "aida", "aisha",
    "albina", "alfiya", "alina", "alisa", "aliya", "amaliya", "amina", "angelina",
    "anisa", "anna", "anora", "anya", "arina", "arjumand", "asalbonu", "asila",
    "asmo", "atirgul", "aylin", "ayzada", "azaliya", "aziza", "badia", "bahora",
    "barchin", "barchinoy", "bargida", "barno", "barnoxon", "bashorat", "basira", "begim",
    "begimzoda", "begoyim", "behruza", "bibi", "bibioysha", "bibisora", "bibixonim",
    "billura", "binafsha", "binoz", "bo'ston", "bonu", "boston", "charos", "daliya",
    "darya", "daryo", "dasha", "diana", "dilafro'z", "dilafroz", "dilangez", "dilarom",
    "dilbahor", "dilbaroy", "dildora", "dildoraxon", "dilfuz", "dilfuza", "dilfuzaxon", "dilnavoz",
    "dilnoza", "dilnozaxon", "dilnur", "dilnura", "dilorom", "diloromoy", "dilovar", "dilrabo",
    "dilroz", "dilsabo", "dilshoda", "dilyora", "dilzoda", "dinara", "diora", "diydor",
    "diyora", "diyorka", "dono", "durdona", "e'tibor", "e'zoza", "elena", "elina",
    "elnora", "etibor", "ezoza", "farahnaz", "farangiz", "farida", "faridaxon", "farina",
    "farzona", "feruza", "feruzaxon", "firuza", "fotima", "fotimaxon", "fozila", "g'azal",
    "g'uncha", "gavhar", "gavharoy", "gavharshod", "gazal", "go'zaloy", "gozal", "gozaloy",
    "gulandom", "gulbadan", "gulbahor", "gulbarchin", "gulbegim", "gulchehra", "guldasta", "gulgun",
    "gulhumor", "guli", "gulira'no", "gulirano", "guljamol", "gulmira", "gulnora", "gulnoraxon",
    "gulnoza", "gulnozaxon", "guloro", "gulpari", "gulrux", "gulruxsor", "gulsanam", "gulshan",
    "gulshoda", "gulsima", "gultoj", "gulya", "gulzoda", "guncha", "guzal", "habiba",
    "hadicha", "hadiya", "hafza", "halima", "hamida", "hanifa", "hilola", "hulkar",
    "humayro", "hurriyat", "husniya", "husnobod", "iffat", "ifora", "ilmira", "imona",
    "inobat", "intizor", "iqlima", "ira", "irfon", "irina", "iroda", "ismigul",
    "istora", "jamila", "jamina", "jannatoy", "jasmina", "jayrona", "jibek", "juliana",
    "kameliya", "kamila", "kamilla", "kamola", "kamolaxon", "karima", "karina", "katya",
    "kavsar", "kibriyo", "kimyo", "klara", "komila", "kristina", "ksyusha", "kumush",
    "kumushbibi", "kumushoy", "kunduzoy", "latofat", "layli", "laylo", "lena", "leyla",
    "leyli", "lobar", "lola", "lolazor", "lutfiya", "madina", "madinaxon", "maftuna",
    "mahbuba", "mahfuza", "mahina", "mahliyo", "mahmuda", "mahzuna", "malika", "malikabonu",
    "malohat", "mamlakat", "mamura", "manzura", "marhabo", "marina", "mariya", "marjona",
    "marvarid", "maryam", "masha", "mastura", "masuma", "matluba", "mavjuda", "mavluda",
    "mayram", "medina", "mehrangiz", "mehriban", "mehribon", "mehriniso", "milana", "mina",
    "mohichehra", "mohichexra", "mohigul", "mohina", "mohinur", "mohira", "mohlaroyim", "mohpari",
    "mohtob", "moxira", "muattar", "mubina", "mumtoz", "mumtozbegim", "munajat", "munavvar",
    "munira", "munisa", "munojat", "muqaddas", "mushtariy", "muslima", "muslimaxon", "muxabbat",
    "muxlisa", "muyassar", "nabila", "nafisa", "nafosat", "naima", "nargiz", "nargiza",
    "nargizaxon", "nasiba", "nasibaxon", "nastya", "natasha", "navbahor", "navro'za", "navroza",
    "nazira", "nazokat", "nigina", "nigora", "nihola", "nilufar", "niso", "nodira",
    "nodirabegim", "nodiraxon", "noila", "norjon", "nozanin", "nozigul", "nozima", "nura",
    "nuriya", "nurjamol", "nurxon", "odina", "oksana", "olga", "oliyaxon", "oltinoy",
    "omina", "oqila", "oybarchin", "oychechak", "oychuchuk", "oydin", "oygul", "oyjamol",
    "oymomo", "oynisa", "oysha", "oysuluv", "oyzoda", "ozoda", "parizod", "parizoda",
    "parvina", "pokiza", "polina", "qirmizoy", "qunduz", "qutlug'nigor", "qutlugnigor", "quvonchoy",
    "ra'no", "rahima", "rano", "rayhon", "rayhona", "rayhonaxon", "rayyona", "regina",
    "risolat", "robiya", "robiyaxon", "rohatoy", "rohila", "roza", "roziya", "rumayso",
    "ruqayya", "rusalina", "ruxshona", "sabina", "sabohat", "sadaf", "sadiya", "safina",
    "safiya", "saida", "saidabonu", "saidaxon", "sajida", "sakina", "salima", "salomat",
    "salomatxon", "salsabil", "samira", "sanam", "sanamoyim", "sanobar", "saodat", "sarvara",
    "sarvinoz", "sayyora", "sayyoraxon", "sevara", "sevinch", "shabnam", "shahina", "shahlo",
    "shahnoza", "shahnozaxon", "shahodat", "shahrizoda", "shahzoda", "shamsiya", "sharifa", "sharofat",
    "shaxlo", "shaxnoza", "shaxodat", "shaxrizoda", "shaxzoda", "shirin", "shirinaxon", "shodiya",
    "shohida", "shohista", "shohsanam", "shoira", "shoxida", "shoxsanam", "shukrona", "sitora",
    "sohiba", "soliha", "solixa", "sora", "subhina", "sug'diyona", "sugdiyona", "sumayya",
    "sumbula", "surayyo", "surayyoxon", "suyumbika", "suyunbibi", "sveta", "svetlana", "tabassum",
    "tahmina", "tamara", "tanho", "tanya", "tasnim", "tasnima", "tatyana", "to'maris",
    "tomaris", "tomiris", "tozagul", "tumaris", "tursinoy", "tursunoy", "ufor", "uljana",
    "ulug'oy", "ulugoy", "umida", "umidaxon", "valeriya", "vasila", "vazira", "vika",
    "viktoriya", "visola", "xadicha", "xadichaxon", "xalisa", "xilola", "xolida", "xonim",
    "xonzoda", "xosiyat", "xumor", "xurshida", "xurshidabonu", "yasina", "yasmina", "yulduz",
    "yulduzoy", "yulia", "yuliya", "zara", "zarifa", "zarina", "zarnigor", "zebiniso",
    "zebo", "zilola", "zinnura", "ziyoda", "zuhal", "zuhra", "zuhraaxon", "zulayho",
    "zulfiniso", "zulfiya", "zulhumor", "zulxumor", "zulya", "zumrad", "аделия", "адиба",
    "адолат", "азалия", "азиза", "аида", "аиша", "айзада", "айлин", "алина",
    "алиса", "алия", "алфия", "альбина", "амалия", "амина", "ангелина", "аниса",
    "анна", "анора", "аня", "аржуманд", "арина", "асалбону", "асила", "асмо",
    "атиргул", "афифа", "афруза", "афсона", "бадиа", "баргида", "барно", "барнохон",
    "барчин", "барчиной", "басира", "бахора", "башорат", "баҳора", "бегим", "бегимзода",
    "бегойим", "бехруза", "беҳруза", "бибиойша", "бибисора", "бибихоним", "биллура",
    "бинафша", "биноз", "бону", "бустон", "бўстон", "вазира", "валерия", "васила",
    "вика", "виктория", "висола", "гавхар", "гавхаршод", "гавҳар", "гавҳарой", "гавҳаршод",
    "газал", "гузал", "гузалой", "гуландом", "гулбадан", "гулбарчин", "гулбахор", "гулбаҳор",
    "гулбегим", "гулгун", "гулдаста", "гулжамол", "гулзода", "гулираъно", "гулмира", "гулноза",
    "гулнозахон", "гулнора", "гулнорахон", "гулоро", "гулпари", "гулрух", "гулрухсор", "гулсанам",
    "гулсима", "гултож", "гулхумор", "гулчехра", "гулчеҳра", "гулшан", "гулшода", "гульмира",
    "гуля", "гулҳумор", "гунча", "гўзал", "гўзалой", "далия", "дарья", "дарё",
    "даша", "диана", "дийдор", "дилангез", "диларом", "дилафруз", "дилафрўз", "дилбарой",
    "дилбахор", "дилбаҳор", "дилдора", "дилдорахон", "дилзода", "дилнавоз", "дилноза", "дилнозахон",
    "дилнура", "диловар", "дилором", "дилоромой", "дилрабо", "дилроз", "дилсабо", "дилфуз",
    "дилфуза", "дилфузахон", "дилшода", "дильнур", "дилёра", "динара", "диора", "диёра",
    "диёрка", "доно", "дурдона", "елена", "елина", "елнора", "еъзоза", "еътибор",
    "жайрона", "жамила", "жамина", "жаннатой", "жасмина", "жибек", "жулиана", "зара",
    "зарина", "зарифа", "зарнигор", "зебинисо", "зебо", "зилола", "зиннура", "зиёда",
    "зулайхо", "зулайҳо", "зулфинисо", "зулфия", "зулхумор", "зуля", "зулҳумор", "зумрад",
    "зухал", "зухра", "зухрахон", "зуҳал", "зуҳра", "иклима", "илмира", "имона",
    "инобат", "интизор", "ира", "ирина", "ирода", "ирфон", "исмигул", "истора",
    "ифора", "иффат", "иқлима", "кавсар", "камелия", "камила", "камола", "камолахон",
    "карима", "карина", "катя", "кибриё", "кимё", "кирмизой", "клара", "комила",
    "кристина", "ксюша", "кувончой", "кумуш", "кумушбиби", "кумушой", "кундуз", "кундузой",
    "кутлуғнигор", "лайли", "лайло", "латофат", "лейла", "лейли", "лена", "лобар",
    "лола", "лолазор", "лутфия", "мавжуда", "мавлуда", "мадина", "мадинахон", "майрам",
    "малика", "маликабону", "малохат", "малоҳат", "мамлакат", "мамура", "манзура", "марварид",
    "маржона", "марина", "мария", "мархабо", "марьям", "марям", "марҳабо", "мастура",
    "масума", "матлуба", "мафтуна", "махбуба", "махзуна", "махина", "махлиё", "махмуда",
    "махфуза", "маша", "маҳбуба", "маҳзуна", "маҳина", "маҳлиё", "маҳмуда", "маҳфуза",
    "медина", "мехрангиз", "мехрибан", "мехрибон", "мехринисо", "меҳрангиз", "меҳрибан", "меҳрибон",
    "меҳринисо", "милана", "мина", "мохигул", "мохина", "мохинур", "мохира", "мохларойим",
    "мохпари", "мохтоб", "моҳигул", "моҳина", "моҳинур", "моҳира", "моҳларойим", "моҳпари",
    "моҳтоб", "муаттар", "мубина", "мукаддас", "мумтоз", "мумтозбегим", "мунаввар", "мунажат",
    "мунира", "муниса", "муножат", "муслима", "муслимахон", "мухлиса", "муштарий", "муяссар",
    "муқаддас", "муҳаббат", "набила", "навбахор", "навбаҳор", "навруза", "наврўза", "назира",
    "назокат", "наима", "наргиз", "наргиза", "наргизахон", "насиба", "насибахон", "настя",
    "наташа", "нафиса", "нафосат", "нигина", "нигора", "нилуфар", "нисо", "нихола",
    "ниҳола", "нодира", "нодирабегим", "нодирахон", "нозанин", "нозигул", "нозима", "ноила",
    "норжон", "нура", "нуржамол", "нурия", "нурхон", "одина", "озода", "ойбарчин",
    "ойгул", "ойдин", "ойжамол", "ойзода", "оймомо", "ойниса", "ойсулув", "ойчечак",
    "ойчучук", "ойша", "оксана", "олияхон", "олтиной", "ольга", "омина", "парвина",
    "паризод", "паризода", "покиза", "полина", "райхон", "райхона", "райхонахон", "райёна",
    "райҳон", "райҳона", "рахима", "раъно", "раҳима", "регина", "рисолат", "робия",
    "робияхон", "роза", "розия", "рохатой", "рохила", "роҳатой", "роҳила", "рукайя",
    "румайсо", "русалина", "рухшона", "руқайя", "сабина", "сабохат", "сабоҳат", "садаф",
    "садия", "сажида", "саида", "саидабону", "саидахон", "сайёра", "сайёрахон", "сакина",
    "салима", "саломат", "саломатхон", "салсабил", "самира", "санам", "санамойим", "санобар",
    "сарвара", "сарвиноз", "сафина", "сафия", "света", "светлана", "севара", "севинч",
    "ситора", "солиха", "солиҳа", "сора", "сохиба", "соҳиба", "субхина", "субҳина",
    "сугдиёна", "сумайя", "сумбула", "сурайё", "сурайёхон", "суюмбика", "суюнбиби", "суғдиёна",
    "табассум", "тамара", "танхо", "таня", "танҳо", "тасним", "таснима", "татьяна",
    "тахмина", "таҳмина", "тозагул", "томирис", "тумарис", "турсиной", "турсуной", "тўмарис",
    "улжана", "улугой", "улуғой", "умида", "умидахон", "уфор", "фарангиз", "фарахназ",
    "фараҳназ", "фарзона", "фарида", "фаридахон", "фарина", "фатима", "феруза", "ферузахон",
    "фируза", "фозила", "фотима", "фотимахон", "хабиба", "хадича", "хадичахон", "хадия",
    "халима", "халиса", "хамида", "ханифа", "хафза", "хилола", "холида", "хонзода",
    "хоним", "хосият", "хулкар", "хумайро", "хумор", "хуррият", "хуршида", "хуршидабону",
    "хусния", "хуснобод", "чарос", "шабнам", "шамсия", "шарифа", "шарофат", "шахзода",
    "шахина", "шахло", "шахноза", "шаходат", "шахризода", "шаҳзода", "шаҳина", "шаҳло",
    "шаҳноза", "шаҳнозахон", "шаҳодат", "шаҳризода", "ширин", "ширинахон", "шодия", "шоира",
    "шохида", "шохиста", "шохсанам", "шоҳида", "шоҳиста", "шоҳсанам", "шукрона", "юлдуз",
    "юлдузой", "юлия", "юля", "ясина", "ясмина", "ғазал", "ғунча", "қирмизой",
    "қувончой", "қундуз", "қутлугнигор", "қутлуғнигор", "ҳабиба", "ҳадича", "ҳадия", "ҳалима",
    "ҳамида", "ҳанифа", "ҳафза", "ҳилола", "ҳулкар", "ҳумайро", "ҳуррият", "ҳусния",
    "ҳуснобод",
    # Transliteratsiyalar va qo'shimcha ayol ismlari / familiyalari
    "muatar", "shakhnoza", "shakhlo", "mokhira", "gulchekhra", "shakhzoda",
    "shakhodat", "shakhrizoda", "rukhshona", "khilola", "khadicha", "kholida",
    "khulkar", "khursheda", "khurshida", "eva", "kamilla", "kamila",
    "diloromkhon", "barnokhon", "muattaraxon", "shanazarova", "shonazarova",
    "shahnazarova", "shakhnazarova", "bahtiyorova", "baxtiyorova",
    # Fatima, Fotima, Mohizoda, Asal va transliteratsiyalar
    "fatima", "фатима", "fatime", "фатиме", "fatimat", "фатимат", "fatya", "фатя", "fatu", "фату",
    "mohizoda", "мохизода", "моҳизода", "moxizoda", "mokhizoda", "shaxrizoda", "shahrizoda", "parizoda",
    "asal", "асал", "asalka", "асалка", "asalcha", "асалча", "asalya", "асаля", "asalina", "асалина",
    "zuxra", "зухра", "zuxro", "зухро", "zuhro", "зуҳро",
    "guzel", "гузель", "guzalya", "гузаля", "gozal", "гозал", "go'zal", "гўзал",
    "aysha", "айша", "aisha", "аиша", "aysham", "айшам",
    "hadicha", "хадича", "xadicha", "хадиджа", "khadija", "khadicha",
    "shoyira", "шойира", "diyoraxon", "диёрахон", "munisaxon", "мунисахон", "jasminaxon", "жасминахон",
    "mubinaxon", "мубинахон", "farangizaxon", "фарангизахон", "robiyaxon", "робияхон", "safiyaxon", "сафияхон",
    "sofiya", "софия", "sofya", "софья", "sumayyaxon", "сумайяхон", "masturaxon", "мастурахон",
    "nargizaxon", "наргизахон", "charosxon", "чаросхон", "rayhonaxon", "райҳонахон", "kumushoy", "кумушой",
    "elmira", "элмира", "эльмира", "irodaxon", "иродахон",
])

_FEMALE_WORDS = ["lady", "ledi", "леди", "miss", "mrs", "girl", "madam", "ayol", "qiz", "аёл", "қиз", "женщина", "девушка", "oilali", "оилали", "ona", "она", "kelin", "келин", "opa", "опа", "xola", "хола", "aya", "ая"]

_FEMALE_SUFFIX_REGEX = re.compile(
    r"(?:eva+|ova+|yeva+|ovna+|evna+|yevna+|qizi|kizi|bonu|xonim|begim|zoda|skaya+|tskaya+|ckaya+|ina+|"
    r"ева+|ова+|ёва+|евна+|овна+|ёвна+|қизи|кизи|бону|хоним|бегим|зода|ская+|цкая+|ина+)(?:ga|dan|ni|ning|га|дан|ни|нинг)?$",
    re.IGNORECASE
)

# Ayol familiyalari patterni (so'z boshida, o'rtasida yoki oxirida bo'lsa ham: Karimova, Aliyeva, Turgunova, Murodova, Каримова, Алиева...)
_FEMALE_SURNAME_PATTERN = re.compile(
    r"(?i)[a-zA-Zа-яА-ЯёЁўқғҳЎҚҒҲ]{2,}(?:eva+|ova+|yeva+|ovna+|evna+|yevna+|qizi|kizi|bonu|xonim|begim|zoda|skaya+|tskaya+|ckaya+|ina+|"
    r"ева+|ова+|ёва+|евна+|овна+|ёвна+|қизи|кизи|бону|хоним|бегим|зода|ская+|цкая+|ина+)",
    re.IGNORECASE
)

# Erkatoy / erkalash ayol shakllari (Maftushka, Zarinushka, Madinok, Gulchixor, Sevarish va h.k.)
_FEMALE_DIMINUTIVES_REGEX = re.compile(
    r"(?i)("
    r"maftush|мафтуш|"
    r"zarinush|заринуш|zarinoch|зариноч|zarink|заринк|"
    r"madinok|мадинок|madinush|мадинуш|madinoch|мадиноч|madink|мадинк|"
    r"gulchixor|гулчихор|gulchik|гульчик|gulchichek|гулчичек|"
    r"sevarish|севариш|sevarush|севаруш|sevark|севарк|"
    r"malikush|маликуш|malikoch|маликоч|malikk|маликк|"
    r"shahlokash|шахлокаш|shahlosh|шахлош|shahloch|шахлоч|"
    r"barnoch|барноч|barnush|барнуш|barnosh|барнош|"
    r"dilfuzach|дилфузач|dilfuzoch|дилфузоч|dilfuzik|дилфузик|"
    r"nigorash|нигораш|nigorush|нигоруш|nigoroch|нигороч|"
    r"kamolush|камолуш|kamoloch|камолоч|kamolk|камолк|"
    r"dilnozush|дилнозуш|dilnozish|дилнозиш|dilnozik|дилнозик|"
    r"shahnozush|шахнозуш|shahnozish|шахнозиш|shahnozik|шахнозик|"
    r"feruzik|ферузик|feruzchik|ферузчик|feruzush|ферузуш|"
    r"lobarik|лобирик|lobarush|лобаруш|lobarch|лобарч|"
    r"sitorik|ситорик|sitorush|ситоруш|sitorch|ситорч|"
    r"munisko|муниско|munisk|муниск|munisoch|мунисоч|"
    r"rayhonch|райхонч|rayhonush|райхонуш|"
    r"umidach|умидач|umidush|умидуш|umidch|умидч|"
    r"nodirk|нодирк|nodirush|нодируш"
    r")"
)

# Vizual ramzlar va grekcha harflarni lotinchaga o'girish jadvali (baxtiyorova, baxromovna va h.k.)
GREEK_LOOKALIKES = str.maketrans({
    'α': 'a', 'β': 'b', 'γ': 'g', 'δ': 'd', 'ε': 'e', 'ζ': 'z', 'η': 'n', 'θ': 'o',
    'ι': 'i', 'κ': 'k', 'λ': 'l', 'μ': 'm', 'ν': 'v', 'ξ': 'x', 'ο': 'o', 'π': 'n',
    'ρ': 'r', 'σ': 'o', 'τ': 't', 'υ': 'u', 'φ': 'f', 'χ': 'x', 'ψ': 'ps', 'ω': 'w',
})

# Leetspeak raqamlarni harflarga o'girish (0->o, 1->i, 3->e, 4->a, 5->s, 8->b)
LEET_LOOKALIKES = str.maketrans({
    '0': 'o', '1': 'i', '3': 'e', '4': 'a', '5': 's', '8': 'b'
})

# Profil ismidagi taqiqlangan kasb/reklama so'zlari (barcha variatsiyalar, xato yozuvlar va qisqartmalar)
PROFILE_STOP_WORDS = frozenset([
    "dispetcher", "dispecher", "dispatcher", "dispetchir", "dispechir", "dispetchr", "dispechr",
    "despetcher", "despecher", "despatcher", "despetchr", "despechr", "desp", "desper",
    "диспеччер", "диспетчер", "диспечер", "диспечир", "диспичир", "диспеч", "диспич", "диспетчир",
    "деспечер", "деспетчер", "деспечр", "деспетчр", "десп", "деспечир",
    "disper", "диспер", "disp", "дисп", "dispa", "диспа", "dispo", "диспо", "dispr", "диспр",
    "dsp", "дсп", "dispetcr", "dispecr", "dispatsh", "dispater",
    "logist", "logistika", "логист", "логистика", "lagist", "лагист", "lagistika", "лагистика",
    "logistka", "логистка", "lagistka", "лагистка", "dispetcherka", "dispecherka", "диспечерка", "диспетчерка",
    "kargo", "cargo", "карго", "gruz", "груз", "perevozka", "перевозка", "makler", "маклер", "baza", "база",
    "menej", "менедж", "menejer", "менеджер", "manager", "operator", "оператор", "trans", "транс", "express", "экспресс", "intertrans",
    "gruzoperevozki", "gruzo", "yuk tashish", "freight", "фрейт", "forwarding", "форвардинг", "ekspeditor", "экспедитор", "broker", "брокер"
])

# Profil ismidagi va usernamesidagi dispetcher/logist qisqartmalari (LOG65, disp_01, disper, desp, dsp va h.k.)
DISP_LOG_PROFILE_REGEX = re.compile(
    r"(?i)("
    r"\w*(?:disp|дисп|desp|десп|dsp|дсп|dispatch|диспатч|dispech|диспеч|dispetch|диспетч|despech|деспеч|despetch|деспетч|dispechr|диспечр|dispetchr|диспетчр|disper|диспер|dispr|диспр|dispa|диспа|dispo|диспо)\w*"
    r"|"
    r"\w*(?:logist|логист|lagist|лагист|logistik|логистик|logistic|logistics|logistka|логистка|logyst|logi\b|логи\b|lagi\b|лаги\b)\w*"
    r"|"
    r"\w*(?:log|лог)\d+\w*"
    r"|"
    r"\w+log\b|\w+лог\b"
    r"|"
    r"(?:^|[\W_\d])(?:log|лог)\w*"
    r"|"
    r"\w*(?:cargo|kargo|карго|trans|транс|freight|фрейт|forwarding|форвардинг|экспедитор|ekspeditor|expeditor|makler|маклер|broker|брокер|perevozk|перевозк|gruzoperevozk|грузоперевозк|operator|оператор|menejer|менеджер|manager)\w*"
    r")"
)

def check_dispatcher_profile_name(first_name: Optional[str], last_name: Optional[str], username: Optional[str]) -> Tuple[bool, str]:
    """
    Foydalanuvchi qoidasi: Akkaunt nomida (display name yoki username) 'LOG', 'LOGIST', 'DISP', 'DISPER',
    'DESP', 'DSP' yoki shunga o'xshash qisqartmalar (LOG65, Лог65, disp_01, despetcher, dsp va h.k.) qatnashgan
    bo'lsa — bunday e'lonlar dispetcher deb topiladi va yopiq guruhga ASLO uzatilmaydi.
    """
    fn_s = first_name or ""
    ln_s = last_name or ""
    un_s = (username or "").lstrip("@")
    raw_name = f"{fn_s} {ln_s}".strip()

    if not raw_name and not un_s:
        return True, "OK"

    norm_name = unicodedata.normalize('NFKD', raw_name).translate(GREEK_LOOKALIKES)
    norm_un = unicodedata.normalize('NFKD', un_s).translate(GREEK_LOOKALIKES)
    leet_name = norm_name.translate(LEET_LOOKALIKES)
    leet_un = norm_un.translate(LEET_LOOKALIKES)

    # 1. Nuqta, chiziqcha va probellarni olib tashlab sof harflarni tekshirish (d.i.s.p, d-i-s-p, l.o.g.i.s.t)
    clean_no_punct = re.sub(r'[^a-zA-Zа-яА-ЯёЁ]+', '', f"{raw_name} {un_s}").lower()
    clean_leet = re.sub(r'[^a-zA-Zа-яА-ЯёЁ]+', '', f"{leet_name} {leet_un}").lower()

    check_targets = [
        raw_name, un_s,
        norm_name, norm_un,
        leet_name, leet_un,
        f"{norm_name} {norm_un}".lower(),
        f"{leet_name} {leet_un}".lower(),
        clean_no_punct, clean_leet
    ]

    for target in check_targets:
        if not target:
            continue
        m = DISP_LOG_PROFILE_REGEX.search(target)
        if m:
            matched_word = m.group(0).strip(" _-.")
            if matched_word.lower() not in ("ulogbek", "улогбек"):
                return False, f"Profil nomida dispetcher/logist belgisi yoki qisqartmasi aniqlandi: '{matched_word}'"

        target_lower = target.lower()
        for stop_w in PROFILE_STOP_WORDS:
            if stop_w in target_lower:
                return False, f"Profil nomida dispetcherlik so'zi bor: '{stop_w}'"

    return True, "OK"

# Telefon raqam patterni (O'zbekiston, Rossiya, Qozog'iston, MDH va xalqaro)
PHONE_PATTERN = re.compile(
    r"(?:"
    r"(?:\+?998[\s\-\.]?)?(?:9[0-9]|88|33|77|50|55|20)[\s\-\.]?[0-9]{3}[\s\-\.]?[0-9]{2}[\s\-\.]?[0-9]{2}"
    r"|"
    r"(?:\+?7|8)[\s\-\.]?(?:\([0-9]{3}\)|[0-9]{3})[\s\-\.]?[0-9]{3}[\s\-\.]?[0-9]{2}[\s\-\.]?[0-9]{2}"
    r"|"
    r"\+?996[\s\-\.]?[0-9]{3}[\s\-\.]?[0-9]{2}[\s\-\.]?[0-9]{2}[\s\-\.]?[0-9]{2}"
    r"|"
    r"\+?992[\s\-\.]?[0-9]{2}[\s\-\.]?[0-9]{3}[\s\-\.]?[0-9]{4}"
    r"|"
    r"\+?90[\s\-\.]?[0-9]{3}[\s\-\.]?[0-9]{3}[\s\-\.]?[0-9]{2}[\s\-\.]?[0-9]{2}"
    r")"
)

# Havolalar va username patterni
LINK_PATTERN = re.compile(r"(@[a-zA-Z0-9_]{4,}|t\.me\/[a-zA-Z0-9_]+|https?:\/\/\S+|www\.\S+)", re.IGNORECASE)

# Emojilar patterni (Dispetcher shablonini aniqlash — to'liq emojilar, belgilar va simvollar)
EMOJI_PATTERN = re.compile(
    r"[\U00010000-\U0010ffff\u2600-\u27bf\u2300-\u23ff\u2b50\u203c\u2049\u2139\u2194-\u21aa\u2934-\u2935\u3030\u303d\u3297\u3299]"
)

def check_female_username(username: Optional[str]) -> Tuple[bool, str]:
    """
    Username ichida ayol ismi, familiyasi yoki ayollik belgilari bor-yo'qligini
    (shu jumladan leetspeak: 0->o, 1->i, 3->e, 4->a va ruscha transliteratsiyalarni) chuqur tekshirish.
    """
    if not username:
        return True, "Username yo'q"
    
    un_clean = str(username).lstrip("@").strip()
    if not un_clean:
        return True, "Bo'sh username"
    
    # 0. Dispetcher va Logist qisqartmalari tekshiruvi (LOG65, disper, disp, logist va h.k.)
    disp_ok, disp_reason = check_dispatcher_profile_name("", "", un_clean)
    if not disp_ok:
        return False, disp_reason

    # 1. Fancy fontlar va grekcha vizual ramzlarni lotinchaga normallashtirish
    norm_un = unicodedata.normalize('NFKD', un_clean).translate(GREEK_LOOKALIKES).lower()

    # 2. Leet va transliteratsiya variantlari (0->o, 1->i, 3->e, 4->a, kh->x, kh->h)
    leet_un = norm_un.translate(LEET_LOOKALIKES)
    variants = {
        norm_un,
        leet_un,
        norm_un.replace('kh', 'x'),
        leet_un.replace('kh', 'x'),
        norm_un.replace('kh', 'h'),
        leet_un.replace('kh', 'h'),
    }

    male_exceptions = frozenset([
        "bobur", "bahodir", "botir", "timur", "damir", "sarvar", "shavkat",
        "alixon", "amirxon", "islomxon", "muhammadxon", "shohruxxon", "mirzoxon", "asadbek",
        "alisher", "javohir", "sardor", "sanjar", "eldor", "nodirbek", "farrux", "jasur",
        "rozali", "roziboy", "rozimat", "rozimuhammad", "rozibek", "roziqul", "ruzali",
        "mavlono", "mavlonov"
    ])

    for var in variants:
        # A. Stop so'zlar
        for fw in _FEMALE_WORDS:
            if fw in var:
                return False, f"Username ayol foydalanuvchiga tegishli (so'z: {fw})"

        # B. Tokenlar bo'yicha tekshirish (ajratilgan qismlar)
        tokens = [t for t in re.split(r"[^a-zA-Zа-яА-ЯёЁўқғҳЎҚҒҲ]+", var) if len(t) >= 2]
        for t in tokens:
            if t in _FEMALE_NAMES:
                return False, f"Username ayol ismi: '{t}'"
            if t in ("qizi", "қизи", "кизи", "bonu", "бону", "xonim", "хоним", "begim", "бегим", "xon", "хон", "kelin", "келин", "opa", "опа"):
                return False, f"Username ayol qo'shimchasi: '{t}'"
            if _FEMALE_SUFFIX_REGEX.search(t) or _FEMALE_SURNAME_PATTERN.search(t):
                if len(t) >= 4 and t not in male_exceptions and not any(t.endswith(mex) for mex in male_exceptions):
                    return False, f"Username ayol familiyasi: '{t}'"
            if ((t.endswith("xon") and len(t) >= 5) or (t.endswith("хон") and len(t) >= 5)) and t not in male_exceptions:
                return False, f"Username ayol ismi (...xon): '{t}'"
            if (t.endswith("oy") or t.endswith("ой")) and len(t) >= 5 and t not in ("saroy", "сарой", "boyvoy"):
                return False, f"Username ayol ismi (...oy): '{t}'"
            if (t.endswith("zoda") or t.endswith("зода")) and len(t) >= 6:
                return False, f"Username ayol familiyasi (...zoda): '{t}'"
            if (t.endswith("gul") or t.endswith("гул")) and len(t) >= 5:
                return False, f"Username ayol ismi (...gul): '{t}'"
            if (t.endswith("niso") or t.endswith("нисо")) and len(t) >= 5:
                return False, f"Username ayol ismi (...niso): '{t}'"

        # C. Birlashgan matn tekshiruvi (muattarshanazarova, logistmuattar, shanazarova01)
        squashed = re.sub(r"[^a-zA-Zа-яА-ЯёЁўқғҳЎҚҒҲ]+", "", var)
        for fn in _FEMALE_NAMES:
            if len(fn) >= 4 and fn in squashed:
                if fn in ("roza", "роза") and any(mex in squashed for mex in male_exceptions):
                    continue
                return False, f"Username ayol ismi qismi: '{fn}'"

        sm = _FEMALE_SURNAME_PATTERN.search(squashed)
        if sm:
            m_str = sm.group(0)
            if not any(m_str.endswith(mex) for mex in male_exceptions):
                return False, f"Username ayol familiyasi qismi: '{m_str}'"

        # D. Erkatoy / erkalash ayol shakllari tekshiruvi (Maftushka, Zarinushka, Madinok, Gulchixor, Sevarish va h.k.)
        dim_m = _FEMALE_DIMINUTIVES_REGEX.search(var) or _FEMALE_DIMINUTIVES_REGEX.search(squashed)
        if dim_m:
            return False, f"Username ayol kishi erkalash shakli: '{dim_m.group(0)}'"

    return True, "Username qabul qilindi"


def check_sender_profile(first_name: Optional[str], last_name: Optional[str], username: Optional[str]) -> Tuple[bool, str]:
    """Jo'natuvchi profili tekshiruvi: Ayol profillar va Emojili akkauntlar darhol chetlatiladi, faqat erkaklar qabul qilinadi."""
    fn_s = first_name or ""
    ln_s = last_name or ""
    un_s = (username or "").lstrip("@")
    raw_name = f"{fn_s} {ln_s}".strip()

    # 0. Butunlay bo'sh akkauntlar tekshiruvi (AGENTS.md: xorijiy/noodatiy harflar va niklar to'siqsiz qabul qilinadi)
    if not raw_name.strip() and not un_s.strip():
        return False, "Profil nomi va username mavjud emas"

    # 1. Emojili akkauntlar filtri (AGENTS.md 7-band)
    if EMOJI_PATTERN.search(raw_name) or EMOJI_PATTERN.search(un_s):
        return False, "Profil nomida emoji mavjud (dispetcherlik belgisi)"

    # 1.1. Maxsus username filtri (barcha berilgan username'lar tekshiriladi)
    if un_s.strip():
        for single_un in un_s.split():
            is_un_ok, un_reason = check_female_username(single_un)
            if not is_un_ok:
                return False, un_reason

    # 1.2. Dispetcher va Logist qisqartmalari tekshiruvi (LOG65, Лог65, disp_01, disper va h.k.)
    disp_ok, disp_reason = check_dispatcher_profile_name(first_name, last_name, username)
    if not disp_ok:
        return False, disp_reason

    # Fancy fontlar va grekcha vizual ramzlarni lotinchaga normallashtirish
    norm_name = unicodedata.normalize('NFKD', raw_name).translate(GREEK_LOOKALIKES)
    norm_un = unicodedata.normalize('NFKD', un_s).translate(GREEK_LOOKALIKES)

    # 2. Profil nomidagi dispetcherlik so'zlari
    full_profile_clean = f"{norm_name} {norm_un}".lower()
    for stop_w in PROFILE_STOP_WORDS:
        if stop_w in full_profile_clean:
            return False, f"Profil nomida dispetcherlik so'zi bor: {stop_w}"

    # 3. Ayollik so'zlari (lady, miss, ayol, qiz, kelin, opa...)
    for fw in _FEMALE_WORDS:
        if fw in full_profile_clean:
            return False, f"Profil ayol foydalanuvchiga tegishli (so'z: {fw})"

    male_exceptions = frozenset([
        "bobur", "bahodir", "botir", "timur", "damir", "sarvar", "shavkat",
        "alixon", "amirxon", "islomxon", "muhammadxon", "shohruxxon", "mirzoxon", "asadbek",
        "alisher", "javohir", "sardor", "sanjar", "eldor", "nodirbek", "farrux", "jasur",
        "rozali", "roziboy", "rozimat", "rozimuhammad", "rozibek", "roziqul", "ruzali",
        "mavlono", "mavlonov"
    ])

    # 4. Profil va username variantlari (oddiy, leetspeak 0->o/1->i, kh->x)
    profile_variants = {
        full_profile_clean,
        full_profile_clean.translate(LEET_LOOKALIKES),
        full_profile_clean.replace('kh', 'x'),
        full_profile_clean.translate(LEET_LOOKALIKES).replace('kh', 'x')
    }

    for p_var in profile_variants:
        tokens = [t.lower() for t in re.split(r"[^a-zA-Zа-яА-ЯёЁўқғҳЎҚҒҲ]+", p_var) if len(t) >= 2]
        for t in tokens:
            # Aniq ayol ismi tekshiruvi
            if t in _FEMALE_NAMES:
                return False, f"Profil ayol foydalanuvchiga tegishli (ism: {t})"
            # Mustaqil ayollik so'zlari: qizi, bonu, xonim, begim, xon, kelin, opa, ona
            if t in ("qizi", "қизи", "кизи", "bonu", "бону", "xonim", "хоним", "begim", "бегим", "xon", "хон", "kelin", "келин", "opa", "опа"):
                return False, f"Profil ayol foydalanuvchiga tegishli (qo'shimcha: {t})"
            # Familiya / qo'shimcha tekshiruvi (...eva, ...ova, ...ovna, ...yevna, ...qizi, ...bonu, ...ina)
            if _FEMALE_SUFFIX_REGEX.search(t) or _FEMALE_SURNAME_PATTERN.search(t):
                if len(t) >= 4 and t not in male_exceptions and not any(t.endswith(mex) for mex in male_exceptions):
                    return False, f"Profil ayol foydalanuvchiga tegishli (familiya/qo'shimcha: {t})"
            # Qo'shma ismlar (...xon / ...хон bilan tugagan barcha ayol ismlari)
            if ((t.endswith("xon") and len(t) >= 5) or (t.endswith("хон") and len(t) >= 5)) and t not in male_exceptions:
                return False, f"Profil ayol foydalanuvchiga tegishli (ism: {t})"
            # ...oy / ...ой bilan tugagan ayol ismlari (Kumushoy, Oltinoy, Diloromoy)
            if (t.endswith("oy") or t.endswith("ой")) and len(t) >= 5 and t not in ("saroy", "сарой", "boyvoy"):
                return False, f"Profil ayol foydalanuvchiga tegishli (ism: {t})"
            # ...zoda / ...зода bilan tugagan ayol ismlari (Shahrizoda, Gulzoda, Parizoda)
            if (t.endswith("zoda") or t.endswith("зода")) and len(t) >= 6:
                return False, f"Profil ayol foydalanuvchiga tegishli (ism: {t})"
            # ...gul / ...гул bilan tugagan ayol ismlari (Mohigul, Oygul, Atirgul)
            if (t.endswith("gul") or t.endswith("гул")) and len(t) >= 5:
                return False, f"Profil ayol foydalanuvchiga tegishli (ism: {t})"
            # ...niso / ...нисо bilan tugagan ayol ismlari (Zebiniso, Mehriniso)
            if (t.endswith("niso") or t.endswith("нисо")) and len(t) >= 5:
                return False, f"Profil ayol foydalanuvchiga tegishli (ism: {t})"

        # 5. Username va nomdagi birlashgan ayol ismlari tekshiruvi (masalan diyora1121, soliha_dilnur, madina2026, dilnoza_trans)
        for sub_part in p_var.split():
            squashed = re.sub(r"[^a-zA-Zа-яА-ЯёЁўқғҳЎҚҒҲ]+", "", sub_part)
            if not squashed:
                continue
            for fn in _FEMALE_NAMES:
                if len(fn) >= 4 and fn in squashed:
                    if fn in ("roza", "роза") and any(mex in squashed for mex in male_exceptions):
                        continue
                    return False, f"Profil ayol foydalanuvchiga tegishli (ism qismi: {fn})"

            # 5.1. Birlashgan matnda ayol familiyasi tekshiruvi (masalan: bahtiyorovalogist, zilolabaxtiyorova, yusupova01)
            surname_match = _FEMALE_SURNAME_PATTERN.search(squashed)
            if surname_match:
                matched_str = surname_match.group(0)
                if not any(matched_str.endswith(mex) for mex in male_exceptions):
                    return False, f"Profil ayol foydalanuvchiga tegishli (familiya: {matched_str})"

            # 5.2. Erkatoy / erkalash ayol shakllari tekshiruvi (Maftushka, Zarinushka, Madinok, Gulchixor, Sevarish va h.k.)
            dim_match = _FEMALE_DIMINUTIVES_REGEX.search(sub_part) or _FEMALE_DIMINUTIVES_REGEX.search(squashed)
            if dim_match:
                return False, f"Profil ayol foydalanuvchiga tegishli (erkalash shakli: {dim_match.group(0)})"

    return True, "Profil qabul qilindi"

# Yashiringan ayol dispetcherlar (erining yoki o'g'lining akkauntidan e'lon beruvchilar) filtri
_FEMALE_TEXT_NAMES = frozenset([
    name for name in _FEMALE_NAMES 
    if len(name) >= 4 and name not in (
        "shirin", "ширин", "olma", "олма", "anor", "анор", 
        "karam", "карам", "roza", "роза", "buxoro", "бухоро", 
        "asaka", "асака", "quva", "қува", "quvasoy", "қувасой",
        "daryo", "дарё", "boston", "бостон", "bo'ston", "бўстон", "бустон",
        "dono", "доно", "g'azal", "gazal", "ғазал", "газал", "tanho", "танхо", "танҳо", "zara", "зара"
    )
])

_FEMALE_TEXT_PATTERNS = [
    r"\b(?:opa|опа|opaga|опага|opam|опам|opangiz|опангиз)\b",
    r"\b(?:xola|хола|xolam|холам|xolaga|холага)\b",
    r"\b(?:aya|ая|ayam|аям|ayaga|аяга)\b",
    r"\b(?:kelin|келин|kelinga|келинга)\b",
    r"\b(?:akajonlar|акажонlar|akalarim|акаларим|shafyor akalar|шафёр акалар)\b",
    r"\b(?:joningizdan aylanay|жонингиздан айланай)\b",
    r"\b(?:iltimos yaxshilab o'qing|илтимос яхшилаб ўқинг|илтимос яхшилаб укинг)\b"
]

def check_female_text_indicators(text: str) -> Tuple[bool, str]:
    """
    Erkak kishi (erining yoki o'g'lining) akkauntidan yozayotgan yashiringan
    ayol dispetcherlarni matn ichidagi so'zlar va ismlar orqali fosh qilish.
    """
    text_lower = text.lower()
    
    # 1. Matnda opa, xola, aya yoki ayollarga xos murojaatlar
    for pattern in _FEMALE_TEXT_PATTERNS:
        match = re.search(pattern, text_lower)
        if match:
            return False, f"Matnda ayol dispetcherlik belgisi aniqlandi: '{match.group(0)}'"

    # 2. Matndagi so'zlarni ajratib ayol ismlari va familiyalari bilan tekshirish
    tokens = [t for t in re.split(r"[^a-zA-Zа-яА-ЯёЁўқғҳЎҚҒҲ0-9_]+", text_lower) if len(t) >= 4]
    male_exceptions_text = ("bobur", "bahodir", "botir", "timur", "damir", "sarvar", "shavkat", "alisher", "jasur", "sanjar", "eldor")
    for token in tokens:
        if token in _FEMALE_TEXT_NAMES:
            return False, f"Matn ichida ayol ismi aniqlandi: '{token}' (ayol dispetcher)"
        if _FEMALE_SUFFIX_REGEX.search(token) or _FEMALE_SURNAME_PATTERN.search(token):
            if len(token) >= 5 and not any(token.endswith(mex) for mex in male_exceptions_text):
                return False, f"Matn ichida ayollik familiyasi/qo'shimchasi aniqlandi: '{token}'"
        # Username yoki compound ism tekshiruvi (masalan: muattar_shanazarova, karim0va, d1lnoza)
        if "_" in token or any(d in token for d in "0123456789"):
            is_un_ok, un_reason = check_female_username(token)
            if not is_un_ok:
                return False, f"Matn ichida ayol username/profili aniqlandi: '{token}' ({un_reason})"

    return True, "OK"

# Harf-raqam almashtirish (leetspeak / homoglyphs) xaritasi telefon raqamlari uchun
PHONE_LEET_MAP = str.maketrans({
    'O': '0', 'o': '0', 'О': '0', 'о': '0', 'Ө': '0', 'ө': '0',
    'l': '1', 'I': '1', 'i': '1', '|': '1', '!': '1',
    'Z': '2', 'z': '2',
    'E': '3', 'e': '3', 'З': '3', 'з': '3',
    'S': '5', 's': '5', 'С': '5', 'с': '5',
    'B': '8', 'b': '8', 'В': '8', 'в': '8'
})

UZ_MOBILE_PREFIXES = ('90', '91', '92', '93', '94', '95', '97', '98', '99', '88', '33', '77', '50', '55', '20')

def format_phone_display(phone: str) -> str:
    """Canonical telefon raqamini chiroyli o'qiladigan shaklga keltirish (+998 90 123 45 67)."""
    if not phone:
        return ""
    digits = re.sub(r"\D", "", str(phone))
    if len(digits) == 12 and digits.startswith("998"):
        return f"+998 {digits[3:5]} {digits[5:8]} {digits[8:10]} {digits[10:12]}"
    elif len(digits) == 11 and digits.startswith("7"):
        return f"+7 {digits[1:4]} {digits[4:7]} {digits[7:9]} {digits[9:11]}"
    elif len(digits) == 9 and digits.startswith(UZ_MOBILE_PREFIXES):
        return f"+998 {digits[0:2]} {digits[2:5]} {digits[5:7]} {digits[7:9]}"
    return f"+{digits}" if not str(phone).startswith("+") else str(phone)

def extract_all_canonical_phones(text: str) -> List[str]:
    """Matndagi barcha telefon raqamlarini kanonik (998901234567...) ko'rinishida topish."""
    if not text:
        return []
    text_leet = text.translate(PHONE_LEET_MAP)
    found = []

    # 1. +998...
    for m in re.finditer(r'\+?\s*9\s*9\s*8[\s\-\.\(]*([0-9\s\-\.\(\)]{9,20})', text_leet):
        d = re.sub(r'\D', '', m.group(1))
        if len(d) >= 9 and d[:9].startswith(UZ_MOBILE_PREFIXES):
            p = f'998{d[:9]}'
            if p not in found:
                found.append(p)

    # 2. UZ mobil prefikslari (90, 91, 88...): '9 0 1 2 3 4 5 6 7' yoki '90 123 45 67'
    for pref in UZ_MOBILE_PREFIXES:
        p0, p1 = pref[0], pref[1]
        pattern = rf'(?:^|[^\w\+])\(?({p0}[\s\-\.]*{p1}[\s\-\.\)]*(?:[\s\-\.]*[0-9]){{7}})(?:[^\d]|$)'
        for m in re.finditer(pattern, text_leet):
            d = re.sub(r'\D', '', m.group(1))
            if len(d) == 9 and d.startswith(UZ_MOBILE_PREFIXES):
                p = f'998{d}'
                if p not in found:
                    found.append(p)

    # 3. 8 bilan boshlangan UZ raqamlari (8 90 123 45 67)
    for m in re.finditer(r'\b8[\s\-\.\(]*([0-9\s\-\.\(\)]{9,20})', text_leet):
        d = re.sub(r'\D', '', m.group(1))
        if len(d) >= 9 and d[:9].startswith(UZ_MOBILE_PREFIXES):
            p = f'998{d[:9]}'
            if p not in found:
                found.append(p)
        elif len(d) >= 10 and d[:10].startswith(('9', '4', '8')):
            p = f'7{d[:10]}'
            if p not in found:
                found.append(p)

    # 4. Rossiya/Qozog'iston (+7)
    for m in re.finditer(r'\+?\s*7[\s\-\.\(]*([0-9\s\-\.\(\)]{10,20})', text_leet):
        d = re.sub(r'\D', '', m.group(1))
        if len(d) >= 10:
            p = f'7{d[:10]}'
            if p not in found:
                found.append(p)

    return found

def extract_phone(text: str) -> Optional[str]:
    """
    Matndan telefon raqamini ajratib olish va yagona kanonik formatga (998901234567) keltirish.
    Bo'shliqlar ('9 0 1 2 3...'), tirelar, qavslar va harf-raqam almashtirishlar (O->0, l->1, z->2)
    to'liq hisobga olinadi.
    """
    phones = extract_all_canonical_phones(text)
    return phones[0] if phones else None

PROVINCE_DISTRICTS: Dict[str, set] = {
    "Toshkent": {"Angren", "Olmaliq", "Chirchiq", "Bekobod", "Yangiyo'l", "Chinoz", "Zangiota", "Parkent", "Bo'ka", "Piskent", "Oqqo'rg'on", "Qibray", "Bo'stonliq", "G'azalkent", "Keles", "Nazarbek", "Ohangaron"},
    "Samarqand": {"Urgut", "Kattaqo'rg'on", "Payariq", "Chelak", "Jomboy", "Bulung'ur", "Ishtixon", "Oqdaryo", "Loyish", "Pastdarg'om", "Juma", "Paxtachi", "Ziyovuddin", "Oqtosh", "Toyloq", "Qo'shrabot"},
    "Farg'ona": {"Qo'qon", "Marg'ilon", "Quva", "Quvasoy", "Oltiariq", "Rishton", "Uchko'prik", "Beshariq", "Yaypan", "Bog'dod", "Buvayda", "Yozyovon", "Toshloq"},
    "Andijon": {"Asaka", "Shahrixon", "Xo'jaobod", "Qorasuv", "Paxtaobod", "Oltinko'l", "Baliqchi", "Buloqboshi", "Izboskan", "Poytug'", "Jalaquduq", "Marhamat"},
    "Namangan": {"Chust", "Pop", "Kosonsoy", "Uchqo'rg'on", "Chortoq", "To'raqo'rg'on", "Yangiqo'rg'on", "Uychi", "Haqqulobod", "Norin", "Mingbuloq"},
    "Buxoro": {"G'ijduvon", "Vobkent", "Shofirkon", "Kogon", "Qorako'l", "Olot (Bojxona)", "Jondor", "Romitan", "Peshku", "Qorovulbozor"},
    "Qashqadaryo": {"Qarshi", "Shahrisabz", "Kitob", "Yakkabog'", "Koson", "Muborak", "G'uzor", "Nishon", "Dehqonobod", "Kasbi", "Mug'lon", "Chiroqchi", "Ko'kdala", "Mirishkor"},
    "Surxondaryo": {"Termiz", "Denov", "Sho'rchi", "Qumqo'rg'on", "Oltinsoy", "Sariosiyo", "Uzun", "Boysun", "Sherobod", "Jarqo'rg'on", "Muzrabot", "Bandixon"},
    "Navoiy": {"Karmana", "Qiziltepa", "Xatirchi", "Zarafshon", "Uchquduq", "Konimex", "Nurota", "Gazgon"},
    "Jizzax": {"Zomin", "Zarbdor", "Do'stlik", "Paxtakor", "G'allaorol", "Baxmal", "O'smat", "Mirzacho'l", "Gagarin", "Forish"},
    "Sirdaryo": {"Guliston", "Yangiyer", "Shirin", "Baxt", "Boyovut", "Sardoba", "Oqoltin", "Sayxunobod", "Xovos"},
    "Xorazm": {"Urganch", "Xiva", "Xonqa", "Shovot", "Bog'ot", "Gurlan", "Hazorasp", "Qo'shko'pir", "Yangiariq", "Tuproqqal'a"},
    "Qoraqalpog'iston": {"Nukus", "Xo'jayli", "Qo'ng'irot", "To'rtko'l", "Beruniy", "Mang'it", "Amudaryo", "Chimboy", "Ellikqala", "Taxtako'pir", "Mo'ynoq"}
}

def extract_destinations(text: str) -> List[str]:
    """
    Matndan yo'nalishlarni aniq e'lon beruvchi ko'rsatgan tartibda va grammatik
    qo'shimchalar (-dan / -ga, из / в) orqali [Qayerdan] [Qayerga] shaklida ajratib olish.
    """
    text_lower = text.lower()
    found_matches = []
    # Kalit so'zlarni uzunligi bo'yicha saralash (uzunroq so'zlar birinchi)
    sorted_keys = sorted(REGIONS_MAP.keys(), key=lambda k: len(k), reverse=True)
    matched_spans = []

    for key in sorted_keys:
        if len(key) <= 3:
            pattern = r"(?<![a-zA-Z0-9_а-яА-ЯёЁўқғҳЎҚҒҲ])" + re.escape(key) + r"(?![a-zA-Z0-9_а-яА-ЯёЁўқғҳЎҚҒҲ])"
        else:
            pattern = r"(?<![a-zA-Z0-9_а-яА-ЯёЁўқғҳЎҚҒҲ])" + re.escape(key)

        for m in re.finditer(pattern, text_lower):
            start, end = m.span()
            if any(s <= start and end <= e for (s, e) in matched_spans):
                continue

            canonical = REGIONS_MAP[key]
            after_text = text_lower[end:end+15]
            before_text = text_lower[max(0, start-15):start]

            is_origin = False
            is_dest = False

            # O'zbekcha jo'nalish qo'shimchalari: -dan / dan / dan...
            if re.match(r"^(?:[\s\-_'ʼ`]*)(dan|den|дан|ден)\b", after_text):
                is_origin = True
            elif re.match(r"^(?:[\s\-_'ʼ`]*)(ga|ka|qa|ge|га|ка|қа|ге)\b", after_text):
                is_dest = True

            # Ruscha predloglar: из Самары / в Андижан
            if re.search(r"\b(из|с|со|от)\s*$", before_text):
                is_origin = True
            elif re.search(r"\b(в|во|до|на|к)\s*$", before_text):
                is_dest = True

            matched_spans.append((start, end))
            found_matches.append({
                "canonical": canonical,
                "start": start,
                "end": end,
                "is_origin": is_origin,
                "is_dest": is_dest,
                "key": key
            })

    if not found_matches:
        return []

    # Matndagi tartib (start) bo'yicha saralash (e'lon beruvchi qanday yozgan bo'lsa)
    found_matches.sort(key=lambda x: x["start"])

    # Bir xil kanonik nom bo'lsa bittasini qoldirish
    seen_canonicals = set()
    unique_matches = []
    for m in found_matches:
        if m["canonical"] not in seen_canonicals:
            seen_canonicals.add(m["canonical"])
            unique_matches.append(m)

    # Viloyat va uning tumani birga kelsa (masalan Andijon Shahrixondan -> Shahrixon qoladi)
    to_remove_canonicals = set()
    matched_canonicals = {m["canonical"] for m in unique_matches}
    for prov, dists in PROVINCE_DISTRICTS.items():
        if prov in matched_canonicals:
            found_dists = [d for d in dists if d in matched_canonicals]
            if found_dists:
                to_remove_canonicals.add(prov)

    # Davlat va shahar kelsa, davlatni olib tashlash (masalan Rossiya va Samara -> Samara qoladi)
    for country, cities in COUNTRY_TO_CITIES.items():
        if country in matched_canonicals:
            if any(c in matched_canonicals for c in cities):
                to_remove_canonicals.add(country)

    filtered_matches = [m for m in unique_matches if m["canonical"] not in to_remove_canonicals]
    if not filtered_matches:
        filtered_matches = unique_matches

    if len(filtered_matches) == 1:
        return [filtered_matches[0]["canonical"]]

    if len(filtered_matches) == 2:
        m1, m2 = filtered_matches[0], filtered_matches[1]

        # Aniq -dan / -ga grammatik belgilari bo'yicha:
        if m1["is_dest"] and m2["is_origin"]:
            return [m2["canonical"], m1["canonical"]]
        elif m1["is_origin"] and not m2["is_origin"]:
            return [m1["canonical"], m2["canonical"]]
        elif m2["is_dest"] and not m1["is_dest"]:
            return [m1["canonical"], m2["canonical"]]
        elif m2["is_origin"] and not m1["is_origin"]:
            return [m2["canonical"], m1["canonical"]]
        elif m1["is_dest"] and not m2["is_dest"]:
            return [m2["canonical"], m1["canonical"]]

        # Agar maxsus belgi bo'lmasa, matndagi e'lon beruvchi ko'rsatgan ketma-ketlik (chapdan o'ngga):
        return [m1["canonical"], m2["canonical"]]

    # Agar 2 tadan ko'p manzil bo'lsa, barchasini qaytaramiz (filtr ko'p yo'nalish deb chetlatishi uchun)
    return [m["canonical"] for m in filtered_matches]

def has_direction_indicator(text_lower: str, destinations: List[str]) -> bool:
    """AGENTS.md: Yo'nalish [Qayerdan] [Qayerga] tuzilishi mavjudligini tekshirish."""
    if not destinations:
        return False
    # Agar 2 ta yo'nalish bo'lsa (masalan Toshkent va Samarqand, yoki Moskva va Toshkent) - yo'nalish bor
    if len(destinations) >= 2:
        return True
    
    # Agar faqat 1 ta shahar bo'lsa, yo'nalish qo'shimchasi bo'lishi shart (-ga, -dan, -qa, -ka)
    # YOKI mahalliy (mesniy/ichki) qatnov ko'rsatilgan bo'lsa
    if any(m in text_lower for m in ["mesniy", "местный", "ichki", "ички", "город", "shahar ichi", "viloyat ichi"]):
        return True

    suffixes = ["ga", "dan", "qa", "ka", "da", "га", "дан", "қа", "ка", "да"]
    canonical = destinations[0]
    for key, val in REGIONS_MAP.items():
        if val == canonical:
            for suf in suffixes:
                if f"{key}{suf}" in text_lower or f"{key} {suf}" in text_lower:
                    return True
            # Ruscha predloglar: "из Москвы", "в Ташкент", "до Алматы", "от Москвы"
            if re.search(r"\b(из|в|во|на|до|от)\s+" + re.escape(key), text_lower):
                return True
    return False

TRUCK_EXTRACTION_RULES = [
    (r"\b(?:fura\s*parovoz|фура\s*паравоз|parovoz|паравоз)(?:lar|лар|ga|га)?\b", "Fura (Parovoz)"),
    (r"\b(?:tent\s*fura|тент\s*фура|tentli\s*fura|тентли\s*фура|fura|фура)(?:lar|лар|ga|га|da|да|dan|дан)?\b", "Fura"),
    (r"\b(?:isuzu|isuzi|isuziy|исузу|исузи|исузий|usuzi|усузи)(?:lar|лар|ga|га|da|да|dan|дан)?\b", "Isuzu"),
    (r"\b(?:chakman|shacman|chacman|чакман|шакман|choqmon|chokman|чокман)(?:lar|лар|ga|га|da|да)?\b", "Chacman"),
    (r"\b(?:kamaz|камаз)(?:lar|лар|ga|га|da|да|dan|дан)?\b", "Kamaz"),
    (r"\b(?:labo|лабо)(?:lar|лар|ga|га|da|да|dan|дан)?\b", "Labo"),
    (r"\b(?:gazel|газел|gazelli|газелли)(?:lar|лар|ga|га|da|да)?\b", "Gazel"),
    (r"\b(?:zil|зил)(?:lar|лар|ga|га|da|да)?\b", "Zil"),
    (r"\b(?:tonar|тонар)(?:lar|лар|ga|га|da|да)?\b", "Tonar"),
    (r"\b(?:traller|траллер|traler|тралер)(?:lar|лар|ga|га)?\b", "Traller"),
    (r"\b(?:sprinter|спринтер)(?:lar|лар|ga|га)?\b", "Sprinter"),
    (r"\b(?:changan|чанган)(?:lar|лар|ga|га)?\b", "Changan"),
    (r"\b(?:porter|портер)(?:lar|лар|ga|га)?\b", "Porter"),
    (r"\b(?:kia|киа)(?:lar|лар|ga|га)?\b", "Kia"),
    (r"\b(?:hyundai|хундай|hunday)(?:lar|лар|ga|га)?\b", "Hyundai"),
    (r"\b(?:ref|реф|reflajator|рефлажатор|refrijerator|рефрижератор)(?:lar|лар|ga|га)?\b", "Ref"),
    (r"\b(?:tent|тент|tentli|тентли)(?:lar|лар|ga|га)?\b", "Tent"),
    (r"\b(?:bort|борт|bortli|бортли|usti\s*ochiq|усти\s*очик)\b", "Bortli"),
    (r"\b(?:shlanda|шланда)(?:lar|лар|ga|га)?\b", "Shlanda"),
    (r"\b(?:howo|хово)(?:lar|лар|ga|га)?\b", "Howo"),
]

GOODS_EXTRACTION_RULES = [
    (r"\b(?:qovun|қовун|kovun|ковун)\b", "Qovun"),
    (r"\b(?:tarvuz|тарвуз|toruz|торуз)\b", "Tarvuz"),
    (r"\b(?:piyoz|пиёз)\b", "Piyoz"),
    (r"\b(?:kartoshka|картошка)\b", "Kartoshka"),
    (r"\b(?:sabzi|сабзи)\b", "Sabzi"),
    (r"\b(?:olma|олма)\b", "Olma"),
    (r"\b(?:anor|анор)\b", "Anor"),
    (r"\b(?:uzum|узум)\b", "Uzum"),
    (r"\b(?:shaftoli|шафтоли)\b", "Shaftoli"),
    (r"\b(?:karam|карам)\b", "Karam"),
    (r"\b(?:pomidor|помидор)\b", "Pomidor"),
    (r"\b(?:bodring|бодринг|bodiring|бодиринг|bodirin|бодирин)\b", "Bodring"),
    (r"\b(?:sholi|шоли)\b", "Sholi"),
    (r"\b(?:meva|мева)\b", "Meva"),
    (r"\b(?:sabzavot|сабзавот)\b", "Sabzavot"),
    (r"\b(?:mol|мол|mollar|моллар)\b", "Mol"),
    (r"\b(?:qo'y|қўй|qoy|кой)\b", "Qo'y"),
    (r"\b(?:sement|цемент)\b", "Sement"),
    (r"\b(?:ohak|оҳак|охак)\b", "Ohak"),
    (r"\b(?:g'isht|ғишт|gisht|гишт)\b", "G'isht"),
    (r"\b(?:taxta|тахта)\b", "Taxta"),
    (r"\b(?:armatura|арматура)\b", "Armatura"),
    (r"\b(?:temir|темир|metall|металл)\b", "Temir"),
    (r"\b(?:marmar|мармар|miramir|мирамир)\b", "Marmar"),
    (r"\b(?:un|ун)\b", "Un"),
    (r"\b(?:shakar|шакар)\b", "Shakar"),
    (r"\b(?:guruch|гуруч)\b", "Guruch"),
    (r"\b(?:tuz|туз)\b", "Tuz"),
    (r"\b(?:paxta|пахта)\b", "Paxta"),
    (r"\b(?:bug'doy|буғдой|bugdoy|бугдой)\b", "Bug'doy"),
    (r"\b(?:arpa|арпа)\b", "Arpa"),
    (r"\b(?:somon|сомон)\b", "Somon"),
    (r"\b(?:ko'mir|кўмир|komir|кумир)\b", "Ko'mir"),
    (r"\b(?:mebel|мебель)\b", "Mebel"),
    (r"\b(?:texnika|техника)\b", "Texnika"),
    (r"\b(?:xashak|хашак|beda|беда)\b", "Xashak"),
    (r"\b(?:yengil\s*yuk|йенгил\s*юк)\b", "Yengil yuk"),
]

def extract_cargo_details(text: str) -> Dict[str, Any]:
    """E'lon matnidan mashina turi, tonnasi, mahsulot turi va narxini aniq ajratib olish."""
    text_lower = text.lower()

    # 1. Mashina turi
    found_trucks = []
    seen_trucks = set()
    for pattern, name in TRUCK_EXTRACTION_RULES:
        if re.search(pattern, text_lower):
            base_key = name.split()[0]
            if base_key not in seen_trucks:
                seen_trucks.add(base_key)
                found_trucks.append(name)
    truck_type = " / ".join(found_trucks[:2]) if found_trucks else None

    # 2. Tonnasi / Og'irligi
    tonnage = None
    m_t = re.search(r"\b(\d+(?:[.,]\d+)?)\s*(?:t|т|tn|тн|tonna|тонна|tona|тона)\b", text_lower)
    if m_t:
        tonnage = f"{m_t.group(1)} t"
    else:
        m_kg = re.search(r"\b(\d+)\s*(?:kg|кг|кило|kilo)\b", text_lower)
        if m_kg:
            tonnage = f"{m_kg.group(1)} kg"
        else:
            m_kub = re.search(r"\b(\d+)\s*(?:kub|куб|кублик|kublik)\b", text_lower)
            if m_kub:
                tonnage = f"{m_kub.group(1)} m³"
            else:
                m_lik = re.search(r"\b(\d+)\s*(?:lik|лик)\b(?!\s*(?:metan|gaz|метан|газ))", text_lower)
                if m_lik and int(m_lik.group(1)) in (3, 5, 10, 20):
                    tonnage = f"{m_lik.group(1)} t"

    # 3. Mahsulot / Yuk turi
    found_goods = []
    for pattern, name in GOODS_EXTRACTION_RULES:
        if re.search(pattern, text_lower) and name not in found_goods:
            found_goods.append(name)
    goods = ", ".join(found_goods[:2]) if found_goods else None

    # 4. Narxi
    price = None
    m_p = re.search(r"\b(\d+(?:[.,]\d+)?)\s*(?:mln|миллион|million|млн)\b", text_lower)
    if m_p:
        price = f"{m_p.group(1)} mln so'm"
    elif re.search(r"\b(?:kelishamiz|келишамиз|kelishamz)\b", text_lower):
        price = "Kelishamiz"

    return {
        "truck_type": truck_type,
        "tonnage": tonnage,
        "goods": goods,
        "price": price
    }

def filter_cargo_message(
    text: str, 
    is_forward: bool = False,
    first_name: Optional[str] = None,
    last_name: Optional[str] = None,
    username: Optional[str] = None
) -> Tuple[bool, str, Dict[str, Any]]:
    """
    Yuk xabarini AGENTS.md qat'iy standartlari bo'yicha saralash.
    Faqat haqiqiy zakazchilar qabul qilinadi, dispetcherlar darhol tashlanadi!
    """
    if not text:
        return False, "Matn bo'sh", {}

    # 1. Forward tekshiruvi (AGENTS.md 2-bo'lim: o'chiriladi)
    if is_forward:
        return False, "Xabar Forward qilingan (vositachi)", {}

    # 2. Matn formati (AGENTS.md: "Juda qisqa, sodda va lo'nda")
    # Zakazchilar 220 belgidan ortiq batafsil yoki rasmiy xabar yozmaydi (raqobatchi tahlili va amaliyot bo'yicha max 220 belgi)
    if len(text) > 220:
        return False, f"Matn juda uzun ({len(text)} belgi — 220 belgidan oshmasligi shart)", {}

    if len(text.strip()) < 15:
        return False, "Matn juda qisqa", {}

    # 2.1. Qatorlar soni tekshiruvi (Haqiqiy zakazchilar 2-6 qator yozadi — qo'shimcha 1-2 qatorga ruxsat)
    raw_lines = text.strip().splitlines()
    non_empty_lines = [l.strip() for l in raw_lines if l.strip()]
    if len(non_empty_lines) > 6:
        return False, f"Qatorlar soni ko'p ({len(non_empty_lines)} qator — dispetcher shabloni)", {}

    # 2.2. Sun'iy bo'sh qatorlar va orasi ochiq banner e'lonlar (Namangandan \n\n Denovga \n\n Yuk 25t...)
    empty_lines_count = sum(1 for l in raw_lines if not l.strip())
    if empty_lines_count >= 4 or (empty_lines_count >= 3 and len(raw_lines) >= (len(non_empty_lines) * 1.8)):
        return False, f"E'londa qatorlar orasida sun'iy bo'sh joylar/ochiq qatorlar qoldirilgan ({empty_lines_count} ta bo'sh qator — dispetcher shabloni)", {}

    if re.search(r"\n\s*\n\s*\n", text):
        return False, "Matnda ortiqcha bo'sh qatorlar qoldirilgan (dispetcher shabloni)", {}

    if re.search(r" {6,}", text):
        return False, "Matnda ko'p sun'iy probellar (bo'sh joylar) bor (dispetcher shabloni)", {}

    # 3. Emojilar soni (3 tadan ko'p emoji bo'lsa - dispetcher shabloni)
    if len(EMOJI_PATTERN.findall(text)) > 3:
        return False, "Matnda emojilar ko'p (dispetcher shabloni)", {}

    # 4. Ko'p telefon raqamlari tekshiruvi (dispetcherlik ofisi)
    canonical_phones_in_msg = extract_all_canonical_phones(text)
    if len(set(canonical_phones_in_msg)) > 1:
        return False, f"Bir nechta har xil telefon raqamlari ko'rsatilgan ({len(set(canonical_phones_in_msg))} ta — dispetcherlik ofisi)", {}

    text_lower = text.lower()

    # 4.1. Bir nechta mashina so'rovi tekshiruvi (2, 3, 4 ta mashinaga ruxsat — faqat 5+ ta mashina dispetcher)
    pat_multi1 = re.search(r"\b([5-9]|\d{2,})\s*(?:ta|dona|та|дона)?\s*(?:fura|tent|mashina|isuzu|labo|kamaz|gazel|man|ref|фура|тент|машина|исузу|лабо|камаз|газел|ман|реф)\b", text_lower)
    pat_multi2 = re.search(r"\b(?:fura|tent|mashina|isuzu|labo|kamaz|gazel|man|ref|фура|тент|машина|исузу|лабо|камаз|газел|ман|реф)\s*(?:tent|тент)?\s*([5-9]|\d{2,})\s*(?:ta|dona|та|дона)\b", text_lower)
    if pat_multi1 or pat_multi2:
        return False, "Ko'p mashina so'ralgan (5+ ta mashina — dispetcher shabloni)", {}

    # 5. Havolalar va reklamalar (@username, t.me/, havolalar)
    if LINK_PATTERN.search(text):
        return False, "Xabarda havola yoki @username mavjud", {}

    # 6. Dispetcher STOP-SO'ZLARI (keshbek, otkat, mashina bor, chetlatilgan mezonlar, texnik so'zlar)
    # Haqiqiy 1-qo'l yukchilar "dispetcher kerakmas" yoki "диспечер керакмас" deb yozsa, chetlatilmaydi:
    text_disp_check = re.sub(
        r"(?i)\b(?:dispetcher|dispecher|диспечер|диспетчер|диспечир|диспичир|оператор|operator)\s*(?:kerakmas|keremas|keregimas|kerak\s*emas|bezovta\s*qilmasin|tel\s*qilmasin|telefon\s*qilmang|керакмас|керемас|керак\s*эмас|безовта\s*қилмасин|безовта\s*килмасин|тел\s*қилманг|тел\s*килманг)\b",
        " ",
        text_lower
    )
    for stop_word in DISPATCHER_STOP_WORDS:
        if stop_word in text_disp_check:
            return False, f"Dispetcher stop-so'zi aniqlandi: '{stop_word}'", {}

    # 7. Profil tekshiruvi (faqat erkaklar, ayol profillar darhol chetlatiladi)
    profile_ok, profile_reason = check_sender_profile(first_name, last_name, username)
    if not profile_ok:
        return False, f"Profil filtri: {profile_reason}", {}

    # 7.1. Matn ichidagi ayollik belgilari va familiyalar tekshiruvi
    female_text_ok, female_text_reason = check_female_text_indicators(text)
    if not female_text_ok:
        return False, f"Matn filtri: {female_text_reason}", {}

    # 8. Yo'nalish tekshiruvi: [Qayerdan] [Qayerga]
    destinations = extract_destinations(text_lower)
    if not destinations:
        return False, "Yo'nalish (shahar/viloyat) aniqlanmadi", {}

    # Davlat va uning shahri birga kelsa, aniq shaharni qoldirib davlatni qisqartirish
    destinations = normalize_destinations(destinations)

    # Bitta xabarda 3 tadan ortiq har xil viloyat bo'lsa - dispetcher
    if len(destinations) > 2:
        return False, "Ko'p yo'nalishlar so'ralgan (dispetcherlik belgisi)", {}

    # Yo'nalish ko'rsatkichi (-ga, -dan yoki 2 ta shahar) bo'lishi shart
    if not has_direction_indicator(text_lower, destinations):
        return False, "Yo'nalish aniq ko'rsatilmagan (yo'nalish qo'shimchasi yo'q)", {}

    # 9. Mashina so'rovi (fura kerak...) YOKI "Yuk bor" YOKI batafsil yuk/tovar ko'rsatilgan e'lonlar
    has_truck = any(t in text_lower for t in TRUCK_TYPES)
    has_need = any(n in text_lower for n in NEED_WORDS)
    has_cargo_available = any(c in text_lower for c in CARGO_AVAILABLE_KEYWORDS)
    has_cargo_goods = any(g in text_lower for g in CARGO_GOODS_KEYWORDS)

    # Ertaga, ertalabga yuk e'lonlari
    timing_keywords = [
        "ertaga", "эртага", "ertalab", "эрталаб", "ertalabga", "эрталабга",
        "ertaman", "эртаман", "ertamanga", "эртаманга", "abedga", "обедга", "tushga", "тушга"
    ]
    has_timing = any(tm in text_lower for tm in timing_keywords)
    has_cargo_word = any(cw in text_lower for cw in ["yuk", "юк", "gruz", "груз", "tonna", "тонна", "тн", "куб", "kub"])
    has_timing_cargo = has_timing and (has_cargo_word or has_need or has_truck or has_cargo_goods)

    # Yuk yoki tovar turi batafsil yozilgan bo'lsa (dehqon, zavod yoki ombor yuklari)
    has_goods_with_need = has_cargo_goods and (has_need or has_truck or "bor" in text_lower or "бор" in text_lower)

    # Aniq yo'nalish va mashina turi bo'lsa (masalan "Asakadan Shahrixonga tent kamaz 941234567")
    has_truck_with_route = has_truck and len(destinations) >= 2

    # O'lchov birligi bilan yuk borligi (masalan: 150kg bor, 2 tonna bor, 50 qop bor, 25t bor)
    has_weight_quantity = bool(re.search(r"\b\d+\s*(?:kg|кг|кило|kilo|tonna|тонна|тн|tn|t|т|tona|тона|qop|қоп|dona|дона|kub|куб|metr|метр)\b.*?\b(?:bor|бор|yuk|юк)\b", text_lower))

    # Tovar va tonnaj bo'lsa va yo'nalish bo'lsa (masalan "Шеработдан Андижон баликчга туз 25т 995260708")
    has_tonnage = bool(re.search(r"\b\d+(?:[.,]\d+)?\s*(?:t|т|tn|тн|tonna|тонна|tona|тона|kg|кг|kub|куб|qop|қоп|metr|метр)\b", text_lower))
    has_goods_with_tonnage = has_cargo_goods and has_tonnage and len(destinations) >= 1

    # Mashina turi yozilmasa ham qayerdan-qayerga ekani va necha tonnaligi yozilgan bo'lsa (masalan "Toshkent Qarshi 7t 931350625")
    has_route_with_tonnage = len(destinations) >= 1 and has_tonnage and (len(destinations) >= 2 or has_direction_indicator(text_lower, destinations))

    # Bo'sh mashina / mashina bor e'lonlari (Foydalanuvchi talabi: chakman, tent, fura, isuzu bo'sh mashina e'lonlari)
    TRUCK_AVAILABLE_KEYWORDS = [
        "mashina bor", "moshina bor", "машина бор", "мошина бор",
        "fura bor", "фура бор", "isuzu bor", "isuzi bor", "исузу бор", "исузи бор",
        "labo bor", "лабо бор", "chakman bor", "чакман бор", "shacman bor", "шакман бор",
        "tent bor", "тент бор", "kamaz bor", "камаз бор", "gazel bor", "газел бор",
        "bo'sh", "бош", "бўш", "bo'sh mashina", "бош машина", "бўш машина",
        "bo'sh fura", "бош фура", "бўш фура", "bo'sh isuzu", "бош исузу",
        "bo'shab qoldi", "бошаб қолди", "bo'shmiz", "бошмиз", "bo'shmiza",
        "yuk kerak", "юк керак", "yuk kere", "юк кере", "yuk kerey", "yuk kerek",
        "ref bor", "реф бор", "zil bor", "зил бор", "mashinamiz bor", "машинамиз бор",
        "mashinalar bor", "машиналар бор"
    ]
    has_truck_available = any(ta in text_lower for ta in TRUCK_AVAILABLE_KEYWORDS) or (has_truck and any(b in text_lower for b in ["bor", "бор", "bo'sh", "бош", "бўш"]))

    if not ((has_truck and has_need) or has_cargo_available or has_timing_cargo or has_goods_with_need or has_truck_with_route or has_weight_quantity or has_goods_with_tonnage or has_route_with_tonnage or has_truck_available):
        return False, "Mashina/yuk so'rovi yoki e'loni aniqlanmadi", {}

    # 10. Telefon raqam mavjudligi
    phone = extract_phone(text)
    if not phone:
        return False, "Telefon raqami topilmadi", {}

    # 11. O'zbekistonga aloqadorlik (O'zbekiston ichki yuki YOKI chet eldan UZBga / UZBdan chet elga)
    if not is_relevant_to_uzbekistan(destinations, phone):
        return False, "E'lon O'zbekistonga aloqador emas (ichki xorijiy yuk)", {}

    is_truck_offer = bool(has_truck_available and not has_need and not has_cargo_available and not has_tonnage)
    details = extract_cargo_details(text)
    cleaned_data = {
        "original_text": text.strip(),
        "destinations": destinations,
        "phone": phone,
        "sender_name": f"{first_name or ''} {last_name or ''}".strip(),
        "is_truck_offer": is_truck_offer,
        "details": details
    }

    return True, "Haqiqiy zakazchi/haydovchi xabari", cleaned_data


def analyze_reported_cargo_ad(
    text: str,
    phone: Optional[str] = None,
    sender_id: Optional[str] = None,
    destinations_text: Optional[str] = None,
    phone_history: Optional[List[Dict[str, Any]]] = None,
    is_blocked: bool = False
) -> Dict[str, Any]:
    """
    Guruhdagi 'Dispetcher emas' / 'Dispetcher' tugmasi bosilganda e'lonni
    chuqur tahlil qilib, uning haqiqiy Zakazchi (Yuk egasi) yoki Dispetcher
    ekanligini aniq dalillar va mezonlar bilan solishtirib xulosa beradi.
    """
    disp_reasons = []
    shipper_reasons = []
    disp_score = 0
    shipper_score = 0

    text_lower = text.lower() if text else ""

    # 1. Baza tarixi va blokirovka
    if is_blocked:
        disp_reasons.append("Ushbu telefon yoki jo'natuvchi bazada qora ro'yxatga kiritilgan")
        disp_score += 100

    if phone_history and len(phone_history) >= 2:
        distinct_dest = len(set(h.get("destinations", "") for h in phone_history))
        if distinct_dest >= 2:
            disp_reasons.append(f"Ushbu raqamdan bir kunda {distinct_dest} ta har xil viloyatga e'lon berilgan (dispetcherlik)")
            disp_score += 50
        else:
            disp_reasons.append(f"Ushbu raqamdan bir kunda {len(phone_history)} ta takroriy e'lon o'tgan")
            disp_score += 25
    elif not phone_history or len(phone_history) <= 1:
        shipper_reasons.append("Raqamdan birinchi marta yakka yuk e'loni berilmoqda (boshqa viloyatlarga tarqalmagan)")
        shipper_score += 25

    # 2. Qat'iy stop-so'zlar (keshbek, otkat, linklar)
    for sw in ["keshbek", "keshbek bor", "otkat", "otkad", "foiz", "bonus"]:
        if sw in text_lower:
            disp_reasons.append(f"Keshbek/otkat so'zi aniqlandi: '{sw}'")
            disp_score += 100

    if LINK_PATTERN.search(text):
        disp_reasons.append("Reklama havolasi, kanal yoki @username mavjud")
        disp_score += 100

    # 3. Dispetcherlik texnik iboralari
    tech_dispatcher_words = [
        "догруз", "dogruz", "попутка", "poputka", "сборный", "паллет", "санпаспорт",
        "боковая", "верхняя", "чистый тент", "договорная", "har kuni", "har doim",
        "doimiy", "reyes", "krug", "reys", "zapros", "firma", "yuridik",
        "perechislenie", "nds", "dogovor", "beznal", "dispetcher", "baza",
        "logistika", "mashina bor", "moshina bor", "fura bor", "isuzu bor", "labo bor",
        "shafyorlar aloqaga", "shofirlar aloqaga", "haydovchilar aloqaga", "aloqaga chiqing", "aloqaga", "алокага", "алоқага"
    ]
    found_tech = [w for w in tech_dispatcher_words if w in text_lower]
    if found_tech:
        disp_reasons.append(f"Dispetcherlik texnik terminlari: {', '.join(found_tech[:3])}")
        disp_score += (30 * len(found_tech))

    # 4. Matn hajmi va uzunligi
    char_len = len(text.strip())
    if char_len <= 110:
        shipper_reasons.append(f"Matn juda ixcham va lo'nda ({char_len} belgi)")
        shipper_score += 25
    elif char_len <= 180:
        shipper_reasons.append(f"Matn me'yoriy uzunlikda ({char_len} belgi)")
        shipper_score += 15
    elif char_len > 220:
        disp_reasons.append(f"Matn uzunligi ortiqcha ({char_len} belgi — 220 belgidan oshmasligi shart)")
        disp_score += 35

    # 5. Qatorlar soni
    lines = [l.strip() for l in text.splitlines() if l.strip()]
    if len(lines) <= 3:
        shipper_reasons.append(f"Qatorlar soni me'yorda ({len(lines)} qator)")
        shipper_score += 20
    elif len(lines) > 4:
        disp_reasons.append(f"Matn ko'p qatorli shablon shaklida ({len(lines)} qator)")
        disp_score += 30

    # 6. Sun'iy probellar va bo'sh qatorlar (bannerlar)
    raw_lines_all = text.strip().splitlines()
    empty_lines_cnt = sum(1 for l in raw_lines_all if not l.strip())
    if empty_lines_cnt >= 3 or (empty_lines_cnt >= 2 and len(raw_lines_all) >= (len(lines) * 1.5)) or re.search(r" {5,}", text) or re.search(r"\n\s*\n\s*\n", text):
        disp_reasons.append(f"E'londa banner ko'rinishidagi sun'iy bo'shliqlar yoki orasi ochiq qatorlar bor ({empty_lines_cnt} ta bo'sh qator)")
        disp_score += 45

    # 7. Emojilar
    emojis = EMOJI_PATTERN.findall(text)
    if len(emojis) == 0:
        shipper_reasons.append("Ortiqcha bezak va emojilarsiz, tabiiy matn")
        shipper_score += 15
    elif len(emojis) > 3:
        disp_reasons.append(f"Ko'p emojilar bilan bezatilgan shablon ({len(emojis)} ta)")
        disp_score += 30

    # 8. Telefon raqamlari soni
    all_raw_phones = PHONE_PATTERN.findall(text)
    if len(all_raw_phones) > 1:
        unique_phones = set(re.sub(r"\D", "", p)[-9:] for p in all_raw_phones if len(re.sub(r"\D", "", p)) >= 9)
        if len(unique_phones) > 1:
            disp_reasons.append(f"Bir nechta har xil telefon raqamlari bor ({len(unique_phones)} ta — ofis/dispetcher)")
            disp_score += 50
        else:
            shipper_reasons.append("Yagona aloqa raqami")
            shipper_score += 15
    else:
        shipper_reasons.append("Yagona aloqa raqami")
        shipper_score += 15

    # 9. Yo'nalishlar
    dests = extract_destinations(text_lower)
    if len(dests) > 2:
        disp_reasons.append(f"Bir vaqtning o'zida ko'p viloyatga e'lon berilgan ({len(dests)} ta)")
        disp_score += 45
    elif len(dests) in (1, 2):
        shipper_reasons.append("Bitta aniq yo'nalish ko'rsatilgan")
        shipper_score += 20

    # 10. To'g'ridan-to'g'ri yuk/mashina so'rovi
    has_truck = any(t in text_lower for t in TRUCK_TYPES)
    has_need = any(n in text_lower for n in NEED_WORDS)
    has_cargo = any(c in text_lower for c in CARGO_AVAILABLE_KEYWORDS)
    if (has_truck and has_need) or has_cargo:
        shipper_reasons.append("To'g'ridan-to'g'ri mashina yoki yuk so'rovi mavjud")
        shipper_score += 15

    # Xulosa chiqarish
    # Dispetcher deb topish shartlari:
    # 1) disp_score >= 35
    # 2) disp_reasons kamida 2 ta bo'lsa
    # 3) yoki qat'iy sabab (keshbek, link, bloklangan) bo'lsa
    # 4) yoki disp_score > shipper_score
    is_dispatcher = (disp_score >= 35 or len(disp_reasons) >= 2 or disp_score > shipper_score)

    if is_dispatcher:
        verdict = "DISPETCHER"
        verdict_text = "⛔️ DISPETCHER (Vositachi)"
    else:
        verdict = "HAQIQIY_YUKCHI"
        verdict_text = "✅ HAQIQIY YUKCHI (Birinchi qo'l)"

    return {
        "is_dispatcher": is_dispatcher,
        "verdict": verdict,
        "verdict_text": verdict_text,
        "disp_score": disp_score,
        "shipper_score": shipper_score,
        "disp_reasons": disp_reasons,
        "shipper_reasons": shipper_reasons,
        "char_len": char_len,
        "line_count": len(lines)
    }

