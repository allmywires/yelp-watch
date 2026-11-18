# 🍽️ Yelp Watch

A local dashboard to monitor your favorite restaurant waitlists via screenshots of their Yelp pages.

## Features

- **Watchlist** — Add and manage your favorite restaurants
- **Screenshot capture** — One-click check of all restaurants, or individual checks
- **Gallery** — View latest screenshots in a clean grid
- **History** — Each check is timestamped so you can track wait time trends

## How It Works

This app takes screenshots of your restaurants' Yelp pages to check for waitlist info. No API integration — it simply captures what you see on the page.

## Setup

### 1. Install dependencies

```bash
pip install -r requirements.txt
playwright install chromium
```

### 2. Run the app

```bash
uvicorn main:app --reload --port 8000
```

### 3. Open the dashboard

Navigate to `http://localhost:8000` in your browser.

## Usage

1. **Add a restaurant** — Enter the name and Yelp URL
2. **Check all** — Click "Check All Waitlists" to screenshot every restaurant
3. **Individual check** — Use the "Check" button on any restaurant for a single capture
4. **Open in browser** — Click "Open" to view the page live
5. **Remove** — Click "✕" to delete a restaurant from your watchlist

## Tech Stack

- **Backend:** Python, FastAPI, aiosqlite
- **Screenshots:** Playwright (headless Chromium)
- **Frontend:** Vanilla HTML/CSS/JS
- **Storage:** SQLite database + local screenshot files

## Notes

- Runs entirely local — no server, no data leaves your machine
- Screenshots are stored in `screenshots/` directory
- Database is `yelp_watch.db` in the project root
