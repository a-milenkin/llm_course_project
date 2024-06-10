import _io
import asyncio
import datetime
import glob
import io
import logging
from copy import copy

import jsonpickle
import numpy as np
from PIL import Image
from pydub import AudioSegment
from telebot import formatting
from telebot import types
from telebot.async_telebot import AsyncTeleBot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
from telebot.types import Message, CallbackQuery

from models.app import App
from routes.english_tips import words_4_using, phrase2start
from routes.pronunciation import new_phrase
from routes.texts import get_start_texts, help_message, hint_callback_text, roles_text, roles, after_set_up_role_text, \
    create_role_by_user_text, failed_create_role_text, help_message_admins
from utils.callback_factories import RolesCallbackData
from utils.callback_factories import SuggestCallbackData, MenuCallbackData, DailyReminderSetupScheduleCallbackData, \
    DailyReminderSetupScheduleCallbackData2
from utils.functions import pop_from_dict
from utils.gpt import voice_chat, text_to_voice_with_duration
from utils.markups import create_conv_reply_markup, create_start_suggests_reply_markup
from utils.markups import create_roles_markup
from utils.message_reactions import set_message_reaction
from utils.schedule import send_stuck_reminder
from utils.send_to_admin import send_error_logs, send_bot_using_logs
from utils.structures import UserData
from utils.text_utils import is_english, markdown_escaped

logger = logging.getLogger(__name__)

USER_NOT_IN_GROUP_STATUSES = ('left', 'user not found', "banned")

try:
    mask = Image.open('assets/mark.png').convert('RGBA')
except Exception:
    mask = None


async def _user_in_group(message: Message, bot: AsyncTeleBot) -> bool:
    membership_settings = App()["config"]["settings"]["membership_check"]
    if not membership_settings["enabled"]:
        return True
    data = await App().Dao.user.find_by_user_id(message.chat.id)
    user = UserData(**data)
    if user.last_generation_date != datetime.datetime.combine(datetime.datetime.now(), datetime.time.min):
        await App().Dao.user.reset_today_generations(message.chat.id)
        user.today_generations = 0
    logger.info(f"User id: {message.chat.id} today generations: {user.today_generations}")

    required_groups = []
    for limitation, required_groups in reversed(membership_settings["daily_requests_subscription_limitations"].items()):
        if user.today_generations >= int(limitation):
            break

    groups_sub_kb = InlineKeyboardMarkup()
    need_to_sub_group_names = []
    for group in required_groups:
        membership = await bot.get_chat_member(group["group_id"], message.chat.id)
        logger.info(f"User id: {message.chat.id}  channel: {group['group_id']} status: {membership.status}")
        if membership.status in USER_NOT_IN_GROUP_STATUSES:
            groups_sub_kb.add(
                InlineKeyboardButton("Вступить в группу", url=group["group_url"])
            )
            need_to_sub_group_names.append(group["group_name"])

    if need_to_sub_group_names:
        need_to_sub_group_names_str = "\n".join(need_to_sub_group_names)
        await bot.send_message(message.chat.id, f"Чтобы получить больше генераций на сегодня, нужно подписаться на \n"
                                                f"{need_to_sub_group_names_str}",
                               reply_markup=groups_sub_kb)
        return False
    return True


async def _spy_forward(message: Message, bot: AsyncTeleBot, caption: str = ""):
    try:
        if App()["config"]["settings"]["spy_forward"]["enabled"]:
            forward_groups = App()["config"]["settings"]["spy_forward"]["forward_groups"]
            for group in forward_groups:
                if not caption:
                    await bot.forward_message(group, message.chat.id, message.message_id)
                else:
                    await bot.copy_message(group, message.chat.id, message.message_id, caption=caption)
    except Exception as e:
        logger.warning(f"Failed to forward message to group {group}: {e}")


def extract_unique_code(text):
    # Extracts the unique_code from the sent /start command.
    return text.split()[1] if len(text.split()) > 1 else None


@send_error_logs
async def send_welcome(message: Message, bot: AsyncTeleBot):
    unique_code = None
    if message.text is not None:
        unique_code = extract_unique_code(message.text)

    user_id = message.from_user.id
    is_new = False

    if user_id not in App()["known_users"]:
        await App().Dao.user.create({"user_id": user_id,
                                     "username": message.from_user.username,
                                     "utm_campaign": unique_code,
                                     "generations": 0,
                                     "today_generations": 0,
                                     "last_generation_date": datetime.datetime.combine(datetime.datetime.now(),
                                                                                       datetime.time.min),
                                     "messages": [],
                                     "bot_state": "conversation",
                                     "first_message_index": 0,
                                     "temp_data": {},
                                     "email": None,
                                     "stuck_reminder_enabled": True,
                                     "reminders": {
                                         "days": [],
                                         "time": datetime.datetime.combine(datetime.date.today(),
                                                                           datetime.time(hour=12)),
                                         "has_been_requested_before": False,
                                         "last_reminder_sent": None,
                                         "last_reminder_message_id": None
                                     }
                                     })
        App()["known_users"].add(user_id)

        path = '/src/assets/welcome_msg_photos/onboarding.gif.mp4'
        with open(path, 'rb') as video:
            await bot.send_video(message.chat.id, video)

        is_new = True
        name = f', {message.from_user.first_name}' if len(message.from_user.first_name) > 2 else ''

    else:
        data = await App().Dao.user.find_by_user_id(message.from_user.id)
        user = UserData(**data)
        await App().Dao.user.update({
            "user_id": message.from_user.id,
            "first_message_index": len(user.messages),
            # "utm_campaign" : unique_code,
            "temp_data": await pop_from_dict(user.temp_data, ['hints', 'transcript_in_ru', 'suggest', 'suggest_id']),
            "bot_state": "conversation"
        })

        name = f', {message.from_user.first_name}' if len(message.from_user.first_name) > 2 else ''

    data = await App().Dao.user.find_by_user_id(message.from_user.id)
    user = UserData(**data)

    start_text0, *msg_list = get_start_texts(name, is_new)

    time_gap = 0.5

    bot_msg = await bot.send_message(text=start_text0, chat_id=message.chat.id, parse_mode='HTML')
    for msg in msg_list:
        await asyncio.sleep(time_gap)
        bot_msg = await bot.edit_message_text(text=msg,
                                              chat_id=message.chat.id,
                                              message_id=bot_msg.message_id,
                                              parse_mode='HTML')

    name = f'{message.from_user.first_name}, ' if len(message.from_user.first_name) > 2 else ''
    question = np.random.choice(phrase2start)
    response_text = f'{name}Let’s start! 🚀\n\n{question}'

    await bot.send_message(text=response_text, chat_id=message.chat.id)
    # TODO возможно добавить create_start_suggests_reply_markup()

    voice_bytesio, voice_duration = await text_to_voice_with_duration(response_text)
    await bot.send_chat_action(chat_id=message.chat.id, action="record_voice")

    # voice_file_path = '/src/assets/voice/start_audio.ogg'
    # with open(voice_file_path, 'rb') as f:
    #     voice_bytesio = io.BytesIO(f.read())
    #     ogg_audio = AudioSegment.from_file(copy(voice_bytesio), format="ogg")
    #     voice_duration = len(ogg_audio) / 1000

    voice_message = await bot.send_voice(
        voice=voice_bytesio,
        chat_id=message.chat.id,
        reply_markup=create_conv_reply_markup()
    )

    await App().Dao.user.update({
        "user_id": message.from_user.id,
        "messages": [*user.messages, {"role": "assistant",
                                      "content": response_text,
                                      "voice_file_id": voice_message.voice.file_id,
                                      "voice_duration": voice_duration,
                                      "created_at": datetime.datetime.now()}],
        "bot_state": "conversation",
        "bot_role": question
    })

    task = asyncio.create_task(send_stuck_reminder(message, bot))
    App().Tasks[user_id] = task
    return voice_message

    # TODO использовать response_duration в сообщении - мол, вай, круто, но давай еще более длинные голосовые записывай!


async def set_up_bot_role(message: Message, bot: AsyncTeleBot):
    data = await App().Dao.user.find_by_user_id(message.from_user.id)
    user = UserData(**data)
    await bot.send_message(
        text=roles_text(user.bot_role),
        chat_id=message.chat.id,
        reply_markup=create_roles_markup(roles)
    )


async def roles_callback(call: CallbackQuery, bot: AsyncTeleBot):
    role = RolesCallbackData.parse_and_destroy(call.data)["role"]
    await bot.delete_message(call.message.chat.id, call.message.id)
    if role == 'create a topic':
        await bot.send_message(
            text=create_role_by_user_text,
            chat_id=call.message.chat.id
        )
        await App().Dao.user.update(
            {"user_id": call.from_user.id,
             "bot_state": "topic_creating"}
        )
        return
    await App().Dao.user.update(
        {"user_id": call.from_user.id,
         "bot_role": role}
    )
    await bot.send_message(
        text=after_set_up_role_text(role),
        chat_id=call.message.chat.id
    )


async def create_role_by_user(message: Message, bot: AsyncTeleBot):
    role = message.text
    if not is_english(role):
        await bot.send_message(
            text=failed_create_role_text,
            chat_id=message.chat.id
        )
        return
    await App().Dao.user.update(
        {"user_id": message.from_user.id,
         "bot_role": role,
         "bot_state": "conversation"}
    )
    await bot.send_message(
        text=after_set_up_role_text(role),
        chat_id=message.chat.id
    )


async def get_menu_markup(message_id, user_id):
    data = await App().Dao.user.find_by_user_id(user_id)
    user = UserData(**data)
    markup = InlineKeyboardMarkup()
    markup.add(
        types.InlineKeyboardButton(f"{'✅' if user.bot_state == 'conversation' else ''} Диалог",
                                   callback_data=MenuCallbackData.new(mode="conversation", message_id=message_id))
    )
    markup.add(
        types.InlineKeyboardButton(f"{'✅' if user.bot_state == 'pronunciation' else ''} Тренировка произношения",
                                   callback_data=MenuCallbackData.new(mode="pronunciation", message_id=message_id))
    )
    return markup


@send_error_logs
async def send_menu(message: Message, bot: AsyncTeleBot):
    if App().Tasks.get(message.from_user.id):
        App().Tasks[message.from_user.id].cancel()
    data = await App().Dao.user.find_by_user_id(message.from_user.id)
    user = UserData(**data)
    # cancel hint after 1 minute
    if App().Tasks.get(message.from_user.id):
        App().Tasks[message.from_user.id].cancel()

    menu = (
        "Выбери режим тренировки!\n"
        "\n"
        "Диалог - если просто хочешь поболтать на любую тему\n"
        "\n"
        "Тренировать произношение - тут мы помогаем тебе улучшить произношение с детальным разбором ошибок\n")

    menu_photo = None
    for photo in glob.glob("assets/mods*"):
        with open(photo, "rb") as f:
            menu_photo = f.read()

    bot_msg = await bot.send_photo(chat_id=message.chat.id, photo=menu_photo, caption=menu)
    await asyncio.sleep(0.3)
    await bot.edit_message_reply_markup(message.chat.id, bot_msg.message_id,
                                        reply_markup=await get_menu_markup(bot_msg.message_id, message.from_user.id))


pronunciation_promo_photo = None
for photo in glob.glob("assets/pronunciation_promo/*.png"):
    with open(photo, "rb") as f:
        pronunciation_promo_photo = f.read()


async def menu_buttons_handler(call: CallbackQuery, bot: AsyncTeleBot):
    data = await App().Dao.user.find_by_user_id(call.from_user.id)
    user = UserData(**data)
    call.message.from_user = call.from_user
    callback_data = MenuCallbackData.parse_and_destroy(call.data)
    call.message.from_user.id = call.message.chat.id  # to use this message later for send_welcome

    if callback_data["mode"] == "conversation":
        await App().Dao.user.update({
            "user_id": call.from_user.id,
            "bot_state": "conversation"
        })
        await bot.edit_message_reply_markup(call.message.chat.id, callback_data["message_id"],
                                            reply_markup=await get_menu_markup(callback_data["message_id"],
                                                                               call.from_user.id))
        await bot.send_message(text="Вы перешли в режим диалога. Чтобы выбрать другой режим - нажмите /menu",
                               chat_id=call.from_user.id)
        await send_welcome(call.message, bot)
    elif callback_data["mode"] == "pronunciation":
        await App().Dao.user.update({
            "user_id": call.from_user.id,
            "bot_state": "pronunciation"
        })
        await bot.edit_message_reply_markup(call.message.chat.id, callback_data["message_id"],
                                            reply_markup=await get_menu_markup(callback_data["message_id"],
                                                                               call.from_user.id))
        await bot.send_message(
            text="Вы перешли в режим тренировки произношения. Чтобы выбрать другой режим - нажмите /menu",
            chat_id=call.from_user.id
        )
        await new_phrase(None, bot, user_id=call.from_user.id)


async def start_conversation_callback(call: CallbackQuery, bot: AsyncTeleBot):
    data = await App().Dao.user.find_by_user_id(call.from_user.id)
    user = UserData(**data)
    if App().Tasks.get(user.user_id):
        App().Tasks[user.user_id].cancel()

    suggest = SuggestCallbackData.parse_and_destroy(call.data)["suggest"]
    temp_data = user.temp_data
    await bot.delete_message(
        call.message.chat.id,
        call.message.id,
    )
    await bot.send_message(text=hint_callback_text, chat_id=call.message.chat.id)
    await bot.send_chat_action(chat_id=call.message.chat.id, action="record_voice")

    if len(user.messages) > 1:
        markup = create_conv_reply_markup()
    else:
        markup = create_start_suggests_reply_markup()

    voice_audio, _ = await text_to_voice_with_duration(suggest)
    response_message = await bot.send_voice(
        voice=voice_audio,
        chat_id=call.message.chat.id,
        reply_markup=markup
    )
    temp_data["suggest"] = suggest
    temp_data["suggest_id"] = response_message.message_id
    await App().Dao.user.update(
        {
            "user_id": user.user_id,
            "temp_data": temp_data
        }
    )

    task = asyncio.create_task(send_stuck_reminder(call.message, bot))
    App().Tasks[call.from_user.id] = task
    return response_message


def daily_reminder_request_wrapper(handler_func):
    async def wrapper(message: Message, bot: AsyncTeleBot):
        data = await App().Dao.user.find_by_user_id(message.from_user.id)
        user = UserData(**data)
        if user.bot_state == "conversation":
            if not user.reminders["has_been_requested_before"] and user.generations >= 5:
                # save user's message to answer it later
                msg_obj = jsonpickle.encode(message)
                # send message with daily reminder request
                voice_file_path = '/src/assets/voice/english_practice_daily_habit.ogg'
                with open(voice_file_path, 'rb') as f:
                    voice_bytesio = io.BytesIO(f.read())
                    ogg_audio = AudioSegment.from_file(copy(voice_bytesio), format="ogg")
                    voice_duration = len(ogg_audio) / 1000
                    ogg_audio: _io.BufferedRandom = ogg_audio.export(format="ogg", codec="libopus")
                voice_message = await bot.send_voice(
                    voice=ogg_audio,
                    chat_id=message.chat.id
                )
                txt = (
                    "🇬🇧 I'll answer your message in a moment, but first...\n"
                    "We've been talking for more than 1 minute 🥰, you're doing great! Do you want to make English practice your daily habit?\n"
                    "\n"
                    "🇷🇺 Сейчас я отвечу на твое сообщение, но сначала...\n"
                    "Мы говорим уже больше 1 минуты, 🥰  ты молодец! Хочешь сделать практику английского своей полезной привычкой?"
                )
                markup = InlineKeyboardMarkup()
                markup.add(
                    InlineKeyboardButton(
                        f"🎉 Да!",
                        callback_data="prompt_daily_reminder_request_yes"
                    ),
                    InlineKeyboardButton(
                        f"Нет",
                        callback_data="prompt_daily_reminder_request_no"
                    )
                )
                daily_reminder_request_message = await bot.send_message(text=txt,
                                                                        chat_id=message.chat.id,
                                                                        reply_markup=markup)

                await App().Dao.user.update({"user_id": message.chat.id,
                                             #  "bot_state": "daily_reminder_request",
                                             "temp_data": {**user.temp_data, "last_message": msg_obj}
                                             })
            else:
                return await handler_func(message, bot)
        elif user.bot_state == "daily_reminder_request":
            pass
            # await email_request_route(message, bot)
        else:
            return await handler_func(message, bot)

    return wrapper


async def daily_reminder_request_buttons_handler(call, bot):
    data = await App().Dao.user.find_by_user_id(call.from_user.id)
    user = UserData(**data)
    if call.data == "prompt_daily_reminder_request_no":
        await App().Dao.user.update({"user_id": call.message.chat.id,
                                     "reminders": {
                                         **user.reminders,
                                         "has_been_requested_before": True
                                     }
                                     })
        await bot.send_message(text="Хорошо, сейчас отвечу на твое последнее сообщение 👇", chat_id=call.message.chat.id)
        last_message = jsonpickle.decode(user.temp_data["last_message"])
        # remove last message
        await App().Dao.user.update({"user_id": call.message.chat.id,
                                     "temp_data": {k: v for k, v in user.temp_data.items() if k != "last_message"}
                                     })
        await voice_handler(last_message, bot)
    elif call.data == "prompt_daily_reminder_request_yes":
        txt = ("🚀 По исследованиям Speakadora среди 10,000 человек всего 5 минут общения на английском "
               "ежедневно способствуют заметному прогрессу!")
        await bot.send_message(text=txt, chat_id=call.message.chat.id)
        schedule = {
            "mon": False,
            "tue": False,
            "wed": False,
            "thu": False,
            "fri": False,
            "sat": False,
            "sun": False
        }
        daily_reminder_request_message = await bot.send_message(text="В какие дни хочешь заниматься?",
                                                                chat_id=call.message.chat.id)
        markup = InlineKeyboardMarkup(row_width=5)
        markup.add(
            InlineKeyboardButton(
                f"{'✅ ' if schedule['mon'] else ''}пн",
                callback_data=DailyReminderSetupScheduleCallbackData.new(
                    schedule={**schedule, "mon": not schedule["mon"]},
                    message_id=daily_reminder_request_message.id,
                    confirm=False
                )
            ),
            InlineKeyboardButton(
                f"{'✅ ' if schedule['tue'] else ''}вт",
                callback_data=DailyReminderSetupScheduleCallbackData.new(
                    schedule={**schedule, "tue": not schedule["tue"]},
                    message_id=daily_reminder_request_message.id,
                    confirm=False
                )
            ),
            InlineKeyboardButton(
                f"{'✅ ' if schedule['wed'] else ''}ср",
                callback_data=DailyReminderSetupScheduleCallbackData.new(
                    schedule={**schedule, "wed": not schedule["wed"]},
                    message_id=daily_reminder_request_message.id,
                    confirm=False
                )
            ),
            InlineKeyboardButton(
                f"{'✅ ' if schedule['thu'] else ''}чт",
                callback_data=DailyReminderSetupScheduleCallbackData.new(
                    schedule={**schedule, "thu": not schedule["thu"]},
                    message_id=daily_reminder_request_message.id,
                    confirm=False
                )
            )
        )
        markup.add(
            InlineKeyboardButton(
                f"{'✅ ' if schedule['fri'] else ''}пт",
                callback_data=DailyReminderSetupScheduleCallbackData.new(
                    schedule={**schedule, "fri": not schedule["fri"]},
                    message_id=daily_reminder_request_message.id,
                    confirm=False
                )
            ),
            InlineKeyboardButton(
                f"{'✅ ' if schedule['sat'] else ''}сб",
                callback_data=DailyReminderSetupScheduleCallbackData.new(
                    schedule={**schedule, "sat": not schedule["sat"]},
                    message_id=daily_reminder_request_message.id,
                    confirm=False
                )
            ),
            InlineKeyboardButton(
                f"{'✅ ' if schedule['sun'] else ''}вс",
                callback_data=DailyReminderSetupScheduleCallbackData.new(
                    schedule={**schedule, "sun": not schedule["sun"]},
                    message_id=daily_reminder_request_message.id,
                    confirm=False
                )
            )
        )
        markup.add(
            InlineKeyboardButton(
                f"Дальше",
                callback_data=DailyReminderSetupScheduleCallbackData.new(schedule=schedule,
                                                                         message_id=daily_reminder_request_message.id,
                                                                         confirm=True)
            )
        )
        await bot.edit_message_reply_markup(message_id=daily_reminder_request_message.id,
                                            chat_id=call.message.chat.id,
                                            reply_markup=markup)


async def daily_reminder_change_schedule_handler(call, bot):
    data = await App().Dao.user.find_by_user_id(call.from_user.id)
    user = UserData(**data)
    callback_data = DailyReminderSetupScheduleCallbackData.parse_and_destroy(call.data)
    schedule = callback_data["schedule"]
    if not callback_data["confirm"]:
        daily_reminder_request_message = {"id": callback_data["message_id"]}
        markup = InlineKeyboardMarkup(row_width=5)
        markup.add(
            InlineKeyboardButton(
                f"{'✅ ' if schedule['mon'] else ''}пн",
                callback_data=DailyReminderSetupScheduleCallbackData.new(
                    schedule={**schedule, "mon": not schedule["mon"]},
                    message_id=callback_data["message_id"],
                    confirm=False
                )
            ),
            InlineKeyboardButton(
                f"{'✅ ' if schedule['tue'] else ''}вт",
                callback_data=DailyReminderSetupScheduleCallbackData.new(
                    schedule={**schedule, "tue": not schedule["tue"]},
                    message_id=callback_data["message_id"],
                    confirm=False
                )
            ),
            InlineKeyboardButton(
                f"{'✅ ' if schedule['wed'] else ''}ср",
                callback_data=DailyReminderSetupScheduleCallbackData.new(
                    schedule={**schedule, "wed": not schedule["wed"]},
                    message_id=callback_data["message_id"],
                    confirm=False
                )
            ),
            InlineKeyboardButton(
                f"{'✅ ' if schedule['thu'] else ''}чт",
                callback_data=DailyReminderSetupScheduleCallbackData.new(
                    schedule={**schedule, "thu": not schedule["thu"]},
                    message_id=callback_data["message_id"],
                    confirm=False
                )
            )
        )
        markup.add(
            InlineKeyboardButton(
                f"{'✅ ' if schedule['fri'] else ''}пт",
                callback_data=DailyReminderSetupScheduleCallbackData.new(
                    schedule={**schedule, "fri": not schedule["fri"]},
                    message_id=callback_data["message_id"],
                    confirm=False
                )
            ),
            InlineKeyboardButton(
                f"{'✅ ' if schedule['sat'] else ''}сб",
                callback_data=DailyReminderSetupScheduleCallbackData.new(
                    schedule={**schedule, "sat": not schedule["sat"]},
                    message_id=callback_data["message_id"],
                    confirm=False
                )
            ),
            InlineKeyboardButton(
                f"{'✅ ' if schedule['sun'] else ''}вс",
                callback_data=DailyReminderSetupScheduleCallbackData.new(
                    schedule={**schedule, "sun": not schedule["sun"]},
                    message_id=callback_data["message_id"],
                    confirm=False
                )
            )
        )
        markup.add(
            InlineKeyboardButton(
                f"Дальше",
                callback_data=DailyReminderSetupScheduleCallbackData.new(schedule=schedule,
                                                                         message_id=callback_data["message_id"],
                                                                         confirm=True)
            )
        )
        daily_reminder_request_message = await bot.edit_message_reply_markup(message_id=callback_data["message_id"],
                                                                             chat_id=call.message.chat.id,
                                                                             reply_markup=markup)
    else:  # confirmed day choice
        # update notification day information
        await App().Dao.user.update({"user_id": call.from_user.id,
                                     "reminders": {
                                         **user.reminders,
                                         "days": [k for k, v in schedule.items() if v == True]
                                     }
                                     })
        await bot.delete_message(chat_id=call.from_user.id, message_id=callback_data["message_id"])
        schedule = {
            "7:00": False,
            "8:00": False,
            "9:00": False,
            "10:00": False,
            "11:00": False,
            "12:00": False,
            "13:00": False,
            "14:00": False,
            "15:00": False,
            "16:00": False,
            "17:00": False,
            "18:00": False,
            "19:00": False,
            "20:00": False,
            "21:00": False,
            "22:00": False,
        }
        daily_reminder_request_message = await bot.send_message(
            text="В какое время (по Москве) присылать напоминание о тренировке?",
            chat_id=call.message.chat.id
        )
        markup = InlineKeyboardMarkup(row_width=5)
        markup.add(
            InlineKeyboardButton(
                f"{'✅ ' if schedule['7:00'] else ''}7:00",
                callback_data=DailyReminderSetupScheduleCallbackData2.new(
                    schedule={**{k: False for k, v in schedule.items()}, "7:00": True},
                    message_id=daily_reminder_request_message.id,
                    confirm=False
                )
            ),
            InlineKeyboardButton(
                f"{'✅ ' if schedule['8:00'] else ''}8:00",
                callback_data=DailyReminderSetupScheduleCallbackData2.new(
                    schedule={**{k: False for k, v in schedule.items()}, "8:00": True},
                    message_id=daily_reminder_request_message.id,
                    confirm=False
                )
            ),
            InlineKeyboardButton(
                f"{'✅ ' if schedule['9:00'] else ''}9:00",
                callback_data=DailyReminderSetupScheduleCallbackData2.new(
                    schedule={**{k: False for k, v in schedule.items()}, "9:00": True},
                    message_id=daily_reminder_request_message.id,
                    confirm=False
                )
            ),
            InlineKeyboardButton(
                f"{'✅ ' if schedule['10:00'] else ''}10:00",
                callback_data=DailyReminderSetupScheduleCallbackData2.new(
                    schedule={**{k: False for k, v in schedule.items()}, "10:00": True},
                    message_id=daily_reminder_request_message.id,
                    confirm=False
                )
            ),
            InlineKeyboardButton(
                f"{'✅ ' if schedule['11:00'] else ''}11:00",
                callback_data=DailyReminderSetupScheduleCallbackData2.new(
                    schedule={**{k: False for k, v in schedule.items()}, "11:00": True},
                    message_id=daily_reminder_request_message.id,
                    confirm=False
                )
            )
        )
        markup.add(
            InlineKeyboardButton(
                f"{'✅ ' if schedule['12:00'] else ''}12:00",
                callback_data=DailyReminderSetupScheduleCallbackData2.new(
                    schedule={**{k: False for k, v in schedule.items()}, "12:00": True},
                    message_id=daily_reminder_request_message.id,
                    confirm=False
                )
            ),
            InlineKeyboardButton(
                f"{'✅ ' if schedule['13:00'] else ''}13:00",
                callback_data=DailyReminderSetupScheduleCallbackData2.new(
                    schedule={**{k: False for k, v in schedule.items()}, "13:00": True},
                    message_id=daily_reminder_request_message.id,
                    confirm=False
                )
            ),
            InlineKeyboardButton(
                f"{'✅ ' if schedule['14:00'] else ''}14:00",
                callback_data=DailyReminderSetupScheduleCallbackData2.new(
                    schedule={**{k: False for k, v in schedule.items()}, "14:00": True},
                    message_id=daily_reminder_request_message.id,
                    confirm=False
                )
            ),
            InlineKeyboardButton(
                f"{'✅ ' if schedule['15:00'] else ''}15:00",
                callback_data=DailyReminderSetupScheduleCallbackData2.new(
                    schedule={**{k: False for k, v in schedule.items()}, "15:00": True},
                    message_id=daily_reminder_request_message.id,
                    confirm=False
                )
            ),
            InlineKeyboardButton(
                f"{'✅ ' if schedule['16:00'] else ''}16:00",
                callback_data=DailyReminderSetupScheduleCallbackData2.new(
                    schedule={**{k: False for k, v in schedule.items()}, "16:00": True},
                    message_id=daily_reminder_request_message.id,
                    confirm=False
                )
            )
        )
        markup.add(
            InlineKeyboardButton(
                f"{'✅ ' if schedule['17:00'] else ''}17:00",
                callback_data=DailyReminderSetupScheduleCallbackData2.new(
                    schedule={**{k: False for k, v in schedule.items()}, "17:00": True},
                    message_id=daily_reminder_request_message.id,
                    confirm=False
                )
            ),
            InlineKeyboardButton(
                f"{'✅ ' if schedule['18:00'] else ''}18:00",
                callback_data=DailyReminderSetupScheduleCallbackData2.new(
                    schedule={**{k: False for k, v in schedule.items()}, "18:00": True},
                    message_id=daily_reminder_request_message.id,
                    confirm=False
                )
            ),
            InlineKeyboardButton(
                f"{'✅ ' if schedule['19:00'] else ''}19:00",
                callback_data=DailyReminderSetupScheduleCallbackData2.new(
                    schedule={**{k: False for k, v in schedule.items()}, "19:00": True},
                    message_id=daily_reminder_request_message.id,
                    confirm=False
                )
            ),
            InlineKeyboardButton(
                f"{'✅ ' if schedule['20:00'] else ''}20:00",
                callback_data=DailyReminderSetupScheduleCallbackData2.new(
                    schedule={**{k: False for k, v in schedule.items()}, "20:00": True},
                    message_id=daily_reminder_request_message.id,
                    confirm=False
                )
            ),
            InlineKeyboardButton(
                f"{'✅ ' if schedule['21:00'] else ''}21:00",
                callback_data=DailyReminderSetupScheduleCallbackData2.new(
                    schedule={**{k: False for k, v in schedule.items()}, "21:00": True},
                    message_id=daily_reminder_request_message.id,
                    confirm=False
                )
            )
        )
        markup.add(
            InlineKeyboardButton(
                f"{'✅ ' if schedule['22:00'] else ''}22:00",
                callback_data=DailyReminderSetupScheduleCallbackData2.new(
                    schedule={**{k: False for k, v in schedule.items()}, "22:00": True},
                    message_id=daily_reminder_request_message.id,
                    confirm=False
                )
            )
        )
        markup.add(
            InlineKeyboardButton(
                f"Дальше",
                callback_data=DailyReminderSetupScheduleCallbackData2.new(schedule=schedule,
                                                                          message_id=daily_reminder_request_message.id,
                                                                          confirm=True)
            )
        )
        await bot.edit_message_reply_markup(message_id=daily_reminder_request_message.id,
                                            chat_id=call.message.chat.id,
                                            reply_markup=markup)


async def daily_reminder_change_schedule_handler2(call, bot):
    data = await App().Dao.user.find_by_user_id(call.from_user.id)
    user = UserData(**data)
    callback_data = DailyReminderSetupScheduleCallbackData2.parse_and_destroy(call.data)
    schedule = callback_data["schedule"]
    if not callback_data["confirm"]:
        markup = InlineKeyboardMarkup(row_width=5)
        markup.add(
            InlineKeyboardButton(
                f"{'✅ ' if schedule['7:00'] else ''}7:00",
                callback_data=DailyReminderSetupScheduleCallbackData2.new(
                    schedule={**{k: False for k, v in schedule.items()}, "7:00": True},
                    message_id=callback_data["message_id"],
                    confirm=False
                )
            ),
            InlineKeyboardButton(
                f"{'✅ ' if schedule['8:00'] else ''}8:00",
                callback_data=DailyReminderSetupScheduleCallbackData2.new(
                    schedule={**{k: False for k, v in schedule.items()}, "8:00": True},
                    message_id=callback_data["message_id"],
                    confirm=False
                )
            ),
            InlineKeyboardButton(
                f"{'✅ ' if schedule['9:00'] else ''}9:00",
                callback_data=DailyReminderSetupScheduleCallbackData2.new(
                    schedule={**{k: False for k, v in schedule.items()}, "9:00": True},
                    message_id=callback_data["message_id"],
                    confirm=False
                )
            ),
            InlineKeyboardButton(
                f"{'✅ ' if schedule['10:00'] else ''}10:00",
                callback_data=DailyReminderSetupScheduleCallbackData2.new(
                    schedule={**{k: False for k, v in schedule.items()}, "10:00": True},
                    message_id=callback_data["message_id"],
                    confirm=False
                )
            ),
            InlineKeyboardButton(
                f"{'✅ ' if schedule['11:00'] else ''}11:00",
                callback_data=DailyReminderSetupScheduleCallbackData2.new(
                    schedule={**{k: False for k, v in schedule.items()}, "11:00": True},
                    message_id=callback_data["message_id"],
                    confirm=False
                )
            )
        )
        markup.add(
            InlineKeyboardButton(
                f"{'✅ ' if schedule['12:00'] else ''}12:00",
                callback_data=DailyReminderSetupScheduleCallbackData2.new(
                    schedule={**{k: False for k, v in schedule.items()}, "12:00": True},
                    message_id=callback_data["message_id"],
                    confirm=False
                )
            ),
            InlineKeyboardButton(
                f"{'✅ ' if schedule['13:00'] else ''}13:00",
                callback_data=DailyReminderSetupScheduleCallbackData2.new(
                    schedule={**{k: False for k, v in schedule.items()}, "13:00": True},
                    message_id=callback_data["message_id"],
                    confirm=False
                )
            ),
            InlineKeyboardButton(
                f"{'✅ ' if schedule['14:00'] else ''}14:00",
                callback_data=DailyReminderSetupScheduleCallbackData2.new(
                    schedule={**{k: False for k, v in schedule.items()}, "14:00": True},
                    message_id=callback_data["message_id"],
                    confirm=False
                )
            ),
            InlineKeyboardButton(
                f"{'✅ ' if schedule['15:00'] else ''}15:00",
                callback_data=DailyReminderSetupScheduleCallbackData2.new(
                    schedule={**{k: False for k, v in schedule.items()}, "15:00": True},
                    message_id=callback_data["message_id"],
                    confirm=False
                )
            ),
            InlineKeyboardButton(
                f"{'✅ ' if schedule['16:00'] else ''}16:00",
                callback_data=DailyReminderSetupScheduleCallbackData2.new(
                    schedule={**{k: False for k, v in schedule.items()}, "16:00": True},
                    message_id=callback_data["message_id"],
                    confirm=False
                )
            )
        )
        markup.add(
            InlineKeyboardButton(
                f"{'✅ ' if schedule['17:00'] else ''}17:00",
                callback_data=DailyReminderSetupScheduleCallbackData2.new(
                    schedule={**{k: False for k, v in schedule.items()}, "17:00": True},
                    message_id=callback_data["message_id"],
                    confirm=False
                )
            ),
            InlineKeyboardButton(
                f"{'✅ ' if schedule['18:00'] else ''}18:00",
                callback_data=DailyReminderSetupScheduleCallbackData2.new(
                    schedule={**{k: False for k, v in schedule.items()}, "18:00": True},
                    message_id=callback_data["message_id"],
                    confirm=False
                )
            ),
            InlineKeyboardButton(
                f"{'✅ ' if schedule['19:00'] else ''}19:00",
                callback_data=DailyReminderSetupScheduleCallbackData2.new(
                    schedule={**{k: False for k, v in schedule.items()}, "19:00": True},
                    message_id=callback_data["message_id"],
                    confirm=False
                )
            ),
            InlineKeyboardButton(
                f"{'✅ ' if schedule['20:00'] else ''}20:00",
                callback_data=DailyReminderSetupScheduleCallbackData2.new(
                    schedule={**{k: False for k, v in schedule.items()}, "20:00": True},
                    message_id=callback_data["message_id"],
                    confirm=False
                )
            ),
            InlineKeyboardButton(
                f"{'✅ ' if schedule['21:00'] else ''}21:00",
                callback_data=DailyReminderSetupScheduleCallbackData2.new(
                    schedule={**{k: False for k, v in schedule.items()}, "21:00": True},
                    message_id=callback_data["message_id"],
                    confirm=False
                )
            )
        )
        markup.add(
            InlineKeyboardButton(
                f"{'✅ ' if schedule['22:00'] else ''}22:00",
                callback_data=DailyReminderSetupScheduleCallbackData2.new(
                    schedule={**{k: False for k, v in schedule.items()}, "22:00": True},
                    message_id=callback_data["message_id"],
                    confirm=False
                )
            )
        )
        markup.add(
            InlineKeyboardButton(
                f"Дальше",
                callback_data=DailyReminderSetupScheduleCallbackData2.new(schedule=schedule,
                                                                          message_id=callback_data["message_id"],
                                                                          confirm=True)
            )
        )
        await bot.edit_message_reply_markup(message_id=callback_data["message_id"],
                                            chat_id=call.message.chat.id,
                                            reply_markup=markup)
    else:
        await bot.delete_message(chat_id=call.from_user.id, message_id=callback_data["message_id"])
        time = next(k for k, v in schedule.items() if v == True)
        time = datetime.datetime.strptime(time, '%H:%M')
        # update notification time information
        await App().Dao.user.update({"user_id": call.from_user.id,
                                     "reminders": {
                                         **user.reminders,
                                         "time": time,
                                         "has_been_requested_before": True
                                     },
                                     "temp_data": {k: v for k, v in user.temp_data.items() if k != "last_message"}
                                     })
        await bot.send_message(text="<b>Ура! Теперь я буду напоминать тебе о тренировках 🎉</b>",
                               chat_id=call.message.chat.id,
                               parse_mode="HTML")
        last_message = jsonpickle.decode(user.temp_data["last_message"])
        await voice_handler(last_message, bot)


async def make_string_good_for_markdown(text, es_list=None, ignore_list=[]):
    escapt_list = ['_', '*', '[', ']', '(', ')', '~', '>', '#', '+', '-', '=', '|', '{', '}', '.', '!', '+']

    if es_list is not None:
        escapt_list = es_list

    escapt_list = [i for i in escapt_list if i not in ignore_list]

    for el in escapt_list:
        text = text.replace(el, f'\\{el}')
    return text


async def number_of_text_messages_in_current_dialog(user_id):
    data = await App().Dao.user.find_by_user_id(user_id)
    user = UserData(**data)
    current_dialog = user.messages[user.first_message_index:]
    user_text_messages = [m for m in current_dialog if m["role"] == "user" and not m["voice_file_id"]]
    return len(user_text_messages)


def text_messages_warning(handler_func):
    """
    we want the user to have a conversation using mostly voice messages
    this decorator sends a warning to the user when they send a text message
    """
    TEXT_MESSAGES_ALLOWED = 3
    FIRST_WARNING = (
        "❗️ Если не практиковаться - ничему не научишься! Сейчас я отвечу на твое сообщение, но мне больше нравится слушать твои голосовые 🥰\n\n"
        "В этом диалоге можешь еще отправить мне текстовых сообщений: {text_messages_available}")
    SECOND_WARNING = (
        "❗️ Давай попрактикуем разговор? Я верю, что у тебя была веская причина записать это сообщение текстом, а не голосом, поэтому я отвечу на него, но в следующий раз, пожалуйста, запиши мне голосовое 🥰\n\n"
        "В этом диалоге можешь еще отправить мне текстовых сообщений: {text_messages_available}")
    THIRD_WARNING = (
        "❗️ Пришла пора признаться. Мои процессоры сгорают от текстовых сообщений 😓 Но так уж и быть, из последних сил постараюсь ответить. В следующий раз, пожалуйста, говори только голосом, или сотри мне память при помощи /start\n\n"
        "В этом диалоге можешь еще отправить мне текстовых сообщений: {text_messages_available}")
    FINAL_ERROR = "❗️ Бот просил вам передать, что все его текстовые процессоры сгорели. Можете продолжить общаться голосом, или создать новый диалог при помощи /start"

    async def wrapper(message: Message, bot: AsyncTeleBot):
        if message.content_type == "text":
            n_text_messages = await number_of_text_messages_in_current_dialog(message.from_user.id)
            if n_text_messages == 0:
                await bot.send_message(
                    text=FIRST_WARNING.format(text_messages_available=TEXT_MESSAGES_ALLOWED - n_text_messages - 1),
                    chat_id=message.chat.id
                )
                return await handler_func(message, bot)
            elif n_text_messages == 1:
                await bot.send_message(
                    text=SECOND_WARNING.format(text_messages_available=TEXT_MESSAGES_ALLOWED - n_text_messages - 1),
                    chat_id=message.chat.id
                )
                return await handler_func(message, bot)
            elif n_text_messages == 2:
                await bot.send_message(
                    text=THIRD_WARNING.format(text_messages_available=TEXT_MESSAGES_ALLOWED - n_text_messages - 1),
                    chat_id=message.chat.id
                )
                return await handler_func(message, bot)
            else:
                await bot.send_message(text=FINAL_ERROR, chat_id=message.chat.id)
                return
        else:
            return await handler_func(message, bot)

    return wrapper


@send_bot_using_logs
@send_error_logs
@daily_reminder_request_wrapper
# @text_messages_warning
async def voice_handler(message: Message, bot: AsyncTeleBot):
    data = await App().Dao.user.find_by_user_id(message.from_user.id)
    user = UserData(**data)
    if App().Tasks.get(user.user_id):
        App().Tasks[user.user_id].cancel()
    input_msg = None
    input_voice_id = None
    input_duration = 10  # default duration for text messages

    if message.content_type == "voice":
        input_voice_id = message.voice.file_id
        voice = await bot.get_file(input_voice_id)
        downloaded_file = await bot.download_file(voice.file_path)
        voice_bytesio = io.BytesIO(downloaded_file)
        voice_bytesio.name = 'voice.mp3'
        input_msg = voice_bytesio
        ogg_audio = AudioSegment.from_file(voice_bytesio, format="ogg")
        input_duration = len(ogg_audio) / 1000
    elif message.content_type == "text":
        input_msg = message.text

    if input_duration >= 5:
        emj = np.random.choice(list('👍👌🤔💋🥰🤗❤️‍🔥😊☺️ '))
        await set_message_reaction(
            App()['config']['bot']['token'],
            message.chat.id,
            message.id,
            emj
        )

    response_text, input_text, tokens_count = await voice_chat(message, input_msg)
    await bot.send_chat_action(chat_id=message.chat.id, action="record_voice")
    response_voice_audio, response_duration = await text_to_voice_with_duration(response_text)
    response_voice_message = await bot.send_voice(
        voice=response_voice_audio,
        chat_id=message.chat.id,
        reply_markup=create_conv_reply_markup()
    )
    await bot.send_message(
        chat_id=message.chat.id,
        text=f'🎙 ||{markdown_escaped(response_text)}||',
        # text=markdown_escaped(response_text),
        parse_mode='MarkdownV2'
    )

    await App().Dao.user.update(
        {
            "user_id": message.from_user.id,
            "messages": [
                *user.messages,
                {"role": "user", "content": input_text, "voice_file_id": input_voice_id,
                 "voice_duration": input_duration, "created_at": datetime.datetime.now(),
                 "tokens": tokens_count},
                {"role": "assistant", "content": response_text,
                 "voice_file_id": response_voice_message.voice.file_id, "voice_duration": response_duration,
                 "created_at": datetime.datetime.now()}
            ]
            ,
            "temp_data": await pop_from_dict(user.temp_data, ['hints', 'transcript_in_ru', 'suggest', 'suggest_id'])
        }
    )
    task = asyncio.create_task(send_stuck_reminder(message, bot))
    App().Tasks[user.user_id] = task

    if np.random.random() > 0.45:
        await bot.send_chat_action(chat_id=message.chat.id, action="typing")
        random_topik = np.random.choice(list(words_4_using.keys()))

        tips_list = words_4_using[random_topik]
        tip = np.random.choice(tips_list)

        heads = ['Попробуй использовать фразу', 'Фразочка для использования',
                 'Рекомендую упомянуть фразу', 'Обогати свою речь',
                 'Запомни фразу', 'Тебе на заметку:', 'Используй в речи',
                 'Ответь, используя это', 'А теперь ответь использую это', 'Давай потренируем это',
                 'Бери в ход фразочку', 'Ты знал эту фразу?',
                 'Обогати свою речь фразой', 'Попробуй использовать в ответе']

        head_intro = np.random.choice(heads)

        text_with_tip = f'''🧩 {head_intro} 👇\n\n{tip}'''
        await asyncio.sleep(3)

        text_with_tip = await make_string_good_for_markdown(text_with_tip, ignore_list=['*'])
        await bot.send_message(text=text_with_tip, chat_id=message.chat.id, parse_mode='MarkdownV2')

    return response_voice_message


async def not_conv_voice(message: Message, bot: AsyncTeleBot):
    not_conv_alert = ('If you want to start a new session please send /start.\n\n'
                      'Если Вы хотите начать новую сессию нажмите /start')
    await bot.send_message(text=not_conv_alert, chat_id=message.chat.id)


async def is_user_subscribed(user: UserData):
    membership_settings = App()["config"]["settings"]["membership_check"]
    if membership_settings["enabled"]:
        membership = await App().Bot.get_chat_member(membership_settings["group_id"], user.user_id)
        if membership.status in USER_NOT_IN_GROUP_STATUSES:
            return False
        else:
            return True
    else:
        return True


async def daily_limit(user: UserData):
    NOT_SUBSCRIBED_LIMIT = 3
    SUBSCRIBED_LIMIT = 50
    if user.subscription == "free":
        if await is_user_subscribed(user):
            return SUBSCRIBED_LIMIT
        else:
            return NOT_SUBSCRIBED_LIMIT
    elif user.subscription == "premium":
        return 100


async def daily_limit_minutes(user: UserData):
    """
    returns daily limit in minutes for the user
    """
    NOT_SUBSCRIBED_LIMIT = 3
    SUBSCRIBED_LIMIT = 5
    if user.subscription == "free":
        if await is_user_subscribed(user):
            return SUBSCRIBED_LIMIT
        else:
            return NOT_SUBSCRIBED_LIMIT
    elif user.subscription == "premium":
        return 100


def add_mark_to_img(bin_image: bytes) -> bytes:
    pil_img = Image.open(io.BytesIO(bin_image)).convert('RGBA')
    final_image = Image.alpha_composite(pil_img, mask)

    img_byte_arr = io.BytesIO()
    final_image.save(img_byte_arr, format='PNG')
    return img_byte_arr.getvalue()


async def send_help(message: Message, bot: AsyncTeleBot):
    if App().Tasks.get(message.from_user.id):
        App().Tasks[message.from_user.id].cancel()

    if message.from_user.id in App()["config"]["bot"]["administrators"]["users"]:
        help_text = help_message_admins
    else:
        help_text = help_message

    await bot.send_message(text=help_text, chat_id=message.chat.id)
