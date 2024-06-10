import asyncio
import base64
import dataclasses
import datetime
import glob
import io
import logging
from copy import copy
import numpy as np

import jsonpickle
from PIL import Image
# from telebot import types
from telebot.async_telebot import AsyncTeleBot
# from telebot.asyncio_helper import ApiTelegramException
# from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
# from telebot.types import InputMediaPhoto
from telebot.types import Message, CallbackQuery

# import copy 

from models.app import App
# from routes.english_tips import words_4_using
# from routes.email_request import EMAIL_REQUEST, email_request_route
# from routes.payments import out_of_free_generations
# from utils.functions import pop_from_dict
from utils.send_to_admin import send_error_logs, send_bot_using_logs
# from utils.callback_factories import SuggestCallbackData
from utils.gpt import voice_chat, text_to_voice_with_duration
# from utils.markups import create_conv_reply_markup, create_start_suggests_reply_markup, create_suggests_markup
# from utils.schedule import send_stuck_reminder
# from utils.structures import UserData
# from utils.avatar import truncate_length

# from pydub import AudioSegment

video_text = '''
Давайте немного пообщаемся. Как вы обычно справляетесь со стрессом?

Let's practice our English for a few minutes. How do you handle with stress?
'''

voice_text = '''
Привет, на связи команда разработки тренажера 🇬🇧 Speakadora AI 👩‍🏫. Рады, что вы с нами и часто тренируетесь!

Мы хотим понять, чего не хватает главным пользователям нашего тренажера? Что улучшить?

Если вам хочется чтобы Speakadora стала еще лучше, то напишите нам в поддержку @Speakadora- чего вам сейчас не хватает? Мы добавим!

По результатам обратной связи мы добавим новые полезности и режимы. За лучший подробный фидбек - мы подарим премиум на месяц!
'''

# import copy

@send_error_logs
async def send_msg(message: Message, bot: AsyncTeleBot):
        
        
        '''тайная функция, делает рассылку'''

        if message.chat.id not in App()['config']['bot']['administrators']['users']:
                return None


#         Задание на аудирование. Что он говорит?



        text = '''🔔 Yesterday is history, but today is a fresh opportunity to learn something new!\n\nHow's your weekend going?\nDid you rest or work this weekend??
        '''.replace('                ', '').strip() 

        users_ids = await App().Dao.user.find_known_users_ids()
        # users_ids, user_rank, user_talk_time = await App().Dao.user.get_users_top(message.from_user.id, top_n = 2000)
        # print(users_ids)
        # users_ids = [5857440845, 6669816639]
        _users_ids = App()['config']['bot']['administrators']['users']

        # path = '/src/assets/materials2send/Titanic_1000_knives.mp4'
        # voice_bytesio, voice_duration = await text_to_voice_with_duration(voice_text)
        # contents = voice_bytesio.read()
        
        send_times, fail_times = 0, 0
        
        for users_id in users_ids:
            
            # path = '/src/assets/materials2send/Titanic_1000_knives.mp4'
            # voice_bytesio, _ = await text_to_voice_with_duration(voice_text)
            
            # photo_path = '/src/assets/materials2send/that.jpg'
            # # vidos = open(path, 'rb')
                
            # send_photo = None
            # with open(photo_path, "rb") as f:
            #     send_photo = f.read()
               
            # user_id = user['id']
            # user_talk_time = user['talk_time']

            # users_id = message.chat.id #5813520738 #message.chat.id
        
            try:

                 
                await bot.forward_message(chat_id=users_id, from_chat_id='@speakadora_live', message_id=54)
                # https://t.me/speakadora_live/35
                
                # await bot.send_message(text=voice_text,chat_id=users_id)

                # caption = video_text
                # await bot.send_photo(chat_id=users_id,
                #                         photo=send_photo,
                #                         caption=caption)
                
                # await bot.send_video(caption=caption, chat_id=users_id, video=vidos, parse_mode="HTML", height = 480, width = 720)
                await asyncio.sleep(1)
                # await bot.send_voice(voice=voice_bytesio, chat_id=users_id)
                # await App().Dao.user.update({
                #     "user_id": users_id,
                #     "bot_state": "conversation"
                # })
                # await asyncio.sleep(1)
                print('Отправил!', users_id)
                send_times +=1

                if send_times % 200 == 0 or send_times == 100:
                       await bot.send_message(text=f'Уже сделал рассылку {send_times} раз. Неудачно {fail_times}', chat_id=message.chat.id)

            except Exception as e:
                print(e)
                print('не смог отправить', users_id)
                await asyncio.sleep(1)
                fail_times += 1


            # break


        print('готово')
        await bot.send_message(text=f'Сделал рассылку {send_times} раз. Неудачно {fail_times}', chat_id=message.chat.id)
        
# &#&#&

# if user_talk_time >= 1:
#     text = f"""
#     🪄 Привет! Ты бодро начал и наговорил с понедельника уже {round(user_talk_time)} мин.
#     Продолжай практиковаться! Регулярность - залог успеха!

#     А хочешь прокачать произношение? У меня как раз появился крутой режим тренировки в /menu. 

#     P.S. - до конца этой недели цена на безлимитный premium всего 490 рублей. Не упускай шанс! ✨
#     """.replace('                ', '').strip()  

# else:
#     text = f"""Hi, how's your day? Let's talk for a few minutes!""".strip()