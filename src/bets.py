import os
import time
import openai
from selenium.webdriver.common.by import By
from selenium.common.exceptions import NoSuchElementException

def navigate_to_football_live(driver):
    driver.get("https://www.sts.pl/live/pilka-nozna")
    time.sleep(3)

def parse_odd_text(odd_str):
    odd_str = odd_str.strip()
    if odd_str in ["-", ""]:
        return 0.0
    odd_str = odd_str.replace(",", ".")
    try:
        return float(odd_str)
    except ValueError:
        return 0.0

def scrape_matches(driver):
    matches_data = []
    all_match_containers = driver.find_elements(
        By.CSS_SELECTOR, "div.collapsable-container bb-live-match-tile"
    )

    for match_el in all_match_containers:
        try:
            team_elements = match_el.find_elements(
                By.CSS_SELECTOR, ".match-tile-scoreboard-team__name span"
            )
            if len(team_elements) == 2:
                team_home = team_elements[0].text.strip()
                team_away = team_elements[1].text.strip()
            else:
                team_home = "Unknown"
                team_away = "Unknown"

            time_elements = match_el.find_elements(
                By.CSS_SELECTOR, ".live-match-tile-time-details__game-name"
            )
            match_time_str = " / ".join(e.text for e in time_elements if e.text)

            score_elements = match_el.find_elements(
                By.CSS_SELECTOR, ".live-match-tile-scoreboard-score__partials div"
            )
            score_parts = [s.text.strip() for s in score_elements if s.text.strip()]

            odds_buttons = match_el.find_elements(By.CSS_SELECTOR, "sds-odds-button")

            if len(odds_buttons) >= 3:
                odd_home_str = odds_buttons[0].find_element(
                    By.CSS_SELECTOR, "[data-testid='odds-value']").text
                odd_draw_str = odds_buttons[1].find_element(
                    By.CSS_SELECTOR, "[data-testid='odds-value']").text
                odd_away_str = odds_buttons[2].find_element(
                    By.CSS_SELECTOR, "[data-testid='odds-value']").text
            else:
                odd_home_str = "0.00"
                odd_draw_str = "0.00"
                odd_away_str = "0.00"

            odd_home = parse_odd_text(odd_home_str)
            odd_draw = parse_odd_text(odd_draw_str)
            odd_away = parse_odd_text(odd_away_str)

            match_info = {
                "team_home": team_home,
                "team_away": team_away,
                "time_str": match_time_str,
                "score_parts": score_parts,
                "odd_home": odd_home,
                "odd_draw": odd_draw,
                "odd_away": odd_away
            }
            matches_data.append(match_info)

        except Exception as e:
            print(f"Error parsing match element: {e}")

    return matches_data

def call_chatgpt_for_bet(match_info):
    system_prompt = (
        "You are a helpful assistant that recommends a betting outcome "
        "for a football match. You analyse data and let me know probability of best income. Respond with just one word: "
        "'home', 'draw', or 'away'."
    )
    user_prompt = (
        f"Match: {match_info['team_home']} vs {match_info['team_away']}\n"
        f"Time: {match_info['time_str']}\n"
        f"Odds:\n"
        f"  Home = {match_info['odd_home']}\n"
        f"  Draw = {match_info['odd_draw']}\n"
        f"  Away = {match_info['odd_away']}\n"
        "Which outcome do you recommend to bet on, in one word?"
    )

    try:
        response = openai.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.0,
            max_tokens=1
        )

        ai_reply = response.choices[0].message.content.strip().lower()

        if "home" in ai_reply:
            return "home"
        elif "draw" in ai_reply or "tie" in ai_reply:
            return "draw"
        elif "away" in ai_reply:
            return "away"
        else:
            return None

    except Exception as e:
        print(f"Error calling ChatGPT API: {e}")
        return None

def analyze_match_data(match_info):
    recommended_outcome = call_chatgpt_for_bet(match_info)
    if not recommended_outcome:
        return None

    outcome_odd = 0.0
    if recommended_outcome == "home":
        outcome_odd = match_info["odd_home"]
    elif recommended_outcome == "draw":
        outcome_odd = match_info["odd_draw"]
    elif recommended_outcome == "away":
        outcome_odd = match_info["odd_away"]
    else:
        return None

    return {
        "bet_type": recommended_outcome,
        "odd_value": outcome_odd
    }

def place_bet(driver, bet_type):
    label_map = {
        "home": "1",
        "draw": "x",
        "away": "2"
    }
    label_to_find = label_map.get(bet_type, None)
    if not label_to_find:
        print(f"Unknown bet_type={bet_type}. Aborting.")
        return

    try:
        odds_buttons = driver.find_elements(By.CSS_SELECTOR, "sds-odds-button")

        for btn in odds_buttons:
            try:
                label_el = btn.find_element(By.CSS_SELECTOR, ".odds-button__label")
                if label_el.text.strip().lower() == label_to_find.lower():
                    btn.click()
                    print(f"Clicked odds button '{label_el.text.strip()}'")
                    time.sleep(1)
                    break
            except NoSuchElementException:
                pass
    except Exception as e:
        print(f"Error selecting bet {bet_type}: {e}")
        return

    try:
        toggle_checkbox = driver.find_element(By.CSS_SELECTOR, "bb-ticket-toleration input#toleration")
        if not toggle_checkbox.is_selected():
            label_el = driver.find_element(By.CSS_SELECTOR, "bb-ticket-toleration .toggle-label")
            label_el.click()
            print("Toggled 'Akceptuję zmiany kursów'")
            time.sleep(1)
    except NoSuchElementException:
        print("Could not find 'Akceptuję zmiany kursów' toggle. Possibly not needed in your session.")

    try:
        stake_input = driver.find_element(By.CSS_SELECTOR, "sts-shared-input[data-cy='ticket-stake'] input#AMOUNT")
        stake_input.clear()
        stake_input.send_keys("2.00")
        print("Stake set to 2.00")
        time.sleep(1)
    except NoSuchElementException:
        print("Stake input not found!")

    try:
        bet_button = driver.find_element(By.CSS_SELECTOR, "button[data-testid='button-place-a-bet']")
        bet_button.click()
        print("Bet placed!")
        time.sleep(2)
    except NoSuchElementException:
        print("Could not find the final bet button. Maybe the slip changed or an error occurred.")
