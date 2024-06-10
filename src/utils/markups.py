from telebot.types import InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardButton

from routes.texts import en_transcript_text, ru_transcript_text, sos_text, rating_text, finish_text
from utils.callback_factories import SuggestCallbackData, RolesCallbackData


def create_conv_reply_markup():
    markup = ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    get_trans_en = KeyboardButton(en_transcript_text)
    get_trans_ru = KeyboardButton(ru_transcript_text)
    get_conv_hints = KeyboardButton(sos_text)
    get_stats = KeyboardButton(rating_text)
    finish = KeyboardButton(finish_text)
    markup.add(get_trans_en, get_conv_hints)
    markup.add(get_trans_ru, finish, get_stats)
    return markup


def create_start_suggests_reply_markup():
    markup = ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    get_conv_hints = KeyboardButton(sos_text)
    finish = KeyboardButton(finish_text)
    markup.add(get_conv_hints, finish)
    return markup


def create_suggests_markup(suggestions: list[str], threshold: int = 37) -> InlineKeyboardMarkup:
    markup = InlineKeyboardMarkup()
    for i, _ in enumerate(suggestions):
        if len(suggestions[i]) < threshold:
            markup.add(
                InlineKeyboardButton(
                    f"🎧 {suggestions[i]}",
                    callback_data=SuggestCallbackData.new(suggest=suggestions[i])
                )
            )
    return markup


def create_roles_markup(roles: list[str]) -> InlineKeyboardMarkup:
    markup = InlineKeyboardMarkup()
    for role in roles:
        markup.add(
            InlineKeyboardButton(
                role,
                callback_data=RolesCallbackData.new(role=role)
            )
        )
    return markup
