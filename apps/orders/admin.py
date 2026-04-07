from django.contrib import admin
from django.utils.html import format_html
from .models import Order, TreatmentDetails, Feedback


class TreatmentDetailsInline(admin.StackedInline):
    model = TreatmentDetails
    extra = 0
    readonly_fields = ('created_at', 'updated_at')


class FeedbackInline(admin.StackedInline):
    model = Feedback
    extra = 0
    readonly_fields = ('created_at',)


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = (
        'id', 'client_name', 'phone1', 'status_badge',
        'agronomist', 'sales_manager', 'time_slot', 'created_at',
    )
    list_filter = ('status', 'time_slot', 'created_at')
    search_fields = ('client_name', 'phone1', 'phone2', 'address', 'problem')
    ordering = ('-created_at',)
    readonly_fields = ('created_at', 'updated_at')
    inlines = [TreatmentDetailsInline, FeedbackInline]
    list_per_page = 50
    date_hierarchy = 'created_at'

    STATUS_COLORS = {
        'pending': '#FFA500',
        'approved': '#2196F3',
        'in_progress': '#9C27B0',
        'completed': '#4CAF50',
        'cancelled': '#F44336',
        'client_confirmed': '#00BCD4',
        'client_rejected': '#FF5722',
    }

    def status_badge(self, obj):
        color = self.STATUS_COLORS.get(obj.status, '#888')
        return format_html(
            '<span style="background:{};color:#fff;padding:3px 8px;border-radius:4px;">{}</span>',
            color, obj.get_status_display()
        )
    status_badge.short_description = 'Status'

    fieldsets = (
        ('Client Info', {
            'fields': ('client_name', 'phone1', 'phone2', 'address', 'problem', 'tree_count')
        }),
        ('Assignment', {
            'fields': ('sales_manager', 'agronomist', 'client', 'time_slot')
        }),
        ('Status', {
            'fields': ('status', 'cancel_reason')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',),
        }),
    )

    actions = ['approve_orders', 'cancel_orders']

    def approve_orders(self, request, queryset):
        updated = queryset.filter(status='pending').update(status='approved')
        self.message_user(request, f"{updated} order(s) approved.")
    approve_orders.short_description = "Approve selected orders"

    def cancel_orders(self, request, queryset):
        updated = queryset.exclude(status__in=['completed', 'cancelled']).update(
            status='cancelled', cancel_reason='Cancelled by admin'
        )
        self.message_user(request, f"{updated} order(s) cancelled.")
    cancel_orders.short_description = "Cancel selected orders"


@admin.register(TreatmentDetails)
class TreatmentDetailsAdmin(admin.ModelAdmin):
    list_display = (
        'order', 'treatment_count', 'root_treatment_applied',
        'final_price', 'payment_type', 're_treatment_needed', 're_treatment_date',
    )
    list_filter = ('payment_type', 'root_treatment_applied', 're_treatment_needed')
    search_fields = ('order__client_name', 'order__id')
    readonly_fields = ('created_at', 'updated_at')


@admin.register(Feedback)
class FeedbackAdmin(admin.ModelAdmin):
    list_display = ('order', 'client', 'rating', 'comment', 'created_at')
    list_filter = ('rating',)
    search_fields = ('order__client_name', 'comment')
    readonly_fields = ('created_at',)
