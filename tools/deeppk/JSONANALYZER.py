import json
import pandas as pd

def safe_parse_json(nested_json_str):
    """
    Attempts to clean and parse a nested JSON string safely.
    """
    try:
        return json.loads(nested_json_str)
    except json.JSONDecodeError as e:
        print(f"❌ JSON Parsing Error: {e}")
        return None

def process_deep_pk_results(json_data):
    try:
        print("✅ Successfully loaded main JSON.")

        # Extract nested JSON from "Deep-PK Predictions"
        deep_pk_predictions_raw = json_data.get("Deep-PK Predictions", "{}")

        if isinstance(deep_pk_predictions_raw, dict):
            deep_pk_predictions = deep_pk_predictions_raw
            preview = json.dumps(deep_pk_predictions_raw)[:500]
        else:
            preview = str(deep_pk_predictions_raw)[:500]
            deep_pk_predictions = safe_parse_json(deep_pk_predictions_raw)

        # Debugging: Print a preview
        print("🔍 Raw Deep-PK Predictions (Preview):", preview)

        # Ensure Deep-PK Predictions is a valid dictionary
        
        if deep_pk_predictions is None:
            print("❌ Failed to clean and parse 'Deep-PK Predictions'.")
            return

        deep_pk_predictions = deep_pk_predictions.get("0", {})

        print("✅ Successfully parsed Deep-PK Predictions.")

        # Define categories
        categories = {
            "Absorption": [],
            "Distribution": [],
            "Metabolism": [],
            "Excretion": [],
            "Toxicology": [],
            "General Properties": []
        }

        # Classify each key-value pair
        for key, value in deep_pk_predictions.items():
            if "Absorption" in key:
                categories["Absorption"].append((key, value))
            elif "Distribution" in key:
                categories["Distribution"].append((key, value))
            elif "Metabolism" in key:
                categories["Metabolism"].append((key, value))
            elif "Excretion" in key:
                categories["Excretion"].append((key, value))
            elif "Toxicity" in key:
                categories["Toxicology"].append((key, value))
            elif "General Properties" in key:
                categories["General Properties"].append((key, value))

        # Convert to DataFrame
        rows = []
        for category, entries in categories.items():
            for key, value in entries:
                rows.append([category, key, value])

        df = pd.DataFrame(rows, columns=["Category", "Parameter", "Value"])

        # Save to CSV
        csv_filename = "DeepPK_Cleaned_Output.csv"
        df.to_csv(csv_filename, index=False)

        print(f"✅ Processed data saved to {csv_filename}")

    except json.JSONDecodeError as e:
        print(f"❌ JSON Parsing Error: {e}")

# -----------------------------------
# 🔹 Load JSON from SmilesDrugProps.py
# -----------------------------------
json_file = "DeepPK_Predictions.json"

try:
    with open(json_file, "r", encoding="utf-8") as file:
        deep_pk_json = json.load(file)

    print("✅ Successfully loaded JSON from SmilesDrugProps.py")

    # Process the JSON data
    process_deep_pk_results(deep_pk_json)

except FileNotFoundError:
    print(f"❌ Error: {json_file} not found. Make sure SmilesDrugProps.py ran successfully.")
except json.JSONDecodeError as e:
    print(f"❌ JSON Parsing Error: {e}")
