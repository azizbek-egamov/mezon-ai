"""Admin panel ruxsatlari: MODERATOR — shablon moderatsiyasi va sinxronizatsiya holati; SUPERADMIN — hammasi."""
from django.utils.translation import gettext_lazy as _
from rest_framework.permissions import BasePermission

from apps.accounts.models import STAFF_ROLES, Role


def is_staff_role(user) -> bool:
    return bool(user and user.is_authenticated and user.is_active and (user.is_superuser or user.role in STAFF_ROLES))


def is_superadmin(user) -> bool:
    return bool(user and user.is_authenticated and user.is_active and (user.is_superuser or user.role == Role.SUPERADMIN))


class IsStaffRole(BasePermission):
    message = _("Faqat yurist-moderator yoki superadmin uchun")

    def has_permission(self, request, view):
        return is_staff_role(request.user)


class IsSuperAdmin(BasePermission):
    message = _("Faqat superadmin uchun")

    def has_permission(self, request, view):
        return is_superadmin(request.user)
