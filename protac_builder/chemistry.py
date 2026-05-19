from __future__ import annotations

import base64
import io
import re
from functools import lru_cache
from pathlib import Path

from rdkit import Chem
from rdkit.Chem import Draw, rdDepictor, rdMolDescriptors
from rdkit.Chem.Draw import rdMolDraw2D

from .paths import PDB_STRUCTURES_DIR


def mol_from_smiles(smiles: str) -> Chem.Mol | None:
    if not smiles:
        return None
    return Chem.MolFromSmiles(smiles)


def convert_smiles_to_molblock(smiles: str) -> str | None:
    smiles = (smiles or "").strip()
    if not smiles:
        return None

    normalized = normalize_attachment_smiles(smiles)
    mol = Chem.MolFromSmiles(normalized)
    if mol is None:
        mol = Chem.MolFromSmiles(_legacy_rgroup_to_dummy(smiles))
    if mol is None:
        return None

    try:
        rdDepictor.Compute2DCoords(mol)
    except Exception:
        pass
    return Chem.MolToMolBlock(mol)


def molblock_to_smiles(mol_block: str) -> str | None:
    mol = Chem.MolFromMolBlock(mol_block or "", sanitize=True)
    if mol is None:
        return None
    Chem.SanitizeMol(mol)
    Chem.RemoveHs(mol)
    return Chem.MolToSmiles(mol, isomericSmiles=True)


def render_smiles_data_url(smiles: str, size: tuple[int, int] = (300, 300)) -> str | None:
    mol = Chem.MolFromSmiles(normalize_attachment_smiles(smiles))
    if mol is None:
        mol = Chem.MolFromSmiles(_legacy_rgroup_to_dummy(smiles))
    if mol is None:
        return None
    image = Draw.MolToImage(mol, size=size)
    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    payload = base64.b64encode(buffer.getvalue()).decode("utf-8")
    return f"data:image/png;base64,{payload}"


def _legacy_rgroup_to_dummy(smiles: str) -> str:
    text = (smiles or "").strip()
    text = re.sub(r"\[R1\]", "[1*]", text, flags=re.IGNORECASE)
    text = re.sub(r"\[R2\]", "[2*]", text, flags=re.IGNORECASE)
    return text


def normalize_attachment_smiles(smiles: str) -> str:
    text = (smiles or "").strip()
    text = re.sub(r"\[R1\]", "[*:1]", text, flags=re.IGNORECASE)
    text = re.sub(r"\[R2\]", "[*:2]", text, flags=re.IGNORECASE)
    text = re.sub(r"\[1\*\]", "[*:1]", text)
    text = re.sub(r"\[2\*\]", "[*:2]", text)
    return text


def _atom_is_label(atom: Chem.Atom, label: str) -> bool:
    if atom.HasProp("molFileAlias") and atom.GetProp("molFileAlias") == label:
        return True
    if atom.HasProp("dummyLabel") and atom.GetProp("dummyLabel") == label:
        return True
    if label == "R1" and atom.GetAtomicNum() == 0 and atom.GetIsotope() == 1:
        return True
    if label == "R2" and atom.GetAtomicNum() == 0 and atom.GetIsotope() == 2:
        return True
    if label == "R1" and (atom.GetSymbol() == "U" or atom.GetAtomicNum() == 92):
        return True
    if label == "R2" and (atom.GetSymbol() == "V" or atom.GetAtomicNum() == 23):
        return True
    if label == "R1" and atom.GetAtomMapNum() == 1:
        return True
    if label == "R2" and atom.GetAtomMapNum() == 2:
        return True
    return False


def find_atom_index_by_label(mol: Chem.Mol, label: str) -> int | None:
    for atom in mol.GetAtoms():
        if _atom_is_label(atom, label):
            return atom.GetIdx()
    return None


def connect_molecules_by_labels(mol1: Chem.Mol, mol2: Chem.Mol, label1: str, label2: str) -> Chem.Mol:
    idx1 = find_atom_index_by_label(mol1, label1)
    idx2 = find_atom_index_by_label(mol2, label2)
    if idx1 is None or idx2 is None:
        raise ValueError(f"Labels {label1} or {label2} not found in the molecules.")

    neighbors1 = list(mol1.GetAtomWithIdx(idx1).GetNeighbors())
    neighbors2 = list(mol2.GetAtomWithIdx(idx2).GetNeighbors())
    if len(neighbors1) != 1 or len(neighbors2) != 1:
        raise ValueError("Attachment labels must each have exactly one neighbor.")

    neighbor_idx1 = neighbors1[0].GetIdx()
    neighbor_idx2 = neighbors2[0].GetIdx()

    combined = Chem.CombineMols(mol1, mol2)
    offset = mol1.GetNumAtoms()

    editable = Chem.EditableMol(combined)
    editable.AddBond(neighbor_idx1, offset + neighbor_idx2, order=Chem.BondType.SINGLE)

    for idx in sorted([idx1, offset + idx2], reverse=True):
        editable.RemoveAtom(idx)

    final = editable.GetMol()
    try:
        Chem.SanitizeMol(final)
    except Exception:
        pass
    return final


def generate_protac_molblock(warhead_mol_block: str, linker_mol_block: str, ligase_mol_block: str) -> str:
    warhead = Chem.MolFromMolBlock(warhead_mol_block or "", sanitize=False)
    linker = Chem.MolFromMolBlock(linker_mol_block or "", sanitize=False)
    ligase = Chem.MolFromMolBlock(ligase_mol_block or "", sanitize=False)
    if not warhead or not linker or not ligase:
        raise ValueError("One or more MOL blocks could not be loaded.")

    intermediate = connect_molecules_by_labels(warhead, linker, "R1", "R1")
    final = connect_molecules_by_labels(intermediate, ligase, "R2", "R2")
    return Chem.MolToMolBlock(final)


def _find_dummy_by_mapnum(mol: Chem.Mol, mapnum: int) -> int | None:
    for atom in mol.GetAtoms():
        if atom.GetAtomicNum() == 0 and atom.GetAtomMapNum() == mapnum:
            return atom.GetIdx()
    return None


def _neighbor_of_dummy(mol: Chem.Mol, dummy_idx: int) -> int:
    atom = mol.GetAtomWithIdx(dummy_idx)
    neighbors = list(atom.GetNeighbors())
    if len(neighbors) != 1:
        raise ValueError(f"Attachment dummy has {len(neighbors)} neighbors (expected 1)")
    return neighbors[0].GetIdx()


def build_protac_smiles(target_smiles: str, linker_smiles: str, ligase_smiles: str) -> str:
    target_smiles = normalize_attachment_smiles(target_smiles)
    linker_smiles = normalize_attachment_smiles(linker_smiles)
    ligase_smiles = normalize_attachment_smiles(ligase_smiles)

    target = Chem.MolFromSmiles(target_smiles)
    linker = Chem.MolFromSmiles(linker_smiles)
    ligase = Chem.MolFromSmiles(ligase_smiles)

    if target is None:
        raise ValueError("Target (warhead) SMILES could not be parsed")
    if linker is None:
        raise ValueError("Linker SMILES could not be parsed")
    if ligase is None:
        raise ValueError("Ligase SMILES could not be parsed")

    w_dummy = _find_dummy_by_mapnum(target, 1)
    l_dummy_1 = _find_dummy_by_mapnum(linker, 1)
    l_dummy_2 = _find_dummy_by_mapnum(linker, 2)
    g_dummy = _find_dummy_by_mapnum(ligase, 2)

    if w_dummy is None:
        raise ValueError("Target missing attachment point [*:1]")
    if g_dummy is None:
        raise ValueError("Ligase missing attachment point [*:2]")
    if l_dummy_1 is None or l_dummy_2 is None:
        raise ValueError("Linker must contain both [*:1] and [*:2]")

    w_neighbor = _neighbor_of_dummy(target, w_dummy)
    l_neighbor_1 = _neighbor_of_dummy(linker, l_dummy_1)
    l_neighbor_2 = _neighbor_of_dummy(linker, l_dummy_2)
    g_neighbor = _neighbor_of_dummy(ligase, g_dummy)

    combined_wl = Chem.CombineMols(target, linker)
    combined = Chem.CombineMols(combined_wl, ligase)

    offset_linker = target.GetNumAtoms()
    offset_ligase = target.GetNumAtoms() + linker.GetNumAtoms()

    editable = Chem.EditableMol(combined)
    editable.AddBond(w_neighbor, offset_linker + l_neighbor_1, Chem.BondType.SINGLE)
    editable.AddBond(offset_linker + l_neighbor_2, offset_ligase + g_neighbor, Chem.BondType.SINGLE)

    for idx in sorted(
        [
            w_dummy,
            offset_linker + l_dummy_1,
            offset_linker + l_dummy_2,
            offset_ligase + g_dummy,
        ],
        reverse=True,
    ):
        editable.RemoveAtom(idx)

    final = editable.GetMol()
    Chem.SanitizeMol(final)
    for atom in final.GetAtoms():
        atom.SetAtomMapNum(0)
    return Chem.MolToSmiles(final, isomericSmiles=True)


def molblock_to_mapped_smiles(mol_block: str) -> tuple[str, list[str]]:
    mol = Chem.MolFromMolBlock(mol_block or "", sanitize=False, removeHs=False)
    if mol is None:
        raise ValueError("Could not parse molBlock")

    rw = Chem.RWMol(mol)
    warnings: list[str] = []
    u_count = 0
    v_count = 0

    for atom in rw.GetAtoms():
        if _atom_is_label(atom, "R1"):
            atom.SetAtomicNum(0)
            atom.SetAtomMapNum(1)
            u_count += 1
        elif _atom_is_label(atom, "R2"):
            atom.SetAtomicNum(0)
            atom.SetAtomMapNum(2)
            v_count += 1

    if u_count == 0:
        warnings.append("No U/R1 attachment atoms found.")
    if v_count == 0:
        warnings.append("No V/R2 attachment atoms found.")

    out = rw.GetMol()
    try:
        Chem.SanitizeMol(out)
    except Exception:
        pass
    return Chem.MolToSmiles(out, canonical=True), warnings


@lru_cache(maxsize=5000)
def smiles_to_svg(smiles: str, width: int = 150, height: int = 150) -> str:
    mol = Chem.MolFromSmiles(normalize_attachment_smiles(smiles))
    if mol is None:
        mol = Chem.MolFromSmiles(_legacy_rgroup_to_dummy(smiles))
    if mol is None:
        return "<svg></svg>"
    rdMolDraw2D.PrepareMolForDrawing(mol)
    drawer = rdMolDraw2D.MolDraw2DSVG(width, height)
    drawer.DrawMolecule(mol)
    drawer.FinishDrawing()
    return drawer.GetDrawingText().replace("svg:", "")


def mol_to_svg_data_url(mol: Chem.Mol, width: int = 300, height: int = 300) -> str:
    try:
        rdDepictor.Compute2DCoords(mol)
    except Exception:
        pass
    drawer = rdMolDraw2D.MolDraw2DSVG(width, height)
    drawer.DrawMolecule(mol)
    drawer.FinishDrawing()
    svg = drawer.GetDrawingText()
    payload = base64.b64encode(svg.encode("utf-8")).decode("utf-8")
    return f"data:image/svg+xml;base64,{payload}"


def load_sdf_as_preview(path: Path) -> dict[str, str]:
    mol = Chem.MolFromMolFile(str(path), sanitize=False)
    if mol is None:
        raise ValueError("Failed to load SDF")
    smiles = Chem.MolToSmiles(mol)
    clean = Chem.MolFromSmiles(smiles)
    if clean is None:
        raise ValueError("Failed to normalize SDF")
    return {
        "mol_block": Chem.MolToMolBlock(clean),
        "image": mol_to_svg_data_url(clean),
    }


def load_pdb_as_preview(path: Path) -> dict[str, str]:
    mol = Chem.MolFromPDBFile(str(path), sanitize=False, removeHs=False)
    if mol is None:
        raise ValueError("Failed to load PDB")
    smiles = Chem.MolToSmiles(mol)
    clean = Chem.MolFromSmiles(smiles)
    if clean is None:
        raise ValueError("Failed to normalize PDB ligand")
    return {
        "mol_block": Chem.MolToMolBlock(clean),
        "image": mol_to_svg_data_url(clean),
    }


def load_raw_sdf_molblock(path: Path) -> str:
    text = path.read_text(encoding="utf-8")
    mol = Chem.MolFromMolBlock(text, sanitize=False)
    if mol is None:
        raise ValueError("RDKit failed to parse SDF")
    Chem.SanitizeMol(mol)
    rdDepictor.Compute2DCoords(mol)
    return Chem.MolToMolBlock(mol)


def find_pdb_info(ligase_name: str) -> tuple[str | None, Path | None, str | None, str | None, str | None]:
    try:
        ligase_type, ligand_code = ligase_name.split("_", 1)
    except ValueError:
        return None, None, None, None, None

    ligase_dir = PDB_STRUCTURES_DIR / ligase_type
    if not ligase_dir.exists():
        return None, None, None, None, None

    candidates = [path for path in ligase_dir.glob(f"*_{ligand_code}.pdb")]
    if not candidates:
        return None, None, None, None, None

    def _is_real_pdb(path: Path) -> bool:
        stem = path.stem.split("_")[0]
        return len(stem) == 4 and stem.isalnum()

    candidates.sort(key=_is_real_pdb, reverse=True)
    pdb_path = candidates[0]
    pdb_id = pdb_path.stem.split("_")[0]

    chain = None
    residue = None
    with pdb_path.open("r", encoding="utf-8", errors="ignore") as handle:
        for line in handle:
            if line.startswith("HETATM") and ligand_code in line:
                chain = line[21].strip() or None
                match = re.findall(r"\d+", line[22:26])
                residue = match[0] if match else None
                break

    return pdb_id, pdb_path, chain, residue, ligand_code


def ligase_card_metadata(sdf_path: Path, image_url: str) -> dict[str, str | float]:
    supplier = Chem.SDMolSupplier(str(sdf_path))
    mol = next((item for item in supplier if item is not None), None)
    if mol is None:
        raise ValueError(f"Could not load ligase SDF: {sdf_path.name}")
    return {
        "name": sdf_path.stem,
        "image": image_url,
        "mw": round(rdMolDescriptors.CalcExactMolWt(mol), 2),
        "formula": rdMolDescriptors.CalcMolFormula(mol),
        "sdf": str(sdf_path),
    }
