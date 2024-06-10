import aiohttp


async def set_message_reaction(token, chat_id, message_id, reaction, is_big=False):
    """
    Отправить реакцию на сообщение пользователя
    :param token: токен тг бота
    :param chat_id: id чата с пользователем
    :param message_id: id сообщения для реакции
    :param reaction: строка содержащая один из возможных emoji
    :param is_big: Pass True to set the reaction with a big animation (Telegram API Docs)
    :return: ответ на апи запрос, в случае успеха: {'ok': True, 'result': True}
    """

    url = f"https://api.telegram.org/bot{token}/setMessageReaction"
    reactions = [{"type": "emoji", "emoji": reaction}]
    data = {
        "chat_id": chat_id,
        "message_id": message_id,
        "reaction": reactions,
        "is_big": is_big
    }
    async with aiohttp.ClientSession() as session:
        async with session.post(url, json=data) as response:
            return await response.json()
