import importlib.util
import json
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module


prep = load_module("prosettac_prep", ROOT / "static/python/PrepFiles.py")
randy = load_module("randy_e3_routes", ROOT / "RANDY/e3_data_routes.py")


PDB = """HETATM    1  C1  A1D A 436      10.000  10.000  10.000  1.00 20.00           C
HETATM    2  O1  A1D A 436      11.000  10.000  10.000  1.00 20.00           O
END
"""


class ProsettacContractTests(unittest.TestCase):
    def test_randy_reads_actual_pdb_identity_not_display_identifier(self):
        with tempfile.TemporaryDirectory() as directory:
            pdb = Path(directory) / "10ZF_A1DCD_1.pdb"
            pdb.write_text(PDB)
            record = {"ligand": "A1DCD", "sdf_file": "10ZF_A1DCD_1.sdf", "pdb_available": True, "sdf_available": True}
            randy._apply_prosettac_structural_metadata(record, pdb)
        self.assertTrue(record["prosettac_exportable"])
        self.assertEqual(record["display_ligand_id"], "A1DCD")
        self.assertEqual(record["pdb_residue_name"], "A1D")
        self.assertEqual(record["pdb_chain"], "A")
        self.assertEqual(record["pdb_residue_number"], "436")

    def test_randy_fails_closed_for_ambiguous_pdb(self):
        with tempfile.TemporaryDirectory() as directory:
            pdb = Path(directory) / "ambiguous.pdb"
            pdb.write_text(PDB + PDB.replace("A1D A 436", "Y70 B 501"))
            record = {"ligand": "A1DCD", "pdb_available": True, "sdf_available": True}
            randy._apply_prosettac_structural_metadata(record, pdb)
        self.assertFalse(record["prosettac_exportable"])
        self.assertIn("uniquely resolve", record["prosettac_export_error"])

    def test_prep_extracts_only_manifest_identity(self):
        with tempfile.TemporaryDirectory() as directory:
            pdb = Path(directory) / "Ligase.pdb"
            pdb.write_text(PDB + PDB.replace("A1D A 436", "A1D B 437"))
            lines = prep.extract_hetatm_by_identity(pdb, {
                "pdb_residue_name": "A1D", "pdb_chain": "A", "pdb_residue_number": "436", "pdb_insertion_code": ""
            })
        self.assertEqual(len(lines), 2)
        self.assertTrue(all(line[21] == "A" and line[22:26].strip() == "436" for line in lines))

    def test_manifest_schema_and_anchor_update(self):
        manifest = {
            "schema_version": 1, "package_type": "prosettac", "anchors_selected": False,
            "e3": {"pdb_residue_name": "A1D", "pdb_residue_number": "436", "head_sdf": "e3_head.sdf"},
            "warhead": {"pdb_residue_name": "Y70", "pdb_residue_number": "501", "head_sdf": "warhead_head.sdf"},
        }
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "package_manifest.json"
            path.write_text(json.dumps(manifest))
            loaded = prep.load_manifest(path)
            prep.update_manifest_anchors(loaded, [17, 8], path)
            updated = json.loads(path.read_text())
        self.assertTrue(updated["anchors_selected"])
        self.assertEqual(updated["anchors"], {"e3": 17, "warhead": 8})


if __name__ == "__main__":
    unittest.main()
