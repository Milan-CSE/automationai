from together import Together
from dotenv import load_dotenv
import os
import json
import re

load_dotenv()  # Load variables from .env

def extract_json_from_text(raw_text):
    try:
        start = raw_text.index('{')
        end = raw_text.rindex('}') + 1
        json_block = raw_text[start:end]
        return json.loads(json_block)
    except Exception as e:
        print("Error parsing LLM JSON:", str(e))
        return None


def get_mapping_from_instruction(instruction):
    prompt = f"""
You are a smart AI agent. Based on the instruction below, return a valid JSON object that contains:

- file_path: a full path to the CSV file
- field_mapping: map HTML form field IDs (name, date, time) to CSV column headers
- row_to_fill: how many rows to fill, based on the user's instruction

Instruction:
{instruction}

Only return valid JSON in this format:

{{
  "file_path": "D:/Courses/Intel_AI_Course/Project_1/attendance_fillup_agent/data/attendance_data.csv",
  "field_mapping": {{
    "name": "Name",
    "date": "Date",
    "time": "Time"
  }},
  "row_to_fill": 3
}}
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
        print("=== RAW LLM OUTPUT ===")
        print(raw_text)

        #find_json = re.search(r"```json\s*(\{.*?})\s*```", raw_text, re.DOTALL) Replacing this with this:

        return extract_json_from_text(raw_text)



        # find_json:
         #   json_block = find_json.group(1)
          #  return json.loads(json_block)
        #else:
         #   print("No valid JSON found.")
          #  return None

    except Exception as e:
        print("Error while calling LLM", e)
        return None

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









