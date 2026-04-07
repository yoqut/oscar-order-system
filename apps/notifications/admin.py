from django.contrib import admin
from .models import NotificationLog


@admin.register(NotificationLog)
class NotificationLogAdmin(admin.ModelAdmin):
    list_display = ('recipient', 'status', 'short_message', 'telegram_message_id', 'created_at')
    list_filter = ('status', 'created_at')
    search_fields = ('recipient__full_name', 'recipient__telegram_id', 'message')
    readonly_fields = ('created_at',)
    ordering = ('-created_at',)
    list_per_page = 100

    def short_message(self, obj):
        return obj.message[:60] + '...' if len(obj.message) > 60 else obj.message
    short_message.short_description = 'Message'
