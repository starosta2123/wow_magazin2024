import telebot
from telebot import types
import sqlite3

# Настройки бота
API_TOKEN = 'API_TOKEN'
ADMIN_CHAT_ID = 'ADMIN_CHAT_ID'

# Инициализация бота
bot = telebot.TeleBot(API_TOKEN)

# Подключение к базе данных SQLite
conn = sqlite3.connect('orders.db', check_same_thread=False)
cursor = conn.cursor()

# Создание таблицы пользователей, если она не существует
cursor.execute('''
    CREATE TABLE IF NOT EXISTS users (
        chat_id INTEGER PRIMARY KEY,
        name TEXT,
        phone TEXT,
        address TEXT
    )
''')

# Создание таблицы заказов, если она не существует
cursor.execute('''
    CREATE TABLE IF NOT EXISTS orders (
        order_id INTEGER PRIMARY KEY AUTOINCREMENT,
        chat_id INTEGER,
        products TEXT,
        comment TEXT,
        status INTEGER DEFAULT 0,
        FOREIGN KEY(chat_id) REFERENCES users(chat_id)
    )
''')
conn.commit()

# Обработчик команды /start для пользователя
@bot.message_handler(commands=['start'])
def start(message):
    chat_id = message.chat.id
    if str(chat_id) == ADMIN_CHAT_ID:
        # Если пользователь является администратором
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        markup.add(types.KeyboardButton("Отправить уведомление"))
        bot.send_message(chat_id, "Выберите действие:", reply_markup=markup)
    else:
        # Если пользователь не является администратором
        cursor.execute('SELECT * FROM users WHERE chat_id = ?', (chat_id,))
        user = cursor.fetchone()
        if user:
            # Если пользователь уже зарегистрирован, переходим к отображению групп товаров
            show_product_groups(chat_id)
        else:
            bot.send_message(chat_id, "Добро пожаловать! Пожалуйста, введите ваше имя:")
            bot.register_next_step_handler(message, get_name)

# Функция для получения имени пользователя
def get_name(message):
    chat_id = message.chat.id
    name = message.text
    cursor.execute('INSERT INTO users (chat_id, name) VALUES (?, ?)', (chat_id, name))
    conn.commit()
    bot.send_message(chat_id, "Пожалуйста, введите ваш телефон:")
    bot.register_next_step_handler(message, get_phone)

# Функция для получения телефона пользователя
def get_phone(message):
    chat_id = message.chat.id
    phone = message.text
    cursor.execute('UPDATE users SET phone = ? WHERE chat_id = ?', (phone, chat_id))
    conn.commit()
    bot.send_message(chat_id, "Пожалуйста, введите ваш адрес:")
    bot.register_next_step_handler(message, get_address)

# Функция для получения адреса пользователя
def get_address(message):
    chat_id = message.chat.id
    address = message.text
    cursor.execute('UPDATE users SET address = ? WHERE chat_id = ?', (address, chat_id))
    conn.commit()
    show_product_groups(chat_id)

# Функция для отображения групп товаров
def show_product_groups(chat_id):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    item1 = types.KeyboardButton("Группа 1")
    item2 = types.KeyboardButton("Группа 2")
    cart_btn = types.KeyboardButton("Корзина")
    edit_data_btn = types.KeyboardButton("Редактировать данные")
    main_menu = types.KeyboardButton("Главное меню")
    markup.add(item1, item2)
    markup.add(cart_btn, edit_data_btn)
    markup.add(main_menu)
    bot.send_message(chat_id, "Выберите группу товаров:", reply_markup=markup)

# Обработчик кнопки "Главное меню"
@bot.message_handler(func=lambda message: message.text == "Главное меню")
def handle_main_menu(message):
    chat_id = message.chat.id
    show_product_groups(chat_id)

# Обработчик выбора группы товаров
@bot.message_handler(func=lambda message: message.text in ["Группа 1", "Группа 2"])
def show_products(message):
    chat_id = message.chat.id
    group = message.text
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    if group == "Группа 1":
        item1 = types.KeyboardButton("Товар 1-1")
        item2 = types.KeyboardButton("Товар 1-2")
        back = types.KeyboardButton("Назад")
        cart_btn = types.KeyboardButton("Корзина")
        main_menu = types.KeyboardButton("Главное меню")
        markup.add(item1, item2, back)
        markup.add(cart_btn, main_menu)
        bot.send_message(chat_id, "Выберите товар из Группы 1:", reply_markup=markup)
    elif group == "Группа 2":
        item1 = types.KeyboardButton("Товар 2-1")
        item2 = types.KeyboardButton("Товар 2-2")
        item3 = types.KeyboardButton("Товар 2-3")
        back = types.KeyboardButton("Назад")
        cart_btn = types.KeyboardButton("Корзина")
        main_menu = types.KeyboardButton("Главное меню")
        markup.add(item1, item2, item3, back)
        markup.add(cart_btn, main_menu)
        bot.send_message(chat_id, "Выберите товар из Группы 2:", reply_markup=markup)

# Функция для добавления товара в корзину
@bot.message_handler(func=lambda message: message.text.startswith("Товар"))
def add_to_cart(message):
    chat_id = message.chat.id
    product = message.text
    cursor.execute('SELECT order_id, products FROM orders WHERE chat_id = ? AND status = 0 ORDER BY order_id DESC LIMIT 1', (chat_id,))
    last_order = cursor.fetchone()
    if last_order:
        order_id, products = last_order
        if products:
            products += f"\n{product}"
        else:
            products = product
        cursor.execute('UPDATE orders SET products = ? WHERE order_id = ?', (products, order_id))
    else:
        products = product
        cursor.execute('INSERT INTO orders (chat_id, products, status) VALUES (?, ?, 0)', (chat_id, products))
    conn.commit()
    bot.send_message(chat_id, f"{product} добавлен в корзину.")
    show_product_groups(chat_id)

# Обработчик кнопки "Корзина"
@bot.message_handler(func=lambda message: message.text == "Корзина")
def view_cart(message):
    chat_id = message.chat.id
    cursor.execute('SELECT products FROM orders WHERE chat_id = ? AND status = 0 ORDER BY order_id DESC LIMIT 1', (chat_id,))
    cart_items = cursor.fetchone()
    if cart_items and cart_items[0]:
        bot.send_message(chat_id, f"Ваша корзина:\n{cart_items[0]}")
        send_order(message)
    else:
        bot.send_message(chat_id, "Ваша корзина пуста.")
        show_product_groups(chat_id)

# Функция для отправки заказа
def send_order(message):
    chat_id = message.chat.id
    bot.send_message(chat_id, "Пожалуйста, добавьте комментарий к вашему заказу:")
    bot.register_next_step_handler(message, get_comment)

# Функция для получения комментария к заказу
def get_comment(message):
    chat_id = message.chat.id
    comment = message.text

    # Получаем ID последнего заказа пользователя
    cursor.execute('SELECT order_id FROM orders WHERE chat_id = ? AND status = 0 ORDER BY order_id DESC LIMIT 1', (chat_id,))
    order_id = cursor.fetchone()

    if order_id:
        # Обновляем комментарий в последнем заказе пользователя
        cursor.execute('UPDATE orders SET comment = ?, status = 0 WHERE order_id = ?', (comment, order_id[0]))
        conn.commit()

        # Отправляем уведомление пользователю с номером заказа
        bot.send_message(chat_id, f"Спасибо за ваш заказ! Номер вашего заказа: {order_id[0]}")

        notify_admin(chat_id, order_id[0])
        clear_cart(chat_id)  # Очистка корзины после заказа
    else:
        bot.send_message(chat_id, "Произошла ошибка при добавлении комментария к заказу.")

# Функция для отправки уведомления администратору
def notify_admin(chat_id, order_id):
    cursor.execute('''
        SELECT users.chat_id, users.name, users.phone, users.address, orders.products, orders.comment
        FROM orders
        INNER JOIN users ON orders.chat_id = users.chat_id
        WHERE orders.order_id = ?
    ''', (order_id,))
    order_info = cursor.fetchone()

    if order_info:
        user_id, name, phone, address, products, comment = order_info
        message_to_admin = f"Новый заказ!\n\n" \
                           f"Номер заказа: {order_id}\n" \
                           f"ID пользователя: {user_id}\n" \
                           f"Имя: {name}\n" \
                           f"Телефон: {phone}\n" \
                           f"Адрес: {address}\n" \
                           f"Комментарий: {comment}\n" \
                           f"Товары:\n{products}"
        bot.send_message(ADMIN_CHAT_ID, message_to_admin)

# Функция для очистки корзины
def clear_cart(chat_id):
    cursor.execute('DELETE FROM orders WHERE chat_id = ? AND status = 0', (chat_id,))
    conn.commit()

# Обработчик кнопки "Редактировать данные"
@bot.message_handler(func=lambda message: message.text == "Редактировать данные")
def edit_user_data(message):
    chat_id = message.chat.id
    cursor.execute('SELECT name, phone, address FROM users WHERE chat_id = ?', (chat_id,))
    user = cursor.fetchone()
    if user:
        name, phone, address = user
        bot.send_message(chat_id, f"Ваши текущие данные:\nИмя: {name}\nТелефон: {phone}\nАдрес: {address}")
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        phone_btn = types.KeyboardButton("Изменить номер телефона")
        address_btn = types.KeyboardButton("Изменить адрес")
        main_menu = types.KeyboardButton("Главное меню")
        markup.add(phone_btn, address_btn)
        markup.add(main_menu)
        bot.send_message(chat_id, "Выберите, что вы хотите изменить:", reply_markup=markup)
    else:
        bot.send_message(chat_id, "Произошла ошибка при получении ваших данных. Попробуйте снова.")
        show_product_groups(chat_id)

# Обработчик кнопки "Изменить номер телефона"
@bot.message_handler(func=lambda message: message.text == "Изменить номер телефона")
def change_phone(message):
    chat_id = message.chat.id
    bot.send_message(chat_id, "Введите новый номер телефона:")
    bot.register_next_step_handler(message, update_phone)

def update_phone(message):
    chat_id = message.chat.id
    new_phone = message.text
    cursor.execute('UPDATE users SET phone = ? WHERE chat_id = ?', (new_phone, chat_id))
    conn.commit()
    bot.send_message(chat_id, "Номер телефона успешно обновлен.")
    show_product_groups(chat_id)

# Обработчик кнопки "Изменить адрес"
@bot.message_handler(func=lambda message: message.text == "Изменить адрес")
def change_address(message):
    chat_id = message.chat.id
    bot.send_message(chat_id, "Введите новый адрес:")
    bot.register_next_step_handler(message, update_address)

def update_address(message):
    chat_id = message.chat.id
    new_address = message.text
    cursor.execute('UPDATE users SET address = ? WHERE chat_id = ?', (new_address, chat_id))
    conn.commit()
    bot.send_message(chat_id, "Адрес успешно обновлен.")
    show_product_groups(chat_id)

# Обработчик кнопки "Отправить уведомление" для администратора
@bot.message_handler(func=lambda message: message.text == "Отправить уведомление")
def send_notification(message):
    chat_id = message.chat.id
    bot.send_message(chat_id, "Введите дату и время доставки в формате DD.MM.YYYY HH:MM:")
    bot.register_next_step_handler(message, get_delivery_time)

# Функция для получения времени доставки
def get_delivery_time(message):
    chat_id = message.chat.id
    delivery_time = message.text
    if validate_delivery_time(delivery_time):
        bot.send_message(chat_id, "Введите ID пользователя:")
        bot.register_next_step_handler(message, get_user_id, delivery_time)
    else:
        bot.send_message(chat_id, "Неверный формат времени. Пожалуйста, введите дату и время доставки в формате DD.MM.YYYY HH:MM:")

# Функция для проверки формата времени доставки
def validate_delivery_time(delivery_time):
    try:
        day, month, year = delivery_time.split()[0].split('.')
        hour, minute = delivery_time.split()[1].split(':')
        int(day)
        int(month)
        int(year)
        int(hour)
        int(minute)
        return True
    except ValueError:
        return False

# Функция для получения ID пользователя
def get_user_id(message, delivery_time):
    chat_id = message.chat.id
    user_id = message.text
    notification_message = f"Ваш заказ будет доставлен {delivery_time}."
    bot.send_message(chat_id, f"Сообщение для пользователя с ID {user_id}:\n{notification_message}")

    try:
        bot.send_message(user_id, notification_message)
    except Exception as e:
        bot.send_message(chat_id, f"Не удалось отправить уведомление пользователю с ID {user_id}. Проверьте правильность ID и доступность бота для отправки сообщений.")

# Обработчик для текстовых сообщений от администратора
@bot.message_handler(func=lambda message: True)
def handle_admin_text(message):
    chat_id = message.chat.id
    bot.send_message(chat_id, "Не понимаю вашего сообщения. Выберите команду из меню или введите /start для начала.")

# Запуск бота
bot.polling(none_stop=True)
