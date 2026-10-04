import os
from flask import Flask, request
import requests
from twilio.twiml.messaging_response import MessagingResponse
from twilio.rest import Client

app = Flask(__name__)

PORT = int(os.environ.get("PORT", 5000))

# Minehut Setup Mapping
MINEHUT_EMAIL = os.environ.get("MINEHUT_EMAIL")
MINEHUT_PASSWORD = os.environ.get("MINEHUT_PASSWORD")
SERVER_NAME = os.environ.get("SERVER_NAME")

# Twilio Access Credentials (Required to send out group relay messages)
TWILIO_ACCOUNT_SID = os.environ.get("TWILIO_ACCOUNT_SID")
TWILIO_AUTH_TOKEN = os.environ.get("TWILIO_AUTH_TOKEN")
TWILIO_NUMBER = os.environ.get("TWILIO_NUMBER") 

BASE_URL = "https://minehut.com"

# Initialize the outbound Twilio delivery engine
if TWILIO_ACCOUNT_SID and TWILIO_AUTH_TOKEN:
    client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
    print("✅ [INIT] Twilio client connected successfully.")
else:
    client = None
    print("⚠️ [INIT] Twilio credentials missing in Render environment.")

# --- HARDCODED PERMANENT MEMORY REGISTRY ---
# Put your number and your friends' numbers here so Render never forgets you.
# Replace the placeholder numbers below with your real phone numbers.
# IMPORTANT: Keep the 'whatsapp:' prefix and include full country codes (e.g., +44 for UK).
GROUP_MEMBERS = {
    "whatsapp:+447444247492",  # ⬅️ REPLACE WITH YOUR MOBILE PHONE NUMBER
    "whatsapp:+447754582794",  # ⬅️ REPLACE WITH FRIEND 1'S PHONE NUMBER
}
# --------------------------------------------

def trigger_minehut_boot():
    print(f"📥 [MINEHUT] Attempting to boot server: {SERVER_NAME}")
    if not MINEHUT_EMAIL or not MINEHUT_PASSWORD or not SERVER_NAME:
        print("❌ [MINEHUT] Error: Missing environment variables on Render!")
        return "❌ Error: Cloud environment variables are missing!"

    # 1. Login to retrieve session token
    login_url = f"{BASE_URL}/users/login"
    payload = {"email": MINEHUT_EMAIL, "password": MINEHUT_PASSWORD}
    response = requests.post(login_url, json=payload)
    
    if response.status_code != 200:
        print(f"❌ [MINEHUT] Login failed: {response.text}")
        return "❌ Error: Minehut login authentication failed."
        
    token = response.json().get("session", {}).get("token")
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    
    # 2. Extract internal unique Server ID
    lookup_url = f"{BASE_URL}/server/{SERVER_NAME}?byName=true"
    lookup_res = requests.get(lookup_url)
    if lookup_res.status_code != 200:
        print(f"❌ [MINEHUT] Server lookup failed: {lookup_res.text}")
        return f"❌ Error: Could not resolve server named '{SERVER_NAME}'."
        
    server_id = lookup_res.json().get("server", {}).get("_id")
    
    # 3. Send request to the updated '/start' API endpoint
    start_url = f"{BASE_URL}/server/{server_id}/start"
    start_res = requests.post(start_url, headers=headers)
    
    if start_res.status_code == 200:
        print("🎉 [MINEHUT] Server boot command accepted successfully!")
        return f"🎮 Command received! '{SERVER_NAME}' is now booting up. Allow 2-3 minutes for Bedrock to load!"
    else:
        print(f"❌ [MINEHUT] Boot command rejected: {start_res.text}")
        return f"⚠️ Minehut rejected the boot request: {start_res.text}"

def broadcast_to_group(sender, text_content):
    """Loops through all hardcoded chat profiles and relays the message to them."""
    print(f"📢 [RELAY] Broadcasting text from {sender} to active group members...")
    if not client or not TWILIO_NUMBER:
        print("❌ [RELAY] Broadcast failed: Twilio environment credentials are unconfigured.")
        return
        
    for member in GROUP_MEMBERS:
        if member != sender:
            try:
                print(f"📤 [RELAY] Forwarding to: {member}")
                client.messages.create(body=text_content, from_=TWILIO_NUMBER, to=member)
            except Exception as e:
                print(f"❌ [RELAY] Delivery error targeting {member}: {e}")

@app.route("/webhook", methods=['POST'])
def whatsapp_group_reply():
    sender = request.values.get('From', '')
    incoming_msg = request.values.get('Body', '').strip()
    incoming_msg_lower = incoming_msg.lower()
    
    print(f"📲 [WEBHOOK] Message caught from {sender}: '{incoming_msg[:50]}...'")
    
    resp = MessagingResponse()
    
    # Check if the message contains the server startup keyword
    if "/startserver" in incoming_msg_lower:
        print("🎯 [WEBHOOK] Command keywords found! Triggering workflow...")
        boot_status_message = trigger_minehut_boot()
        resp.message(boot_status_message)
        # Broadcast the startup notification to everyone else in your list
        broadcast_to_group(sender, f"📢 [System Notice]: {boot_status_message}")
    else:
        # If it's a normal chat message from a registered member, relay it to everyone else
        if sender in GROUP_MEMBERS and not incoming_msg_lower.startswith("https://"):
            clean_phone = sender.replace('whatsapp:', '')
            formatted_chat = f"👤 [{clean_phone}]: {incoming_msg}"
            print(f"🔄 [WEBHOOK] Relaying normal chat text to room: '{formatted_chat}'")
            broadcast_to_group(sender, formatted_chat)
        return str(MessagingResponse())
        
    return str(resp)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=PORT)
