from __future__ import annotations

import json
import os
import secrets
import shutil
import subprocess
import sys
import traceback
from datetime import datetime, timezone
from pathlib import Path

from rdkit import Chem
from rdkit.Chem import Draw

from .admet import calculate_properties
from .paths import DEEPPK_OUTPUT_DIR, DEEPPK_TOOLS_DIR, LOGS_DIR, STATIC_DIR


PDF_REPORT_NAME = "JARI_PROTAC_Report.pdf"
RAW_CSV_NAME = "DeepPK_Predictions.csv"
CLEAN_CSV_NAME = "DeepPK_Cleaned_Output.csv"
JSON_NAME = "DeepPK_Predictions.json"
SVG_NAME = "Protac.svg"
PNG_NAME = "Protac.png"
PIPELINE_LOG_NAME = "deeppk_pipeline.log"
ERROR_LOG_NAME = "deeppk_errors.log"


class DeepPkPipelineError(RuntimeError):
    def __init__(self, payload: dict[str, object], status_code: int = 500):
        super().__init__(str(payload.get("details") or payload.get("error") or "DeepPK report generation failed."))
        self.payload = payload
        self.status_code = status_code


def _now_stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")


def _job_id() -> str:
    return f"{_now_stamp()}_{secrets.token_hex(4)}"


def _molecule_from_input(smiles: str = "", mol_block: str = "") -> tuple[Chem.Mol, str]:
    if mol_block and mol_block.strip():
        mol = Chem.MolFromMolBlock(mol_block, sanitize=True)
        if mol is not None:
            return mol, Chem.MolToSmiles(mol, isomericSmiles=True)
    if smiles and smiles.strip():
        mol = Chem.MolFromSmiles(smiles.strip())
        if mol is not None:
            return mol, Chem.MolToSmiles(mol, isomericSmiles=True)
    raise ValueError("Valid SMILES or MOL block required")


def _descriptor_warnings(props: dict[str, object]) -> list[str]:
    warnings: list[str] = []
    if float(props.get("molecular_weight", 0) or 0) > 900:
        warnings.append("Very high molecular weight for a PROTAC-like molecule.")
    if int(props.get("rotatable_bonds", 0) or 0) > 15:
        warnings.append("High rotatable bond count may reduce conformational efficiency.")
    if float(props.get("tpsa", 0) or 0) > 180:
        warnings.append("High TPSA may reduce passive permeability.")
    if float(props.get("logp", 0) or 0) > 8:
        warnings.append("High LogP may indicate solubility or exposure risk.")
    if int(props.get("hbd", 0) or 0) > 8:
        warnings.append("High hydrogen bond donor count may impair permeability.")
    if int(props.get("hba", 0) or 0) > 15:
        warnings.append("High hydrogen bond acceptor count may impair permeability.")
    return warnings


def _ensure_png(job_dir: Path, mol: Chem.Mol) -> Path:
    png_path = job_dir / PNG_NAME
    image = Draw.MolToImage(mol, size=(1200, 1200))
    image.save(png_path)
    return png_path


def _ensure_static_assets(job_dir: Path) -> None:
    static_images_dir = job_dir / "static" / "images"
    static_images_dir.mkdir(parents=True, exist_ok=True)
    favicon_source = STATIC_DIR / "images" / "favicon.png"
    if favicon_source.exists():
        shutil.copy2(favicon_source, static_images_dir / "favicon.png")


def _tool_path(name: str) -> Path:
    path = DEEPPK_TOOLS_DIR / name
    if not path.exists():
        raise FileNotFoundError(f"Missing DeepPK tool: {path}")
    return path


def _run_script(
    script_name: str,
    *,
    job_dir: Path,
    env: dict[str, str],
    timeout: int,
) -> str:
    command = [sys.executable, str(_tool_path(script_name))]
    result = subprocess.run(
        command,
        cwd=job_dir,
        env=env,
        capture_output=True,
        text=True,
        timeout=timeout,
        check=False,
    )
    combined = (result.stdout or "") + ("\n" + result.stderr if result.stderr else "")
    with (job_dir / PIPELINE_LOG_NAME).open("a", encoding="utf-8") as handle:
        handle.write(f"\n===== {script_name} =====\n")
        handle.write(combined)
        handle.write("\n")
    if result.returncode != 0:
        raise RuntimeError(f"{script_name} failed. {combined.strip()}".strip())
    return combined


def _load_prediction_json(job_dir: Path) -> dict[str, object]:
    payload_path = job_dir / JSON_NAME
    if not payload_path.exists():
        raise FileNotFoundError(f"Expected DeepPK output not found: {payload_path}")
    with payload_path.open(encoding="utf-8") as handle:
        return json.load(handle)


def _response_files(job_id: str) -> dict[str, str | None]:
    base = f"/api/deeppk/download/{job_id}"
    return {
        "pdf_url": f"{base}/{PDF_REPORT_NAME}",
        "csv_url": f"{base}/{RAW_CSV_NAME}",
        "clean_csv_url": f"{base}/{CLEAN_CSV_NAME}",
        "json_url": f"{base}/{JSON_NAME}",
        "svg_url": f"{base}/{SVG_NAME}",
        "pipeline_log_url": f"{base}/{PIPELINE_LOG_NAME}",
    }


def _ensure_fallback_outputs(job_dir: Path) -> None:
    raw_csv = job_dir / RAW_CSV_NAME
    clean_csv = job_dir / CLEAN_CSV_NAME
    if not raw_csv.exists() and clean_csv.exists():
        shutil.copy2(clean_csv, raw_csv)


def _shorten(text: str, limit: int = 280) -> str:
    compact = " ".join(str(text or "").split())
    if len(compact) <= limit:
        return compact
    return compact[: limit - 1].rstrip() + "…"


def _safe_error_details(stage: str, exc: Exception) -> str:
    raw = _shorten(str(exc) or exc.__class__.__name__, 420)
    lowered = raw.lower()

    if isinstance(exc, subprocess.TimeoutExpired):
        return "DeepPK timed out while waiting for the external prediction service."
    if "could not resolve host" in lowered or "failed to connect" in lowered:
        return "The external DeepPK service is temporarily unavailable."
    if "submission failed" in lowered or "could not extract job id" in lowered:
        return "The external DeepPK service did not return a valid job ID."
    if "timed out" in lowered:
        return "The external DeepPK service timed out or remained busy too long."
    if stage == "collect_outputs" and "missing outputs" in lowered:
        return "DeepPK finished partially, but one or more report files were missing."
    if stage == "prepare_job_dir" and "permission" in lowered:
        return "The server could not prepare a writable DeepPK job directory."
    return raw or "DeepPK report generation failed."


def _log_pipeline_error(*, stage: str, job_id: str | None, exc: Exception) -> None:
    LOGS_DIR.mkdir(parents=True, exist_ok=True)
    error_log = LOGS_DIR / ERROR_LOG_NAME
    stamp = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    traceback_text = traceback.format_exc()
    with error_log.open("a", encoding="utf-8") as handle:
        handle.write(f"[{stamp}] stage={stage} job_id={job_id or '-'}\n")
        handle.write(traceback_text)
        handle.write("\n")


def _failure_payload(
    *,
    stage: str,
    exc: Exception,
    job_id: str | None,
    rdkit_descriptors: dict[str, object] | None,
    retryable: bool,
) -> dict[str, object]:
    return {
        "success": False,
        "error": "DeepPK report generation failed.",
        "details": _safe_error_details(stage, exc),
        "stage": stage,
        "job_id": job_id,
        "rdkit_descriptors": rdkit_descriptors or {},
        "retryable": retryable,
    }


def run_deeppk_pipeline(smiles: str = "", mol_block: str = "") -> dict[str, object]:
    stage = "validate_input"
    job_id: str | None = None
    job_dir: Path | None = None
    props: dict[str, object] | None = None
    warnings: list[str] = []

    try:
        mol, canonical_smiles = _molecule_from_input(smiles=smiles, mol_block=mol_block)

        stage = "rdkit_descriptors"
        props = calculate_properties(smiles=canonical_smiles)
        warnings = _descriptor_warnings(props)

        stage = "prepare_job_dir"
        job_id = _job_id()
        job_dir = DEEPPK_OUTPUT_DIR / job_id
        job_dir.mkdir(parents=True, exist_ok=True)
        _ensure_static_assets(job_dir)
        _ensure_png(job_dir, mol)

        max_wait = int(os.environ.get("DEEPPK_MAX_WAIT_SECONDS", "300"))
        check_interval = int(os.environ.get("DEEPPK_CHECK_INTERVAL_SECONDS", "15"))
        env = os.environ.copy()
        env["SMILES_INPUT"] = canonical_smiles
        env["DEEPPK_MAX_WAIT_SECONDS"] = str(max_wait)
        env["DEEPPK_CHECK_INTERVAL_SECONDS"] = str(check_interval)
        env["MPLCONFIGDIR"] = str(job_dir / ".matplotlib")
        Path(env["MPLCONFIGDIR"]).mkdir(parents=True, exist_ok=True)

        stage = "run_smiles_drug_props"
        _run_script("SmilesDrugProps.py", job_dir=job_dir, env=env, timeout=max_wait + 90)

        stage = "run_json_analyzer"
        _run_script("JSONANALYZER.py", job_dir=job_dir, env=env, timeout=90)

        stage = "run_deeppk_display"
        _run_script("DeepPKDisplay.py", job_dir=job_dir, env=env, timeout=180)

        stage = "collect_outputs"
        _ensure_fallback_outputs(job_dir)
        expected = [
            job_dir / PDF_REPORT_NAME,
            job_dir / RAW_CSV_NAME,
            job_dir / CLEAN_CSV_NAME,
            job_dir / JSON_NAME,
            job_dir / SVG_NAME,
        ]
        missing = [str(path.name) for path in expected if not path.exists()]
        if missing:
            raise FileNotFoundError(f"DeepPK pipeline finished but missing outputs: {', '.join(missing)}")

        prediction_json = _load_prediction_json(job_dir)
        files = _response_files(job_id)

        stage = "response"
        links = {
            "pdf": files["pdf_url"],
            "csv": files["csv_url"],
            "cleaned_csv": files["clean_csv_url"],
            "json": files["json_url"],
            "svg": files["svg_url"],
        }
        return {
            "success": True,
            "message": "DeepPK report generated successfully.",
            "job_id": job_id,
            "pdf_url": files["pdf_url"],
            "links": links,
            "deeppk": files,
            "rdkit_descriptors": props,
            "warnings": warnings,
            "deep_pk_summary": prediction_json.get("Deep-PK Predictions"),
        }
    except Exception as exc:
        _log_pipeline_error(stage=stage, job_id=job_id, exc=exc)

        retryable = stage != "validate_input"
        status_code = 400 if stage == "validate_input" and isinstance(exc, ValueError) else 500
        raise DeepPkPipelineError(
            _failure_payload(
                stage=stage,
                exc=exc,
                job_id=job_id,
                rdkit_descriptors=props,
                retryable=retryable,
            ),
            status_code=status_code,
        ) from exc


def get_deeppk_file(job_id: str, filename: str) -> Path:
    root = DEEPPK_OUTPUT_DIR.resolve()
    candidate = (DEEPPK_OUTPUT_DIR / job_id / filename).resolve()
    if root not in candidate.parents or not candidate.exists():
        raise FileNotFoundError(filename)
    return candidate
