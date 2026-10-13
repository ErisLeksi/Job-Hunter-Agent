import sqlite3
import re
import requests
from bs4 import BeautifulSoup

DB_PATH = "jobs.db"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
}

# --- 1. SENIORITY & NON-TECH EXCLUSIONS (Titles) ---
HARD_EXCLUDE_KEYWORDS = [
    r"\bsenior\b", r"\bsr\.?\b", r"\blead\b", r"\bprincipal\b", r"\bstaff\b",
    r"\bdirector\b", r"\bvp\b", r"\bvice president\b", r"\bhead of\b",
    r"\barchitect\b", r"\bmanager\b", r"\bintermediate\b", r"\bmid[\s-]level\b",
    r"\bdistinguished\b", r"\btech lead\b",

    # Common non-tech false-positives
    r"\bcnc\b", r"\boperator\b", r"\bwelder\b", r"\belectrician\b",
    r"\btechnician\b", r"\bmechanic\b", r"\bnurse\b", r"\bdriver\b",
    r"\bsales\b", r"\baccount executive\b", r"\brecruiter\b", r"\bmarketing\b"
]

# --- 2. CORE TECH VALIDATION ---
TECH_CORE_KEYWORDS = [
    r"\bsoftware\b", r"\bdeveloper\b", r"\bengineer\b", r"\bfrontend\b",
    r"\bfront-end\b", r"\bbackend\b", r"\bback-end\b", r"\bfullstack\b",
    r"\bfull-stack\b", r"\bfull stack\b", r"\bweb\b", r"\bprogrammer\b",
    r"\bdata analyst\b", r"\bdata engineer\b", r"\bdevops\b", r"\bqa\b"
]

# --- 3. EARLY-CAREER BOOSTERS (Includes Associate) ---
JUNIOR_BOOSTERS = [
    r"\bjunior\b", r"\bjr\.?\b", r"\bassociate\b", r"\bentry[\s-]level\b",
    r"\bnew grad\b", r"\bgraduate\b", r"\bintern\b", r"\binternship\b",
    r"\bco-op\b", r"\bcoop\b"
]

# --- 4. TARGET REGIONS (Ontario, PEI, NS, NB, SK + Remote / Canada) ---
TARGET_LOCATIONS = [
    # Provinces & abbreviations
    r"\bontario\b", r"\bon\b", r"\btoronto\b", r"\bottawa\b", r"\bwaterloo\b", r"\bkitchener\b",
    r"\bprince edward island\b", r"\bpei\b", r"\bp\.e\.i\b", r"\bcharlottetown\b",
    r"\bnova scotia\b", r"\bns\b", r"\bhalifax\b",
    r"\bnew brunswick\b", r"\bnb\b", r"\bfredericton\b", r"\bmoncton\b", r"\bsaint john\b",
    r"\bsaskatchewan\b", r"\bsk\b", r"\bregina\b", r"\bsaskatoon\b",
    # Broad/Remote
    r"\bremote\b", r"\bcanada\b", r"\banywhere\b"
]

# Explicit exclusions for off-target locations
EXCLUDED_LOCATIONS = [
    r"\bvancouver\b", r"\bbc\b", r"\bbritish columbia\b",
    r"\bcalgary\b", r"\bedmonton\b", r"\balberta\b", r"\bab\b",
    r"\bquebec\b", r"\bqc\b", r"\bmontreal\b",
    r"\bunited states\b", r"\busa\b", r"\buk\b", r"\beurope\b"
]

TECH_STACK_KEYWORDS = [
    r"\bpython\b", r"\bjavascript\b", r"\btypescript\b", r"\breact\b",
    r"\bnode\.?js\b", r"\bnext\.?js\b", r"\bsql\b", r"\bapi\b", r"\baws\b",
    r"\bvue\b", r"\bdjango\b", r"\bfastapi\b"
]


def check_location(loc_str: str) -> bool:
    """Checks if the location matches target provinces or remote/Canada tags."""
    if not loc_str:
        return True  # If unstated, don't drop prematurely

    loc_lower = loc_str.lower()
    
    # Drop if explicitly locked to another province/country without Remote/Canada
    is_remote_or_canada = any(re.search(p, loc_lower) for p in [r"\bremote\b", r"\bcanada\b"])
    if not is_remote_or_canada:
        for excl in EXCLUDED_LOCATIONS:
            if re.search(excl, loc_lower):
                return False

    return any(re.search(pat, loc_lower) for pat in TARGET_LOCATIONS)


def fetch_description(url: str, source: str) -> str:
    """Quickly extracts text content from job URL to check for hidden requirements."""
    try:
        if source == "Greenhouse" and "boards-api.greenhouse.io" in url:
            # If it's a Greenhouse API endpoint, fetch JSON directly
            res = requests.get(url, headers=HEADERS, timeout=6)
            if res.status_code == 200:
                content = res.json().get("content", "")
                return BeautifulSoup(content, "html.parser").get_text()
        
        # Standard web fallback
        res = requests.get(url, headers=HEADERS, timeout=6)
        if res.status_code == 200:
            soup = BeautifulSoup(res.text, "html.parser")
            # Strip scripts and styles
            for elem in soup(["script", "style", "nav", "footer"]):
                elem.decompose()
            return soup.get_text(separator=" ")
    except Exception:
        pass
    return ""


def extract_hidden_years_experience(text: str) -> int:
    """
    Scans body text for patterns like:
    '5+ years of experience', '7-10 years', 'minimum 6 years'
    Returns the highest required years found (0 if none or under 4).
    """
    if not text:
        return 0

    # Patterns matching: [digit]+ years / [digit]-[digit] years / minimum [digit] years
    patterns = [
        r"(\d+)\+?\s*(?:to|-)\s*(\d+)?\s*(?:years?|yrs?)(?:\s*of)?\s*(?:experience|exp)",
        r"(?:minimum|at least)\s*(\d+)\s*(?:years?|yrs?)",
        r"(\d+)\+\s*(?:years?|yrs?)(?:\s*of)?\s*(?:experience|exp)"
    ]

    max_years = 0
    for pat in patterns:
        matches = re.finditer(pat, text, re.IGNORECASE)
        for match in matches:
            groups = [int(g) for g in match.groups() if g and g.isdigit()]
            if groups:
                max_years = max(max_years, max(groups))

    return max_years


def evaluate_job(title: str, location: str, url: str, source: str):
    title_clean = title.strip()

    # 1. Title Hard Exclusions
    for pattern in HARD_EXCLUDE_KEYWORDS:
        if re.search(pattern, title_clean, re.IGNORECASE):
            matched = re.search(pattern, title_clean, re.IGNORECASE).group(0)
            return 0, f"EXCLUDED: Matched seniority/non-tech term '{matched}'"

    # 2. Location Filtering
    if not check_location(location):
        return 0, f"EXCLUDED: Location '{location}' outside target regions"

    # 3. Core Tech Requirement
    is_tech = any(re.search(pattern, title_clean, re.IGNORECASE) for pattern in TECH_CORE_KEYWORDS)
    if not is_tech:
        return 0, "EXCLUDED: Non-tech or unclassified role"

    # 4. Check Hidden Experience in Job Description (Condition 3)
    # Only scrape if the title doesn't already state intern/co-op
    is_intern = bool(re.search(r"\b(intern|internship|co-op|coop)\b", title_clean, re.IGNORECASE))
    if not is_intern and url:
        desc_text = fetch_description(url, source)
        years_req = extract_hidden_years_experience(desc_text)
        if years_req >= 4:
            return 0, f"EXCLUDED: Hidden experience requirement ({years_req}+ years found in description)"

    # Base score
    score = 50
    reasons = ["Baseline tech role"]

    # 5. Early-Career / Associate Boosters (+30 pts)
    for pattern in JUNIOR_BOOSTERS:
        match = re.search(pattern, title_clean, re.IGNORECASE)
        if match:
            score += 30
            reasons.append(f"Level match '{match.group(0)}'")
            break

    # 6. Tech Stack Boosters (+10 pts each, up to 20 max)
    stack_boost = 0
    for pattern in TECH_STACK_KEYWORDS:
        match = re.search(pattern, title_clean, re.IGNORECASE)
        if match:
            stack_boost += 10
            reasons.append(f"Stack '{match.group(0)}'")
            if stack_boost >= 20:
                break
    score += stack_boost

    return min(score, 100), "; ".join(reasons)


def run_matcher():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Pull jobs to evaluate
    cursor.execute("SELECT id, title, company, location, original_url, source_portal FROM jobs")
    all_jobs = cursor.fetchall()

    print(f"[*] Running deep evaluation on {len(all_jobs)} listings...")

    matched_count = 0
    rejected_count = 0

    for job_id, title, company, location, url, source in all_jobs:
        score, reason = evaluate_job(title, location, url, source)

        cursor.execute(
            """
            UPDATE jobs
            SET match_score = ?, match_reason = ?
            WHERE id = ?
            """,
            (score, reason, job_id)
        )

        if score > 0:
            matched_count += 1
        else:
            rejected_count += 1

    conn.commit()
    conn.close()

    print("\n=== Matching Complete ===")
    print(f"✅ Approved / High-Confidence Matches: {matched_count}")
    print(f"❌ Pruned / Filtered Roles: {rejected_count}")


if __name__ == "__main__":
    run_matcher()