"""Ish turlari (12-bosqich): jinoyat, fuqarolik, iqtisodiy, maʼmuriy va "boshqa".

Har bir tur uchun:
  * `scope` — huquqiy asoslashda qidiriladigan lex.uz hujjatlari (`document_ids` YOKI `doc_types`). Boshqa sohaning protsessual
    kodekslari chalg'itadi (jinoyat ishida Maʼmuriy sud kodeksi chiqib qolgan edi) — shuning uchun tur bo'yicha toraytiriladi.
    Ro'yxatdagi barcha id lar bazada tekshirilgan (yadro korpusi, kuchda): `manage.py check_case_scopes`.
  * promptlar: jinoyat ishi uchun yozilgan asl matnlar o'zgarishsiz qoladi; boshqa turlarda ularning ayrim iboralari
    `adapt()` bilan almashtiriladi. Almashtiriladigan iboralar asl matnda borligini test tekshiradi (matn o'zgarsa —
    jimgina buzilmaydi).
"""
from dataclasses import dataclass, field

from django.utils.translation import gettext_lazy as _

# Barcha turlarda: Konstitutsiya va Oliy sud Plenumi qarorlari.
CONSTITUTION = 6445145
FK1, FK2 = 111189, 180552                 # Fuqarolik kodeksi (birinchi / ikkinchi qism)
FPK, IPK, MSIYUK = 3517337, 3523891, 3527353   # protsessual kodekslar
MJTK = 97664                              # Maʼmuriy javobgarlik toʻgʻrisidagi kodeks
JK, JPK, JIK = 111453, 111460, 163629


@dataclass(frozen=True)
class CaseType:
    code: str
    label: object                          # gettext_lazy
    persona: str                           # tahlil promptlaridagi rol
    scope: dict
    label_gen: str = ""                    # "fuqarolik ishidan" (ajratish prompti)
    label_by: str = ""                     # "fuqarolik ishi boʻyicha" (huquqiy so'rov prompti)
    party_role: str = "himoyachi"          # defense_action: kim uchun
    final_doc: str = ""                    # "yakuniy hujjat (masalan, ...)"
    procedural_exclusion: str = ""         # ziddiyat vazifasida alohida tahlil qilinadigan protsessual masalalar
    procedural_actions: str = ""           # ajratish promptidagi protsessual harakatlar ro'yxati
    procedural_task: str = ""              # tahlilning "procedural" vazifasi (Vazifa: procedural_issues — ...)
    codes_hint: str = ""                   # huquqiy so'rov promptida: qaysi hujjatlar
    query_examples: str = ""
    retroactivity: str = ""                # baholash promptining 6-qoidasi
    replacements: list[tuple[str, str]] = field(default_factory=list)


# ---- Jinoyat ishi: mavjud promptlar o'zgarishsiz (apps/cases/analysis.py, extract.py, legal.py dagi asl matn)
CRIMINAL = CaseType(
    code="criminal", label=_("Jinoyat ishi"), persona="jinoyat ishlari boʻyicha tajribali himoyachi-advokat",
    scope={"document_ids": [JPK, JK, CONSTITUTION, JIK], "doc_types": ["PLENUM"]},
)

PROCEDURAL_TAIL = (
    " Hisob-kitobni explanation da koʻrsat. Har bir band kamida bitta fakt id siga tayansin. Koʻrsatuvlar va hujjatlar "
    "orasidagi faktik ziddiyatlarni (vaqt, summa, sana, rang, raqam, hujjatda dalilning notoʻgʻri bayoni) YOZMA — ular "
    "alohida tahlil qilinadi; bu yerda faqat tartib va muddat masalalari. summary — boʻsh satr.")

CIVIL = CaseType(
    code="civil", label=_("Fuqarolik ishi"),
    persona="fuqarolik ishlari (daʼvo, mulk, oila, meros, mehnat nizolari) boʻyicha tajribali advokat-vakil",
    scope={"document_ids": [FK1, FK2, FPK, 104720, 106136, 152653, 6257288, CONSTITUTION, 2055680, 4680944, 4704, 112328,
                            26477], "doc_types": ["PLENUM"]},
    label_gen="fuqarolik ishidan", label_by="fuqarolik ishi boʻyicha", party_role="vakil",
    final_doc="yakuniy hujjat (masalan, sud hal qiruv qarori yoki daʼvo/javob arizasi)",
    procedural_exclusion="muddatlar, xabarnomalar, iltimosnomalar, dalillar taqdim etish tartibi, shikoyat muddatlari",
    procedural_actions="protsessual harakatlar (daʼvo arizasi berilishi, sud majlislari, xabarnomalar, ekspertiza, ajrim va "
                       "qarorlar, shikoyatlar, iltimosnomalar va ularning sanasi/vaqti)",
    procedural_task=("Vazifa: procedural_issues — protsessual muddatlar va tartib buzilishi ehtimoli: daʼvo muddati oʻtganmi "
                     "(va uni uzish yoki tiklash asoslari bormi), daʼvo qoʻyishdan oldingi majburiy tartib (talabnoma) rioya "
                     "qilinganmi, sud majlisi vaqti va joyi haqida taraflarga oʻz vaqtida xabar berilganmi, dalillarni "
                     "taqdim etish va ularga baho berish tartibi, ekspertiza tayinlash, iltimosnomalarning asossiz rad "
                     "etilishi, sud hujjatiga shikoyat (apellyatsiya, kassatsiya) berish va ijro muddatlari." + PROCEDURAL_TAIL),
    codes_hint="Asosan Fuqarolik kodeksi, Fuqarolik protsessual kodeksi, Mehnat va Oila kodekslari, tegishli qonunlar va "
               "Oliy sud Plenumi qarorlari.",
    query_examples='"daʼvo muddati", "shartnomani bekor qilish asoslari", "zararni qoplash", "dalillarga baho berish", '
                   '"sud majlisi haqida xabardor qilish tartibi"',
    retroactivity="Qonunning orqaga qaytish kuchi faqat qonunda alohida koʻrsatilgan hollardagina boʻlishi mumkin — "
                  "voqea sanasidagi tahrirni qoʻlla.",
)

ECONOMIC = CaseType(
    code="economic", label=_("Iqtisodiy ish"),
    persona="iqtisodiy (tadbirkorlik, shartnoma) nizolari boʻyicha tajribali advokat-vakil",
    scope={"document_ids": [FK1, FK2, IPK, 18942, 28144, 8151376, 6518381, 4664142, 85259, 1072079, 4680944, 26477,
                            CONSTITUTION], "doc_types": ["PLENUM"]},
    label_gen="iqtisodiy nizo ishidan", label_by="iqtisodiy nizo ishi boʻyicha", party_role="vakil",
    final_doc="yakuniy hujjat (masalan, iqtisodiy sud qarori yoki daʼvo/javob arizasi)",
    procedural_exclusion="muddatlar, pretenziya tartibi, yurisdiksiya, xabarnomalar, shikoyat muddatlari",
    procedural_actions="protsessual harakatlar (pretenziya yuborilishi, daʼvo arizasi, sud majlislari, xabarnomalar, "
                       "ekspertiza, taʼminot choralari, qarorlar, shikoyatlar va ularning sanasi/vaqti)",
    procedural_task=("Vazifa: procedural_issues — shartnoma va protsessual muddatlar hamda tartib buzilishi ehtimoli: "
                     "majburiyatni bajarish muddati va kechiktirish oqibatlari (penya, jarima, foiz — summalarni qayta "
                     "hisobla), daʼvo muddati, majburiy pretenziya tartibi va muddati, ishning iqtisodiy sud yoki hakamlik "
                     "sudiga tegishliligi (yurisdiksiya), taraflarga xabar berilishi, dalillar va ekspertiza, taʼminot "
                     "choralari, sud hujjatiga shikoyat va ijro muddatlari." + PROCEDURAL_TAIL),
    codes_hint="Asosan Fuqarolik kodeksi, Iqtisodiy protsessual kodeksi, tadbirkorlik va xoʻjalik jamiyatlari boʻyicha "
               "qonunlar va Oliy sud Plenumi qarorlari.",
    query_examples='"majburiyatni bajarmaganlik uchun penya", "shartnomani bir tomonlama bekor qilish", "pretenziya tartibi", '
                   '"daʼvo muddati", "hakamlik kelishuvi"',
    retroactivity="Shartnoma munosabatlariga shartnoma tuzilgan sanadagi qonun tahriri qoʻllanadi — voqea sanasidagi "
                  "tahrirni qoʻlla.",
)

ADMINISTRATIVE = CaseType(
    code="administrative", label=_("Maʼmuriy ish"),
    persona="maʼmuriy ishlar (maʼmuriy sud va maʼmuriy javobgarlik) boʻyicha tajribali advokat-vakil",
    scope={"document_ids": [MSIYUK, MJTK, 3492199, 4674902, 2876354, CONSTITUTION, 5511879, 4680944, 26477, 5307951, 152653],
           "doc_types": ["PLENUM"]},
    label_gen="maʼmuriy ishdan", label_by="maʼmuriy ish boʻyicha", party_role="vakil",
    final_doc="yakuniy hujjat (masalan, maʼmuriy protokol yoki organ qarori)",
    procedural_exclusion="muddatlar, protokol tuzish tartibi, huquqlarni tushuntirish, shikoyat tartibi",
    procedural_actions="protsessual harakatlar (protokol tuzilishi, huquq va majburiyatlar tushuntirilishi, ish koʻrilishi, "
                       "qarorlar, shikoyatlar, tekshiruv va ularning sanasi/vaqti)",
    procedural_task=("Vazifa: procedural_issues — maʼmuriy tartib va muddatlar buzilishi ehtimoli: maʼmuriy huquqbuzarlik "
                     "haqidagi protokol tuzish tartibi va muddati, shaxsga huquq va majburiyatlari tushuntirilganligi, ishni "
                     "koʻrish muddati, maʼmuriy jazo qoʻllash muddati oʻtmaganmi, qaror nusxasi berilishi, yuqori organga va "
                     "maʼmuriy sudga shikoyat berish muddati va tartibi, maʼmuriy tartib-taomil (tekshiruv, eshitish) rioya "
                     "qilinganligi, jarima va penya hisob-kitobi." + PROCEDURAL_TAIL),
    codes_hint="Asosan Maʼmuriy sud ishlarini yuritish toʻgʻrisidagi kodeks, Maʼmuriy javobgarlik toʻgʻrisidagi kodeks, "
               "Maʼmuriy tartib-taomillar toʻgʻrisidagi qonun, Soliq va Bojxona kodekslari, Konstitutsiya va Oliy sud "
               "Plenumi qarorlari.",
    query_examples='"maʼmuriy jazo qoʻllash muddati", "protokol tuzish tartibi", "maʼmuriy qarorga shikoyat qilish muddati", '
                   '"maʼmuriy tartib-taomil", "jarimani bekor qilish asoslari"',
    retroactivity="Maʼmuriy javobgarlikni yengillashtiruvchi qonun orqaga qaytish kuchiga ega boʻlishi mumkin — "
                  "voqea sanasidagi tahrirni qoʻlla va keyingi yengillashtirishni alohida koʻrsat.",
)

OTHER = CaseType(
    code="any", label=_("Boshqa / aralash"), persona="tajribali advokat-vakil", scope={},
    label_gen="ishdan", label_by="ish boʻyicha", party_role="vakil",
    final_doc="yakuniy hujjat (masalan, sud yoki organ qarori)",
    procedural_exclusion="muddatlar, xabarnomalar, iltimosnomalar, shikoyat muddatlari",
    procedural_actions="protsessual harakatlar (arizalar, majlislar, xabarnomalar, ekspertiza, qarorlar, shikoyatlar, "
                       "iltimosnomalar va ularning sanasi/vaqti)",
    procedural_task=("Vazifa: procedural_issues — protsessual muddatlar va tartib buzilishi ehtimoli: murojaat va shikoyat "
                     "muddatlari, taraflarga xabar berilishi, dalillarni taqdim etish va baholash tartibi, iltimosnomalarning "
                     "asossiz rad etilishi, qaror va hujjatlarni oʻz vaqtida berish va ijro etish." + PROCEDURAL_TAIL),
    codes_hint="Ishga tegishli kodekslar, qonunlar va Oliy sud Plenumi qarorlari.",
    query_examples='"murojaat muddati", "dalillarga baho berish", "xabardor qilish tartibi", "shikoyat qilish muddati"',
    retroactivity="Voqea sanasidagi tahrirni qoʻlla; qonunning orqaga qaytish kuchi faqat qonunda koʻrsatilgan hollarda.",
)

CASE_TYPES: dict[str, CaseType] = {t.code: t for t in (CRIMINAL, CIVIL, ECONOMIC, ADMINISTRATIVE, OTHER)}
DEFAULT = "criminal"

# ---- Jinoyat ishi promptlaridagi almashtiriladigan iboralar (asl matnda bo'lishi shart — test tekshiradi)
PERSONA_PHRASE = "jinoyat ishlari boʻyicha tajribali himoyachi-advokat"
EXTRACT_CASE_PHRASE = "jinoyat ishidan"
EXTRACT_ACTIONS_PHRASE = ("protsessual harakatlar (ushlab turish, tintuv, soʻroq, ekspertiza, qarorlar, tanishtirish, "
                          "iltimosnomalar va ularning sanasi/vaqti)")
CONTRADICTION_FINAL_PHRASE = "yakuniy hujjat (masalan, ayblov\n   xulosasi)"
CONTRADICTION_ROLE_PHRASE = "ish holati boʻyicha himoyachi uchun"
CONTRADICTION_EXCL_PHRASE = "muddatlar, qarorlar bilan tanishtirish, tanib olish/tintuv tartibi,\n   iltimosnomalar, qamoq asoslari"
QUERY_CASE_PHRASE = "jinoyat ishi boʻyicha"
QUERY_CODES_PHRASE = "Asosan Jinoyat-protsessual kodeksi, Jinoyat kodeksi, Konstitutsiya va Oliy sud Plenumi qarorlari."
QUERY_EXAMPLES_PHRASE = ('"ushlab turish muddati", "dalillarga baho berish", "ekspertiza tayinlash toʻgʻrisidagi\n'
                         'qaror bilan tanishtirish", "tanib olish uchun koʻrsatish tartibi", "aybsizlik prezumpsiyasi shubhalar '
                         'ayblanuvchi foydasiga"')
ASSESS_DEFENSE_PHRASE = "himoyachi nima talab qilishi kerak"
ASSESS_RETRO_PHRASE = ("keyingi oʻzgarish ahvolni yengillashtirsa (jazo yumshatilgan, qilmish jinoyat emas deb topilgan), buni "
                       "alohida koʻrsat — bunday qonun orqaga qaytish kuchiga ega boʻlishi mumkin.")


def get_case_type(code: str | None) -> CaseType:
    return CASE_TYPES.get(code or DEFAULT, CASE_TYPES[DEFAULT])


def _swap(text: str, pairs: list[tuple[str, str]]) -> str:
    for old, new in pairs:
        text = text.replace(old, new)
    return text


def adapt_extract(system: str, ct: CaseType) -> str:
    if ct.code == DEFAULT:
        return system
    return _swap(system, [(EXTRACT_CASE_PHRASE, ct.label_gen), (EXTRACT_ACTIONS_PHRASE, ct.procedural_actions)])


def adapt_analysis_common(common: str, ct: CaseType) -> str:
    return common if ct.code == DEFAULT else _swap(common, [(PERSONA_PHRASE, ct.persona)])


def adapt_contradiction_task(task: str, ct: CaseType) -> str:
    if ct.code == DEFAULT:
        return task
    return _swap(task, [(CONTRADICTION_FINAL_PHRASE, ct.final_doc), (CONTRADICTION_EXCL_PHRASE, ct.procedural_exclusion),
                        (CONTRADICTION_ROLE_PHRASE, f"ish holati boʻyicha {ct.party_role} uchun")])


def procedural_task(criminal_task: str, ct: CaseType) -> str:
    return criminal_task if ct.code == DEFAULT else ct.procedural_task


def adapt_query_system(system: str, ct: CaseType) -> str:
    if ct.code == DEFAULT:
        return system
    return _swap(system, [(QUERY_CASE_PHRASE, ct.label_by), (QUERY_CODES_PHRASE, ct.codes_hint),
                          (QUERY_EXAMPLES_PHRASE, ct.query_examples)])


def adapt_assess_system(system: str, ct: CaseType) -> str:
    if ct.code == DEFAULT:
        return system
    return _swap(system, [(PERSONA_PHRASE, ct.persona), (ASSESS_DEFENSE_PHRASE, f"{ct.party_role} nima talab qilishi kerak"),
                          (ASSESS_RETRO_PHRASE, ct.retroactivity)])


def scope_of(code: str | None) -> dict:
    return dict(get_case_type(code).scope)
