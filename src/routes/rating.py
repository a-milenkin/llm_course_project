import datetime

from telebot.async_telebot import AsyncTeleBot
from telebot.types import Message

from models.app import App

def prefix(n):
    if n == 1:
        return "🥇"
    elif n == 2:
        return "🥈"
    elif n == 3:
        return "🥉"
    else:
        return f"  {n}. "

month_number_to_rus = {
    1: "января",
    2: "февраля",
    3: "марта",
    4: "апреля",
    5: "мая",
    6: "июня",
    7: "июля",
    8: "августа",
    9: "сентября",
    10: "октября",
    11: "ноября",
    12: "декабря"
}


async def get_rating(message: Message, bot: AsyncTeleBot):
    if App().Tasks.get(message.from_user.id):
        App().Tasks[message.from_user.id].cancel()
    today = datetime.date.today()
    last_monday = today - datetime.timedelta(days=today.weekday())
    users_top, user_rank, user_talk_time = await App().Dao.user.get_users_top(message.from_user.id)
    rating_text = f"🏆Топ 10 студентов за эту неделю (c {last_monday.day} {month_number_to_rus[last_monday.month]}):\n\n"
    for i, user in enumerate(users_top):
        rating_text += f"{prefix(i+1)} ***{str(user['name'])[3:]} - {user['talk_time']} мин.\n"
    rating_text += ('--------------------------------------\n'
                       f'{user_rank}. {message.from_user.username} - {await App().Dao.user.get_talk_time(message.from_user.id, interval="week")} мин.')
    rating_text = f'{rating_text}\n\nПосмотри свою более подробную статистику /profile'
    await bot.send_message(text=rating_text, chat_id=message.chat.id)
