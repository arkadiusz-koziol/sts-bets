import time
from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.common.exceptions import NoSuchElementException


def login_sts(driver: WebDriver, username: str, password: str):
    driver.get("https://www.sts.pl/live")
    time.sleep(2)

    try:
        accept_all_button = driver.find_element(By.ID, "CybotCookiebotDialogBodyLevelButtonLevelOptinAllowAll")
        accept_all_button.click()
        time.sleep(1)
    except NoSuchElementException:
        print("Cookie consent button not found or already accepted.")

    login_button = driver.find_element(By.CSS_SELECTOR, "button[data-cy='static-button']")
    login_button.click()
    time.sleep(2)
    username_input = driver.find_element(By.ID, "Username")
    username_input.send_keys(username)
    password_input = driver.find_element(By.ID, "Password")
    password_input.send_keys(password)
    login_submit_button = driver.find_element(By.CSS_SELECTOR, "button[data-testid='button-login']")
    login_submit_button.click()
    time.sleep(2)
