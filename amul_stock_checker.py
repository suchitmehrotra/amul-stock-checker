"""
Amul High Protein Plain Lassi - Stock Checker
Checks availability for pincode 201310 (ATS Pristine, Noida)
and sends a Telegram notification when the product is back in stock.
"""

import sys
import json
import time
import os
import urllib.request
import urllib.parse

# --- CONFIG ---
# Tokens can be overridden via environment variables (for GitHub Actions secrets)
RECIPIENTS = [
    (os.environ['SUCHIT_TOKEN'], os.environ['SUCHIT_CHAT_ID'], "Suchit"),
    (os.environ['SUYASH_TOKEN'], os.environ['SUYASH_CHAT_ID'], "Suyash"),
]
PINCODE = "201310"
PRODUCT_ALIAS = "amul-high-protein-plain-lassi-200-ml-or-pack-of-30"
PRODUCT_URL = f"https://shop.amul.com/en/product/{PRODUCT_ALIAS}"


def send_telegram_message(token, chat_id, text):
    data = urllib.parse.urlencode({
        'chat_id': chat_id,
        'text': text,
        'parse_mode': 'Markdown'
    }).encode()
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    req = urllib.request.Request(url, data=data)
    try:
        with urllib.request.urlopen(req, timeout=10) as r:
            resp = json.loads(r.read())
            return resp.get('ok', False)
    except Exception as e:
        print(f"Telegram error: {e}")
        return False


def notify_all(msg):
    for token, chat_id, name in RECIPIENTS:
        sent = send_telegram_message(token, chat_id, msg)
        print(f"  → {name}: {'✅ sent' if sent else '❌ failed'}")


def check_stock():
    from playwright.sync_api import sync_playwright

    product_found = False
    product_info = {}

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) '
                       'AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        )
        page = context.new_page()

        def on_response(response):
            if 'ms.products' in response.url:
                try:
                    body = response.json()
                    for item in body.get('data', []):
                        if 'lassi' in item.get('alias', '').lower():
                            nonlocal product_found, product_info
                            if item.get('available') and item.get('inventory_quantity', 0) > 0:
                                product_found = True
                                product_info = item
                except Exception:
                    pass

        page.on('response', on_response)

        # Set pincode
        page.goto('https://shop.amul.com/', timeout=30000)
        page.wait_for_load_state('networkidle', timeout=15000)
        time.sleep(1)
        try:
            page.locator('input').first.fill(PINCODE)
            time.sleep(1)
            page.locator(f'text={PINCODE}').first.click(timeout=5000)
            time.sleep(2)
        except Exception as e:
            print(f"Pincode error: {e}")

        # Browse protein category to trigger product API calls
        page.goto('https://shop.amul.com/en/browse/protein', timeout=30000)
        page.wait_for_load_state('networkidle', timeout=20000)
        time.sleep(3)
        page.evaluate('window.scrollTo(0, document.body.scrollHeight)')
        time.sleep(2)

        browser.close()

    return product_found, product_info


def main():
    from datetime import datetime
    check_time = datetime.now().strftime("%d %b %Y, %I:%M %p")
    print(f"[{check_time}] Checking Amul High Protein Lassi stock for pincode {PINCODE}...")

    is_available, info = check_stock()

    if is_available:
        name = info.get('name', 'Amul High Protein Plain Lassi')
        price = info.get('price', 'N/A')
        inv = info.get('inventory_quantity', 'N/A')
        msg = (
            f"\U0001f389 *IN STOCK!*\n\n"
            f"*{name}* is available for delivery to ATS Pristine, Noida (201310)!\n\n"
            f"\U0001f4b0 Price: \u20b9{price}\n"
            f"\U0001f4e6 Units available: {inv}\n\n"
            f"\U0001f449 [Order now]({PRODUCT_URL})\n\n"
            f"_Hurry \u2014 stock may be limited!_\n"
            f"_Checked at: {check_time}_"
        )
        print("🎉 PRODUCT IS IN STOCK! Sending Telegram notifications...")
        notify_all(msg)
    else:
        msg = (
            f"\u274c *Not available yet*\n\n"
            f"*Amul High Protein Plain Lassi (Pack of 30)* is still not available "
            f"for delivery to ATS Pristine, Noida (201310).\n\n"
            f"_Checked at: {check_time}_\n"
            f"_Checking again every 10 minutes..._"
        )
        print("Not in stock. Sending Telegram notification...")
        notify_all(msg)


if __name__ == "__main__":
    main()
