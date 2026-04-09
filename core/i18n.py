"""
4-language translation system for the client bot.
Main bot (staff) uses Uzbek only.

Usage:
    from core.i18n import t, get_user_lang, set_user_lang

    text = t('welcome_new', lang='ru', name='Ali')
    lang = await get_user_lang(telegram_id)
    await set_user_lang(telegram_id, 'ru')
"""
import logging
from core.redis_client import redis

logger = logging.getLogger(__name__)

LANG_CACHE_TTL = 3600  # 1 hour

LANG_NAMES = {
    'uz': "O'zbek",
    'ru': 'Русский',
    'uz_kr': 'Ўзбек',
    'en': 'English',
}

TRANSLATIONS: dict[str, dict[str, str]] = {
    'uz': {
        'select_lang': "🌐 Tilni tanlang:",
        'lang_changed': "✅ Til o'zgartirildi!",
        'welcome_new': (
            "Salom! 👋\n\n"
            "Oscar Agro xizmatiga xush kelibsiz!\n\n"
            "Ro'yxatdan o'tish uchun bir necha savol:"
        ),
        'ask_name': "👤 To'liq ismingizni kiriting:",
        'ask_phone': "📞 Telefon raqamingizni kiriting yoki tugmani bosing:",
        'share_phone_btn': "📱 Raqamni ulashish",
        'invalid_name': "⚠️ Ism kamida 2 ta harf bo'lishi kerak. Qayta kiriting:",
        'invalid_phone': "⚠️ Noto'g'ri telefon raqami. Qayta kiriting:",
        'registered': "✅ Ro'yxatdan o'tish muvaffaqiyatli!\n\nXush kelibsiz, {name}! 🌱",
        'main_menu': "📋 Asosiy menyu:",
        'btn_orders': "📦 Buyurtmalar",
        'btn_profile': "👤 Profilim",
        'btn_faq': "❓ Savol-javoblar",
        'btn_contact': "📞 Aloqa",
        'btn_prices': "💰 Narxlar",
        'btn_back': "⬅️ Orqaga",
        'btn_cancel': "❌ Bekor qilish",
        'btn_confirm': "✅ Tasdiqlash",
        'btn_skip': "⏭ O'tkazib yuborish",
        'orders_menu': "📦 Buyurtmalar:",
        'btn_create_order': "➕ Yangi buyurtma",
        'btn_active_orders': "📋 Faol buyurtmalar",
        'btn_order_history': "📁 Tarix",
        'ask_problem': "🔴 Muammo yoki kasallikni batafsil yozing:",
        'problem_too_short': "⚠️ Kamida 5 ta harf kiriting.",
        'ask_address': "📍 Xizmat ko'rsatiladigan manzilni kiriting:",
        'address_too_short': "⚠️ Manzilni to'liqroq yozing (kamida 5 ta harf).",
        'ask_tree_count': "🌳 Daraxt sonini kiriting (raqam):",
        'invalid_tree_count': "⚠️ Faqat musbat raqam kiriting:",
        'order_summary': (
            "📋 <b>Buyurtma ma'lumotlari:</b>\n\n"
            "🔴 Muammo: {problem}\n"
            "📍 Manzil: {address}\n"
            "🌳 Daraxtlar: {tree_count}\n"
            "📞 Telefon: {phone}\n\n"
            "Tasdiqlaysizmi?"
        ),
        'order_sent': (
            "✅ Buyurtmangiz qabul qilindi!\n\n"
            "Sotuvchi tez orada siz bilan bog'lanadi.\n"
            "Buyurtma raqami: <b>#{order_id}</b>"
        ),
        'order_cancelled_msg': "❌ Buyurtma bekor qilindi.",
        'no_active_orders': "📭 Hozircha faol buyurtmalar yo'q.",
        'no_order_history': "📭 Buyurtmalar tarixi yo'q.",
        'ask_cancel_reason': "❌ Bekor qilish sababini yozing:",
        'ask_reject_reason': "❌ Rad etish sababini yozing:",
        'status_awaiting_sales': "⏳ Sotuvchi qaramoqda",
        'status_awaiting_client': "⏳ Sizning tasdiqingizni kutmoqda",
        'status_pending': "🕐 Tasdiqlash kutilmoqda",
        'status_approved': "✅ Tasdiqlandi",
        'status_in_progress': "🔄 Bajarilmoqda",
        'status_completed': "✅ Bajarildi",
        'status_cancelled': "❌ Bekor qilindi",
        'status_client_confirmed': "✅ Siz tasdiqlagan",
        'status_client_rejected': "❌ Siz rad etgan",
        'order_notification': (
            "📬 <b>Yangi buyurtma #{order_id}</b>\n\n"
            "Siz nomingizda buyurtma yaratildi:\n\n"
            "{order_card}\n\n"
            "Tasdiqlaysizmi?"
        ),
        'service_completed_msg': (
            "✅ <b>Xizmat bajarildi!</b>\n\n"
            "Buyurtma #{order_id}\n\n"
            "{treatment_summary}\n\n"
            "Xizmatni qabul qilasizmi?"
        ),
        'btn_accept_order': "✅ Qabul qilaman",
        'btn_reject_order': "❌ Rad etaman",
        'btn_confirm_service': "✅ Xizmat bajarildi",
        'btn_reject_service': "❌ Qabul qilmayman",
        'order_accepted_msg': "✅ Buyurtma qabul qilindi! Agronom tez orada keladi.",
        'order_rejected_msg': "❌ Buyurtma rad etildi.",
        'service_confirmed_msg': "✅ Xizmat tasdiqlandid! Rahmat! 🙏",
        'service_rejected_msg': "❌ Xizmat rad etildi. Agronom bilan bog'laniladi.",
        'ask_rating': "⭐ Xizmatni baholang:",
        'ask_comment': "💬 Izoh yozing (yoki o'tkazib yuborish):",
        'rated_msg': "✅ Baholangiz uchun rahmat! {stars}",
        'profile_view': (
            "👤 <b>Mening profilim</b>\n\n"
            "📛 Ism: {name}\n"
            "📞 Tel: {phone}\n"
            "🌐 Til: {lang}\n"
            "📅 Ro'yxat: {date}"
        ),
        'btn_edit_name': "✏️ Ismni o'zgartirish",
        'btn_edit_phone': "📞 Telefon o'zgartirish",
        'btn_change_lang': "🌐 Tilni o'zgartirish",
        'ask_new_name': "✏️ Yangi ismingizni kiriting:",
        'ask_new_phone': "📞 Yangi telefon raqamingizni kiriting:",
        'name_updated': "✅ Ism yangilandi: <b>{name}</b>",
        'phone_updated': "✅ Telefon yangilandi: <b>{phone}</b>",
        'contact_info': (
            "📞 <b>Bog'lanish ma'lumotlari</b>\n\n"
            "📱 Telefon: {phone}\n"
            "📍 Manzil: {address}\n"
            "{website_line}"
        ),
        'prices_info': "💰 <b>Narxlar</b>\n\n{prices}",
        'prices_not_set': "💰 Narxlar hozircha belgilanmagan. Aloqa uchun qo'ng'iroq qiling.",
        'faq_title': "❓ <b>Savol-javoblar</b>\n\nSavol tanlang:",
        'faq_empty': "❓ Hozircha FAQ yo'q.",
        'error_generic': "❌ Xatolik yuz berdi. Qayta urinib ko'ring.",
        'error_not_registered': "⚠️ Avval ro'yxatdan o'ting. /start bosing.",
        'unknown_command': "❓ Noma'lum buyruq. Menyu tugmalaridan foydalaning.",
        'retreatment_reminder': (
            "🔔 <b>Eslatma!</b>\n\n"
            "Buyurtma #{order_id} uchun qayta ishlov sanasi: <b>{date}</b>\n\n"
            "Agronom bilan bog'laning."
        ),
    },
    'ru': {
        'select_lang': "🌐 Выберите язык:",
        'lang_changed': "✅ Язык изменён!",
        'welcome_new': (
            "Привет! 👋\n\n"
            "Добро пожаловать в Oscar Agro!\n\n"
            "Для регистрации ответьте на несколько вопросов:"
        ),
        'ask_name': "👤 Введите ваше полное имя:",
        'ask_phone': "📞 Введите номер телефона или нажмите кнопку:",
        'share_phone_btn': "📱 Поделиться номером",
        'invalid_name': "⚠️ Имя должно содержать минимум 2 символа. Повторите:",
        'invalid_phone': "⚠️ Неверный номер телефона. Повторите:",
        'registered': "✅ Регистрация прошла успешно!\n\nДобро пожаловать, {name}! 🌱",
        'main_menu': "📋 Главное меню:",
        'btn_orders': "📦 Заказы",
        'btn_profile': "👤 Мой профиль",
        'btn_faq': "❓ Вопрос-ответ",
        'btn_contact': "📞 Контакты",
        'btn_prices': "💰 Цены",
        'btn_back': "⬅️ Назад",
        'btn_cancel': "❌ Отмена",
        'btn_confirm': "✅ Подтвердить",
        'btn_skip': "⏭ Пропустить",
        'orders_menu': "📦 Заказы:",
        'btn_create_order': "➕ Новый заказ",
        'btn_active_orders': "📋 Активные заказы",
        'btn_order_history': "📁 История",
        'ask_problem': "🔴 Опишите проблему подробно:",
        'problem_too_short': "⚠️ Введите минимум 5 символов.",
        'ask_address': "📍 Введите адрес для обслуживания:",
        'address_too_short': "⚠️ Введите адрес подробнее (минимум 5 символов).",
        'ask_tree_count': "🌳 Введите количество деревьев (число):",
        'invalid_tree_count': "⚠️ Введите положительное число:",
        'order_summary': (
            "📋 <b>Данные заказа:</b>\n\n"
            "🔴 Проблема: {problem}\n"
            "📍 Адрес: {address}\n"
            "🌳 Деревьев: {tree_count}\n"
            "📞 Телефон: {phone}\n\n"
            "Подтверждаете?"
        ),
        'order_sent': (
            "✅ Ваш заказ принят!\n\n"
            "Продавец свяжется с вами.\n"
            "Номер заказа: <b>#{order_id}</b>"
        ),
        'order_cancelled_msg': "❌ Заказ отменён.",
        'no_active_orders': "📭 Активных заказов нет.",
        'no_order_history': "📭 История заказов пуста.",
        'ask_cancel_reason': "❌ Укажите причину отмены:",
        'ask_reject_reason': "❌ Укажите причину отклонения:",
        'status_awaiting_sales': "⏳ Ожидает продавца",
        'status_awaiting_client': "⏳ Ожидает вашего подтверждения",
        'status_pending': "🕐 Ожидает подтверждения",
        'status_approved': "✅ Подтверждён",
        'status_in_progress': "🔄 Выполняется",
        'status_completed': "✅ Выполнен",
        'status_cancelled': "❌ Отменён",
        'status_client_confirmed': "✅ Вы подтвердили",
        'status_client_rejected': "❌ Вы отклонили",
        'order_notification': (
            "📬 <b>Новый заказ #{order_id}</b>\n\n"
            "Заказ создан на ваше имя:\n\n"
            "{order_card}\n\n"
            "Подтверждаете?"
        ),
        'service_completed_msg': (
            "✅ <b>Работа выполнена!</b>\n\n"
            "Заказ #{order_id}\n\n"
            "{treatment_summary}\n\n"
            "Принимаете работу?"
        ),
        'btn_accept_order': "✅ Принять",
        'btn_reject_order': "❌ Отклонить",
        'btn_confirm_service': "✅ Работа выполнена",
        'btn_reject_service': "❌ Не принимаю",
        'order_accepted_msg': "✅ Заказ принят! Агроном скоро прибудет.",
        'order_rejected_msg': "❌ Заказ отклонён.",
        'service_confirmed_msg': "✅ Работа принята! Спасибо! 🙏",
        'service_rejected_msg': "❌ Работа отклонена. Агроном будет уведомлён.",
        'ask_rating': "⭐ Оцените услугу:",
        'ask_comment': "💬 Оставьте комментарий (или пропустите):",
        'rated_msg': "✅ Спасибо за оценку! {stars}",
        'profile_view': (
            "👤 <b>Мой профиль</b>\n\n"
            "📛 Имя: {name}\n"
            "📞 Тел: {phone}\n"
            "🌐 Язык: {lang}\n"
            "📅 Регистрация: {date}"
        ),
        'btn_edit_name': "✏️ Изменить имя",
        'btn_edit_phone': "📞 Изменить телефон",
        'btn_change_lang': "🌐 Изменить язык",
        'ask_new_name': "✏️ Введите новое имя:",
        'ask_new_phone': "📞 Введите новый телефон:",
        'name_updated': "✅ Имя обновлено: <b>{name}</b>",
        'phone_updated': "✅ Телефон обновлён: <b>{phone}</b>",
        'contact_info': (
            "📞 <b>Контакты</b>\n\n"
            "📱 Телефон: {phone}\n"
            "📍 Адрес: {address}\n"
            "{website_line}"
        ),
        'prices_info': "💰 <b>Цены</b>\n\n{prices}",
        'prices_not_set': "💰 Цены пока не указаны. Позвоните нам.",
        'faq_title': "❓ <b>Вопрос-ответ</b>\n\nВыберите вопрос:",
        'faq_empty': "❓ FAQ пока пуст.",
        'error_generic': "❌ Произошла ошибка. Попробуйте снова.",
        'error_not_registered': "⚠️ Сначала пройдите регистрацию. Нажмите /start.",
        'unknown_command': "❓ Неизвестная команда. Используйте кнопки меню.",
        'retreatment_reminder': (
            "🔔 <b>Напоминание!</b>\n\n"
            "Для заказа #{order_id} запланирована повторная обработка: <b>{date}</b>\n\n"
            "Свяжитесь с агрономом."
        ),
    },
    'uz_kr': {
        'select_lang': "🌐 Тилни танланг:",
        'lang_changed': "✅ Тил ўзгартирилди!",
        'welcome_new': (
            "Салом! 👋\n\n"
            "Оскар Агро хизматига хуш келибсиз!\n\n"
            "Рўйхатдан ўтиш учун бир неча савол:"
        ),
        'ask_name': "👤 Тўлиқ исмингизни киринг:",
        'ask_phone': "📞 Телефон рақамингизни киринг ёки тугмани босинг:",
        'share_phone_btn': "📱 Рақамни улашиш",
        'invalid_name': "⚠️ Ism камида 2 та ҳарф бўлиши керак. Қайта киринг:",
        'invalid_phone': "⚠️ Нотўғри телефон рақами. Қайта киринг:",
        'registered': "✅ Рўйхатдан ўтиш муваффақиятли!\n\nХуш келибсиз, {name}! 🌱",
        'main_menu': "📋 Асосий меню:",
        'btn_orders': "📦 Буюртмалар",
        'btn_profile': "👤 Профилим",
        'btn_faq': "❓ Савол-жавоблар",
        'btn_contact': "📞 Алоқа",
        'btn_prices': "💰 Нархлар",
        'btn_back': "⬅️ Орқага",
        'btn_cancel': "❌ Бекор қилиш",
        'btn_confirm': "✅ Тасдиқлаш",
        'btn_skip': "⏭ Ўтказиб юбориш",
        'orders_menu': "📦 Буюртмалар:",
        'btn_create_order': "➕ Янги буюртма",
        'btn_active_orders': "📋 Фаол буюртмалар",
        'btn_order_history': "📁 Тарих",
        'ask_problem': "🔴 Муаммо ёки касалликни батафсил ёзинг:",
        'problem_too_short': "⚠️ Камида 5 та ҳарф киринг.",
        'ask_address': "📍 Хизмат кўрсатиладиган манзилни киринг:",
        'address_too_short': "⚠️ Манзилни тўлиқроқ ёзинг (камида 5 та ҳарф).",
        'ask_tree_count': "🌳 Дарахт сонини киринг (рақам):",
        'invalid_tree_count': "⚠️ Фақат мусбат рақам киринг:",
        'order_summary': (
            "📋 <b>Буюртма маълумотлари:</b>\n\n"
            "🔴 Муаммо: {problem}\n"
            "📍 Манзил: {address}\n"
            "🌳 Дарахтлар: {tree_count}\n"
            "📞 Телефон: {phone}\n\n"
            "Тасдиқлайсизми?"
        ),
        'order_sent': (
            "✅ Буюртмангиз қабул қилинди!\n\n"
            "Сотувчи тез орада сиз билан боғланади.\n"
            "Буюртма рақами: <b>#{order_id}</b>"
        ),
        'order_cancelled_msg': "❌ Буюртма бекор қилинди.",
        'no_active_orders': "📭 Ҳозирча фаол буюртмалар йўқ.",
        'no_order_history': "📭 Буюртмалар тарихи йўқ.",
        'ask_cancel_reason': "❌ Бекор қилиш сабабини ёзинг:",
        'ask_reject_reason': "❌ Рад этиш сабабини ёзинг:",
        'status_awaiting_sales': "⏳ Сотувчи қараяпти",
        'status_awaiting_client': "⏳ Сизнинг тасдиғингизни кутяпти",
        'status_pending': "🕐 Тасдиқлаш кутилмоқда",
        'status_approved': "✅ Тасдиқланди",
        'status_in_progress': "🔄 Бажарилмоқда",
        'status_completed': "✅ Бажарилди",
        'status_cancelled': "❌ Бекор қилинди",
        'status_client_confirmed': "✅ Сиз тасдиқладингиз",
        'status_client_rejected': "❌ Сиз рад этдингиз",
        'order_notification': (
            "📬 <b>Янги буюртма #{order_id}</b>\n\n"
            "Сиз номингизда буюртма яратилди:\n\n"
            "{order_card}\n\n"
            "Тасдиқлайсизми?"
        ),
        'service_completed_msg': (
            "✅ <b>Хизмат бажарилди!</b>\n\n"
            "Буюртма #{order_id}\n\n"
            "{treatment_summary}\n\n"
            "Хизматни қабул қиласизми?"
        ),
        'btn_accept_order': "✅ Қабул қиламан",
        'btn_reject_order': "❌ Рад этаман",
        'btn_confirm_service': "✅ Хизмат бажарилди",
        'btn_reject_service': "❌ Қабул қилмайман",
        'order_accepted_msg': "✅ Буюртма қабул қилинди! Агроном тез орада келади.",
        'order_rejected_msg': "❌ Буюртма рад этилди.",
        'service_confirmed_msg': "✅ Хизмат тасдиқланди! Раҳмат! 🙏",
        'service_rejected_msg': "❌ Хизмат рад этилди. Агроном бilan боғланилади.",
        'ask_rating': "⭐ Хизматни баҳоланг:",
        'ask_comment': "💬 Изоҳ ёзинг (ёки ўтказиб юборинг):",
        'rated_msg': "✅ Баҳолагингиз учун раҳмат! {stars}",
        'profile_view': (
            "👤 <b>Менинг профилим</b>\n\n"
            "📛 Ism: {name}\n"
            "📞 Тел: {phone}\n"
            "🌐 Тил: {lang}\n"
            "📅 Рўйхат: {date}"
        ),
        'btn_edit_name': "✏️ Исмни ўзгартириш",
        'btn_edit_phone': "📞 Телефон ўзгартириш",
        'btn_change_lang': "🌐 Тилни ўзгартириш",
        'ask_new_name': "✏️ Янги исмингизни киринг:",
        'ask_new_phone': "📞 Янги телефон рақамингизни киринг:",
        'name_updated': "✅ Ism янгиланди: <b>{name}</b>",
        'phone_updated': "✅ Телефон янгиланди: <b>{phone}</b>",
        'contact_info': (
            "📞 <b>Боғланиш маълумотлари</b>\n\n"
            "📱 Телефон: {phone}\n"
            "📍 Манзил: {address}\n"
            "{website_line}"
        ),
        'prices_info': "💰 <b>Нархлар</b>\n\n{prices}",
        'prices_not_set': "💰 Нархлар ҳозирча белгиланмаган. Алоқа учун қўнғироқ қилинг.",
        'faq_title': "❓ <b>Савол-жавоблар</b>\n\nСавол танланг:",
        'faq_empty': "❓ Ҳозирча FAQ йўқ.",
        'error_generic': "❌ Хатолик юз берди. Қайта уриниб кўринг.",
        'error_not_registered': "⚠️ Аввал рўйхатдан ўтинг. /start босинг.",
        'unknown_command': "❓ Номаълум буйруқ. Меню тугмаларидан фойдаланинг.",
        'retreatment_reminder': (
            "🔔 <b>Эслатма!</b>\n\n"
            "Буюртма #{order_id} учун қайта ишлов санаси: <b>{date}</b>\n\n"
            "Агроном билан боғланинг."
        ),
    },
    'en': {
        'select_lang': "🌐 Select language:",
        'lang_changed': "✅ Language changed!",
        'welcome_new': (
            "Hello! 👋\n\n"
            "Welcome to Oscar Agro!\n\n"
            "Please answer a few questions to register:"
        ),
        'ask_name': "👤 Enter your full name:",
        'ask_phone': "📞 Enter your phone number or press the button:",
        'share_phone_btn': "📱 Share phone number",
        'invalid_name': "⚠️ Name must be at least 2 characters. Try again:",
        'invalid_phone': "⚠️ Invalid phone number. Try again:",
        'registered': "✅ Registration successful!\n\nWelcome, {name}! 🌱",
        'main_menu': "📋 Main menu:",
        'btn_orders': "📦 Orders",
        'btn_profile': "👤 My Profile",
        'btn_faq': "❓ FAQ",
        'btn_contact': "📞 Contact",
        'btn_prices': "💰 Prices",
        'btn_back': "⬅️ Back",
        'btn_cancel': "❌ Cancel",
        'btn_confirm': "✅ Confirm",
        'btn_skip': "⏭ Skip",
        'orders_menu': "📦 Orders:",
        'btn_create_order': "➕ New Order",
        'btn_active_orders': "📋 Active Orders",
        'btn_order_history': "📁 History",
        'ask_problem': "🔴 Describe the problem in detail:",
        'problem_too_short': "⚠️ Enter at least 5 characters.",
        'ask_address': "📍 Enter the service address:",
        'address_too_short': "⚠️ Please be more specific (at least 5 characters).",
        'ask_tree_count': "🌳 Enter number of trees:",
        'invalid_tree_count': "⚠️ Enter a positive number:",
        'order_summary': (
            "📋 <b>Order Details:</b>\n\n"
            "🔴 Problem: {problem}\n"
            "📍 Address: {address}\n"
            "🌳 Trees: {tree_count}\n"
            "📞 Phone: {phone}\n\n"
            "Confirm?"
        ),
        'order_sent': (
            "✅ Your order has been received!\n\n"
            "A sales manager will contact you soon.\n"
            "Order ID: <b>#{order_id}</b>"
        ),
        'order_cancelled_msg': "❌ Order cancelled.",
        'no_active_orders': "📭 No active orders.",
        'no_order_history': "📭 No order history.",
        'ask_cancel_reason': "❌ Please state the reason for cancellation:",
        'ask_reject_reason': "❌ Please state the reason for rejection:",
        'status_awaiting_sales': "⏳ Awaiting sales manager",
        'status_awaiting_client': "⏳ Awaiting your confirmation",
        'status_pending': "🕐 Awaiting approval",
        'status_approved': "✅ Approved",
        'status_in_progress': "🔄 In progress",
        'status_completed': "✅ Completed",
        'status_cancelled': "❌ Cancelled",
        'status_client_confirmed': "✅ You confirmed",
        'status_client_rejected': "❌ You rejected",
        'order_notification': (
            "📬 <b>New Order #{order_id}</b>\n\n"
            "An order has been created for you:\n\n"
            "{order_card}\n\n"
            "Do you confirm?"
        ),
        'service_completed_msg': (
            "✅ <b>Service Completed!</b>\n\n"
            "Order #{order_id}\n\n"
            "{treatment_summary}\n\n"
            "Do you accept the work?"
        ),
        'btn_accept_order': "✅ Accept",
        'btn_reject_order': "❌ Reject",
        'btn_confirm_service': "✅ Service done",
        'btn_reject_service': "❌ Not accepting",
        'order_accepted_msg': "✅ Order accepted! The agronomist will arrive soon.",
        'order_rejected_msg': "❌ Order rejected.",
        'service_confirmed_msg': "✅ Service confirmed! Thank you! 🙏",
        'service_rejected_msg': "❌ Service rejected. The agronomist will be notified.",
        'ask_rating': "⭐ Rate the service:",
        'ask_comment': "💬 Leave a comment (or skip):",
        'rated_msg': "✅ Thank you for your rating! {stars}",
        'profile_view': (
            "👤 <b>My Profile</b>\n\n"
            "📛 Name: {name}\n"
            "📞 Phone: {phone}\n"
            "🌐 Language: {lang}\n"
            "📅 Registered: {date}"
        ),
        'btn_edit_name': "✏️ Change name",
        'btn_edit_phone': "📞 Change phone",
        'btn_change_lang': "🌐 Change language",
        'ask_new_name': "✏️ Enter new name:",
        'ask_new_phone': "📞 Enter new phone number:",
        'name_updated': "✅ Name updated: <b>{name}</b>",
        'phone_updated': "✅ Phone updated: <b>{phone}</b>",
        'contact_info': (
            "📞 <b>Contact Information</b>\n\n"
            "📱 Phone: {phone}\n"
            "📍 Address: {address}\n"
            "{website_line}"
        ),
        'prices_info': "💰 <b>Prices</b>\n\n{prices}",
        'prices_not_set': "💰 Prices not set yet. Please call us.",
        'faq_title': "❓ <b>FAQ</b>\n\nSelect a question:",
        'faq_empty': "❓ No FAQ items yet.",
        'error_generic': "❌ An error occurred. Please try again.",
        'error_not_registered': "⚠️ Please register first. Press /start.",
        'unknown_command': "❓ Unknown command. Please use the menu buttons.",
        'retreatment_reminder': (
            "🔔 <b>Reminder!</b>\n\n"
            "Re-treatment is scheduled for Order #{order_id}: <b>{date}</b>\n\n"
            "Please contact your agronomist."
        ),
    },
}


def t(key: str, lang: str = 'uz', **kwargs) -> str:
    """Translate key to the given language with optional format kwargs."""
    lang = lang if lang in TRANSLATIONS else 'uz'
    text = TRANSLATIONS[lang].get(key) or TRANSLATIONS['uz'].get(key) or key
    if kwargs:
        try:
            return text.format(**kwargs)
        except (KeyError, IndexError):
            return text
    return text


async def get_user_lang(telegram_id: int) -> str:
    """Get user language from Redis cache (fast path) or DB (cold path)."""
    cache_key = f"user_lang:{telegram_id}"
    cached = await redis.get(cache_key)
    if cached:
        return cached

    try:
        from apps.accounts.models import TelegramUser
        user = await TelegramUser.objects.aget(telegram_id=telegram_id)
        lang = user.language or 'uz'
    except Exception:
        lang = 'uz'

    await redis.setex(cache_key, LANG_CACHE_TTL, lang)
    return lang


async def set_user_lang(telegram_id: int, lang: str) -> None:
    """Update user language in DB and invalidate cache."""
    from apps.accounts.models import TelegramUser
    await TelegramUser.objects.filter(telegram_id=telegram_id).aupdate(language=lang)
    await redis.setex(f"user_lang:{telegram_id}", LANG_CACHE_TTL, lang)
