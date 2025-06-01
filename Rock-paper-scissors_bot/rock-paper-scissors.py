import telebot as tb
from telebot import types
import random
import json
import os

token = open("token.txt").readline().strip()
bot = tb.TeleBot(token)

EMOJI = {'камень': '🗿', 'бумага': '📄', 'ножницы': '✂️'}
RESULTS_TEXT = {
    'win': "Победа за вами! \n🎉 Наполняйте бокалы!",
    'draw': "Ничья! \n🔄 Давайте реванш?",
    'loss': "Вы проиграли... \n💤 Удача сегодня не на вашей стороне"
}
STATS_FILE = 'stats.json'

def load_stats():
    if os.path.exists(STATS_FILE):
        with open(STATS_FILE, 'r') as f:
            return json.load(f)
    return {}

def save_stats(stats):
    with open(STATS_FILE, 'w') as f:
        json.dump(stats, f, indent=2)

def update_stats(user_id, result):
    stats = load_stats()
    user_id = str(user_id)
    user_stats = stats.get(user_id, {'wins': 0, 'losses': 0, 'draws': 0})
    
    if result == 'win':
        user_stats['wins'] += 1
    elif result == 'loss':
        user_stats['losses'] += 1
    elif result == 'draw':
        user_stats['draws'] += 1
    
    stats[user_id] = user_stats
    save_stats(stats)
    return user_stats

def get_stats(user_id):
    stats = load_stats()
    return stats.get(str(user_id), {'wins': 0, 'losses': 0, 'draws': 0})

def reset_stats(user_id):
    stats = load_stats()
    user_id = str(user_id)
    if user_id in stats:
        del stats[user_id]
        save_stats(stats)
    return {'wins': 0, 'losses': 0, 'draws': 0}

def determine_winner(user_choice, bot_choice):
    if user_choice == bot_choice:
        return 'draw'
    wins = [('камень', 'ножницы'), ('бумага', 'камень'), ('ножницы', 'бумага')]
    return 'win' if (user_choice, bot_choice) in wins else 'loss'

def game_keyboard():
    markup = types.InlineKeyboardMarkup(row_width=3)
    buttons = [
        types.InlineKeyboardButton(f"Камень {EMOJI['камень']}", callback_data='камень'),
        types.InlineKeyboardButton(f"Бумага {EMOJI['бумага']}", callback_data='бумага'),
        types.InlineKeyboardButton(f"Ножницы {EMOJI['ножницы']}", callback_data='ножницы')
    ]
    markup.add(*buttons)
    return markup

def after_game_keyboard():
    markup = types.InlineKeyboardMarkup()
    markup.row(
        types.InlineKeyboardButton("🔄 Сыграть ещё", callback_data='play_again'),
        types.InlineKeyboardButton("📊 Статистика", callback_data='show_stats')
    )
    return markup

def stats_keyboard():
    markup = types.InlineKeyboardMarkup()
    markup.row(
        types.InlineKeyboardButton("🎮 Новая игра", callback_data='play_again'),
        types.InlineKeyboardButton("🔄 Сбросить статистику", callback_data='reset_stats')
    )
    return markup

@bot.message_handler(commands=['start'])
def start(message):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add(types.KeyboardButton("🎮 Играть"), types.KeyboardButton('📊 Статистика'))
    bot.send_message(
        message.chat.id,
        "👋 Приветствую, стратег!\n"
        "Я бот для эпичных баталий в *Камень-Ножницы-Бумага!*\n\n"
        "▪️ Используй /play для начала битвы\n"
        "▪️ /stats чтобы проверить свою статистику",
        reply_markup=markup,
        parse_mode='Markdown'
    )

@bot.message_handler(commands=['play'])
def play_cmd(message):
    bot.send_message(message.chat.id, "Выберите ваше оружие:", reply_markup=game_keyboard())

@bot.message_handler(commands=['stats'])
def stats_cmd(message):
    show_stats(message.chat.id)

def show_stats(chat_id, message_id=None):
    stats = get_stats(chat_id)
    text = (
        "📊 *Ваша статистика:*\n\n"
        f"🏆 Побед: `{stats['wins']}`\n"
        f"💥 Поражений: `{stats['losses']}`\n"
        f"🤝 Ничьих: `{stats['draws']}`\n\n"
        "_Используйте /play для новой игры_"
    )
    
    if message_id:
        bot.edit_message_text(
            text,
            chat_id,
            message_id,
            reply_markup=stats_keyboard(),
            parse_mode='Markdown'
        )
    else:
        bot.send_message(
            chat_id, 
            text, 
            reply_markup=stats_keyboard(), 
            parse_mode='Markdown'
        )

@bot.message_handler(content_types=['text'])
def handle_text(message):
    if message.text == '🎮 Играть':
        play_cmd(message)
    elif message.text == '📊 Статистика':
        show_stats(message.chat.id)

@bot.callback_query_handler(func=lambda call: True)
def callback_handler(call):
    if call.data in ['камень', 'бумага', 'ножницы']:
        handle_game_choice(call)
    elif call.data == 'play_again':
        bot.edit_message_text(
            "Выберите ваше оружие:",
            call.message.chat.id,
            call.message.message_id,
            reply_markup=game_keyboard()
        )
    elif call.data == 'show_stats':
        show_stats(call.message.chat.id, call.message.message_id)
    elif call.data == 'reset_stats':
        reset_stats(call.message.chat.id)
        bot.answer_callback_query(
            call.id,
            text="Статистика сброшена!",
            show_alert=True
        )
        show_stats(call.message.chat.id, call.message.message_id)

def handle_game_choice(call):
    user_choice = call.data
    bot_choice = random.choice(list(EMOJI.keys()))
    
    result = determine_winner(user_choice, bot_choice)
    update_stats(call.message.chat.id, result)
    
    result_message = (
        f"Ваш выбор: {user_choice} {EMOJI[user_choice]}\n"
        f"Мой выбор: {bot_choice} {EMOJI[bot_choice]}\n\n"
        f"**{RESULTS_TEXT[result]}**"
    )
    
    bot.edit_message_text(
        result_message,
        call.message.chat.id,
        call.message.message_id,
        reply_markup=after_game_keyboard(),
        parse_mode='Markdown'
    )

if __name__ == '__main__':
    print('Бот запущен и готов к битвам! ⚔️')
    bot.infinity_polling()