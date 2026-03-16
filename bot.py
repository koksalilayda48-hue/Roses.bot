import os, random, re, logging
from telegram import Update, ChatPermissions
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    filters,
    ContextTypes,
    JobQueue
)

BOT_TOKEN = os.environ.get("BOT_TOKEN")
AUTHORIZED_CHAT_ID = int(os.environ.get("AUTHORIZED_CHAT_ID"))
MONITOR_CHANNELS = [os.environ.get("MONITOR_CHANNEL")]
ADMIN_IDS = [int(os.environ.get("API_ID"))]

KUFUR_LIST = ["küfür1","küfür2"]
SPAM_LINK_PATTERN = r"(http|https|www\.)"
CAPTCHA_QUESTIONS = {"2+2=?":"4","3+5=?":"8"}
WELCOME_MESSAGE = "Hoş geldin {name}! 🎉 Lütfen captcha'yı çöz."

pending_captcha = {}
user_warnings = {}

logging.basicConfig(format='%(asctime)s - %(levelname)s - %(message)s', level=logging.INFO)

# ----------------- Yeni Üye Karşılama -----------------
async def welcome(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.id != AUTHORIZED_CHAT_ID:
        return
    for member in update.message.new_chat_members:
        await update.message.reply_text(WELCOME_MESSAGE.format(name=member.full_name))
        question = random.choice(list(CAPTCHA_QUESTIONS.keys()))
        pending_captcha[member.id] = CAPTCHA_QUESTIONS[question]
        await context.bot.send_message(update.effective_chat.id, f"Captcha sorusu: {question}")
        await context.bot.restrict_chat_member(update.effective_chat.id, member.id, ChatPermissions(can_send_messages=False))

# ----------------- Mesaj Kontrol -----------------
async def check_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.id != AUTHORIZED_CHAT_ID:
        return

    user_id = update.message.from_user.id
    text = update.message.text.lower()

    # Captcha kontrol
    if user_id in pending_captcha:
        if text == pending_captcha[user_id]:
            await update.message.reply_text("✅ Doğrulama başarılı!")
            await context.bot.restrict_chat_member(update.effective_chat.id, user_id,
                ChatPermissions(can_send_messages=True, can_send_media_messages=True, can_send_other_messages=True))
            del pending_captcha[user_id]
        else:
            await update.message.reply_text("❌ Yanlış captcha! Kickleniyorsun.")
            await context.bot.kick_chat_member(update.effective_chat.id, user_id)
        return

    # Küfür ve link kontrol
    for word in KUFUR_LIST:
        if word in text:
            await update.message.delete()
            await warn_user(update, user_id, "Küfür yasak!")
            return

    if re.search(SPAM_LINK_PATTERN, text):
        await update.message.delete()
        await warn_user(update, user_id, "Link yasak!")
        return

# ----------------- Uyarı Sistemi -----------------
async def warn_user(update, user_id, reason):
    user_warnings[user_id] = user_warnings.get(user_id,0)+1
    await update.message.reply_text(f"{update.message.from_user.first_name}, uyarı {user_warnings[user_id]}/3: {reason}")
    if user_warnings[user_id]>=3:
        await update.message.reply_text(f"{update.message.from_user.first_name} 3 uyarı aldı, atılıyor! ❌")
        await update.message.chat.kick_member(user_id)
        user_warnings[user_id]=0

# ----------------- Admin Komutları -----------------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.id != AUTHORIZED_CHAT_ID:
        return
    await update.message.reply_text("Güvenlik botu aktif! ✅")

async def pending(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.id != AUTHORIZED_CHAT_ID:
        return
    if update.message.from_user.id in ADMIN_IDS:
        await update.message.reply_text(f"Doğrulama bekleyenler: {list(pending_captcha.keys())}")

# ----------------- Kanal Kontrol Job -----------------
async def monitor_channels(context: ContextTypes.DEFAULT_TYPE):
    for ch in MONITOR_CHANNELS:
        try:
            await context.bot.send_message(ch, "Bot ara kontrol 🛡️")
        except Exception as e:
            logging.error(f"{ch} hatası: {e}")

# ----------------- Bot Başlat -----------------
app = ApplicationBuilder().token(BOT_TOKEN).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("pending", pending))
app.add_handler(MessageHandler(filters.StatusUpdate.NEW_CHAT_MEMBERS, welcome))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, check_message))

job_queue = app.job_queue
job_queue.run_repeating(monitor_channels, interval=1800, first=10)  # 30 dakikada bir

app.run_polling()
