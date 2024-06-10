import asyncio

from telebot.async_telebot import AsyncTeleBot
from telebot.types import Message, CallbackQuery, ReplyKeyboardRemove

from models.app import App


def filter_message(message: Message):
    if str(message.chat.id) in App()['config']['bot']['administrators']['users']:
        return False
    if message.text in ['/start', '/help', '/profile', '/pay', '/rating']:
        return False
    return True


def send_error_logs(handler_func):
    async def wrapper(message: Message, bot: AsyncTeleBot):
        try:
            response_message = await handler_func(message, bot)
        except Exception as e:
            error_text = f"Бот упал с ошибкой! 👇\n\n{e}"
            print(error_text)

            if "VOICE_MESSAGES_FORBIDDEN" in str(e):
                await App().Dao.user.update({"user_id": message.from_user.id, 'bot_state': 'default', 'messages': []})
                voice_alert = ('Для общения со мной необходимо, чтобы у тебя были разрешены входящие '
                               'голосовые сообщения, а сейчас они запрещены и я не могу начать с тобой практику 😢.'
                               'Разреши входящие гс и попробуй заново начать нашу практику /start 🙏')
                await bot.send_message(
                    text=voice_alert, chat_id=message.chat.id, reply_markup=ReplyKeyboardRemove()
                )

            else:
                await bot.send_message(
                    text="Возникла ошибка в работе бота, попробуйте еще раз немного позже.\n"
                         "Сообщения об ошибках приходят разработчикам и они сразу принимаются за их исправление."
                         "При необходимости Вы можете обратиться в техподдержку.\n"
                         "Написать в поддержку — @HQmupbasic. Режим работы: 08:00 - 23:00 по мск.",
                    chat_id=message.chat.id
                )
                for admin_id in App()['config']['bot']['administrators']['users']:
                    admin_id = int(admin_id)
                    await bot.send_message(text=error_text, chat_id=admin_id)
                    raise e

        return response_message

    return wrapper


def send_bot_using_logs(handler_func):
    """
    Для работы необходимо, чтобы handler_func возвращал объект Message, отправленный ботом.
    """

    async def wrapper(message: Message, bot: AsyncTeleBot):
        response_message = await handler_func(message, bot)
        if isinstance(message, CallbackQuery):
            message = message.message
        if not filter_message(message):
            return response_message
        if message.chat.id in App()['config']['bot']['administrators']['users']:
            return response_message
        try:
            for admin_id in App()['config']['bot']['administrators']['users']:
                admin_id = int(admin_id)
                await bot.send_message(
                    text=f"Вот сообщение пользователя @{message.chat.username} (id {message.chat.id})👇",
                    chat_id=admin_id)
                await bot.forward_message(admin_id, message.chat.id, message.message_id)
                await bot.forward_message(admin_id, message.chat.id, response_message.message_id)
            await asyncio.sleep(1)

        except Exception as e:
            print(f'Баг!!!\n\n{e}')

        return response_message

    return wrapper
