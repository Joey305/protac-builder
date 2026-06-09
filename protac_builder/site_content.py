from __future__ import annotations

"""
Lightweight metadata and discovery configuration for the editable content pages.

Page body copy now lives in templates/pages/*.html so site owners can edit each
page directly in Jinja/HTML without working inside Python dictionaries.
"""

from copy import deepcopy
from typing import Any


PUBLIC_DOMAIN = "https://protacbuilder.com"

ECOSYSTEM_LINKS = {
    "protac_builder": {
        "label": "PROTAC Builder",
        "href": f"{PUBLIC_DOMAIN}/builder",
        "description": "Assemble warheads, linkers, and E3 recruiters into candidate degraders.",
    },
    "warhead_hunter": {
        "label": "Warhead Hunter",
        "href": "https://warheadhunter.com/examples",
        "description": "Explore target-binding warheads, example jobs, and warhead-focused discovery workflows.",
    },
    "warhead_hunter_home": {
        "label": "Warhead Hunter",
        "href": "https://warheadhunter.com",
        "description": "Warhead-focused discovery environment for target engagement context and handoff into degrader assembly.",
    },
    "e3_ligandalyzer": {
        "label": "E3 Ligandalyzer",
        "href": "https://e3ligandalyzer.com/explorer",
        "description": "Inspect E3 recruiters, ligases, scaffolds, and recruiter attachment context.",
    },
    "e3_ligandalyzer_scaffolds": {
        "label": "Ligandalyzer Scaffolds",
        "href": "https://e3ligandalyzer.com/scaffolds",
        "description": "Browse recruiter chemotypes and scaffold-level organization.",
    },
    "vlisemod": {
        "label": "V-LiSEMOD",
        "href": "https://vlisemod.com",
        "description": "Viral protein-ligand structures and solvent-exposed moieties for viral target warhead discovery.",
    },
    "vlisemod_home": {
        "label": "V-LiSEMOD",
        "href": "https://vlisemod.com",
        "description": "Viral-Ligand Solvent Exposed Moiety Database for viral targets, bound ligands, and warhead starting points.",
    },
    "schurer_lab": {
        "label": "Schurer Lab",
        "href": "https://schurerlab.org",
        "description": "Research group behind the connected degrader discovery tool ecosystem.",
    },
}


PAGE_META: dict[str, dict[str, Any]] = {
    "home": {
        "slug": "",
        "template": "pages/home.html",
        "meta_title": "PROTAC Builder - Free In Silico Degrader Design Tool",
        "meta_description": "Build PROTACs in a free web app that combines warheads, linkers, and E3 recruiters for in silico degrader design, API workflows, and downstream modeling handoff.",
        "software_app_schema": True,
        "article_schema": False,
    },
    "what_is_a_protac": {
        "slug": "what-is-a-protac",
        "template": "pages/what_is_a_protac.html",
        "meta_title": "What Is a PROTAC? | Proteolysis-Targeting Chimera Explained",
        "meta_description": "Learn what a PROTAC is, how proteolysis-targeting chimeras work, and how warheads, linkers, E3 ligase recruiters, ternary complexes, ubiquitination, and proteasomal degradation fit into targeted protein degradation.",
        "software_app_schema": False,
        "article_schema": True,
    },
    "how_to_build_a_protac": {
        "slug": "how-to-build-a-protac",
        "template": "pages/how_to_build_a_protac.html",
        "meta_title": "How to Build a PROTAC | Practical PROTAC Design Workflow",
        "meta_description": "Learn how to build a PROTAC by selecting a POI warhead, E3 recruiter, linker, attachment vectors, assembly strategy, and validation workflow.",
        "software_app_schema": False,
        "article_schema": True,
    },
    "examples": {
        "slug": "examples",
        "template": "pages/examples.html",
        "meta_title": "PROTAC Builder Examples | PROTAC Builder",
        "meta_description": "Browse example PROTAC Builder workflows for BRD4, CRBN, VHL, custom warheads, API batches, and cross-site handoffs from Warhead Hunter, E3 Ligandalyzer, and V-LiSEMOD.",
        "software_app_schema": False,
        "article_schema": True,
    },
    "component_hubs": {
        "slug": "component-hubs",
        "template": "pages/component_hubs.html",
        "meta_title": "PROTAC Component Hubs | Warheads, Linkers, and E3 Recruiters",
        "meta_description": "Explore the core PROTAC component workflow: target-binding warheads, linker design, E3 ligase recruiters, attachment vectors, bridgeability, and handoff into PROTAC Builder.",
        "software_app_schema": False,
        "article_schema": True,
    },
    "warheads": {
        "slug": "warheads",
        "template": "pages/warheads.html",
        "meta_title": "PROTAC Warhead Discovery | Target-Binding Ligands and Linker Attachment Sites",
        "meta_description": "Learn how PROTAC warhead discovery uses ligand-bound protein structures, solvent exposure mapping, RCSB search, attachment-vector inspection, and Warhead Hunter outputs to guide degrader assembly.",
        "software_app_schema": False,
        "article_schema": True,
    },
    "linkers": {
        "slug": "linkers",
        "template": "pages/linkers.html",
        "meta_title": "PROTAC Linker Design Hub | PROTAC Builder",
        "meta_description": "Learn how linker length, polarity, flexibility, rigidity, and bridgeability affect PROTAC design and downstream ternary complex feasibility.",
        "software_app_schema": False,
        "article_schema": True,
    },
    "e3_ligase_recruiters": {
        "slug": "e3-ligase-recruiters",
        "template": "pages/e3_ligase_recruiters.html",
        "meta_title": "E3 Ligase Recruiters for PROTAC Design | Structure-First Recruiter Selection",
        "meta_description": "Explore how to choose E3 ligase recruiters for PROTAC design using structure-first recruiter ligand analysis, scaffold diversity, solvent exposure, expression context, and PROTAC Builder integration.",
        "software_app_schema": False,
        "article_schema": True,
    },
    "constraint_driven_protac_design": {
        "slug": "constraint-driven-protac-design",
        "template": "pages/constraint_driven_protac_design.html",
        "meta_title": "Constraint-Driven PROTAC Design | Geometry-Aware Degrader Modeling",
        "meta_description": "Learn how constraint-driven PROTAC design uses anchor atoms, exit vectors, linker bridgeability, solved structures, PRosettaC-style modeling, and downstream validation to build geometry-aware degrader candidates.",
        "software_app_schema": False,
        "article_schema": True,
    },
    "in_silico_protac_modeling": {
        "slug": "in-silico-protac-modeling",
        "template": "pages/in_silico_protac_modeling.html",
        "meta_title": "In Silico PROTAC Modeling | Computational PROTAC Design Workflows",
        "meta_description": "Learn how in silico PROTAC modeling combines ternary complex docking, PRosettaC-style constraints, molecular dynamics, machine learning, generative linker design, feasibility filters, and benchmarking to prioritize degrader candidates.",
        "software_app_schema": False,
        "article_schema": True,
    },
    "benchmarking": {
        "slug": "benchmarking",
        "template": "pages/benchmarking.html",
        "meta_title": "PROTAC Modeling Benchmarking | Standards for Computational PROTAC Design",
        "meta_description": "Learn how to benchmark computational PROTAC modeling methods across ternary structure prediction, pose ranking, degradation prediction, generative design, molecular representation, domain shift, and reproducibility.",
        "software_app_schema": False,
        "article_schema": True,
    },
    "downstream_modeling_tools": {
        "slug": "downstream-modeling",
        "template": "pages/downstream_modeling_tools.html",
        "meta_title": "Downstream PROTAC Modeling Tools | Ternary Complex Handoff Workflows",
        "meta_description": "Learn how PROTAC Builder outputs can feed downstream modeling workflows including restrained docking, PRosettaC-style ternary modeling, molecular dynamics, linker bridgeability checks, ML re-ranking, descriptors, and benchmarking.",
        "software_app_schema": False,
        "article_schema": True,
    },
    "ecosystem": {
        "slug": "ecosystem",
        "template": "pages/ecosystem.html",
        "meta_title": "Schurer Lab PROTAC Design Ecosystem | PROTAC Builder",
        "meta_description": "Learn how PROTAC Builder connects with Warhead Hunter, E3 Ligandalyzer, V-LiSEMOD, and API workflows across the Schurer Lab degrader discovery ecosystem.",
        "software_app_schema": False,
        "article_schema": True,
    },
    "faq": {
        "slug": "faq",
        "template": "pages/faq.html",
        "meta_title": "PROTAC Builder FAQ | Scope, Workflow, Inputs, API, and Limitations",
        "meta_description": "Find answers about PROTAC Builder scope, warheads, linkers, E3 recruiters, custom SMILES, examples, API workflows, downstream modeling, limitations, and responsible interpretation of generated candidates.",
        "software_app_schema": False,
        "article_schema": True,
    },
    "methods": {
        "slug": "methods",
        "template": "pages/methods.html",
        "meta_title": "PROTAC Builder Methods | Assembly Workflow, Components, and Handoffs",
        "meta_description": "Learn the PROTAC Builder methodology for assembling warheads, linkers, and E3 recruiters, defining attachment atoms, preparing candidate structures, using API workflows, and handing off to downstream modeling.",
        "software_app_schema": False,
        "article_schema": True,
    },
    "database_schema": {
        "slug": "database-schema",
        "template": "pages/database_schema.html",
        "meta_title": "PROTAC Builder Data And Schema Notes | PROTAC Builder",
        "meta_description": "Public-facing data and schema notes for PROTAC Builder, including curated linkers, ligase lists, recruiter mappings, and API-oriented resources.",
        "software_app_schema": False,
        "article_schema": True,
    },
    "release_notes": {
        "slug": "release-notes",
        "template": "pages/release_notes.html",
        "meta_title": "PROTAC Builder Release Notes | PROTAC Builder",
        "meta_description": "Release notes for the current PROTAC Builder site structure, including SEO pages, navigation updates, ecosystem links, and developer discovery files.",
        "software_app_schema": False,
        "article_schema": True,
    },
    "download_manifest": {
        "slug": "download-manifest",
        "template": "pages/download_manifest.html",
        "meta_title": "PROTAC Builder Download Manifest | PROTAC Builder",
        "meta_description": "Public download and API manifest for PROTAC Builder, including template linkers, API docs, OpenAPI files, llms.txt, and sitemap discovery.",
        "software_app_schema": False,
        "article_schema": True,
    },
    "case_studies": {
        "slug": "case-studies",
        "template": "pages/case_studies.html",
        "meta_title": "PROTAC Builder Case Studies | Warhead, Recruiter, Viral Target, and Batch Workflows",
        "meta_description": "Explore conceptual PROTAC Builder case studies showing warhead-first, E3 recruiter-first, viral target, and batch workflow paths through Warhead Hunter, E3 Ligandalyzer, V-LiSEMOD, PROTAC Builder, and downstream modeling.",
        "software_app_schema": False,
        "article_schema": True,
    },
    "submit_data": {
        "slug": "submit-data",
        "template": "pages/submit_data.html",
        "meta_title": "Submit Data Or Contribute | PROTAC Builder",
        "meta_description": "Learn how to contribute feedback, request additions, or work with the PROTAC Builder open-access ecosystem.",
        "software_app_schema": False,
        "article_schema": True,
    },
    "api_examples": {
        "slug": "api-examples",
        "template": "pages/api_examples.html",
        "meta_title": "PROTAC Builder API Examples | PROTAC Builder",
        "meta_description": "API examples for curated linkers, ligase lists, PROTAC generation, batch workflows, and machine-readable discovery files in PROTAC Builder.",
        "software_app_schema": False,
        "article_schema": True,
    },
    "batch_workflows": {
        "slug": "batch-workflows",
        "template": "pages/batch_workflows.html",
        "meta_title": "Batch Workflows | PROTAC Builder",
        "meta_description": "Use PROTAC Builder batch workflows for template linkers, API Builder payloads, builder batch routes, and downstream scripted pipelines.",
        "software_app_schema": False,
        "article_schema": True,
    },
}


SITEMAP_PATHS = [
    "/",
    "/builder",
    "/api-builder",
    "/api-docs",
    "/about",
    "/what-is-a-protac",
    "/how-to-build-a-protac",
    "/examples",
    "/component-hubs",
    "/warheads",
    "/linkers",
    "/e3-ligase-recruiters",
    "/constraint-driven-protac-design",
    "/in-silico-protac-modeling",
    "/benchmarking",
    "/downstream-modeling",
    "/ecosystem",
    "/faq",
    "/methods",
    "/database-schema",
    "/release-notes",
    "/download-manifest",
    "/case-studies",
    "/submit-data",
    "/api-examples",
    "/batch-workflows",
]


OPENAPI_SPEC: dict[str, Any] = {
    "openapi": "3.1.0",
    "info": {
        "title": "PROTAC Builder Public API",
        "version": "1.0.0",
        "description": "Public endpoints currently exposed by the Flask-based PROTAC Builder application. The spec is generated from the existing route surface and intentionally avoids undocumented claims.",
    },
    "servers": [{"url": PUBLIC_DOMAIN}],
    "paths": {
        "/api/linkers/curated": {"get": {"summary": "List curated linker templates", "responses": {"200": {"description": "Curated linker payload"}}}},
        "/api/ligases": {"get": {"summary": "List ligases exposed by the app", "responses": {"200": {"description": "Ligase list payload"}}}},
        "/api/ligase/render": {"get": {"summary": "Render a ligase structure representation", "responses": {"200": {"description": "Ligase render response"}}}},
        "/api/ligase/raw/{name}": {"get": {"summary": "Load raw ligase data by name", "parameters": [{"name": "name", "in": "path", "required": True, "schema": {"type": "string"}}], "responses": {"200": {"description": "Ligase raw response"}, "404": {"description": "Ligase not found"}}}},
        "/api/recruiter/{name}": {"get": {"summary": "Load recruiter data by name", "parameters": [{"name": "name", "in": "path", "required": True, "schema": {"type": "string"}}], "responses": {"200": {"description": "Recruiter response"}, "404": {"description": "Recruiter not found"}}}},
        "/api/recruiter/converted/{session_id}": {"get": {"summary": "Load converted recruiter data for a handoff session", "parameters": [{"name": "session_id", "in": "path", "required": True, "schema": {"type": "string"}}], "responses": {"200": {"description": "Converted recruiter response"}, "400": {"description": "Missing session ID"}}}},
        "/api/ligand/smiles": {"get": {"summary": "Fetch ligand SMILES data", "responses": {"200": {"description": "Ligand SMILES response"}}}},
        "/api/ligand/data": {"get": {"summary": "Fetch ligand data", "responses": {"200": {"description": "Ligand data response"}}}},
        "/api/ligand/modify": {"post": {"summary": "Modify ligand data", "responses": {"200": {"description": "Ligand modification response"}}}},
        "/api/ligand/store": {"post": {"summary": "Store ligand data", "responses": {"200": {"description": "Ligand storage response"}}}},
        "/api/molecule/smiles-to-mol": {"post": {"summary": "Convert SMILES to MOL", "responses": {"200": {"description": "Converted MOL payload"}}}},
        "/api/molecule/mol-to-smiles": {"post": {"summary": "Convert MOL to SMILES", "responses": {"200": {"description": "Converted SMILES payload"}}}},
        "/api/molecule/render-smiles": {"post": {"summary": "Render structure from SMILES", "responses": {"200": {"description": "Rendered structure response"}}}},
        "/api/protac/generate": {"post": {"summary": "Generate a PROTAC from components", "responses": {"200": {"description": "Generated PROTAC response"}}}},
        "/api/protac/download-smiles": {"post": {"summary": "Download generated PROTAC SMILES", "responses": {"200": {"description": "Download response"}}}},
        "/api/protac/log": {"post": {"summary": "Log frontend PROTAC activity", "responses": {"200": {"description": "Log acknowledgement"}}}},
        "/api/protac/batch-linkers": {"post": {"summary": "Generate PROTACs across linker batches", "responses": {"200": {"description": "Batch generation response"}}}},
        "/api/protac/structure/convert": {"post": {"summary": "Convert PROTAC structure representations", "responses": {"200": {"description": "Structure conversion response"}}}},
        "/api/protac/structure/mapped-smiles": {"post": {"summary": "Generate mapped SMILES for a structure", "responses": {"200": {"description": "Mapped SMILES response"}}}},
        "/api/protac/linkers/inspect": {"post": {"summary": "Inspect linker CSV input", "responses": {"200": {"description": "Linker inspection response"}}}},
        "/api/protac/builder/batch": {"post": {"summary": "Run builder batch workflow", "responses": {"200": {"description": "Builder batch response"}}}},
        "/api/protac/builder/cli": {"post": {"summary": "Run builder CLI-style workflow", "responses": {"200": {"description": "Builder CLI response"}}}},
        "/api/protac/builder/usage": {"get": {"summary": "Retrieve builder usage summary", "responses": {"200": {"description": "Usage summary"}}}},
        "/api/protac/builder/template/linkers": {"get": {"summary": "Download linker template CSV", "responses": {"200": {"description": "CSV download"}}}},
        "/api/protac/builder/template/download-count": {"get": {"summary": "Retrieve template download count", "responses": {"200": {"description": "Download count"}}}},
        "/api/warheadhunter/job/{job_id}": {"get": {"summary": "Retrieve proxied Warhead Hunter job index", "parameters": [{"name": "job_id", "in": "path", "required": True, "schema": {"type": "string"}}], "responses": {"200": {"description": "Warhead Hunter job metadata"}}}},
        "/api/warheadhunter/job/{job_id}/file/{filename}": {"get": {"summary": "Retrieve a proxied Warhead Hunter job file", "parameters": [{"name": "job_id", "in": "path", "required": True, "schema": {"type": "string"}}, {"name": "filename", "in": "path", "required": True, "schema": {"type": "string"}}], "responses": {"200": {"description": "Warhead Hunter file response"}}}},
        "/api/e3ligase/pdb/{ligase}/{filename}": {"get": {"summary": "Download a ligase PDB file", "parameters": [{"name": "ligase", "in": "path", "required": True, "schema": {"type": "string"}}, {"name": "filename", "in": "path", "required": True, "schema": {"type": "string"}}], "responses": {"200": {"description": "PDB file response"}}}},
        "/api/e3ligase/sdf/{ligase}/{filename}": {"get": {"summary": "Download a ligase SDF file", "parameters": [{"name": "ligase", "in": "path", "required": True, "schema": {"type": "string"}}, {"name": "filename", "in": "path", "required": True, "schema": {"type": "string"}}], "responses": {"200": {"description": "SDF file response"}}}},
        "/api/warhead/sdf/{pdb_id}/{ligand_code}": {"get": {"summary": "Download a warhead SDF file", "parameters": [{"name": "pdb_id", "in": "path", "required": True, "schema": {"type": "string"}}, {"name": "ligand_code", "in": "path", "required": True, "schema": {"type": "string"}}], "responses": {"200": {"description": "Warhead SDF response"}}}},
        "/api/deeppk/run": {"post": {"summary": "Run the DeepPK-related pipeline", "responses": {"200": {"description": "Pipeline response"}, "500": {"description": "Pipeline error"}}}},
        "/api/deeppk/download/{job_id}/{filename}": {"get": {"summary": "Download a DeepPK artifact", "parameters": [{"name": "job_id", "in": "path", "required": True, "schema": {"type": "string"}}, {"name": "filename", "in": "path", "required": True, "schema": {"type": "string"}}], "responses": {"200": {"description": "Artifact download"}, "404": {"description": "File not found"}}}},
        "/api/admet/run": {"post": {"summary": "Run ADMET report generation", "responses": {"200": {"description": "ADMET response"}, "400": {"description": "Bad input"}, "500": {"description": "Server error"}}}},
        "/api/admet/download/{filename}": {"get": {"summary": "Download an ADMET artifact", "parameters": [{"name": "filename", "in": "path", "required": True, "schema": {"type": "string"}}], "responses": {"200": {"description": "Artifact download"}, "404": {"description": "File not found"}}}},
    },
}


def get_page_meta(page_key: str) -> dict[str, Any]:
    page = deepcopy(PAGE_META[page_key])
    slug = page.get("slug", "")
    page["canonical_url"] = f"{PUBLIC_DOMAIN}/{slug}".rstrip("/")
    if not slug:
        page["canonical_url"] = PUBLIC_DOMAIN
    return page


def llms_text(base_url: str) -> str:
    lines = [
        "# PROTAC Builder",
        "",
        "Public pages",
        f"- Home: {base_url}/",
        f"- Builder: {base_url}/builder",
        f"- API Builder: {base_url}/api-builder",
        f"- API Docs: {base_url}/api-docs",
        f"- About: {base_url}/about",
        f"- What Is A PROTAC: {base_url}/what-is-a-protac",
        f"- How To Build A PROTAC: {base_url}/how-to-build-a-protac",
        f"- Examples: {base_url}/examples",
        f"- Component Hubs: {base_url}/component-hubs",
        f"- Warheads: {base_url}/warheads",
        f"- Linkers: {base_url}/linkers",
        f"- E3 Ligase Recruiters: {base_url}/e3-ligase-recruiters",
        f"- Constraint-Driven PROTAC Design: {base_url}/constraint-driven-protac-design",
        f"- In Silico PROTAC Modeling: {base_url}/in-silico-protac-modeling",
        f"- Benchmarking: {base_url}/benchmarking",
        f"- Downstream Modeling Tools: {base_url}/downstream-modeling",
        f"- Ecosystem: {base_url}/ecosystem",
        f"- FAQ: {base_url}/faq",
        f"- Methods: {base_url}/methods",
        f"- Database Schema Notes: {base_url}/database-schema",
        f"- Release Notes: {base_url}/release-notes",
        f"- Download Manifest: {base_url}/download-manifest",
        f"- API Examples: {base_url}/api-examples",
        f"- Batch Workflows: {base_url}/batch-workflows",
        "",
        "Machine-readable resources",
        f"- OpenAPI JSON: {base_url}/openapi.json",
        f"- OpenAPI YAML: {base_url}/openapi.yaml",
        f"- Sitemap: {base_url}/sitemap.xml",
        "",
        "Related ecosystem sites",
        "- Warhead Hunter: https://warheadhunter.com",
        "- E3 Ligandalyzer: https://e3ligandalyzer.com",
        "- V-LiSEMOD: Viral-Ligand Solvent Exposed Moiety Database for viral protein-ligand structures and warhead discovery. https://vlisemod.com",
    ]
    return "\n".join(lines) + "\n"


def yaml_dump(value: Any, indent: int = 0) -> str:
    space = "  " * indent
    if isinstance(value, dict):
        lines: list[str] = []
        for key, item in value.items():
            if isinstance(item, (dict, list)):
                lines.append(f"{space}{key}:")
                lines.append(yaml_dump(item, indent + 1))
            else:
                rendered = repr(item) if isinstance(item, str) and (":" in item or item.startswith("{")) else item
                if isinstance(item, str):
                    rendered = '"' + item.replace('"', '\\"') + '"'
                elif item is True:
                    rendered = "true"
                elif item is False:
                    rendered = "false"
                elif item is None:
                    rendered = "null"
                lines.append(f"{space}{key}: {rendered}")
        return "\n".join(lines)
    if isinstance(value, list):
        lines = []
        for item in value:
            if isinstance(item, (dict, list)):
                lines.append(f"{space}-")
                lines.append(yaml_dump(item, indent + 1))
            else:
                rendered: Any = item
                if isinstance(item, str):
                    rendered = '"' + item.replace('"', '\\"') + '"'
                elif item is True:
                    rendered = "true"
                elif item is False:
                    rendered = "false"
                elif item is None:
                    rendered = "null"
                lines.append(f"{space}- {rendered}")
        return "\n".join(lines)
    return f"{space}{value}"
