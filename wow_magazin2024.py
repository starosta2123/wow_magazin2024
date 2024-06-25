import telebot
from telebot import types
import requests

#Настройки бота
API_TOKEN = 'API_TOKEN'
ADMIN_CHAT_ID = 'ADMIN_CHAT_ID'
# YKASSA_SHOP_ID = '401451'
# YKASSA_SECRET_KEY = 'test_oLFWBUnXbREdqZnNGqJHx8oDq8nLo2KNFwFe92xzkw8'

bot = telebot.TeleBot(API_TOKEN)

# "База данных" с заказами пользователей
user_data = {}
cart = {}

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
        user_data[chat_id] = {}
        bot.send_message(chat_id, "Добро пожаловать! Пожалуйста, введите ваше имя:")
        bot.register_next_step_handler(message, get_name)

# Функция для получения имени пользователя
def get_name(message):
    chat_id = message.chat.id
    user_data[chat_id]['name'] = message.text
    bot.send_message(chat_id, "Пожалуйста, введите ваш телефон:")
    bot.register_next_step_handler(message, get_phone)

# Функция для получения телефона пользователя
def get_phone(message):
    chat_id = message.chat.id
    user_data[chat_id]['phone'] = message.text
    bot.send_message(chat_id, "Пожалуйста, введите ваш адрес:")
    bot.register_next_step_handler(message, get_address)

# Функция для получения адреса пользователя
def get_address(message):
    chat_id = message.chat.id
    user_data[chat_id]['address'] = message.text
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
    if chat_id not in user_data:
        user_data[chat_id] = {}
    if 'cart' not in user_data[chat_id]:
        user_data[chat_id]['cart'] = []
    user_data[chat_id]['cart'].append(product)
    bot.send_message(chat_id, f"{product} добавлен в корзину.")
    show_product_groups(chat_id)

# Обработчик кнопки "Корзина"
@bot.message_handler(func=lambda message: message.text == "Корзина")
def view_cart(message):
    chat_id = message.chat.id
    if chat_id in user_data and 'cart' in user_data[chat_id] and user_data[chat_id]['cart']:
        cart_items = "\n".join(user_data[chat_id]['cart'])
        bot.send_message(chat_id, f"Ваша корзина:\n{cart_items}")
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
    user_data[chat_id]['comment'] = message.text
    bot.send_message(chat_id, "Комментарий получен. Спасибо за ваш заказ!")
    notify_admin(chat_id)

# Функция для отправки уведомления администратору
def notify_admin(chat_id):
    if chat_id in user_data:
        user_info = user_data[chat_id]
        if 'name' in user_info and 'phone' in user_info and 'address' in user_info and 'comment' in user_info and 'cart' in user_info:
            cart_items = "\n".join(user_info['cart'])
            admin_message = (f"Новый заказ!\n\n"
                             f"Имя: {user_info['name']}\n"
                             f"Телефон: {user_info['phone']}\n"
                             f"Адрес: {user_info['address']}\n"
                             f"Комментарий: {user_info['comment']}\n"
                             f"Товары:\n{cart_items}\n"
                             f"ID пользователя: {chat_id}")
            bot.send_message(ADMIN_CHAT_ID, admin_message)
        else:
            bot.send_message(ADMIN_CHAT_ID, "Недостаточно данных для уведомления о заказе.")

# Обработчик кнопки "Главное меню"
@bot.message_handler(func=lambda message: message.text == "Главное меню")
def main_menu(message):
    chat_id = message.chat.id
    show_product_groups(chat_id)

# Обработчик для администратора: просмотр последних заказов
@bot.message_handler(func=lambda message: message.text == "Посмотреть заказы")
def view_orders(message):
    chat_id = message.chat.id
    orders_text = "Последние заказы:\n\n"
    # Тестовая логика
    for i in range(1, 6):
        order_info = (f"Заказ {i}:\n"
                      f"Имя: Иванов Иван\n"
                      f"Телефон: +1234567890\n"
                      f"Адрес: г. Москва, ул. Пушкина, д. Колотушкина\n"
                      f"Товары:\n"
                      f"Товар 1\n"
                      f"Товар 2\n\n")
        orders_text += order_info

    bot.send_message(chat_id, orders_text)

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

