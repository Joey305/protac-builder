#!/usr/bin/env python3
"""
PrepFiles.py

Clean rewrite of the original workflow:
1. Ensure Python dependencies are available
2. Ensure Open Babel CLI (obabel) is available
3. Filter Ligase.pdb and Warhead.pdb by user-selected chains
4. Extract ligand HETATM records from Protac_params.txt head codes
5. Convert extracted ligand PDBs to SDF using obabel
6. Merge filtered proteins with extracted ligands into output structure PDBs
7. Display SDFs with atom labels and allow anchor atom updates in Protac_params.txt
"""

from __future__ import annotations

import importlib
import json
import os
import shutil
import subprocess
import sys
import webbrowser
from pathlib import Path
from typing import Iterable


# =========================
# Dependency management
# =========================

def ensure_python_package(pkg_name: str, import_name: str | None = None, pip_name: str | None = None):
    """Require a Python package without mutating a scientist's environment."""
    import_name = import_name or pkg_name
    pip_name = pip_name or pkg_name

    try:
        return importlib.import_module(import_name)
    except ImportError:
        sys.exit(
            f"❌ Required Python package '{pip_name}' is missing.\n"
            f"Install it in this environment, then rerun: {sys.executable} -m pip install {pip_name}"
        )


def ensure_executable(exe_name: str, conda_package: str | None = None) -> str:
    """
    Ensure a command-line executable exists on PATH.
    """
    path = shutil.which(exe_name)
    if path:
        print(f"✅ Found executable '{exe_name}' at: {path}")
        return path

    print(f"⚠️ Executable '{exe_name}' not found on PATH.")

    sys.exit(
        f"❌ Required executable '{exe_name}' is missing.\n"
        f"Install it with:\n"
        f"    conda install -c conda-forge {conda_package or exe_name}\n"
    )


py3Dmol = None
Chem = None
OBABEL = None


def initialize_runtime_dependencies() -> None:
    """Load optional runtime tooling only when preparation is actually run."""
    global py3Dmol, Chem, OBABEL
    py3Dmol = ensure_python_package("py3Dmol")
    Chem = ensure_python_package("rdkit", import_name="rdkit.Chem")
    OBABEL = ensure_executable("obabel", conda_package="openbabel")


# =========================
# File helpers
# =========================

def require_file(path: str | Path) -> Path:
    p = Path(path)
    if not p.exists():
        sys.exit(f"❌ Required file not found: {p}")
    return p


def read_lines(path: str | Path) -> list[str]:
    with open(path, "r") as fh:
        return fh.readlines()


def write_lines(path: str | Path, lines: Iterable[str]) -> None:
    with open(path, "w") as fh:
        fh.writelines(lines)


def normalize_chain_input(text: str) -> list[str]:
    chains = [c.strip() for c in text.split(",") if c.strip()]
    if not chains:
        sys.exit("❌ No chains were provided.")
    return chains


# =========================
# Protac params parsing
# =========================

def parse_params_file(params_file: str | Path):
    """
    Parses Protac_params.txt and returns:
    - first_head, second_head
    - structures list
    - chains list
    - anchor_atoms list
    - original lines
    """
    lines = read_lines(params_file)

    heads: list[str] = []
    structures: list[str] = []
    chains: list[str] = []
    anchor_atoms: list[int] = []

    for raw in lines:
        line = raw.strip()
        if not line or ":" not in line:
            continue

        key, value = line.split(":", 1)
        parts = value.strip().split()

        if key == "Heads":
            heads = parts
        elif key == "Structures":
            structures = parts
        elif key == "Chains":
            chains = parts
        elif key == "Anchor atoms":
            if any(value.upper() in {"PENDING", "UNSELECTED"} for value in parts):
                continue
            try:
                anchor_atoms = [int(x) for x in parts]
            except ValueError:
                sys.exit("❌ Could not parse integer anchor atoms from Protac_params.txt")

    if len(heads) < 2:
        sys.exit("❌ Could not extract two head entries from Protac_params.txt")

    first_head = heads[0].split(".")[0]
    second_head = heads[1].split(".")[0]

    return first_head, second_head, structures, chains, anchor_atoms, lines


def update_anchor_atoms_in_params(params_file: str | Path, original_lines: list[str], anchor_atoms: list[int]) -> None:
    new_lines = []
    replaced = False

    for line in original_lines:
        if line.startswith("Anchor atoms:"):
            new_lines.append(f"Anchor atoms: {' '.join(map(str, anchor_atoms))}\n")
            replaced = True
        else:
            new_lines.append(line)

    if not replaced:
        new_lines.append(f"\nAnchor atoms: {' '.join(map(str, anchor_atoms))}\n")

    write_lines(params_file, new_lines)


def load_manifest(path: str | Path = "package_manifest.json") -> dict:
    manifest_path = require_file(path)
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        sys.exit(f"❌ Could not read package manifest: {exc}")
    if manifest.get("schema_version") != 1:
        sys.exit(f"❌ Unsupported package manifest schema: {manifest.get('schema_version')!r}")
    if manifest.get("package_type") != "prosettac":
        sys.exit("❌ package_manifest.json is not a PRosettaC package.")
    for component_name in ("e3", "warhead"):
        component = manifest.get(component_name)
        required = ("pdb_residue_name", "pdb_residue_number", "head_sdf")
        if not isinstance(component, dict) or any(not str(component.get(key, "")).strip() for key in required):
            sys.exit(f"❌ Manifest {component_name} structural metadata is incomplete.")
    return manifest


# =========================
# PDB processing
# =========================

def filter_pdb_by_chains(input_file: str | Path, selected_chains: list[str], include_hetatm: bool = False) -> list[str]:
    filtered_lines = []
    with open(input_file, "r") as pdb_file:
        for line in pdb_file:
            if line.startswith("ATOM") or (include_hetatm and line.startswith("HETATM")):
                chain = line[21].strip()
                if chain in selected_chains:
                    filtered_lines.append(line)
    return filtered_lines


def extract_hetatm_by_codes(input_file: str | Path, codes: list[str]) -> list[str]:
    filtered_lines = []
    target_codes = {c.strip() for c in codes}

    with open(input_file, "r") as pdb_file:
        for line in pdb_file:
            if line.startswith("HETATM"):
                atom_code = line[17:20].strip()
                if atom_code in target_codes:
                    filtered_lines.append(line)

    return filtered_lines


def extract_hetatm_by_identity(input_file: str | Path, identity: dict) -> list[str]:
    """Extract exactly one PDB residue using explicit manifest structural IDs."""
    expected = (
        str(identity.get("pdb_residue_name") or "").strip().upper(),
        str(identity.get("pdb_chain") or "").strip(),
        str(identity.get("pdb_residue_number") or "").strip(),
        str(identity.get("pdb_insertion_code") or "").strip(),
    )
    selected: list[str] = []
    other_groups: set[tuple[str, str, str, str]] = set()
    with open(input_file, "r") as pdb_file:
        for line in pdb_file:
            if not line.startswith("HETATM") or len(line) < 27:
                continue
            observed = (line[17:20].strip().upper(), line[21].strip(), line[22:26].strip(), line[26].strip())
            if observed == expected:
                selected.append(line)
            else:
                other_groups.add(observed)
    if not selected:
        sys.exit(
            "❌ Expected bound residue was not found: "
            f"{expected[0]} / chain {expected[1] or '[blank]'} / residue {expected[2]}{expected[3]}"
        )
    return selected


def detect_chains(pdb_file: str | Path) -> list[str]:
    chains = set()
    with open(pdb_file, "r") as file:
        for line in file:
            if line.startswith("ATOM") or line.startswith("HETATM"):
                chain = line[21].strip()
                if chain:
                    chains.add(chain)
    return sorted(chains)


def get_last_residue_number(pdb_lines: list[str], target_chain: str | None = None) -> int:
    max_residue_number = 0
    for line in pdb_lines:
        if line.startswith("ATOM") or line.startswith("HETATM"):
            if target_chain is None or line[21] == target_chain:
                residue_text = line[22:26].strip()
                if residue_text:
                    residue_number = int(residue_text)
                    max_residue_number = max(max_residue_number, residue_number)
    return max_residue_number


def renumber_residues(pdb_lines: list[str], start_residue: int, target_chain: str | None = None) -> list[str]:
    residue_map: dict[int, int] = {}
    current_residue = start_residue
    new_lines: list[str] = []

    for line in pdb_lines:
        if line.startswith("ATOM") or line.startswith("HETATM"):
            if target_chain is None or line[21] == target_chain:
                residue_number = int(line[22:26].strip())
                if residue_number not in residue_map:
                    residue_map[residue_number] = current_residue
                    current_residue += 1
                new_residue = residue_map[residue_number]
                new_line = line[:22] + f"{new_residue:4d}" + line[26:]
                new_lines.append(new_line)
            else:
                new_lines.append(line)
        else:
            new_lines.append(line)

    return new_lines


def adjust_dimer_residues_inplace(pdb_file: str | Path) -> Path:
    """
    If at least two chains are present, renumber the second chain so its residue
    numbering starts after the first chain ends.
    """
    pdb_file = Path(pdb_file)
    chains = detect_chains(pdb_file)
    if len(chains) < 2:
        return pdb_file

    primary_chain, secondary_chain = chains[:2]
    pdb_lines = read_lines(pdb_file)
    first_chain_last = get_last_residue_number(pdb_lines, primary_chain)
    new_pdb_lines = renumber_residues(pdb_lines, first_chain_last + 1, secondary_chain)
    write_lines(pdb_file, new_pdb_lines)
    return pdb_file


def force_chain_assignment(pdb_lines: list[str], target_chain: str) -> list[str]:
    processed_lines = []
    for line in pdb_lines:
        if line.startswith("ATOM") or line.startswith("HETATM"):
            new_line = line[:21] + target_chain + line[22:]
            processed_lines.append(new_line)
        else:
            processed_lines.append(line)
    return processed_lines


def merge_pdb_files(protein_file: str | Path, ligand_file: str | Path, output_file: str | Path, target_chain: str) -> None:
    protein_file = adjust_dimer_residues_inplace(protein_file)

    protein_lines = force_chain_assignment(read_lines(protein_file), target_chain)
    last_residue_number = get_last_residue_number(protein_lines)

    ligand_lines = force_chain_assignment(read_lines(ligand_file), target_chain)
    ligand_lines = renumber_residues(ligand_lines, last_residue_number + 1)

    write_lines(output_file, protein_lines + ligand_lines)
    print(f"✅ Merged PDB written: {output_file}")


# =========================
# Open Babel conversion
# =========================

def run_obabel(input_pdb: str | Path, output_sdf: str | Path) -> None:
    command = [OBABEL, str(input_pdb), "-O", str(output_sdf)]
    try:
        subprocess.run(command, check=True)
    except subprocess.CalledProcessError as e:
        sys.exit(f"❌ Open Babel conversion failed: {e}")


# =========================
# Viewer / anchor editing
# =========================

def show_molecule(sdf_file: str | Path) -> None:
    mols = Chem.SDMolSupplier(str(sdf_file), removeHs=False)
    mol = mols[0] if mols and len(mols) > 0 else None
    if mol is None:
        print(f"⚠️ Could not read molecule from {sdf_file}")
        return

    mol_block = Chem.MolToMolBlock(mol)

    viewer = py3Dmol.view(width=800, height=600)
    viewer.addModel(mol_block, "mol")
    viewer.setStyle({"stick": {}})

    conf = mol.GetConformer()
    for atom in mol.GetAtoms():
        idx = atom.GetIdx() + 1
        pos = conf.GetAtomPosition(atom.GetIdx())
        viewer.addLabel(
            str(idx),
            {
                "position": {"x": pos.x, "y": pos.y, "z": pos.z},
                "backgroundColor": "white",
                "fontColor": "black",
                "fontSize": 12,
            },
        )

    viewer.zoomTo()
    html_file = Path(f"{Path(sdf_file).stem}_viewer.html")
    html_file.write_text(viewer._make_html())
    try:
        opened = webbrowser.open(html_file.resolve().as_uri())
        if not opened:
            print(f"⚠️ Could not open a browser automatically. Open this file manually: {html_file.resolve()}")
    except Exception:
        print(f"⚠️ Could not open a browser automatically. Open this file manually: {html_file.resolve()}")


def prompt_anchor_atom(sdf_file: Path) -> int:
    mols = Chem.SDMolSupplier(str(sdf_file), removeHs=False)
    mol = mols[0] if mols and len(mols) else None
    if mol is None:
        sys.exit(f"❌ Cannot validate atom indices because {sdf_file} cannot be parsed.")
    atom_count = mol.GetNumAtoms()
    while True:
        raw = input(f"Enter attachment atom number for {sdf_file.name} (1-{atom_count}): ").strip()
        try:
            return validate_anchor_atom(raw, atom_count)
        except ValueError as exc:
            print(f"⚠️ {exc}")


def validate_anchor_atom(raw: str, atom_count: int) -> int:
    """Validate the one-based PRosettaC atom numbering convention."""
    try:
        atom_index = int(str(raw).strip())
    except ValueError as exc:
        raise ValueError("Enter an integer atom number.") from exc
    if not 1 <= atom_index <= atom_count:
        raise ValueError(f"Atom number must be between 1 and {atom_count}.")
    return atom_index


def update_manifest_anchors(manifest: dict, anchor_atoms: list[int], path: str | Path = "package_manifest.json") -> None:
    manifest["anchors_selected"] = True
    manifest["preparation_status"] = "anchors_selected"
    manifest["anchors"] = {"e3": anchor_atoms[0], "warhead": anchor_atoms[1]}
    Path(path).write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")


# =========================
# Workflow
# =========================

def main() -> None:
    initialize_runtime_dependencies()
    ligase_file = require_file("Ligase.pdb")
    warhead_file = require_file("Warhead.pdb")
    params_file = require_file("Protac_params.txt")
    manifest = load_manifest()

    first_head, second_head, structures, chains, anchor_atoms, original_param_lines = parse_params_file(params_file)

    print(
        "✅ Loaded structural identities: "
        f"E3 {manifest['e3']['pdb_residue_name']} / chain {manifest['e3'].get('pdb_chain') or '[blank]'} / residue {manifest['e3']['pdb_residue_number']}; "
        f"warhead {manifest['warhead']['pdb_residue_name']} / chain {manifest['warhead'].get('pdb_chain') or '[blank]'} / residue {manifest['warhead']['pdb_residue_number']}"
    )
    print(f"✅ Structures: {structures if structures else '[none found]'}")
    print(f"✅ Chains from params: {chains if chains else '[none found]'}")

    ligase_chains = normalize_chain_input(
        input("Enter the chains for Ligase (e.g., 'A', 'B', or 'A,B') **If structure was selected from Schürer Lab Ligandalyzer, please type A**: ")
    )
    warhead_chains = normalize_chain_input(
        input("Enter the chains for Warhead (e.g., 'A', 'B', or 'A,B'): ")
    )

    ligase_filtered_lines = filter_pdb_by_chains(ligase_file, ligase_chains)
    warhead_filtered_lines = filter_pdb_by_chains(warhead_file, warhead_chains)

    if not ligase_filtered_lines:
        sys.exit("❌ No ATOM records matched the selected Ligase chains.")
    if not warhead_filtered_lines:
        sys.exit("❌ No ATOM records matched the selected Warhead chains.")

    ligase_filtered_pdb = Path("Ligase_filtered.pdb")
    warhead_filtered_pdb = Path("Warhead_filtered.pdb")
    write_lines(ligase_filtered_pdb, ligase_filtered_lines)
    write_lines(warhead_filtered_pdb, warhead_filtered_lines)
    print(f"✅ Wrote {ligase_filtered_pdb} and {warhead_filtered_pdb}")

    first_head_filtered = Path("e3_head_filtered.pdb")
    second_head_filtered = Path("warhead_head_filtered.pdb")

    ligase_head_lines = extract_hetatm_by_identity(ligase_file, manifest["e3"])
    warhead_head_lines = extract_hetatm_by_identity(warhead_file, manifest["warhead"])

    write_lines(first_head_filtered, ligase_head_lines)
    write_lines(second_head_filtered, warhead_head_lines)
    print(f"✅ Wrote {first_head_filtered} and {second_head_filtered}")

    first_head_sdf = Path(manifest["e3"]["head_sdf"])
    second_head_sdf = Path(manifest["warhead"]["head_sdf"])
    run_obabel(first_head_filtered, first_head_sdf)
    run_obabel(second_head_filtered, second_head_sdf)
    print(f"✅ Wrote {first_head_sdf} and {second_head_sdf}")

    if structures and chains:
        if len(structures) >= 1 and len(chains) >= 1:
            merge_pdb_files(ligase_filtered_pdb, first_head_filtered, f"{structures[0]}.pdb", chains[0])

        if len(structures) >= 2 and len(chains) >= 2:
            merge_pdb_files(warhead_filtered_pdb, second_head_filtered, f"{structures[1]}.pdb", chains[1])
    else:
        print("⚠️ Structures/Chains not found in Protac_params.txt, skipping merged structure generation.")

    sdf_files = [first_head_sdf, second_head_sdf]

    selected_anchor_atoms: list[int] = []
    for sdf_file in sdf_files:
        if not sdf_file.exists():
            sys.exit(f"❌ Prepared SDF not found: {sdf_file}")

        print(f"Displaying {sdf_file} in your browser...")
        show_molecule(sdf_file)
        input(
            f"Inspect {sdf_file.name} in the browser, identify the anchor atom index, "
            "then come back here and press Enter to continue..."
        )

        selected_anchor_atoms.append(prompt_anchor_atom(sdf_file))

    update_anchor_atoms_in_params(params_file, original_param_lines, selected_anchor_atoms)
    update_manifest_anchors(manifest, selected_anchor_atoms)
    print("✅ Protac_params.txt and package_manifest.json updated successfully.")


if __name__ == "__main__":
    main()
