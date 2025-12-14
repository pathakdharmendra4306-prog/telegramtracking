import os
import time
import json
import logging
import requests
from flask import Flask, request

# --- YOUR CREDENTIALS ---
TELEGRAM_BOT_TOKEN = "8460676423:AAGh_hVH5zBWT8hjLkRXqdmrpZ4LOFx45JA"
FACEBOOK_PIXEL_ID = "867625472330121"
FACEBOOK_ACCESS_TOKEN = "EAANYHGEbtlYBQNns5nxUAM2wqE4GodVGnYkfiQTRyS6Nf18KiOCTzFXcen3P7ngNLhJSYEKhjcQzYuF6HjiZCeRnZCuZAPmKp5nTe97xyXDxtkLZBKNIypVjJyqIsN5RQh31kt7ZA9cZBX1vOwO17LTVAjK3aK0Pal9wBX5SwlTHiGlIX3W2jP55BOVQkrnwZDZD"
CHANNEL_ID = "-1002520649839" 
INVITE_LINK = "https://t.me/+9RB3qhCIDQdhMjM9"

# Fixed Typo: Double Underscore
app = Flask(__name__) 
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# --- IN-MEMORY DATABASE ---
user_tracking_db = {}

def send_to_facebook_capi(fbclid, user_id):
    url = f"https://graph.facebook.com/v19.0/{FACEBOOK_PIXEL_ID}/events"
    current_time = int(time.time())
    fbc_value = f"fb.1.{current_time}.{fbclid}"

    payload = {
        "access_token": FACEBOOK_ACCESS_TOKEN,
        "data": [
            {
                "event_name": "CompleteRegistration",
                "event_time": current_time,
                "action_source": "system_generated",
                "event_source_url": INVITE_LINK,
                "user_data": {
                    "fbc": fbc_value,
                    "external_id": str(user_id)
                },
                "custom_data": {
                    "status": "joined_private_channel",
                    "channel_id": CHANNEL_ID
                }
            }
        ]
    }
    try:
        requests.post(url, json=payload)
    except Exception as e:
        logger.error(f"CAPI Error: {e}")

# --- UPDATED FUNCTION: SENDS LOCAL IMAGE FILE ---
def send_welcome_message(chat_id, caption, reply_markup=None):
    url_photo = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendPhoto"
    url_text = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    
    data = {
        "chat_id": chat_id, 
        "caption": caption, 
        "parse_mode": "HTML"
    }
    
    if reply_markup:
        data["reply_markup"] = json.dumps(reply_markup)

    # Try to find 'welcome.jpg' in the folder
    if os.path.exists("welcome.jpg"):
        try:
            with open("welcome.jpg", "rb") as img_file:
                # Send Photo
                requests.post(url_photo, data=data, files={"photo": img_file})
        except Exception as e:
            logger.error(f"Image Error: {e}")
            # Fallback to Text if image fails
            data["text"] = caption
            requests.post(url_text, data=data)
    else:
        # Fallback to Text if no image found
        logger.warning("welcome.jpg not found, sending text only.")
        data["text"] = caption
        requests.post(url_text, data=data)

@app.route(f'/{TELEGRAM_BOT_TOKEN}', methods=['POST'])
def webhook():
    update = request.json
    if not update:
        return "OK", 200

    if 'message' in update and 'text' in update['message']:
        text = update['message']['text']
        user_id = update['message']['from']['id']
        chat_id = update['message']['chat']['id']

        if text.startswith("/start"):
            parts = text.split(' ')
            if len(parts) > 1:
                fbclid = parts[1]
                user_tracking_db[user_id] = {"fbclid": fbclid}
            
            # --- WELCOME CONTENT ---
            keyboard = {
                "inline_keyboard": [[
                    {"text": "🚀 JOIN VIP CHANNEL NOW", "url": INVITE_LINK}
                ]]
            }
            
            caption_text = (
                "<b>🔥 Welcome to the THE GOAT Predictions!</b>\n\n"
                "Agar aapko telegram channel me join hona toh niche button pe click karo.\n"
                "https://t.me/+9RB3qhCIDQdhMjM9"
            )
            
            send_welcome_message(chat_id, caption_text, keyboard)

    if 'chat_member' in update:
        updated_chat_id = update['chat_member']['chat']['id']
        if str(updated_chat_id) != str(CHANNEL_ID):
            return "OK", 200

        new_member = update['chat_member'].get('new_chat_member', {})
        old_member = update['chat_member'].get('old_chat_member', {})
        user_id = new_member.get('user', {}).get('id')
        
        status = new_member.get('status')
        old_status = old_member.get('status')
        
        is_joining = status in ['member', 'administrator', 'creator'] and old_status in ['left', 'kicked', 'restricted']

        if is_joining and user_id in user_tracking_db:
            fbclid = user_tracking_db[user_id]['fbclid']
            logger.info(f"CONVERSION: User {user_id} joined")
            send_to_facebook_capi(fbclid, user_id)
            del user_tracking_db[user_id]

    return "OK", 200

@app.route('/', methods=['GET'])
def index():
    return "Server is Live", 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))

