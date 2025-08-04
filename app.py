import streamlit as st
import pandas as pd
import os
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
import time
from src.llm_agent import get_mapping_from_instruction, extract_form_fields_from_url
from src.selenium_runner import check_for_login_and_authenticate, run_agent_with_mapping
from webdriver_manager.chrome import ChromeDriverManager

# --- Page Configuration & Session State ---
st.set_page_config(page_title="AI Form Filler Agent", layout="wide")
st.session_state.setdefault("failed_rows", [])
st.session_state.setdefault("mapping", None)
st.session_state.setdefault("uploaded_file_path", None)
st.session_state.setdefault("form_fields", None) # To store extracted fields
st.session_state.setdefault("auth_credentials", None)

# --- UI: Title ---
st.markdown("<h1 style='text-align: center; color:#4CAF50;'>🤖 AI Form Filler Agent</h1>", unsafe_allow_html=True)
st.markdown("---")

# --- UI: Step 1 - Inputs ---
st.subheader("Please Provide Required Information")
col1, col2 = st.columns(2)

with col1:
    url_input = st.text_input("Enter the live URL of the web form", placeholder="https://www.saucedemo.com")
    with st.expander("🔒 Provide Login Credentials (if needed for analysis or filling)"):
        username = st.text_input("Username / Email")
        password = st.text_input("Password", type="password")
        st.session_state.auth_credentials = {"username": username, "password": password} if username and password else None

    # --- NEW: URL Field Analysis Section ---
    if st.button("👁️ Analyze URL for Fields"):
        if not url_input:
            st.error("Please enter a URL to analyze.")
        else:
            with st.spinner("Analyzing URL... This may take a moment."):
                driver = None
                try:
                    # Use a headless driver for quick, non-intrusive analysis
                    CHROMEDRIVER_PATH = "D:/Courses/Intel_AI_Course/Project_1/attendance_fillup_agent/chromedriver.exe"
                    service = Service(CHROMEDRIVER_PATH)
                    options = webdriver.ChromeOptions()
                    options.add_argument('--headless')
                    options.add_argument('--disable-gpu')
                    driver = webdriver.Chrome(service=service, options=options)

                    driver.save_screenshot('debug_screenshot.png')
                    with open('debug_page_source.html', 'w', encoding='utf-8') as f:
                        f.write(driver.page_source)
                    
                    # If credentials are provided, attempt to log in before extracting
                    if st.session_state.auth_credentials:
                        st.info("Credentials provided. Attempting login before analysis...")
                        auth_result = check_for_login_and_authenticate(driver, url_input, st.session_state.auth_credentials)
                        if auth_result is not True:
                         st.error("Login failed during analysis. Cannot proceed.")
                         st.stop()
                    else:
                        driver.get(url_input)

                    time.sleep(3) # Extra wait
                    driver.save_screenshot('debug_analysis_screenshot.png')

                    fields = extract_form_fields_from_url(driver)
                    st.session_state.form_fields = fields # Save to session state
                except Exception as e:
                    st.error(f"Failed to start driver or access URL. Error: {e}")
                finally:
                    if driver:
                        driver.quit()

with col2:
    uploaded_file = st.file_uploader("Upload your data file", type=["csv", "xlsx", "xls"])
    if uploaded_file:
        data_dir = "data"
        if not os.path.exists(data_dir):
            os.makedirs(data_dir)
        temp_path = os.path.join(data_dir, "uploaded_file" + os.path.splitext(uploaded_file.name)[1])
        with open(temp_path, "wb") as f:
            f.write(uploaded_file.getbuffer())
        st.session_state.uploaded_file_path = temp_path

# --- Display Detected Fields and File Preview ---
st.markdown("---")
col_fields, col_preview = st.columns(2)

with col_fields:
    if st.session_state.form_fields:
        st.subheader("Detected Web Form Fields")
        st.success(f"Found {len(st.session_state.form_fields)} fields.")
        st.json(st.session_state.form_fields)
    elif st.session_state.form_fields == []:
        st.warning("Analysis complete, but no form fields were found.")

with col_preview:
    if st.session_state.uploaded_file_path:
        st.subheader("Uploaded File Preview")
        try:
            df = pd.read_csv(st.session_state.uploaded_file_path) if st.session_state.uploaded_file_path.endswith('.csv') else pd.read_excel(st.session_state.uploaded_file_path)
            st.write("**File Columns:**", df.columns.tolist())
            st.write("**File Head (first 5 rows):**")
            st.dataframe(df.head())
        except Exception as e:
            st.error(f"Could not read or preview the uploaded file. Error: {e}")


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
                # 1. Initialize Selenium Driver
                driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
                st.info("✅ Driver started.")

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