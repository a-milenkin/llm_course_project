import asyncio

from telebot.async_telebot import AsyncTeleBot
from telebot.types import Message, InlineKeyboardMarkup, InlineKeyboardButton

from models.app import App
from routes.texts import reminder_text
import routes
from utils.callback_factories import StuckReminderCallbackData, DailyReminderCallbackData
from utils.structures import UserData


async def setup_tasks(app):
    app.Tasks = dict()


async def send_stuck_reminder(message: Message, bot: AsyncTeleBot, delay=220):
    try:
        data = await App().Dao.user.find_by_user_id(message.from_user.id)
        user = UserData(**data)
        await asyncio.sleep(delay)
        print(user)
        if user.stuck_reminder_enabled:
            if user.bot_state != 'conversation':
                return
            markup = InlineKeyboardMarkup()
            markup.add(
                InlineKeyboardButton(
                    f"Отключить напоминания",
                    callback_data=StuckReminderCallbackData.new(stuck_reminder_enable=False)
                )
            )
            await bot.send_message(
                chat_id=message.chat.id,
                text=reminder_text,
                reply_markup=markup
            )
    except asyncio.CancelledError:
        return

async def send_daily_reminder(user_id, text):
    try:
        data = await App().Dao.user.find_by_user_id(user_id)
        user = UserData(**data)

        markup = InlineKeyboardMarkup()
        markup.add(
            InlineKeyboardButton(
                f"Отключить напоминания",
                callback_data=DailyReminderCallbackData.new(action="disable_reminders")
            )
        )
        markup.add(
            InlineKeyboardButton(
                f"🏋️ Начать тренировку",
                callback_data=DailyReminderCallbackData.new(action="start_training")
            )
        )
        return await App().Bot.send_message(
            chat_id=user_id,
            text=text,
            reply_markup=markup
        )
    except asyncio.CancelledError:
        return

async def daily_reminder_callback_handler(call, bot):
    callback_data = DailyReminderCallbackData.parse_and_destroy(call.data)
    if callback_data["action"] == "disable_reminders":
        await App().Dao.user.update({
                    "user_id": call.from_user.id,
                    "reminders": {
                        "days": [],
                        "time": null,
                        "has_been_requested_before": True,
                        "last_reminder_sent": None
                    }
                    })
        await bot.send_message(
            chat_id=call.from_user.id,
            text="<b>Напоминания отключены</b>",
            parse_mode="HTML"
        )
    elif callback_data["action"] == "start_training":
        call.message.from_user.id = call.message.chat.id # to use this message later for send_welcome
        await App().Dao.user.update({
                    "user_id": call.from_user.id,
                    "bot_state": "conversation"
                    })
        await routes.avatar.send_welcome(call.message, bot)

async def stuck_reminder_callback_handler(call, bot):
    print("hello from stuck_reminder_callback_handler")
    callback_data = StuckReminderCallbackData.parse_and_destroy(call.data)
    print(callback_data)
    if callback_data["stuck_reminder_enable"] == False:
        await App().Dao.user.update({
                    "user_id": call.from_user.id,
                    "stuck_reminder_enabled": False
                    })
        await bot.send_message(
            chat_id=call.from_user.id,
            text="<b>Напоминания отключены</b>",
            parse_mode="HTML"
        )