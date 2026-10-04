import os
from flask import Flask, request
import requests
from twilio.twiml.messaging_response import MessagingResponse

app = Flask(__name__)

PORT = int(os.environ.get("PORT", 5000))

MINEHUT_EMAIL = os.environ.get("MINEHUT_EMAIL")
MINEHUT_PASSWORD = os.environ.get("MINEHUT_PASSWORD")
SERVER_NAME = os.environ.get("SERVER_NAME")

BASE_URL = "https://minehut.com"

def trigger_minehut_boot():
    if not MINEHUT_EMAIL or not MINEHUT_PASSWORD or not SERVER_NAME:
        return "❌ Error: Cloud environment variables are missing!"

    # 1. Login to get Auth Token
    login_url = f"{BASE_URL}/users/login"
    payload = {"email": MINEHUT_EMAIL, "password": MINEHUT_PASSWORD}
    response = requests.post(login_url, json=payload)
    
    if response.status_code != 200:
        return "❌ Error: Minehut login failed."
        
    token = response.json().get("session", {}).get("token")
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    
    # 2. Find Server ID
    lookup_url = f"{BASE_URL}/server/{SERVER_NAME}?byName=true"
    lookup_res = requests.get(lookup_url)
    if lookup_res.status_code != 200:
        return f"❌ Error: Could not find server named '{SERVER_NAME}'."
        
    server_id = lookup_res.json().get("server", {}).get("_id")
    
    # 3. Hit start endpoint
    start_url = f"{BASE_URL}/server/{server_id}/start_service"
    start_res = requests.post(start_url, headers=headers)
    
    if start_res.status_code in:
        return f"🎮 Command received! '{SERVER_NAME}' is now booting up. Allow 2-3 minutes for Bedrock to load!"
    else:
        return f"⚠️ Minehut rejected the boot command: {start_res.text}"

@app.route("/webhook", methods=['POST'])
def whatsapp_group_reply():
    # Reads the text message sent in the chat
    incoming_msg = request.values.get('Body', '').lower().strip()
    resp = MessagingResponse()
    msg = resp.message()
    
    # If it matches the command, trigger the server boot
    if incoming_msg == "/startserver":
        boot_status_message = trigger_minehut_boot()
        msg.body(boot_status_message)
    else:
        # Silently ignore regular conversation, memes, and normal messages
        return str(MessagingResponse())
        
    return str(resp)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=PORT)
