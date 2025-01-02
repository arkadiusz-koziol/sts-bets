import time
import re
from selenium.webdriver.common.by import By
from selenium.common.exceptions import NoSuchElementException, StaleElementReferenceException

from sports.football import parse_odd_text  # reuse parse_odd_text
from common.bet_logic import get_balance, save_bets_data

def navigate_to_hockey_live(driver):
    driver.get("https://www.sts.pl/live/hokej-na-lodzie")
    time.sleep(3)

def parse_hockey_time(time_str):
    tercja = 0
    match_tercja = re.search(r"(\d+) tercja", time_str.lower())
    if match_tercja:
        tercja = int(match_tercja.group(1))

    minute = 0
    match_min = re.search(r"(\d+)'", time_str)
    if match_min:
        minute = int(match_min.group(1))

    return tercja, minute

def scrape_hockey_matches(driver):
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

            team_elements = match_el.find_elements(By.CSS_SELECTOR, ".match-tile-scoreboard-team__name span")
            if len(team_elements) == 2:
                team_home = team_elements[0].text.strip()
                team_away = team_elements[1].text.strip()
            else:
                team_home = "Unknown"
                team_away = "Unknown"

            time_elements = match_el.find_elements(By.CSS_SELECTOR, ".live-match-tile-time-details__game-name")
            match_time_str = " / ".join(e.text for e in time_elements if e.text)

            tercja, minute_in_tercja = parse_hockey_time(match_time_str)

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
                "tercja": tercja,
                "minute_in_tercja": minute_in_tercja,
                "odd_home": odd_home,
                "odd_draw": odd_draw,
                "odd_away": odd_away
            }

            matches_data.append((match_el, match_info))

        except StaleElementReferenceException:
            print("[HOCKEY] Stale element, skipping.")
            continue
        except Exception as e:
            print(f"[HOCKEY] Error parsing match: {e}")

    return matches_data

def pick_hockey_bet_type(match_info):
    if match_info["tercja"] != 3:
        return None
    if match_info["minute_in_tercja"] < 10:
        return None

    print(f"[HOCKEY] Checking match_id={match_info['match_id']} => tercja={match_info['tercja']}, "
          f"minute_in_tercja={match_info['minute_in_tercja']}, raw='{match_info['time_str']}'")

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

def place_hockey_bet(driver, match_el, match_info, bets_data):
    """
    Place a hockey bet immediately, then save to .json if successful.
    """
    bet_data = pick_hockey_bet_type(match_info)
    if not bet_data:
        return (0, 0)

    outcome, odd_val = bet_data
    label_map = {"home": "1", "draw": "x", "away": "2"}
    label_to_find = label_map.get(outcome, None)
    if not label_to_find:
        print(f"[HOCKEY] Unknown bet type: {outcome}")
        return (0, 0)

    # 1) click the correct odds button
    try:
        odds_buttons = match_el.find_elements(By.CSS_SELECTOR, "sds-odds-button")
        for btn in odds_buttons:
            try:
                label_el = btn.find_element(By.CSS_SELECTOR, ".odds-button__label")
                if label_el.text.strip().lower() == label_to_find.lower():
                    btn.click()
                    print(f"[HOCKEY] Clicked odds '{label_el.text.strip()}' in tile.")
                    time.sleep(2)
                    break
            except NoSuchElementException:
                pass
    except Exception as e:
        print(f"[HOCKEY place_bet] Error selecting bet: {e}")
        return (0, 0)

    stake_used = 2.0
    potential_win = 0.0

    # 2) set stake
    try:
        stake_input = driver.find_element(By.CSS_SELECTOR, "sts-shared-input[data-cy='ticket-stake'] input#AMOUNT")
        stake_input.clear()
        stake_input.send_keys(str(stake_used))
        print(f"[HOCKEY] Stake set to {stake_used:.2f}")
        time.sleep(2)
    except NoSuchElementException:
        print("[HOCKEY] stake input not found => fail.")
        return (0, 0)

    # 3) parse potential
    try:
        place_bet_button = driver.find_element(By.CSS_SELECTOR, "button[data-testid='button-place-a-bet']")
        potential_el = place_bet_button.find_element(By.CSS_SELECTOR, ".submit-button__content")
        raw_text = potential_el.text.strip()
        cleaned = raw_text.replace(",", ".").replace("zł", "").replace("\xa0", "").strip()
        potential_win = float(cleaned)
        print(f"[HOCKEY] Potential win: {potential_win:.2f}")
    except Exception:
        print("[HOCKEY] Could not parse potential => 0.0")

    # 4) confirm bet (some sites need two clicks)
    try:
        place_bet_button.click()
        time.sleep(2)
        place_bet_button = driver.find_element(By.CSS_SELECTOR, "button[data-testid='button-place-a-bet']")
        place_bet_button.click()
        print("[HOCKEY] Bet placed!")
        time.sleep(3)
    except NoSuchElementException:
        print("[HOCKEY] final bet button not found => partial fail.")

    # 5) Immediately save
    if stake_used > 0:
        bets_data["betted_matches"].add(match_info["match_id"])
        bets_data["bets_details"].append({
            "sport": "hockey",
            "match_id": match_info["match_id"],
            "teams": f"{match_info['team_home']} vs {match_info['team_away']}",
            "stake": stake_used,
            "potential_win": potential_win,
            "balance_after": get_balance(driver),
        })
        save_bets_data(bets_data)

    return (stake_used, potential_win)
