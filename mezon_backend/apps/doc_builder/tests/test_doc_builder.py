import io
from datetime import date
from decimal import Decimal
from pathlib import Path
from unittest import skipUnless

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.core.management import call_command
from django.test import TestCase, override_settings

from apps.accounts.models import Role
from apps.doc_builder.admin import DocumentTemplateAdmin
from apps.doc_builder.models import DocumentTemplate
from apps.doc_builder.rendering import fill, format_values, render_blocks
from apps.doc_builder.starter_templates import TEMPLATES

HAS_FONTS = (Path("C:/Windows/Fonts") / "times.ttf").exists()
SCHEMA = [{"name": "fio", "label": "F.I.Sh.", "type": "text"},
          {"name": "summa", "label": "Summa", "type": "money"},
          {"name": "sana", "label": "Sana", "type": "date"},
          {"name": "izoh", "label": "Izoh", "type": "textarea", "required": False}]
BODY = """>> Sudga
>> {{ fio }}dan

## DAʼVO ARIZASI

{{ sana }} kuni {{ summa }} soʻm berilgan.
{% if izoh %}{{ izoh }}
{% endif %}- birinchi talab
~ {{ fio }} | ____
"""
SAMPLE = {"text": "Aliyev Vali", "textarea": "Birinchi qator\nIkkinchi qator", "date": "2026-03-04",
          "number": "3", "money": "85000000", "phone": "+998 90 123 45 67", "jshshir": "31205910450027"}


def make(**kw):
    t = DocumentTemplate(title=kw.pop("title", "Test"), category="CLAIM", form_schema=kw.pop("form_schema", SCHEMA),
                         body=kw.pop("body", BODY), is_published=kw.pop("is_published", True), **kw)
    t.full_clean()
    t.save()
    return t


def sample_data(template):
    return {f["name"]: (f["options"][0] if f.get("type") == "select" else SAMPLE[f.get("type", "text")])
            for f in template.form_schema}


class TemplateModelTests(TestCase):
    def test_validation(self):
        with self.assertRaises(ValidationError):  # sxemada yo'q maydon
            make(body="{{ fio }} {{ nomalum }}")
        with self.assertRaises(ValidationError):  # sintaksis xatosi
            make(body="{% if fio %}yopilmagan")
        for bad in ([], [{"name": "Fio", "label": "x"}], [{"name": "a", "label": "x", "type": "rasm"}],
                    [{"name": "a", "label": "x", "type": "select"}], [{"name": "a", "label": "x"}, {"name": "a", "label": "y"}]):
            with self.assertRaises(ValidationError, msg=bad):
                make(form_schema=bad, body="")

    def test_edit_bumps_version_and_resets_approval(self):
        user = get_user_model().objects.create_user("+998901112233", "Kuchli-parol-77", full_name="Moderator",
                                                    role=Role.MODERATOR)
        t = make()
        DocumentTemplate.objects.filter(pk=t.pk).update(approved_by=user, approved_at="2026-10-26T10:00:00Z")
        t.refresh_from_db()
        t.description = "faqat tavsif"
        t.save()
        t.refresh_from_db()
        self.assertEqual((t.version, t.approved_by), (1, user))  # tavsif o'zgarishi tasdiqni buzmaydi
        t.body = BODY + "\nYangi qator"
        t.save()
        t.refresh_from_db()
        self.assertEqual((t.version, t.approved_by, t.approved_at), (2, None, None))

    def test_rendering_and_formatting(self):
        t = make()
        values = format_values(t, {"fio": "Aliyev Vali", "summa": Decimal("85000000"), "sana": date(2026, 3, 4),
                                   "izoh": ""})
        self.assertEqual((values["summa"], values["sana"]), ("85 000 000", "04.03.2026"))
        blocks = render_blocks(t, values)
        self.assertEqual([(b.kind, b.text) for b in blocks], [
            ("right", "Sudga"), ("right", "Aliyev Validan"), ("space", ""), ("center", "DAʼVO ARIZASI"), ("space", ""),
            ("p", "04.03.2026 kuni 85 000 000 soʻm berilgan."), ("item", "birinchi talab"),
            ("sign", "Aliyev Vali | ____")])
        self.assertEqual((blocks[-1].sign_left, blocks[-1].sign_right), ("Aliyev Vali", "____"))

    def test_required_fields_and_formats(self):
        t = make(form_schema=SCHEMA + [{"name": "tel", "label": "Tel", "type": "phone"},
                                       {"name": "jsh", "label": "JSHSHIR", "type": "jshshir"}])
        form, blocks = fill(t, {"fio": "", "summa": "abc", "sana": "2026-03-04", "tel": "12345", "jsh": "123"})
        self.assertIsNone(blocks)
        self.assertEqual(set(form.errors), {"fio", "summa", "tel", "jsh"})


@skipUnless(HAS_FONTS, "Times New Roman shrifti yo'q")
class StarterTemplatesTests(TestCase):
    def test_all_starter_templates_render_to_docx_and_pdf(self):
        call_command("load_starter_templates", stdout=io.StringIO())
        self.assertEqual(DocumentTemplate.objects.count(), len(TEMPLATES))
        from apps.doc_builder.writers import to_docx, to_pdf
        for t in DocumentTemplate.objects.all():
            form, blocks = fill(t, sample_data(t))
            self.assertIsNotNone(blocks, (t.title, form.errors))
            text = "\n".join(b.text for b in blocks)
            self.assertNotIn("{{", text)
            self.assertTrue(to_docx(blocks).startswith(b"PK"), t.title)
            self.assertTrue(to_pdf(blocks).startswith(b"%PDF"), t.title)
        call_command("load_starter_templates", stdout=io.StringIO())  # qayta yuklash — takrorlanmaydi
        self.assertEqual(DocumentTemplate.objects.count(), len(TEMPLATES))
        self.assertEqual(set(DocumentTemplate.objects.values_list("version", flat=True)), {1})


@skipUnless(HAS_FONTS, "Times New Roman shrifti yo'q")
@override_settings(BILLING_ENFORCED=False)   # kvotalar alohida sinaladi (apps/billing/tests)
class TemplateViewsTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user("+998901112233", "Kuchli-parol-77", full_name="Advokat")
        self.client.force_login(self.user)
        self.t = make(title="Daʼvo")
        self.data = {"fio": "Aliyev Vali", "summa": "1500", "sana": "2026-03-04"}

    def test_login_required(self):
        self.client.logout()
        self.assertEqual(self.client.get("/templates/").status_code, 302)
        self.assertEqual(self.client.post(f"/templates/{self.t.id}/", {**self.data, "action": "pdf"}).status_code, 302)

    def test_list_preview_and_download(self):
        draft = make(title="Qoralama", is_published=False)
        page = self.client.get("/templates/")
        self.assertContains(page, "Daʼvo")
        self.assertNotContains(page, "Qoralama")
        self.assertEqual(self.client.get(f"/templates/{draft.id}/").status_code, 404)
        preview = self.client.post(f"/templates/{self.t.id}/", {**self.data, "action": "preview"})
        self.assertContains(preview, "04.03.2026 kuni 1 500 soʻm berilgan.")
        docx = self.client.post(f"/templates/{self.t.id}/", {**self.data, "action": "docx"})
        self.assertTrue(docx.content.startswith(b"PK"))
        self.assertIn("attachment", docx["Content-Disposition"])
        pdf = self.client.post(f"/templates/{self.t.id}/", {**self.data, "action": "pdf"})
        self.assertTrue(pdf.content.startswith(b"%PDF"))
        invalid = self.client.post(f"/templates/{self.t.id}/", {"action": "pdf"})
        self.assertEqual(invalid["Content-Type"], "text/html; charset=utf-8")  # xato — forma qayta ko'rsatiladi

    def test_only_moderator_can_approve(self):
        from django.contrib.admin.sites import AdminSite
        from django.contrib.messages.storage.fallback import FallbackStorage
        from django.test import RequestFactory
        admin = DocumentTemplateAdmin(DocumentTemplate, AdminSite())
        for role, approved in ((Role.LAWYER, False), (Role.MODERATOR, True)):
            request = RequestFactory().post("/")
            request.user = get_user_model()(phone_number="+998900000000", role=role, full_name="X")
            request.user.save()
            request.session = {}
            request._messages = FallbackStorage(request)
            admin.approve(request, DocumentTemplate.objects.filter(pk=self.t.pk))
            self.t.refresh_from_db()
            self.assertEqual(self.t.approved_at is not None, approved)
            request.user.delete()
