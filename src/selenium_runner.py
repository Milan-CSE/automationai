from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.common.exceptions import NoSuchElementException
import time
import pandas as pd
from src.llm_agent import solve_row_error
from src.llm_agent import ask_llm_what_to_do
import os

def run_agent_with_mapping(mapping, driver):
    """
    Runs a Selenium agent to fill a web form from a live URL using a dynamic mapping.
    """
    CHROMEDRIVER_PATH = "D:/Courses/Intel_AI_Course/Project_1/attendance_fillup_agent/chromedriver.exe" # Make sure this path is correct
    service = Service(CHROMEDRIVER_PATH)
    driver = webdriver.Chrome(service=service)
    
    failed_rows = []
    
    try:
        # Read data from CSV or Excel
        file_path = mapping["file_path"]
        if file_path.endswith('.csv'):
            data = pd.read_csv(file_path)
        else:
            data = pd.read_excel(file_path)

        row_limit = int(mapping.get("row_to_fill", len(data)))
        print(f"Limiting to {row_limit} rows")
        data = data.head(row_limit)

        log_dir = "logs"
        if not os.path.exists(log_dir):
            os.makedirs(log_dir)
        log_file = open(os.path.join(log_dir, "form_status.txt"), "w")

        # --- Main Loop to Fill Form ---
        for index, row in data.iterrows():
            try:

                filled_data_log = []
                # Dynamically fill fields based on the mapping
                for field_id, column_name in mapping["field_mapping"].items():
                    if column_name not in row:
                        raise ValueError(f"Column '{column_name}' not found in the data file.")

                    value_to_fill = row[column_name]
                    
                    # Skip filling if data is missing
                    if pd.isna(value_to_fill):
                        print(f"Skipping field '{field_id}' for row {index + 1} due to missing data.")
                        continue

                    # Find element and fill it
                    try:
                        element = driver.find_element(By.ID, field_id)
                    except NoSuchElementException:
                        # Fallback to finding by 'name' attribute if ID fails
                        element = driver.find_element(By.NAME, field_id)

                    element.clear()
                    element.send_keys(str(value_to_fill))
                    filled_data_log.append(f"{field_id}: {value_to_fill}")

                print(f"Filled row {index + 1}: {', '.join(filled_data_log)}")
                
                # Find and click the submit button
                # This might need to be more robust (e.g., find by text or a more specific XPath)
                submit_button = driver.find_element(By.XPATH, "//input[@type='submit'] | //button[@type='submit']")
                submit_button.click()
                time.sleep(2) # Wait for submission processing

                log_file.write(f"Successfully submitted row {index + 1}: {row.to_dict()}\n")

            except Exception as e:
                error_message = str(e)
                print(f"Failed to process row {index + 1}: {error_message}")
                failed_row_data = row.to_dict()
                failed_row_data["index"] = index + 1
                failed_row_data["error"] = error_message
                failed_rows.append(failed_row_data)
                log_file.write(f"Failed row {index + 1}: {row.to_dict()} - Error: {error_message}\n")

        print("Form fill process completed.")

    except Exception as e:
        print(f"An error occurred during Selenium execution: {e}")
    finally:
        if 'driver' in locals() and driver:
            driver.quit()
        if 'log_file' in locals() and log_file:
            log_file.close()
            
    return failed_rows

# Check if the page is a login page and handle authentication

def check_for_login_and_authenticate(driver, url, credentials=None):
    """
    Checks if the page is a login page and uses credentials to log in if provided.
    """
    driver.get(url)
    time.sleep(2)

    login_field_identifiers = ['user-name', 'username', 'email', 'user_login']
    password_field_identifiers = ['password', 'pass', 'user_pass']
    
    login_field, password_field = None, None

    for identifier in login_field_identifiers:
        try:
            login_field = driver.find_element(By.ID, identifier) or driver.find_element(By.NAME, identifier)
            if login_field: break
        except NoSuchElementException:
            continue

    for identifier in password_field_identifiers:
        try:
            password_field = driver.find_element(By.ID, identifier) or driver.find_element(By.NAME, identifier)
            if password_field: break
        except NoSuchElementException:
            continue

    if login_field and password_field:
        if credentials:
            print("Login page detected. Authenticating...")
            login_field.send_keys(credentials['username'])
            password_field.send_keys(credentials['password'])
            
            # --- NEW: Robust Button Finding Logic ---
            submit_button = None
            # A list of strategies to find the login button
            button_strategies = [
                (By.XPATH, "//button[@type='submit']"),
                (By.XPATH, "//input[@type='submit']"),
                (By.ID, "login-button"),
                (By.ID, "Login"),
                (By.XPATH, "//*[contains(text(), 'Log In')]"),
                (By.XPATH, "//*[contains(text(), 'Sign In')]"),
                (By.XPATH, "//*[contains(text(), 'Login')]"),
                (By.CLASS_NAME, "login-button") # Add more common class names if you find them
            ]

            for by, selector in button_strategies:
                try:
                    print(f"Trying to find button with: {by} = '{selector}'")
                    submit_button = driver.find_element(by, selector)
                    if submit_button:
                        print("Button found!")
                        break # Exit the loop once the button is found
                except NoSuchElementException:
                    continue # Try the next strategy
            
            if submit_button:
                submit_button.click()
                print("Login submitted.")
                time.sleep(3)
                return True
            else:
                # This is where your error was triggered
                print("Could not find a submit button using any known strategy.")
                return False
        else:
            return "LOGIN_REQUIRED" 
            
    print("No standard login page detected. Proceeding...")
    return True

def run_agent_with_mapping_and_return_failed(mapping, url):
    """Wrapper function for easier calling from Streamlit."""
    try:
        return run_agent_with_mapping(mapping, url)
    except Exception as e:
        print(f"Error in wrapper for selenium execution: {e}")
        return []