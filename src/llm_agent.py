import json
import time
from bs4 import BeautifulSoup
from dotenv import load_dotenv
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from together import Together

load_dotenv()

def extract_json_from_text(raw_text):
    try:
        start = raw_text.find('{')
        end = raw_text.rfind('}') + 1
        if start == -1 or end == 0: return None
        return json.loads(raw_text[start:end])
    except Exception as e:
        print(f"Error parsing LLM JSON: {e}")
        return None

def extract_form_fields_from_url(driver):
    """
    Uses the PASSED-IN driver to handle iFrames and Shadow DOM.
    It does NOT create its own driver.
    """
    print(f"Attempting to extract fields from page: {driver.title}")
    
    try:
        WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.TAG_NAME, "body")))
    except Exception as e:
        print(f"Page body did not load in time: {e}")
        return []

    js_script = """
    function getFormFields(element) {
        let fields = [];
        element.querySelectorAll('input, select, textarea').forEach(el => {
            if (el.type === 'submit' || el.type === 'button' || el.type === 'reset') return;
            if (el.id) fields.push(el.id);
            else if (el.name) fields.push(el.name);
        });
        element.querySelectorAll('*').forEach(el => {
            if (el.shadowRoot) {
                fields = fields.concat(getFormFields(el.shadowRoot));
            }
        });
        return fields;
    }
    return getFormFields(document);
    """
    try:
        all_fields = driver.execute_script(js_script)
        all_fields = list(set(f for f in all_fields if f)) # Remove empty and duplicate fields
        if all_fields: return all_fields

        iframes = driver.find_elements(By.TAG_NAME, 'iframe')
        for frame in iframes:
            try:
                driver.switch_to.frame(frame)
                time.sleep(1)
                iframe_fields = driver.execute_script(js_script)
                driver.switch_to.default_content()
                iframe_fields = list(set(f for f in iframe_fields if f))
                if iframe_fields: return iframe_fields
            except Exception:
                driver.switch_to.default_content()
        return []
    except Exception as e:
        print(f"An error occurred during field extraction: {e}")
        return []

def get_mapping_from_instruction(instruction, form_fields, file_columns):
    prompt = f"""
You are an intelligent mapping agent. Your task is to map HTML form field identifiers to file column headers based on a user's instruction and the number of rows to fill.
User Instruction: "{instruction}"
Available Form Fields: {json.dumps(form_fields, indent=2)}
Available File Columns: {json.dumps(file_columns, indent=2)}
Only return a valid JSON object in the format: {{"field_mapping": {{"form_field_id_1": "column_name_1"}}, "row_to_fill": 5}}
"""
    client = Together()
    try:
        response = client.chat.completions.create(
            model="meta-llama/Llama-3-8b-chat-hf",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.0
        )
        raw_text = response.choices[0].message.content
        return extract_json_from_text(raw_text)
    except Exception as e:
        print(f"Error while calling LLM for mapping: {e}")
        return None