# 🎯 Job-Hunter-Agent

> **Status:** 🚧 Active Development — Phase 1 Complete, Advanced Agent Pipeline in Progress

An autonomous, multi-source pipeline and personal job-hunting agent engineered to aggregate, deduplicate, evaluate, and surface early-career tech opportunities across Canada and North America.

---

## 📌 Project Status & System Overview

This project is being engineered incrementally to handle real-world edge cases in automated job acquisition: anti-bot protections, inconsistent job formats, high-noise non-technical postings, and opaque job requirements.

* **Current State:** Data collection and storage pipeline is operational. Over 2,100 listings have been indexed from 7 target boards and feeds into a local SQLite database with URL-based deduplication.
* **In Progress:** Designing the rule-based heuristic gate and semantic evaluation system (`matcher.py`), followed by real-time notification dispatch.

The architecture decouples heavy ingestion from multi-stage decision reasoning:

1. **Collector (Ingestion Layer — Operational):** Gathers structured feeds, public APIs, and raw job cards across 7 sources, saving unique rows directly into SQLite.
2. **Matcher (Reasoning & Scoring Layer — In Progress):** Applies a two-tier filter: fast deterministic keyword/title elimination followed by deep semantic scoring against candidate profile requirements.
3. **Notifier (Delivery Layer — Planned):** Formats high-confidence matches into actionable briefs with company metadata and application URLs.
4. **Autonomous Agent Loop (Orchestration Layer — Planned):** Manages recurring scheduled runs, proxy rotation, state persistence, and application lifecycle tracking.

---

## 📐 Architecture & Data Flow

```text
┌────────────────────────────────────────────────────────────────────────┐
│                     7 Target Ingestion Sources                         │
│  (LinkedIn, Indeed, Glassdoor, Google for Jobs, Wellfound,             │
│   Canada Job Bank Atom XML Feed, Greenhouse REST API)                  │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │
                                    ▼
                             [collector.py]
                                    │
                                    ▼
                            [(jobs.db SQLite)]
                                    │
                   ┌────────────────┴────────────────┐
                   ▼                                 ▼
      [Tier 1: Heuristic Filter]        [Tier 2: Semantic Matcher]
      - Title & seniority pruning       - JD deep scraper
      - Tech-only domain filter         - Resume / skills scoring
                   └────────────────┬────────────────┘
                                    │
                                    ▼
                           [jobs.db (Scored)]
                                    │
                                    ▼
                           [Telegram Dispatcher]
                         - Rich notification card
                         - Direct apply link
                                    │
                                    ▼
                         [Application Tracker]
```

---

## 🌐 Integrated Target Sources

| Source Portal | Ingestion Method | Status | Notes |
| :--- | :--- | :--- | :--- |
| **LinkedIn** | `python-jobspy` | Active | Target search queries for software developer roles |
| **Indeed** | `python-jobspy` | Active | Location-targeted Canadian postings |
| **Glassdoor** | `python-jobspy` | Active | Employer aggregator data |
| **Google for Jobs** | Search HTML Parser | Active | Broad-scope aggregated web results |
| **Wellfound** | Direct Web Parser | Active | AngelList startup roles & early-stage teams |
| **Canada Job Bank** | Atom XML Feed | Active | Official federal feed (`jobSearchRSSfeed`) via `xml.etree` |
| **Greenhouse ATS** | Public REST API | Active | Direct company endpoints (`boards-api.greenhouse.io`) |

---

## 🛠️ Tech Stack

* **Core Runtime:** Python 3.10+
* **Storage & State:** SQLite (`jobs.db`) with unique indexing and deduplication logic
* **Data Ingestion:** `requests`, `BeautifulSoup4`, `python-jobspy`, `xml.etree.ElementTree`
* **Parsing & Heuristics:** Regular expressions, token matchers, structured JSON extractors
* **Planned Agent Tooling:** Pydantic models, LLM scoring engine (OpenAI / Claude / Gemini API), python-telegram-bot

---

## 🗺️ Engineering & Development Roadmap

### Phase 1: Ingestion Pipeline & Persistence (Complete)
- [x] Multi-source ingestion pipeline architecture (`collector.py`)
- [x] SQLite database schema with URL-based conflict handling (`database.py`)
- [x] Canada Job Bank Atom XML parser (`fetch_canada_job_bank`)
- [x] Greenhouse ATS multi-company API ingestion engine (`fetch_greenhouse_jobs`)
- [x] Initial dataset validation (2,100+ unique postings indexed)

### Phase 2: Heuristic Filtering & Data Normalization (In Progress)
- [ ] **Deterministic Exclusion Filter:** Fast-drop rule engine for non-tech roles, trades, and unqualified titles (e.g., CNC operators, drivers, non-software engineering).
- [ ] **Seniority Gate:** Strict title boundary enforcement against senior, lead, principal, staff, architect, VP, director, and intermediate designations.
- [ ] **Target Role Whitelisting:** Affirmative inclusion triggers for junior, associate, entry-level, new grad, intern, and general developer titles.
- [ ] **Location & Work-Style Normalization:** Categorize postings by work style (Remote, Hybrid, On-site) and region (Canada-wide, Ontario corridor, US/NA eligible).

### Phase 3: Deep Scraping & Semantic Reasoning Engine
- [ ] **Full Description Fetcher:** Asynchronous worker to resolve raw URLs and extract full body text/responsibilities from job postings.
- [ ] **Candidate Profile Schema:** Configuration containing candidate skills, preferred tech stack, frameworks, and education level.
- [ ] **LLM Evaluation & Match Scoring:**
  - Semantic fit analysis (0–100 relevance score).
  - Explicit extraction of true years-of-experience requirements vs. title inflation.
  - Identification of visa/work-authorization prerequisites and clearance checks.
  - Rejection categorization (e.g., "Mismatched Stack", "Requires 5+ Years", "Clearance Required").

### Phase 4: Notification & Dispatch System
- [ ] **Telegram Bot Integration:** Dedicated channel bot formatting matches into structured briefing cards.
- [ ] **Notification Throttling & Batching:** Digest modes (instant high-priority alerts vs. daily summary briefings) to avoid notification fatigue.
- [ ] **Interactive Action Buttons:** Telegram inline keyboard buttons to mark listings as "Applied", "Saved", or "Irrelevant".

### Phase 5: Application Tracking & Feedback Loop
- [ ] **Application Lifecycle Schema:** Database tracking of applied roles (`status: DISCOVERED -> MATCHED -> APPLIED -> INTERVIEW -> ARCHIVED`).
- [ ] **Feedback Fine-Tuning:** Use user thumbs-up/down actions on notifications to adjust future semantic matching weights.
- [ ] **Duplicate Cross-Posting Detection:** Fuzzy title + company matching to prevent alerts for the same role syndicated across multiple platforms.

### Phase 6: Orchestration, Resilience & Deployment
- [ ] **Bot-Detection Mitigation:** Header randomization, adaptive backoff intervals, and proxy integration for challenged endpoints.
- [ ] **Automated Scheduling:** Headless execution via GitHub Actions cron workflows or a local system daemon.
- [ ] **Health Monitoring & Dead-Feed Alerts:** Automated checks notifying when source structures change, endpoints break, or anti-bot defenses trigger.