import streamlit as st
import pandas as pd
import os
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
import time
from src.llm_agent import get_mapping_from_instruction, extract_form_fields_from_url
from src.selenium_runner import check_for_login_and_authenticate, run_agent_with_mapping

# --- Page Configuration & Session State ---
st.set_page_config(page_title="AI Form Filler Agent", layout="wide")
st.session_state.setdefault("failed_rows", [])
st.session_state.setdefault("mapping", None)
st.session_state.setdefault("uploaded_file_path", None)
st.session_state.setdefault("form_fields", None) 
st.session_state.setdefault("auth_credentials", None)

# --- UI: Title ---
st.markdown("<h1 style='text-align: center; color:#4CAF50;'>🤖 AI Form Filler Agent</h1>", unsafe_allow_html=True)
st.markdown("---")

# --- Function to setup the driver (to avoid code repetition) ---
def setup_driver():
    options = webdriver.ChromeOptions()
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    
    # Explicitly point to the chromedriver installed by packages.txt
    service = Service("/usr/bin/chromedriver")
    
    return webdriver.Chrome(service=service, options=options)

# --- UI: Step 1 - Inputs ---
st.subheader("Step 1: Analyze the Webpage")
url_input = st.text_input("Enter the live URL of the web form", placeholder="https://www.saucedemo.com")

if st.button("👁️ Analyze URL for Fields"):
    if not url_input:
        st.error("Please enter a URL to analyze.")
    else:
        with st.spinner("Analyzing URL..."):
            driver = None
            try:
                driver = setup_driver()
                
                if st.session_state.auth_credentials:
                    st.info("Credentials provided. Logging in before analysis...")
                    check_for_login_and_authenticate(driver, url_input, st.session_state.auth_credentials)
                else:
                    driver.get(url_input)
                
                time.sleep(3)
                fields = extract_form_fields_from_url(driver)
                st.session_state.form_fields = fields
            except Exception as e:
                st.error(f"Failed to start driver or access URL. Error: {e}")
                if driver: driver.save_screenshot('debug_error_screenshot.png')
            finally:
                if driver: driver.quit()

# --- Display Sections ---
st.markdown("---")
col_fields, col_preview = st.columns(2)


# --- UI: Step 2 - Run the Agent ---
st.markdown("---")
st.subheader("Enter instruction & Start the Agent")
instruction = st.text_area("Instruction for AI", placeholder="e.g., 'Map the form fields to the file columns and fill out 5 rows.'", height=100)

if st.button("🚀 Start Agent and Fill Form"):
    # --- Input Validation ---
    if not all([url_input, st.session_state.uploaded_file_path, instruction, st.session_state.form_fields]):
        st.error("Please ensure you have successfully analyzed a URL, uploaded a file, and provided an instruction.")
    else:
        # --- Main Agent Logic ---
        driver = None
        try:
            with st.spinner("🤖 Agent is starting... Please wait."):
            
                # Use the helper function
                st.info("✅ Initializing driver for the main task...")
                driver = setup_driver()
                st.info("✅ Driver started successfully.")

                # 2. Handle Login
                if st.session_state.auth_credentials:
                    auth_result = check_for_login_and_authenticate(driver, url_input, st.session_state.auth_credentials)
                    if auth_result is True:
                        st.success("Authentication successful!")
                    elif auth_result == "INCORRECT_CREDENTIALS":
                        st.error("Login Failed! The username or password provided is incorrect.")
                        st.stop()
                    else: # Catches False or other errors
                        st.error("Login Failed! Could not complete the login process.")
                        st.stop()
                else:
                    driver.get(url_input)
                # This is a simplified placeholder for the rest of your logic
                st.success("✅ Agent has finished the process!")

        except Exception as e:
            st.error(f"An unexpected error occurred: {str(e)}")
        finally:
            if driver:
                driver.quit()

# --- UI: Display Results ---
if st.session_state.failed_rows:
    st.markdown("---")
    st.subheader("Results")
    st.warning("Some rows failed to process. See details below.")
    st.dataframe(pd.DataFrame(st.session_state.failed_rows))