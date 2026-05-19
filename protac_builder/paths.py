from pathlib import Path


BASE_DIR = Path(__file__).resolve().parents[1]
DATA_DIR = BASE_DIR / "data"
STATIC_DIR = BASE_DIR / "static"
TEMPLATES_DIR = BASE_DIR / "templates"
UPLOADS_DIR = BASE_DIR / "uploads"
LOGS_DIR = BASE_DIR / "logs"
ADMET_REPORTS_DIR = UPLOADS_DIR / "admet_reports"
DEEPPK_OUTPUT_DIR = BASE_DIR / "outputs" / "deeppk_reports"
DEEPPK_UPLOAD_DIR = UPLOADS_DIR / "deeppk"
DEEPPK_TOOLS_DIR = BASE_DIR / "tools" / "deeppk"

LINKER_CSV_PATH = DATA_DIR / "linkers.csv"
WARHEAD_CSV_PATH = DATA_DIR / "output_csvs" / "Ligand_Atoms_Smiles_part1.csv"

LIGASE_DIR = BASE_DIR / "Ligases"
PDB_STRUCTURES_DIR = LIGASE_DIR / "PDB_Structures"
RECRUITER_MODULE_DIR = LIGASE_DIR / "MODULE" / "e3-recruiter-mod"
RECRUITER_LIGASES_DIR = RECRUITER_MODULE_DIR / "Ligases"
RECRUITER_TMP_DIR = RECRUITER_MODULE_DIR / "tmp_sessions"

LINKER_IMAGE_DIR = STATIC_DIR / "linker_images"
LIGASE_IMAGE_DIR = STATIC_DIR / "Ligase_Images"
STATIC_DATA_DIR = STATIC_DIR / "data"
HUNTER_JOBS_DIR = STATIC_DIR / "hunter_jobs"
STATIC_PYTHON_DIR = STATIC_DIR / "python"

GENERATED_PROTACS_LOG = STATIC_DATA_DIR / "Generated_PROTACs.csv"
PROTAC_USAGE_LOG = STATIC_DATA_DIR / "protac_builder_usage.csv"
PROTAC_DOWNLOAD_LOG = STATIC_DATA_DIR / "protac_api_downloads.csv"
PROTAC_USAGE_SEED_PATH = STATIC_DATA_DIR / "protac_builder_usage_seed.json"
API_LINKERS_CSV = STATIC_DATA_DIR / "API_Linkers.csv"
LEGACY_PROTAC_LOG = STATIC_DATA_DIR / "PROTAC_log.csv"
LIGASES_JSON_PATH = STATIC_DATA_DIR / "ligases.json"
RECRUITER_PDB_MAP_PATH = STATIC_DATA_DIR / "recruiter_pdb_map.json"
GENERATED_SMILES_PATH = BASE_DIR / "generated_protac.smi"
PREPFILES_PATH = STATIC_PYTHON_DIR / "PrepFiles.py"


def ensure_runtime_dirs() -> None:
    for path in [
        DATA_DIR,
        DATA_DIR / "output_csvs",
        STATIC_DIR,
        STATIC_DATA_DIR,
        STATIC_PYTHON_DIR,
        LINKER_IMAGE_DIR,
        LIGASE_IMAGE_DIR,
        HUNTER_JOBS_DIR,
        UPLOADS_DIR,
        ADMET_REPORTS_DIR,
        DEEPPK_OUTPUT_DIR,
        DEEPPK_UPLOAD_DIR,
        DEEPPK_TOOLS_DIR,
        LOGS_DIR,
        LIGASE_DIR,
        PDB_STRUCTURES_DIR,
        RECRUITER_LIGASES_DIR,
        RECRUITER_TMP_DIR,
    ]:
        path.mkdir(parents=True, exist_ok=True)
