from __future__ import annotations

import csv
import io
import os
import re
import shutil
import subprocess
import tempfile

import pandas as pd
from flask import Request
from rdkit import Chem
from rdkit.Chem import AllChem

from .chemistry import normalize_attachment_smiles


_LINKER_PATTERNS = [
    (re.compile(r"\[\*:1\].*\[\*:2\]"), 10),
    (re.compile(r"\[R1\].*\[R2\]"), 9),
    (re.compile(r"\[\*:\s*1\]"), 6),
    (re.compile(r"\[\*:\s*2\]"), 6),
]


def safe_str(value: object) -> str:
    if value is None:
        return ""
    try:
        return str(value).strip()
    except Exception:
        return ""


def read_csv_smart(file_storage) -> pd.DataFrame:
    try:
        return pd.read_csv(file_storage, sep=None, engine="python")
    except Exception:
        file_storage.stream.seek(0)
        return pd.read_csv(file_storage, sep="\t")


def detect_linker_smiles_column(df: pd.DataFrame) -> str | None:
    best_col = None
    best_score = -1
    for col in df.columns:
        score = 0
        col_lower = str(col).lower()
        if "smiles" in col_lower:
            score += 2
        if "smiles_r" in col_lower or "smilesr" in col_lower:
            score += 2
        if "inchi" in col_lower:
            score -= 3

        sample = df[col].dropna().astype(str).head(25).tolist()
        for value in sample:
            for pattern, weight in _LINKER_PATTERNS:
                if pattern.search(value.strip()):
                    score += weight
            if len(value) > 3 and " " not in value and any(ch in value for ch in "[]=#()*"):
                score += 1

        if score > best_score:
            best_score = score
            best_col = str(col)

    if best_score < 5:
        return None
    return best_col


def detect_name_column(df: pd.DataFrame, smiles_col: str | None) -> str | None:
    candidates: list[tuple[int, str]] = []
    for col in df.columns:
        col_str = str(col)
        if col_str == smiles_col:
            continue
        lower = col_str.lower()
        score = 0
        if "name" in lower:
            score += 10
        if "compound" in lower:
            score += 8
        if lower == "id" or lower.endswith("id") or " id" in lower:
            score += 7
        if "title" in lower:
            score += 6
        if "smiles" in lower or "inchi" in lower or "formula" in lower:
            score -= 8
        if len(df[col].dropna()) > 0:
            score += 1
        candidates.append((score, col_str))
    if not candidates:
        return None
    candidates.sort(reverse=True, key=lambda item: item[0])
    best_score, best_col = candidates[0]
    return best_col if best_score > 0 else None


def inspect_linker_csv(file_storage) -> dict[str, object]:
    df = read_csv_smart(file_storage)
    if df.empty:
        raise ValueError("CSV is empty")
    smiles_col = detect_linker_smiles_column(df)
    name_col = detect_name_column(df, smiles_col)
    preview = df.head(10).fillna("").astype(str).to_dict(orient="records")
    return {
        "columns": [str(col) for col in df.columns],
        "preview_rows": preview,
        "suggested_smiles_col": smiles_col or "",
        "suggested_name_col": name_col or "",
    }


def parse_structure_input(smiles_text: str, file_obj) -> tuple[str, str]:
    mol = None
    if smiles_text.strip():
        mol = Chem.MolFromSmiles(smiles_text.strip())
        if mol is None:
            raise ValueError("Invalid SMILES")
    elif file_obj:
        with tempfile.TemporaryDirectory() as tmp_dir:
            temp_path = os.path.join(tmp_dir, file_obj.filename or "upload")
            file_obj.save(temp_path)
            mol = _rdkit_from_uploaded_file(temp_path)
            if mol is None:
                obabel_smiles = _openbabel_to_smiles(temp_path)
                if obabel_smiles:
                    mol = Chem.MolFromSmiles(obabel_smiles)
            if mol is None:
                raise ValueError("Could not parse this structure file with RDKit/OpenBabel.")
    else:
        raise ValueError("Provide either structure_file or smiles")

    try:
        AllChem.Compute2DCoords(mol)
    except Exception:
        pass
    return Chem.MolToMolBlock(mol), Chem.MolToSmiles(mol, canonical=True)


def _rdkit_from_uploaded_file(file_path: str):
    ext = os.path.splitext(file_path)[1].lower().lstrip(".")
    if ext == "mol":
        return Chem.MolFromMolFile(file_path, sanitize=True, removeHs=False)
    if ext == "sdf":
        supplier = Chem.SDMolSupplier(file_path, sanitize=True, removeHs=False)
        return next((mol for mol in supplier if mol is not None), None)
    if ext == "mol2":
        return Chem.MolFromMol2File(file_path, sanitize=True, removeHs=False)
    if ext in {"smi", "smiles", "txt"}:
        with open(file_path, "r", encoding="utf-8", errors="ignore") as handle:
            smiles = handle.read().strip().split()[0]
        return Chem.MolFromSmiles(smiles)
    if ext in {"pdb", "pdbqt"}:
        return Chem.MolFromPDBFile(file_path, sanitize=False, removeHs=False)
    return None


def _openbabel_to_smiles(file_path: str) -> str | None:
    obabel = shutil.which("obabel")
    if not obabel:
        return None
    ext = os.path.splitext(file_path)[1].lower().lstrip(".")
    try:
        output = subprocess.check_output(
            [obabel, f"-i{ext}", file_path, "-osmi"],
            stderr=subprocess.STDOUT,
            text=True,
        ).strip()
    except Exception:
        return None
    if not output:
        return None
    return output.split()[0]


def read_name_smiles_csv(file_storage) -> list[tuple[int, str, str]]:
    text = file_storage.read().decode("utf-8-sig")
    sample = text[:2048]
    try:
        dialect = csv.Sniffer().sniff(sample, delimiters=",;\t")
    except Exception:
        dialect = csv.get_dialect("excel")

    reader = csv.DictReader(io.StringIO(text), dialect=dialect)
    if not reader.fieldnames:
        raise ValueError("CSV has no headers")

    field_map = {field.strip().lower(): field.strip() for field in reader.fieldnames}
    if "name" not in field_map or "smiles" not in field_map:
        raise ValueError("CSV must have headers NAME and SMILES")

    rows = []
    for row_number, row in enumerate(reader, start=2):
        name = safe_str(row.get(field_map["name"]))
        smiles = safe_str(row.get(field_map["smiles"]))
        if not name and not smiles:
            continue
        rows.append((row_number, name, normalize_attachment_smiles(smiles)))
    return rows


def to_csv_string(header: list[str], rows: list[tuple | list]) -> str:
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(header)
    for row in rows:
        writer.writerow(row)
    return output.getvalue()


def get_smiles_input(request: Request, field: str) -> str:
    value = safe_str(request.form.get(field))
    if value:
        return value
    file_obj = request.files.get(field)
    if not file_obj:
        return ""
    text = file_obj.read().decode("utf-8-sig", errors="replace")
    for line in text.splitlines():
        stripped = line.strip()
        if stripped and not stripped.startswith("#"):
            return stripped.split()[0]
    return ""
