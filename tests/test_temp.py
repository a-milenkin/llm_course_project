import asyncio

import pytest
from pyrogram import filters

from routes.texts import help_message
from tests.conftest import CHAT_ID


@pytest.mark.asyncio
async def test_help(app):
    async for ap in app:
        app = ap

    received_messages = []

    expected_help_message = help_message

    @app.on_message(filters.chat(CHAT_ID) & filters.incoming)
    async def handle_bot_message(client, message):
        received_messages.append(message.text)

    async with app:
        await app.send_message(CHAT_ID, '/help')
        await asyncio.sleep(2)  # время ожидания ответа

    assert expected_help_message in received_messages


if __name__ == '__main__':
    asyncio.run(test_help())
