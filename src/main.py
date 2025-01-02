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

from sports.football import (
    navigate_to_football_live,
    scrape_football_matches,
    place_bet as place_football_bet
)
from sports.hockey import (
    navigate_to_hockey_live,
    scrape_hockey_matches,
    place_hockey_bet
)
from sports.basketball import (
    navigate_to_basketball_live,
    scrape_basketball_matches,
    place_basketball_bet
)
from sports.tennis import (
    navigate_to_tennis_live,
    scrape_tennis_matches,
    place_tennis_bet
)
from sports.inspiration import bet_inspiration_coupons

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
        # 1) Log in
        login_sts(driver, username, password)
        input("If a captcha appeared, solve it manually. Press Enter when finished...")
        print("Logged in successfully.")

        # 2) Load bet data (match_ids, coupon_ids, etc.)
        bets_data = load_bets_data()
        print(f"Loaded data: {len(bets_data['betted_matches'])} matches already bet, "
              f"{len(bets_data['betted_coupons'])} coupons already bet.")

        while True:
            # ==========  FOOTBALL  ==========
            clear_basket(driver)
            balance = get_balance(driver)
            print(f"Current balance: {balance:.2f} zł")
            if balance < 2.0:
                print("Balance < 2.0, skipping bets.")
                time.sleep(60)
                continue

            # Bet on Football
            navigate_to_football_live(driver)
            football_matches = scrape_football_matches(driver)
            print(f"[FOOTBALL] Found {len(football_matches)} matches...")

            for (match_el, match_info) in football_matches:
                match_id = match_info["match_id"]
                if not match_id:
                    continue
                if match_id in bets_data["betted_matches"]:
                    continue

                print(f"[FOOTBALL] Checking match_id={match_id}, {match_info['team_home']} vs {match_info['team_away']}")
                stake_used, potential_win = place_football_bet(driver, match_el, match_info, bets_data)
                # If stake_used==0 => no bet or fail, we skip
                if stake_used > 0:
                    print(f"[FOOTBALL] bet placed => stake={stake_used}, potential={potential_win:.2f}\n")

            print("Done checking FOOTBALL. Sleep 20s...\n")
            time.sleep(20)

            # ==========  HOCKEY  ==========
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

                print(f"[HOCKEY] Checking match_id={match_id}, {match_info['team_home']} vs {match_info['team_away']}")
                stake_used, potential_win = place_hockey_bet(driver, match_el, match_info, bets_data)
                if stake_used > 0:
                    print(f"[HOCKEY] bet placed => stake={stake_used}, potential={potential_win:.2f}\n")

            print("Done checking HOCKEY. Sleep 20s...\n")
            time.sleep(20)

            # ==========  BASKETBALL  ==========
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

                print(f"[BASKETBALL] Checking match_id={match_id}, {match_info['team_home']} vs {match_info['team_away']}")
                stake_used, potential_win = place_basketball_bet(driver, match_el, match_info, bets_data)
                if stake_used > 0:
                    print(f"[BASKETBALL] bet placed => stake={stake_used}, potential={potential_win:.2f}\n")

            print("Done checking BASKETBALL. Sleep 20s...\n")
            time.sleep(20)
            
            # ==========  TENNIS  ==========
            clear_basket(driver)
            if get_balance(driver) < 2.0:
                print("Balance < 2.0, skipping tennis.")
                time.sleep(20)
                continue

            navigate_to_tennis_live(driver)
            tennis_matches = scrape_tennis_matches(driver)
            print(f"[TENNIS] Found {len(tennis_matches)} matches...")

            for (match_el, match_info) in tennis_matches:
                mid = match_info["match_id"]
                if not mid:
                    continue
                if mid in bets_data["betted_matches"]:
                    continue

                stake_used, potential_win = place_tennis_bet(driver, match_el, match_info, bets_data)
                if stake_used > 0:
                    print(f"[TENNIS] Bet placed for match_id={mid}, potential={potential_win:.2f}...\n")

            print("Done checking TENNIS. Sleep 20s...\n")
            time.sleep(20)

            # # ==========  INSPIRATION  ==========
            # # One bet per copied coupon from high-success users
            # clear_basket(driver)
            # bets_data = bet_inspiration_coupons(driver, bets_data)
            # print("Done checking Inspiration coupons. Sleeping 60s...\n")
            # time.sleep(60)

    finally:
        driver.quit()

if __name__ == "__main__":
    main()
