from django.db import models


class UserRole(models.TextChoices):
    SUPER_ADMIN = 'super_admin', 'Super Admin'
    SALES_MANAGER = 'sales_manager', 'Sales Manager'
    AGRONOMIST = 'agronomist', 'Agronomist'
    CLIENT = 'client', 'Client'


class TelegramUser(models.Model):
    telegram_id = models.BigIntegerField(unique=True, db_index=True)
    username = models.CharField(max_length=255, null=True, blank=True)
    full_name = models.CharField(max_length=255)
    phone = models.CharField(max_length=20, null=True, blank=True)
    role = models.CharField(
        max_length=20,
        choices=UserRole.choices,
        default=UserRole.CLIENT,
        db_index=True,
    )
    is_active = models.BooleanField(default=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'telegram_users'
        verbose_name = 'Telegram User'
        verbose_name_plural = 'Telegram Users'

    def __str__(self):
        name = self.full_name or self.username or str(self.telegram_id)
        return f"{name} [{self.get_role_display()}]"

    @property
    def is_admin(self):
        return self.role == UserRole.SUPER_ADMIN

    @property
    def is_sales_manager(self):
        return self.role == UserRole.SALES_MANAGER

    @property
    def is_agronomist(self):
        return self.role == UserRole.AGRONOMIST

    @property
    def is_client(self):
        return self.role == UserRole.CLIENT


class UserState(models.Model):
    """Persists FSM state for each Telegram user across bot interactions."""
    telegram_id = models.BigIntegerField(unique=True, db_index=True)
    state = models.CharField(max_length=100, null=True, blank=True)
    data = models.JSONField(default=dict)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'user_states'
        verbose_name = 'User State'
        verbose_name_plural = 'User States'

    def __str__(self):
        return f"State[{self.telegram_id}] = {self.state}"
