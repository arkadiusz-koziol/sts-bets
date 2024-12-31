import time
import re
from selenium.webdriver.common.by import By
from selenium.common.exceptions import NoSuchElementException, StaleElementReferenceException
from sports.football import parse_odd_text, place_bet

def navigate_to_basketball_live(driver):
    driver.get("https://www.sts.pl/live/koszykowka")
    time.sleep(3)

def parse_basketball_time(time_str):
    total_game_minutes = 40

    quarter_match = re.search(r"(\d+)\s*kwarta", time_str.lower())
    half_match = re.search(r"(\d+)\s*po[łl]owa", time_str.lower())
    minute_match = re.search(r"(\d+)'", time_str)

    current_period = 0
    used_in_period = 0

    if quarter_match:
        current_period = int(quarter_match.group(1))
    elif half_match:
        current_period = int(half_match.group(1))

    if minute_match:
        used_in_period = int(minute_match.group(1))
    quarter_length = 10
    half_length = 20

    total_elapsed = 0
    if quarter_match:
        total_elapsed = (current_period - 1) * quarter_length + used_in_period
    elif half_match:
        total_elapsed = (current_period - 1) * half_length + used_in_period
    
    return total_game_minutes, total_elapsed

def scrape_basketball_matches(driver):
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

            total_game_minutes, total_elapsed = parse_basketball_time(match_time_str)

            odds_buttons = match_el.find_elements(By.CSS_SELECTOR, "sds-odds-button")
            if len(odds_buttons) >= 2:
                odd_1_str = odds_buttons[0].find_element(
                    By.CSS_SELECTOR, "[data-testid='odds-value']").text
                odd_2_str = odds_buttons[1].find_element(
                    By.CSS_SELECTOR, "[data-testid='odds-value']").text
            else:
                odd_1_str = "0.00"
                odd_2_str = "0.00"

            odd_1 = parse_odd_text(odd_1_str)
            odd_2 = parse_odd_text(odd_2_str)

            match_info = {
                "match_id": match_id,
                "team_home": team_home,
                "team_away": team_away,
                "time_str": match_time_str,
                "total_game_minutes": total_game_minutes,
                "total_elapsed": total_elapsed,
                "odd_1": odd_1,
                "odd_2": odd_2,
            }

            matches_data.append((match_el, match_info))

        except StaleElementReferenceException:
            print("[BASKETBALL] Stale element, skipping.")
            continue
        except Exception as e:
            print(f"[BASKETBALL] Error parsing match: {e}")

    return matches_data

def pick_basketball_bet_type(match_info):
    total_game = match_info["total_game_minutes"]
    elapsed = match_info["total_elapsed"]
    threshold_elapsed = 0.9 * total_game

    if elapsed < threshold_elapsed:
        return None

    odd_1 = match_info["odd_1"]
    odd_2 = match_info["odd_2"]

    the_min = min(odd_1, odd_2)
    the_max = max(odd_1, odd_2)

    if the_min < 1.15:
        return None
    if the_max > 2.0:
        return None

    ratio = the_max / the_min
    if ratio < 1.25:
        return None

    if odd_1 == the_min:
        return ("home", odd_1)
    else:
        return ("away", odd_2)
