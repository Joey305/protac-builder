from __future__ import annotations

from copy import deepcopy
from datetime import date
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
        "href": "https://vlisemod.com/protacability_page",
        "description": "Review structure-guided readiness and context-specific modeling evidence.",
    },
    "vlisemod_home": {
        "label": "V-LiSEMOD",
        "href": "https://vlisemod.com",
        "description": "Structure-guided workspace for ligand exposure, triage, and downstream modeling context.",
    },
    "schurer_lab": {
        "label": "Schurer Lab",
        "href": "https://schurerlab.org",
        "description": "Research group behind the connected degrader discovery tool ecosystem.",
    },
}


def _link(label: str, href: str, description: str, *, external: bool = False) -> dict[str, Any]:
    return {
        "label": label,
        "href": href,
        "description": description,
        "external": external,
    }


def _card(
    title: str,
    body: str,
    href: str,
    *,
    kicker: str | None = None,
    cta: str | None = None,
    external: bool = False,
) -> dict[str, Any]:
    return {
        "title": title,
        "body": body,
        "href": href,
        "kicker": kicker,
        "cta": cta or ("Visit page" if not external else "Open site"),
        "external": external,
    }


def _page(
    *,
    slug: str,
    meta_title: str,
    meta_description: str,
    h1: str,
    kicker: str,
    intro: list[str],
    hero_actions: list[dict[str, Any]] | None = None,
    hero_pills: list[str] | None = None,
    sections: list[dict[str, Any]] | None = None,
    faq: list[dict[str, str]] | None = None,
    software_app_schema: bool = False,
    article_schema: bool = False,
) -> dict[str, Any]:
    return {
        "slug": slug,
        "meta_title": meta_title,
        "meta_description": meta_description,
        "h1": h1,
        "kicker": kicker,
        "intro": intro,
        "hero_actions": hero_actions or [],
        "hero_pills": hero_pills or [],
        "sections": sections or [],
        "faq": faq or [],
        "software_app_schema": software_app_schema,
        "article_schema": article_schema,
    }


PAGES: dict[str, dict[str, Any]] = {
    "home": _page(
        slug="",
        meta_title="PROTAC Builder - Free In Silico Degrader Design Tool",
        meta_description="Build PROTACs in a free web app that combines warheads, linkers, and E3 recruiters for in silico degrader design, API workflows, and downstream modeling handoff.",
        h1="PROTAC Builder - Free In Silico Degrader Design Tool",
        kicker="Schurer Lab Degrader Design",
        intro=[
            "PROTAC Builder is a free, server-rendered web application for assembling warheads, linkers, and E3 ligase recruiters into candidate degraders.",
            "The site is designed for medicinal chemists, chemical biologists, computational chemists, students, and workflow developers who need a practical starting point for in silico PROTAC design.",
            "Within the broader Schurer Lab ecosystem, Warhead Hunter supports warhead discovery, E3 Ligandalyzer supports recruiter and scaffold exploration, V-LiSEMOD supports structure-guided context assessment, and PROTAC Builder brings those component choices together for degrader assembly.",
        ],
        hero_pills=[
            "Warhead + linker + E3 recruiter workflow",
            "Browser-based builder and API surface",
            "Downstream modeling handoff",
            "Cautious, validation-first scientific framing",
        ],
        hero_actions=[
            _link("Launch PROTAC Builder", "/builder", "Open the interactive degrader assembly workflow."),
            _link("Open API Builder", "/api-builder", "Generate batch-oriented requests and workflow payloads."),
            _link("Read API Docs", "/api-docs", "Review documented public endpoints."),
        ],
        sections=[
            {
                "id": "workflow",
                "title": "Three-part PROTAC design workflow",
                "paragraphs": [
                    "A practical degrader design session starts with a target-binding warhead, an E3 ligase recruiter, and a linker that can bridge the two without forcing impossible geometry.",
                    "PROTAC Builder focuses on the assembly step: standardizing components, editing attachment atoms, generating merged structures, and preparing outputs for additional scoring, filtering, or structural modeling.",
                ],
                "cards": [
                    _card("Warhead discovery", "Start from target-binding chemistry and attachment-aware warhead exploration.", "/warheads", kicker="Component Hub", cta="Explore warheads"),
                    _card("Linker design", "Review linker length, polarity, flexibility, and bridgeability concepts before assembly.", "/linkers", kicker="Component Hub", cta="Explore linkers"),
                    _card("E3 recruiter discovery", "Compare recruiter classes, attachment vectors, and ligase context.", "/e3-ligase-recruiters", kicker="Component Hub", cta="Explore recruiters"),
                ],
            },
            {
                "id": "ecosystem",
                "title": "Connected discovery ecosystem",
                "paragraphs": [
                    "The site does not pretend to be a complete standalone library for every warhead, recruiter, or context dataset. Instead, it links cleanly into the sister tools that go deeper in each area.",
                ],
                "cards": [
                    _card("Warhead Hunter", ECOSYSTEM_LINKS["warhead_hunter"]["description"], ECOSYSTEM_LINKS["warhead_hunter"]["href"], kicker="Upstream Discovery", cta="Explore warheads in Warhead Hunter", external=True),
                    _card("E3 Ligandalyzer", ECOSYSTEM_LINKS["e3_ligandalyzer"]["description"], ECOSYSTEM_LINKS["e3_ligandalyzer"]["href"], kicker="Recruiter Discovery", cta="Inspect E3 recruiters in Ligandalyzer", external=True),
                    _card("V-LiSEMOD", ECOSYSTEM_LINKS["vlisemod"]["description"], ECOSYSTEM_LINKS["vlisemod"]["href"], kicker="Context And Triage", cta="Evaluate ligase and tissue context in V-LiSEMOD", external=True),
                    _card("Return to PROTAC Builder", "Bring chosen components back into the builder for degrader assembly and export.", "/builder", kicker="Assembly", cta="Return to PROTAC Builder"),
                ],
            },
            {
                "id": "learn",
                "title": "Learn, benchmark, and operationalize",
                "cards": [
                    _card("What is a PROTAC?", "Foundational explanation of targeted protein degradation and degrader anatomy.", "/what-is-a-protac", kicker="Educational"),
                    _card("How to build a PROTAC", "Step-by-step guide covering component selection, attachment points, and export.", "/how-to-build-a-protac", kicker="Practical Guide"),
                    _card("In silico PROTAC modeling", "Overview of restrained docking, refinement, scoring, and hybrid workflows.", "/in-silico-protac-modeling", kicker="Science"),
                    _card("Examples", "Browse example workflows for BRD4-, CRBN-, VHL-, API-, and handoff-oriented use cases.", "/examples", kicker="Examples"),
                ],
            },
        ],
        software_app_schema=True,
    ),
    "what_is_a_protac": _page(
        slug="what-is-a-protac",
        meta_title="What Is a PROTAC? | PROTAC Builder",
        meta_description="Learn what a PROTAC is, how proteolysis-targeting chimeras work, and why warheads, linkers, E3 recruiters, and ternary complex geometry matter.",
        h1="What Is a PROTAC?",
        kicker="Educational Pillar",
        intro=[
            "A PROTAC, or proteolysis-targeting chimera, is a bifunctional small molecule that brings a protein of interest into proximity with an E3 ligase so the target can be ubiquitinated and degraded by the proteasome.",
            "Most degrader concepts can be described through three structural parts: a target-binding warhead, a linker, and an E3 ligase recruiter.",
        ],
        hero_actions=[
            _link("Open the builder", "/builder", "Launch the interactive assembly workflow."),
            _link("Read the build guide", "/how-to-build-a-protac", "Follow a stepwise degrader design process."),
        ],
        sections=[
            {
                "id": "anatomy",
                "title": "Anatomy of a proteolysis-targeting chimera",
                "bullets": [
                    "Warhead: binds the protein of interest and defines the target-facing anchor.",
                    "Linker: connects both ends while shaping distance, flexibility, polarity, and projection.",
                    "E3 recruiter: binds an E3 ligase and defines the ligase-facing anchor and attachment vector.",
                ],
                "cards": [
                    _card("Warhead discovery", "Review target-binding context and handoff into degrader assembly.", "/warheads", kicker="Component"),
                    _card("Linker design", "Understand why geometry and bridgeability matter in degrader design.", "/linkers", kicker="Component"),
                    _card("E3 recruiter discovery", "Explore recruiter classes and attachment-vector considerations.", "/e3-ligase-recruiters", kicker="Component"),
                ],
            },
            {
                "id": "mechanism",
                "title": "How PROTACs recruit an E3 ligase",
                "paragraphs": [
                    "A degrader does not work by simple occupancy alone. Productive degradation depends on whether the molecule can support a compatible ternary complex between the protein of interest, the degrader, and the recruited E3 ligase.",
                    "That is why attachment atoms, linker geometry, and protein-protein orientation matter so much in modern computational PROTAC workflows.",
                ],
            },
            {
                "id": "next-steps",
                "title": "Where the connected tools fit",
                "cards": [
                    _card("Explore warheads in Warhead Hunter", "Use the sister site when you need deeper warhead discovery or target-context exploration.", ECOSYSTEM_LINKS["warhead_hunter"]["href"], kicker="External", cta="Open Warhead Hunter", external=True),
                    _card("Inspect E3 recruiters in Ligandalyzer", "Use recruiter, scaffold, and ligase-oriented views before final assembly.", ECOSYSTEM_LINKS["e3_ligandalyzer"]["href"], kicker="External", cta="Open E3 Ligandalyzer", external=True),
                    _card("Evaluate ligase context in V-LiSEMOD", "Use structure-guided triage and context pages where that evidence is relevant.", ECOSYSTEM_LINKS["vlisemod"]["href"], kicker="External", cta="Open V-LiSEMOD", external=True),
                    _card("Assemble in PROTAC Builder", "Return to the builder once you are ready to combine components.", "/builder", kicker="Assembly", cta="Return to builder"),
                ],
            },
        ],
        article_schema=True,
    ),
    "how_to_build_a_protac": _page(
        slug="how-to-build-a-protac",
        meta_title="How to Build a PROTAC | PROTAC Builder",
        meta_description="Follow a practical PROTAC design workflow covering warheads, E3 recruiters, linkers, attachment points, API generation, and downstream modeling handoff.",
        h1="How to Build a PROTAC",
        kicker="Practical Guide",
        intro=[
            "A practical PROTAC workflow starts by clarifying the target-binding warhead and the E3 recruiter before worrying about linker enumeration.",
            "The goal is not to claim guaranteed degradation, but to standardize components, choose sensible anchor points, and prepare structures for additional computational and experimental validation.",
        ],
        hero_actions=[
            _link("Launch PROTAC Builder", "/builder", "Start the interactive assembly workflow."),
            _link("Open examples", "/examples", "See concrete use cases."),
        ],
        sections=[
            {
                "id": "steps",
                "title": "Recommended staged workflow",
                "bullets": [
                    "Choose a target-binding warhead and confirm the intended protein-of-interest context.",
                    "Use Warhead Hunter when you need deeper warhead discovery or target-binding exploration.",
                    "Choose an E3 ligase recruiter and inspect recruiter/scaffold context in E3 Ligandalyzer when helpful.",
                    "Use V-LiSEMOD when structure-guided ligase or context triage is relevant to your question.",
                    "Choose a linker with realistic length, polarity, flexibility, and attachment geometry.",
                    "Define attachment atoms or anchor points on both ends before assembly.",
                    "Generate or load SMILES, MOL, or SDF representations where supported.",
                    "Run descriptor, ADMET, or DeepPK-related workflows where those outputs help downstream prioritization.",
                    "Export candidates into restrained ternary modeling, docking, or batch workflows.",
                    "Use API and batch tooling when screening larger enumerations.",
                ],
            },
            {
                "id": "tools",
                "title": "Recommended tools for each stage",
                "cards": [
                    _card("Warhead Hunter", "Deeper warhead and target-context discovery before degrader assembly.", ECOSYSTEM_LINKS["warhead_hunter"]["href"], kicker="Upstream", cta="Use Warhead Hunter", external=True),
                    _card("E3 Ligandalyzer", "Recruiter, scaffold, attachment-vector, and ligase-oriented exploration.", ECOSYSTEM_LINKS["e3_ligandalyzer"]["href"], kicker="Upstream", cta="Use E3 Ligandalyzer", external=True),
                    _card("V-LiSEMOD", "Context-heavy triage and structure-guided readiness review.", ECOSYSTEM_LINKS["vlisemod"]["href"], kicker="Upstream", cta="Use V-LiSEMOD", external=True),
                    _card("API Builder", "Generate batch-friendly payloads for larger screens and scripted workflows.", "/api-builder", kicker="Operationalize", cta="Open API Builder"),
                ],
            },
        ],
        article_schema=True,
    ),
    "examples": _page(
        slug="examples",
        meta_title="PROTAC Builder Examples | PROTAC Builder",
        meta_description="Browse example PROTAC Builder workflows for BRD4, CRBN, VHL, custom warheads, API batches, and cross-site handoffs from Warhead Hunter, E3 Ligandalyzer, and V-LiSEMOD.",
        h1="PROTAC Builder Examples",
        kicker="Workflow Gallery",
        intro=[
            "These examples are discovery-oriented workflow patterns rather than claims of validated degrader performance.",
            "Use them to understand how PROTAC Builder fits into component selection, API automation, and downstream modeling handoff.",
        ],
        sections=[
            {
                "id": "gallery",
                "title": "Example workflows",
                "cards": [
                    _card("Build a BRD4-oriented PROTAC", "Start from a bromodomain warhead concept and move into component assembly.", "/how-to-build-a-protac", kicker="Medicinal Chemistry", cta="Review workflow"),
                    _card("Build a CRBN-based PROTAC", "Open the builder with CRBN preselected for recruiter-side exploration.", "/builder?ligase=CRBN", kicker="Open In Builder", cta="Open CRBN in Builder"),
                    _card("Build a VHL-based PROTAC", "Open the builder with VHL preselected for recruiter-side exploration.", "/builder?ligase=VHL", kicker="Open In Builder", cta="Open VHL in Builder"),
                    _card("Use a custom warhead SMILES", "Start from a user-defined warhead instead of a preset example.", "/builder", kicker="Custom Input", cta="Open builder"),
                    _card("Move from Warhead Hunter to PROTAC Builder", "Use warhead-first discovery before returning to degrader assembly.", ECOSYSTEM_LINKS["warhead_hunter"]["href"], kicker="Cross-site Handoff", cta="Explore Warhead Hunter", external=True),
                    _card("Move from E3 Ligandalyzer to PROTAC Builder", "Inspect recruiter and scaffold context, then return with a session-aware handoff when available.", "https://e3ligandalyzer.com/explorer", kicker="Cross-site Handoff", cta="Explore E3 Ligandalyzer", external=True),
                    _card("Use V-LiSEMOD before choosing an E3 ligase", "Review structure-guided context and readiness signals before final assembly.", ECOSYSTEM_LINKS["vlisemod"]["href"], kicker="Cross-site Handoff", cta="Explore V-LiSEMOD", external=True),
                    _card("Batch-generate PROTACs with the API", "Prepare batch-oriented workflows from the API Builder and API docs.", "/api-builder", kicker="Automation", cta="Open API Builder"),
                    _card("Export to downstream modeling workflows", "Prepare componentized outputs for restrained ternary modeling and related evaluation.", "/downstream-modeling-tools", kicker="Modeling", cta="View downstream tools"),
                    _card("Run descriptor and prediction workflows", "Use documented ADMET and DeepPK-adjacent outputs when supported.", "/api-docs", kicker="Prediction", cta="Read API docs"),
                ],
            }
        ],
        article_schema=True,
    ),
    "component_hubs": _page(
        slug="component-hubs",
        meta_title="PROTAC Component Hubs | PROTAC Builder",
        meta_description="Browse PROTAC component hubs for warheads, linkers, and E3 ligase recruiters, with links into Warhead Hunter, E3 Ligandalyzer, V-LiSEMOD, and the PROTAC Builder assembly workflow.",
        h1="PROTAC Component Hubs",
        kicker="Discovery Hubs",
        intro=[
            "PROTAC Builder connects the three core component classes used in degrader design, but deeper component-specific exploration often lives in sister tools.",
            "These pages are discovery hubs and guides, not blanket claims of complete molecular libraries.",
        ],
        sections=[
            {
                "id": "components",
                "title": "Three component areas",
                "cards": [
                    _card("Warhead discovery", "Target-binding chemistry, attachment-aware design, and target context.", "/warheads", kicker="Hub", cta="Explore warheads"),
                    _card("Linker design", "Geometry, bridgeability, polarity, and feasibility considerations.", "/linkers", kicker="Hub", cta="Explore linkers"),
                    _card("E3 recruiter discovery", "Recruiter classes, scaffolds, attachment vectors, and ligase context.", "/e3-ligase-recruiters", kicker="Hub", cta="Explore recruiters"),
                ],
            },
            {
                "id": "ecosystem",
                "title": "Related component resources",
                "cards": [
                    _card("Warhead Hunter", ECOSYSTEM_LINKS["warhead_hunter"]["description"], ECOSYSTEM_LINKS["warhead_hunter"]["href"], kicker="External", cta="Explore warheads in Warhead Hunter", external=True),
                    _card("E3 Ligandalyzer", ECOSYSTEM_LINKS["e3_ligandalyzer_scaffolds"]["description"], ECOSYSTEM_LINKS["e3_ligandalyzer_scaffolds"]["href"], kicker="External", cta="Inspect E3 recruiters in Ligandalyzer", external=True),
                    _card("V-LiSEMOD", ECOSYSTEM_LINKS["vlisemod"]["description"], ECOSYSTEM_LINKS["vlisemod"]["href"], kicker="External", cta="Review context in V-LiSEMOD", external=True),
                    _card("PROTAC Builder", "Return here to assemble chosen components into candidate degraders.", "/builder", kicker="Assembly", cta="Open builder"),
                ],
            },
        ],
        article_schema=True,
    ),
    "warheads": _page(
        slug="warheads",
        meta_title="PROTAC Warhead Discovery Hub | PROTAC Builder",
        meta_description="Learn how warheads function in PROTAC design, why attachment context matters, and when to use Warhead Hunter and PROTAC Builder together.",
        h1="PROTAC Warhead Discovery Hub",
        kicker="Warhead Discovery",
        intro=[
            "A warhead is the target-binding part of a PROTAC. It determines the protein-of-interest context, possible attachment vectors, and much of the downstream feasibility of ternary complex formation.",
            "This page is a discovery hub rather than a claim of a complete standalone warhead library inside PROTAC Builder.",
        ],
        sections=[
            {
                "id": "role",
                "title": "Why warhead context matters",
                "bullets": [
                    "Warhead pose and solvent exposure shape where a linker can be attached.",
                    "Attachment atom choice influences exit vector, steric burden, and bridgeability.",
                    "Target-specific warhead chemistry often needs more context than an assembly tool alone can provide.",
                ],
            },
            {
                "id": "handoff",
                "title": "Recommended workflow",
                "cards": [
                    _card("Explore warheads in Warhead Hunter", "Use warhead-first discovery and examples before degrader assembly.", ECOSYSTEM_LINKS["warhead_hunter"]["href"], kicker="External", cta="Open Warhead Hunter", external=True),
                    _card("Assemble in PROTAC Builder", "Bring the chosen target-binding ligand back into the builder.", "/builder", kicker="Assembly", cta="Return to builder"),
                    _card("See examples", "Review cross-site and component-aware example workflows.", "/examples", kicker="Examples", cta="Open examples"),
                ],
            },
        ],
        article_schema=True,
    ),
    "linkers": _page(
        slug="linkers",
        meta_title="PROTAC Linker Design Hub | PROTAC Builder",
        meta_description="Learn how linker length, polarity, flexibility, rigidity, and bridgeability affect PROTAC design and downstream ternary complex feasibility.",
        h1="PROTAC Linker Design Hub",
        kicker="Linker Design",
        intro=[
            "Linkers do more than connect two fragments. In PROTAC design they influence whether the target and E3 ligase can adopt a productive ternary arrangement.",
            "This hub focuses on linker geometry and feasibility rather than claiming a complete linker library.",
        ],
        sections=[
            {
                "id": "properties",
                "title": "Design dimensions to watch",
                "bullets": [
                    "Length and end-to-end reach",
                    "Polarity and physicochemical burden",
                    "Flexibility versus conformational bias",
                    "Attachment geometry and vector alignment",
                    "Constraint-driven bridgeability between anchors",
                ],
            },
            {
                "id": "next",
                "title": "Where to go next",
                "cards": [
                    _card("Open the builder", "Use curated linker templates and molecule assembly workflows.", "/builder", kicker="Assembly", cta="Open builder"),
                    _card("How to build a PROTAC", "Follow the staged workflow for selecting anchors and linkers.", "/how-to-build-a-protac", kicker="Guide", cta="Read the guide"),
                    _card("Downstream modeling tools", "See how linker choices feed into restrained ternary modeling and refinement.", "/downstream-modeling-tools", kicker="Modeling", cta="View downstream tools"),
                ],
            },
        ],
        article_schema=True,
    ),
    "e3_ligase_recruiters": _page(
        slug="e3-ligase-recruiters",
        meta_title="E3 Ligase Recruiter Discovery Hub | PROTAC Builder",
        meta_description="Learn how E3 ligase recruiters function in PROTAC design and when to use E3 Ligandalyzer and V-LiSEMOD before returning to PROTAC Builder.",
        h1="E3 Ligase Recruiter Discovery Hub",
        kicker="Recruiter Discovery",
        intro=[
            "E3 ligase recruiters anchor the degrader to a chosen ligase system and define a recruiter-side attachment vector.",
            "The right recruiter choice depends on scaffold geometry, exposure, ligase context, and downstream feasibility, so this page points to deeper recruiter-specific resources where available.",
        ],
        sections=[
            {
                "id": "concepts",
                "title": "What to evaluate",
                "bullets": [
                    "Recruiter scaffold and chemotype",
                    "Attachment-vector and exit-vector considerations",
                    "Ligase context and available structural evidence",
                    "Compatibility with the chosen warhead and linker concept",
                ],
                "paragraphs": [
                    "Examples like CRBN and VHL are common teaching cases, but the page avoids claiming a complete recruiter catalog unless that data is available locally.",
                ],
            },
            {
                "id": "tools",
                "title": "Connected tools for recruiter selection",
                "cards": [
                    _card("Inspect E3 recruiters in Ligandalyzer", "Use the recruiter explorer, ligand detail pages, and scaffold views.", ECOSYSTEM_LINKS["e3_ligandalyzer"]["href"], kicker="External", cta="Open E3 Ligandalyzer", external=True),
                    _card("Review context in V-LiSEMOD", "Use structure-guided context pages when ligase or system context matters to the decision.", ECOSYSTEM_LINKS["vlisemod"]["href"], kicker="External", cta="Open V-LiSEMOD", external=True),
                    _card("Return to PROTAC Builder", "Bring the chosen recruiter back into degrader assembly.", "/builder", kicker="Assembly", cta="Return to builder"),
                ],
            },
        ],
        article_schema=True,
    ),
    "constraint_driven_protac_design": _page(
        slug="constraint-driven-protac-design",
        meta_title="Constraint-Driven PROTAC Design | PROTAC Builder",
        meta_description="Learn how anchor atoms, distance restraints, linker bridgeability, and ternary complex geometry shape constraint-driven computational PROTAC design.",
        h1="Constraint-Driven PROTAC Design",
        kicker="Science",
        intro=[
            "Constraint-driven PROTAC design treats linker assembly as a geometry problem as well as a medicinal chemistry problem.",
            "Rather than assuming any warhead-linker-recruiter combination is plausible, the workflow asks whether anchor atoms, distances, orientations, and bridgeability support a realistic ternary arrangement.",
        ],
        sections=[
            {
                "id": "concepts",
                "title": "Core constraints",
                "bullets": [
                    "Anchor atoms or attachment atoms on both component ends",
                    "Distance restraints between exit vectors",
                    "Linker bridgeability across candidate protein-protein orientations",
                    "Compatibility between linker flexibility and desired geometry",
                    "Selective export into downstream ternary complex modeling",
                ],
            },
            {
                "id": "workflow",
                "title": "Practical staged workflow",
                "bullets": [
                    "Define warhead and recruiter anchors.",
                    "Choose or enumerate linkers.",
                    "Check geometric feasibility and bridgeability.",
                    "Generate candidate PROTACs.",
                    "Export to downstream ternary modeling.",
                    "Rank and validate with structure-based or learned methods.",
                ],
                "paragraphs": [
                    "PROTAC Builder helps with representation, anchor editing, and candidate assembly. It does not guarantee degradation outcomes and should be treated as a preparation layer in a broader validation workflow.",
                ],
            },
        ],
        article_schema=True,
    ),
    "in_silico_protac_modeling": _page(
        slug="in-silico-protac-modeling",
        meta_title="In Silico PROTAC Modeling | PROTAC Builder",
        meta_description="Overview of restrained docking, PRosettaC-style modeling, MD refinement, HAPOD-like scoring, learned re-ranking, and hybrid in silico PROTAC workflows.",
        h1="In Silico PROTAC Modeling",
        kicker="Science",
        intro=[
            "Computational PROTAC design spans component selection, ternary complex construction, refinement, ranking, and downstream prioritization.",
            "A strong workflow usually combines geometry-aware filters with structure-based and learned methods instead of relying on a single score.",
        ],
        sections=[
            {
                "id": "methods",
                "title": "Method families",
                "bullets": [
                    "Restrained or tethered docking for ternary construction",
                    "PRosettaC-style anchor and distance-constrained workflows",
                    "Molecular dynamics refinement and dynamic stability review",
                    "HAPOD-style or interface-focused scoring ideas",
                    "Energy landscape and solvation-aware analyses",
                    "Field-based or grid-based scoring methods",
                    "Data-driven ranking and generative design pipelines",
                ],
            },
            {
                "id": "hybrid",
                "title": "Hybrid staged workflow",
                "paragraphs": [
                    "A practical staged workflow often standardizes representation first, performs rapid geometric screening second, uses learned reranking where it adds value, and reserves expensive ensemble validation for a smaller prioritized set.",
                ],
                "cards": [
                    _card("Constraint-driven design", "Start from anchor-aware feasibility before heavy modeling.", "/constraint-driven-protac-design", kicker="Upstream"),
                    _card("Benchmarking", "Review what should be reported when evaluating modeling pipelines.", "/benchmarking", kicker="Credibility"),
                    _card("Downstream tools", "See how builder outputs feed into ternary modeling and scoring workflows.", "/downstream-modeling-tools", kicker="Operational"),
                ],
            },
        ],
        article_schema=True,
    ),
    "benchmarking": _page(
        slug="benchmarking",
        meta_title="PROTAC Modeling Benchmarking | PROTAC Builder",
        meta_description="Benchmarking guidance for PROTAC ternary structure prediction, pose ranking, degradation outcome prediction, generative design evaluation, and reproducible reporting.",
        h1="PROTAC Modeling Benchmarking",
        kicker="Benchmarking Hub",
        intro=[
            "Benchmarking is a major bottleneck in computational PROTAC design because datasets, representations, scoring conventions, and domains of applicability are still fragmented.",
            "This page focuses on what should be reported and compared, not on invented benchmark wins.",
        ],
        sections=[
            {
                "id": "areas",
                "title": "Benchmarking areas",
                "bullets": [
                    "Ternary structure prediction",
                    "Pose ranking and enrichment",
                    "Degradation outcome prediction",
                    "Generative design evaluation",
                    "Domain shift across new E3 ligases, targets, and linker chemotypes",
                    "Scoring robustness and calibration",
                    "Representation and conformer standardization",
                ],
            },
            {
                "id": "reporting",
                "title": "Recommended reporting elements",
                "bullets": [
                    "System definition and scope",
                    "PROTAC representation and attachment-point notation",
                    "Conformer and structure preparation details",
                    "Modeling protocol and scoring rules",
                    "Evaluation criteria and controls",
                    "Negative or challenging examples",
                    "Reproducibility assets and versioning",
                    "Domain of applicability",
                ],
            },
        ],
        article_schema=True,
    ),
    "downstream_modeling_tools": _page(
        slug="downstream-modeling-tools",
        meta_title="Downstream Modeling Tools for PROTAC Design | PROTAC Builder",
        meta_description="See how PROTAC Builder outputs can feed into restrained ternary modeling, docking, molecular dynamics, interface metrics, descriptor workflows, and batch pipelines.",
        h1="Downstream Modeling Tools",
        kicker="Workflow Integration",
        intro=[
            "Builder outputs are best treated as inputs for deeper modeling, filtering, and experimental design rather than as final answers.",
            "The strongest workflows combine clean component representation with follow-on scoring, structural validation, and domain-aware interpretation.",
        ],
        sections=[
            {
                "id": "categories",
                "title": "Common downstream categories",
                "bullets": [
                    "PRosettaC-style restrained ternary modeling",
                    "Docking and ternary pose construction workflows",
                    "Molecular dynamics refinement",
                    "DockQ and interface metric analysis",
                    "Linker geometry and bridgeability checks",
                    "RDKit descriptor workflows",
                    "ADMET or DeepPK-adjacent screening where supported",
                    "Notebook, server, and batch-generation pipelines",
                    "Machine-learning reranking and generative design systems",
                ],
            },
            {
                "id": "caveat",
                "title": "Important caveat",
                "paragraphs": [
                    "Exported structures, descriptors, and generated candidates remain hypotheses. They should be interpreted alongside assay design, structure review, and experimental validation rather than as claims of guaranteed degradation.",
                ],
            },
        ],
        article_schema=True,
    ),
    "ecosystem": _page(
        slug="ecosystem",
        meta_title="Schurer Lab PROTAC Design Ecosystem | PROTAC Builder",
        meta_description="Learn how PROTAC Builder connects with Warhead Hunter, E3 Ligandalyzer, V-LiSEMOD, and API workflows across the Schurer Lab degrader discovery ecosystem.",
        h1="Schurer Lab PROTAC Design Ecosystem",
        kicker="Connected Tools",
        intro=[
            "The degrader design workflow spans multiple questions, so the ecosystem is intentionally distributed across tools instead of forcing every function into one interface.",
            "PROTAC Builder is the assembly layer that connects upstream warhead, recruiter, and context work to downstream modeling handoff.",
        ],
        sections=[
            {
                "id": "tools",
                "title": "Tool roles",
                "cards": [
                    _card("PROTAC Builder", "Assemble warhead, linker, and E3 recruiter components into candidate degraders.", "/builder", kicker="Assembly", cta="Open PROTAC Builder"),
                    _card("Warhead Hunter", "Explore target-binding warheads and warhead-focused discovery context.", ECOSYSTEM_LINKS["warhead_hunter_home"]["href"], kicker="Discovery", cta="Open Warhead Hunter", external=True),
                    _card("E3 Ligandalyzer", "Inspect E3 recruiters, ligase scaffolds, ligand pages, and attachment context.", ECOSYSTEM_LINKS["e3_ligandalyzer"]["href"], kicker="Recruiters", cta="Open E3 Ligandalyzer", external=True),
                    _card("V-LiSEMOD", "Explore structure-guided readiness, context, and downstream triage views where relevant.", ECOSYSTEM_LINKS["vlisemod_home"]["href"], kicker="Context", cta="Open V-LiSEMOD", external=True),
                    _card("API Builder And Docs", "Move from interactive design into scripted, notebook, or batch-oriented workflows.", "/api-builder", kicker="Developer", cta="Open API Builder"),
                ],
            },
            {
                "id": "journey",
                "title": "Typical user journey",
                "bullets": [
                    "Explore target-binding chemistry in Warhead Hunter when the warhead decision is still open.",
                    "Inspect recruiter or scaffold context in E3 Ligandalyzer when the recruiter choice is still open.",
                    "Use V-LiSEMOD when structure-guided context or readiness evidence matters to the question.",
                    "Return to PROTAC Builder to assemble the degrader and prepare outputs for downstream modeling or batch workflows.",
                ],
            },
        ],
        article_schema=True,
    ),
    "faq": _page(
        slug="faq",
        meta_title="PROTAC Builder FAQ | PROTAC Builder",
        meta_description="Frequently asked questions about PROTAC Builder, its scope, sister tools, API workflows, and how to interpret generated degrader candidates.",
        h1="PROTAC Builder FAQ",
        kicker="Resources",
        intro=[
            "These answers focus on scope, workflow fit, and careful interpretation of generated outputs.",
        ],
        faq=[
            {
                "question": "Does PROTAC Builder guarantee that a generated molecule will degrade the target?",
                "answer": "No. The builder standardizes components and assembles candidate degraders, but degradation still depends on broader structural, biophysical, cellular, and experimental factors.",
            },
            {
                "question": "Is this site a complete library of all warheads, linkers, or recruiters?",
                "answer": "No. The site provides component hubs and assembly workflows, while deeper component-specific exploration may live in Warhead Hunter, E3 Ligandalyzer, or other connected resources.",
            },
            {
                "question": "When should I use Warhead Hunter or E3 Ligandalyzer first?",
                "answer": "Use Warhead Hunter when the target-binding ligand is still under exploration, and use E3 Ligandalyzer when recruiter, scaffold, or ligase-side attachment context is still under exploration.",
            },
            {
                "question": "Can I use PROTAC Builder in scripted or batch workflows?",
                "answer": "Yes. The site exposes API-oriented routes and an API Builder page to help with notebook, server, and batch workflows.",
            },
        ],
        article_schema=True,
    ),
    "methods": _page(
        slug="methods",
        meta_title="PROTAC Builder Methods | PROTAC Builder",
        meta_description="Methods overview for PROTAC Builder, including component assembly, attachment editing, template linkers, and downstream workflow positioning.",
        h1="PROTAC Builder Methods",
        kicker="Resources",
        intro=[
            "PROTAC Builder focuses on component assembly, attachment editing, and workflow handoff rather than on claiming an end-to-end degradation prediction engine.",
        ],
        sections=[
            {
                "id": "scope",
                "title": "Current method scope",
                "bullets": [
                    "Warhead, linker, and recruiter component assembly",
                    "Attachment-point editing in the browser",
                    "Curated linker template support",
                    "Generated structure export and workflow handoff",
                    "Descriptor and API-adjacent workflow support where implemented",
                ],
            }
        ],
        article_schema=True,
    ),
    "database_schema": _page(
        slug="database-schema",
        meta_title="PROTAC Builder Data And Schema Notes | PROTAC Builder",
        meta_description="Public-facing data and schema notes for PROTAC Builder, including curated linkers, ligase lists, recruiter mappings, and API-oriented resources.",
        h1="Data And Schema Notes",
        kicker="Developer Resources",
        intro=[
            "The public-facing app uses a small set of structured files and API responses rather than exposing a single downloadable relational database schema.",
            "This page summarizes the current public surface so developers can understand what is actually available.",
        ],
        sections=[
            {
                "id": "files",
                "title": "Current structured resources",
                "bullets": [
                    "Curated linker template CSV",
                    "Ligase list JSON",
                    "Recruiter-to-PDB mapping JSON",
                    "Generated PROTAC log CSV",
                    "API templates and usage summaries",
                ],
            }
        ],
        article_schema=True,
    ),
    "release_notes": _page(
        slug="release-notes",
        meta_title="PROTAC Builder Release Notes | PROTAC Builder",
        meta_description="Release notes for the current PROTAC Builder site structure, including SEO pages, navigation updates, ecosystem links, and developer discovery files.",
        h1="Release Notes",
        kicker="Resources",
        intro=[
            f"Current release snapshot: {date.today().strftime('%B %d, %Y')}.",
            "This release organizes educational pages, component hubs, science pages, and ecosystem links around the existing builder and API workflows.",
        ],
        sections=[
            {
                "id": "highlights",
                "title": "Highlights",
                "bullets": [
                    "New educational and discovery pages for PROTAC design queries",
                    "Dropdown-based navigation grouping for Builder, Discovery, Science, Resources, Ecosystem, and Developer",
                    "Cross-site linking to Warhead Hunter, E3 Ligandalyzer, and V-LiSEMOD",
                    "Dynamic sitemap, robots, llms, and OpenAPI exposure for public discovery",
                ],
            }
        ],
        article_schema=True,
    ),
    "download_manifest": _page(
        slug="download-manifest",
        meta_title="PROTAC Builder Download Manifest | PROTAC Builder",
        meta_description="Public download and API manifest for PROTAC Builder, including template linkers, API docs, OpenAPI files, llms.txt, and sitemap discovery.",
        h1="Download Manifest",
        kicker="Developer Resources",
        intro=[
            "This manifest lists the public resources that can be downloaded or indexed directly from the current site.",
        ],
        sections=[
            {
                "id": "manifest",
                "title": "Public resources",
                "cards": [
                    _card("Template linkers CSV", "Download the curated linker template used for batch builder workflows.", "/api/protac/builder/template/linkers", kicker="Download", cta="Download CSV"),
                    _card("API docs", "Human-readable documentation for public API routes.", "/api-docs", kicker="Docs"),
                    _card("OpenAPI JSON", "Machine-readable API description generated from current routes.", "/openapi.json", kicker="Machine Readable", cta="Open JSON"),
                    _card("OpenAPI YAML", "YAML version of the public API description.", "/openapi.yaml", kicker="Machine Readable", cta="Open YAML"),
                    _card("llms.txt", "Plain-text discovery guide for agents and automated readers.", "/llms.txt", kicker="Discovery", cta="Open llms.txt"),
                    _card("Sitemap", "XML sitemap for public pages.", "/sitemap.xml", kicker="Discovery", cta="Open sitemap"),
                ],
            }
        ],
        article_schema=True,
    ),
    "case_studies": _page(
        slug="case-studies",
        meta_title="PROTAC Builder Case Studies | PROTAC Builder",
        meta_description="Case-study style examples showing how PROTAC Builder fits with warhead discovery, recruiter exploration, and downstream modeling workflows.",
        h1="Case Studies",
        kicker="Resources",
        intro=[
            "These case studies describe workflow patterns and tool fit. They are not claims of experimentally validated degradation outcomes by the web app alone.",
        ],
        sections=[
            {
                "id": "cases",
                "title": "Case-study themes",
                "cards": [
                    _card("Warhead-first workflow", "Move from target-binding exploration in Warhead Hunter into component assembly.", ECOSYSTEM_LINKS["warhead_hunter"]["href"], kicker="Case Study", cta="Open Warhead Hunter", external=True),
                    _card("Recruiter-first workflow", "Move from recruiter-side analysis in E3 Ligandalyzer into degrader assembly.", ECOSYSTEM_LINKS["e3_ligandalyzer"]["href"], kicker="Case Study", cta="Open E3 Ligandalyzer", external=True),
                    _card("Context-first workflow", "Review structure-guided readiness in V-LiSEMOD before final assembly.", ECOSYSTEM_LINKS["vlisemod"]["href"], kicker="Case Study", cta="Open V-LiSEMOD", external=True),
                    _card("Batch workflow", "Use API Builder and API docs to move from interactive design to scripted generation.", "/api-builder", kicker="Case Study", cta="Open API Builder"),
                ],
            }
        ],
        article_schema=True,
    ),
    "submit_data": _page(
        slug="submit-data",
        meta_title="Submit Data Or Contribute | PROTAC Builder",
        meta_description="Learn how to contribute feedback, request additions, or work with the PROTAC Builder open-access ecosystem.",
        h1="Submit Data Or Contribute",
        kicker="Community",
        intro=[
            "The safest current contribution paths are through the public repository, issue reporting, and coordinated updates across the related Schurer Lab tools.",
        ],
        sections=[
            {
                "id": "paths",
                "title": "Contribution paths",
                "bullets": [
                    "Open issues or discussion threads in the public GitHub repository when relevant.",
                    "Request new examples, documentation improvements, or workflow clarifications.",
                    "Coordinate cross-tool updates when a feature spans PROTAC Builder, Warhead Hunter, E3 Ligandalyzer, or V-LiSEMOD.",
                ],
                "cards": [
                    _card("GitHub repository", "Review the public project repository and documentation.", "https://github.com/schurerlab/protacbuilder", kicker="External", cta="Open GitHub", external=True),
                    _card("About page", "Review the project background and scientific framing.", "/about", kicker="Local", cta="Open About"),
                ],
            }
        ],
        article_schema=True,
    ),
    "api_examples": _page(
        slug="api-examples",
        meta_title="PROTAC Builder API Examples | PROTAC Builder",
        meta_description="API examples for curated linkers, ligase lists, PROTAC generation, batch workflows, and machine-readable discovery files in PROTAC Builder.",
        h1="API Examples",
        kicker="Developer",
        intro=[
            "These examples point to documented public routes that can be used in notebooks, scripts, and lightweight automation.",
        ],
        sections=[
            {
                "id": "examples",
                "title": "Useful starting points",
                "cards": [
                    _card("Curated linkers", "Fetch the curated linker list used by the builder.", "/api/linkers/curated", kicker="GET", cta="Open endpoint"),
                    _card("Ligase list", "Retrieve the current ligase list exposed by the app.", "/api/ligases", kicker="GET", cta="Open endpoint"),
                    _card("Template linkers download", "Download the CSV template for batch builder workflows.", "/api/protac/builder/template/linkers", kicker="GET", cta="Download template"),
                    _card("API docs", "Review the rest of the documented route surface.", "/api-docs", kicker="Docs", cta="Read docs"),
                ],
            }
        ],
        article_schema=True,
    ),
    "batch_workflows": _page(
        slug="batch-workflows",
        meta_title="Batch Workflows | PROTAC Builder",
        meta_description="Use PROTAC Builder batch workflows for template linkers, API Builder payloads, builder batch routes, and downstream scripted pipelines.",
        h1="Batch Workflows",
        kicker="Developer",
        intro=[
            "Batch workflows help move from one-off interactive assembly to reproducible screening and scripted enumeration.",
        ],
        sections=[
            {
                "id": "batch",
                "title": "Suggested batch workflow",
                "bullets": [
                    "Download the template linker CSV.",
                    "Prepare warhead and recruiter inputs with consistent attachment notation.",
                    "Use the API Builder to shape requests.",
                    "Send batch-oriented requests through the documented builder routes.",
                    "Export results into descriptor, scoring, or downstream modeling pipelines.",
                ],
                "cards": [
                    _card("API Builder", "Build batch-friendly payloads from the UI.", "/api-builder", kicker="UI"),
                    _card("API docs", "Review the current public batch routes.", "/api-docs", kicker="Docs"),
                    _card("Download manifest", "See machine-readable discovery resources and downloads.", "/download-manifest", kicker="Resources"),
                ],
            }
        ],
        article_schema=True,
    ),
}


ALIAS_TO_PAGE = {
    "home": "home",
    "what-is-a-protac": "what_is_a_protac",
    "how-to-build-a-protac": "how_to_build_a_protac",
    "examples": "examples",
    "component-hubs": "component_hubs",
    "warheads": "warheads",
    "linkers": "linkers",
    "e3-ligase-recruiters": "e3_ligase_recruiters",
    "constraint-driven-protac-design": "constraint_driven_protac_design",
    "in-silico-protac-modeling": "in_silico_protac_modeling",
    "benchmarking": "benchmarking",
    "downstream-modeling-tools": "downstream_modeling_tools",
    "ecosystem": "ecosystem",
    "faq": "faq",
    "methods": "methods",
    "database-schema": "database_schema",
    "release-notes": "release_notes",
    "download-manifest": "download_manifest",
    "case-studies": "case_studies",
    "submit-data": "submit_data",
    "api-examples": "api_examples",
    "batch-workflows": "batch_workflows",
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
    "/downstream-modeling-tools",
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


def get_page(page_key: str) -> dict[str, Any]:
    page = deepcopy(PAGES[page_key])
    slug = page.get("slug", "")
    page["canonical_url"] = f"{PUBLIC_DOMAIN}/{slug}".rstrip("/")
    if slug == "":
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
        f"- Downstream Modeling Tools: {base_url}/downstream-modeling-tools",
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
        "- V-LiSEMOD: https://vlisemod.com",
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
