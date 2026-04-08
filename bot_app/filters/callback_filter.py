from telebot.asyncio_filters import AdvancedCustomFilter
from telebot.callback_data import CallbackDataFilter


class CallFilter(AdvancedCustomFilter):

    key = 'call'

    async def check(self, message, call):

        if message.data == call:
            return True
        else:
            return False

class F(AdvancedCustomFilter):
    """Universal filter for all CallbackData factories.

    Usage:
        bot.add_custom_filter(F())

        @bot.callback_query_handler(func=None, config=rate_factory.filter())
        async def handler(call): ...
    """
    key = "config"

    async def check(self, call, config: CallbackDataFilter) -> bool:
        return config.check(query=call)