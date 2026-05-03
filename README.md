# HubSpot Company Sourcer

Automated pipeline that runs every 5 minutes, scrapes DuckDuckGo for domains
using HubSpot signals, detects confirmed HubSpot usage, and pushes new companies
into your HubSpot CRM with `hubspot_user = true`.

## How it works

```
query (queries.py)
  → scrape DuckDuckGo (scraper.py)
  → deduplicate against seen_domains.txt + HubSpot CRM (dedup.py)
  → detect HubSpot usage (detect.py → hubspot_detector.py)
  → push confirmed companies to CRM (push.py → hubspot_api.py)
  → log run metrics to run_log.csv (logger.py)
```

Each run picks the next query from a bank of 60+ search strings targeting
HubSpot JS snippets, forms, COS templates, and behavioural signals. The query
order shuffles daily (seeded by date) and rotates sequentially within the day.

---

## Setup

### 1. Clone the repo

```bash
git clone https://github.com/omchoithwani/hubspot-sourcer.git
cd hubspot-sourcer
```

### 2. Create a virtual environment

```bash
python3 -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure credentials

```bash
cp .env.example .env
```

Open `.env` and set your HubSpot Private App token:

```
HUBSPOT_TOKEN=pat-na1-xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx
```

To get a token: **HubSpot → Settings → Integrations → Private Apps → Create a private app**.  
Required scopes: `crm.objects.companies.read`, `crm.objects.companies.write`.

### 5. Create the `hubspot_user` property in HubSpot

In HubSpot, go to **Settings → Properties → Company properties → Create property**:

- Label: `HubSpot User`  
- Internal name: `hubspot_user`  
- Field type: Single checkbox (or text)

---

## Running locally

**Single run** (useful for testing):

```bash
python main.py
```

**Continuous scheduler** (runs every 5 minutes):

```bash
python scheduler.py
```

Logs are printed to stdout and appended to `run_log.csv`.

---

## File reference

| File | Purpose |
|------|---------|
| `main.py` | Orchestrates one full run |
| `queries.py` | 60-query bank + daily-shuffled sequential rotation |
| `scraper.py` | DuckDuckGo HTML scraper + domain extractor |
| `dedup.py` | Two-stage dedup: local file then HubSpot CRM |
| `detect.py` | Thin wrapper around `hubspot_detector.py` |
| `push.py` | Create or update Company in HubSpot CRM |
| `logger.py` | Appends one CSV row per run to `run_log.csv` |
| `auth.py` | Loads HubSpot token from `.env` |
| `scheduler.py` | Runs `main.py` every 5 minutes via `schedule` |
| `hubspot_detector.py` | Core detection logic (DNS, HTTP headers, HTML patterns) |
| `hubspot_api.py` | HubSpot CRM API helpers |
| `seen_domains.txt` | Flat dedup store — created on first run |
| `run_log.csv` | Run metrics — created on first run |

---

## Deploying on Render

1. Push this repo to GitHub.

2. In [Render](https://render.com), create a new **Background Worker**:
   - **Environment**: Python 3
   - **Build command**: `pip install -r requirements.txt`
   - **Start command**: `python scheduler.py`

3. Under **Environment Variables**, add:
   ```
   HUBSPOT_TOKEN = pat-na1-...
   ```

4. Deploy. Render will keep the worker running indefinitely, restarting it if it crashes.

> **Persistent files note**: `seen_domains.txt`, `run_log.csv`, and `run_counter.txt`
> are written to the local filesystem. On Render's free tier the disk is ephemeral —
> files reset on each deploy. To persist them across deploys, either:
> - Use a Render **Persistent Disk** (paid), or
> - Replace the file-based stores with a lightweight database (e.g. Render PostgreSQL or Redis).

---

## Switching to OAuth

All auth is isolated in `auth.py`. When you're ready to switch from a Private App
token to OAuth, replace `get_token()` in `auth.py` with your OAuth token-fetch logic.
No other file needs to change.
