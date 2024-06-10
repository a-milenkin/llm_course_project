import string
import emoji


def is_english(text):
    allowed_chars = set(string.ascii_letters + string.punctuation + string.whitespace)
    return all(char in allowed_chars or emoji.is_emoji(char) for char in text)


def is_russian(text):
    russian_letters = 'абвгдеёжзийклмнопрстуфхцчшщъыьэюяn'
    allowed_chars = set(russian_letters + russian_letters.upper() + string.punctuation + string.whitespace)
    return all(char in allowed_chars or emoji.is_emoji(char) for char in text)
