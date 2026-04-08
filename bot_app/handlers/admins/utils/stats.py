from apps.accounts.models import TelegramUser
from apps.orders.models import Order, Feedback, TreatmentDetails
from ....core.loader import bot


async def _send_statistics(chat_id: int) -> None:
    from django.db.models import Count, Avg
    from asgiref.sync import sync_to_async

    @sync_to_async
    def _fetch():
        total = Order.objects.count()
        by_status = dict(Order.objects.values_list('status').annotate(c=Count('id')))
        completed = by_status.get('completed', 0) + by_status.get('client_confirmed', 0)
        cancelled = by_status.get('cancelled', 0) + by_status.get('client_rejected', 0)
        pending = by_status.get('pending', 0)
        approved = by_status.get('approved', 0)
        in_prog = by_status.get('in_progress', 0)
        avg_rating = Feedback.objects.aggregate(avg=Avg('rating'))['avg'] or 0
        retreatments = TreatmentDetails.objects.filter(re_treatment_needed=True).count()
        total_managers = TelegramUser.objects.filter(role='sales_manager', is_active=True).count()
        total_agros = TelegramUser.objects.filter(role='agronomist', is_active=True).count()
        total_clients = TelegramUser.objects.filter(role='client', is_active=True).count()
        return (total, completed, cancelled, pending, approved, in_prog,
                avg_rating, retreatments, total_managers, total_agros, total_clients)

    (total, completed, cancelled, pending, approved, in_prog,
     avg_rating, retreatments, total_managers, total_agros, total_clients) = await _fetch()

    text = (
        f"📊 <b>Statistika</b>\n\n"
        f"<b>Buyurtmalar:</b>\n"
        f"  Jami: {total}\n"
        f"  Yangi: {pending}\n"
        f"  Tasdiqlangan: {approved}\n"
        f"  Bajarilmoqda: {in_prog}\n"
        f"  Yakunlangan: {completed}\n"
        f"  Bekor qilingan: {cancelled}\n"
        f"  Qayta ishlov: {retreatments}\n\n"
        f"<b>Foydalanuvchilar:</b>\n"
        f"  Sotuvchilar: {total_managers}\n"
        f"  Agronomlar: {total_agros}\n"
        f"  Mijozlar: {total_clients}\n\n"
        f"<b>O'rtacha reyting:</b> {'⭐' * round(avg_rating)} ({avg_rating:.1f})"
    )
    await bot.send_message(chat_id, text)