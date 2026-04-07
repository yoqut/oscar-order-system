from django.contrib import admin
from .models import TelegramUser, UserState


@admin.register(TelegramUser)
class TelegramUserAdmin(admin.ModelAdmin):
    list_display = ('telegram_id', 'full_name', 'username', 'role', 'phone', 'is_active', 'created_at')
    list_filter = ('role', 'is_active')
    search_fields = ('telegram_id', 'full_name', 'username', 'phone')
    ordering = ('-created_at',)
    readonly_fields = ('telegram_id', 'created_at', 'updated_at')
    list_editable = ('role', 'is_active')
    list_per_page = 50

    fieldsets = (
        ('Identity', {
            'fields': ('telegram_id', 'username', 'full_name', 'phone')
        }),
        ('Access', {
            'fields': ('role', 'is_active')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',),
        }),
    )


@admin.register(UserState)
class UserStateAdmin(admin.ModelAdmin):
    list_display = ('telegram_id', 'state', 'updated_at')
    search_fields = ('telegram_id', 'state')
    readonly_fields = ('updated_at',)
