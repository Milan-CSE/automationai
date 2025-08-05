# app.py (Temporary Direct Install Diagnostic Tool)

import streamlit as st
import subprocess
import os

st.set_page_config(layout="wide")
st.title("Streamlit Cloud Direct Installation Tool 🔬")

st.warning(
    "This is a diagnostic tool. Its purpose is to force the installation of Chrome "
    "and see the live output from the server's package manager."
)

if st.button("Attempt to Manually Install & Verify Chrome"):

    st.header("1. Updating Package Lists (`apt-get update`)")
    with st.spinner("Running apt-get update..."):
        update_result = subprocess.run(['apt-get', 'update'], capture_output=True, text=True)
    
    st.subheader("Update Log:")
    st.code(update_result.stdout + "\n" + update_result.stderr, language="shell")
    if update_result.returncode == 0:
        st.success("Package lists updated successfully.")
    else:
        st.error("Failed to update package lists.")


    st.header("2. Installing Chromium & Chromedriver (`apt-get install`)")
    with st.spinner("Running apt-get install -y chromium chromium-driver..."):
        install_result = subprocess.run(
            ['apt-get', 'install', '-y', 'chromium', 'chromium-driver'], 
            capture_output=True, 
            text=True
        )

    st.subheader("Installation Log:")
    st.code(install_result.stdout + "\n" + install_result.stderr, language="shell")
    if install_result.returncode == 0:
        st.success("Chromium and Chromedriver installation command finished successfully.")
    else:
        st.error("Installation command failed.")


    st.header("3. Final Verification (`os.path.exists`)")
    chromium_path = "/usr/bin/chromium"
    driver_path = "/usr/bin/chromedriver"

    st.write(f"Checking for `{chromium_path}`...")
    st.info(f"Exists: **{os.path.exists(chromium_path)}**")

    st.write(f"Checking for `{driver_path}`...")
    st.info(f"Exists: **{os.path.exists(driver_path)}**")