import os

import pytest
from dotenv import load_dotenv
from pyrogram import Client


@pytest.fixture()
async def app():
    load_dotenv('test.env')

    session_string = os.getenv("SESSION_STRING_TEST")
    api_id = os.getenv("API_ID")
    api_hash = os.getenv("API_HASH")

    app = Client(
        'my_account',
        session_string=session_string,
        api_id=api_id,
        api_hash=api_hash,
        test_mode=True
    )

    async with app:
        yield app
