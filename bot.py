import os, random, re, logging
from telegram import Update, ChatPermissions
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, CallbackContext

# ----------------- Ayarlar -----------------
BOT_TOKEN = os.environ.get("BOT_TOKEN")
AUTHORIZED_CHAT_ID = -1001234567890
MONITOR_CHANNELS = ["@anlikhaberi"]
ADMIN_IDS = [33397779]

KUFUR_LIST = ["küfür1","küfür2"]
SPAM_LINK_PATTERN = r"(http|https|www\.)"
CAPTCHA_QUESTIONS = {"2+2=?":"4","3+5=?":"8"}
WELCOME_MESSAGE = "Hoş geldin {name}! 🎉 Lütfen captcha'yı çöz."

pending_captcha = {}
user_warnings = {}

logging.basicConfig(format='%(asctime)s - %(levelname)s - %(message)s', level=logging.INFO)

# ----------------- Yetki Kontrol -----------------
def only_authorized(func):
    def wrapper(update, context):
        if update.effective_chat.id != AUTHORIZED_CHAT_ID:
            return
        return func(update, context)
    return wrapper

# ----------------- Safe Run -----------------
def safe_run(func):
    def wrapper(update, context):
        try:
            func(update, context)
        except Exception as e:
            logging.error(f"Hata: {e}")
    return wrapper

# ----------------- Yeni Üye Karşılama -----------------
@only_authorized
@safe_run
def welcome(update: Update, context: CallbackContext):
    for member in update.message.new_chat_members:
        update.message.reply_text(WELCOME_MESSAGE.format(name=member.full_name))
        question = random.choice(list(CAPTCHA_QUESTIONS.keys()))
        pending_captcha[member.id] = CAPTCHA_QUESTIONS[question]
        context.bot.send_message(update.effective_chat.id, f"Captcha sorusu: {question}")
        context.bot.restrict_chat_member(update.effective_chat.id, member.id, ChatPermissions(can_send_messages=False))

# ----------------- Mesaj Kontrol -----------------
@only_authorized
@safe_run
def check_message(update: Update, context: CallbackContext):
    user_id = update.message.from_user.id
    text = update.message.text.lower()
    
    if user_id in pending_captcha:
        if text == pending_captcha[user_id]:
            update.message.reply_text("✅ Doğrulama başarılı!")
            context.bot.restrict_chat_member(update.effective_chat.id, user_id,
                ChatPermissions(can_send_messages=True, can_send_media_messages=True, can_send_other_messages=True))
            del pending_captcha[user_id]
        else:
            update.message.reply_text("❌ Yanlış captcha! Kickleniyorsun.")
            context.bot.kick_chat_member(update.effective_chat.id, user_id)
        return

    for word in KUFUR_LIST:
        if word in text:
            update.message.delete()
            warn_user(update, user_id, "Küfür yasak!")
            return

    if re.search(SPAM_LINK_PATTERN, text):
        update.message.delete()
        warn_user(update, user_id, "Link yasak!")
        return

# ----------------- Uyarı Sistemi -----------------
@only_authorized
@safe_run
def warn_user(update, user_id, reason):
    user_warnings[user_id] = user_warnings.get(user_id,0)+1
    update.message.reply_text(f"{update.message.from_user.first_name}, uyarı {user_warnings[user_id]}/3: {reason}")
    if user_warnings[user_id]>=3:
        update.message.reply_text(f"{update.message.from_user.first_name} 3 uyarı aldı, atılıyor! ❌")
        update.message.chat.kick_member(user_id)
        user_warnings[user_id]=0

# ----------------- Admin Komutları -----------------
@only_authorized
@safe_run
def start(update: Update, context: CallbackContext):
    update.message.reply_text("Güvenlik botu aktif! ✅")

@only_authorized
@safe_run
def pending(update: Update, context: CallbackContext):
    if update.message.from_user.id in ADMIN_IDS:
        update.message.reply_text(f"Doğrulama bekleyenler: {list(pending_captcha.keys())}")

# ----------------- Kanal Kontrol Job -----------------
def monitor_channels(context):
    for ch in MONITOR_CHANNELS:
        try:
            context.bot.send_message(ch, "Bot ara kontrol 🛡️")
        except Exception as e:
            logging.error(f"{ch} hatası: {e}")

# ----------------- Bot Başlat -----------------
updater = Updater(BOT_TOKEN)
dispatcher = updater.dispatcher

dispatcher.add_handler(CommandHandler("start", start))
dispatcher.add_handler(CommandHandler("pending", pending))
dispatcher.add_handler(MessageHandler(Filters.status_update.new_chat_members, welcome))
dispatcher.add_handler(MessageHandler(Filters.text & ~Filters.command, check_message))

job_queue = updater.job_queue
job_queue.run_repeating(monitor_channels, interval=1800, first=10)  # 30 dakikada bir

updater.start_polling(poll_interval=2, timeout=60)
updater.idle()
