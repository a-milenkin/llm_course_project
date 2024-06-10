import asyncio
import base64
import dataclasses
import datetime
import glob
import io
import logging
from copy import copy
import numpy as np
import aiohttp
import math
import random

import jsonpickle
from PIL import Image
from telebot import types
from telebot.async_telebot import AsyncTeleBot
from telebot.asyncio_helper import ApiTelegramException
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
from telebot.types import InputMediaPhoto
from telebot.types import Message, CallbackQuery

from models.app import App
from routes.english_tips import words_4_using
from routes.email_request import EMAIL_REQUEST, email_request_route
from utils.functions import pop_from_dict
from utils.send_to_admin import send_error_logs, send_bot_using_logs
from utils.callback_factories import SuggestCallbackData, MenuCallbackData, PronunciationCallbackData
from utils.gpt import voice_chat, text_to_voice_with_duration
from utils.markups import create_conv_reply_markup, create_start_suggests_reply_markup, create_suggests_markup
from utils.schedule import send_stuck_reminder
from utils.structures import UserData
from utils.send_to_admin import send_error_logs, send_bot_using_logs

from pydub import AudioSegment

PHRASES = []
with open("/src/routes/pronunciation_phrases.txt", "r") as f:
    for line in f.readlines():
        if not line.startswith("#") and len(line) > 5:
            PHRASES.append(line)

async def new_phrase(message, bot, user_id = None):
    user_id = message.from_user.id if message else user_id
    data = await App().Dao.user.find_by_user_id(user_id)
    user = UserData(**data)
    phrase = random.choice(PHRASES)
    text = ("Repeat after me 👇\n"
            "\n"
            f"{phrase}")
    await App().Bot.send_message(text=text, chat_id=user_id)
    response_voice_audio, response_duration = await text_to_voice_with_duration(phrase)
    voice_bytes = response_voice_audio.read()

    await App().Dao.user.update({
                "user_id": user_id,
                "temp_data": {**user.temp_data,
                              "pronunciation_state": {
                                  **user.temp_data.get("pronunciation_state", {}),
                                  "phrase": phrase,
                                  "voice_assistant": base64.b64encode(voice_bytes).decode()
                              }
                }
            })

    response_voice_message = await bot.send_voice(
        voice=io.BytesIO(voice_bytes),
        chat_id=user_id
    )

async def speechace_request(phrase: str, voice_bytes):
    form_data = {
        "text": phrase,
        "user_audio_file": io.BytesIO(voice_bytes)
    }
    async with App().Managers.session_manager.speechace.post(
            f'/api/scoring/text/v9/json?key={App()["config"]["speechace"]["api_key"]}&dialect=en-us&user_id=XYZ-ABC-99001',
            data=form_data
        ) as resp:
            return await resp.json()

def linkable_prefix(word):
    """
    returns longest prefix that could be turned into telegram bot command
    For example:
    "Hey" -> "Hey" (because /Hey is a valid telegram bot command)
    "Let's" -> "Let" (because /Let is a valid telegram bot command. /Let's - not)
    """
    valid_characters = set("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_")
    for i, char in enumerate(word):
        if char not in valid_characters:
            return word[:i]
    return word

async def word_analyzer_ui(user_id):
    data = await App().Dao.user.find_by_user_id(user_id)
    user = UserData(**data)
    final_text = "Click any word to analyze pronunciation 👇\n"
    words = user.temp_data["pronunciation_state"]["words"]
    length_limit = 35
    lines = [[]]
    current_length = 0
    for word_index, w in enumerate(words):
        w_linkable = linkable_prefix(w["word"])
        order = [linkable_prefix(ww["word"]) for ww in words][:word_index].count(w_linkable) + 1 # "number of times we met this word before" + 1
        if current_length == 0:
            lines[-1].append({
                "word": w["word"],
                "linkable": w_linkable,
                "ending_punctuation": w["ending_punctuation"],
                "order": order,
                "warning": w["quality_score"] < 90
            })
            current_length += len(w["word"]) + 2 # /_{word}
        else:
            spaces_before_ending_punctuation = int(bool(w["ending_punctuation"])) # one space if we have a punctuation. zero spaces if we don't have a punctuation
            potential_new_length = current_length + 1 + 2 + len(w["word"]) + spaces_before_ending_punctuation + len(w["ending_punctuation"]) # <previous_str> /_{word} ?
            if potential_new_length > length_limit or len(lines[-1]) == 4:
                lines.append([])
                current_length = 0 # we switched to the new line
            else:
                current_length = potential_new_length # we stayed on the same line
            lines[-1].append({
                "word": w["word"],
                "linkable": w_linkable,
                "ending_punctuation": w["ending_punctuation"],
                "order": order,
                "warning": w["quality_score"] < 90
            })
    for line_index, line in enumerate(lines):
        txt_line = ""
        feedback1_line = ""
        feedback2_line = ""
        for i, w in enumerate(line):
            space = "" if i == 0 else " "
            space_before_punctuation = " " if w["ending_punctuation"] else ""
            txt_line += f"{space}/{'_'*w['order']}<b>{w['word']}</b>{space_before_punctuation}{w['ending_punctuation']}"
            space_fb = "" if i == 0 else " "
            space_before_punctuation_fb = " " if w["ending_punctuation"] else ""
            word_spacing = (len(w["word"]) - 2) // 2
            mark = '⚠️' if w["warning"] else '✅'
            feedback1_line += f"{space_fb} {' '*w['order']}{'^'*len(w['word'])}{space_before_punctuation_fb}{' '*len(w['ending_punctuation'])}"
            # feedback2_line += f"{space_fb} {' '*w['order']}{' '*word_spacing}{mark}{' '*word_spacing}{space_before_punctuation_fb}{' '*len(w['ending_punctuation'])}"
            padding = length_limit // 12
            feedback2_line += f"{' '*padding}{mark}{' '*padding}"
        final_text += txt_line + "\n"
        final_text += feedback1_line + "\n"
        final_text += feedback2_line + "\n"
        # if line_index < len(lines) - 1:
        #     final_text += "᠆"*length_limit + "\n"
    return final_text
            


def progress_bar(percentage):
    percentage /= 10
    percentage = math.ceil(percentage) # round up
    return "✅"*percentage + "⬜️"*(10 - percentage)

@send_bot_using_logs
@send_error_logs
async def voice_handler(message, bot):
    data = await App().Dao.user.find_by_user_id(message.from_user.id)
    user = UserData(**data)
    if message.content_type == "voice":
        input_voice_id = message.voice.file_id
        voice = await bot.get_file(input_voice_id)
        downloaded_file = await bot.download_file(voice.file_path)
        voice_bytes = downloaded_file
        voice_bytesio = io.BytesIO(voice_bytes)
        voice_bytesio.name = 'voice.mp3'
        input_msg = voice_bytesio
        ogg_audio = AudioSegment.from_file(voice_bytesio, format="ogg")
        input_duration = len(ogg_audio) / 1000
    else:
        raise Exception("voice please")
    
    voice_assistant_b64 = user.temp_data["pronunciation_state"]["voice_assistant"]
    voice_assistant_bytes = base64.b64decode(voice_assistant_b64.encode('ascii'))
    speechace_response_user = await speechace_request(user.temp_data["pronunciation_state"]["phrase"], voice_bytes)
    speechace_response_assistant = await speechace_request(user.temp_data["pronunciation_state"]["phrase"], voice_assistant_bytes)
    if speechace_response_user["status"] == "success" and speechace_response_assistant["status"] == "success":
        await App().Dao.user.update({
                    "user_id": message.from_user.id,
                    "temp_data": {**user.temp_data,
                                "pronunciation_state": {
                                    **user.temp_data.get("pronunciation_state", {}),
                                    "voice_user": base64.b64encode(voice_bytes).decode(),
                                    "speechace_score": speechace_response_user["text_score"]["speechace_score"]["pronunciation"],
                                    "ielts_score": speechace_response_user["text_score"]["ielts_score"]["pronunciation"],
                                    "pte_score": speechace_response_user["text_score"]["pte_score"]["pronunciation"],
                                    "toeic_score": speechace_response_user["text_score"]["toeic_score"]["pronunciation"],
                                    "cefr_score": speechace_response_user["text_score"]["cefr_score"]["pronunciation"],
                                    "words": [{
                                        "word": w["word"],
                                        "ending_punctuation": w.get("ending_punctuation", ""),
                                        "quality_score": w["quality_score"],
                                        "extent_user": [
                                            w["phone_score_list"][0]["extent"][0],
                                            w["phone_score_list"][-1]["extent"][-1]
                                        ],
                                        "extent_assistant": [
                                            speechace_response_assistant["text_score"]["word_score_list"][word_index]["phone_score_list"][0]["extent"][0],
                                            speechace_response_assistant["text_score"]["word_score_list"][word_index]["phone_score_list"][-1]["extent"][-1],
                                        ],
                                        "phone_score_list": [{
                                            "phone": p["phone"],
                                            "quality_score": p["quality_score"],
                                            "sound_most_like": p["sound_most_like"]
                                        } for p in w["phone_score_list"]]
                                    } for word_index, w in enumerate(speechace_response_user["text_score"]["word_score_list"])]
                                }
                    }
                })
        pronunciation_score = speechace_response_user["text_score"]["speechace_score"]["pronunciation"]
        pronunciation_score = int((max(0, pronunciation_score - 30) / 70) * 100)
        ielts_score = speechace_response_user["text_score"]["ielts_score"]["pronunciation"]
        pte_score = speechace_response_user["text_score"]["pte_score"]["pronunciation"]
        toeic_score = speechace_response_user["text_score"]["toeic_score"]["pronunciation"]
        cefr_score = speechace_response_user["text_score"]["cefr_score"]["pronunciation"]
        text = (
            "Nice! 🎉 Your pronunciation score:\n"
            f"{progress_bar(pronunciation_score)} {pronunciation_score}%\n"
            f"IELTS: {ielts_score}\n"
            f"CEFR: {cefr_score} &lt;-- this is your fluency level\n"
            f"TOEIC: {toeic_score}\n"
            f"PTE: {pte_score}\n"
            f"\n"
            f"{await word_analyzer_ui(message.from_user.id)}"
        )
        markup = InlineKeyboardMarkup()
        markup.add(
            types.InlineKeyboardButton(f"🔄 Try again",
                                    callback_data=PronunciationCallbackData.new(action="try_again"))
        )
        markup.add(
            types.InlineKeyboardButton(f"▶️ Next phrase",
                                    callback_data=PronunciationCallbackData.new(action="next_phrase"))
        )
        return await App().Bot.send_message(text=text, chat_id=message.from_user.id, reply_markup=markup, parse_mode="HTML")
    else:
        print("speechace_response_user:", speechace_response_user)
        print("speechace_response_assistant:", speechace_response_assistant)
        return await App().Bot.send_message(text="Something went wrong. Please try again.", chat_id=message.from_user.id)

async def word_feedback_handler(message, bot):
    data = await App().Dao.user.find_by_user_id(message.from_user.id)
    user = UserData(**data)
    key = message.text[1:] # remove "/"
    words = user.temp_data["pronunciation_state"]["words"]
    words = [{
        "word": w["word"],
        "linkable": linkable_prefix(w["word"]),
        "order": [linkable_prefix(ww["word"]) for ww in words][:word_index].count(linkable_prefix(w["word"])) + 1, # "number of times we met this word before" + 1
        "index": word_index
    } for word_index, w in enumerate(words)]
    words = [{
        **w,
        "key": '_'*w["order"] + w["linkable"]
    } for w in words]
    word = next(w for w in words if w["key"] == key)
    word = user.temp_data["pronunciation_state"]["words"][word["index"]]
    ipa_transcription = "".join([arpabet_to_ipa(p["phone"]) for p in word["phone_score_list"]])
    text = f"Разбор вашего произношения слова {word['word']} [{ipa_transcription}]:\n"
    for p in word["phone_score_list"]:
        ipa = arpabet_to_ipa(p['phone'])
        ipa = ipa if len(ipa) == 2 else f"{ipa} "
        fb = "✅ Good" if p["quality_score"] > 80 else f"⚠️ Sounds more like \"{arpabet_to_ipa(p['sound_most_like'])}\""
        text += f"<code>{ipa} - {fb}</code>\n"
    await App().Bot.send_message(text=text, chat_id=message.from_user.id, parse_mode="HTML")

    voice_assistant_b64 = user.temp_data["pronunciation_state"]["voice_assistant"]
    voice_assistant_bytes = base64.b64decode(voice_assistant_b64.encode('ascii'))
    voice_assistant_bytesio = io.BytesIO(voice_assistant_bytes)
    voice_assistant_bytesio.name = 'voice.mp3'
    voice_assistant_ogg_audio = AudioSegment.from_file(voice_assistant_bytesio, format="ogg")
    assistant_start = word["extent_assistant"][0]*10
    assistant_end = word["extent_assistant"][1]*10
    voice_assistant_ogg_audio = voice_assistant_ogg_audio[assistant_start:assistant_end]
    silence = AudioSegment.silent(duration=500)
    voice_assistant_ogg_audio += silence
    voice_assistant_word_bytesio = io.BytesIO()
    voice_assistant_ogg_audio.export(voice_assistant_word_bytesio, format="ogg", codec="libopus")
    await bot.send_voice(
        voice=voice_assistant_word_bytesio,
        chat_id=message.chat.id
    )

    voice_user_b64 = user.temp_data["pronunciation_state"]["voice_user"]
    voice_user_bytes = base64.b64decode(voice_user_b64.encode('ascii'))
    voice_user_bytesio = io.BytesIO(voice_user_bytes)
    voice_user_bytesio.name = 'voice.mp3'
    voice_user_ogg_audio = AudioSegment.from_file(voice_user_bytesio, format="ogg")
    user_start = word["extent_user"][0] * 10
    user_end = word["extent_user"][1] * 10
    voice_user_ogg_audio = voice_user_ogg_audio[user_start:user_end]
    voice_user_word_bytesio = io.BytesIO()
    voice_user_ogg_audio.export(voice_user_word_bytesio, format="ogg", codec="libopus")
    await bot.send_voice(
        voice=voice_user_word_bytesio,
        chat_id=message.chat.id
    )
    markup = InlineKeyboardMarkup()
    markup.add(
        types.InlineKeyboardButton(f"🔄 Try again",
                                callback_data=PronunciationCallbackData.new(action="try_again"))
    )
    markup.add(
        types.InlineKeyboardButton(f"▶️ Next phrase",
                                callback_data=PronunciationCallbackData.new(action="next_phrase"))
    )
    await App().Bot.send_message(text="Пойдем дальше или попробуем снова?", chat_id=message.chat.id, parse_mode="HTML", reply_markup=markup)

async def buttons_handler(call: CallbackQuery, bot: AsyncTeleBot):
    data = await App().Dao.user.find_by_user_id(call.from_user.id)
    user = UserData(**data)
    callback_data = PronunciationCallbackData.parse_and_destroy(call.data)
    if callback_data["action"] == "try_again":
        text = ("Repeat after me 👇\n"
            "\n"
            f"{user.temp_data['pronunciation_state']['phrase']}")
        await App().Bot.send_message(text=text, chat_id=call.from_user.id, parse_mode="HTML")
        voice_assistant_b64 = user.temp_data["pronunciation_state"]["voice_assistant"]
        voice_assistant_bytes = base64.b64decode(voice_assistant_b64.encode('ascii'))
        voice_assistant_bytesio = io.BytesIO(voice_assistant_bytes)
        voice_assistant_bytesio.name = 'voice.mp3'
        voice_assistant_ogg_audio = AudioSegment.from_file(voice_assistant_bytesio, format="ogg")
        voice_assistant_word_bytesio = io.BytesIO()
        voice_assistant_ogg_audio.export(voice_assistant_word_bytesio, format="ogg", codec="libopus")
        await bot.send_voice(
            voice=voice_assistant_word_bytesio,
            chat_id=call.from_user.id
        )
    elif callback_data["action"] == "next_phrase":
        await new_phrase(None, bot, user_id=call.from_user.id)
    

def arpabet_to_ipa(phone):
    _arpabet2ipa = {
        'AA':'ɑ',
        'AE':'æ',
        'AH':'ʌ',
        'AH0':'ə',
        'AO':'ɔ',
        'AW':'aʊ',
        'AY':'aɪ',
        'EH':'ɛ',
        'ER':'ɝ',
        'ER0':'ɚ',
        'EY':'eɪ',
        'IH':'ɪ',
        'IH0':'ɨ',
        'IY':'i',
        'OW':'oʊ',
        'OY':'ɔɪ',
        'UH':'ʊ',
        'UW':'u',
        'B':'b',
        'CH':'tʃ',
        'D':'d',
        'DH':'ð',
        'EL':'l̩ ',
        'EM':'m̩',
        'EN':'n̩',
        'F':'f',
        'G':'ɡ',
        'HH':'h',
        'JH':'dʒ',
        'K':'k',
        'L':'l',
        'M':'m',
        'N':'n',
        'NG':'ŋ',
        'P':'p',
        'Q':'ʔ',
        'R':'ɹ',
        'S':'s',
        'SH':'ʃ',
        'T':'t',
        'TH':'θ',
        'V':'v',
        'W':'w',
        'WH':'ʍ',
        'Y':'j',
        'Z':'z',
        'ZH':'ʒ'
    }
    if phone:
        return _arpabet2ipa[phone.upper()]
    else:
        return "_"