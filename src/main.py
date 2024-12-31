import os
import time
from dotenv import load_dotenv
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from common.auth import login_sts
from common.bet_logic import (
    load_bets_data,
    save_bets_data,
    get_balance,
    clear_basket
)

# Sports modules
from sports.football import (
    navigate_to_football_live,
    scrape_football_matches,
    pick_football_bet_type,
    place_bet
)
from sports.hockey import (
    navigate_to_hockey_live,
    scrape_hockey_matches,
    pick_hockey_bet_type
)
from sports.basketball import (
    navigate_to_basketball_live,
    scrape_basketball_matches,
    pick_basketball_bet_type
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

            # ---- 1) Bet on Football
            navigate_to_football_live(driver)
            football_matches = scrape_football_matches(driver)
            print(f"[FOOTBALL] Found {len(football_matches)} matches...")

            for (match_el, match_info) in football_matches:
                match_id = match_info["match_id"]
                if not match_id:
                    continue

                if match_id in bets_data["betted_matches"]:
                    continue

                outcome = pick_football_bet_type(match_info)
                if outcome is None:
                    continue

                bet_type, odd_val = outcome
                print(f"[FOOTBALL] Attempting bet: {bet_type}, odd={odd_val:.2f} "
                      f"on {match_info['team_home']} vs {match_info['team_away']}")

                if get_balance(driver) < 2.0:
                    print("Balance dropped below 2.0, skipping bet.")
                    continue

                stake_used, potential_win = place_bet(driver, match_el, bet_type)
                if stake_used == 0:
                    print("[FOOTBALL] Bet not placed. Possibly an error. Skipping.")
                    continue

                bets_data["betted_matches"].add(match_id)
                bets_data["bets_details"].append({
                    "sport": "football",
                    "match_id": match_id,
                    "teams": f"{match_info['team_home']} vs {match_info['team_away']}",
                    "stake": stake_used,
                    "potential_win": odd_val * stake_used,
                    "balance_after": get_balance(driver),
                })
                save_bets_data(bets_data)
            print("Done checking FOOTBALL. Sleep 20s...\n")
            time.sleep(23)

            # ---- 2) Bet on Hockey
            clear_basket(driver)
            if get_balance(driver) < 2.0:
                print("Balance < 2.0 after football, skipping hockey.")
                time.sleep(60)
                continue

            navigate_to_hockey_live(driver)
            hockey_matches = scrape_hockey_matches(driver)
            print(f"[HOCKEY] Found {len(hockey_matches)} matches...")

            for (match_el, match_info) in hockey_matches:
                match_id = match_info["match_id"]
                if not match_id:
                    continue

                if match_id in bets_data["betted_matches"]:
                    continue

                outcome = pick_hockey_bet_type(match_info)
                if outcome is None:
                    continue

                bet_type, odd_val = outcome
                print(f"[HOCKEY] Attempting bet: {bet_type}, odd={odd_val:.2f} "
                      f"on {match_info['team_home']} vs {match_info['team_away']}")

                if get_balance(driver) < 2.0:
                    print("Balance dropped below 2.0, skipping hockey bet.")
                    continue

                stake_used, potential_win = place_bet(driver, match_el, bet_type)
                if stake_used == 0:
                    print("[HOCKEY] Bet not placed. Possibly an error. Skipping.")
                    continue

                # Mark as bet
                bets_data["betted_matches"].add(match_id)
                bets_data["bets_details"].append({
                    "sport": "hockey",
                    "match_id": match_id,
                    "teams": f"{match_info['team_home']} vs {match_info['team_away']}",
                    "stake": stake_used,
                    "potential_win": odd_val * stake_used,
                    "balance_after": get_balance(driver),
                })
                save_bets_data(bets_data)
            print("Done checking HOCKEY. Sleep 20s...\n")
            time.sleep(26)
           
            # ---- 3) Bet on Volleyball
            clear_basket(driver)

            if get_balance(driver) < 2.0:
                print("Balance < 2.0, skipping basketball.")
                time.sleep(60)
                continue

            navigate_to_basketball_live(driver)
            basket_matches = scrape_basketball_matches(driver)
            print(f"[BASKETBALL] Found {len(basket_matches)} matches...")

            for (match_el, match_info) in basket_matches:
                match_id = match_info["match_id"]
                if not match_id:
                    continue
                if match_id in bets_data["betted_matches"]:
                    continue

                outcome = pick_basketball_bet_type(match_info)
                if outcome is None:
                    continue

                bet_type, odd_val = outcome
                print(f"[BASKETBALL] Attempting bet: {bet_type}, odd={odd_val:.2f} "
                    f"on {match_info['team_home']} vs {match_info['team_away']}")

                # final check balance
                if get_balance(driver) < 2.0:
                    print("Balance below 2.0, skipping basketball bet.")
                    continue

                stake_used, potential_win = place_bet(driver, match_el, bet_type)
                if stake_used == 0:
                    print("[BASKETBALL] Bet not placed. Possibly an error.")
                    continue

                bets_data["betted_matches"].add(match_id)
                bets_data["bets_details"].append({
                    "sport": "basketball",
                    "match_id": match_id,
                    "teams": f"{match_info['team_home']} vs {match_info['team_away']}",
                    "stake": stake_used,
                    "potential_win": odd_val * stake_used,
                    "balance_after": get_balance(driver),
                })

                save_bets_data(bets_data)
            print("Done checking BASKETBALL. Sleep 20s...\n")
            time.sleep(33)

    finally:
        driver.quit()

if __name__ == "__main__":
    main()
