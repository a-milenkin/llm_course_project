# send_welcome
def get_start_texts(name: str, is_new: bool):
    if is_new:
        start_text0 = f"🥳 I'm so excited to see you here{name}!"
    else:
        start_text0 = f"🙋‍♀️ Привет{name}!"

    start_text = f'''{start_text0}\n🎯 Давай болтать, используя голосовые сообщения?!'''
    start_text1 = f'''{start_text}\n💬 Я поддержу беседу любой сложности, давая подсказки'''
    start_text2 = f'''{start_text1}\n🧩 Со мной ты закрепишь сотни разговорных фраз'''
    start_text3 = f'''{start_text2}\n👌 Ты избавишься от ошибок в речи и улучшишь произношение!'''
    start_text4 = f'''{start_text3}\n🏃‍♂️ Всего 15 минут ежедневного общения со мной прокачают твой английский за месяц!'''

    if is_new:
        start_text5 = f'''{start_text4}\n\n🗯 Запиши голосовое, как прошел твой день или что ты ел сегодня на завтрак на английском!'''
        return start_text0, start_text, start_text1, start_text2, start_text3, start_text4, start_text5

    # start_text5 = f'''{start_text4}\n<b>Кстати, боту можно задать тему для разговора 👉 /topics</b>'''
    return start_text0, start_text, start_text1, start_text2, start_text3, start_text4,


start_response_text = '🚀 Let’s start!\n\nTell me about your day or what have you eaten at breakfast today?'


def roles_text(current_role):
    return f'Select a topic or suggest your own\nCurrent topic: {current_role}'


additional_topics = ['💼 Career and background','👨‍🚀 About working style',
                     '🙋 Assumed problem', '🕵️‍♂️ Looking for a job', 
                     '🧠🚀 The problem of seeing creativity', '🎯 Career goals',
                     '👨‍💼 Meeting at work', '👩‍🏫 Business presentation',
                     '📈 Leadership and management', '🗂 Roles and responsibilities',
                     '🏡 Working from home', '🌙 overtime',
                     '💰 Salary', '🙋‍♂️ Raise and promotion',
                     '👔 Relationships at work', '👨‍🍼Relationships and family',
                     '🤼 Competition at work', '💂‍♀️ Side job',
                     '👨‍🦳 Retirement planning', '🤑 Personal finance', 
                     '🚀 Start a business 💡']


roles = ['👨‍🍼 Relationships and family', '🚀 Start a business 💡',
         '🕵️‍♂️ Looking for a job', '🧠 The problem of seeing creativity',
         '💼 Traveling', '♥️ Dates and acquaintances 💐', '🎧 Music and films 🎬']

# roles = ['Relationships and family', 'Start a business',
#          'Looking for a job', 'The problem of seeing creativity',
#          'Traveling', 'Dates and acquaintances', 'Music and films']

roles.append('create a topic')  # must be in end, don't change


def after_set_up_role_text(role: str) -> str:
    return f"Ok, now the bot will keep topic: {role}"


create_role_by_user_text = ("Напиши, кем быть боту (например, my best friend, psychologist, historian и др.)\n"
                            "Пиши на английском")
failed_create_role_text = ("Кажется, такая роль не подходит 🤔\n"
                           "Попробуй ввести существительное с описанием или имя известного "
                           "человека в качестве роли для бота. Пиши на английском")

# send_help
help_message = (

    '🚀 Я Chatodor, создан для эффективной практики вашего английского. Я погружаю в реальную разговорную среду с носителем.\n'
    'Я сделан на базе GigaChat, передовой российской llm, разработанной командой Сбербанка\n\n'
    '👩‍💻 Наши исследования показали; чтобы заметно улучшить свои навыки устной и письменной речи, вам достаточно всего недели работы со мной (от 15 минут в день)! 🚀'
    '📈 Вы можете легко отслеживать свой прогресс в /profile и /rating.\n\n'
)
help_message_admins = (
    f"{help_message}\n\n"
    "For Admins:\n"
    "/admins - команда для вывода метрик\n"
    "!info@<user_id> - команда для вывода профиля пользователя по его id"
)

reminder_text = ('Если не знаешь, как ответить, можешь воспользоваться '
                 'sos кнопкой, я подскажу тебе, как можно продолжить разговор')

hints_text = ('You can use these options to continue the conversation:\n'
              'Можете воспользоваться этими вариантами продолжения разговора:')
hint_callback_text = "Repeat after me 👇"
after_finish_text = 'You are finished, use /start for new session'

# keyboard markup
en_transcript_text = '🇬🇧 Text the same in English'
ru_transcript_text = '🇷🇺 Написать то же самое на Русском'
sos_text = "🆘 I'm stuck! Hints, please"
rating_text = "🕰 Сколько я наговорил?"
finish_text = '🏁 Finish & get feedback'


# upload user file
file_upload_text = ("Можешь отправить файл со своими материалами (txt, pdf), или можешь просто отправить "
                    "материалы текстовым сообщением, а еще ты можешь отправить ссылку на статью и мы сможем "
                    "работать по ней 🙃, а если передумал, нажми кнопку cancel")


def get_success_upload_text(file_type: str, file_name: str) -> str:
    if file_type in ["txt", "pdf"]:
        if file_name is not None:
            success_upload_text = f"Файл {file_name} успешно сохранен.\n"
        else:
            success_upload_text = f"Файл успешно сохранен.\n"
    elif file_type == "url":
        success_upload_text = f"Статья успешно обработана.\n"
    else:
        raise ValueError(f"file type {file_type} is not supported, please choose from [txt, pdf, url]")

    return success_upload_text + ("Теперь я буду использовать твои материалы в наших разговорах, "
                                  "пока ты их не освоишь ☺️\n")


wrong_file_extension = ("Пожалуйста, отправьте файл в формате txt или pdf, или просто текстовое сообщение, "
                        "или валидную ссылку на статью")
