import time
import re
from selenium.webdriver.common.by import By
from selenium.common.exceptions import NoSuchElementException, StaleElementReferenceException

# Needed so we can save each bet immediately
from common.bet_logic import get_balance, save_bets_data

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

def scrape_football_matches(driver):
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
                odd_home_str = odds_buttons[0].find_element(By.CSS_SELECTOR, "[data-testid='odds-value']").text
                odd_draw_str = odds_buttons[1].find_element(By.CSS_SELECTOR, "[data-testid='odds-value']").text
                odd_away_str = odds_buttons[2].find_element(By.CSS_SELECTOR, "[data-testid='odds-value']").text
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

        except StaleElementReferenceException:
            print("[FOOTBALL] Stale element, skipping.")
            continue
        except Exception as e:
            print(f"[FOOTBALL] Error parsing match: {e}")

    return matches_data

def pick_football_bet_type(match_info):
    # Only bet if minute >=79
    if match_info["time_min"] < 79:
        return None

    candidates = [
        ("home", match_info["odd_home"]),
        ("draw", match_info["odd_draw"]),
        ("away", match_info["odd_away"])
    ]

    valid = [(outcome, val) for (outcome, val) in candidates if 1.20 <= val <= 2.0]
    if not valid:
        return None

    best_outcome, best_odd = min(valid, key=lambda x: x[1])
    return best_outcome, best_odd

def place_bet(driver, match_el, match_info, bets_data):
    """
    Places a bet on this football match, saves to .json immediately if successful.
    Returns (stake_used, potential_win).
    """
    bet_type = pick_football_bet_type(match_info)
    if not bet_type:
        return (0, 0)  # no valid bet

    outcome, odd_val = bet_type
    label_map = {"home": "1", "draw": "x", "away": "2"}
    label_to_find = label_map.get(outcome)
    if not label_to_find:
        print(f"Unknown bet_type={outcome}. Aborting.")
        return (0, 0)

    # 1) Click the correct odds
    try:
        odds_buttons = match_el.find_elements(By.CSS_SELECTOR, "sds-odds-button")
        for btn in odds_buttons:
            try:
                label_el = btn.find_element(By.CSS_SELECTOR, ".odds-button__label")
                if label_el.text.strip().lower() == label_to_find.lower():
                    btn.click()
                    print(f"[FOOTBALL] Clicked odds '{label_el.text.strip()}' in tile.")
                    time.sleep(2)
                    break
            except NoSuchElementException:
                pass
    except Exception as e:
        print(f"[FOOTBALL place_bet] Error selecting bet {outcome}: {e}")
        return (0, 0)

    stake_used = 2.0
    potential_win = 0.0

    # 2) Input stake
    try:
        stake_input = driver.find_element(By.CSS_SELECTOR, "sts-shared-input[data-cy='ticket-stake'] input#AMOUNT")
        stake_input.clear()
        stake_input.send_keys(str(stake_used))
        print(f"[FOOTBALL] Stake set to {stake_used:.2f}")
        time.sleep(2)
    except NoSuchElementException:
        print("[FOOTBALL] Stake input not found!")
        return (0, 0)

    # 3) Parse potential
    try:
        place_bet_button = driver.find_element(By.CSS_SELECTOR, "button[data-testid='button-place-a-bet']")
        potential_el = place_bet_button.find_element(By.CSS_SELECTOR, ".submit-button__content")
        raw_text = potential_el.text.strip()  # e.g. "2,28 zł"
        cleaned = raw_text.replace(",", ".").replace("zł", "").replace("\xa0", "").strip()
        potential_win = float(cleaned)
        print(f"[FOOTBALL] Potential win: {potential_win:.2f} zł")
    except Exception:
        print("[FOOTBALL] Could not parse potential win from the button => 0.0")

    # 4) Confirm bet (some sites require 2 clicks, if so:
    try:
        place_bet_button.click()
        time.sleep(2)
        # Attempt second click if needed:
        place_bet_button = driver.find_element(By.CSS_SELECTOR, "button[data-testid='button-place-a-bet']")
        place_bet_button.click()
        print("[FOOTBALL] Bet placed!")
        time.sleep(3)
    except NoSuchElementException:
        print("[FOOTBALL] Could not find final bet button (second click).")

    # 5) Save bet if stake_used > 0
    if stake_used > 0:
        # Mark as bet in your bets_data
        bets_data["betted_matches"].add(match_info["match_id"])
        bets_data["bets_details"].append({
            "sport": "football",
            "match_id": match_info["match_id"],
            "teams": f"{match_info['team_home']} vs {match_info['team_away']}",
            "stake": stake_used,
            # We can store odd_val * stake or the parsed potential_win
            "potential_win": potential_win,
            "balance_after": get_balance(driver),
        })
        save_bets_data(bets_data)

    return (stake_used, potential_win)
