from models.app import App
from telebot import types
from telebot.async_telebot import AsyncTeleBot

from routes.texts import after_finish_text, hints_text
from utils.functions import pop_from_dict
from utils.gpt import get_last_transcript, get_last_transcript_in_ru, voice_chat, get_feedback
from utils.markups import create_suggests_markup
from utils.structures import UserData


async def get_transcript_en(message: types.Message, bot: AsyncTeleBot):
    if App().Tasks.get(message.from_user.id):
        App().Tasks[message.from_user.id].cancel()

    last_transcript = await get_last_transcript(message)
    await bot.send_message(text=last_transcript, chat_id=message.chat.id)


async def get_transcript_ru(message: types.Message, bot: AsyncTeleBot):
    if App().Tasks.get(message.from_user.id):
        App().Tasks[message.from_user.id].cancel()

    last_transcript_in_ru = await get_last_transcript_in_ru(message)
    await bot.send_message(text=last_transcript_in_ru, chat_id=message.chat.id)


async def get_hints(message: types.Message, bot: AsyncTeleBot):
    if App().Tasks.get(message.from_user.id):
        App().Tasks[message.from_user.id].cancel()

    data = await App().Dao.user.find_by_user_id(message.from_user.id)
    user = UserData(**data)
    temp_data = user.temp_data
    if temp_data.get('suggest'):
        await bot.send_message(
            text=f"hint: {temp_data['suggest']}\n\nRepeat after me 👇",
            chat_id=message.chat.id
        )
        await bot.forward_message(
            user.user_id,
            message.chat.id,
            temp_data['suggest_id']
        )
        return
    if temp_data.get('hints'):
        await bot.send_message(
            text=hints_text,
            chat_id=message.chat.id,
            reply_markup=create_suggests_markup(temp_data['hints'])
        )
        return

    conv_suggests_text = await voice_chat(
        message,
        ("How can I respond to your message? Help me continue the conversation "
         "by offering 5 short (they should be no more than 7 words) options "
         "for you to answer to continue the conversation. Answer only in json format without introduction."),
        is_hints=True
    )
    conv_suggests = conv_suggests_text.conversation_suggests

    await bot.send_message(
        text=hints_text,
        chat_id=message.chat.id,
        reply_markup=create_suggests_markup(conv_suggests)
    )
    temp_data['hints'] = conv_suggests
    await App().Dao.user.update(
        {
            'user_id': user.user_id,
            'temp_data': temp_data
        }
    )


async def finish_conv(message: types.Message, bot: AsyncTeleBot):
    if App().Tasks.get(message.from_user.id):
        App().Tasks[message.from_user.id].cancel()

    data = await App().Dao.user.find_by_user_id(message.from_user.id)
    user = UserData(**data)

    await App().Dao.user.update(
        {
            "user_id": message.from_user.id,
            'bot_state': 'default',
            'bot_role': 'english tutor',
            "temp_data": await pop_from_dict(user.temp_data, ['hints', 'transcript_in_ru', 'suggest', 'suggest_id'])
        }
    )
    await bot.send_message(
        text=after_finish_text,
        chat_id=message.chat.id,
        reply_markup=types.ReplyKeyboardRemove()
    )
    if len(user.messages[user.first_message_index:]) > 1:  # if dialog is not empty
        await bot.send_message(
            text=(await get_feedback(message.from_user.id)),
            chat_id=message.chat.id,
            reply_markup=types.ReplyKeyboardRemove()
        )
