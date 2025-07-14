import streamlit as st
from src.llm_agent import get_mapping_from_instruction
import pandas as pd
from src.selenium_runner import run_agent_with_mapping_and_return_failed

# File upload at the top
uploaded_file = st.file_uploader("Upload your CSV file", type=["csv"])

if uploaded_file is not None:
    df = pd.read_csv(uploaded_file)
    st.success("File uploaded successfully!")
    st.dataframe(df.head())

    # Save the uploaded file to a fixed path
    temp_path = "data/uploaded_data.csv"
    df.to_csv(temp_path, index=False)

    # Inject into session so mapping/agent uses this file
    st.session_state["uploaded_file_path"] = temp_path

# Title
col1, = st.columns([0.85])
with col1:
    st.markdown("<h1 style='color:#4CAF50;'>🧠 AI Attendance Filler</h1>", unsafe_allow_html=True)

st.session_state.setdefault("failed_rows", None)
st.session_state.setdefault("retry_index", None)
st.session_state.setdefault("mapping", None)


# instruction input
st.subheader("Describe the Task")
with st.container():
    st.markdown("## Define the Instruction")
    st.markdown("Tell the agent what task to perform from the CSV file (e.g., 'Fill the attendance form using the CSV')")
    instruction = st.text_input(" Instruction")


# When user clicks Generate Mapping
if instruction and st.button(" Generate Mapping"):
    with st.spinner("Generating mapping using LLM..."):
        mapping = get_mapping_from_instruction(instruction)

        # Inject the uploaded file path if it exists
        if "uploaded_file_path" in st.session_state:
            mapping["file_path"] = st.session_state["uploaded_file_path"]

    if mapping:
        st.success(" Mapping generated successfully!")
        st.session_state.mapping = mapping  # Save mapping to session
        st.json(mapping)
    else:
        st.error("Could not generate mapping from instruction.")

# Show Start Agent button only if mapping exists
if st.session_state.mapping:
    st.markdown("---")
    st.subheader("Run the Agent")
    if st.button("Start Agent"):
        try:
            st.info("Agent started... Please wait while the form is being filled.")

            failed_rows = run_agent_with_mapping_and_return_failed(st.session_state.mapping)  # new function
            st.session_state["failed_rows"] = failed_rows

            if failed_rows:
                st.warning("Some rows failed. Manual correction required.")
                st.session_state["retry_index"] = failed_rows[0]["index"]  # Take first
            else:
                st.success(" Agent finished filling forms!")

        except Exception as e:
            st.error(f"Agent failed to run: {str(e)}")

#Manual Correction only if failed row exists

if st.session_state.failed_rows and st.session_state.retry_index:
    st.markdown("---")
    row_index = st.session_state.retry_index
    failed_row = next(r for r in st.session_state.failed_rows if r["index"] == row_index)

    st.header(f"Manual Correction — Row {row_index}")
    st.info(f"Original values → Name: {failed_row['name']} | Date: {failed_row['date']} | Time: {failed_row['time']}")

    with st.form("manual_fill_form"):
        name_input = st.text_input("Name", value="" if pd.isna(failed_row["name"]) else failed_row["name"])
        date_input = st.text_input("Date", value="" if pd.isna(failed_row["date"]) else failed_row["date"])
        time_input = st.text_input("Time", value="" if pd.isna(failed_row["time"]) else failed_row["time"])
        submitted = st.form_submit_button("Submit Manual Data")

    # Update CSV file
    if submitted:

        df = pd.read_csv(st.session_state.mapping["file_path"])
        df.loc[row_index - 1, st.session_state.mapping["field_mapping"]["name"]] = name_input
        df.loc[row_index - 1, st.session_state.mapping["field_mapping"]["date"]] = date_input
        df.loc[row_index - 1, st.session_state.mapping["field_mapping"]["time"]] = time_input
        df.to_csv(st.session_state.mapping["file_path"], index=False)

        st.success(" CSV updated. You can now retry this row from the Start Agent button.")

        # Optionally, remove this row from failed_rows
        st.session_state["failed_rows"] = [
            r for r in st.session_state["failed_rows"] if r["index"] != row_index
        ]
        st.session_state["retry_index"] = None  # Reset retry index

        if st.button("Retry Agent"):
            st.rerun()


