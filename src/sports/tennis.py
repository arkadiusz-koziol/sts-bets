# sports/tennis.py

import time
import re
from selenium.webdriver.common.by import By
from selenium.common.exceptions import NoSuchElementException, StaleElementReferenceException

from sports.football import parse_odd_text  # Reuse parse_odd_text from football.py
from common.bet_logic import get_balance, save_bets_data

def navigate_to_tennis_live(driver):
    """
    Navigate to the tennis live page
    """
    driver.get("https://www.sts.pl/live/tenis")
    time.sleep(3)

def scrape_tennis_matches(driver):
    """
    Return a list of (match_el, match_info).
    match_info is a dict with:
      {
        "match_id": str or None,
        "player1": str,
        "player2": str,
        "time_str": str,  # e.g. "1 set", "2 set"
        "games_player1": int (current set games),
        "games_player2": int (current set games),
        "odd_1": float,
        "odd_2": float
      }
    We'll only pick matches in set #2, and ensure "3 or fewer games left."
    """
    matches_data = []

    all_match_containers = driver.find_elements(
        By.CSS_SELECTOR, "div.collapsable-container bb-live-match-tile"
    )

    for match_el in all_match_containers:
        try:
            # 1) Identify match_id
            anchor = match_el.find_element(By.CSS_SELECTOR, "a")
            data_cy = anchor.get_attribute("data-cy")
            href = anchor.get_attribute("href")
            if data_cy and "/" in data_cy:
                match_id = data_cy.split("/")[-1]
            elif href and "/" in href:
                match_id = href.split("/")[-1]
            else:
                match_id = None

            # 2) Players
            team_els = match_el.find_elements(
                By.CSS_SELECTOR, ".match-tile-scoreboard-team__name span"
            )
            if len(team_els) == 2:
                player1 = team_els[0].text.strip()
                player2 = team_els[1].text.strip()
            else:
                player1 = "Unknown"
                player2 = "Unknown"

            # 3) Time string => e.g. "1 set" or "2 set"
            time_el = match_el.find_elements(
                By.CSS_SELECTOR, ".live-match-tile-time-details__game-name"
            )
            time_str = " / ".join(e.text for e in time_el if e.text)

            # 4) Parse scoreboard partial => e.g. games
            #    We look for ".live-match-tile-scoreboard-score__partials"
            #    The FIRST partial row typically shows the current set games.
            #    e.g. 4 5 => means 4:5 in the second set so far
            partials = match_el.find_elements(
                By.CSS_SELECTOR,
                ".live-match-tile-scoreboard-score__partials div"
            )
            # partials might contain multiple lines: 1) set 1 / set 2 scores, 2) total sets, etc.
            # We'll assume the FIRST line we see is the current set if we are in set #2
            # or we do a more robust approach: parse last line if "2 set"...
            # For simplicity, let's just parse the first two integers if they exist:

            games_player1 = 0
            games_player2 = 0
            game_values = []
            for p in partials:
                txt = p.text.strip()
                if txt.isdigit():
                    game_values.append(int(txt))

            # typically game_values might be [6,4, 2,2] if there's 2 partial lines
            # We only want the CURRENT set row. It's site-specific. We'll assume the *first row*
            # is set #1, the second row is set #2. So if "2 set," we parse the second row, etc.

            # We'll do a small helper:
            set_number = parse_current_set_number(time_str)  # see below
            if set_number == 2:
                # we attempt to parse the second row
                # each "row" typically has 2 digits => we need to skip the first 2 digits from game_values
                if len(game_values) >= 4:
                    # row1 => [0,1], row2 => [2,3]
                    # so player1=game_values[2], player2=game_values[3]
                    # that means the partial array might be bigger if the match had multiple sets
                    games_player1 = game_values[2]
                    games_player2 = game_values[3]
                elif len(game_values) >= 2:
                    # fallback if there's only 2 partial digits => maybe it's set #2 right away
                    games_player1 = game_values[0]
                    games_player2 = game_values[1]
            else:
                # if not 2 set, we might still parse the first row, but in theory we skip anyway
                games_player1 = 0
                games_player2 = 0

            # 5) Odds => only 2 outcomes => "1" or "2"
            odds_buttons = match_el.find_elements(By.CSS_SELECTOR, "sds-odds-button")
            if len(odds_buttons) >= 2:
                odd_1_str = odds_buttons[0].find_element(
                    By.CSS_SELECTOR, "[data-testid='odds-value']"
                ).text
                odd_2_str = odds_buttons[1].find_element(
                    By.CSS_SELECTOR, "[data-testid='odds-value']"
                ).text
            else:
                odd_1_str = "0.00"
                odd_2_str = "0.00"

            odd_1 = parse_odd_text(odd_1_str)
            odd_2 = parse_odd_text(odd_2_str)

            match_info = {
                "match_id": match_id,
                "player1": player1,
                "player2": player2,
                "time_str": time_str,
                "games_player1": games_player1,
                "games_player2": games_player2,
                "odd_1": odd_1,
                "odd_2": odd_2
            }

            matches_data.append((match_el, match_info))

        except StaleElementReferenceException:
            print("[TENNIS] Stale element, skipping.")
            continue
        except Exception as e:
            print(f"[TENNIS] Error parsing match: {e}")

    return matches_data

def parse_current_set_number(time_str):
    """
    If time_str e.g. "1 set", returns 1
    if "2 set", returns 2
    else 0
    """
    match = re.search(r"(\d+)\s*set", time_str.lower())
    if match:
        return int(match.group(1))
    return 0

def is_set_almost_finished(g1, g2):
    """
    Return True if "there are only 3 or fewer games left in this set."
    Typically a set finishes at 6 games (unless tie-break with 7, but let's keep it simple).
    So if max(g1,g2) >= 6 => set might be done or tie-break. We skip.
    If the leading side is at 5 => maybe 1 game left. If leading side is 4 => 2 games left, etc.

    We'll assume a 'normal' set to 6. So leftover = 6 - max(g1,g2).
    If leftover <= 3 => True
    Also ensure the set isn't over => if max(g1,g2) >= 6 => skip (the set might be done or a tie-break).
    """
    big = max(g1, g2)
    if big >= 6:
        return False  # set is probably done or in tie-break
    leftover = 6 - big
    return (leftover <= 3)

def pick_tennis_bet_type(match_info):
    """
    1) Must be "2 set"
    2) Must be is_set_almost_finished(g1, g2) => True
    3) Among odd_1, odd_2 in [1.15, 2.0], pick the *lowest*
    """
    set_number = parse_current_set_number(match_info["time_str"])
    if set_number != 2:
        return None

    g1 = match_info["games_player1"]
    g2 = match_info["games_player2"]
    if not is_set_almost_finished(g1, g2):
        return None

    candidates = []
    if 1.15 <= match_info["odd_1"] <= 2.0:
        candidates.append(("player1", match_info["odd_1"]))
    if 1.15 <= match_info["odd_2"] <= 2.0:
        candidates.append(("player2", match_info["odd_2"]))

    if not candidates:
        return None

    # pick the outcome with the *lowest* odd
    best_outcome, best_odd = min(candidates, key=lambda x: x[1])
    return best_outcome, best_odd

def place_tennis_bet(driver, match_el, match_info, bets_data):
    """
    Place the bet if conditions are met => immediate save to .json
    2 outcomes => label "1" or "2"
    """
    bet_data = pick_tennis_bet_type(match_info)
    if not bet_data:
        return (0, 0)

    outcome, odd_val = bet_data
    label_map = {"player1": "1", "player2": "2"}
    label_to_find = label_map.get(outcome, None)
    if not label_to_find:
        print("[TENNIS] Unknown outcome => skip.")
        return (0, 0)

    # Check balance inside the function => user wants per-bet check
    balance_now = get_balance(driver)
    if balance_now < 2.0:
        print(f"[TENNIS] balance={balance_now:.2f} <2 => skip match={match_info['match_id']}")
        return (0, 0)

    print(f"[TENNIS] Attempting bet: {outcome}, odd={odd_val:.2f} on {match_info['player1']} vs {match_info['player2']}")
    stake_used = 2.0
    potential_win = 0.0

    # 1) click the correct odds => "sds-odds-button" with label map
    try:
        odds_buttons = match_el.find_elements(By.CSS_SELECTOR, "sds-odds-button")
        for btn in odds_buttons:
            try:
                label_el = btn.find_element(By.CSS_SELECTOR, ".odds-button__label")
                if label_el.text.strip().lower() == label_to_find.lower():
                    btn.click()
                    print(f"[TENNIS] Clicked odds '{label_el.text.strip()}' in tile.")
                    time.sleep(2)
                    break
            except NoSuchElementException:
                pass
    except Exception as e:
        print(f"[TENNIS] Error selecting bet: {e}")
        return (0, 0)

    # 2) input stake=2
    try:
        stake_input = driver.find_element(By.CSS_SELECTOR, "sts-shared-input[data-cy='ticket-stake'] input#AMOUNT")
        stake_input.clear()
        stake_input.send_keys(str(stake_used))
        print("[TENNIS] Stake set to 2.0")
        time.sleep(2)
    except NoSuchElementException:
        print("[TENNIS] stake input not found => fail.")
        return (0, 0)

    # 3) parse potential
    try:
        place_btn = driver.find_element(By.CSS_SELECTOR, "button[data-testid='button-place-a-bet']")
        potential_el = place_btn.find_element(By.CSS_SELECTOR, ".submit-button__content")
        raw_text = potential_el.text.strip()  # e.g. "2,28 zł"
        cleaned = raw_text.replace(",", ".").replace("zł", "").replace("\xa0", "").strip()
        potential_win = float(cleaned)
        print(f"[TENNIS] Potential win: {potential_win:.2f}")
    except Exception:
        print("[TENNIS] Could not parse potential => 0.0")

    # 4) confirm bet (2-click if needed)
    try:
        # first click
        place_btn.click()
        time.sleep(2)

        # second click attempt
        place_btn_2 = driver.find_element(By.CSS_SELECTOR, "button[data-testid='button-place-a-bet']")
        place_btn_2.click()
        print("Bet placed!")
        time.sleep(3)

    except StaleElementReferenceException:
        print("Element became stale; possibly only one click is needed or site updated.")
        print("Proceeding with no second click.")

    except NoSuchElementException:
        print("No second place button found => continuing anyway.")


    # 5) immediately save
    if stake_used > 0:
        bets_data["betted_matches"].add(match_info["match_id"])
        bets_data["bets_details"].append({
            "sport": "tennis",
            "match_id": match_info["match_id"],
            "players": f"{match_info['player1']} vs {match_info['player2']}",
            "stake": stake_used,
            # or user might do odd_val * stake => but we do potential_win from slip
            "potential_win": potential_win,
            "balance_after": get_balance(driver),
        })
        save_bets_data(bets_data)

    return (stake_used, potential_win)
