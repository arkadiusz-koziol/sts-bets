# sports/inspiration.py

import time
import re
from selenium.webdriver.common.by import By
from selenium.common.exceptions import NoSuchElementException, StaleElementReferenceException, TimeoutException
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from common.bet_logic import get_balance, save_bets_data

def go_to_inspiration_page(driver):
    driver.get("https://www.sts.pl/strefa-inspiracji/polecamy")
    time.sleep(3)

def find_inspiration_users(driver):
    """
    Return user boxes from .coupons-zone__profiles-info
    """
    try:
        container = driver.find_element(By.CSS_SELECTOR, "div.coupons-zone__profiles-info")
        user_boxes = container.find_elements(By.CSS_SELECTOR, "sts-coupons-zone-profile-info")
        return user_boxes
    except NoSuchElementException:
        print("[INSP] No .coupons-zone__profiles-info container found.")
        return []

def get_user_success_rate(user_box):
    try:
        rate_el = user_box.find_element(
            By.CSS_SELECTOR,
            ".coupons-zone__profile-info-item-details-stats-badge-content-value"
        )
        raw_text = rate_el.text.strip()
        print(f"[INSP DEBUG] user box raw rate => '{raw_text}'")
        return float(raw_text.replace("%", "").replace("\xa0","").strip())
    except Exception as e:
        print(f"[INSP] Could not parse success for user => {e}")
        return 0.0

def get_coupon_id(driver, timeout=10):
    """
    Wait up to `timeout` s for p.coupon-details__body-info-item-value.copied-info
    Return its text or None
    """
    try:
        wait = WebDriverWait(driver, timeout)
        el = wait.until(
            EC.presence_of_element_located(
                (By.CSS_SELECTOR, "p.coupon-details__body-info-item-value.copied-info")
            )
        )
        coupon_str = el.text.strip()
        print(f"[INSP] Found coupon_id={coupon_str}")
        return coupon_str
    except (TimeoutException, NoSuchElementException) as e:
        print(f"[INSP] Could not find coupon ID => {e}")
        return None

def copy_coupon(driver):
    """
    Click the copy icon => <sts-shared-icon-button iconname="icon-copy"...>
    Return True if success
    """
    time.sleep(2)
    try:
        copy_button = driver.find_element(
            By.CSS_SELECTOR,
            "sts-shared-icon-button[iconname='icon-copy'] div.icon-button__icon i.icon.icon-copy"
        )
        copy_button.click()
        print("[INSP] Copied coupon to basket.")
        time.sleep(2)
        return True
    except NoSuchElementException:
        return False

def place_inspiration_bet(driver, coupon_id, bets_data, stake=2.0):
    """
    1) stake=2
    2) single-click "Obstaw i graj"
    3) parse final success overlay => "Możesz wygrać X zł"
    4) click "OK, zamknij" if found
    5) if success => save bet to bets_data
    Return (stake_used, potential_win)
    """
    from selenium.common.exceptions import NoSuchElementException

    used_stake = 0.0
    potential = 0.0

    # A) set stake
    try:
        stake_input = driver.find_element(
            By.CSS_SELECTOR,
            "sts-shared-input[data-cy='ticket-stake'] input#AMOUNT"
        )
        stake_input.clear()
        stake_input.send_keys(str(stake))
        print(f"[INSP] Stake set to {stake:.2f}")
        used_stake = stake
        time.sleep(1)
    except NoSuchElementException:
        print("[INSP] stake input not found => fail.")
        return (0, 0)

    # B) click "Obstaw i graj" once
    try:
        bet_btn = driver.find_element(
            By.CSS_SELECTOR, 
            "button[data-testid='button-place-a-bet']"
        )
        bet_btn.click()
        print("[INSP] Clicked 'Obstaw i graj' once.")
        time.sleep(2)
    except NoSuchElementException:
        print("[INSP] No 'Obstaw i graj' button => fail.")
        return (0, 0)

    # C) parse final success overlay
    try:
        success_box = driver.find_element(By.CSS_SELECTOR, "div.status-dialog-content__description")
        raw_text = success_box.text
        match = re.search(r"Możesz wygrać\s*([\d\.,]+)\s*zł", raw_text)
        if match:
            val_str = match.group(1).replace(",", ".").replace("\xa0","")
            potential = float(val_str)
            print(f"[INSP] Confirmed potential from success overlay: {potential:.2f} zł")
        else:
            print("[INSP] Could not find 'Możesz wygrać' => 0.0")

        # D) click "OK, zamknij" if present
        try:
            ok_close_btn = driver.find_element(
                By.XPATH,
                "//button[contains(@class,'static-button') and contains(.,'OK, zamknij')]"
            )
            ok_close_btn.click()
            time.sleep(1)
            print("[INSP] Clicked 'OK, zamknij' to close overlay.")
        except NoSuchElementException:
            print("[INSP] 'OK, zamknij' not found => maybe auto-closed.")
    except NoSuchElementException:
        print("[INSP] no success overlay => potential=0.0")

    # E) If used_stake > 0 => store in JSON
    if used_stake > 0:
        bets_data["betted_coupons"].add(coupon_id)
        bets_data["bets_details"].append({
            "sport": "inspiration",
            "coupon_id": coupon_id,
            "stake": used_stake,
            "potential_win": potential,
            "balance_after": get_balance(driver),
        })
        save_bets_data(bets_data)

    return (used_stake, potential)

def go_to_next_coupon_page(driver):
    """
    Finds .sts-bonus-components__pagination-page => e.g. "Kupon 2 z 3"
    If current < total => click next => return True
    else return False
    """
    time.sleep(2)
    try:
        pagination_info = driver.find_element(
            By.CSS_SELECTOR,
            "div.sts-bonus-components__pagination-page"
        )
        text = pagination_info.text.strip()  # e.g. "Kupon 2 z 3"
        text = text.replace("\xa0"," ")
        match = re.search(r"(?i)Kupon\s*(\d+)\s*[^\d]+\s*(\d+)", text)
        if not match:
            print(f"[INSP] Could not parse pagination => '{text}'")
            return False

        current_num = int(match.group(1))
        total_num = int(match.group(2))
        if current_num >= total_num:
            print(f"[INSP] Last coupon => no next page. (current={current_num}, total={total_num})")
            return False

        next_btn = driver.find_element(
            By.CSS_SELECTOR,
            "sts-shared-static-button[icon='icon-next'] button.secondary.small.static.static-button.only-icon:not(.disabled)"
        )
        next_btn.click()
        print(f"[INSP] Moved to next coupon => (current was {current_num}, total={total_num})")
        time.sleep(3)
        return True
    except NoSuchElementException:
        print("[INSP] No pagination or next button => no more coupons.")
        return False
    except Exception as e:
        print(f"[INSP] Problem reading pagination => {e}")
        return False

def bet_inspiration_coupons(driver, bets_data):
    """
    1) go_to_inspiration_page
    2) for each user with success>=79 => open
       while True => get coupon_id => if not bet => copy => place => next
    """
    go_to_inspiration_page(driver)
    user_boxes = find_inspiration_users(driver)
    print(f"[INSP] Found {len(user_boxes)} user boxes in strefa-inspiracji.")

    for box in user_boxes:
        success = get_user_success_rate(box)
        print(f"[INSP] success={success:.2f}% for this user box.")
        if success < 79:
            continue

        # open user
        try:
            box.click()
            time.sleep(2)
        except Exception as e:
            print(f"[INSP] Could not click user box => {e}")
            continue

        while True:
            coupon_id = get_coupon_id(driver)
            if not coupon_id:
                print("[INSP] No coupon ID found => stopping this user.")
                break

            if coupon_id in bets_data["betted_coupons"]:
                print(f"[INSP] Already bet coupon {coupon_id} => next page.")
                if not go_to_next_coupon_page(driver):
                    time.sleep(5)
                    break
                continue

            # copy to basket
            if not copy_coupon(driver):
                print("[INSP] Could not copy coupon => skip or next page")
                if not go_to_next_coupon_page(driver):
                    time.sleep(5)
                    break
                continue

            # place bet => save
            stake_used, potential_win = place_inspiration_bet(driver, coupon_id, bets_data)
            if stake_used == 0:
                print("[INSP] Bet not placed => skip coupon.")
            # else we already saved in place_inspiration_bet

            # next page?
            if not go_to_next_coupon_page(driver):
                time.sleep(5)
                break

        time.sleep(2)

    return bets_data
