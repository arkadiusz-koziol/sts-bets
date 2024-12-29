import os
import time
from dotenv import load_dotenv
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.by import By
from selenium.common.exceptions import NoSuchElementException

from bets import (
    navigate_to_football_live,
    scrape_matches,
    pick_bet_type,
    place_bet
)
from auth import login_sts

def get_balance(driver):
    try:
        balance_el = driver.find_element(
            By.CSS_SELECTOR, 
            "sts-shared-icon-button-deposit-info .icon-button-deposit-info__amount"
        )
        raw_text = balance_el.text.strip()
        cleaned_text = raw_text.replace("zł", "").replace("\xa0", "").strip()
        cleaned_text = cleaned_text.replace(",", ".")
        return float(cleaned_text)
    except NoSuchElementException:
        print("Could not find the deposit info element. Returning 0.0.")
        return 0.0
    except ValueError:
        print("Error parsing balance text. Returning 0.0.")
        return 0.0
    except Exception as e:
        print(f"Unexpected error reading balance: {e}")
        return 0.0

def main():
    load_dotenv()

    username = os.getenv("STS_USERNAME")
    password = os.getenv("STS_PASSWORD")

    if not username or not password:
        print("Missing STS_USERNAME or STS_PASSWORD in .env!")
        return

    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service)

    try:
        login_sts(driver, username, password)
        input("If a captcha appeared, solve it manually. Press Enter when finished...")

        print("Logged in successfully. Starting the betting loop...")

        betted_matches = set()
        while True:
            balance = get_balance(driver)
            print(f"Current balance: {balance:.2f} zł")
            
            if balance < 2.0:
                print("Balance is below 2.00 zł, skipping bets this round.")
                print("Waiting 60 seconds before next check...\n")
                time.sleep(60)
                continue

            navigate_to_football_live(driver)
            matches = scrape_matches(driver)
            print(f"Found {len(matches)} matches...")

            for (match_el, match_info) in matches:
                match_id = match_info["match_id"]
                if not match_id:
                    continue

                if match_id in betted_matches:
                    continue

                outcome = pick_bet_type(match_info)
                if outcome is None:
                    continue

                bet_type, odd_val = outcome
                print(f"Placing bet: {bet_type} (odd={odd_val:.2f}) on match "
                      f"{match_info['team_home']} vs {match_info['team_away']}")

                place_bet(driver, match_el, bet_type)

                betted_matches.add(match_id)

            print("Done checking. Waiting 60 seconds before next check...\n")
            time.sleep(60)

    finally:
        driver.quit()

if __name__ == "__main__":
    main()
