from django.db import models


class UserRole(models.TextChoices):
    SUPER_ADMIN = 'super_admin', 'Super Admin'
    SALES_MANAGER = 'sales_manager', 'Sales Manager'
    AGRONOMIST = 'agronomist', 'Agronomist'
    CLIENT = 'client', 'Client'


class Language(models.TextChoices):
    UZ = 'uz', "O'zbek"
    RU = 'ru', 'Русский'
    UZ_KR = 'uz_kr', 'Ўзбек'
    EN = 'en', 'English'


class RegisteredVia(models.TextChoices):
    CLIENT_BOT = 'client_bot', 'Client Bot'
    MAIN_BOT = 'main_bot', 'Main Bot'
    ADMIN = 'admin', 'Admin Panel'


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
    language = models.CharField(
        max_length=10,
        choices=Language.choices,
        default=Language.UZ,
    )
    registered_via = models.CharField(
        max_length=20,
        choices=RegisteredVia.choices,
        default=RegisteredVia.ADMIN,
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
    """Legacy DB state — kept for migration compatibility. State now lives in Redis."""
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


class FAQItem(models.Model):
    question_uz = models.TextField(verbose_name="Savol (UZ)")
    question_ru = models.TextField(verbose_name="Вопрос (RU)")
    question_uz_kr = models.TextField(verbose_name="Савол (УЗ Кр)", blank=True)
    question_en = models.TextField(verbose_name="Question (EN)", blank=True)
    answer_uz = models.TextField(verbose_name="Javob (UZ)")
    answer_ru = models.TextField(verbose_name="Ответ (RU)")
    answer_uz_kr = models.TextField(verbose_name="Жавоб (УЗ Кр)", blank=True)
    answer_en = models.TextField(verbose_name="Answer (EN)", blank=True)
    order = models.PositiveIntegerField(default=0, verbose_name="Tartib")
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = 'faq_items'
        ordering = ['order']
        verbose_name = 'FAQ Item'
        verbose_name_plural = 'FAQ Items'

    def __str__(self):
        return self.question_uz[:60]

    def get_question(self, lang: str) -> str:
        return getattr(self, f'question_{lang}', '') or self.question_uz

    def get_answer(self, lang: str) -> str:
        return getattr(self, f'answer_{lang}', '') or self.answer_uz


class CompanyInfo(models.Model):
    """Singleton model for company contact information."""
    phone = models.CharField(max_length=50, default='+998 XX XXX XX XX')
    address_uz = models.TextField(default='Manzil ko\'rsatilmagan')
    address_ru = models.TextField(default='Адрес не указан')
    address_uz_kr = models.TextField(default='Манзил кўрсатилмаган', blank=True)
    address_en = models.TextField(default='Address not specified', blank=True)
    website = models.CharField(max_length=255, blank=True)
    price_info_uz = models.TextField(blank=True, verbose_name="Narxlar (UZ)")
    price_info_ru = models.TextField(blank=True, verbose_name="Цены (RU)")
    price_info_uz_kr = models.TextField(blank=True, verbose_name="Нархлар (УЗ Кр)")
    price_info_en = models.TextField(blank=True, verbose_name="Prices (EN)")

    class Meta:
        db_table = 'company_info'
        verbose_name = 'Company Info'
        verbose_name_plural = 'Company Info'

    def __str__(self):
        return f"Company Info — {self.phone}"

    def save(self, *args, **kwargs):
        self.pk = 1
        super().save(*args, **kwargs)

    def get_address(self, lang: str) -> str:
        return getattr(self, f'address_{lang}', '') or self.address_uz

    def get_prices(self, lang: str) -> str:
        return getattr(self, f'price_info_{lang}', '') or self.price_info_uz

    @classmethod
    def get_instance(cls):
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj
