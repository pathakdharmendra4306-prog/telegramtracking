import os
import time
import json
import logging
import requests
from flask import Flask, request

# --- YOUR CREDENTIALS (HARDCODED) ---
TELEGRAM_BOT_TOKEN = "8460676423:AAGh_hVH5zBWT8hjLkRXqdmrpZ4LOFx45JA"
FACEBOOK_PIXEL_ID = "867625472330121"
FACEBOOK_ACCESS_TOKEN = "EAANYHGEbtlYBQNns5nxUAM2wqE4GodVGnYkfiQTRyS6Nf18KiOCTzFXcen3P7ngNLhJSYEKhjcQzYuF6HjiZCeRnZCuZAPmKp5nTe97xyXDxtkLZBKNIypVjJyqIsN5RQh31kt7ZA9cZBX1vOwO17LTVAjK3aK0Pal9wBX5SwlTHiGlIX3W2jP55BOVQkrnwZDZD"
CHANNEL_ID = "-1002520649839"  # Added the -100 prefix automatically
INVITE_LINK = "https://t.me/+9RB3qhCIDQdhMjM9"

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# --- IN-MEMORY DATABASE ---
user_tracking_db = {}

def send_to_facebook_capi(fbclid, user_id):
    """Sends 'CompleteRegistration' event to Facebook CAPI"""
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
        r = requests.post(url, json=payload)
        logger.info(f"CAPI Response: {r.status_code} - {r.text}")
        return r.status_code == 200
    except Exception as e:
        logger.error(f"CAPI Error: {e}")
        return False

def send_telegram_message(chat_id, text, reply_markup=None):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {"chat_id": chat_id, "text": text, "parse_mode": "HTML"}
    if reply_markup:
        payload["reply_markup"] = reply_markup
    requests.post(url, json=payload)

@app.route(f'/{TELEGRAM_BOT_TOKEN}', methods=['POST'])
def webhook():
    update = request.json
    if not update:
        return "OK", 200

    # 1. HANDLE /start COMMAND (Deep Linking)
    if 'message' in update and 'text' in update['message']:
        text = update['message']['text']
        user_id = update['message']['from']['id']
        chat_id = update['message']['chat']['id']

        if text.startswith("/start"):
            parts = text.split(' ')
            if len(parts) > 1:
                fbclid = parts[1]
                user_tracking_db[user_id] = {"fbclid": fbclid}
                logger.info(f"TRACKED: User {user_id} -> FBCLID {fbclid}")
            
            keyboard = {
                "inline_keyboard": [[
                    {"text": "🚀 JOIN VIP CHANNEL", "url": INVITE_LINK}
                ]]
            }
            send_telegram_message(chat_id, "<b>Tap below to join the Private Channel!</b>", keyboard)

    # 2. HANDLE CHANNEL JOIN (Chat Member Update)
    if 'chat_member' in update:
        updated_chat_id = update['chat_member']['chat']['id']
        
        # Verify the update comes from YOUR specific private channel
        if str(updated_chat_id) != str(CHANNEL_ID):
            return "OK", 200

        new_member = update['chat_member'].get('new_chat_member', {})
        old_member = update['chat_member'].get('old_chat_member', {})
        user_id = new_member.get('user', {}).get('id')
        
        status = new_member.get('status')
        old_status = old_member.get('status')
        
        # Check if they actually joined
        is_joining = status in ['member', 'administrator', 'creator'] and old_status in ['left', 'kicked', 'restricted']

        if is_joining and user_id in user_tracking_db:
            fbclid = user_tracking_db[user_id]['fbclid']
            logger.info(f"CONVERSION: User {user_id} joined private channel {CHANNEL_ID}")
            send_to_facebook_capi(fbclid, user_id)
            del user_tracking_db[user_id]

    return "OK", 200

@app.route('/', methods=['GET'])
def index():
    return "Bot Server is Running.", 200

if __name__ == "__main__":

    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
