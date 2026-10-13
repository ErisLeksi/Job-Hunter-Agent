import os
import requests
from dotenv import load_dotenv

# Explicitly load .env from the script's current directory
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(BASE_DIR, ".env"))

def send_telegram_alert(message: str) -> bool:
    bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
    chat_id = os.getenv("TELEGRAM_CHAT_ID")

    if not bot_token or not chat_id:
        raise ValueError(f"Missing credentials! BOT_TOKEN={bool(bot_token)}, CHAT_ID={bool(chat_id)}")
    
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": message,
        "parse_mode": "HTML",
        "disable_web_page_preview": True
    }
    
    response = requests.post(url, json=payload, timeout=10)
    response.raise_for_status()
    return True

if __name__ == "__main__":
    test_message = (
        "🚀 <b>Job Hunter Scout Online!</b>\n\n"
        "Your notification pipeline is connected and ready."
    )
    send_telegram_alert(test_message)
    print("Notification sent! Check your Telegram app.")