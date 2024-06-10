import glob
import os
import uuid

from telebot.async_telebot import AsyncTeleBot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
from telebot.types import Message, CallbackQuery

from models.app import App
from routes.texts import file_upload_text, wrong_file_extension, get_success_upload_text
from utils.callback_factories import FileUploadCallbackData
from utils.send_to_admin import send_error_logs, send_bot_using_logs
from utils.similarity_search import SimilaritySearch, is_url
from utils.structures import UserData


async def upload_user_file(message: Message, bot: AsyncTeleBot):
    data = await App().Dao.user.find_by_user_id(message.from_user.id)
    user = UserData(**data)
    markup = InlineKeyboardMarkup()
    markup.add(
        InlineKeyboardButton(
            f"Cancel",
            callback_data=FileUploadCallbackData.new(bot_state=user.bot_state)
        )
    )
    await App().Dao.user.update(
        {
            "user_id": message.from_user.id,
            "bot_state": "file_uploading"
        }
    )
    await bot.send_message(text=file_upload_text, chat_id=message.chat.id, reply_markup=markup)


async def upload_user_file_callback(call: CallbackQuery, bot: AsyncTeleBot):
    callback_data = FileUploadCallbackData.parse_and_destroy(call.data)
    await App().Dao.user.update(
        {
            "user_id": call.from_user.id,
            "bot_state": callback_data['bot_state']
        }
    )
    await bot.delete_message(call.message.chat.id, call.message.id)


def delete_existing_user_file(path):
    # Ищем все файлы, начинающиеся на 'user_file.' с любым расширением
    existing_files = glob.glob(os.path.join(path, 'user_file.*'))
    for file in existing_files:
        os.remove(file)
        print(f"Deleted existing file: {file}")


@send_bot_using_logs
@send_error_logs
async def save_user_file(message: Message, bot: AsyncTeleBot):
    # print('message content_type: ', message.content_type)
    # if message.content_type == 'document':
    #     print('message document.mime_type: ', message.document.mime_type)
    data = await App().Dao.user.find_by_user_id(message.from_user.id)
    user = UserData(**data)

    file_info = await bot.get_file(message.document.file_id)
    file_extension = file_info.file_path.split('.')[-1]
    if file_extension in ['pdf', 'txt']:
        print(file_info.file_path)
        downloaded_file = await bot.download_file(file_info.file_path)

    else:
        return await bot.send_message(chat_id=message.chat.id, text=wrong_file_extension)

    # random_file_name = str(uuid.uuid4()) + '.txt'

    if not os.path.exists(f'assets/user_files/{user.user_id}'):
        os.mkdir(f'assets/user_files/{user.user_id}')

    delete_existing_user_file(f"assets/user_files/{user.user_id}")

    # заглушка на один файл: постоянно будет перезаписываться один файл
    # потом нужно будет заменить user_file.txt в пути на random_file_name
    file_path = f"assets/user_files/{user.user_id}/user_file.{file_info.file_path.split('.')[-1]}"
    with open(file_path, 'wb') as new_file:
        new_file.write(downloaded_file)

    # сохранение индекса поиска по файлу
    user_file_db = SimilaritySearch(
        file_path,
        f'assets/user_files/{user.user_id}/index'
    )

    await App().Dao.user.update(
        {
            "user_id": message.from_user.id,
            "bot_state": "conversation",
            "user_file_idx": 0
        }
    )
    file_name = message.document.file_name
    success_upload_text = get_success_upload_text(file_extension, file_name)
    response = await bot.send_message(chat_id=message.chat.id, text=success_upload_text)

    return response


@send_bot_using_logs
@send_error_logs
async def save_user_file_from_text(message: Message, bot: AsyncTeleBot):
    data = await App().Dao.user.find_by_user_id(message.from_user.id)
    user = UserData(**data)

    downloaded_file = bytes(message.text, 'utf-8')

    # random_file_name = str(uuid.uuid4()) + '.txt'

    if not os.path.exists(f'assets/user_files/{user.user_id}'):
        os.mkdir(f'assets/user_files/{user.user_id}')

    delete_existing_user_file(f"assets/user_files/{user.user_id}")

    # заглушка на один файл: постоянно будет перезаписываться один файл
    # потом нужно будет заменить user_file.txt в пути на random_file_name
    with open(f"assets/user_files/{user.user_id}/user_file.txt", 'wb') as new_file:
        new_file.write(downloaded_file)

    # сохранение индекса поиска по файлу
    user_file_db = SimilaritySearch(
        f'assets/user_files/{user.user_id}/user_file.txt',
        f'assets/user_files/{user.user_id}/index'
    )

    await App().Dao.user.update(
        {
            "user_id": message.from_user.id,
            "bot_state": "conversation",
            "user_file_idx": 0
        }
    )
    file_type = 'txt'
    if is_url(message.text):
        file_type = 'url'

    success_upload_text = get_success_upload_text(file_type, None)
    response = await bot.send_message(chat_id=message.chat.id, text=success_upload_text)

    return response
