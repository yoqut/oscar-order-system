from django.db import models
from apps.accounts.models import TelegramUser


class TimeSlot(models.TextChoices):
    SLOT_1 = '08:30-09:30', '08:30 - 09:30'
    SLOT_2 = '10:00-11:00', '10:00 - 11:00'
    SLOT_3 = '15:00-16:00', '15:00 - 16:00'
    SLOT_4 = '16:30-17:30', '16:30 - 17:30'
    SLOT_5 = '18:00-19:00', '18:00 - 19:00'


class OrderStatus(models.TextChoices):
    PENDING = 'pending', 'Pending'
    APPROVED = 'approved', 'Approved'
    IN_PROGRESS = 'in_progress', 'In Progress'
    COMPLETED = 'completed', 'Completed'
    CANCELLED = 'cancelled', 'Cancelled'
    CLIENT_CONFIRMED = 'client_confirmed', 'Client Confirmed'
    CLIENT_REJECTED = 'client_rejected', 'Client Rejected'


class PaymentType(models.TextChoices):
    CASH = 'cash', 'Naqd pul'
    CARD = 'card', 'Karta'
    BANK_TRANSFER = 'bank_transfer', 'Bank o\'tkazmasi'


class Order(models.Model):
    sales_manager = models.ForeignKey(
        TelegramUser,
        on_delete=models.PROTECT,
        related_name='created_orders',
        limit_choices_to={'role': 'sales_manager'},
    )
    agronomist = models.ForeignKey(
        TelegramUser,
        on_delete=models.PROTECT,
        related_name='assigned_orders',
        limit_choices_to={'role': 'agronomist'},
    )
    client = models.ForeignKey(
        TelegramUser,
        on_delete=models.SET_NULL,
        related_name='client_orders',
        null=True,
        blank=True,
        limit_choices_to={'role': 'client'},
    )
    # Client contact info filled by sales manager
    client_name = models.CharField(max_length=255)
    phone1 = models.CharField(max_length=20)
    phone2 = models.CharField(max_length=20, null=True, blank=True)
    tree_count = models.PositiveIntegerField()
    problem = models.TextField()
    address = models.TextField()
    time_slot = models.CharField(max_length=20, choices=TimeSlot.choices)
    status = models.CharField(
        max_length=20,
        choices=OrderStatus.choices,
        default=OrderStatus.PENDING,
        db_index=True,
    )
    cancel_reason = models.TextField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'orders'
        verbose_name = 'Order'
        verbose_name_plural = 'Orders'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['status', 'created_at']),
            models.Index(fields=['agronomist', 'status']),
        ]

    def __str__(self):
        return f"Order #{self.pk} — {self.client_name} ({self.get_status_display()})"

    def get_summary(self):
        slot_display = self.get_time_slot_display()
        return (
            f"<b>Order #{self.pk}</b>\n"
            f"Client: {self.client_name}\n"
            f"Phone: {self.phone1}"
            + (f" / {self.phone2}" if self.phone2 else "")
            + f"\nTrees: {self.tree_count}\n"
            f"Time slot: {slot_display}\n"
            f"Problem: {self.problem}\n"
            f"Address: {self.address}\n"
            f"Status: {self.get_status_display()}"
        )


class TreatmentDetails(models.Model):
    order = models.OneToOneField(
        Order,
        on_delete=models.CASCADE,
        related_name='treatment_details',
    )
    treatment_count = models.PositiveIntegerField()
    root_treatment_applied = models.BooleanField(default=False)
    final_price = models.DecimalField(max_digits=12, decimal_places=2)
    payment_type = models.CharField(max_length=20, choices=PaymentType.choices)
    re_treatment_needed = models.BooleanField(default=False)
    re_treatment_date = models.DateField(null=True, blank=True)
    re_treatment_notified = models.BooleanField(default=False)
    proof_file_id = models.CharField(max_length=255, null=True, blank=True)
    proof_file_type = models.CharField(
        max_length=10,
        choices=[('photo', 'Photo'), ('video', 'Video')],
        null=True,
        blank=True,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'treatment_details'
        verbose_name = 'Treatment Details'
        verbose_name_plural = 'Treatment Details'

    def __str__(self):
        return f"Treatment for Order #{self.order_id}"

    def get_summary(self):
        root = "Ha" if self.root_treatment_applied else "Yo'q"
        retreatment = "Ha" if self.re_treatment_needed else "Yo'q"
        return (
            f"Ishlov soni: {self.treatment_count}\n"
            f"Ildiz ishlov: {root}\n"
            f"Narx: {self.final_price} so'm\n"
            f"To'lov turi: {self.get_payment_type_display()}\n"
            f"Qayta ishlov: {retreatment}"
            + (f"\nQayta sana: {self.re_treatment_date}" if self.re_treatment_date else "")
        )


class Feedback(models.Model):
    order = models.OneToOneField(
        Order,
        on_delete=models.CASCADE,
        related_name='feedback',
    )
    client = models.ForeignKey(
        TelegramUser,
        on_delete=models.SET_NULL,
        null=True,
        related_name='feedbacks',
    )
    rating = models.PositiveSmallIntegerField(
        choices=[(i, f"{i} ⭐") for i in range(1, 6)]
    )
    comment = models.TextField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'feedbacks'
        verbose_name = 'Feedback'
        verbose_name_plural = 'Feedbacks'

    def __str__(self):
        return f"Feedback for Order #{self.order_id} — {self.rating}⭐"
