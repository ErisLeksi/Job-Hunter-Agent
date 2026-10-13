import requests
from bs4 import BeautifulSoup
from jobspy import scrape_jobs
from database import init_db, insert_job
import xml.etree.ElementTree as ET

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
}

# --- 1 to 3: LinkedIn, Indeed, Glassdoor (via JobSpy) ---
def fetch_jobspy_boards(search_term="Software Developer", location="Canada") -> int:
    print(f"[*] Querying LinkedIn, Indeed, and Glassdoor for '{search_term}'...")
    count = 0
    try:
        jobs = scrape_jobs(
            site_name=["linkedin", "indeed", "glassdoor"],
            search_term=search_term,
            location=location,
            results_wanted=15,
            country_indeed="canada"
        )

        for _, row in jobs.iterrows():
            company = str(row.get("company") or "Unknown")
            title = str(row.get("title") or "Unknown")
            loc = str(row.get("location") or location)
            source = str(row.get("site") or "JobBoard").capitalize()
            job_url = str(row.get("job_url") or "")

            if job_url and insert_job(company, title, loc, source, job_url):
                count += 1
    except Exception as e:
        print(f"[JobSpy Error]: {e}")

    return count


# --- 4: Google for Jobs ---
def fetch_google_jobs(query="Software Developer jobs Canada") -> int:
    print("[*] Querying Google for Jobs listings...")
    count = 0
    try:
        url = f"https://www.google.com/search?q={query.replace(' ', '+')}&ibp=htl;jobs"
        res = requests.get(url, headers=HEADERS, timeout=12)
        if res.status_code == 200:
            soup = BeautifulSoup(res.text, "html.parser")
            for a_tag in soup.find_all("a", href=True):
                href = a_tag["href"]
                if "http" in href and "google.com" not in href:
                    text = a_tag.get_text(strip=True) or "Google Job Opening"
                    if insert_job("Employer via Google", text, "Canada / Remote", "Google-Jobs", href):
                        count += 1
                        if count >= 10:
                            break
    except Exception as e:
        print(f"[Google Jobs Error]: {e}")
    return count


# --- 5: Wellfound (AngelList Startups) ---
def fetch_wellfound_jobs() -> int:
    print("[*] Querying Wellfound startup openings...")
    count = 0
    try:
        url = "https://wellfound.com/jobs"
        res = requests.get(url, headers=HEADERS, timeout=12)
        if res.status_code == 200:
            soup = BeautifulSoup(res.text, "html.parser")
            for link in soup.find_all("a", href=True):
                href = link["href"]
                if "/jobs/" in href and not href.endswith("/jobs/"):
                    full_url = f"https://wellfound.com{href}" if href.startswith("/") else href
                    title = link.get_text(strip=True) or "Startup Role"
                    if insert_job("Wellfound Startup", title, "Remote / North America", "Wellfound", full_url):
                        count += 1
                        if count >= 10:
                            break
    except Exception as e:
        print(f"[Wellfound Error]: {e}")
    return count


# --- 6: Canada Job Bank (Direct Official Atom/RSS Feed) ---
def fetch_canada_job_bank(search_term="software") -> int:
    print("[*] Querying Canada Job Bank Atom Feed...")
    count = 0
    try:
        url = f"https://www.jobbank.gc.ca/jobsearch/feed/jobSearchRSSfeed?searchstring={search_term.replace(' ', '+')}"
        res = requests.get(url, headers=HEADERS, timeout=12)
        if res.status_code == 200:
            root = ET.fromstring(res.content)
            # Atom feeds use XML namespaces
            ns = {"atom": "http://www.w3.org/2005/Atom"}
            
            for entry in root.findall("atom:entry", ns):
                title_elem = entry.find("atom:title", ns)
                link_elem = entry.find("atom:link", ns)
                summary_elem = entry.find("atom:summary", ns)

                title = title_elem.text.strip() if title_elem is not None and title_elem.text else "Software Role"
                job_url = link_elem.attrib.get("href", "") if link_elem is not None else ""
                summary = summary_elem.text if summary_elem is not None and summary_elem.text else ""

                # Canada Job Bank often includes employer or location in summary
                company = "Canada Employer"
                location = "Canada"
                if summary:
                    parts = summary.split(" - ")
                    if len(parts) >= 2:
                        company = parts[0].strip()
                        location = parts[1].strip()

                if job_url and insert_job(company, title, location, "Canada-JobBank", job_url):
                    count += 1
    except Exception as e:
        print(f"[Canada Job Bank Error]: {e}")
    return count
    return count


# --- 7: Greenhouse Direct ATS Boards ---
def fetch_greenhouse_jobs() -> int:
    print("[*] Querying Greenhouse ATS company boards...")
    # Target tech companies hiring in Canada & Remote (including Canadian tech like ApplyBoard & Wealthsimple)
    companies = [
        "applyboard", "wealthsimple", "stripe", "figma", 
        "cloudflare", "github", "gitlab", "datadog", "pinterest"
    ]
    count = 0
    for company_slug in companies:
        try:
            url = f"https://boards-api.greenhouse.io/v1/boards/{company_slug}/jobs"
            res = requests.get(url, headers=HEADERS, timeout=10)
            if res.status_code == 200:
                data = res.json()
                for item in data.get("jobs", []):
                    title = item.get("title", "")
                    job_url = item.get("absolute_url", "")
                    loc = item.get("location", {}).get("name", "Remote / Canada")
                    
                    if job_url and insert_job(
                        company=company_slug.capitalize(),
                        title=title,
                        location=loc,
                        source_portal="Greenhouse",
                        original_url=job_url
                    ):
                        count += 1
        except Exception as e:
            print(f"[Greenhouse Error ({company_slug})]: {e}")

    return count


def run_collector():
    init_db()
    print("=== Starting Collector Across Target Boards ===\n")

    total = 0
    total += fetch_jobspy_boards(search_term="Software Developer", location="Canada")
    total += fetch_google_jobs()
    total += fetch_wellfound_jobs()
    total += fetch_canada_job_bank()
    total += fetch_greenhouse_jobs()

    print(f"\n[Done] Total new unique postings saved into database: {total}")

if __name__ == "__main__":
    run_collector()