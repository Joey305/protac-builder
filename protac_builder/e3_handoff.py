from __future__ import annotations

import os
from urllib.parse import quote, urljoin

import requests


def _remote_token() -> str:
    return (
        os.environ.get("E3_RANDY_TOKEN", "").strip()
        or os.environ.get("RANDY_E3_TOKEN", "").strip()
        or os.environ.get("RANDY_BACKUP_TOKEN", "").strip()
        or os.environ.get("PROTAC_BACKUP_TOKEN", "").strip()
    )


def _remote_headers() -> dict[str, str]:
    headers = {"User-Agent": "protac-builder-e3-proxy/1.0"}
    token = _remote_token()
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return headers


def _candidate_remote_bases() -> list[str]:
    bases: list[str] = []
    for value in (
        os.environ.get("E3_DATA_API_BASE", "").strip(),
        os.environ.get("E3_LIGANDALYZER_API_BASE", "").strip(),
        os.environ.get("PROTAC_CONVERTED_SESSION_BASE", "").strip(),
        "https://e3ligandalyzer-adb8adfde220.herokuapp.com",
        "https://stan.rove-vernier.ts.net",
    ):
        clean = value.rstrip("/")
        if clean and clean not in bases:
            bases.append(clean)
    return bases


def fetch_remote_ligase_pdb(ligase: str, filename: str, timeout: float = 20.0) -> tuple[bytes, str]:
    quoted_ligase = quote(str(ligase or "").strip(), safe="")
    quoted_name = quote(str(filename or "").strip(), safe="/")
    last_response: requests.Response | None = None
    last_error: requests.RequestException | None = None

    for base in _candidate_remote_bases():
        url = urljoin(base.rstrip("/") + "/", f"backup/e3/file/pdb/{quoted_ligase}/{quoted_name}")
        try:
            response = requests.get(url, headers=_remote_headers(), timeout=timeout)
            last_response = response
            if response.status_code == 404:
                continue
            response.raise_for_status()
            return response.content, response.headers.get("content-type", "chemical/x-pdb")
        except requests.HTTPError:
            raise
        except requests.RequestException as exc:
            last_error = exc
            continue

    if last_response is not None and last_response.status_code == 404:
        raise requests.HTTPError("Remote ligase PDB not found.", response=last_response)
    if last_error is not None:
        raise last_error
    raise FileNotFoundError("No remote E3 ligase data source is configured.")
