import telebot
from telebot import types
import sqlite3
from yookassa import Configuration, Payment

# Настройки бота и Yookassa
API_TOKEN = 'YOUR_TELEGRAM_BOT_API_TOKEN'
ADMIN_CHAT_ID = 'YOUR_ADMIN_CHAT_ID'
YOOKASSA_SHOP_ID = 'YOUR_YOOKASSA_SHOP_ID'
YOOKASSA_SECRET_KEY = 'YOUR_YOOKASSA_SECRET_KEY.'

# Инициализация бота
bot = telebot.TeleBot(API_TOKEN)

# Настройки Yookassa
Configuration.account_id = YOOKASSA_SHOP_ID
Configuration.secret_key = YOOKASSA_SECRET_KEY

# Подключение к базе данных SQLite
conn = sqlite3.connect('orders.db', check_same_thread=False)
cursor = conn.cursor()

# Создание таблиц пользователей и заказов, если они не существуют
cursor.execute('''
    CREATE TABLE IF NOT EXISTS users (
        chat_id INTEGER PRIMARY KEY,
        name TEXT,
        phone TEXT,
        address TEXT
    )
''')
cursor.execute('''
    CREATE TABLE IF NOT EXISTS orders (
        order_id INTEGER PRIMARY KEY AUTOINCREMENT,
        chat_id INTEGER,
        products TEXT,
        comment TEXT,
        status INTEGER DEFAULT 0,
        total_amount REAL,
        payment_status TEXT DEFAULT 'pending',
        FOREIGN KEY(chat_id) REFERENCES users(chat_id)
    )
''')

# Добавление столбца payment_status, если он не существует
try:
    cursor.execute('ALTER TABLE orders ADD COLUMN payment_status TEXT DEFAULT "pending"')
except sqlite3.OperationalError:
    # Если столбец уже существует, просто продолжаем выполнение
    pass

conn.commit()

# Словарь с ценами на товары
product_prices = {
    "Товар 1-1": 100.0,
    "Товар 1-2": 150.0,
    "Товар 2-1": 200.0,
    "Товар 2-2": 250.0,
    "Товар 2-3": 300.0
}


# Обработчик команды /start для пользователя
@bot.message_handler(commands=['start'])
def start(message):
    chat_id = message.chat.id
    if str(chat_id) == ADMIN_CHAT_ID:
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        markup.add(types.KeyboardButton("Отправить уведомление"))
        bot.send_message(chat_id, "Выберите действие:", reply_markup=markup)
    else:
        cursor.execute('SELECT * FROM users WHERE chat_id = ?', (chat_id,))
        user = cursor.fetchone()
        if user:
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
    main_menu = types.KeyboardButton("Главное меню")
    edit_data = types.KeyboardButton("Редактировать данные")
    markup.add(item1, item2)
    markup.add(cart_btn, main_menu)
    markup.add(edit_data)
    bot.send_message(chat_id, "Выберите группу товаров:", reply_markup=markup)


# Обработчик выбора группы товаров
@bot.message_handler(func=lambda message: message.text in ["Группа 1", "Группа 2", "Главное меню"])
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
    elif group == "Главное меню":
        show_product_groups(chat_id)


# Функция для добавления товара в корзину
@bot.message_handler(func=lambda message: message.text.startswith("Товар"))
def add_to_cart(message):
    chat_id = message.chat.id
    product = message.text
    price = product_prices.get(product, 0)

    cursor.execute(
        'SELECT products, total_amount FROM orders WHERE chat_id = ? AND status = 0 ORDER BY order_id DESC LIMIT 1',
        (chat_id,))
    last_order = cursor.fetchone()

    if last_order and last_order[0]:
        products = last_order[0] + f"\n{product}"
        total_amount = last_order[1] + price
        cursor.execute(
            'UPDATE orders SET products = ?, total_amount = ? WHERE chat_id = ? AND status = 0 ORDER BY order_id DESC LIMIT 1',
            (products, total_amount, chat_id))
    else:
        products = product
        total_amount = price
        cursor.execute('INSERT INTO orders (chat_id, products, total_amount) VALUES (?, ?, ?)',
                       (chat_id, products, total_amount))

    conn.commit()
    bot.send_message(chat_id, f"{product} добавлен в корзину.")
    show_product_groups(chat_id)


# Обработчик кнопки "Корзина"
@bot.message_handler(func=lambda message: message.text == "Корзина")
def view_cart(message):
    chat_id = message.chat.id
    cursor.execute(
        'SELECT products, total_amount FROM orders WHERE chat_id = ? AND status = 0 ORDER BY order_id DESC LIMIT 1',
        (chat_id,))
    cart_items = cursor.fetchone()
    if cart_items and cart_items[0]:
        bot.send_message(chat_id, f"Ваша корзина:\n{cart_items[0]}\n\nОбщая сумма: {cart_items[1]} руб.")
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
    cursor.execute('SELECT order_id FROM orders WHERE chat_id = ? AND status = 0 ORDER BY order_id DESC LIMIT 1',
                   (chat_id,))
    order_id = cursor.fetchone()

    if order_id:
        cursor.execute('UPDATE orders SET comment = ? WHERE order_id = ?', (comment, order_id[0]))
        conn.commit()
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        pay_now = types.KeyboardButton("Оплатить")
        pay_later = types.KeyboardButton("Оплатить позже")
        markup.add(pay_now, pay_later)
        bot.send_message(chat_id, "Выберите способ оплаты:", reply_markup=markup)
    else:
        bot.send_message(chat_id, "Произошла ошибка. Пожалуйста, попробуйте снова.")


# Обработчик выбора способа оплаты
@bot.message_handler(func=lambda message: message.text in ["Оплатить", "Оплатить позже"])
def handle_payment_option(message):
    chat_id = message.chat.id
    cursor.execute(
        'SELECT order_id, total_amount FROM orders WHERE chat_id = ? AND status = 0 ORDER BY order_id DESC LIMIT 1',
        (chat_id,))
    order_info = cursor.fetchone()

    if order_info:
        order_id, total_amount = order_info
        if message.text == "Оплатить":
            payment = Payment.create({
                "amount": {
                    "value": str(total_amount),
                    "currency": "RUB"
                },
                "confirmation": {
                    "type": "redirect",
                    "return_url": "https://www.example.com/return"
                },
                "capture": True,
                "description": f"Order #{order_id}"
            })
            confirmation_url = payment.confirmation.confirmation_url
            cursor.execute('UPDATE orders SET payment_status = "pending" WHERE order_id = ?', (order_id,))
            conn.commit()
            bot.send_message(chat_id, f"Пожалуйста, оплатите заказ по следующей ссылке:\n{confirmation_url}")
            notify_admin(order_id, payment_status="pending")
        elif message.text == "Оплатить позже":
            cursor.execute('UPDATE orders SET status = 1 WHERE order_id = ?', (order_id,))
            conn.commit()
            notify_admin(order_id, payment_status="not_paid")
            bot.send_message(chat_id, "Ваш заказ отправлен администратору. Вы можете оплатить его позже.")
            show_product_groups(chat_id)


# Функция для уведомления администратора о новом заказе
def notify_admin(order_id, payment_status):
    cursor.execute(
        'SELECT users.chat_id, users.name, users.phone, users.address, orders.products, orders.comment, orders.total_amount '
        'FROM orders JOIN users ON orders.chat_id = users.chat_id WHERE orders.order_id = ?', (order_id,))
    order_info = cursor.fetchone()

    if order_info:
        admin_message = (f"Новый заказ #{order_id}\n\n"
                         f"ID пользователя: {order_info[0]}\n"
                         f"Имя: {order_info[1]}\n"
                         f"Телефон: {order_info[2]}\n"
                         f"Адрес: {order_info[3]}\n\n"
                         f"Товары:\n{order_info[4]}\n\n"
                         f"Комментарий: {order_info[5]}\n\n"
                         f"Общая сумма: {order_info[6]} руб.\n\n"
                         f"Статус оплаты: {'Оплачен' if payment_status == 'pending' else 'Не оплачен'}")
        bot.send_message(ADMIN_CHAT_ID, admin_message)


# Функции для редактирования данных пользователя
@bot.message_handler(func=lambda message: message.text == "Редактировать данные")
def edit_data(message):
    chat_id = message.chat.id
    bot.send_message(chat_id, "Что вы хотите изменить? Выберите:", reply_markup=edit_data_markup())


def edit_data_markup():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add(types.KeyboardButton("Изменить имя"))
    markup.add(types.KeyboardButton("Изменить телефон"))
    markup.add(types.KeyboardButton("Изменить адрес"))
    markup.add(types.KeyboardButton("Главное меню"))
    return markup


@bot.message_handler(func=lambda message: message.text in ["Изменить имя", "Изменить телефон", "Изменить адрес"])
def edit_specific_data(message):
    chat_id = message.chat.id
    if message.text == "Изменить имя":
        bot.send_message(chat_id, "Введите новое имя:")
        bot.register_next_step_handler(message, update_name)
    elif message.text == "Изменить телефон":
        bot.send_message(chat_id, "Введите новый телефон:")
        bot.register_next_step_handler(message, update_phone)
    elif message.text == "Изменить адрес":
        bot.send_message(chat_id, "Введите новый адрес:")
        bot.register_next_step_handler(message, update_address)


def update_name(message):
    chat_id = message.chat.id
    new_name = message.text
    cursor.execute('UPDATE users SET name = ? WHERE chat_id = ?', (new_name, chat_id))
    conn.commit()
    bot.send_message(chat_id, "Имя успешно обновлено.")
    show_product_groups(chat_id)


def update_phone(message):
    chat_id = message.chat.id
    new_phone = message.text
    cursor.execute('UPDATE users SET phone = ? WHERE chat_id = ?', (new_phone, chat_id))
    conn.commit()
    bot.send_message(chat_id, "Телефон успешно обновлен.")
    show_product_groups(chat_id)


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
