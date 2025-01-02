import os
import json
import time
from selenium.webdriver.common.by import By
from selenium.common.exceptions import NoSuchElementException

def get_daily_bet_filename():
    date_str = time.strftime("%d_%m_%Y")
    daily_filename = f"bets_data_{date_str}.json"

    folder = os.path.join(os.path.dirname(__file__), "db")
    os.makedirs(folder, exist_ok=True)

    return os.path.join(folder, daily_filename)

def load_bets_data():
    json_path = get_daily_bet_filename()

    if not os.path.exists(json_path):
        return {
            "betted_matches": set(),
            "betted_coupons": set(),   # NEW: track coupon IDs
            "bets_details": []
        }
    try:
        with open(json_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            data["betted_matches"] = set(data.get("betted_matches", []))
            # If not present, initialize empty set
            data["betted_coupons"] = set(data.get("betted_coupons", []))
            return data
    except Exception as e:
        print(f"Error loading {json_path}: {e}")
        return {
            "betted_matches": set(),
            "betted_coupons": set(),
            "bets_details": []
        }

def save_bets_data(bets_data):
    json_path = get_daily_bet_filename()

    data_to_save = {
        "betted_matches": list(bets_data["betted_matches"]),
        "betted_coupons": list(bets_data.get("betted_coupons", [])),
        "bets_details": bets_data["bets_details"],
        "last_saved": time.strftime("%Y-%m-%d %H:%M:%S")
    }
    try:
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(data_to_save, f, ensure_ascii=False, indent=2)
        print(f"[OK] bets_data saved to {json_path}")
    except Exception as e:
        print(f"Error saving {json_path}: {e}")

def get_balance(driver):
    try:
        balance_el = driver.find_element(
            By.CSS_SELECTOR, 
            "sts-shared-icon-button-deposit-info .icon-button-deposit-info__amount"
        )
        raw_text = balance_el.text.strip()
        cleaned_text = raw_text.replace("zł", "").replace("\xa0", "").strip()
        cleaned_text = cleaned_text.replace(",", ".")
        return float(cleaned_text)
    except NoSuchElementException:
        print("Could not find deposit info element. Returning 0.0.")
        return 0.0
    except ValueError:
        print("Error parsing balance text. Returning 0.0.")
        return 0.0
    except Exception as e:
        print(f"Unexpected error reading balance: {e}")
        return 0.0

def clear_basket(driver):
    try:
        menu_button = driver.find_element(By.CSS_SELECTOR, "button[data-cy='ticket-header-menu-open']")
        menu_button.click()
        print("Opened ticket menu.")
    except NoSuchElementException:
        print("No menu button found (possibly no basket?). Skipping basket clear.")
        return
    except Exception as e:
        print(f"Error clicking menu button: {e}")
        return

    time.sleep(1)

    try:
        clear_button = driver.find_element(
            By.CSS_SELECTOR, 
            "bb-ticket-menu-item[data-cy='ticket-header-menu-clear'] button.ticket-menu-item"
        )
        clear_button.click()
        print("Basket cleared (Wyczyść kupon).")
    except NoSuchElementException:
        print("No 'Wyczyść kupon' button found.")
    except Exception as e:
        print(f"Error clearing the basket: {e}")
