import pandas as pd
from llm_agent import get_mapping_from_instruction
from selenium_runner import run_agent_with_mapping


instruction = input("What do you want agent to do? ")

mapping = get_mapping_from_instruction(instruction)

if mapping:
    df = pd.read_csv(mapping["file_path"])
    max_rows = len(df)

    if mapping["row_to_fill"] > max_rows:
        mapping["row_to_fill"] = max_rows
        print(f"Row limit exceeded. Adjusted to {max_rows}")
    else:
        run_agent_with_mapping(mapping)

else:
    print("could not understand the task.")