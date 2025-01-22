import re
import telebot
import pandas as pd
from io import BytesIO
from telebot import types

token = ''
bot = telebot.TeleBot(token)

teachers = {'1': 1,
            '2': 2}  # Для отправки сообщения конкретному преподавателю нужно добавить ФИО и Telegram ID в данный список

current_df = {}

@bot.message_handler(commands=['start'])
def handle_start(message):
    bot.send_message(message.chat.id, "Данный бот выполняет задания 3 и 7 - проверка заполнений тем урока и подсчет пар у выбранной/ых групп соответсвенно.\nДля работы бота отправьте файл 'Отчет по темам занятий.xls'")

@bot.message_handler(content_types=['document'])
def handle_document(message):
    global current_df
    document = message.document
    file_info = bot.get_file(document.file_id)
    file = bot.download_file(file_info.file_path)
    df = pd.read_excel(BytesIO(file), engine='openpyxl')
    current_df[message.from_user.id] = df

    unique_groups = df['Группа'].unique()
    markup = types.ReplyKeyboardMarkup(one_time_keyboard=True)
    markup.add(types.KeyboardButton("Завершить работу бота"))
    for group in unique_groups:
        markup.add(types.KeyboardButton(group))

    misspelled = 0
    for themes in df['Тема урока']:
        if not re.match(r'^Урок №\d+\. Тема:.*', themes):
            misspelled += 1
    if misspelled >= 1:
        markup = types.ReplyKeyboardMarkup(one_time_keyboard=True)
        markup.add(types.KeyboardButton("Да"), types.KeyboardButton("Нет"))
        bot.send_message(message.chat.id,
                         "Было найдено " + str(misspelled) + " неправильно введенных тем уроков. Стоит ли уведомить преподавателей?",
                         reply_markup=markup)
        bot.register_next_step_handler(message, process_notify_step)
    else:
        bot.send_message(message.chat.id, "Теперь вы можете посмотреть количество пар по каждому предмету у выбираемой/ых групп. Выберите группу:", reply_markup=markup)
        bot.register_next_step_handler(message, process_group_step)

def process_notify_step(message):
    if message.text.strip().upper() == "ДА":
        user_id = message.from_user.id
        df = current_df.get(user_id)

        notifications = {}
        incorrect_entries = {}

        for index, row in df.iterrows():
            if row['Тема урока'] and not re.match(r'^Урок №\d+\. Тема:.*', row['Тема урока']):
                teacher_name = row['ФИО преподавателя']
                if teacher_name not in incorrect_entries:
                    incorrect_entries[teacher_name] = []

                incorrect_entries[teacher_name].append(row['Тема урока'])

        notificated = 0
        for teacher_name, issues in incorrect_entries.items():
            text_filename = f"{teacher_name.replace(' ', '_')}_неправильные_темы.txt"
            with open(text_filename, 'w', encoding='utf-8') as f:
                for issue in issues:
                    f.write(issue + '\n')

            message_text = f"Здравствуйте, {teacher_name}, я бот.\nХочу уведомить вас о том, что у вас неправильно введенные темы уроков.\nПрикреплён файл с неправильными темами."
            try:
                bot.send_message(teachers[teacher_name], message_text)
                with open(text_filename, 'rb') as file_to_send:
                    bot.send_document(teachers[teacher_name], file_to_send, caption="Неправильные темы")
                notificated += 1
            except KeyError:
                bot.send_message(message.chat.id,
                                 f"Преподавателя \"{teacher_name}\" нет в базе.\nСообщение не было отправленно.")
        if notificated < len(notifications):
            bot.send_message(message.chat.id, "Не все преподаватели были уведомлены.")
        else:
            bot.send_message(message.chat.id, "Преподаватели уведомлены.")
    else:
        bot.send_message(message.chat.id, "Преподаватели не уведомлены.")

    user_id = message.from_user.id
    df = current_df.get(user_id)

    unique_groups = df['Группа'].unique()
    markup = types.ReplyKeyboardMarkup(one_time_keyboard=True)
    markup.add(types.KeyboardButton("Завершить работу бота"))
    for group in unique_groups:
        markup.add(types.KeyboardButton(group))

    bot.send_message(message.chat.id, "Теперь вы можете посмотреть количество пар по каждому предмету у выбираемой/ых групп. Выберите группу:", reply_markup=markup)
    bot.register_next_step_handler(message, process_group_step)

def process_group_step(message):
    if message.text == "Завершить работу бота":
        markup = types.ReplyKeyboardRemove()
        bot.send_message(message.chat.id, "Кнопки удалены.", reply_markup=markup)
        bot.send_message(message.chat.id, "Работа бота завершена. Если хотите начать заново, введите либо нажмите на /start.")
        return

    user_id = message.from_user.id
    df = current_df.get(user_id)

    if df is None:
        bot.send_message(message.chat.id, "Сначала отправьте документ.")
        return

    group_name = message.text
    filtered_data = df[df['Группа'] == group_name]

    pair_counts = filtered_data.groupby('Предмет')['Лента'].count()
    if pair_counts.empty:
        bot.send_message(message.chat.id, "Не найдено пар для группы {}".format(group_name))
    else:
        result_lines = []
        for subject, count in pair_counts.items():
            result_lines.append(f"{subject}\n{count}")
        result = "\n".join(result_lines)
        bot.send_message(message.chat.id, "Количество пар для группы {}:\n{}".format(group_name, result))

    unique_groups = df['Группа'].unique()
    markup = types.ReplyKeyboardMarkup(one_time_keyboard=True)
    markup.add(types.KeyboardButton("Завершить работу бота"))
    for group in unique_groups:
        markup.add(types.KeyboardButton(group))

    bot.send_message(message.chat.id, "Выберите другую группу:", reply_markup=markup)
    bot.register_next_step_handler(message, process_group_step)

if __name__ == '__main__':
    bot.polling(none_stop=True)