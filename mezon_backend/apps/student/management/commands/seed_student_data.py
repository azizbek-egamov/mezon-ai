from django.core.management.base import BaseCommand
from apps.student.models import StudentCaseBank, StudentQuizQuestion, StudentLegalGlossary, LawCategory, DifficultyLevel


class Command(BaseCommand):
    help = "Talabalar ekotizimi uchun kazuslar, test savollari va yuridik glossariyni yuklaydi."

    def handle(self, *args, **options):
        self.stdout.write("Kazuslar, test savollari va glossariyni yuklash boshlandi...")

        # 1. Kazuslar banki
        cases_data = [
            {
                "title": "Avtotransport vositasini ijaraga berish va garov nizosi",
                "category": LawCategory.CIVIL,
                "difficulty": DifficultyLevel.MEDIUM,
                "facts": (
                    "Fuqaro Aliyev oʻziga tegishli Nexia-3 avtomashinasini fuqaro Karimovga 6 oy muddatga ogʻzaki kelishuv "
                    "asosida ijaraga berdi. Karimov 2 oy ijara haqini toʻlagach, moliyaviy qiyinchilikka uchrab, "
                    "avtomashinani fuqaro Sobirovdan 50 million soʻm qarz evaziga garovga qoʻydi va tilxat yozib berdi. "
                    "Keyinchalik Aliyev avtomashinasini qaytarib berishni talab qilganida, Sobirov garov summasi "
                    "qaytarilmaguncha mashinani bermasligini, oʻzi insofli egallovchi ekanligini bildirdi."
                ),
                "task_question": (
                    "1. Aliyev va Karimov oʻrtasidagi ijara shartnomasi qonuniy kuchga egami?\n"
                    "2. Karimovning avtomashinani garovga qoʻyish huquqi bormi edi?\n"
                    "3. Sobirov insofli egallovchi deb hisoblanadimi va Aliyev oʻz mulkini qanday huquqiy yoʻl bilan qaytarib olishi mumkin?"
                ),
                "relevant_laws": [
                    {"law": "FK", "article": 539, "title": "Ijara shartnomasining shakli"},
                    {"law": "FK", "article": 264, "title": "Garovga qoʻyuvchi"},
                    {"law": "FK", "article": 228, "title": "Mulkdorning mol-mulkini boshqa shaxsning noqonuniy egaligidan talab qilib olishi (vindikatsiya)"},
                ],
                "reference_solution": {
                    "issue": "Ogʻzaki ijara shartnomasining haqiqiyligi, begona mulkni garovga qoʻyish oqibatlari va mol-mulkni noqonuniy egalikdan talab qilib olish (vindikatsiya).",
                    "rule": "FK 539-moddasi (avtotransport ijarasi notarial tasdiqlanishi shart), FK 264-moddasi (faqat mulkdor yoki uning vakili garovga qoʻyishi mumkin), FK 228-moddasi (vindikatsiya).",
                    "analysis": "1) Avtotransport vositasi ijarasi notarial tasdiqlanishi va roʻyxatdan oʻtkazilishi shart, aks holda bitim haqiqiy emas (FK 115-m). 2) Karimov mulkdor emas, uning garovga qoʻyishi oʻz-oʻzidan haqiqiy emas. 3) Sobirov mulkdor boʻlmagan shaxsdan garovga olganligi sababli garov huquqi vujudga kelmaydi. Aliyev FK 228-moddasiga asosan avtomashinani har qanday noqonuniy egalikdan talab qilib olishga haqli.",
                    "conclusion": "Aliyev sudga Sobirovga nisbatan avtomashinani oʻzining noqonuniy egaligidan olib berish (vindikatsion daʼvo) toʻgʻrisida daʼvo arizasi kiritishi lozim. Sud daʼvoni toʻliq qanoatlantirishi kerak. Sobirov esa Karimovdan qarz summasini undirishi mumkin."
                }
            },
            {
                "title": "Sinov muddati davrida homilador ayol bilan mehnat shartnomasini bekor qilish",
                "category": LawCategory.LABOR,
                "difficulty": DifficultyLevel.MEDIUM,
                "facts": (
                    "Fuqaro Karimova MChJ ga buxgalter lavozimiga 3 oylik dastlabki sinov muddati bilan ishga qabul qilindi. "
                    "2 oy oʻtgach, ish beruvchi uning hisobotlarida xatoliklar borligini vaj qilib, sinovdan oʻta olmadi deb buyruq chiqardi. "
                    "Karimova esa buyruq chiqishidan 3 kun oldin 8 haftalik homiladorligi toʻgʻrisidagi tibbiy maʼlumotnomani taqdim etgan edi. "
                    "Ish beruvchi: 'Sinov muddati davrida har qanday xodim bilan shartnomani bekor qilish huquqim bor' deb javob berdi."
                ),
                "task_question": (
                    "1. Homilador ayollarga ishga qabul qilishda dastlabki sinov belgilanadimi?\n"
                    "2. Ish beruvchining sinov natijasi qoniqarsizligi vaji bilan shartnomani bekor qilishi qonuniymi?\n"
                    "3. Karimova qanday talablar bilan sudga murojaat qilishi mumkin?"
                ),
                "relevant_laws": [
                    {"law": "MK", "article": 129, "title": "Dastlabki sinov belgilanmaydigan shaxslar"},
                    {"law": "MK", "article": 408, "title": "Homilador ayollar bilan mehnat shartnomasini bekor qilishdagi kafolatlar"},
                ],
                "reference_solution": {
                    "issue": "Homilador ayollarga nisbatan dastlabki sinov belgilanishining qonuniyligi va homiladorlik davrida mehnat shartnomasini ish beruvchi tashabbusi bilan bekor qilish taqiqi.",
                    "rule": "Yangi Mehnat kodeksining 129-moddasi va 408-moddasi.",
                    "analysis": "1) MK 129-moddasiga binoan, homilador ayollarga ishga qabul qilish chogʻida dastlabki sinov belgilanishi qatʼiyan man etiladi. Agar mehnat shartnomasida bunday shart kiritilgan boʻlsa ham, u yuridik kuchga ega emas. 2) MK 408-moddasiga muvofiq, homilador ayollar bilan mehnat shartnomasini ish beruvchining tashabbusi bilan bekor qilishga faqat tashkilot tugatilgan hollardagina yoʻl qoʻyiladi. Sinov natijasi qoniqarsizligi vaji bilan boʻshatish noqonuniydir.",
                    "conclusion": "Ish beruvchining buyrugʻi noqonuniy. Karimova sudga ishga tiklash, majburiy progul vaqti uchun ish haqi va maʼnaviy zarar undirish toʻgʻrisida daʼvo arizasi kiritishi lozim. Sud daʼvoni qanoatlantirib, Karimovaning ishga tiklanishini taʼminlaydi."
                }
            },
            {
                "title": "Oʻzganing mulkini aldash yoʻli bilan egallash (Firibgarlik va fuqarolik-huquqiy munosabatlar chegarasi)",
                "category": LawCategory.CRIMINAL,
                "difficulty": DifficultyLevel.HARD,
                "facts": (
                    "Fuqaro Toirov qurilish materiallari savdosi bilan shugʻullanuvchi tadbirkor Rahimovga oʻzini yirik pudratchi "
                    "deb tanishtirib, soxta muhr va rekvizitlar bosilgan shartnoma asosida 120 million soʻmlik sement mahsulotini "
                    "30 kun ichida toʻlash sharti bilan qabul qilib oldi. Toirov mahsulotni oʻsha kuniyoq bozor narxidan ancha arzon "
                    "narxda naqd pulga sotib yubordi va pullarni shaxsiy ehtiyojlariga sarfladi. Toʻlov muddati kelganida u telefonlarini "
                    "oʻchirib, yashirinib yurdi. Tergovda Toirov: 'Bu oddiy fuqarolik-huquqiy nizo, men toʻlovni keyinroq bermoqchi edim' deb koʻrsatma berdi."
                ),
                "task_question": (
                    "1. Toirovning harakatlarida jinoyat tarkibi mavjudmi yoki fuqarolik-huquqiy javobgarlik kelib chiqadimi?\n"
                    "2. Firibgarlik (JK 168-modda) va majburiyatni bajarmaslik oʻrtasidagi chegaralash mezonlari qanday?\n"
                    "3. Toirovning harakatlarini JKning qaysi moddasi bilan malakalash kerak?"
                ),
                "relevant_laws": [
                    {"law": "JK", "article": 168, "title": "Firibgarlik"},
                    {"law": "Oliy Sud Plenumi Qarori", "article": 17, "title": "Firibgarlik ishlari boʻyicha sud amaliyoti toʻgʻrisida"},
                ],
                "reference_solution": {
                    "issue": "Firibgarlik jinoyati tarkibi bilan fuqarolik-huquqiy shartnoma majburiyatlarini bajarmaslik holatining chegaralanishi (subʼyektiv tomon, qasdning paydo boʻlish vaqti).",
                    "rule": "Oʻzbekiston Respublikasi JK 168-moddasi, Oliy sud Plenumi Qarorlari.",
                    "analysis": "Toirovda aldash va mulkni qaytarmaslik qasdi shartnoma tuzilishidan oldin paydo boʻlgan (soxta hujjatlar ishlatilgan, mahsulot zudlik bilan arzon narxda sotilib, yashiringan). Bu holat uning majburiyatni bajarish niyati umuman boʻlmaganidan dalolat beradi. Mazkur harakatlar fuqarolik munosabati emas, balki JK 168-moddasi boʻyicha qasddan sodir etilgan firibgarlik jinoyatidir.",
                    "conclusion": "Toirovning harakatlari OʻzR JK 168-moddasi tegishli qismi (yirik miqdorda firibgarlik) bilan toʻgʻri malakalanishi lozim. Yetkazilgan 120 mln soʻm moddiy zarar jinoyat ishi doirasida fuqaroviy daʼvo orqali undiriladi."
                }
            },
            {
                "title": "Maʼmuriy organ qarori ustidan sudga shikoyat qilish muddati",
                "category": LawCategory.ADMINISTRATIVE,
                "difficulty": DifficultyLevel.EASY,
                "facts": (
                    "Tuman hokimining 2024-yil 10-yanvardagi qarori bilan fuqaro Yusupovga tegishli savdo doʻkoni joylashgan yer uchastkasini "
                    "davlat va jamoat ehtiyojlari uchun olib qoʻyish belgilandi. Qaror Yusupovga 2024-yil 1-fevralda topshirildi. "
                    "Yusupov kompensatsiya masalasida hokimlik bilan 2 oy muzokara olib bordi, biroq kelisha olmadi. "
                    "2024-yil 15-aprelda Yusupov Maʼmuriy sudga hokim qarorini haqiqiy emas deb topish haqida ariza berdi. "
                    "Hokimlik vakili sudda Yusupov 1 oylik murojaat muddatini oʻtkazib yuborganligini aytib, arizani koʻrmasdan qoldirishni soʻradi."
                ),
                "task_question": (
                    "1. Maʼmuriy sud ishlarini yuritish toʻgʻrisidagi kodeks boʻyicha maʼmuriy organ qarorlari ustidan sudga murojaat qilish muddati qancha?\n"
                    "2. Ushbu muddat qaysi paytdan boshlab hisoblanadi?\n"
                    "3. Sud hokimlik vakilining iltimosnomasini qanoatlantirishi kerakmi?"
                ),
                "relevant_laws": [
                    {"law": "MSIYK", "article": 186, "title": "Sudga murojaat qilish muddati"},
                ],
                "reference_solution": {
                    "issue": "Maʼmuriy organ hujjati ustidan sudga murojaat qilish muddatlari va ularni hisoblash tartibi.",
                    "rule": "MSIYK 186-moddasi.",
                    "analysis": "MSIYK 186-moddasiga koʻra, maʼmuriy organ qarori ustidan sudga ariza (shikoyat) qaror manfaatdor shaxsga maʼlum boʻlgan kundan eʼtiboran uch oy ichida berilishi mumkin (agar boshqa muddat qonunda belgilanmagan boʻlsa). Yusupov qarorni 1-fevralda olgan boʻlsa, 3 oylik muddat 1-maygacha davom etadi. 15-aprelda topshirilgan ariza qonuniy muddat ichida berilgan.",
                    "conclusion": "Hokimlik vakilining vajlari asossiz. Yusupov qonunda belgilangan 3 oylik muddatni buzmagan. Sud ishni mazmunan koʻrib chiqishi shart."
                }
            }
        ]

        for item in cases_data:
            StudentCaseBank.objects.update_or_create(
                title=item["title"],
                defaults=item
            )
        self.stdout.write(self.style.SUCCESS(f"{len(cases_data)} ta kazus muvaffaqiyatli saqlandi."))

        # 2. Test savollari (Quiz)
        quiz_data = [
            {
                "category": LawCategory.CIVIL,
                "question_text": "Fuqarolik huquqida umumiy daʼvo muddati necha yil qilib belgilangan?",
                "options": [
                    {"key": "A", "text": "1 yil"},
                    {"key": "B", "text": "3 yil"},
                    {"key": "C", "text": "5 yil"},
                    {"key": "D", "text": "10 yil"}
                ],
                "correct_option": "B",
                "explanation": "Oʻzbekiston Respublikasi Fuqarolik kodeksining 150-moddasiga koʻra, umumiy daʼvo muddati uch yil qilib belgilanadi.",
                "law_reference": "FK 150-modda"
            },
            {
                "category": LawCategory.CIVIL,
                "question_text": "Koʻchmas mulkni hadya qilish shartnomasi qanday shaklda tuzilishi shart?",
                "options": [
                    {"key": "A", "text": "Oddiy yozma shaklda"},
                    {"key": "B", "text": "Ogʻzaki shaklda"},
                    {"key": "C", "text": "Notarial tasdiqlangan va davlat roʻyxatidan oʻtkazilgan shaklda"},
                    {"key": "D", "text": "Faqat mahallaning tasdigʻi bilan"}
                ],
                "correct_option": "C",
                "explanation": "FK 504-moddasiga binoan, koʻchmas mulkni hadya qilish shartnomasi notarial tasdiqlanishi va davlat roʻyxatidan oʻtkazilishi lozim.",
                "law_reference": "FK 504-modda"
            },
            {
                "category": LawCategory.LABOR,
                "question_text": "Yangi Mehnat kodeksiga koʻra, xodimlar uchun yillik asosiy eng kam mehnat taʼtili davomiyligi necha kalendar kunni tashkil etadi?",
                "options": [
                    {"key": "A", "text": "15 ish kuni"},
                    {"key": "B", "text": "21 kalendar kun"},
                    {"key": "C", "text": "24 ish kuni"},
                    {"key": "D", "text": "30 kalendar kun"}
                ],
                "correct_option": "B",
                "explanation": "Yangi Mehnat kodeksining 217-moddasiga muvofiq, yillik asosiy eng kam mehnat taʼtili davomiyligi yigirma bir kalendar kunni tashkil etadi.",
                "law_reference": "MK 217-modda"
            },
            {
                "category": LawCategory.CRIMINAL,
                "question_text": "Jinoyat qonunchiligida qilmishning jinoiyligini istisno qiluvchi qanday holatlar mavjud?",
                "options": [
                    {"key": "A", "text": "Faqat zaruriy mudofaa va oxirgi zarurat"},
                    {"key": "B", "text": "Zaruriy mudofaa, oxirgi zarurat, buyruqni bajarish, asosli tavakkalchilik va h.k."},
                    {"key": "C", "text": "Mastlik holati va ehtiyotsizlik"},
                    {"key": "D", "text": "Jabrlanuvchining xohishi boʻlmasa jinoyat hisoblanmaydi"}
                ],
                "correct_option": "B",
                "explanation": "JKning 37-41-moddalari qilmishning jinoiyligini istisno qiluvchi holatlarni (zaruriy mudofaa, oxirgi zarurat, ijtimoiy xavfli qilmish sodir etgan shaxsni ushlash va h.k.) belgilaydi.",
                "law_reference": "JK 37-modda"
            },
            {
                "category": LawCategory.ADMINISTRATIVE,
                "question_text": "Maʼmuriy sud ishlarini yuritish toʻgʻrisidagi kodeks boʻyicha kassatsiya shikoyati qaysi muddatda beriladi?",
                "options": [
                    {"key": "A", "text": "Apellatsiya instansiyasi qarori chiqqan kundan eʼtiboran olti oy ichida"},
                    {"key": "B", "text": "Bir oy ichida"},
                    {"key": "C", "text": "Uch oy ichida"},
                    {"key": "D", "text": "Bir yil ichida"}
                ],
                "correct_option": "A",
                "explanation": "MSIYK 228-moddasiga asosan, kassatsiya shikoyati apellatsiya instansiyasi sudining qarori qabul qilingan kundan eʼtiboran olti oy ichida berilishi mumkin.",
                "law_reference": "MSIYK 228-modda"
            }
        ]

        for q in quiz_data:
            StudentQuizQuestion.objects.update_or_create(
                question_text=q["question_text"],
                defaults=q
            )
        self.stdout.write(self.style.SUCCESS(f"{len(quiz_data)} ta test savoli muvaffaqiyatli saqlandi."))

        # 3. Yuridik Glossariy va Lotincha Aforizmlar (ZERO API COST)
        glossary_data = [
            {
                "term": "Pacta sunt servanda",
                "latin_term": "Pacta sunt servanda",
                "category": LawCategory.CIVIL,
                "is_roman_latin": True,
                "definition": "Shartnomalar bajarilishi shart. Fuqarolik va xalqaro ommaviy huquqning fundamental prinsipi boʻlib, taraflar oʻz zimmasiga olgan majburiyatlarni vijdonan bajarishi shartligini anglatadi.",
                "legal_source": "Rim xususiy huquqi; FK 236-moddasi (Majburiyatlarni lozim darajada bajarish)",
                "example_usage": "Ikkala tomon ham 'pacta sunt servanda' qoidasiga binoan oʻz majburiyatlarini toʻliq ijro etishlari lozim."
            },
            {
                "term": "Nullum crimen, nulla poena sine lege",
                "latin_term": "Nullum crimen, nulla poena sine lege",
                "category": LawCategory.CRIMINAL,
                "is_roman_latin": True,
                "definition": "Qonunda koʻrsatilmagan boʻlsa, jinoyat ham yoʻq, jazo ham yoʻq. Jinoyat huquqining qonuniylik prinsipini ifodalovchi asosiy qoida.",
                "legal_source": "Rim huquqi; OʻzR Konstitutsiyasi 28-modda, OʻzR JK 4-modda (Qonuniylik prinsipi)",
                "example_usage": "Shaxsni qilmish sodir etilgan vaqtda qonunda nazarda tutilmagan harakat uchun jinoiy javobgarlikka tortib boʻlmaydi."
            },
            {
                "term": "Audiatur et altera pars",
                "latin_term": "Audiatur et altera pars",
                "category": LawCategory.CIVIL,
                "is_roman_latin": True,
                "definition": "Ikkinchi taraf ham tinglansin. Sud jarayonida taraflarning tengligi, tortishuvchanlik va har ikkala tomonning oʻz dalillarini keltirish huquqini taʼminlovchi protsessual qoida.",
                "legal_source": "Rim protsessi; FPK 9-modda (Sud protsessida taraflarning tortishuvchanligi va teng huquqliligi)",
                "example_usage": "Sudya qaror chiqarishdan oldin har ikki tomonning dalillarini teng eshitishi shart."
            },
            {
                "term": "In dubio pro reo",
                "latin_term": "In dubio pro reo",
                "category": LawCategory.CRIMINAL,
                "is_roman_latin": True,
                "definition": "Shubha ayblanuvchi (sudlanuvchi) foydasiga talqin qilinadi. Aybsizlik prezumpsiyasining ajralmas tarkibiy qismi.",
                "legal_source": "Konstitutsiya 28-modda; JPK 23-modda (Aybsizlik prezumpsiyasi)",
                "example_usage": "Tergovda bartaraf etib boʻlmaydigan har qanday shubha ayblanuvchining foydasiga hal qilinishi lozim."
            },
            {
                "term": "Bona fides",
                "latin_term": "Bona fides",
                "category": LawCategory.CIVIL,
                "is_roman_latin": True,
                "definition": "Insofli egalik, vijdonlilik, halollik. Fuqarolik-huquqiy munosabatlarda subʼyektlarning oʻz huquq va majburiyatlarini suiisteʼmol qilmasdan amalga oshirishi.",
                "legal_source": "Rim huquqi; FK 9-modda (Fuqarolik huquqlarini amalga oshirish va majburiyatlarni bajarish chegaralari), FK 229-m",
                "example_usage": "Mulkni haq evaziga olgan shaxs uning begonalashtirish huquqiga ega boʻlmagan shaxsga tegishli ekanligini bilmagan va bilishi mumkin boʻlmagan boʻlsa, insofli egallovchi hisoblanadi."
            },
            {
                "term": "Dura lex, sed lex",
                "latin_term": "Dura lex, sed lex",
                "category": LawCategory.CONSTITUTIONAL,
                "is_roman_latin": True,
                "definition": "Qonun qattiqqoʻl, biroq u qonundir. Qonunning ustuvorligi va qatʼiyligi uning barcha uchun istisnosiz majburiyligini bildiradi.",
                "legal_source": "Rim falsafasi va qonunchiligi; Konstitutsiya 15-modda (Konstitutsiya va qonunlarning ustunligi)",
                "example_usage": "Qonun talablari qanchalik qatʼiy boʻlmasin, barcha mansabdor shaxslar unga boʻysunishi shart."
            },
            {
                "term": "Res judicata",
                "latin_term": "Res judicata",
                "category": LawCategory.CIVIL,
                "is_roman_latin": True,
                "definition": "Hal qilingan ish. Qonuniy kuchga kirgan sud qarori boʻyicha ayni bir xil taraflar, ayni bir predmet va asoslar boʻyicha qayta sudga murojaat qilish mumkin emasligini ifodalaydi.",
                "legal_source": "FPK 194-modda (Ish yuritishni tugatish asoslari)",
                "example_usage": "Ayni shu nizo yuzasidan sudning qonuniy kuchga kirgan hal qiluv qarori mavjudligi sababli daʼvo arizasi koʻrib chiqilmaydi."
            },
            {
                "term": "Vindikatsiya",
                "latin_term": "Rei vindicatio",
                "category": LawCategory.CIVIL,
                "is_roman_latin": True,
                "definition": "Mulkdorning oʻz mol-mulkini boshqa shaxsning qonunsiz egaligidan talab qilib olishi haqidagi ashyoviy daʼvosi.",
                "legal_source": "FK 228-moddasi (Mulkdorning mol-mulkini boshqa shaxsning qonunsiz egaligidan talab qilib olishi)",
                "example_usage": "Aliyev noqonuniy sotib yuborilgan mashinasini qaytarish uchun vindikatsion daʼvo bilan sudga murojaat qildi."
            },
            {
                "term": "Negator daʼvo",
                "latin_term": "Actio negatoria",
                "category": LawCategory.CIVIL,
                "is_roman_latin": True,
                "definition": "Mulkdorning oʻz huquqlari egalik qilishdan mahrum etish bilan bogʻliq boʻlmagan har qanday buzilishlarini bartaraf etishni talab qilish haqidagi daʼvosi.",
                "legal_source": "FK 231-moddasi (Mulkdorning egalik qilishdan mahrum boʻlmagan huquqlari buzilishini bartaraf etishni talab qilishi)",
                "example_usage": "Qoʻshnisining noqonuniy devor qurib quyosh nurini toʻsib qoʻyishi oqibatida qoʻzgʻatilgan daʼvo negator daʼvodir."
            },
            {
                "term": "Restitutsiya",
                "latin_term": "Restitutio in integrum",
                "category": LawCategory.CIVIL,
                "is_roman_latin": True,
                "definition": "Haqiqiy boʻlmagan bitim oqibatida taraflarni bitim tuzilgunga qadar mavjud boʻlgan dastlabki holatga qaytarish (ikki tomonlama restitutsiya).",
                "legal_source": "FK 114-moddasi (Bitimning haqiqiy emasligi oqibatlari)",
                "example_usage": "Bitim haqiqiy emas deb topilganda, har bir taraf olgan hamma narsani ikkinchi tarafga qaytarib berishi shart."
            }
        ]

        for g in glossary_data:
            StudentLegalGlossary.objects.update_or_create(
                term=g["term"],
                defaults=g
            )
        self.stdout.write(self.style.SUCCESS(f"{len(glossary_data)} ta yuridik atama va lotin iboralari muvaffaqiyatli saqlandi."))

        self.stdout.write(self.style.SUCCESS("Barcha maʼlumotlar toʻliq yuklandi!"))
