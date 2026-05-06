# LinkedIn Post Scraper Setup

This project provides a robust LinkedIn scraper using **Playwright** and **BeautifulSoup**.

## Prerequisites

1. **Python 3.8+**
2. **Playwright Dependencies**:
   ```bash
   pip install playwright playwright-stealth beautifulsoup4 python-dotenv
   playwright install chromium
   ```

## Configuration

1. Copy `.env.example` to `.env`:
   ```bash
   cp .env.example .env
   ```
2. Fill in your LinkedIn credentials in `.env`:
   - `LINKEDIN_USERNAME`: Your LinkedIn email.
   - `LINKEDIN_PASSWORD`: Your LinkedIn password.

## Running the Scraper

Run the following command:
```bash
python linkedin_scraper.py
```

## Features

- **Stealth Mode**: Uses `playwright-stealth` to bypass basic bot detection.
- **Infinite Scroll**: Automatically scrolls to load more posts (default limit: 50).
- **Data Export**: Saves scraped data (text, relative date, likes, comments) to `linkedin_posts.csv`.

## Troubleshooting

- **Authwall/Captcha**: LinkedIn may trigger a Captcha. If running with `headless=False` (default), you can solve the captcha manually in the browser window.
- **Selectors**: LinkedIn frequently updates its class names. If the scraper stops finding data, inspect the page and update the CSS selectors in `linkedin_scraper.py`.

## Note on Ethics & Terms of Service

Scraping LinkedIn may violate their Terms of Service. Use this tool responsibly and for educational purposes only.
