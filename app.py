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

# --- UI: Title ---
st.markdown("<h1 style='text-align: center; color:#4CAF50;'>🤖 AI Form Filler Agent</h1>", unsafe_allow_html=True)
st.markdown("---")

# --- Function to setup the driver for Streamlit Cloud ---
def setup_driver():
    options = webdriver.ChromeOptions()
    # Explicitly tell Selenium where the browser binary is
    options.binary_location = "/usr/bin/google-chrome-stable"
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    
    # Explicitly point to the chromedriver installed by packages.txt
    service = Service(executable_path="/usr/bin/chromedriver")
    
    return webdriver.Chrome(service=service, options=options)

# --- UI Inputs ---
st.subheader("Step 1: Provide All Information")
url_input = st.text_input("Enter the live URL of the web form", placeholder="https://www.saucedemo.com")
uploaded_file = st.file_uploader("Upload your data file (CSV or Excel)", type=["csv", "xlsx", "xls"])

with st.expander("🔒 Provide Login Credentials (if needed)"):
    username = st.text_input("Username / Email")
    password = st.text_input("Password", type="password")

instruction = st.text_area("Instruction for AI", placeholder="e.g., 'Map form fields to file columns and fill 5 rows.'", height=100)

st.markdown("---")

# --- Single Button to Run Everything ---
if st.button("🚀 Start Agent", type="primary", use_container_width=True):
    # Validate Inputs
    if not all([url_input, uploaded_file, instruction]):
        st.error("Please provide a URL, upload a file, and write an instruction.")
    else:
        # Save uploaded file temporarily
        data_dir = "data"
        if not os.path.exists(data_dir):
            os.makedirs(data_dir)
        temp_path = os.path.join(data_dir, uploaded_file.name)
        with open(temp_path, "wb") as f:
            f.write(uploaded_file.getbuffer())

        auth_credentials = {"username": username, "password": password} if username and password else None
        
        driver = None
        try:
            with st.spinner("🤖 Agent is starting... Please wait."):
                
                # --- NEW: Sanity Check to see if files exist ---
                st.info("1. Verifying browser and driver installation...")
                chrome_exists = os.path.exists("/usr/bin/google-chrome-stable")
                driver_exists = os.path.exists("/usr/bin/chromedriver")
                st.write(f"- Google Chrome executable found: {chrome_exists}")
                st.write(f"- Chromedriver executable found: {driver_exists}")
                if not chrome_exists or not driver_exists:
                    st.error("FATAL: Chrome or Chromedriver not found at the expected path. Please check your packages.txt file and reboot the app.")
                    st.stop()
                # --- End of Sanity Check ---

                st.info("2. Initializing secure cloud browser...")
                driver = setup_driver()
                
                st.info("3. Navigating to page and handling login...")
                if auth_credentials:
                    auth_result = check_for_login_and_authenticate(driver, url_input, auth_credentials)
                    if auth_result is True:
                        st.success("Authentication successful!")
                    else:
                        st.error(f"Login failed: {auth_result}. Please check credentials and try again.")
                        st.stop()
                else:
                    driver.get(url_input)
                
                # ... (The rest of the logic remains the same) ...
                
                st.success("✅ Agent has finished the process!")

        except Exception as e:
            st.error(f"An unexpected error occurred: {e}")
        finally:
            if driver:
                driver.quit()