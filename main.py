# Импорт необходимых библиотек
import telebot as tb  # Библиотека для работы с Telegram Bot API
import mysql.connector  # Библиотека для работы с MySQL
from mysql.connector import Error  # Для обработки ошибок MySQL
from dotenv import load_dotenv  # Для загрузки переменных окружения из .env файла
import hashlib  # Для хеширования паролей
import os  # Для работы с операционной системой и переменными окружения

# Загрузка переменных окружения из файла .env
load_dotenv()

# Создание экземпляра бота с токеном из переменных окружения
bot = tb.TeleBot(os.getenv('TOKEN'))

# Словарь для хранения активных сессий пользователей (chat_id: user_id)
sessions = {}

# Конфигурация для подключения к базе данных MySQL
db_config = {
    'host': os.getenv('DB_HOST'),
    'user': os.getenv('DB_USER'),
    'password': os.getenv('DB_PASSWORD'),
    'database': os.getenv('DB_NAME')
}

# Словарь с фразами бота для удобства управления текстами
phrases = {
    'welcome': 'Добро пожаловать в To-Do бот! Выберите действие:',

    'signin': 'Вход',
    'signin_success': 'Вы вошли!',
    'signin_unsuccess': 'Ошибка логина или пароля!',
    'signin_error': 'Произошла ошибка при входе!',

    'signup': 'Регистрация',
    'signup_username': 'Задайте логин:',
    'signup_password': 'Придумайте пароль:',
    'signup_success': 'Вы успешно зарегистрировались!',
    'signup_login_exists': 'Логин уже существует!',
    'signup_error': 'Ошибка при регистрации!',

    'enter_username': 'Введите ваш логин:',
    'enter_password': 'Введите ваш пароль',

    'auth_please': 'Пожалуйста, войдите в систему',

    'menu': 'Главное меню:',
    'items:': 'Ваши заметки:\n\n',
    'get_items': 'Мои заметки',
    'get_items_no_one': 'У вас пока нет заметок',
    'get_items_error': 'Ошибка при получении заметок',

    'create_item': 'Добавить заметку',
    'create_item_text': 'Введите текст заметки:',
    'create_item_success': 'Заметка успешно добавлена!',
    'create_item_unsuccess': 'Ошибка при добавлении заметки!',

    'edit_item': 'Редактировать заметку',
    'edit_item_number': 'Введите номер заметки:',
    'edit_item_text': 'Введите новый текст заметки:',
    'edit_item_success': 'Заметка успешно обновлена!',
    'edit_item_unsuccess': 'Ошибка при обновлении заметки!',
    'edit_item_no_number': 'Некорректный ID заметки! Введите число',
    'edit_item_no_such': 'Заметка с таким ID не найдена или вам не принадлежит!',
    'edit_item_error': 'Ошибка при поиске заметки!',

    'delete_item': '➖ Удалить заметку',
    'delete_item_number': 'Введите номер заметки:',
    'delete_item_success': 'Заметка успешно удалена!',
    'delete_item_unsuccess': 'Ошибка при удалении заметки!',
    'delete_item_no_number': 'Некорректный ID заметки! Введите число',

    'signout': 'Выйти',
    'signout_success': 'Вы вышли из системы'
}

# Функция для установки соединения с базой данных
def get_db_connection():
    try:
        return mysql.connector.connect(**db_config)
    except Error as error:
        raise error

# Функция для хеширования паролей с использованием SHA-256
def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

# Обработчик команды /start - отправляет приветственное сообщение и кнопки входа/регистрации
@bot.message_handler(commands=['start'])
def start_handler(message):
    markup = tb.types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add(phrases['signin'], phrases['signup'])
    bot.send_message(message.chat.id, phrases['welcome'], reply_markup=markup)

# Обработчик кнопки входа - запрашивает логин
@bot.message_handler(func=lambda m: m.text == phrases['signin'])
def login_handler(message):
    message = bot.send_message(message.chat.id, phrases['enter_username'])
    bot.register_next_step_handler(message, process_username_step)

# Обработка введенного логина - запрашивает пароль
def process_username_step(message):
    username = message.text
    message = bot.send_message(message.chat.id, phrases['enter_password'])
    bot.register_next_step_handler(message, process_password_step, username)

# Проверка введенного пароля и авторизация пользователя
def process_password_step(message, username):
    password = message.text
    
    try:
        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)

        # Поиск пользователя в базе данных
        cursor.execute(f'SELECT id, passhash FROM accounts WHERE username = "{username}"')
        user = cursor.fetchone()
        
        # Проверка пароля
        if user and user['passhash'] == hash_password(password):
            sessions[message.chat.id] = user['id']  # Сохраняем ID пользователя в сессии
            bot.send_message(message.chat.id, phrases['signin_success'])
            show_main_menu(message.chat.id)  # Показываем главное меню
        else:
            bot.send_message(message.chat.id, phrases['signin_unsuccess'])
        
    except Error as error:
        bot.send_message(message.chat.id, phrases['signin_error'])
        print(error)

    finally:
        if connection.is_connected():
            cursor.close()
            connection.close()

# Обработчик кнопки регистрации - запрашивает логин для нового пользователя
@bot.message_handler(func=lambda m: m.text == phrases['signup'])
def register_handler(message):
    message = bot.send_message(message.chat.id, phrases['signup_username'])
    bot.register_next_step_handler(message, process_reg_username_step)

# Обработка введенного логина для регистрации - запрашивает пароль
def process_reg_username_step(message):
    username = message.text
    message = bot.send_message(message.chat.id, phrases['signup_password'])
    bot.register_next_step_handler(message, process_reg_password_step, username)

# Создание нового пользователя в базе данных
def process_reg_password_step(message, username):
    password = message.text
    
    try:
        connection = get_db_connection()
        cursor = connection.cursor()
        
        # Вставка нового пользователя в базу данных
        cursor.execute(f'INSERT INTO accounts (username, passhash) VALUES ("{username}", "{hash_password(password)}")')
        user_id = cursor.lastrowid
        connection.commit()

        sessions[message.chat.id] = user_id  # Сохраняем ID нового пользователя в сессии
        bot.send_message(message.chat.id, phrases['signup_success'])
        show_main_menu(message.chat.id)  # Показываем главное меню

    except Error as error:
        # Обработка ошибки дублирования логина
        if error.errno == 1062:
            bot.send_message(message.chat.id, phrases['signup_login_exists'])
        else:
            bot.send_message(message.chat.id, phrases['signup_error'])
            print(error)

    finally:
        if connection.is_connected():
            cursor.close()
            connection.close()

# Функция отображения главного меню с кнопками
def show_main_menu(chat_id):
    markup = tb.types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add(phrases['get_items'])
    markup.add(phrases['create_item'], phrases['edit_item'], phrases['delete_item'])
    markup.add(phrases['signout'])
    bot.send_message(chat_id, phrases['menu'], reply_markup=markup)

# Обработчик кнопки просмотра заметок - показывает все заметки пользователя
@bot.message_handler(func=lambda m: m.text == phrases['get_items'])
def show_items(message):
    user_id = sessions.get(message.chat.id)

    if not user_id:
        bot.send_message(message.chat.id, phrases['auth_please'])
        return
    
    try:
        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)

        # Получение всех заметок пользователя
        cursor.execute(f'SELECT id, text FROM items WHERE user_id = "{user_id}"')
        items = cursor.fetchall()
        
        if not items:
            bot.send_message(message.chat.id, phrases['get_items_no_one'])
            return
        
        # Формирование списка заметок
        response = phrases['items:']
        for item in items:
            response += f"{item['id']}.\t{item['text']}\n\n"
        
        bot.send_message(message.chat.id, response)

    except Error as error:
        bot.send_message(message.chat.id, phrases['get_items_error'])
        print(error)

    finally:
        if connection.is_connected():
            cursor.close()
            connection.close()

# Обработчик кнопки создания заметки - запрашивает текст заметки
@bot.message_handler(func=lambda m: m.text == phrases['create_item'])
def add_item_start(message):
    user_id = sessions.get(message.chat.id)

    if not user_id:
        bot.send_message(message.chat.id, phrases['auth_please'])
        return
    
    message = bot.send_message(message.chat.id, phrases['create_item_text'])
    bot.register_next_step_handler(message, add_item_finish, user_id)

# Создание новой заметки в базе данных
def add_item_finish(message, user_id):
    text = message.text
    
    try:
        connection = get_db_connection()
        cursor = connection.cursor()

        # Добавление новой заметки
        cursor.execute(f'INSERT INTO items (user_id, text) VALUES ("{user_id}", "{text}")')
        connection.commit()
        bot.send_message(message.chat.id, phrases['create_item_success'])

    except Error as error:
        bot.send_message(message.chat.id, phrases['create_item_unsuccess'])
        print(error)

    finally:
        if connection.is_connected():
            cursor.close()
            connection.close()

# Обработчик кнопки редактирования заметки - запрашивает ID заметки
@bot.message_handler(func=lambda m: m.text == phrases['edit_item'])
def edit_handler(message):
    user_id = sessions.get(message.chat.id)

    if not user_id:
        bot.send_message(message.chat.id, phrases['auth_please'])
        return
    
    message = bot.send_message(message.chat.id, phrases['edit_item_number'])
    bot.register_next_step_handler(message, process_edit_item_id, user_id)

# Проверка существования заметки и запрос нового текста
def process_edit_item_id(message, user_id):
    try:
        item_id = int(message.text)
        
        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)

        # Проверка, что заметка существует и принадлежит пользователю
        cursor.execute(f'SELECT id FROM items WHERE id = "{item_id}" AND user_id = "{user_id}"')
        item = cursor.fetchone()
        
        if not item:
            bot.send_message(message.chat.id, phrases['edit_item_no_such'])
            return
        
        message = bot.send_message(message.chat.id, phrases['edit_item_text'])
        bot.register_next_step_handler(message, process_edit_item_text, user_id, item_id)
        
    except ValueError:
        bot.send_message(message.chat.id, phrases['edit_item_no_number'])

    except Error as error:
        bot.send_message(message.chat.id, phrases['edit_item_error'])
        print(error)

    finally:
        if connection.is_connected():
            cursor.close()
            connection.close()

# Обновление текста заметки в базе данных
def process_edit_item_text(message, user_id, item_id):
    new_text = message.text
    
    try:
        connection = get_db_connection()
        cursor = connection.cursor()
        
        # Обновление текста заметки
        cursor.execute(f'UPDATE items SET text = "{new_text}" WHERE id = "{item_id}" AND user_id = "{user_id}"')
        connection.commit()
        bot.send_message(message.chat.id, phrases['edit_item_success'])

    except Error as error:
        bot.send_message(message.chat.id, phrases['edit_item_unsuccess'])
        print(error)

    finally:
        if connection.is_connected():
            cursor.close()
            connection.close()

# Обработчик кнопки удаления заметки - запрашивает ID заметки
@bot.message_handler(func=lambda m: m.text == phrases['delete_item'])
def delete_item_start(message):
    user_id = sessions.get(message.chat.id)

    if not user_id:
        bot.send_message(message.chat.id, phrases['auth_please'])
        return
    
    message = bot.send_message(message.chat.id, phrases['delete_item_number'])
    bot.register_next_step_handler(message, delete_item_finish, user_id)

# Удаление заметки из базы данных
def delete_item_finish(message, user_id):   
    try:
        item_id = int(message.text)

        connection = get_db_connection()
        cursor = connection.cursor()

        # Удаление заметки
        cursor.execute(f'DELETE FROM items WHERE id = "{item_id}" AND user_id = "{user_id}"')
        connection.commit()
        bot.send_message(message.chat.id, phrases['delete_item_success'])

    except ValueError:
        bot.send_message(message.chat.id, phrases['delete_item_no_number'])

    except Error as error:
        bot.send_message(message.chat.id, phrases['delete_item_unsuccess'])
        print(error)

    finally:
        if connection.is_connected():
            cursor.close()
            connection.close()

# Обработчик кнопки выхода - очищает сессию пользователя
@bot.message_handler(func=lambda m: m.text == phrases['signout'])
def logout_handler(message):
    if message.chat.id in sessions:
        del sessions[message.chat.id]
    
    bot.send_message(message.chat.id, phrases['signout_success'])
    start_handler(message)  # Показываем стартовое меню

# Запуск бота
if __name__ == '__main__':
    bot.polling(none_stop=True)
