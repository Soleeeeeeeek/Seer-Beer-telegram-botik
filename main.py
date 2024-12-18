import psycopg2
import telebot
from telebot import *
import datetime

TOKEN = "api key"
conn = psycopg2.connect(
    dbname="dbname",
    user="user",
    password="password",
    host="localhost"
)
cursor = conn.cursor()
bot = TeleBot(TOKEN)

corz = []
regorlog = 0
setloc = ''
user_code = None
user_data = {}

class UserAuthentication:
    def __init__(self, bot):
        self.bot = bot
        self.user_data = {}
        self.user_code = None

    def register(self, message):
        self.bot.send_message(message.chat.id, "Введите ваше имя:")
        self.bot.register_next_step_handler(message, self.process_name)

    def process_name(self, message):
        self.user_data['name'] = message.text
        self.bot.send_message(message.chat.id, "Введите ваш email:")
        self.bot.register_next_step_handler(message, self.process_email)

    def process_email(self, message):
        self.user_data['email'] = message.text
        cursor.execute("SELECT * FROM клиенты WHERE электронная_почта = %s", (self.user_data['email'],))
        if cursor.fetchone():
            self.bot.send_message(message.chat.id, "Такой пользователь уже зарегистрирован.")
            return
        self.bot.send_message(message.chat.id, "Введите ваш телефон:")
        self.bot.register_next_step_handler(message, self.process_phone)

    def process_phone(self, message):
        self.user_data['телефон'] = message.text
        self.bot.send_message(message.chat.id, "Введите пароль:")
        self.bot.register_next_step_handler(message, self.process_password)

    def process_password(self, message):
        self.user_data['пароль'] = message.text
        user_id = message.from_user.id
        cursor.execute("INSERT INTO клиенты (имя, электронная_почта, телефон, пароль, tgid) VALUES (%s, %s, %s, %s,%s)", 
                       (self.user_data['name'], self.user_data['email'], self.user_data['телефон'], self.user_data['пароль'], user_id))
        conn.commit()
        self.bot.send_message(message.chat.id, "Вы успешно зарегистрировались!")
        regorlog = 1
        keyboard = types.ReplyKeyboardRemove()
        self.bot.send_message(message.chat.id, "Регистрация и логин скрыты.", reply_markup=keyboard)
        self.user_code = self.get_user_code(user_id)
        self.show_menu(message)

    def process_email_login(self, message):
        self.user_data['email'] = message.text
        self.bot.send_message(message.chat.id, "Введите пароль:")
        self.bot.register_next_step_handler(message, self.process_password_login)

    def process_password_login(self, message):
        password = message.text
        cursor.execute("SELECT * FROM клиенты WHERE электронная_почта = %s AND пароль = %s", (self.user_data['email'], password))
        if user := cursor.fetchone():
            self.bot.send_message(message.chat.id, "Вы успешно залогинились!")
            regorlog = 1
            keyboard = types.ReplyKeyboardRemove()
            self.bot.send_message(message.chat.id, "Регистрация и логин скрыты.", reply_markup=keyboard)
        else:
            self.bot.send_message(message.chat.id, "Неверный пароль.")

    def get_user_code(self, user_id):
        cursor.execute("SELECT код_клиента FROM клиенты WHERE tgid = %s", (user_id,))
        result = cursor.fetchone()
        return result[0] if result else None

class Menu:
    def __init__(self, bot):
        self.bot = bot

    def show_menu(self, message):
        keyboard = types.ReplyKeyboardMarkup(row_width=1, resize_keyboard=True)
        btn1 = types.KeyboardButton('Сделать заказ')
        keyboard.add(btn1)
        self.bot.send_message(message.chat.id, "Меню:", reply_markup=keyboard)

class Order:
    def __init__(self, bot):
        self.bot = bot
        self.corz = []

    def show_product(self, message):
        keyboard = types.InlineKeyboardMarkup()
        btn0 = types.InlineKeyboardButton("выбрать адресс", callback_data='btn0')
        keyboard.add(btn0)
        cursor.execute("SELECT название_товара, товары.код_товара, товары.стоимость FROM товары JOIN склад ON товары.код_товара = склад.код_товара WHERE склад.количество > 0;")
        products = cursor.fetchall()
        for product in products:
            button_text = f"{product[0]} - {product[2]} руб."
            button = types.InlineKeyboardButton(button_text, callback_data=f'order_{product[1]}')
            keyboard.add(button)
        self.bot.send_message(message.chat.id, 'Выберите товар:', reply_markup=keyboard)

    def process_address(self, message):
        global user_code
        user_id = message.from_user.id
        cursor.execute("SELECT код_клиента FROM клиенты WHERE tgid = %s", (user_id,))
        result = cursor.fetchone()
        user_code = result[0]
        global setloc
        setloc = message.text
        keyboard = types.InlineKeyboardMarkup()
        btn1 = types.InlineKeyboardButton("оформить заказ", callback_data='btn1')
        keyboard.add(btn1)
        self.bot.send_message(message.chat.id, f"Ваш адрес: {setloc}", reply_markup=keyboard)

    def handle_callbacks(self, call):
        global user_code
        if call.data.startswith('order_'):
            product_code = int(call.data.split('_')[1])
            cursor.execute("SELECT название_товара FROM товары WHERE код_товара = %s", (product_code,))
            product_name = cursor.fetchone()[0]
            self.corz.append({'код_товара': product_code, 'название_товара': product_name})
            self.bot.send_message(call.message.chat.id, f'Товар "{product_name}" добавлен в заказ.')
        elif call.data.startswith('btn0'):
            self.bot.send_message(call.message.chat.id, "Пожалуйста, введите ваш адрес доставки:")
            self.bot.register_next_step_handler(call.message, self.process_address)
        elif call.data.startswith('btn1'):
            for item in self.corz:
                cursor.execute('INSERT INTO заказы (дата_заказа, адрес, количество, код_клиента, код_товара) VALUES (%s, %s, %s, %s, %s)', 
                               (datetime.datetime.now(), setloc, 1, user_code, item['код_товара']))
            conn.commit()
            self.bot.send_message(call.message.chat.id, 'Заказ успешно добавлен в базу данных!')
            self.corz.clear()

user_auth = UserAuthentication(bot)
menu = Menu(bot)
order = Order(bot)

@bot.message_handler(commands=['start'])
def send_welcome(message):
    global regorlog
    if user_auth.get_user_code(message.from_user.id):
        regorlog = 1
        bot.send_message(message.chat.id, "Вы уже залогинились или зарегистрировались.")
        menu.show_menu(message)
    else:
        keyboard = types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
        itembtn1 = types.KeyboardButton('Регистрация')
        itembtn2 = types.KeyboardButton('Логин')
        keyboard.add(itembtn1, itembtn2)
        bot.send_message(message.chat.id, "Добро пожаловать! Выберите действие:", reply_markup=keyboard)

@bot.message_handler(func=lambda message: True)
def handle_message(message):
    if message.text == 'Регистрация':
        user_auth.register(message)
    elif message.text == 'Логин':
        user_auth.process_email_login(message)
    elif message.text == 'Сделать заказ':
        order.show_product(message)
    else:
        bot.reply_to(message, "Извините, я не понимаю эту команду.")

@bot.callback_query_handler(func=lambda call: True)
def handle_callbacks(call):
    order.handle_callbacks(call)

bot.polling()
