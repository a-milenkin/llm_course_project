import datetime

import numpy as np
from telebot.async_telebot import AsyncTeleBot
from telebot.types import Message, CallbackQuery

from models.app import App
from utils.functions import make_string_good_for_markdown
from utils.structures import UserData


async def send_profile(message: Message, bot: AsyncTeleBot):
    """
    Функция для вызова статистики юзера
    """

    data = await App().Dao.user.find_by_user_id(message.chat.id)
    user = UserData(**data)
    if App().Tasks.get(user.user_id):
        App().Tasks[user.user_id].cancel()

    today_duration = await App().Dao.user.get_talk_time(message.from_user.id, interval="day", role='user')
    week_duration = await App().Dao.user.get_talk_time(message.from_user.id, interval="week", role='user')
    total_duration = await App().Dao.user.get_talk_time(message.from_user.id, interval="total", role='user')

    total_listeaning = await App().Dao.user.get_talk_time(message.from_user.id, interval="total", role='assistant')

    days_training = await App().Dao.user.get_general_bottle_days(interval='total', user_id=message.from_user.id)
    days_training = list(days_training.items())[0][0]

    voice_duration = total_duration
    voice_duration = 100 if voice_duration > 100 else voice_duration
    voice_duration = round(voice_duration, 2)
    progress = int(voice_duration // 10) + 1
    sprint_line = '✅' * progress + '⬜' * (9 - progress)

    day2emoji = {'mon': 0, 'tue': 1, 'wen': 2, 'thu': 3, 'fri': 4, 'sat': 5, 'sun': 6}
    week_activity_dict = await App().Dao.user.get_usage_by_weekday(message.from_user.id)
    dayofweek = int(datetime.datetime.today().weekday())

    # Модифицируем словать так, чтоб убрать из него значения из будущего
    for k, v in day2emoji.items():
        if v < dayofweek:
            day2emoji[k] = '✅' if week_activity_dict[k]['talk_time'] > 0 else '❌'
            val = week_activity_dict[k]['talk_time']
            week_activity_dict[k]['talk_time'] = f'{val} мин'
        elif v == dayofweek:
            day2emoji[k] = '✅' if week_activity_dict[k]['talk_time'] > 0 else '🤔'
            val = week_activity_dict[k]['talk_time']
            week_activity_dict[k]['talk_time'] = f'{val} мин' if val > 0 else ''
        else:
            week_activity_dict[k]['talk_time'] = ''
            day2emoji[k] = '⌛'

    time2emoji = {1: '🥉', 5: '🥈', 10: '🥇', 13: '🏅',
                  15: '🦄', 20: '🚀', 30: '🏅', 50: '🧠', 75: '🐲',
                  100: '🎖', 200: '👨‍🚀', 300: '🏆', 500: '🏵', 1000: '🤯',
                  }

    today_duration = round(today_duration, 4)

    level_text = ''
    for k, emoji in time2emoji.items():
        if total_duration >= k:
            level_num = int(np.log(total_duration * 10 + 1) + 1)
            level_text = f'Уровень {level_num}{emoji}'

    motive_text = ' - позанимайся сегодня!'
    profile_message = f"""
Личный кабинет {f'@{message.from_user.username}' if message.from_user.username != None else ''}

            Ваша цель на день: 5 мин.🎯 
            🎙 Вы наговорили 🚀:
            - Сегодня: {today_duration} мин.
            - За неделю: {week_duration} мин.
            - Всего: {total_duration} мин. -> {level_text}
            👂 Вы наслушали {int(total_listeaning)} мин. английской речи
            💪 Вы занимались {days_training} дней

            До дневной нормы осталось всего {max([5 - today_duration, 0])} мин.! 

            🏃‍♂️ Пробеги марафон по говорению!
            {sprint_line} 100 мин
            {voice_duration} мин, {round(voice_duration)}%

            📈 Дни, в которые ты общался:
            {day2emoji['mon']} Monday {motive_text if day2emoji['mon'] == '🤔' else ''} {week_activity_dict['mon']['talk_time']} 
            {day2emoji['tue']} Tuesday {motive_text if day2emoji['tue'] == '🤔' else ''} {week_activity_dict['tue']['talk_time']} 
            {day2emoji['wen']} Wednesday {motive_text if day2emoji['wen'] == '🤔' else ''} {week_activity_dict['wen']['talk_time']} 
            {day2emoji['thu']} Thursday {motive_text if day2emoji['thu'] == '🤔' else ''} {week_activity_dict['thu']['talk_time']} 
            {day2emoji['fri']} Friday {motive_text if day2emoji['fri'] == '🤔' else ''} {week_activity_dict['fri']['talk_time']} 
            {day2emoji['sat']} Saturday {motive_text if day2emoji['sat'] == '🤔' else ''} {week_activity_dict['sat']['talk_time']} 
            {day2emoji['sun']} Sunday {motive_text if day2emoji['sun'] == '🤔' else ''} {week_activity_dict['sun']['talk_time']} 
            """.replace('            ', '')  # ❌

    escapt_list = ['_', '[', ']', '(', ')', '~', '>', '#', '+', '-', '=', '|', '{', '}', '.', '!']
    profile_message = await make_string_good_for_markdown(profile_message, es_list=escapt_list)

    await bot.send_message(text=profile_message,
                           chat_id=message.chat.id,
                           parse_mode='MarkdownV2')

    return profile_message


async def send_users_profile(message: Message, bot: AsyncTeleBot):
    if message.chat.id not in App()['config']['bot']['administrators']['users']:
        return None

    author = message.chat.id
    user_id = int(message.text.split('@')[1])

    message.chat.id = user_id
    message.from_user.id = user_id

    # data = await App().Dao.user.find_by_user_id(user_id)
    # user = UserData(**data)
    # message.from_user = user

    profile_message = await send_profile(message, bot)
    await bot.send_message(text=profile_message, chat_id=author, parse_mode='MarkdownV2')


async def profile_back(call: CallbackQuery, bot: AsyncTeleBot):
    if App().Tasks.get(call.message.from_user.id):
        App().Tasks[call.message.from_user.id].cancel()

    txt = 'Жду твое голосовое! Давай попробуем пообщаться 👇'
    bot_message = await bot.send_message(text=txt, chat_id=call.from_user.id)
