import telebot
import pandas as pd
from io import BytesIO
from telebot import types

token = ''
bot = telebot.TeleBot(token)

current_df = {}

@bot.message_handler(commands=['start'])
def handle_start(message):
    bot.send_message(message.chat.id, "Для работы бота отправьте файл 'Отчет по темам занятий.xls'")

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
    for group in unique_groups:
        markup.add(types.KeyboardButton(group))
    markup.add(types.KeyboardButton("END"))

    bot.send_message(message.chat.id, "Выберите группу:", reply_markup=markup)
    bot.register_next_step_handler(message, process_group_step)
def process_group_step(message):
    if message.text == "END":
        markup = types.ReplyKeyboardRemove()
        bot.send_message(message.chat.id, "Кнопки удалены.", reply_markup=markup)
        bot.send_message(message.chat.id, "Работа бота завершена. Если хотите начать заново, введите /start.")
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
        result = pair_counts.to_string()
        bot.send_message(message.chat.id, "Количество пар для группы {}:\n{}".format(group_name, result))

    unique_groups = df['Группа'].unique()
    markup = types.ReplyKeyboardMarkup(one_time_keyboard=True)
    for group in unique_groups:
        markup.add(types.KeyboardButton(group))
    markup.add(types.KeyboardButton("END"))

    bot.send_message(message.chat.id, "Выберите другую группу:", reply_markup=markup)
    bot.register_next_step_handler(message, process_group_step)

if __name__ == '__main__':
    bot.polling(none_stop=True)