import asyncio
import base64
import dataclasses
import datetime
import glob
import io
import logging
# from copy import copy
import numpy as np

import jsonpickle
from PIL import Image
# from telebot import types
from telebot.async_telebot import AsyncTeleBot
# from telebot.asyncio_helper import ApiTelegramException
# from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
# from telebot.types import InputMediaPhoto
from telebot.types import Message, CallbackQuery

from models.app import App
# from routes.english_tips import words_4_using
# from routes.email_request import EMAIL_REQUEST, email_request_route
# from routes.payments import out_of_free_generations
# from utils.functions import pop_from_dict
from utils.send_to_admin import send_error_logs, send_bot_using_logs
# from utils.callback_factories import SuggestCallbackData
# from utils.gpt import get_init_ans, voice_chat, text_to_voice_with_duration
# from utils.markups import create_conv_reply_markup, create_start_suggests_reply_markup, create_suggests_markup
# from utils.schedule import send_stuck_reminder
# from utils.structures import UserData
# from utils.avatar import truncate_length

# from pydub import AudioSegment


# def truncate_length(messages):
#     """
#     We want to store all messages
#     """
#     return messages

@send_error_logs
async def send_metrics(message: Message, bot: AsyncTeleBot):

        if message.chat.id not in App()['config']['bot']['administrators']['users']:
                return None

        '''
        тайная функция, возвращающая админам метрики
        '''

        today_users = await App().Dao.user.get_new_users_by_interval(interval="day")
        week_users = await App().Dao.user.get_new_users_by_interval(interval="week")
        month_users = await App().Dao.user.get_new_users_by_interval(interval="month")
        days_30_users = await App().Dao.user.get_new_users_by_interval(interval="30days")
        total_users = await App().Dao.user.get_new_users_by_interval(interval="total")

        try: day_duration = await App().Dao.user.get_users_speaking_duration(interval="day")
        except: day_duration = {'talk_time_sum': 0, 'talk_time_avg' : 0, "talk_time_bot_sum" : 0}
        week_duration = await App().Dao.user.get_users_speaking_duration(interval="week")
        month_duration = await App().Dao.user.get_users_speaking_duration(interval="month")
        total_duration = await App().Dao.user.get_users_speaking_duration(interval="total")

        day_payments = await App().Dao.payments.get_new_payments_by_interval(interval="day")
        total_payments = await App().Dao.payments.get_new_payments_by_interval(interval="total")

        campaign_stats = await App().Dao.user.get_campaign_stats()
        campaign_stats_list = [f'{k} -> {v}' for k,v in campaign_stats.items()]
        campaign_stats_string = '\n'.join(campaign_stats_list)

        # Количество активных дней
        bottle = await App().Dao.user.get_general_bottle_days(interval="total") 
        bottle_string = ''
        for n_days in range(60):
                if n_days in bottle.keys():
                        bottle_string += f'дней {n_days} : {bottle[n_days]} человек\n'

        # Количество активных дней
        voices_dict, median_voice, users_sum = await App().Dao.user.get_general_funnel_voices(interval="total")  
        voices_string = ''
        voices_dict= dict(sorted(voices_dict.items(), key=lambda item: item[0]))
        for voice_num, n_people in voices_dict.items():
                if voice_num <= 10 or n_people % 10 == 0: # Убираем часть, чтоб не частить
                        perc = 100*((users_sum - n_people)/users_sum)
                        if perc > 5: perc = f'{int(perc)}%'
                        elif perc > 1: perc = f'{round(perc, 1)}%'
                        elif perc > 1/5: perc = f'{round(perc, 2)}%'
                        else: perc = f'{users_sum - n_people}'
                        voices_string += f'gte {voice_num} голосовых : {perc} чел \n'

        profile_message = f"""
                Метрики тренажера

                🆕🧑‍💻 Новые говоруны:
                Сегодня: {today_users} 
                За эту неделю: {week_users} 
                За этот месяц: {month_users}
                За 30 дней: {days_30_users}  
                Всего: {total_users}

                💃 Подписок:
                💸 Сегодня: {day_payments}
                💰 Всего: {total_payments}

                🦐 Статистика по кампаниям:
                {campaign_stats_string}
                
                🧑‍💻🚀 Наговорили:
                За сегодня {round(day_duration['talk_time_sum'])} мин.
                За эту неделю {round(week_duration['talk_time_sum']/60)} час
                За этот месяц {round(month_duration['talk_time_sum']/60)} час
                За все время {round(total_duration['talk_time_sum']/60)} час

                🤖 Наговорил бот:
                За сегодня {round(day_duration['talk_time_bot_sum'])} мин.
                За эту неделю {round(week_duration['talk_time_bot_sum']/60)} час
                За все время {round(total_duration['talk_time_bot_sum']/60)} час

                🗣 Средняя длина голосовой {round(total_duration['talk_time_avg'])} сек.
                🤖 Средняя длина голосовой {round(total_duration['talk_time_bot_avg'])} сек.
                🎡 Медиана голосовых {median_voice} (без нуля)

                🛝 Воронка активных дней:
                {bottle_string}
                🎢 Воронка отправленных голосовых:
                {voices_string}
                """.replace('                ', '') # ❌ 🎡🎢

        

    # Доступно {generation_day_limit} 💌 сообщений в день {f"(сегодня осталось {(await routes_avatar.daily_limit(user)) - user.today_generations})"}
            
#     escapt_list = ['_', '[', ']', '(', ')', '~', '>', '#', '+', '-', '=', '|', '{', '}', '.', '!']
#     profile_message = await make_string_good_for_markdown(profile_message, es_list=escapt_list)

        # await App().Dao.user.get_user_csv()  
        
        await bot.send_message(text=profile_message,
                                chat_id=message.chat.id,
                                #    reply_markup=markup,
                                #    parse_mode='MarkdownV2'
                                )
        


    # return voice_message