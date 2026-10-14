import html
import os
import sqlite3
import time
import requests
from dotenv import load_dotenv


load_dotenv()

DB_PATH = "jobs.db"

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

MIN_SCORE_THRESHOLD = 80


def send_telegram_message(text: str) -> bool:
    """Dispatches an HTML-formatted message to Telegram."""
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        print("      [Error]: TELEGRAM_BOT_TOKEN or TELEGRAM_CHAT_ID is missing.")
        return False

    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": text,
        "parse_mode": "HTML",
        "disable_web_page_preview": False,
    }
    try:
        res = requests.post(url, json=payload, timeout=10)
        if res.status_code != 200:
            print(f"      [Telegram API Error ({res.status_code})]: {res.text}")
            return False
        return True
    except Exception as e:
        print(f"      [Telegram Network Error]: {e}")
        return False


def format_job_card(
    company: str,
    title: str,
    location: str,
    score: int,
    reason: str,
    url: str,
    source: str,
) -> str:
    """Constructs a clean Telegram alert card using HTML formatting."""
    clean_company = html.escape(str(company or "Unknown"))
    clean_title = html.escape(str(title or "Unknown Role"))
    clean_location = html.escape(str(location or "Canada"))
    clean_source = html.escape(str(source or "Aggregator"))
    clean_reason = html.escape(str(reason or "N/A"))
    clean_url = html.escape(str(url or ""))

    return (
        f"🎯 <b>New Matched Role ({score} pts)</b>\n\n"
        f"🏢 <b>Company:</b> {clean_company}\n"
        f"💼 <b>Role:</b> {clean_title}\n"
        f"📍 <b>Location:</b> {clean_location}\n"
        f"🌐 <b>Source:</b> {clean_source}\n\n"
        f"💡 <b>Match Insights:</b> {clean_reason}\n\n"
        f'🔗 <a href="{clean_url}">Apply Here</a>'
    )


def run_notifier(batch_limit: int = 10):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Query matching jobs that haven't been notified yet
    cursor.execute(
        """
        SELECT id, company, title, location, match_score, match_reason, original_url, source_portal
        FROM jobs
        WHERE match_score >= ? AND (notified IS NULL OR notified = 0)
        ORDER BY match_score DESC
        LIMIT ?
        """,
        (MIN_SCORE_THRESHOLD, batch_limit),
    )
    jobs_to_notify = cursor.fetchall()

    if not jobs_to_notify:
        print(
            f"[*] No new un-notified jobs found with score >= {MIN_SCORE_THRESHOLD}."
        )
        conn.close()
        return

    print(
        f"[*] Dispatching {len(jobs_to_notify)} high-confidence alerts to Telegram..."
    )

    dispatched = 0
    for job_id, company, title, loc, score, reason, url, source in jobs_to_notify:
        msg = format_job_card(company, title, loc, score, reason, url, source)

        if send_telegram_message(msg):
            cursor.execute(
                "UPDATE jobs SET notified = 1 WHERE id = ?", (job_id,)
            )
            conn.commit()
            dispatched += 1
            print(f"  -> Dispatched: {title} ({company})")
            time.sleep(1)  # Rate limiting between Telegram API calls
        else:
            print(f"  [!] Failed to send notification for job ID: {job_id}")

    conn.close()
    print(f"\n[Done] Successfully sent {dispatched} alerts to Telegram.")


if __name__ == "__main__":
    run_notifier()