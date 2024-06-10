import uuid
import requests
import dataclasses
from dataclasses import dataclass, field
import datetime
import aiohttp
import logging
import asyncio
import time
import re
import jsonpickle

from telebot import types
from telebot.async_telebot import AsyncTeleBot
from telebot.asyncio_helper import ApiTelegramException
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
from telebot.types import InputMediaPhoto
from telebot.types import Message, CallbackQuery

from models.app import App
from utils.structures import UserData
import routes.avatar as routes_avatar

EMAIL_REQUEST = """Я отвечу на твое сообщение, но сначала мне нужен твой email  ✉️ и мотоцикл 🏍. Ладно, можно без мотоцикла 🙂

Мы очень не любим спам, поэтому если и будем присылать письма, то это будет:

✅ полезное письмо с секретными промптами ChatGPT
✅ всегда можно будет легко отписаться прямо из письма

Напиши свою почту 👇
"""
DOESNT_LOOK_LIKE_EMAIL = """Кажется, это не почта. Если все указано верно, напиши, пожалуйста, @HQmupbasic
THANKS_FOR_EMAIL = "Спасибо! Сейчас отвечу на твое сообщение."


def validate_email(email):
    regex = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,7}\b'
    return bool(re.fullmatch(regex, email))

async def email_request_route(message: Message, bot: AsyncTeleBot):
    data = await App().Dao.user.find_by_user_id(message.from_user.id)
    user = UserData(**data)
    if message.content_type == "text" and validate_email(message.text):
        await bot.send_message(text=THANKS_FOR_EMAIL, chat_id=message.chat.id)
        last_message = jsonpickle.decode(user.temp_data["last_message"])
        # save email, switch bot state to conversation, remove last message
        await App().Dao.user.update({"user_id": message.chat.id,
                                     "email": message.text,
                                     "bot_state": "conversation",
                                     "temp_data": {k: v for k, v in user.temp_data.items() if k != "last_message"}
                                    })
        await routes_avatar.voice_handler(last_message, bot)
    else:
        await bot.send_message(text=DOESNT_LOOK_LIKE_EMAIL, chat_id=message.chat.id)