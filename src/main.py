import os
import time
from dotenv import load_dotenv
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from football.bets import (
    navigate_to_football_live,
    scrape_matches,
    pick_bet_type,
    place_bet
)
from auth import login_sts
from football.bet_logic import (
    load_bets_data,
    save_bets_data,
    get_balance,
    clear_basket
)

def main():
    load_dotenv()

    username = os.getenv("STS_USERNAME")
    password = os.getenv("STS_PASSWORD")

    if not username or not password:
        print("Missing STS_USERNAME or STS_PASSWORD in .env!")
        return

    service = Service(ChromeDriverManager().install())
    options = Options()
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")

    driver = webdriver.Chrome(service=service, options=options)

    try:
        login_sts(driver, username, password)
        input("If a captcha appeared, solve it manually. Press Enter when finished...")
        print("Logged in successfully.")

        bets_data = load_bets_data()
        print(f"Loaded data: {len(bets_data['betted_matches'])} matches already bet.")

        while True:
            clear_basket(driver)

            balance = get_balance(driver)
            print(f"Current balance: {balance:.2f} zł")
            if balance < 2.0:
                print("Balance < 2.0, skipping bets.")
                time.sleep(60)
                continue

            navigate_to_football_live(driver)
            matches = scrape_matches(driver)
            print(f"Found {len(matches)} matches...")

            for (match_el, match_info) in matches:
                match_id = match_info["match_id"]
                if not match_id:
                    continue

                if match_id in bets_data["betted_matches"]:
                    continue

                outcome = pick_bet_type(match_info)
                if outcome is None:
                    continue

                bet_type, odd_val = outcome
                print(f"Attempting bet: {bet_type}, odd={odd_val:.2f} on {match_info['team_home']} vs {match_info['team_away']}")

                if get_balance(driver) < 2.0:
                    print("Balance dropped below 2.0, skipping bet.")
                    continue

                stake_used, potential_win = place_bet(driver, match_el, bet_type)
                if stake_used == 0:
                    print("Bet not placed. Possibly an error. Skipping.")
                    continue

                bets_data["betted_matches"].add(match_id)
                bets_data["bets_details"].append({
                    "match_id": match_id,
                    "teams": f"{match_info['team_home']} vs {match_info['team_away']}",
                    "stake": stake_used,
                    "potential_win": potential_win,
                    "balance_after": get_balance(driver),
                })

                save_bets_data(bets_data)

            print("Done checking. Sleep 60s...\n")
            time.sleep(60)

    finally:
        driver.quit()

if __name__ == "__main__":
    main()
