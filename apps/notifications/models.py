from django.db import models
from apps.accounts.models import TelegramUser


class NotificationStatus(models.TextChoices):
    PENDING = 'pending', 'Pending'
    SENT = 'sent', 'Sent'
    FAILED = 'failed', 'Failed'


class NotificationLog(models.Model):
    recipient = models.ForeignKey(
        TelegramUser,
        on_delete=models.SET_NULL,
        null=True,
        related_name='notifications',
    )
    message = models.TextField()
    telegram_message_id = models.BigIntegerField(null=True, blank=True)
    status = models.CharField(
        max_length=10,
        choices=NotificationStatus.choices,
        default=NotificationStatus.PENDING,
        db_index=True,
    )
    error_message = models.TextField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'notification_logs'
        verbose_name = 'Notification Log'
        verbose_name_plural = 'Notification Logs'
        ordering = ['-created_at']

    def __str__(self):
        recipient = self.recipient.full_name if self.recipient else 'Unknown'
        return f"Notification to {recipient} [{self.status}] at {self.created_at:%Y-%m-%d %H:%M}"
