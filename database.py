import sqlite3

DB_PATH = "jobs.db"

def init_db():
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS jobs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                company TEXT NOT NULL,
                title TEXT NOT NULL,
                location TEXT,
                source_portal TEXT,
                original_url TEXT UNIQUE,
                direct_url TEXT,
                match_score INTEGER DEFAULT 0,
                match_reason TEXT,
                notified INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.commit()

def job_exists(url: str) -> bool:
    """Checks whether a job URL has already been recorded."""
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT 1 FROM jobs WHERE original_url = ?", (url,))
        return cursor.fetchone() is not None

def insert_job(company: str, title: str, location: str, source_portal: str, original_url: str) -> bool:
    """Inserts a new job. Returns True if inserted, False if it was already in the database."""
    if job_exists(original_url):
        return False
    
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT OR IGNORE INTO jobs (company, title, location, source_portal, original_url)
            VALUES (?, ?, ?, ?, ?)
        """, (company, title, location, source_portal, original_url))
        conn.commit()
        return cursor.rowcount > 0

if __name__ == "__main__":
    init_db()
    print("Database initialized successfully: jobs.db ready!")