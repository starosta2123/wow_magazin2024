import telebot
from telebot import types
import sqlite3
from yookassa import Configuration, Payment
import time
import threading

# Настройки бота и Yookassa
API_TOKEN = 'API_TOKEN'
ADMIN_CHAT_ID = 'ADMIN_CHAT_ID'
YOOKASSA_SHOP_ID = 'YOOKASSA_SHOP_ID'
YOOKASSA_SECRET_KEY = 'YOOKASSA_SECRET_KEY'

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
        payment_id TEXT,
        FOREIGN KEY(chat_id) REFERENCES users(chat_id)
    )
''')

conn.commit()

# Словарь с ценами на товары и ссылками на изображения
products = {
    "Группа 1": [
        {"name": "Товар 1-1 (100 руб)", "price": 100.0, "image_url": "https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcR9apjZiHZttidLKVS-zMLTlaFfvcG1pzdWpg&s"},
        {"name": "Товар 1-2 (150 руб)", "price": 150.0, "image_url": "https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcSr76mEileUe9WYQmOPSQST7o1gptHEfyvfGg&s"}
    ],
    "Группа 2": [
        {"name": "Товар 2-1 (200 руб)", "price": 200.0, "image_url": "https://cs1.livemaster.ru/storage/36/66/b3a7b11eaa139492e1426c72c9rc--posuda-kruzhka-shrek.jpg"},
        {"name": "Товар 2-2 (250 руб)", "price": 250.0, "image_url": "https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcTKnNtFG4l4Vcrsh_w51bq15S5iodtF-zj_eg&s"},
        {"name": "Товар 2-3 (300 руб)", "price": 300.0, "image_url": "https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcQ0memid57YTbs_lUtzGQlHdPo8ubbFO4rAWA&s"}
    ]
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
    for group in products.keys():
        markup.add(types.KeyboardButton(group))
    cart_btn = types.KeyboardButton("Корзина")
    main_menu = types.KeyboardButton("Главное меню")
    edit_data = types.KeyboardButton("Редактировать данные")
    markup.add(cart_btn, main_menu)
    markup.add(edit_data)
    bot.send_message(chat_id, "Выберите группу товаров:", reply_markup=markup)


# Обработчик выбора группы товаров
@bot.message_handler(func=lambda message: message.text in products.keys())
def show_products(message):
    chat_id = message.chat.id
    group = message.text
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    for item in products[group]:
        markup.add(types.KeyboardButton(item["name"]))
    back = types.KeyboardButton("Назад")
    cart_btn = types.KeyboardButton("Корзина")
    main_menu = types.KeyboardButton("Главное меню")
    markup.add(back, cart_btn, main_menu)
    bot.send_message(chat_id, f"Выберите товар из {group}:", reply_markup=markup)


# Функция для добавления товара в корзину
@bot.message_handler(func=lambda message: any(message.text == item["name"] for group in products.values() for item in group))
def add_to_cart(message):
    chat_id = message.chat.id
    product_name = message.text
    for group in products.values():
        for item in group:
            if item["name"] == product_name:
                product = item
                break

    price = product["price"]
    image_url = product["image_url"]

    cursor.execute(
        'SELECT products, total_amount FROM orders WHERE chat_id = ? AND status = 0 ORDER BY order_id DESC LIMIT 1',
        (chat_id,))
    last_order = cursor.fetchone()

    if last_order and last_order[0]:
        products_in_order = last_order[0] + f"\n{product_name}"
        total_amount = last_order[1] + price
        cursor.execute(
            'UPDATE orders SET products = ?, total_amount = ? WHERE chat_id = ? AND status = 0 AND order_id = (SELECT order_id FROM orders WHERE chat_id = ? AND status = 0 ORDER BY order_id DESC LIMIT 1)',
            (products_in_order, total_amount, chat_id, chat_id))
    else:
        products_in_order = product_name
        total_amount = price
        cursor.execute('INSERT INTO orders (chat_id, products, total_amount) VALUES (?, ?, ?)',
                       (chat_id, products_in_order, total_amount))

    conn.commit()
    bot.send_photo(chat_id, photo=image_url, caption=f"{product_name} добавлен в корзину.")
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
        markup.add(types.KeyboardButton("Оплатить"), types.KeyboardButton("Оплатить позже"))
        bot.send_message(chat_id, "Выберите способ оплаты:", reply_markup=markup)
    else:
        bot.send_message(chat_id, "Произошла ошибка. Пожалуйста, попробуйте снова.")


# Функция для уведомления администратора
def notify_admin(order_id, payment_status):
    cursor.execute('SELECT * FROM orders WHERE order_id = ?', (order_id,))
    order_info = cursor.fetchone()
    if order_info:
        chat_id, products, comment, status, total_amount, payment_status_db, payment_id = order_info[1:]
        cursor.execute('SELECT name, phone, address FROM users WHERE chat_id = ?', (chat_id,))
        user_info = cursor.fetchone()
        if user_info:
            name, phone, address = user_info
            bot.send_message(ADMIN_CHAT_ID,
                             f"Новый заказ №{order_id}\n\nПользователь: {name}\nТелефон: {phone}\nАдрес: {address}\n\nТовары:\n{products}\n\nКомментарий: {comment}\n\nОбщая сумма: {total_amount} руб.\n\nСтатус оплаты: {payment_status}")


# Функция для проверки статуса платежа
def check_payment_status(payment_id):
    payment = Payment.find_one(payment_id)
    return payment.status


# Фоновая функция для периодической проверки статуса платежа
def background_payment_check(order_id, payment_id, chat_id):
    while True:
        payment_status = check_payment_status(payment_id)
        if payment_status == 'succeeded':
            cursor.execute('UPDATE orders SET payment_status = "succeeded", status = 1 WHERE order_id = ?', (order_id,))
            conn.commit()
            notify_admin(order_id, payment_status="Оплачен")
            bot.send_message(chat_id, "Ваш заказ успешно оплачен и отправлен администратору.")
            show_product_groups(chat_id)  # Возвращаемся к выбору групп товаров
            break
        elif payment_status == 'canceled':
            bot.send_message(chat_id, "Произошла ошибка при оплате. Пожалуйста, попробуйте снова.")
            break
        time.sleep(30)


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
            cursor.execute('UPDATE orders SET payment_status = "pending", payment_id = ? WHERE order_id = ?',
                           (payment.id, order_id))
            conn.commit()
            bot.send_message(chat_id, f"Пожалуйста, оплатите заказ по следующей ссылке:\n{confirmation_url}")

            # Запуск фоновой задачи для проверки статуса платежа
            threading.Thread(target=background_payment_check, args=(order_id, payment.id, chat_id)).start()

        elif message.text == "Оплатить позже":
            cursor.execute('UPDATE orders SET status = 1 WHERE order_id = ?', (order_id,))
            conn.commit()
            notify_admin(order_id, payment_status="Не оплачен")
            bot.send_message(chat_id, "Ваш заказ отправлен администратору. Вы можете оплатить его позже.")
            show_product_groups(chat_id)  # Возвращаемся к выбору групп товаров
    else:
        bot.send_message(chat_id, "Произошла ошибка. Пожалуйста, попробуйте снова.")


# Обработчик кнопки "Редактировать данные"
@bot.message_handler(func=lambda message: message.text == "Редактировать данные")
def edit_user_data(message):
    chat_id = message.chat.id
    cursor.execute('SELECT name, phone, address FROM users WHERE chat_id = ?', (chat_id,))
    user_info = cursor.fetchone()

    if user_info:
        name, phone, address = user_info
        bot.send_message(chat_id, f"Ваши текущие данные:\n\nИмя: {name}\nТелефон: {phone}\nАдрес: {address}")
        bot.send_message(chat_id, "Введите новое имя или /skip, чтобы пропустить:")
        bot.register_next_step_handler(message, edit_name)
    else:
        bot.send_message(chat_id, "Произошла ошибка. Пожалуйста, попробуйте снова.")


# Функция для редактирования имени пользователя
def edit_name(message):
    chat_id = message.chat.id
    name = message.text
    if name != '/skip':
        cursor.execute('UPDATE users SET name = ? WHERE chat_id = ?', (name, chat_id))
        conn.commit()
    bot.send_message(chat_id, "Введите новый телефон или /skip, чтобы пропустить:")
    bot.register_next_step_handler(message, edit_phone)


# Функция для редактирования телефона пользователя
def edit_phone(message):
    chat_id = message.chat.id
    phone = message.text
    if phone != '/skip':
        cursor.execute('UPDATE users SET phone = ? WHERE chat_id = ?', (phone, chat_id))
        conn.commit()
    bot.send_message(chat_id, "Введите новый адрес или /skip, чтобы пропустить:")
    bot.register_next_step_handler(message, edit_address)


# Функция для редактирования адреса пользователя
def edit_address(message):
    chat_id = message.chat.id
    address = message.text
    if address != '/skip':
        cursor.execute('UPDATE users SET address = ? WHERE chat_id = ?', (address, chat_id))
        conn.commit()
    bot.send_message(chat_id, "Ваши данные обновлены.")
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
