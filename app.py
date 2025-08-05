# app.py (Temporary Diagnostic Tool)

import streamlit as st
import subprocess
import os

st.set_page_config(layout="wide")
st.title("Streamlit Cloud Environment Investigator 🕵️")

st.info(
    "This tool runs commands on the Streamlit server to help diagnose why Selenium is not working. "
    "Click the button below and then copy and paste the ENTIRE output back for analysis."
)

if st.button("🔬 Run Diagnostic Commands"):

    commands = [
        ["echo", "--- 1. Checking Current Directory and .streamlit folder ---"],
        ["ls", "-la"],
        ["ls", "-la", ".streamlit/"],
        ["echo", "--- 2. Checking contents of packages.txt ---"],
        ["cat", ".streamlit/packages.txt"],
        ["echo", "--- 3. Searching entire system for chromedriver (this may take a moment) ---"],
        ["find", "/", "-name", "chromedriver", "-type", "f", "2>/dev/null"],
        ["echo", "--- 4. Searching entire system for chromium-browser ---"],
        ["find", "/", "-name", "chromium-browser", "-type", "f", "2>/dev/null"],
        ["echo", "--- 5. Checking OS Release Information ---"],
        ["cat", "/etc/os-release"],
        ["echo", "--- 6. End of Report ---"]
    ]

    st.subheader("Diagnostic Report")
    
    for cmd_list in commands:
        command_str = " ".join(cmd_list)
        st.code(f"$ {command_str}", language="shell")
        try:
            result = subprocess.run(
                cmd_list,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                check=True
            )
            if result.stdout:
                st.text(result.stdout)
            if result.stderr:
                st.warning(result.stderr)
        except FileNotFoundError:
            st.error(f"Command not found: {cmd_list[0]}")
        except subprocess.CalledProcessError as e:
            st.error(f"Command failed with exit code {e.returncode}:")
            if e.stdout:
                st.text(e.stdout)
            if e.stderr:
                st.warning(e.stderr)
        except Exception as e:
            st.error(f"An unexpected error occurred: {e}")