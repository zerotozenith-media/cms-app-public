from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.db import models


class UserManager(BaseUserManager):
    """
    Required whenever username is removed in favour of email , Django's
    default UserManager still expects a username positional argument
    without this.
    """
    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError("Users must have an email address.")
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        return self.create_user(email, password, **extra_fields)


class Role(models.Model):
    name = models.CharField(max_length=100, unique=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


class RolePermission(models.Model):
    """
    Real action-level permissions (Batch 0.6, Finding 2) , replaces the
    demo's flat "list of visible pages" with per-module, per-action control.
    """
    role = models.ForeignKey("accounts.Role", on_delete=models.CASCADE, related_name="permissions")
    module = models.CharField(max_length=50, help_text="e.g. 'attendance', 'members', 'finance'")
    can_view = models.BooleanField(default=False)
    can_create = models.BooleanField(default=False)
    can_edit = models.BooleanField(default=False)
    can_delete = models.BooleanField(default=False)

    class Meta:
        unique_together = ("role", "module")
        ordering = ["role", "module"]

    def __str__(self):
        return f"{self.role} / {self.module}"


class User(AbstractUser):
    """
    Custom user model (Batch 0.6). Extends Django's built-in AbstractUser
    rather than reinventing password hashing / login machinery , Django's
    is_active field maps directly to the approved schema's `status`
    (Active/Inactive), and last_login is Django's built-in field, so
    neither is duplicated here.
    """
    username = None  # not used , email is the login identifier
    email = models.EmailField(unique=True)
    role = models.ForeignKey(
        "accounts.Role", on_delete=models.PROTECT, related_name="users",
        null=True, blank=True,
        help_text="Nullable at the DB level only so Django's createsuperuser bootstrap "
                   "command works before any Role exists yet. The real 'Add User' feature "
                   "in the app enforces this as required.",
    )
    location = models.ForeignKey(
        "core.Location", on_delete=models.SET_NULL, null=True, blank=True,
        related_name="users",
        help_text="Blank = access to all locations (e.g. Administrator).",
    )
    member = models.ForeignKey(
        "members.Member", on_delete=models.SET_NULL, null=True, blank=True,
        related_name="user_accounts",
        help_text="Optional link when a staff user is also a congregant (Batch 0.6, Finding 1).",
    )

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = []

    objects = UserManager()

    class Meta:
        ordering = ["email"]

    def __str__(self):
        return self.email

    def delete(self, *args, **kwargs):
        # Batch 0.6, Finding 4: the last remaining Administrator cannot be deleted.
        if self.role_id and self.role.name == "Administrator":
            other_admins = User.objects.filter(role__name="Administrator").exclude(pk=self.pk)
            if not other_admins.exists():
                from django.core.exceptions import ValidationError
                raise ValidationError("Cannot delete the last remaining Administrator account.")
        return super().delete(*args, **kwargs)


class AuditLog(models.Model):
    """
    Batch 0.6 approved schema. This was missed in Batch 1.2's model build ,
    caught and fixed here in Batch 1.4, since login-attempt logging needs
    an audit trail to write to anyway.
    """
    user = models.ForeignKey(
        "accounts.User", on_delete=models.SET_NULL, null=True, blank=True,
        related_name="audit_entries",
    )
    user_name_snapshot = models.CharField(
        max_length=200,
        help_text="Captured at the moment of the action, so this stays readable "
                   "even if the account is later renamed or removed.",
    )
    timestamp = models.DateTimeField(auto_now_add=True)
    action = models.CharField(max_length=100)
    entity_type = models.CharField(max_length=100)
    entity_name = models.CharField(max_length=200, blank=True, default="")
    details = models.TextField(blank=True, default="")

    class Meta:
        ordering = ["-timestamp"]
        verbose_name_plural = "Audit log"

    def __str__(self):
        return f"{self.timestamp} , {self.user_name_snapshot} , {self.action} {self.entity_type}"


class LoginAttempt(models.Model):
    """
    New model, not part of the original Batch 0.6 schema , added here in
    Batch 1.4 specifically to support the agreed login security features
    (rate limiting, lockout, bot detection). Kept separate from AuditLog
    deliberately: login attempts are high-volume and security-focused
    (including failed attempts against emails that don't even exist),
    which doesn't fit the business-action-history purpose AuditLog serves.
    """
    class Reason(models.TextChoices):
        SUCCESS = "success", "Success"
        INVALID_CREDENTIALS = "invalid_credentials", "Invalid credentials"
        ACCOUNT_LOCKED = "account_locked", "Account temporarily locked"
        ACCOUNT_INACTIVE = "account_inactive", "Account inactive"
        RATE_LIMITED = "rate_limited", "Too many attempts from this IP"
        HONEYPOT = "honeypot", "Honeypot field triggered"
        TOO_FAST = "too_fast", "Submitted faster than humanly possible"

    email_attempted = models.EmailField()
    ip_address = models.GenericIPAddressField()
    successful = models.BooleanField()
    reason = models.CharField(max_length=30, choices=Reason.choices)
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-timestamp"]

    def __str__(self):
        status = "OK" if self.successful else f"FAILED ({self.reason})"
        return f"{self.timestamp} , {self.email_attempted} , {status}"
