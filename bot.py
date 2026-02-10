import random
import sqlite3
import time
import os
from aiogram import Bot, Dispatcher, types
from aiogram.utils import executor
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, BotCommand

TOKEN = os.getenv("TOKEN")

bot = Bot(token=TOKEN)
dp = Dispatcher(bot)

# ---------- COMMAND MENU ----------
async def set_commands(bot):
    commands = [
        BotCommand("start", "Запустить бота"),
        BotCommand("play", "Играть рейтинг"),
        BotCommand("rank", "Мой ранг"),
        BotCommand("top", "Топ игроков"),
        BotCommand("help", "Помощь"),
    ]
    await bot.set_my_commands(commands)

# ---------- DATABASE ----------
conn = sqlite3.connect("mlbb.db")
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS players(
    user_id INTEGER PRIMARY KEY,
    rank_index INTEGER,
    stars INTEGER,
    streak INTEGER,
    last_play INTEGER
)
""")
conn.commit()

# ---------- RANKS ----------
RANKS = [
    ("Warrior", 3),
    ("Elite", 4),
    ("Master", 4),
    ("Grandmaster", 5),
    ("Epic", 5),
    ("Legend", 5),
    ("Mythic", 10)
]

ROLES = ["Танк", "Лес", "Мид", "Голд", "Саппорт"]

WIN_EVENTS = [
    "Ты в соло разнёс катку, враги удалили игру.",
    "Команда внезапно начала играть нормально.",
    "Франко попал хуком. Это вообще законно?",
]

LOSE_EVENTS = [
    "Aydora вылезла из куста и стерла тебя.",
    "Твой ADC пошёл 1v5 и удивился.",
    "Танк купил урон и умер первым.",
]

EPIC_EVENTS = [
    "🔥 ЭПИК: ты украл лорда и стал богом.",
    "🔥 ЭПИК: сделал savage и сломал врагам психику.",
]

TROLL_EVENTS = [
    "🤡 Тиммейт пикнул второго лесника.",
    "🤡 Саппорт пошёл фармить бафф.",
]

# ---------- KEYBOARD ----------
kb = ReplyKeyboardMarkup(resize_keyboard=True)
kb.add(
    KeyboardButton("🎮 Играть рейтинг"),
    KeyboardButton("📊 Мой ранг"),
)
kb.add(
    KeyboardButton("🏆 Топ"),
    KeyboardButton("❓ Помощь"),
)

# ---------- HELPERS ----------
def get_player(user_id):
    cursor.execute("SELECT * FROM players WHERE user_id=?", (user_id,))
    return cursor.fetchone()

def create_player(user_id):
    cursor.execute(
        "INSERT INTO players VALUES (?, ?, ?, ?, ?)",
        (user_id, 0, 0, 0, 0)
    )
    conn.commit()

def cooldown_left(last_play):
    now = int(time.time())
    cd = 2 * 60 * 60
    return max(0, cd - (now - last_play))

# ---------- START ----------
@dp.message_handler(commands=["start"])
async def start(msg: types.Message):
    if not get_player(msg.from_user.id):
        create_player(msg.from_user.id)

    await msg.answer(
        "🔥 Добро пожаловать в MLBB BOT\nЖми /play и апайся.",
        reply_markup=kb
    )

# ---------- RANK ----------
@dp.message_handler(commands=["rank"])
@dp.message_handler(lambda m: m.text == "📊 Мой ранг")
async def rank(msg: types.Message):
    p = get_player(msg.from_user.id)
    rank, need = RANKS[p[1]]

    await msg.answer(
        f"🏅 Ранг: {rank}\n⭐ Звёзды: {p[2]}/{need}\n🔥 Стрик: {p[3]}"
    )

# ---------- PLAY ----------
@dp.message_handler(commands=["play"])
@dp.message_handler(lambda m: m.text == "🎮 Играть рейтинг")
async def play(msg: types.Message):

    p = get_player(msg.from_user.id)
    if not p:
        create_player(msg.from_user.id)
        p = get_player(msg.from_user.id)

    left = cooldown_left(p[4])
    if left > 0:
        await msg.answer(f"⏳ КД. Жди {left//60} мин.")
        return

    role = random.choice(ROLES)
    roll = random.randint(1, 100)

    text = f"🎭 Роль: {role}\n"

    if roll <= 50:
        win = True
        stars_change = 1
        text += random.choice(WIN_EVENTS)

    elif roll <= 75:
        win = False
        stars_change = -1
        text += random.choice(LOSE_EVENTS)

    elif roll <= 90:
        win = True
        stars_change = 2
        text += random.choice(EPIC_EVENTS) + "\n💎 MVP!"

    else:
        win = False
        stars_change = -1
        text += random.choice(TROLL_EVENTS)

    rank_i, stars, streak = p[1], p[2], p[3]

    streak = streak + 1 if win else 0
    stars += stars_change

    if stars >= RANKS[rank_i][1] and rank_i < len(RANKS) - 1:
        rank_i += 1
        stars = 0
        text += f"\n⬆️ Апнулся до {RANKS[rank_i][0]}"

    if stars < 0:
        if rank_i > 0:
            rank_i -= 1
            stars = RANKS[rank_i][1] - 1
            text += f"\n⬇️ Упал до {RANKS[rank_i][0]}"
        else:
            stars = 0

    cursor.execute("""
        UPDATE players
        SET rank_index=?, stars=?, streak=?, last_play=?
        WHERE user_id=?
    """, (rank_i, stars, streak, int(time.time()), msg.from_user.id))

    conn.commit()

    await msg.answer(text)

# ---------- TOP ----------
@dp.message_handler(commands=["top"])
@dp.message_handler(lambda m: m.text == "🏆 Топ")
async def top(msg: types.Message):
    cursor.execute("""
        SELECT user_id, rank_index, stars
        FROM players
        ORDER BY rank_index DESC, stars DESC
        LIMIT 5
    """)
    rows = cursor.fetchall()

    text = "🏆 ТОП ИГРОКОВ:\n"

    for i, r in enumerate(rows, 1):
        text += f"{i}. {RANKS[r[1]][0]} ({r[2]}⭐)\n"

    await msg.answer(text)

# ---------- HELP ----------
@dp.message_handler(commands=["help"])
@dp.message_handler(lambda m: m.text == "❓ Помощь")
async def help(msg: types.Message):
    await msg.answer(
        "/play — играть\n"
        "/rank — ранг\n"
        "/top — топ"
    )

# ---------- START ----------
async def on_startup(dp):
    await set_commands(bot)

executor.start_polling(dp, on_startup=on_startup)
