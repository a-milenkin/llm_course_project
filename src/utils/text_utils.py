import string


def is_english(text):
    allowed_chars = set(string.ascii_letters + string.punctuation + string.whitespace)
    return all(char in allowed_chars for char in text)


def is_russian(text):
    russian_letters = 'абвгдеёжзийклмнопрстуфхцчшщъыьэюя'
    allowed_chars = set(russian_letters + russian_letters.upper() + string.punctuation + string.whitespace)
    return all(char in allowed_chars for char in text)


def markdown_escaped(text):
    for char in ["!", "'", "`", ".", "-", "(", ")", "<", ">", "*", "+"]:
        text = text.replace(char, f'\{char}')
    return text
