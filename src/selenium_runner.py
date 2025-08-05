import time
import pandas as pd
from selenium.webdriver.common.by import By
from selenium.common.exceptions import NoSuchElementException

def check_for_login_and_authenticate(driver, url, credentials):
    driver.get(url)
    time.sleep(2)
    try:
        login_field = driver.find_element(By.CSS_SELECTOR, "input[type='text'], input[type='email'], input[name*='user'], input[id*='user']")
        password_field = driver.find_element(By.CSS_SELECTOR, "input[type='password'], input[name*='pass'], input[id*='pass']")
    except NoSuchElementException:
        print("No standard login page detected. Proceeding...")
        return True # Not a login page

    if login_field and password_field:
        login_field.send_keys(credentials['username'])
        password_field.send_keys(credentials['password'])
        submit_button = None
        button_strategies = [ (By.XPATH, "//button[@type='submit']"), (By.XPATH, "//input[@type='submit']"), (By.ID, "login-button") ]
        for by, selector in button_strategies:
            try:
                submit_button = driver.find_element(by, selector)
                if submit_button: break
            except NoSuchElementException: continue
        
        if submit_button:
            submit_button.click()
            time.sleep(3)
            error_keywords = ['incorrect', 'invalid', 'failed', 'wrong', 'error']
            if any(keyword in driver.page_source.lower() for keyword in error_keywords):
                return "INCORRECT_CREDENTIALS"
            return True
        else:
            return "SUBMIT_BUTTON_NOT_FOUND"
    return True

def run_agent_with_mapping(driver, mapping):
    """
    Uses the PASSED-IN driver. Does NOT create its own.
    """
    failed_rows = []
    try:
        file_path = mapping["file_path"]
        data = pd.read_csv(file_path) if file_path.endswith('.csv') else pd.read_excel(file_path)
        row_limit = int(mapping.get("row_to_fill", len(data)))
        data = data.head(row_limit)
        
        form_url = driver.current_url

        for index, row in data.iterrows():
            try:
                driver.get(form_url) # Navigate back to the form for each new entry
                time.sleep(2)
                for field_id, column_name in mapping["field_mapping"].items():
                    if column_name not in row: continue
                    value_to_fill = row[column_name]
                    if pd.isna(value_to_fill): continue
                    try:
                        element = driver.find_element(By.ID, field_id)
                    except NoSuchElementException:
                        element = driver.find_element(By.NAME, field_id)
                    element.clear()
                    element.send_keys(str(value_to_fill))
                
                driver.find_element(By.XPATH, "//input[@type='submit'] | //button[@type='submit']").click()
                time.sleep(2)
            except Exception as e:
                failed_rows.append({"index": index + 1, "data": row.to_dict(), "error": str(e)})
                print(f"Failed to process row {index + 1}: {e}")
    except Exception as e:
        print(f"An error occurred during form filling: {e}")
    return failed_rows