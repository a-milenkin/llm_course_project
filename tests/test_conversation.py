import asyncio

import pytest
from pyrogram import filters
from pyrogram.types import InlineKeyboardMarkup

from routes.texts import start_response_text, reminder_text, after_finish_text, en_transcript_text, \
    ru_transcript_text, sos_text, rating_text, hints_text, get_start_texts, hint_callback_text
from tests.conftest import CHAT_ID
from tests.utils.lang_check import is_english, is_russian


@pytest.mark.asyncio
async def test_start(app):
    async for ap in app:
        app = ap

    received_messages = []
    voice_received = False
    async with app:
        me = await app.get_me()
    expected_first_message = get_start_texts(f", {me.first_name}", True)[-1]

    @app.on_edited_message(filters.chat(CHAT_ID) & filters.text)
    async def handle_edited_message(client, message):
        received_messages.append(message.text)

    @app.on_message(filters.chat(CHAT_ID) & filters.text)
    async def handle_bot_message(client, message):
        received_messages.append(message.text)

    @app.on_message(filters.chat(CHAT_ID) & filters.voice)
    async def handle_voice_message(client, message):
        nonlocal voice_received
        voice_received = True

    async with app:
        await app.send_message(CHAT_ID, "/start")
        await asyncio.sleep(10)

    assert expected_first_message in received_messages
    assert voice_received


@pytest.mark.asyncio
async def test_voice_chat(app):
    async for ap in app:
        app = ap

    voice_received = []

    @app.on_message(filters.chat(CHAT_ID) & filters.voice)
    async def handle_voice_message(client, message):
        voice_received.append(True)

    async with app:
        await app.send_voice(CHAT_ID, 'assests/voice/voice1.ogg')
        await asyncio.sleep(10)
        await app.send_voice(CHAT_ID, 'assests/voice/voice2.ogg')
        await asyncio.sleep(10)

    assert len(voice_received) == 2


@pytest.mark.asyncio
async def test_reminder(app):
    async for ap in app:
        app = ap

    received_messages = []
    expected_message = reminder_text
    disable_button = False

    @app.on_message(filters.chat(CHAT_ID) & filters.text)
    async def handle_bot_message(client, message):
        nonlocal disable_button
        received_messages.append(message.text)
        disable_button = (message.reply_markup and isinstance(message.reply_markup, InlineKeyboardMarkup)
                          and len(message.reply_markup.inline_keyboard) > 0)

    async with app:
        await asyncio.sleep(130)

    assert expected_message in received_messages
    assert disable_button


@pytest.mark.asyncio
async def test_en_transcript(app):
    async for ap in app:
        app = ap

    received_messages = []

    @app.on_message(filters.chat(CHAT_ID) & filters.text)
    async def handle_bot_message(client, message):
        received_messages.append(message.text)

    async with app:
        await app.send_message(CHAT_ID, en_transcript_text)
        await asyncio.sleep(3)

    assert len(received_messages) >= 1
    assert is_english(received_messages[0])


@pytest.mark.asyncio
async def test_ru_transcript(app):
    async for ap in app:
        app = ap

    received_messages = []

    @app.on_message(filters.chat(CHAT_ID) & filters.text)
    async def handle_bot_message(client, message):
        received_messages.append(message.text)

    async with app:
        await app.send_message(CHAT_ID, ru_transcript_text)
        await asyncio.sleep(6)

    assert len(received_messages) >= 1
    assert is_russian(received_messages[0])


@pytest.mark.asyncio
async def test_hints(app):
    async for ap in app:
        app = ap

    received_messages = []
    have_inline = False
    voice_received = False
    expected_message1 = hints_text
    expected_message2 = hint_callback_text

    @app.on_message(filters.chat(CHAT_ID) & filters.text)
    async def message_handler(client, message):
        received_messages.append(message.text)
        if (message.reply_markup and isinstance(message.reply_markup, InlineKeyboardMarkup)
                and len(message.reply_markup.inline_keyboard) > 0):
            nonlocal have_inline
            have_inline = True
            message_id = message.id
            await client.request_callback_answer(
                chat_id=message.chat.id,
                message_id=message_id,
                callback_data=message.reply_markup.inline_keyboard[0][0].callback_data
            )

    @app.on_message(filters.chat(CHAT_ID) & filters.voice)
    async def handle_voice_message(client, message):
        nonlocal voice_received
        voice_received = True

    async with app:
        await app.send_message(CHAT_ID, sos_text)
        await asyncio.sleep(15)

    assert expected_message1 in received_messages
    assert have_inline
    assert expected_message2 in received_messages
    assert voice_received


@pytest.mark.asyncio
async def test_rating(app):
    async for ap in app:
        app = ap

    received_messages = []

    @app.on_message(filters.chat(CHAT_ID) & filters.text)
    async def handle_bot_message(client, message):
        received_messages.append(message.text)

    async with app:
        await app.send_message(CHAT_ID, rating_text)
        await asyncio.sleep(6)


@pytest.mark.asyncio
async def test_finish(app):
    async for ap in app:
        app = ap

    received_messages = []
    expected_message = after_finish_text

    @app.on_message(filters.chat(CHAT_ID) & filters.text)
    async def handle_bot_message(client, message):
        received_messages.append(message.text)

    async with app:
        await app.send_message(CHAT_ID, '🏁 Finish & get feedback')
        await asyncio.sleep(10)

    assert expected_message in received_messages
    assert len(received_messages) == 2
