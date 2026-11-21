from django import forms
from django.contrib.auth import authenticate, password_validation
from django.contrib.auth.forms import BaseUserCreationForm
from django.core.exceptions import ValidationError
from django.utils.translation import gettext
from django.utils.translation import gettext_lazy as _

from apps.i18n.errors import localize_django_error

from .models import Role, User, normalize_phone


class PhoneField(forms.CharField):
    default_error_messages = {
        **forms.CharField.default_error_messages,
        "required": _("Bu maydonni toʻldiring."),
        "max_length": _("Telefon raqami juda uzun."),
    }

    def clean(self, value):
        return normalize_phone(super().clean(value))


TEXT_ERRORS = {"required": _("Bu maydonni toʻldiring."), "max_length": _("Kiritilgan matn juda uzun.")}
CHOICE_ERRORS = {"required": _("Bu maydonni toʻldiring."),
                 "invalid_choice": _("Tanlangan qiymat ruxsat etilmagan.")}


class LoginForm(forms.Form):
    phone_number = PhoneField(label=_("Telefon"), max_length=32)
    password = forms.CharField(label=_("Parol"), widget=forms.PasswordInput,
                               error_messages={"required": _("Bu maydonni toʻldiring.")})

    def __init__(self, request=None, *args, **kwargs):
        self.request, self.user = request, None
        super().__init__(*args, **kwargs)

    def clean(self):
        data = super().clean()
        if self.errors:
            return data
        self.user = authenticate(self.request, phone_number=data["phone_number"], password=data["password"])
        if self.user is None:
            raise ValidationError(gettext("Telefon raqami yoki parol notoʻgʻri"))
        return data


class RegisterForm(forms.Form):
    phone_number = PhoneField(label=_("Telefon"), max_length=32)
    full_name = forms.CharField(label=_("F.I.Sh."), max_length=255, error_messages=TEXT_ERRORS)
    role = forms.ChoiceField(label=_("Kim sifatida"), choices=[(Role.LAWYER, Role.LAWYER.label),
                                                             (Role.STUDENT, Role.STUDENT.label),
                                                             (Role.CLIENT, Role.CLIENT.label)],
                             error_messages=CHOICE_ERRORS)
    advocate_license_no = forms.CharField(label=_("Advokatlik guvohnomasi raqami"), max_length=50, required=False,
                                           error_messages=TEXT_ERRORS)
    university = forms.CharField(label=_("OTM / Universitet"), max_length=150, required=False,
                                 error_messages=TEXT_ERRORS)
    study_level = forms.CharField(label=_("Bosqich / Kurs"), max_length=50, required=False,
                                  error_messages=TEXT_ERRORS)
    student_id_no = forms.CharField(label=_("Talabalik guvohnomasi / HEMIS ID"), max_length=50, required=False,
                                    error_messages=TEXT_ERRORS)
    password1 = forms.CharField(label=_("Parol"), widget=forms.PasswordInput,
                                error_messages={"required": _("Bu maydonni toʻldiring.")})
    password2 = forms.CharField(label=_("Parolni takrorlang"), widget=forms.PasswordInput,
                                error_messages={"required": _("Bu maydonni toʻldiring.")})
    consent = forms.BooleanField(label=_("Shaxsiy maʼlumotlarimni qayta ishlashga roziman (OʻRQ-547)"),
                                 error_messages={"required": _("Davom etish uchun rozilikni tasdiqlang.")})

    def clean_phone_number(self):
        phone = self.cleaned_data["phone_number"]
        if User.objects.filter(phone_number=phone).exists():
            raise ValidationError(gettext("Bu raqam bilan akkaunt allaqachon bor"))
        return phone

    def clean(self):
        data = super().clean()
        p1, p2 = data.get("password1"), data.get("password2")
        if p1 and p2 and p1 != p2:
            self.add_error("password2", gettext("Parollar mos kelmadi"))
        elif p1:
            user = User(phone_number=data.get("phone_number", ""), full_name=data.get("full_name", ""))
            try:
                password_validation.validate_password(p1, user)
            except ValidationError as e:
                for item in e.error_list:
                    self.add_error("password1", ValidationError(localize_django_error(item), code=item.code,
                                                                 params=item.params))
        return data

    def save(self) -> User:
        d = self.cleaned_data
        user = User(phone_number=d["phone_number"], full_name=d["full_name"].strip(), role=d["role"],
                    advocate_license_no=(d.get("advocate_license_no") or "").strip(),
                    university=(d.get("university") or "").strip(),
                    study_level=(d.get("study_level") or "").strip(),
                    student_id_no=(d.get("student_id_no") or "").strip())
        user.set_password(d["password1"])
        user.record_consent("pii")
        user.save()
        return user


class AdminUserCreationForm(BaseUserCreationForm):
    class Meta:
        model = User
        fields = ("phone_number", "full_name", "role")

    def clean_phone_number(self):
        return normalize_phone(self.cleaned_data["phone_number"])
