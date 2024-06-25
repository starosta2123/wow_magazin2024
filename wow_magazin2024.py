import telebot
from telebot import types
import sqlite3

# Настройки бота
API_TOKEN = ''
ADMIN_CHAT_ID = ''

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
        markup.add(types.KeyboardButton("Посмотреть заказы"))
        markup.add(types.KeyboardButton("Отправить уведомление"))
        bot.send_message(chat_id, "Выберите действие:", reply_markup=markup)
    else:
        # Если пользователь не является администратором
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
    markup.add(item1, item2)
    markup.add(cart_btn, main_menu)
    bot.send_message(chat_id, "Выберите группу товаров:", reply_markup=markup)

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
    cursor.execute('SELECT products FROM orders WHERE chat_id = ? AND status = 0 ORDER BY order_id DESC LIMIT 1', (chat_id,))
    last_order = cursor.fetchone()
    if last_order and last_order[0]:
        products = last_order[0] + f"\n{product}"
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
        bot.send_message(chat_id, "Комментарий получен. Спасибо за ваш заказ!")
        notify_admin(chat_id)
        clear_cart(chat_id)  # Очистка корзины после заказа
    else:
        bot.send_message(chat_id, "Произошла ошибка при добавлении комментария к заказу.")

#функции для отправки уведомления администратору
def notify_admin(chat_id):
    cursor.execute('''
        SELECT users.name, users.phone, users.address, orders.products, orders.comment
        FROM orders
        INNER JOIN users ON orders.chat_id = users.chat_id
        WHERE orders.chat_id = ? AND orders.status = 0
        ORDER BY orders.order_id DESC LIMIT 1
    ''', (chat_id,))
    order_info = cursor.fetchone()

    if order_info:
        name, phone, address, products, comment = order_info
        message_to_admin = f"Новый заказ!\n\n" \
                           f"Имя: {name}\n" \
                           f"Телефон: {phone}\n" \
                           f"Адрес: {address}\n" \
                           f"Комментарий: {comment}\n" \
                           f"Товары:\n{products}"
        bot.send_message(ADMIN_CHAT_ID, message_to_admin)
    else:
        bot.send_message(ADMIN_CHAT_ID, "Произошла ошибка при получении информации о заказе.")

# Обработчик кнопки "Посмотреть заказы" для администратора
@bot.message_handler(func=lambda message: message.text == "Посмотреть заказы")
def view_orders(message):
    cursor.execute('''
        SELECT users.name, users.phone, users.address, orders.products, orders.comment
        FROM orders
        INNER JOIN users ON orders.chat_id = users.chat_id
        WHERE orders.status = 0
        ORDER BY orders.order_id DESC LIMIT 3
    ''')
    recent_orders = cursor.fetchall()

    if recent_orders:
        for order in recent_orders:
            name, phone, address, products, comment = order
            order_message = f"Последний заказ:\n\n" \
                            f"Имя: {name}\n" \
                            f"Телефон: {phone}\n" \
                            f"Адрес: {address}\n" \
                            f"Комментарий: {comment}\n" \
                            f"Товары:\n{products}"
            bot.send_message(ADMIN_CHAT_ID, order_message)
    else:
        bot.send_message(ADMIN_CHAT_ID, "Заказов нет.")

# Функция для очистки корзины после заказа
def clear_cart(chat_id):
    cursor.execute('UPDATE orders SET status = 1 WHERE chat_id = ? AND status = 0', (chat_id,))
    conn.commit()


# Обработчик для администратора: отправка уведомления пользователю
@bot.message_handler(func=lambda message: message.text == "Отправить уведомление")
def send_notification(message):
    chat_id = message.chat.id
    bot.send_message(chat_id, "Введите дату и время доставки в формате DD.MM.YYYY HH:MM:")
    bot.register_next_step_handler(message, get_delivery_time)

# Функция для получения времени доставки
def get_delivery_time(message):
    chat_id = message.chat.id
    delivery_time = message.text
    # Добавим проверку формата времени в примере для удобства
    # В реальном приложении лучше использовать более строгую проверку
    if validate_delivery_time(delivery_time):
        bot.send_message(chat_id, "Введите ID пользователя:")
        bot.register_next_step_handler(message, get_user_id, delivery_time)
    else:
        bot.send_message(chat_id, "Неверный формат времени. Пожалуйста, введите дату и время доставки в формате DD.MM.YYYY HH:MM:")

# Функция для проверки формата времени доставки
def validate_delivery_time(delivery_time):

    try:
        # Простая проверка формата
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

    # Отправляем уведомление пользователю с указанным ID
    try:
        bot.send_message(user_id, notification_message)
    except Exception as e:
        bot.send_message(chat_id,
                         f"Не удалось отправить уведомление пользователю с ID {user_id}. Проверьте правильность ID и доступность бота для отправки сообщений.")


# Обработчик для текстовых сообщений от администратора
@bot.message_handler(func=lambda message: True)
def handle_admin_text(message):
    chat_id = message.chat.id
    bot.send_message(chat_id, "Не понимаю вашего сообщения. Выберите команду из меню или введите /start для начала.")


# Запуск бота
bot.polling(none_stop=True)
