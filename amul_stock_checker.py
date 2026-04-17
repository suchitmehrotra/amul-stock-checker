"""
Amul High Protein Lassi - Stock Checker
Checks availability of Plain and Rose Lassi (Pack of 30) for pincode 201310
(ATS Pristine, Noida) and sends a combined Telegram notification.
"""

import sys
import json
import time
import os
import urllib.request
import urllib.parse

# --- CONFIG ---
RECIPIENTS = [
    (os.environ['SUCHIT_TOKEN'], os.environ['SUCHIT_CHAT_ID'], "Suchit"),
    (os.environ['SUYASH_TOKEN'], os.environ['SUYASH_CHAT_ID'], "Suyash"),
]
PINCODE = "201310"
PRODUCTS = {
    "plain": {
        "alias": "amul-high-protein-plain-lassi-200-ml-or-pack-of-30",
        "label": "Amul High Protein Plain Lassi (Pack of 30)",
        "url": "https://shop.amul.com/en/product/amul-high-protein-plain-lassi-200-ml-or-pack-of-30",
    },
    "rose": {
        "alias": "amul-high-protein-rose-lassi-200-ml-or-pack-of-30",
        "label": "Amul High Protein Rose Lassi (Pack of 30)",
        "url": "https://shop.amul.com/en/product/amul-high-protein-rose-lassi-200-ml-or-pack-of-30",
    },
}


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

    results = {key: None for key in PRODUCTS}  # None = not found, dict = product info

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
                        alias = item.get('alias', '').lower()
                        for key, product in PRODUCTS.items():
                            if product['alias'] in alias or (
                                'lassi' in alias and (
                                    ('plain' in alias and key == 'plain') or
                                    ('rose' in alias and key == 'rose')
                                )
                            ):
                                if item.get('available') and item.get('inventory_quantity', 0) > 0:
                                    results[key] = item
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

    return results


def main():
    from datetime import datetime, timezone, timedelta
    IST = timezone(timedelta(hours=5, minutes=30))
    check_time = datetime.now(IST).strftime("%d %b %Y, %I:%M %p IST")
    print(f"[{check_time}] Checking Amul High Protein Lassi stock for pincode {PINCODE}...")

    results = check_stock()

    any_in_stock = any(v is not None for v in results.values())

    # First line = notification preview: show plain/rose status at a glance
    plain_status = "IN STOCK ✅" if results.get("plain") else "OUT ❌"
    rose_status = "IN STOCK ✅" if results.get("rose") else "OUT ❌"
    preview_line = f"Plain: {plain_status} | Rose: {rose_status}"

    lines = [f"{preview_line}\n"]

    for key, product in PRODUCTS.items():
        info = results[key]
        if info:
            price = info.get('price', 'N/A')
            inv = info.get('inventory_quantity', 'N/A')
            lines.append(
                f"✅ *{product['label']}*\n"
                f"💰 Price: ₹{price} | Units: {inv}\n"
                f"👉 [Order now]({product['url']})\n"
            )
        else:
            lines.append(f"❌ *{product['label']}*\n_Not available_\n")

    lines.append(f"_Checked at: {check_time}_")
    msg = "\n".join(lines)

    if any_in_stock:
        print("🎉 AT LEAST ONE PRODUCT IS IN STOCK! Sending Telegram notifications...")
    else:
        print("Neither product is in stock. Sending Telegram notification...")

    notify_all(msg)


if __name__ == "__main__":
    main()
