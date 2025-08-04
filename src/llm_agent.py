from together import Together
from dotenv import load_dotenv
import os
import json
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from bs4 import BeautifulSoup
import time

load_dotenv()

def extract_json_from_text(raw_text):
    """Safely extracts a JSON object from a string."""
    try:
        # Use a more robust method to find the JSON block
        start = raw_text.find('{')
        end = raw_text.rfind('}') + 1
        if start == -1 or end == 0:
            print("No JSON object found in the text.")
            return None
        json_block = raw_text[start:end]
        return json.loads(json_block)
    except Exception as e:
        print(f"Error parsing LLM JSON: {e}")
        return None

def extract_form_fields_from_url(driver):
    """
    Uses Selenium and BeautifulSoup to extract input, select, and textarea fields from a live URL.
    Returns a list of field 'id' or 'name' attributes.
    """
    CHROMEDRIVER_PATH = "D:/Courses/Intel_AI_Course/Project_1/attendance_fillup_agent/chromedriver.exe" # Make sure this path is correct
    service = Service(CHROMEDRIVER_PATH)
    options = webdriver.ChromeOptions()
    options.add_argument('--headless') # Run in the background
    options.add_argument('--disable-gpu')
    driver = webdriver.Chrome(service=service, options=options)

    try:
        page_source = driver.page_source
        soup = BeautifulSoup(page_source, 'html.parser')

        fields = set()
        # Find all relevant form elements
        form_elements = soup.find_all(['input', 'textarea', 'select'])

        for element in form_elements:
            # Prioritize 'id', then 'name', as the identifier
            field_id = element.get('id')
            if field_id and field_id not in ['submit', 'button']: # Ignore submit buttons
                 fields.add(field_id)
            else:
                field_name = element.get('name')
                if field_name:
                    fields.add(field_name)

        return list(fields)
    except Exception as e:
        print(f"Error extracting form fields: {e}")
        return []


def get_mapping_from_instruction(instruction, form_fields, file_columns):
    """
    Generates a mapping between form fields and file columns using an LLM.
    """
    prompt = f"""
You are an intelligent mapping agent. Your task is to map HTML form field identifiers to CSV/Excel column headers based on a user's instruction.

User Instruction: "{instruction}"

Available Form Fields:
{json.dumps(form_fields, indent=2)}

Available File Columns:
{json.dumps(file_columns, indent=2)}

Based on the instruction and the provided lists, create a JSON object that maps the form fields to the most appropriate file columns. The keys of the JSON object must be the form field identifiers and the values must be the corresponding column names from the file.

Only return a valid JSON object in the following format. Do not add any explanations, notes, or apologies.

Example Output Format:
{{
  "field_mapping": {{
    "form_field_id_1": "corresponding_column_name_1",
    "form_field_id_2": "corresponding_column_name_2"
  }}
}}
"""
    client = Together()
    try:
        response = client.chat.completions.create(
            model="meta-llama/Llama-3-8b-chat-hf", # Using a reliable model
            messages=[{"role": "user", "content": prompt}],
            temperature=0.0 # Be deterministic for mapping
        )

        raw_text = response.choices[0].message.content
        print("=== RAW LLM OUTPUT FOR MAPPING ===")
        print(raw_text)

        return extract_json_from_text(raw_text)

    except Exception as e:
        print(f"Error while calling LLM for mapping: {e}")
        return None

# The functions ask_llm_what_to_do and solve_row_error can remain as they are,
# as they are for post-processing failed rows and their logic is still applicable.
# (Code for these functions is omitted for brevity but should be kept from your original file)

# If some row failed row to fillup and get error

def ask_llm_what_to_do(failed_rows):
    failed_data = json.dumps(failed_rows, indent=2)
    prompt = f"""You are an AI decision-maker agent. Some rows failed during form submission.

    Here are failed rows:
    {failed_data}
    
    What should I do next?
    
    Reply ONLY in this format (do not explain anything):
    
    {{
        "decisions": [
        {{ "index": 3, "action": "retry" }}
        If retry failed use this format :
        {{ "index": 3, "action": "skip" }}
            ]
    }}
    Do not add any explanation or notes. Only return a JSON object in the above format.
    """
    client = Together()

    try:
        response = client.chat.completions.create(
            model="deepseek-ai/DeepSeek-R1-Distill-Llama-70B-free",
            messages= [{
                "role": "user",
                "content": prompt
            }]
        )

        raw_text = response.choices[0].message.content
        print("----RAW JSON LLM ")
        print(raw_text)

        return extract_json_from_text(raw_text)


    except Exception as e:
        print("Error while re-fill failed row", e)
        return None

# Human_in_the_loop

def solve_row_error(failed_rows):
    failed_data = json.dumps(failed_rows, indent=2)

    prompt = f"""
    You are an AI agent for retrying to fill each failed row that are failed during form submission. 
    For that you asking human what to do for that failed_rows and trying to re_fill.

    Here are failed rows:
    {failed_data}
    
    What should you do next?
    
    Reply only in this formate and do not explain anything else:
    {{
        "action": "Ask-User"
    }}
    
    Do not add anything else reply only in above JSON formate.
    """
    client = Together()

    try:

        response = client.chat.completions.create(
                model="deepseek-ai/DeepSeek-R1-Distill-Llama-70B-free",
                messages=[
                    {
                        "role": "user",
                        "content": prompt
                    }
                ]
            )

        raw_text = response.choices[0].message.content
        print("----retrying_text-----")
        print(raw_text)

        return extract_json_from_text(raw_text)


    except Exception as e:
        print("Error while re-fill failed row with human reply.", e)
        return None









