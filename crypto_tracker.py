"""
Cryptocurrency Price Tracker
Scrapes real-time crypto prices from CoinMarketCap using Selenium.
Features: CSV export, historical logging, price/change filtering, headless toggle.
"""

import time
import os
import pandas as pd
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium_stealth import stealth
from webdriver_manager.chrome import ChromeDriverManager

# ─────────────────────────────────────────────
#  CONFIGURATION — Edit these settings
# ─────────────────────────────────────────────

HEADLESS = False          # True = background mode, False = visible browser
TOP_N = 10                # Number of top coins to scrape

# Filtering (set to None to disable)
MIN_PRICE = None          # e.g. 100.0 — only coins priced above this value
MAX_PRICE = None          # e.g. 50000.0 — only coins priced below this value
MIN_CHANGE_24H = None     # e.g. 2.0 — only coins with 24h change > 2%
MAX_CHANGE_24H = None     # e.g. -1.0 — only coins with 24h change < -1%

OUTPUT_FILE = "crypto_prices.csv"   # CSV file to save/append data

# ─────────────────────────────────────────────


def create_driver(headless: bool) -> webdriver.Chrome:
    """Create and configure a Chrome WebDriver with stealth settings."""
    options = Options()

    if headless:
        options.add_argument("--headless=new")
        print("[INFO] Running in headless (background) mode.")
    else:
        print("[INFO] Running in visible browser mode.")

    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_argument("--window-size=1920,1080")
    options.add_argument(
        "user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    )
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option("useAutomationExtension", False)

    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=options)

    stealth(
        driver,
        languages=["en-US", "en"],
        vendor="Google Inc.",
        platform="Win32",
        webgl_vendor="Intel Inc.",
        renderer="Intel Iris OpenGL Engine",
        fix_hairline=True,
    )

    return driver


def scrape_crypto_data(driver: webdriver.Chrome, top_n: int) -> list[dict]:
    """Navigate to CoinMarketCap and scrape top N coin data."""
    url = "https://coinmarketcap.com/"
    print(f"[INFO] Loading {url} ...")
    driver.get(url)

    # Wait for the coin table to load
    wait = WebDriverWait(driver, 20)
    wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "table tbody tr")))
    time.sleep(3)  # Allow JS to fully render

    rows = driver.find_elements(By.CSS_SELECTOR, "table tbody tr")
    print(f"[INFO] Found {len(rows)} rows. Extracting top {top_n}...")

    coins = []
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    for row in rows[:top_n]:
        try:
            cells = row.find_elements(By.TAG_NAME, "td")
            if len(cells) < 8:
                continue

            # Rank
            rank = cells[1].text.strip()

            # Name & Symbol
            name_cell = cells[2].text.strip().split("\n")
            name = name_cell[0] if len(name_cell) > 0 else "N/A"
            symbol = name_cell[1] if len(name_cell) > 1 else "N/A"

            # Price
            price_text = cells[3].text.strip().replace("$", "").replace(",", "")
            price = float(price_text) if price_text else 0.0

            # 24h Change
            change_text = cells[4].text.strip().replace("%", "").replace("+", "")
            change_24h = float(change_text) if change_text else 0.0

            # Market Cap
            market_cap = cells[7].text.strip()

            coins.append({
                "Timestamp": timestamp,
                "Rank": rank,
                "Name": name,
                "Symbol": symbol,
                "Price (USD)": price,
                "24h Change (%)": change_24h,
                "Market Cap": market_cap,
            })

        except (ValueError, IndexError) as e:
            print(f"[WARN] Skipped a row due to parse error: {e}")
            continue

    return coins


def apply_filters(coins: list[dict]) -> list[dict]:
    """Apply user-defined price and change filters."""
    filtered = coins

    if MIN_PRICE is not None:
        filtered = [c for c in filtered if c["Price (USD)"] >= MIN_PRICE]
    if MAX_PRICE is not None:
        filtered = [c for c in filtered if c["Price (USD)"] <= MAX_PRICE]
    if MIN_CHANGE_24H is not None:
        filtered = [c for c in filtered if c["24h Change (%)"] >= MIN_CHANGE_24H]
    if MAX_CHANGE_24H is not None:
        filtered = [c for c in filtered if c["24h Change (%)"] <= MAX_CHANGE_24H]

    removed = len(coins) - len(filtered)
    if removed > 0:
        print(f"[FILTER] {removed} coin(s) removed by active filters.")

    return filtered


def save_to_csv(coins: list[dict], filepath: str):
    """Append coin data to CSV (creates file if it doesn't exist)."""
    df = pd.DataFrame(coins)
    file_exists = os.path.isfile(filepath)

    df.to_csv(filepath, mode="a", header=not file_exists, index=False)

    if file_exists:
        print(f"[CSV] Data appended to '{filepath}' (historical logging).")
    else:
        print(f"[CSV] New file created: '{filepath}'.")


def display_results(coins: list[dict]):
    """Print a formatted table of results to the console."""
    if not coins:
        print("[INFO] No coins to display after filtering.")
        return

    print("\n" + "=" * 75)
    print(f"{'Rank':<6} {'Name':<18} {'Symbol':<8} {'Price (USD)':>14} {'24h %':>9}  {'Market Cap'}")
    print("=" * 75)

    for c in coins:
        change = c["24h Change (%)"]
        change_str = f"+{change:.2f}%" if change >= 0 else f"{change:.2f}%"
        print(
            f"{c['Rank']:<6} {c['Name']:<18} {c['Symbol']:<8} "
            f"${c['Price (USD)']:>13,.4f} {change_str:>9}  {c['Market Cap']}"
        )

    print("=" * 75)
    print(f"Scraped at: {coins[0]['Timestamp']}\n")


def main():
    print("\n=== Cryptocurrency Price Tracker ===\n")

    driver = create_driver(HEADLESS)

    try:
        coins = scrape_crypto_data(driver, TOP_N)
    finally:
        driver.quit()
        print("[INFO] Browser closed.")

    if not coins:
        print("[ERROR] No data scraped. CoinMarketCap may have blocked the request.")
        return

    # Apply filters
    coins = apply_filters(coins)

    # Display in console
    display_results(coins)

    # Save to CSV (with historical logging via append mode)
    if coins:
        save_to_csv(coins, OUTPUT_FILE)

    print("[DONE] Tracker finished successfully.")


if __name__ == "__main__":
    main()