from django.urls import path
from .views import MainBotWebhookView, ClientBotWebhookView

urlpatterns = [
    path('main/webhook/<str:token>/', MainBotWebhookView.as_view(), name='main_bot_webhook'),
    path('client/webhook/<str:token>/', ClientBotWebhookView.as_view(), name='client_bot_webhook'),
]
