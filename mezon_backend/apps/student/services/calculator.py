"""Davlat boji va protsessual muddatlar kalkulyatori (ZERO API COST).
O'zbekiston Respublikasining "Davlat boji to'g'risida"gi Qonuni (O'RQ-600),
Fuqarolik protsessual kodeksi (FPK), Iqtisodiy protsessual kodeksi (IPK)
va Ma'muriy sud ishlarini yuritish to'g'risidagi kodeksi (MSIYK) asosida.
"""
from datetime import date, timedelta
from decimal import Decimal, ROUND_HALF_UP

# Amaldagi Bazaviy hisoblash miqdori (BHM) — so'mda
CURRENT_BHM = 375_000


def calculate_court_fee(
    court_type: str,
    claim_type: str,
    claim_amount: float = 0,
    is_repeated_divorce: bool = False,
    stage: str = "FIRST_INSTANCE",
    bhm: int = CURRENT_BHM,
) -> dict:
    """Davlat boji miqdorini aniq hisoblab beradi.
    court_type: CIVIL (Fuqarolik), ECONOMIC (Iqtisodiy), ADMINISTRATIVE (Ma'muriy)
    claim_type: PROPERTY (Mulkiy), NON_PROPERTY (Nomulkiy), DIVORCE (Nikohdan ajratish),
                CONTRACT_DISPUTE (Shartnomaviy nizo), ORDER (Sud buyrug'i)
    stage: FIRST_INSTANCE, APPEAL_CASSATION
    """
    fee = Decimal("0.0")
    bhm_dec = Decimal(str(bhm))
    amount_dec = Decimal(str(max(claim_amount, 0)))
    law_article = ""

    if court_type == "CIVIL":
        if claim_type == "PROPERTY":
            # Mulkiy da'volar: da'vo bahosining 4% miqdorida, lekin BHMning 1 baravaridan kam bo'lmagan
            calculated = (amount_dec * Decimal("0.04")).quantize(Decimal("1"), rounding=ROUND_HALF_UP)
            fee = max(calculated, bhm_dec)
            law_article = "O'RQ-600 5-modda, 1-band 'a' kichik bandi (da'vo bahosining 4 foizi, kamida 1 BHM)"
        elif claim_type == "DIVORCE":
            # Nikohdan ajratish: 2 BHM; takroriy nikohda 4 BHM
            fee = bhm_dec * (Decimal("4.0") if is_repeated_divorce else Decimal("2.0"))
            law_article = "O'RQ-600 5-modda, 1-band 'b' kichik bandi (nikohdan ajratishda 2 BHM, takroriyda 4 BHM)"
        elif claim_type == "ORDER":
            # Sud buyrug'i: da'vo arizasi stavkasining 50%
            base_fee = max((amount_dec * Decimal("0.04")).quantize(Decimal("1"), rounding=ROUND_HALF_UP), bhm_dec)
            fee = (base_fee * Decimal("0.5")).quantize(Decimal("1"), rounding=ROUND_HALF_UP)
            law_article = "O'RQ-600 5-modda (sud buyrug'i uchun belgilangan stavkaning 50 foizi)"
        else:
            # Nomulkiy da'volar: BHMning 50%
            fee = (bhm_dec * Decimal("0.5")).quantize(Decimal("1"), rounding=ROUND_HALF_UP)
            law_article = "O'RQ-600 5-modda, 1-band 'g' kichik bandi (nomulkiy da'volarda BHMning 50 foizi)"

    elif court_type == "ECONOMIC":
        if claim_type == "PROPERTY":
            # Mulkiy: 2%, lekin kamida 1 BHM
            calculated = (amount_dec * Decimal("0.02")).quantize(Decimal("1"), rounding=ROUND_HALF_UP)
            fee = max(calculated, bhm_dec)
            law_article = "O'RQ-600 5-modda, 2-band 'a' kichik bandi (da'vo bahosining 2 foizi, kamida 1 BHM)"
        elif claim_type == "CONTRACT_DISPUTE":
            # Shartnomani tuzish, o'zgartirish, bekor qilish: 10 BHM
            fee = bhm_dec * Decimal("10.0")
            law_article = "O'RQ-600 5-modda, 2-band 'b' kichik bandi (shartnoma nizolarida 10 BHM)"
        elif claim_type == "ORDER":
            base_fee = max((amount_dec * Decimal("0.02")).quantize(Decimal("1"), rounding=ROUND_HALF_UP), bhm_dec)
            fee = (base_fee * Decimal("0.5")).quantize(Decimal("1"), rounding=ROUND_HALF_UP)
            law_article = "O'RQ-600 5-modda (sud buyrug'i uchun stavkaning 50 foizi)"
        else:
            # Nomulkiy: 10 BHM
            fee = bhm_dec * Decimal("10.0")
            law_article = "O'RQ-600 5-modda, 2-band (nomulkiy da'volarda 10 BHM)"

    elif court_type == "ADMINISTRATIVE":
        # Davlat organlari va mansabdor shaxslar qarorlari ustidan: 1 BHM
        fee = bhm_dec * Decimal("1.0")
        law_article = "O'RQ-600 5-modda, 3-band (ma'muriy arizalar uchun 1 BHM)"

    # Apellyatsiya / Kassatsiya bosqichi bo'lsa, stavkaning 50%
    if stage == "APPEAL_CASSATION":
        fee = (fee * Decimal("0.5")).quantize(Decimal("1"), rounding=ROUND_HALF_UP)
        law_article += " + shikoyat berishda stavkaning 50 foizi"

    # Pochta xarajati (taxminan 0.1 BHM)
    postal_cost = (bhm_dec * Decimal("0.1")).quantize(Decimal("1"), rounding=ROUND_HALF_UP)
    total_payment = fee + postal_cost

    return {
        "court_type": court_type,
        "claim_type": claim_type,
        "bhm_rate": bhm,
        "claim_amount": float(amount_dec),
        "court_fee_uzs": float(fee),
        "postal_cost_uzs": float(postal_cost),
        "total_uzs": float(total_payment),
        "legal_basis": law_article,
    }


def calculate_deadline(start_date: date, procedure: str) -> dict:
    """Protsessual muddatlarni hisoblaydi va yakuniy sanani chiqaradi."""
    # procedure:
    #   CIVIL_APPEAL (1 oy)
    #   ECONOMIC_APPEAL (1 oy)
    #   ADMIN_APPEAL (1 oy)
    #   CRIMINAL_APPEAL (20 kun)
    #   ADMIN_OFFENSE_APPEAL (10 kun)
    #   COURT_ORDER_OBJECTION (10 kun)
    #   CLAIM_LIMITATION_GENERAL (3 yil)
    #   LABOR_DISMISSAL_CLAIM (3 oy)

    deadline_date = start_date
    rule_desc = ""

    if procedure in ("CIVIL_APPEAL", "ECONOMIC_APPEAL", "ADMIN_APPEAL"):
        # 1 oy (FPK 385-1-m, IPK 262-m, MSIYK 202-m)
        # 1 oy keyingi oyning mos sanasi
        year = start_date.year + (1 if start_date.month == 12 else 0)
        month = 1 if start_date.month == 12 else start_date.month + 1
        day = min(start_date.day, 28) # xavfsiz sana
        deadline_date = date(year, month, day)
        rule_desc = "Qaror qabul qilingan kundan boshlab 1 oy muddatda (FPK 385-1-m / IPK 262-m)"
    elif procedure == "CRIMINAL_APPEAL":
        # 20 kun (JPK 497-4-m)
        deadline_date = start_date + timedelta(days=20)
        rule_desc = "Hukm e'lon qilingan kundan boshlab 20 sutka ichida (JPK 497-4-m)"
    elif procedure in ("ADMIN_OFFENSE_APPEAL", "COURT_ORDER_OBJECTION"):
        # 10 kun (MJtK 315-m / FPK 177-m)
        deadline_date = start_date + timedelta(days=10)
        rule_desc = "Qaror yoki sud buyrug'i nusxasi olingan kundan boshlab 10 kun ichida"
    elif procedure == "LABOR_DISMISSAL_CLAIM":
        # 3 oy (Yangi MK 560-m)
        year = start_date.year + (start_date.month + 3 - 1) // 12
        month = (start_date.month + 3 - 1) % 12 + 1
        day = min(start_date.day, 28)
        deadline_date = date(year, month, day)
        rule_desc = "Ish beruvchining buyrug'i topshirilgan kundan e'tiboran 3 oy ichida (MK 560-m)"
    elif procedure == "CLAIM_LIMITATION_GENERAL":
        # 3 yil (FK 150-m)
        deadline_date = date(start_date.year + 3, start_date.month, start_date.day)
        rule_desc = "Huquq buzilganligi ma'lum bo'lgan kundan boshlab umumiy 3 yillik da'vo muddati (FK 150-m)"
    else:
        deadline_date = start_date + timedelta(days=30)
        rule_desc = "Umumiy 30 kunlik muddat"

    # Agar so'nggi kun shanba (5) yoki yakshanba (6) bo'lsa, dushanbaga ko'chiriladi (FPK 152-m)
    weekday = deadline_date.weekday()
    adjusted = False
    if weekday == 5:  # Shanba
        deadline_date += timedelta(days=2)
        adjusted = True
    elif weekday == 6:  # Yakshanba
        deadline_date += timedelta(days=1)
        adjusted = True

    return {
        "start_date": start_date.isoformat(),
        "deadline_date": deadline_date.isoformat(),
        "procedure": procedure,
        "rule_description": rule_desc,
        "adjusted_for_weekend": adjusted,
    }

