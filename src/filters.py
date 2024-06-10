from telebot import asyncio_filters
from telebot.asyncio_filters import AdvancedCustomFilter
from telebot.types import Message

from models.app import App
from utils.structures import UserData


class KnownUser(asyncio_filters.SimpleCustomFilter):
    key = "known_user"

    @staticmethod
    async def check(message: Message):
        return message.from_user.id in App()["known_users"]


class Admin(asyncio_filters.SimpleCustomFilter):
    key = 'admin'

    @staticmethod
    async def check(message: Message):
        return message.from_user.id in App()["config"]["bot"]["administrators"]["users"]


class CheckMessagesCountMore(AdvancedCustomFilter):
    key = 'messages_count'

    async def check(self, message, text):
        data = await App().Dao.user.find_by_user_id(message.from_user.id)
        user = UserData(**data)
        return len(user.messages) > int(text)


class CheckBotState(AdvancedCustomFilter):
    key = 'bot_state'

    async def check(self, message, allowed_states):
        if isinstance(allowed_states, str):
            allowed_states = [allowed_states]
        data = await App().Dao.user.find_by_user_id(message.from_user.id)
        user = UserData(**data)
        return user.bot_state in allowed_states
