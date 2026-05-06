import asyncio
import csv
import os
import re
import time
from datetime import datetime
from dotenv import load_dotenv
from playwright.async_api import async_playwright
from playwright_stealth import Stealth
from bs4 import BeautifulSoup

# Load environment variables
load_dotenv()

# Configuration
LINKEDIN_USERNAME = os.getenv("LINKEDIN_USERNAME", "")
LINKEDIN_PASSWORD = os.getenv("LINKEDIN_PASSWORD", "")
TARGET_URL = "https://www.linkedin.com/company/opportunities-for-youth-organization/posts/?feedView=all"
OUTPUT_FOLDER = "outputs"
USER_DATA_DIR = "linkedin_session" # Persistent context
BATCH_SIZE = 50
SCROLL_PAUSE = 3.0 

async def save_batch_to_file(posts, batch_num):
    """Saves a batch of posts to a unique CSV file in the outputs folder."""
    if not os.path.exists(OUTPUT_FOLDER):
        os.makedirs(OUTPUT_FOLDER)
        
    filename = os.path.join(OUTPUT_FOLDER, f"batch_{batch_num}.csv")
    keys = ["date_relative", "text"]
    
    clean_posts = [{"date_relative": p["date_relative"], "text": p["text"]} for p in posts]
    
    with open(filename, 'w', newline='', encoding='utf-8') as f:
        dict_writer = csv.DictWriter(f, fieldnames=keys)
        dict_writer.writeheader()
        dict_writer.writerows(clean_posts)
    
    print(f"[{datetime.now().strftime('%H:%M:%S')}] ---> Saved Batch {batch_num} to {filename}")

async def scrape_linkedin():
    async with async_playwright() as p:
        # Using persistent context to handle login better
        context = await p.chromium.launch_persistent_context(
            user_data_dir=USER_DATA_DIR,
            headless=False,
            viewport={'width': 1280, 'height': 900},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
        )
        
        page = context.pages[0] if context.pages else await context.new_page()
        stealth_obj = Stealth()
        await stealth_obj.apply_stealth_async(page)

        # 1. Check Login
        print(f"[{datetime.now().strftime('%H:%M:%S')}] Navigating to login page...")
        await page.goto("https://www.linkedin.com/login", wait_until="load")
        
        if "feed" not in page.url:
            if LINKEDIN_USERNAME and LINKEDIN_PASSWORD:
                print(f"[{datetime.now().strftime('%H:%M:%S')}] Attempting login...")
                try:
                    selectors = ['input[name="session_key"]', '#username', '#session_key']
                    username_field = None
                    for sel in selectors:
                        try:
                            username_field = await page.wait_for_selector(sel, timeout=3000)
                            if username_field: break
                        except: continue
                    
                    if username_field:
                        await username_field.fill(LINKEDIN_USERNAME)
                        await page.fill('input[name="session_password"], #password', LINKEDIN_PASSWORD)
                        await page.click('button[type="submit"]')
                        print(f"[{datetime.now().strftime('%H:%M:%S')}] Login form submitted.")
                except Exception as e:
                    print(f"[{datetime.now().strftime('%H:%M:%S')}] Login sequence failed: {e}")
            
            print(f"[{datetime.now().strftime('%H:%M:%S')}] Waiting for session stability...")
            await asyncio.sleep(10)
        else:
            print(f"[{datetime.now().strftime('%H:%M:%S')}] Already logged in.")

        # 2. Navigate to target company posts
        print(f"[{datetime.now().strftime('%H:%M:%S')}] Navigating to: {TARGET_URL}")
        await page.goto(TARGET_URL)
        
        # Wait for actual post containers to appear
        try:
            print(f"[{datetime.now().strftime('%H:%M:%S')}] Waiting for posts to load...")
            await page.wait_for_selector(".feed-shared-update-v2, [data-urn]", timeout=30000)
        except Exception:
            print(f"[{datetime.now().strftime('%H:%M:%S')}] Timeout waiting for post containers. Checking page content anyway.")

        # 3. Scrape Loop
        all_post_ids = set()
        current_batch = []
        batch_count = 1
        last_height = await page.evaluate("document.body.scrollHeight")
        total_scraped = 0
        consecutive_zero_new = 0
        
        print(f"[{datetime.now().strftime('%H:%M:%S')}] Starting scrape loop...")
        
        while True:
            html = await page.content()
            soup = BeautifulSoup(html, "html.parser")
            # Broader container selection
            containers = soup.select(".feed-shared-update-v2, .main-feed-activity-card-with-comments, [data-urn^='urn:li:activity:']")
            
            new_in_this_pass = 0
            for container in containers:
                try:
                    post_id = container.get("data-urn", "")
                    if not post_id or post_id in all_post_ids:
                        continue
                        
                    # --- Extract Post Text ---
                    post_text = ""
                    text_selectors = [
                        ".feed-shared-update-v2__description-wrapper",
                        ".update-components-text",
                        ".feed-shared-text",
                        ".feed-shared-update-v2__commentary",
                        ".feed-shared-text-view",
                        ".break-words"
                    ]
                    for sel in text_selectors:
                        text_elem = container.select_one(sel)
                        if text_elem:
                            post_text = text_elem.get_text(separator=" ", strip=True)
                            if post_text: break
                    
                    # --- Extract Date ---
                    date_elem = container.select_one(".update-components-actor__sub-description, .feed-shared-actor__sub-description")
                    post_date = date_elem.get_text(strip=True).split("•")[0].strip() if date_elem else "Unknown"

                    all_post_ids.add(post_id)
                    total_scraped += 1
                    new_in_this_pass += 1
                    
                    current_batch.append({
                        "date_relative": post_date,
                        "text": post_text
                    })
                    
                    if len(current_batch) >= BATCH_SIZE:
                        await save_batch_to_file(current_batch, batch_count)
                        current_batch = []
                        batch_count += 1
                        
                except Exception as e:
                    pass

            if new_in_this_pass > 0:
                print(f"[{datetime.now().strftime('%H:%M:%S')}] Total Scraped: {total_scraped} (+{new_in_this_pass} new)")
                consecutive_zero_new = 0
            else:
                consecutive_zero_new += 1

            # Scroll
            await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            await asyncio.sleep(SCROLL_PAUSE)
            
            new_height = await page.evaluate("document.body.scrollHeight")
            if new_height == last_height or consecutive_zero_new > 5:
                await page.evaluate("window.scrollBy(0, -600)")
                await asyncio.sleep(1)
                await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                await asyncio.sleep(SCROLL_PAUSE)
                new_height = await page.evaluate("document.body.scrollHeight")
                
                if new_height == last_height and consecutive_zero_new > 8:
                    print(f"[{datetime.now().strftime('%H:%M:%S')}] End reached.")
                    break
            last_height = new_height

        if current_batch:
            await save_batch_to_file(current_batch, batch_count)

        print(f"[{datetime.now().strftime('%H:%M:%S')}] Finished. Total: {total_scraped}")
        await context.close()

if __name__ == "__main__":
    asyncio.run(scrape_linkedin())
