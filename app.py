import streamlit as st
import pandas as pd
import os
from src.llm_agent import get_mapping_from_instruction, extract_form_fields_from_url
from src.selenium_runner import run_agent_with_mapping_and_return_failed

# --- Page Configuration ---
st.set_page_config(
    page_title="AI Form Filler Agent",
    page_icon="🤖",
    layout="wide"
)

# --- Initial Setup & Session State ---
# Create a data directory if it doesn't exist
if not os.path.exists("data"):
    os.makedirs("data")

# Initialize session state variables
st.session_state.setdefault("failed_rows", [])
st.session_state.setdefault("mapping", None)
st.session_state.setdefault("form_fields", None)
st.session_state.setdefault("file_columns", None)
st.session_state.setdefault("uploaded_file_path", None)
st.session_state.setdefault("url_to_fill", None)


# --- UI: Title ---
st.markdown("<h1 style='text-align: center; color:#4CAF50;'>🤖 AI Form Filler Agent</h1>", unsafe_allow_html=True)
st.markdown("---")


# --- UI: Step 1 - Inputs (URL and File) ---
st.subheader("Step 1: Provide URL and Data File")
col1, col2 = st.columns(2)

with col1:
    url_input = st.text_input(
        "Enter the live URL of the web form",
        placeholder="https://example.com/form",
        key="url_input_key"
    )
    if url_input:
        st.session_state["url_to_fill"] = url_input

with col2:
    uploaded_file = st.file_uploader(
        "Upload your data file",
        type=["csv", "xlsx", "xls"],
        help="Upload a CSV or Excel file containing the data to fill."
    )

if uploaded_file:
    # Save the uploaded file to a fixed path
    temp_path = os.path.join("data", "uploaded_file" + os.path.splitext(uploaded_file.name)[1])
    with open(temp_path, "wb") as f:
        f.write(uploaded_file.getbuffer())
    st.session_state["uploaded_file_path"] = temp_path
    st.success(f"File '{uploaded_file.name}' uploaded successfully!")


# --- UI: Step 2 - Analysis ---
if st.session_state["url_to_fill"] and st.session_state["uploaded_file_path"]:
    st.markdown("---")
    st.subheader("Step 2: Analyze Page and File")

    if st.button("🔍 Analyze and Extract Fields"):
        with st.spinner("Analyzing URL to find form fields..."):
            try:
                st.session_state.form_fields = extract_form_fields_from_url(st.session_state["url_to_fill"])
                if not st.session_state.form_fields:
                    st.error("Could not find any form fields (like <input>, <select>, <textarea>) on the provided URL.")
                else:
                    st.success(f"Found {len(st.session_state.form_fields)} form fields.")
            except Exception as e:
                st.error(f"Failed to analyze URL: {e}")
                st.session_state.form_fields = None

        with st.spinner("Reading file to get column headers..."):
            try:
                file_path = st.session_state["uploaded_file_path"]
                if file_path.endswith('.csv'):
                    df = pd.read_csv(file_path)
                else:
                    df = pd.read_excel(file_path)
                st.session_state.file_columns = df.columns.tolist()
                st.success(f"Found {len(st.session_state.file_columns)} columns in the file.")
                st.markdown("**Data Preview:**")
                st.dataframe(df.head())
            except Exception as e:
                st.error(f"Failed to read file: {e}")
                st.session_state.file_columns = None

# Display extracted fields and columns
if st.session_state.form_fields and st.session_state.file_columns:
    col1, col2 = st.columns(2)
    with col1:
        st.info("Detected Form Fields:")
        st.json(st.session_state.form_fields)
    with col2:
        st.info("Detected File Columns:")
        st.json(st.session_state.file_columns)


# --- UI: Step 3 - Mapping (Automatic & Manual) ---
if st.session_state.form_fields and st.session_state.file_columns:
    st.markdown("---")
    st.subheader("Step 3: Map Form Fields to File Columns")

    tab1, tab2 = st.tabs(["🤖 Automatic Mapping (AI)", "✍️ Manual Mapping"])

    # Automatic Mapping Tab
    with tab1:
        instruction = st.text_input(
            "Instruction for AI",
            placeholder="e.g., 'Map form fields to the corresponding columns in my file.'"
        )
        rows_to_fill_auto = st.number_input("How many rows to process?", min_value=1, value=10, key="auto_rows")

        if st.button("Generate AI Mapping"):
            with st.spinner("Generating mapping using LLM..."):
                mapping = get_mapping_from_instruction(
                    instruction=instruction,
                    form_fields=st.session_state.form_fields,
                    file_columns=st.session_state.file_columns,
                )
                if mapping and "field_mapping" in mapping:
                    # Validate that the mapped columns exist in the file
                    mapped_cols = mapping["field_mapping"].values()
                    missing_cols = [col for col in mapped_cols if col not in st.session_state.file_columns]
                    if missing_cols:
                        st.error(f"AI mapping failed: The following columns specified by the AI do not exist in your file: `{missing_cols}`. Please try again or use manual mapping.")
                    else:
                        st.session_state.mapping = {
                           "file_path": st.session_state["uploaded_file_path"],
                           "field_mapping": mapping["field_mapping"],
                           "row_to_fill": rows_to_fill_auto
                        }
                        st.success("AI mapping generated successfully!")
                        st.json(st.session_state.mapping)
                else:
                    st.error("Could not generate a valid mapping from the instruction.")

    # Manual Mapping Tab
    with tab2:
        st.warning("If automatic mapping fails or is incorrect, define it manually below.")
        manual_mapping = {}
        for field in st.session_state.form_fields:
            # Add a "None" option to allow skipping fields
            options = [None] + st.session_state.file_columns
            selected_col = st.selectbox(f"Form Field: `{field}` ->", options=options, key=f"map_{field}")
            if selected_col:
                manual_mapping[field] = selected_col

        rows_to_fill_manual = st.number_input("How many rows to process?", min_value=1, value=10, key="manual_rows")

        if st.button("Set Manual Mapping"):
            if not manual_mapping:
                st.error("Please map at least one field.")
            else:
                st.session_state.mapping = {
                    "file_path": st.session_state["uploaded_file_path"],
                    "field_mapping": manual_mapping,
                    "row_to_fill": rows_to_fill_manual
                }
                st.success("Manual mapping saved!")
                st.json(st.session_state.mapping)

# --- UI: Step 4 - Run Agent ---
if st.session_state.mapping:
    st.markdown("---")
    st.subheader("Step 4: Run the Agent")
    st.info("The agent will now open a browser window to perform the form filling live.")

    if st.button("🚀 Start Agent"):
        try:
            st.info("Agent started... Please wait while the form is being filled.")
            with st.spinner("Processing rows... See the live browser window for activity."):
                failed_rows = run_agent_with_mapping_and_return_failed(
                    st.session_state.mapping,
                    st.session_state["url_to_fill"]
                )
            st.session_state["failed_rows"] = failed_rows

            if failed_rows:
                st.warning("Some rows failed. See details below.")
                st.dataframe(pd.DataFrame(failed_rows))
            else:
                st.success("✅ Agent finished filling forms with no errors!")

        except Exception as e:
            st.error(f"Agent failed to run: {str(e)}")

# --- UI: Manual Correction for Failed Rows ---
if st.session_state.failed_rows:
    st.markdown("---")
    st.header("Manual Correction for Failed Rows")
    st.warning("The agent could not process some rows. You can manually correct the data and re-run the agent.")
    st.dataframe(pd.DataFrame(st.session_state.failed_rows))