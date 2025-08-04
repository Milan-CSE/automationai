import streamlit as st
import pandas as pd
import os
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from src.llm_agent import get_mapping_from_instruction, extract_form_fields_from_url
from src.selenium_runner import check_for_login_and_authenticate, run_agent_with_mapping

# --- Page Configuration & Session State ---
st.set_page_config(page_title="AI Form Filler Agent", layout="wide")
st.session_state.setdefault("failed_rows", [])
st.session_state.setdefault("mapping", None)
st.session_state.setdefault("uploaded_file_path", None)

# --- UI: Title ---
st.markdown("<h1 style='text-align: center; color:#4CAF50;'>🤖 AI Form Filler Agent</h1>", unsafe_allow_html=True)
st.markdown("---")

# --- UI: Step 1 - Inputs ---
st.subheader("Step 1: Provide All Information")
col1, col2 = st.columns(2)

with col1:
    url_input = st.text_input("Enter the live URL of the web form", placeholder="https://www.saucedemo.com")
    with st.expander("🔒 Provide Login Credentials (if needed)"):
        username = st.text_input("Username / Email")
        password = st.text_input("Password", type="password")
        st.session_state.auth_credentials = {"username": username, "password": password} if username and password else None

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

# --- NEW: Decoupled File Preview Section ---
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
st.subheader("Step 2: Start the Agent")
instruction = st.text_area("Instruction for AI", placeholder="e.g., 'Map the form fields to the file columns and fill out 5 rows.'", height=100)

if st.button("🚀 Start Agent and Fill Form"):
    # --- Input Validation ---
    if not url_input:
        st.error("Please provide the URL of the web form.")
    elif not uploaded_file:
        st.error("Please upload a data file.")
    elif not instruction:
        st.error("Please provide an instruction for the AI.")
    else:
        # --- Main Agent Logic ---
        driver = None
        try:
            with st.spinner("🤖 Agent is starting... Please wait."):
                # 1. Initialize Selenium Driver
                CHROMEDRIVER_PATH = "D:/Courses/Intel_AI_Course/Project_1/attendance_fillup_agent/chromedriver.exe"
                service = Service(CHROMEDRIVER_PATH)
                driver = webdriver.Chrome(service=service)
                st.info("✅ Driver started.")

                # 2. Handle Login (if credentials were provided)
                if st.session_state.auth_credentials:
                    st.info("🔐 Credentials provided. Attempting to log in...")
                    auth_result = check_for_login_and_authenticate(driver, url_input, st.session_state.auth_credentials)
                    if not auth_result:
                        st.error("Login failed! Please check credentials or if the login page is standard.")
                        st.stop()
                    st.success("Authentication successful!")
                else:
                    driver.get(url_input)

                # 3. Extract Form Fields from the current page (post-login)
                st.info("🔍 Extracting form fields from the page...")
                form_fields = extract_form_fields_from_url(driver=driver)
                if not form_fields:
                    st.error("Could not find any form fields on the target page.")
                    st.stop()
                st.success(f"Found {len(form_fields)} form fields.")
                # --- NEW: Preview of Form Fields ---
                with st.expander("📄 Click to see detected form fields from URL"):
                    st.json(form_fields)

                # 4. Read File Columns and Head
                st.info("📄 Reading columns and data from your file...")
                df = pd.read_csv(st.session_state.uploaded_file_path) if st.session_state.uploaded_file_path.endswith('.csv') else pd.read_excel(st.session_state.uploaded_file_path)
                file_columns = df.columns.tolist()
                st.success(f"Read {len(file_columns)} columns from the file.")
                # --- NEW: Preview of Uploaded File ---
                with st.expander("📄 Click to see uploaded file preview"):
                    st.write("**File Columns:**")
                    st.write(file_columns)
                    st.write("**File Head (first 5 rows):**")
                    st.dataframe(df.head())

                # 5. Generate Mapping with LLM
                st.info("🧠 AI is generating the field mapping...")
                mapping_data = get_mapping_from_instruction(instruction, form_fields, file_columns)
                if not mapping_data or "field_mapping" not in mapping_data:
                    st.error("AI could not generate a valid mapping. Please try a clearer instruction.")
                    st.stop()
                st.session_state.mapping = {
                    "file_path": st.session_state.uploaded_file_path,
                    "field_mapping": mapping_data["field_mapping"],
                    "row_to_fill": mapping_data.get("row_to_fill", 10) # Default to 10 if not specified
                }
                st.success("AI mapping generated successfully!")
                st.json(st.session_state.mapping['field_mapping'])

                # 6. Run the Form Filling Process
                st.info("✍️ Agent is now filling the form. See the browser window for activity...")
                failed_rows = run_agent_with_mapping(driver, st.session_state.mapping)
                st.session_state.failed_rows = failed_rows
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