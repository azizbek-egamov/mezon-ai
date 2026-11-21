"""Admin amallarini jurnalga yozish (models.AuditEvent)."""
from .lockout import client_ip
from .models import AuditEvent


def audit(request, action: str, target: str, **details) -> AuditEvent:
    return AuditEvent.objects.create(actor=request.user if request.user.is_authenticated else None, action=action,
                                     target=target, details=details, ip=client_ip(request) or None)


def remember_login_ip(request, user, registered: bool = False) -> None:
    """Kirish/ro'yxatdan o'tish IP sini saqlash (anti-fraud radari uchun)."""
    ip = client_ip(request) or None
    fields = {"last_login_ip": ip}
    if registered:
        fields["registered_ip"] = ip
    type(user).objects.filter(pk=user.pk).update(**fields)
    for k, v in fields.items():
        setattr(user, k, v)
