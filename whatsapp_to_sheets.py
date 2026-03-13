from flask import Flask, request, jsonify
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime
import hmac, hashlib, os

app = Flask(__name__)

# ── Config ──────────────────────────────────────────────
VERIFY_TOKEN      = "your_verify_token_here"       # any secret string
WHATSAPP_TOKEN    = "your_whatsapp_api_token_here" # from Meta dashboard
APP_SECRET        = "your_app_secret_here"         # from Meta app settings
SPREADSHEET_ID    = "1vcYSxl8FXuQ8HNjDPahceyoubs2xeZt6kkoyWe7VrE0"    # from sheet URL
SHEET_NAME        = "Messages"                     # tab name in your sheet
CREDENTIALS_FILE  = "credentials.json"             # service account key
# ────────────────────────────────────────────────────────

SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]

def get_sheet():
    creds = Credentials.from_service_account_file(CREDENTIALS_FILE, scopes=SCOPES)
    client = gspread.authorize(creds)
    sheet = client.open_by_key(SPREADSHEET_ID).worksheet(SHEET_NAME)
    return sheet

def ensure_header(sheet):
    if sheet.row_values(1) != ["Timestamp", "From", "Name", "Type", "Message"]:
        sheet.insert_row(["Timestamp", "From", "Name", "Type", "Message"], 1)

def save_message(sender, name, msg_type, text):
    sheet = get_sheet()
    ensure_header(sheet)
    row = [
        datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        sender,
        name,
        msg_type,
        text
    ]
    sheet.append_row(row)
    print(f"✅ Saved: {row}")

# ── Webhook verification ─────────────────────────────────
@app.route("/webhook", methods=["GET"])
def verify():
    mode  = request.args.get("hub.mode")
    token = request.args.get("hub.verify_token")
    challenge = request.args.get("hub.challenge")
    if mode == "subscribe" and token == VERIFY_TOKEN:
        return challenge, 200
    return "Forbidden", 403

# ── Receive messages ─────────────────────────────────────
@app.route("/webhook", methods=["POST"])
def receive():
    data = request.get_json()
    try:
        for entry in data.get("entry", []):
            for change in entry.get("changes", []):
                value = change.get("value", {})
                messages = value.get("messages", [])
                contacts = value.get("contacts", [])
                
                name = contacts[0]["profile"]["name"] if contacts else "Unknown"

                for msg in messages:
                    sender   = msg.get("from", "")
                    msg_type = msg.get("type", "")
                    
                    if msg_type == "text":
                        text = msg["text"]["body"]
                    elif msg_type == "image":
                        text = "[Image received]"
                    elif msg_type == "audio":
                        text = "[Audio received]"
                    elif msg_type == "document":
                        text = f"[Document: {msg['document'].get('filename', '')}]"
                    elif msg_type == "location":
                        loc  = msg["location"]
                        text = f"[Location: {loc['latitude']}, {loc['longitude']}]"
                    else:
                        text = f"[{msg_type} message]"
                    
                    save_message(sender, name, msg_type, text)

    except Exception as e:
        print(f"Error: {e}")
    
    return jsonify({"status": "ok"}), 200

if __name__ == "__main__":
    app.run(port=5000, debug=True)