from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from auth import login_sts
from captcha_solver import solve_hcaptcha

def main():
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service)

    try:
        # 1. Log in
        login_sts(driver, username="example@example.com", password="Password123!")

        # 2. Attempt to solve hCaptcha if it appears
        solved = solve_hcaptcha(
            driver, 
            ai_api_endpoint="https://your-ai-solver.example.com/solve", 
            api_key="YOUR_API_KEY"
        )

        if solved:
            print("Captcha solved (or not required). Proceeding...")
        else:
            print("Captcha not solved successfully. Exiting or handle error...")

        # 3. Continue with next steps (placing bets, etc.)
        #    ...
        
        input("Press Enter to quit...")

    finally:
        driver.quit()

if __name__ == "__main__":
    main()
