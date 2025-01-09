import telebot
import pandas as pd
from io import BytesIO
from telebot import types

token = ''

bot = telebot.TeleBot(token)

# Храним DataFrame во временной переменной
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

    # Загружаем Excel файл в DataFrame
    df = pd.read_excel(BytesIO(file), engine='openpyxl')

    # Сохраняем DataFrame для дальнейшего использования
    current_df[message.from_user.id] = df

    # Извлекаем уникальные группы
    unique_groups = df['Группа'].unique()

    # Создаем клавиатуру с кнопками для выбора группы
    markup = types.ReplyKeyboardMarkup(one_time_keyboard=True)
    for group in unique_groups:
        markup.add(types.KeyboardButton(group))

    bot.send_message(message.chat.id, "Выберите группу:", reply_markup=markup)

    # Ожидаем от пользователя указание группы
    bot.register_next_step_handler(message, process_group_step)

def process_group_step(message):
    user_id = message.from_user.id
    df = current_df.get(user_id)

    if df is None:
        bot.send_message(message.chat.id, "Сначала отправьте документ.")
        return

    group_name = message.text
    # Фильтруем данные по выбранной группе
    filtered_data = df[df['Группа'] == group_name]

    # Считаем количество пар по каждому предмету
    pair_counts = filtered_data.groupby('Предмет')['Лента'].count()

    if pair_counts.empty:
        bot.send_message(message.chat.id, "Не найдено пар для группы {}".format(group_name))
    else:
        result = pair_counts.to_string()
        bot.send_message(message.chat.id, "Количество пар для группы {}:\n{}".format(group_name, result))

    # После обработки снова предлагаем выбрать группу
    # Извлекаем уникальные группы
    unique_groups = df['Группа'].unique()
    markup = types.ReplyKeyboardMarkup(one_time_keyboard=True)
    for group in unique_groups:
        markup.add(types.KeyboardButton(group))

    bot.send_message(message.chat.id, "Выберите другую группу:", reply_markup=markup)

    # Ожидаем от пользователя указание новой группы
    bot.register_next_step_handler(message, process_group_step)

if __name__ == '__main__':
    bot.polling(none_stop=True)