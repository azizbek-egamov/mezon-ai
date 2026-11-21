from django.db import migrations

# TZ §8.1 boshlang'ich qiymatlari (Admin paneldan o'zgartiriladi). Narx TZ da yo'q — belgilanmagan (None).
PLANS = {
    "FREE": dict(name="Bepul", sort_order=0, lifetime_case_limit=1, max_pages_per_case=15, lifetime_chat_limit=3,
                 lifetime_template_limit=1, watermark=True),
    "PRO_MONTHLY": dict(name="Pro (oylik)", sort_order=10, duration_days=30, daily_case_limit=10,
                        monthly_case_limit=300, max_pages_per_case=150, daily_chat_limit=100),
    "ENTERPRISE_YEARLY": dict(name="Enterprise (yillik)", sort_order=20, duration_days=365, daily_case_limit=35,
                              max_pages_per_case=500, priority_queue=True),
}


def create_plans(apps, schema_editor):
    Plan = apps.get_model("billing", "Plan")
    for code, fields in PLANS.items():
        Plan.objects.get_or_create(code=code, defaults=fields)


class Migration(migrations.Migration):
    dependencies = [("billing", "0001_initial")]
    operations = [migrations.RunPython(create_plans, migrations.RunPython.noop)]
