from __future__ import annotations

import csv
import json
import secrets
from datetime import datetime
from pathlib import Path

from rdkit import Chem
from rdkit.Chem import Crippen, Descriptors, Lipinski, QED, rdMolDescriptors

from .paths import ADMET_REPORTS_DIR


def _ensure_reports_dir() -> None:
    ADMET_REPORTS_DIR.mkdir(parents=True, exist_ok=True)


def _molecule_from_input(smiles: str = "", mol_block: str = ""):
    if mol_block and mol_block.strip():
        mol = Chem.MolFromMolBlock(mol_block, sanitize=True)
        if mol is not None:
            return mol
    if smiles and smiles.strip():
        mol = Chem.MolFromSmiles(smiles.strip())
        if mol is not None:
            return mol
    raise ValueError("Valid SMILES or MOL block required")


def _lipinski_violations(props: dict[str, float | int]) -> int:
    violations = 0
    if float(props["molecular_weight"]) > 500:
        violations += 1
    if float(props["logp"]) > 5:
        violations += 1
    if int(props["hbd"]) > 5:
        violations += 1
    if int(props["hba"]) > 10:
        violations += 1
    return violations


def _protac_warnings(props: dict[str, float | int]) -> list[str]:
    warnings: list[str] = []
    if float(props["molecular_weight"]) > 900:
        warnings.append("Very high molecular weight for a PROTAC-like molecule.")
    if int(props["rotatable_bonds"]) > 15:
        warnings.append("High rotatable bond count may reduce conformational efficiency.")
    if float(props["tpsa"]) > 180:
        warnings.append("High TPSA may reduce passive permeability.")
    if float(props["logp"]) > 8:
        warnings.append("High LogP may indicate solubility or exposure risk.")
    if int(props["hbd"]) > 8:
        warnings.append("High hydrogen bond donor count may impair permeability.")
    if int(props["hba"]) > 15:
        warnings.append("High hydrogen bond acceptor count may impair permeability.")
    if int(props["formal_charge"]) != 0:
        warnings.append("Non-zero formal charge may affect permeability and formulation.")
    return warnings


def calculate_properties(smiles: str = "", mol_block: str = "") -> dict[str, float | int]:
    mol = _molecule_from_input(smiles=smiles, mol_block=mol_block)
    props: dict[str, float | int] = {
        "molecular_weight": round(Descriptors.MolWt(mol), 3),
        "exact_molecular_weight": round(rdMolDescriptors.CalcExactMolWt(mol), 5),
        "logp": round(Crippen.MolLogP(mol), 3),
        "tpsa": round(rdMolDescriptors.CalcTPSA(mol), 3),
        "hbd": int(Lipinski.NumHDonors(mol)),
        "hba": int(Lipinski.NumHAcceptors(mol)),
        "rotatable_bonds": int(Lipinski.NumRotatableBonds(mol)),
        "ring_count": int(rdMolDescriptors.CalcNumRings(mol)),
        "heavy_atom_count": int(rdMolDescriptors.CalcNumHeavyAtoms(mol)),
        "formal_charge": int(Chem.GetFormalCharge(mol)),
        "qed": round(float(QED.qed(mol)), 4),
        "smiles": Chem.MolToSmiles(mol, isomericSmiles=True),
    }
    props["lipinski_violations"] = _lipinski_violations(props)
    return props


def create_admet_report(smiles: str = "", mol_block: str = "") -> dict[str, object]:
    props = calculate_properties(smiles=smiles, mol_block=mol_block)
    warnings = _protac_warnings(props)
    _ensure_reports_dir()

    run_id = datetime.utcnow().strftime("%Y%m%d_%H%M%S") + "_" + secrets.token_hex(4)
    json_path = ADMET_REPORTS_DIR / f"{run_id}.json"
    csv_path = ADMET_REPORTS_DIR / f"{run_id}.csv"

    payload = {
        "success": True,
        "descriptors": props,
        "properties": props,
        "warnings": warnings,
        "files": {
            "csv": f"/api/admet/download/{csv_path.name}",
            "json": f"/api/admet/download/{json_path.name}",
            "pdf": None,
        },
        "report_id": run_id,
    }

    json_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    with csv_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(["property", "value"])
        for key, value in props.items():
            writer.writerow([key, value])
        writer.writerow(["warnings", " | ".join(warnings)])

    return payload


def get_admet_file(filename: str) -> Path:
    _ensure_reports_dir()
    candidate = (ADMET_REPORTS_DIR / filename).resolve()
    if ADMET_REPORTS_DIR.resolve() not in candidate.parents or not candidate.exists():
        raise FileNotFoundError(filename)
    return candidate
