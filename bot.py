
import os
import logging
import sqlite3
from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
)
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes,
)

TOKEN = os.getenv("BOT_TOKEN")
CHANNEL_ID = os.getenv("CHANNEL_ID")
CHANNEL_LINK = os.getenv(
    "CHANNEL_LINK",
    "https://t.me/+vhATNIegb-M4NGIy"
)
REQUIRED_INVITES = 5
DB_NAME = "werlex.db"

logging.basicConfig(level=logging.INFO)
log = logging.getLogger(__name__)


def setup_db():
    with sqlite3.connect(DB_NAME) as db:
        db.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                invited_by INTEGER,
                joined INTEGER DEFAULT 0
            )
        """)


def add_user(user_id, invited_by=None):
    with sqlite3.connect(DB_NAME) as db:
        existing = db.execute(
            "SELECT user_id FROM users WHERE user_id=?",
            (user_id,)
        ).fetchone()

        if existing:
            return

        if invited_by == user_id:
            invited_by = None

        db.execute(
            "INSERT INTO users (user_id, invited_by) VALUES (?, ?)",
            (user_id, invited_by)
        )


def invite_count(user_id):
    with sqlite3.connect(DB_NAME) as db:
        row = db.execute(
            "SELECT COUNT(*) FROM users WHERE invited_by=?",
            (user_id,)
        ).fetchone()
        return row[0]


async def is_subscribed(user_id, context):
    if not CHANNEL_ID:
        return False
    try:
        member = await context.bot.get_chat_member(
            chat_id=CHANNEL_ID,
            user_id=user_id
        )
        return member.status in ("member", "administrator", "creator")
    except Exception:
        log.exception("Subscription check failed")
        return False


def menu():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📢 Вступить в канал", url=CHANNEL_LINK)],
        [InlineKeyboardButton("✅ Проверить подписку", callback_data="check")],
        [InlineKeyboardButton("👥 Пригласить друзей", callback_data="ref")],
    ])


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if not user:
        return

    inviter = None
    if context.args:
        try:
            inviter = int(context.args[0])
        except ValueError:
            pass

    add_user(user.id, inviter)

    await update.message.reply_text(
        "Добро пожаловать в WERLEX ACCESS!\n\n"
        "Вступи в наш канал и нажми «Проверить подписку».\n"
        "Для получения доступа также нужно пригласить 5 друзей.",
        reply_markup=menu()
    )


async def buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id

    if query.data == "check":
        subscribed = await is_subscribed(user_id, context)
        invited = invite_count(user_id)

        if subscribed and invited >= REQUIRED_INVITES:
            await query.message.reply_text(
                "✅ Условия выполнены! Администратор может выдать тебе доступ."
            )
        else:
            await query.message.reply_text(
                "Твой статус:\n"
                f"Подписка: {'✅' if subscribed else '❌'}\n"
                f"Приглашено друзей: {invited}/{REQUIRED_INVITES}\n\n"
                "Выполни оба условия и проверь снова."
            )

    elif query.data == "ref":
        me = await context.bot.get_me()
        link = f"https://t.me/{me.username}?start={user_id}"
        await query.message.reply_text(
            "Приглашай друзей по своей ссылке:\n"
            f"{link}\n\n"
            f"Приглашено: {invite_count(user_id)}/{REQUIRED_INVITES}"
        )


def main():
    if not TOKEN:
        raise RuntimeError("Set BOT_TOKEN in hosting environment")

    setup_db()
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(buttons))
    app.run_polling()


if __name__ == "__main__":
    main()
         
