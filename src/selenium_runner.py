from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
import time
import pandas as pd
from src.llm_agent import solve_row_error
from src.llm_agent import ask_llm_what_to_do
import json


def run_agent_with_mapping(mapping):
    try:
        CHROMEDRIVER_PATH = "D:/Courses/Intel_AI_Course/Project_1/attendance_fillup_agent/chromedriver.exe"
        service = Service(CHROMEDRIVER_PATH)
        driver = webdriver.Chrome(service=service)

        data = pd.read_csv(mapping["file_path"])
        row_limit = int(mapping.get("row_to_fill", len(data)))
        print(f"Limiting to {row_limit} rows")

        data = data.head(row_limit)
        driver.get("file:///D:/Courses/Intel_AI_Course/Project_1/attendance_fillup_agent/docs/attendance_form.html")

        log_file = open("D:/Courses/Intel_AI_Course/Project_1/attendance_fillup_agent/logs/form_status.txt", "w")

        # fill html form
        failed_rows = []

        for index, row in data.iterrows():

            try:
                name_l = row[mapping["field_mapping"]["name"]]
                date_l = row[mapping["field_mapping"]["date"]]
                time_l = row[mapping["field_mapping"]["time"]]

                if pd.isna(name_l) or pd.isna(date_l) or pd.isna(time_l):
                    raise Exception(f" Missing value in row {index + 1}")

                find_name = driver.find_element(By.ID, "name")
                find_name.clear()
                find_name.send_keys(name_l)

                find_date = driver.find_element(By.ID, "date")
                find_date.clear()
                find_date.send_keys(date_l)

                find_time = driver.find_element(By.ID, "time")
                find_time.clear()
                find_time.send_keys(time_l)

                print(f" Filled row {index + 1}: {name_l}, {date_l}, {time_l}")

                driver.find_element(By.XPATH, "//input[@type='submit']").click()
                time.sleep(2)

                log_file.write(f"Successfully fillup: {name_l} - {date_l} - {time_l}\n")

            except Exception as e:
                print(f" Failed row {index + 1}: {str(e)}")

                failed_rows.append({
                    "index": index+1,
                    "name": name_l,
                    "date": date_l,
                    "time": time_l,
                    "error": str(e)
                })
                print(failed_rows)

                log_file.write(f"Failed: {name_l} - {date_l} - {time_l} - Error: {str(e)}\n")

        print("Form fill complete.")
        print(f"Total rows fillup: {len(data)}")

        if failed_rows:
            decision = ask_llm_what_to_do(failed_rows)
            print("DEBUG LLM Decision JSON:", json.dumps(decision, indent=2))

            print("LLM returned this decision:", decision)

            #if not isinstance(decision, dict):
            if not decision or "decisions" not in decision:
                print("LLM response is not a valid dictionary. Skipping retry.")
                return
            print("Decision type: ", type(decision))

            if decision and isinstance(decision, dict) and "decisions" in decision:
                retry_indexes = [d["index"] for d in decision["decisions"] if d["action"] == "retry"]

                if retry_indexes:
                    print("Retrying failed rows...")


                # Retry to fill failed rows.

                for failed in failed_rows:

                    if failed["index"] in retry_indexes:
                        name_l = failed["name"]
                        date_l = failed["date"]
                        time_l = failed["time"]


                        if pd.isna(name_l) or pd.isna(date_l) or pd.isna(time_l):
                            print(f" Missing data in row {failed['index']}.. Asking human...")

                            if pd.isna(name_l) or pd.isna(date_l) or pd.isna(time_l):
                                print(f"\nMissing data in row {failed['index']}. Asking human what to do...\n")

                                human_action = solve_row_error([failed])  # Ask human via LLM

                                if human_action and human_action.get("action") == "Ask-User":
                                    print(f"\nManual entry required for row {failed['index']}\n")
                                    log_file.write(f"Manual entry required for row {failed['index']}\n")

                                    # Ask user to enter missing values
                                    '''
                                    name_input = input(
                                        f"Enter name for row {failed['index']} (or press Enter to keep '{failed['name']}'): ").strip()
                                    date_input = input(
                                        f"Enter date for row {failed['index']} (or press Enter to keep '{failed['date']}'): ").strip()
                                    time_input = input(
                                        f"Enter time for row {failed['index']} (or press Enter to keep '{failed['time']}'): ").strip()

                                    # Fallback to existing if user skipped
                                    name_l = name_input if name_input else failed["name"]
                                    date_l = date_input if date_input else failed["date"]
                                    time_l = time_input if time_input else failed["time"]'''

                                    # Update csv file with user input

                                    data.at[failed["index"] - 1, mapping["field_mapping"]["name"]] = name_l
                                    data.at[failed["index"] - 1, mapping["field_mapping"]["date"]] = date_l
                                    data.at[failed["index"] - 1, mapping["field_mapping"]["time"]] = time_l

                                    # Save updated data back to CSV file
                                    data.to_csv(mapping["file_path"], index=False)
                                    print(f"CSV file updated for row {failed['index']}")

                        try:

                            find_name = driver.find_element(By.ID, "name")
                            find_name.clear()
                            find_name.send_keys(name_l)

                            find_date = driver.find_element(By.ID, "date")
                            find_date.clear()
                            find_date.send_keys(date_l)

                            find_time = driver.find_element(By.ID, "time")
                            find_time.clear()
                            find_time.send_keys(time_l)

                            driver.find_element(By.XPATH, "//input[@type='submit']").click()
                            time.sleep(1)

                            log_file.write(f"Retry fillup is successful: {name_l},{date_l},{time_l}\n")
                            print("failed success info:",failed['index'])

                        except Exception as e:
                            log_file.write(f"RETRY Failed: {name_l} - {date_l} - {time_l} - Error: {str(e)}\n")
                            print("Retry failed for index:", failed['index'])


            else:
                print("LLM skip the retrying process.")

                # You can loop over failed_rows here again and try to fill them again
        else:
            print("No failed rows.")

        try:
            if driver:
                driver.quit()
        except Exception as e:
            print("Error while quitting the driver:", str(e))

    except Exception as e:
        print("Error during selenium Execution", e)

    return failed_rows

def run_agent_with_mapping_and_return_failed(mapping):
    try:
        return run_agent_with_mapping(mapping)
    except Exception as e:
        print("Error during selenium execution:", e)
        return []
