import sys
import json
import os
import subprocess
import time
import json
import pandas as pd
from rdkit import Chem
from rdkit.Chem import Draw
from rdkit.Chem import Descriptors, Lipinski
from rich.console import Console
from rich.table import Table
from rich import box
from rdkit.Chem.Draw import rdMolDraw2D


### ---- 1️⃣ Compute RDKit Properties ---- ###
def compute_rdkit_properties(smiles):
    mol = Chem.MolFromSmiles(smiles)
    if mol is None:
        return {"Error": "Invalid SMILES string"}

    properties = {
        "Molecular Weight (MW)": Descriptors.MolWt(mol),
        "logP (Lipophilicity)": Descriptors.MolLogP(mol),
        "TPSA (Topological Polar Surface Area)": Descriptors.TPSA(mol),
        "Hydrogen Bond Donors (HBD)": Descriptors.NumHDonors(mol),
        "Hydrogen Bond Acceptors (HBA)": Descriptors.NumHAcceptors(mol),
        "Rotatable Bonds": Lipinski.NumRotatableBonds(mol),
        "Lipinski Rule of 5": (
            Descriptors.MolWt(mol) < 500 and
            Descriptors.MolLogP(mol) < 5 and
            Descriptors.NumHDonors(mol) <= 5 and
            Descriptors.NumHAcceptors(mol) <= 10
        )
    }
    return properties


from rdkit import Chem
from rdkit.Chem.Draw import rdMolDraw2D
from rdkit.Chem import rdDepictor

def generate_svg_image(smiles, filename="Protac.svg", image_size=(1200, 1200)):
    mol = Chem.MolFromSmiles(smiles)
    if mol is None:
        print("❌ Invalid SMILES string for SVG generation.")
        return

    rdDepictor.Compute2DCoords(mol)

    drawer = rdMolDraw2D.MolDraw2DSVG(image_size[0], image_size[1])
    opts = drawer.drawOptions()
    opts.bondLineWidth = 2
    opts.addAtomIndices = True

    drawer.DrawMolecule(mol)
    drawer.FinishDrawing()

    svg = drawer.GetDrawingText()
    with open(filename, "w", encoding="utf-8") as f:
        f.write(svg)

    print(f"✅ SVG image saved as {filename}")



### ---- 2️⃣ Submit SMILES to Deep-PK ---- ###
def submit_to_deep_pk(smiles):
    curl_timeout = int(os.environ.get("DEEPPK_CURL_TIMEOUT_SECONDS", "20"))
    curl_command = [
        "curl", "https://biosig.lab.uq.edu.au/deeppk/api/predict",
        "--silent", "--show-error", "--max-time", str(curl_timeout),
        "-X", "POST", "-i",
        "-F", f"smiles={smiles}",
        "-F", "pred_type=admet"
    ]

    try:
        result = subprocess.run(curl_command, capture_output=True, text=True, timeout=curl_timeout + 5)
        output = result.stdout

        job_id_start = output.find('{"job_id":')
        if job_id_start == -1:
            print("❌ Deep-PK submission failed!")
            return None

        job_id_json = output[job_id_start:]
        job_data = json.loads(job_id_json)
        job_id = job_data.get("job_id")

        if job_id:
            print(f"✅ Submitted to Deep-PK. Job ID: {job_id}")
            return job_id
        else:
            print("❌ Could not extract job ID.")
            return None

    except Exception as e:
        print(f"❌ Error submitting to Deep-PK: {e}")
        return None


### ---- 3️⃣ Retrieve ADMET Predictions ---- ###
def get_deep_pk_results(job_id, max_wait_time=3600, check_interval=30):
    start_time = time.time()
    curl_timeout = int(os.environ.get("DEEPPK_CURL_TIMEOUT_SECONDS", "20"))

    while True:
        try:
            curl_command = [
                "curl", "https://biosig.lab.uq.edu.au/deeppk/api/predict",
                "--silent", "--show-error", "--max-time", str(curl_timeout),
                "-X", "GET",
                "-F", f"job_id={job_id}"
            ]

            result = subprocess.run(curl_command, capture_output=True, text=True, timeout=curl_timeout + 5)
            output = result.stdout

            if '"status": "running"' in output:
                elapsed_time = time.time() - start_time
                if elapsed_time >= max_wait_time:
                    print("⏳ Timed out after 15 minutes.")
                    return {"Error": "Deep-PK job timed out"}

                print(f"⏳ Still processing... Retrying in {check_interval} seconds.")
                time.sleep(check_interval)
            else:
                if "<html" in output.lower() or "<!doctype html" in output.lower():
                    return {"Error": "Deep-PK returned an HTML error page"}
                print("✅ Results received!")
                return json.loads(output)

        except Exception as e:
            print(f"❌ Error retrieving Deep-PK results: {e}")
            return {"Error": str(e)}


### ---- 4️⃣ Parse & Organize Deep-PK Predictions ---- ###
def parse_deep_pk_predictions(json_data):
    if isinstance(json_data, str):
        json_data = json.loads(json_data)

    # Extract Deep-PK Predictions
    predictions_str = json_data.get("Deep-PK Predictions", "{}")

    try:
        predictions = json.loads(predictions_str).get("0", {})
    except json.JSONDecodeError:
        print("❌ Failed to parse Deep-PK JSON")
        return {}

    categorized_data = {
        "Absorption": {},
        "Distribution": {},
        "Metabolism": {},
        "Excretion": {},
        "Toxicology": {},
        "General Properties": {},
    }

    # Properly structure data
    for key, value in predictions.items():
        if "/" in key:
            category, param = key.split("/", 1)
            if category in categorized_data:
                categorized_data[category][param] = value

    return categorized_data


### ---- 5️⃣ Save Results to Organized CSV ---- ###
def save_to_csv(rdkit_data, categorized_data, filename="DeepPK_Predictions.csv"):
    rows = []

    # Add RDKit properties
    for param, prediction in rdkit_data.items():
        rows.append(["RDKit Properties", param, prediction, "-", "-"])

    # Add Deep-PK Predictions
    for category, data in categorized_data.items():
        for param, prediction in data.items():
            if "Prediction" in param:
                param_clean = param.replace(" Predictions", "")
                confidence_key = param_clean + " Probability"
                interpretation_key = param_clean + " Interpretation"

                confidence = data.get(confidence_key, "-")
                interpretation = data.get(interpretation_key, "-")

                rows.append([category, param_clean, prediction, confidence, interpretation])

    df = pd.DataFrame(rows, columns=["Category", "Parameter", "Prediction", "Confidence", "Interpretation"])
    df.to_csv(filename, index=False)
    print(f"✅ Data saved to {filename}")


### ---- 6️⃣ Display Results in Terminal (Formatted) ---- ###
def display_results(categorized_data):
    console = Console()

    section_colors = {
        "Absorption": "cyan",
        "Distribution": "blue",
        "Metabolism": "green",
        "Excretion": "magenta",
        "Toxicology": "red",
        "General Properties": "yellow"
    }

    for section, data in categorized_data.items():
        if not data:
            continue  

        table = Table(title=f"[{section_colors[section]}]{section}[/]", box=box.ROUNDED, highlight=True)
        table.add_column("Parameter", style="bold")
        table.add_column("Prediction", style="white")
        table.add_column("Confidence", style="yellow")
        table.add_column("Interpretation", style="dim")

        for param, prediction in data.items():
            if "Prediction" in param:
                param_clean = param.replace(" Predictions", "")
                confidence_key = param_clean + " Probability"
                interpretation_key = param_clean + " Interpretation"

                confidence = data.get(confidence_key, "-")
                interpretation = data.get(interpretation_key, "N/A")

                table.add_row(param_clean, str(prediction), str(confidence), interpretation)

        console.print(table)
        console.print("\n")


### ---- 7️⃣ Main Function ---- ###
def analyze_drug_properties(smiles):
    rdkit_results = compute_rdkit_properties(smiles)
    deep_pk_job_id = submit_to_deep_pk(smiles)

    if not deep_pk_job_id:
        return {"RDKit Properties": rdkit_results, "Deep-PK Error": "Submission failed"}

    max_wait_time = int(os.environ.get("DEEPPK_MAX_WAIT_SECONDS", "3600"))
    check_interval = int(os.environ.get("DEEPPK_CHECK_INTERVAL_SECONDS", "30"))
    deep_pk_results = get_deep_pk_results(
        deep_pk_job_id,
        max_wait_time=max_wait_time,
        check_interval=check_interval,
    )
    categorized_data = parse_deep_pk_predictions(deep_pk_results)

    display_results(categorized_data)
    save_to_csv(rdkit_results, categorized_data)

    return {
        "RDKit Properties": rdkit_results,
        "Deep-PK Predictions": deep_pk_results
    }




### **🔹 How We Get SMILES Input Now** ###
if __name__ == "__main__":
    if len(sys.argv) > 1:
        smiles_input = sys.argv[1]
    elif "SMILES_INPUT" in os.environ:
        smiles_input = os.environ["SMILES_INPUT"]
    else:
        print("Error: No SMILES string provided. Exiting.")
        sys.exit(1)

    print(f"Running analysis for SMILES: {smiles_input}")

    # Generate the SVG image
    generate_svg_image(smiles_input)


    # Continue with the original workflow
    results = analyze_drug_properties(smiles_input)

    # Save results to JSON
    output_filename = "DeepPK_Predictions.json"
    with open(output_filename, "w", encoding="utf-8") as file:
        json.dump(results, file, indent=4)

    print(f"JSON saved to {output_filename}")




# ### ---- 8️⃣ Example Usage ---- ###
# if __name__ == "__main__":
#     smiles_input = "COC(=O)N[C@H](C(=O)NN(Cc1ccc(-c2ccccn2)cc1)C[C@H](O)[C@H](Cc1ccccc1)NC(=O)[C@@H](NC(=O)ON1CCC(C#Cc2ccc(Cc3cccc4c3C(=O)N([C@H]3CCC(=O)NC3=O)C4=O)cn2)CC1)C(C)(C)C)C(C)(C)C"
#     results = analyze_drug_properties(smiles_input)
#     # Save the results to a JSON file for JSONANALYZER.py
#     output_filename = "DeepPK_Predictions.json"
#     with open(output_filename, "w", encoding="utf-8") as file:
#         json.dump(results, file, indent=4)

#     print(f"✅ JSON saved to {output_filename}")
#     print(json.dumps(results, indent=4))



###Changes to theoretically make a call like

#####         python3 SmilesDrugProps.py "COC(=O)N[C@H](C(=O)NN(Cc1ccc(-c2ccccn2)cc1)C[C@H](O)..."


