import os
import time
import openai
from dotenv import load_dotenv
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager

from bets import (
    navigate_to_football_live,
    scrape_matches,
    analyze_match_data,
    place_bet
)
from auth import login_sts

def main():
    load_dotenv()

    username = os.getenv("STS_USERNAME")
    password = os.getenv("STS_PASSWORD")
    ai_key = os.getenv("AI_KEY_SECRET")

    if not username or not password:
        print("Missing STS_USERNAME or STS_PASSWORD in .env!")
        return

    if not ai_key:
        print("Missing AI_KEY_SECRET in .env!")
        return

    openai.api_key = ai_key

    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service)

    try:
        login_sts(driver, username, password)
        input("If a captcha appeared, solve it manually. Press Enter when finished...")

        print("Logged in successfully. Starting further actions...")

        navigate_to_football_live(driver)

        matches = scrape_matches(driver)
        print(f"Found {len(matches)} matches...")

        for match_data in matches:
            analysis = analyze_match_data(match_data)
            if not analysis:
                continue

            bet_type = analysis["bet_type"]
            odd_val = analysis["odd_value"]

            if odd_val < 1.15:
                print(f"AI recommended {bet_type}, but odd {odd_val} < 1.15. Skipping.")
                continue

            print(f"Betting on {bet_type} with odd {odd_val} for match: "
                  f"{match_data['team_home']} vs {match_data['team_away']}")
            place_bet(driver, bet_type)

            break 
        # TODO: Implement a loop to bet on multiple matches
        # TODO: Implement a way, to check if the bet is not been betted previously

        input("Press Enter to quit...")

    finally:
        driver.quit()

if __name__ == "__main__":
    main()
