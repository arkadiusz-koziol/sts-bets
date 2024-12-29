import time
import re
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

def parse_match_minute(time_str):
    match = re.search(r"(\d+)'", time_str)
    if match:
        return int(match.group(1))
    return 0

def scrape_matches(driver):

    matches_data = []

    all_match_containers = driver.find_elements(
        By.CSS_SELECTOR, "div.collapsable-container bb-live-match-tile"
    )

    for match_el in all_match_containers:
        try:
            anchor = match_el.find_element(By.CSS_SELECTOR, "a")
            data_cy = anchor.get_attribute("data-cy")
            href = anchor.get_attribute("href")

            if data_cy and "/" in data_cy:
                match_id = data_cy.split("/")[-1]
            elif href and "/" in href:
                match_id = href.split("/")[-1]
            else:
                match_id = None

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

            time_min = parse_match_minute(match_time_str)

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
                "match_id": match_id,
                "team_home": team_home,
                "team_away": team_away,
                "time_str": match_time_str,
                "time_min": time_min,
                "odd_home": odd_home,
                "odd_draw": odd_draw,
                "odd_away": odd_away
            }

            matches_data.append((match_el, match_info))

        except Exception as e:
            print(f"Error parsing match element: {e}")

    return matches_data

def pick_bet_type(match_info):
    if match_info["time_min"] < 79:
        return None

    candidates = [
        ("home", match_info["odd_home"]),
        ("draw", match_info["odd_draw"]),
        ("away", match_info["odd_away"])
    ]

    valid = [(outcome, oddval) for (outcome, oddval) in candidates 
             if 1.15 <= oddval <= 2.0]

    if not valid:
        return None

    best_outcome, best_odd = min(valid, key=lambda x: x[1])
    return best_outcome, best_odd

def place_bet(driver, match_el, bet_type):
    label_map = {
        "home": "1",
        "draw": "x",
        "away": "2"
    }
    label_to_find = label_map.get(bet_type)
    if not label_to_find:
        print(f"Unknown bet_type={bet_type}. Aborting.")
        return

    try:
        odds_buttons = match_el.find_elements(By.CSS_SELECTOR, "sds-odds-button")
        for btn in odds_buttons:
            try:
                label_el = btn.find_element(By.CSS_SELECTOR, ".odds-button__label")
                if label_el.text.strip().lower() == label_to_find.lower():
                    btn.click()
                    print(f"Clicked odds button '{label_el.text.strip()}' in this match tile.")
                    time.sleep(2)
                    break
            except NoSuchElementException:
                pass
    except Exception as e:
        print(f"Error selecting bet {bet_type} in match tile: {e}")
        return

    try:
        toggle_checkbox = driver.find_element(By.CSS_SELECTOR, "bb-ticket-toleration input#toleration")
        if not toggle_checkbox.is_selected():
            label_el = driver.find_element(By.CSS_SELECTOR, "bb-ticket-toleration .toggle-label")
            label_el.click()
            print("Toggled 'Akceptuję zmiany kursów'")
            time.sleep(2)
    except NoSuchElementException:
        print("Could not find 'Akceptuję zmiany kursów' toggle.")

    try:
        stake_input = driver.find_element(By.CSS_SELECTOR, "sts-shared-input[data-cy='ticket-stake'] input#AMOUNT")
        stake_input.clear()
        stake_input.send_keys("2.00")
        print("Stake set to 2.00")
        time.sleep(2)
    except NoSuchElementException:
        print("Stake input not found!")

    try:
        bet_button = driver.find_element(By.CSS_SELECTOR, "button[data-testid='button-place-a-bet']")
        bet_button.click()
        time.sleep(2)
        bet_button = driver.find_element(By.CSS_SELECTOR, "button[data-testid='button-place-a-bet']")
        bet_button.click()
        print("Bet placed!")
        time.sleep(4)
    except NoSuchElementException:
        print("Could not find final bet button.")
