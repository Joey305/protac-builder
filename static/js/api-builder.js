(function () {
  if (!document.body || document.body.dataset.page !== "api-builder") return;

  let warheadSketcher = null;
  let ligaseSketcher = null;
  let WARHEAD_MAPPED_SMILES = "";
  let LIGASE_MAPPED_SMILES = "";
  let LINKER_FILE = null;
  let LINKER_COLUMNS = [];
  let CSV_PREVIEW_ROWS = [];
  let SELECTED_NAME_COL = "";
  let SELECTED_SMILES_COL = "";
  let LAST_RESULTS = [];
  let LAST_FAILURES = [];
  let VISIBILITY_LISTENER_REGISTERED = false;
  let API_BUILDER_STARTED = false;


  const API_BUILDER_DEBUG_VERSION = "2026-05-29-debug-chem-v1";
  const API_BUILDER_DEBUG = true;
  let SCRIPT_LOAD_ATTEMPT = 0;
  let FETCH_COUNTER = 0;

  function debugTimestamp() {
    try {
      return new Date().toISOString();
    } catch (_error) {
      return String(Date.now());
    }
  }

  function debugLog(label, payload) {
    if (!API_BUILDER_DEBUG) return;
    if (payload === undefined) {
      console.log(`[api-builder ${API_BUILDER_DEBUG_VERSION}] ${label}`);
      return;
    }
    console.log(`[api-builder ${API_BUILDER_DEBUG_VERSION}] ${label}`, payload);
  }

  function debugWarn(label, payload) {
    if (payload === undefined) {
      console.warn(`[api-builder ${API_BUILDER_DEBUG_VERSION}] ${label}`);
      return;
    }
    console.warn(`[api-builder ${API_BUILDER_DEBUG_VERSION}] ${label}`, payload);
  }

  function debugError(label, payload) {
    if (payload === undefined) {
      console.error(`[api-builder ${API_BUILDER_DEBUG_VERSION}] ${label}`);
      return;
    }
    console.error(`[api-builder ${API_BUILDER_DEBUG_VERSION}] ${label}`, payload);
  }

  function shortText(value, limit = 900) {
    const text = String(value ?? "");
    const compact = text.replace(/\s+/g, " ").trim();
    if (compact.length <= limit) return compact;
    return `${compact.slice(0, limit).trim()}…`;
  }

  function looksLikeHtml(text) {
    return /<!doctype html|<html|<head|<body|<title|application error/i.test(String(text || ""));
  }

  function formatError(error) {
    if (!error) return { message: "Unknown error" };
    return {
      name: error.name || "Error",
      message: error.message || String(error),
      stack: error.stack || "",
    };
  }

  function formDataSummary(body) {
    if (!(body instanceof FormData)) return null;
    const rows = [];
    body.forEach((value, key) => {
      if (value instanceof File) {
        rows.push({
          key,
          type: "File",
          name: value.name,
          size: value.size,
          mime: value.type || "",
        });
      } else {
        const text = String(value ?? "");
        rows.push({
          key,
          type: "field",
          length: text.length,
          preview: shortText(text, 180),
        });
      }
    });
    return rows;
  }

  function headersSummary(headers) {
    const out = {};
    try {
      if (!headers) return out;
      headers.forEach((value, key) => {
        out[key] = value;
      });
    } catch (_error) {
      return out;
    }
    return out;
  }

  function getChemDoodleGlobal() {
    let cd = null;

    try {
      if (window.ChemDoodle) cd = window.ChemDoodle;
    } catch (_error) {
      cd = null;
    }

    try {
      if (!cd && typeof globalThis !== "undefined" && globalThis.ChemDoodle) {
        cd = globalThis.ChemDoodle;
      }
    } catch (_error) {
      // ignore
    }

    try {
      // This guarded check avoids the Chrome console ReferenceError caused by ChemDoodle?.readMOL.
      // eslint-disable-next-line no-undef
      if (!cd && typeof ChemDoodle !== "undefined") cd = ChemDoodle;
    } catch (_error) {
      // ignore
    }

    if (cd && !window.ChemDoodle) {
      try {
        window.ChemDoodle = cd;
      } catch (_error) {
        // ignore
      }
    }

    return cd;
  }

  function scriptDiagnostics() {
    return Array.from(document.scripts || []).map((script) => ({
      id: script.id || "",
      src: script.src || "inline",
      loaded: script.dataset ? script.dataset.loaded || script.dataset.apiBuilderLoaded || "" : "",
      async: Boolean(script.async),
      defer: Boolean(script.defer),
    })).filter((script) => {
      return /ChemDoodle|api-builder|jquery|bootstrap/i.test(script.src) || /api-builder-chemdoodle/i.test(script.id);
    });
  }

  function chemDoodleDiagnostics() {
    const cd = getChemDoodleGlobal();
    return {
      version: API_BUILDER_DEBUG_VERSION,
      time: debugTimestamp(),
      href: window.location.href,
      readyState: document.readyState,
      bodyDatasetPage: document.body ? document.body.dataset.page || "" : "NO_BODY",
      hasWindowChemDoodle: Boolean(window.ChemDoodle),
      hasChemDoodleObject: Boolean(cd),
      hasSketcherCanvas: Boolean(cd && typeof cd.SketcherCanvas === "function"),
      hasReadMOL: Boolean(cd && typeof cd.readMOL === "function"),
      hasWriteMOL: Boolean(cd && typeof cd.writeMOL === "function"),
      warheadNode: Boolean(document.getElementById("warhead-editor")),
      ligaseNode: Boolean(document.getElementById("ligase-editor")),
      hasWarheadSketcher: Boolean(warheadSketcher || window.apiWarheadSketcher),
      hasLigaseSketcher: Boolean(ligaseSketcher || window.apiLigaseSketcher),
      scripts: scriptDiagnostics(),
    };
  }

  function printDiagnostics(label = "manual") {
    const diag = chemDoodleDiagnostics();
    try {
      console.groupCollapsed(`[api-builder ${API_BUILDER_DEBUG_VERSION}] diagnostics: ${label}`);
      console.table({
        readyState: diag.readyState,
        bodyDatasetPage: diag.bodyDatasetPage,
        hasWindowChemDoodle: diag.hasWindowChemDoodle,
        hasChemDoodleObject: diag.hasChemDoodleObject,
        hasSketcherCanvas: diag.hasSketcherCanvas,
        hasReadMOL: diag.hasReadMOL,
        hasWriteMOL: diag.hasWriteMOL,
        warheadNode: diag.warheadNode,
        ligaseNode: diag.ligaseNode,
        hasWarheadSketcher: diag.hasWarheadSketcher,
        hasLigaseSketcher: diag.hasLigaseSketcher,
      });
      console.log("full diagnostics", diag);
      console.groupEnd();
    } catch (_error) {
      console.log(`[api-builder ${API_BUILDER_DEBUG_VERSION}] diagnostics`, diag);
    }
    return diag;
  }

  debugLog("script loaded", {
    version: API_BUILDER_DEBUG_VERSION,
    href: window.location.href,
    readyState: document.readyState,
  });

  function sleep(ms) {
    return new Promise((resolve) => setTimeout(resolve, ms));
  }

  function lockDownChemDoodle() {
    const CD = getChemDoodleGlobal();
    if (!CD) {
      debugWarn("ChemDoodle lockdown skipped; ChemDoodle global is missing.", chemDoodleDiagnostics());
      return;
    }

    try {
      CD.iChemLabsServer = null;
      CD.servicesAllowed = false;
      CD.monitoring = false;
      CD.licenseCheck = false;

      if (!CD.iChemLabs) CD.iChemLabs = {};
      CD.iChemLabs.server = null;
      CD.iChemLabs.useServices = false;

      if (!CD.feature) CD.feature = {};
      if (!CD.feature.uil) CD.feature.uil = {};
      CD.feature.uil.loadRemote = false;

      debugLog("ChemDoodle cloud/services disabled.");
    } catch (error) {
      debugWarn("ChemDoodle lockdown warning", formatError(error));
    }
  }

  function chemDoodleReady() {
    const CD = getChemDoodleGlobal();
    return !!(
      CD &&
      typeof CD.SketcherCanvas === "function" &&
      typeof CD.readMOL === "function" &&
      typeof CD.writeMOL === "function"
    );
  }

  function loadScriptOnce(src, id, options = {}) {
    const force = Boolean(options.force);
    return new Promise((resolve, reject) => {
      const baseSrc = src.split("?")[0];
      const existingById = !force && id ? document.getElementById(id) : null;
      const existingBySrc = !force ? Array.from(document.scripts).find((script) => {
        return script.src && script.src.includes(baseSrc);
      }) : null;

      const existing = existingById || existingBySrc;

      if (existing) {
        debugLog("script already present", {
          id: existing.id || id || "",
          src: existing.src,
          loaded: existing.dataset.loaded || existing.dataset.apiBuilderLoaded || "unknown",
        });

        if (existing.dataset.loaded === "true" || existing.dataset.apiBuilderLoaded === "true") {
          resolve();
          return;
        }

        existing.addEventListener("load", () => {
          existing.dataset.loaded = "true";
          existing.dataset.apiBuilderLoaded = "true";
          debugLog("existing script load event", { id: existing.id || "", src: existing.src });
          resolve();
        }, { once: true });

        existing.addEventListener("error", (event) => {
          debugError("existing script error event", { id: existing.id || "", src: existing.src, event });
          reject(new Error(`Existing script failed: ${existing.src || src}`));
        }, { once: true });

        // If the script loaded before we attached the listener, this prevents a permanent wait.
        setTimeout(resolve, 1200);
        return;
      }

      const script = document.createElement("script");
      script.src = src;
      script.async = false;
      script.defer = false;
      script.dataset.loaded = "false";
      script.dataset.apiBuilderLoaded = "false";
      if (id) script.id = force ? `${id}-retry-${SCRIPT_LOAD_ATTEMPT += 1}` : id;

      debugLog("loading script", { id: script.id || "", src: script.src, force });

      script.onload = () => {
        script.dataset.loaded = "true";
        script.dataset.apiBuilderLoaded = "true";
        debugLog("script loaded", { id: script.id || "", src: script.src });
        resolve();
      };

      script.onerror = () => {
        debugError("script failed to load", { id: script.id || "", src: script.src });
        reject(new Error(`Failed to load script: ${src}`));
      };

      document.head.appendChild(script);
    });
  }

  async function ensureChemDoodleLoaded() {
    if (chemDoodleReady()) {
      lockDownChemDoodle();
      debugLog("ChemDoodle already ready", chemDoodleDiagnostics());
      return true;
    }

    debugWarn("ChemDoodle not ready; attempting dynamic load", chemDoodleDiagnostics());

    for (let attempt = 0; attempt < 3; attempt += 1) {
      try {
        const force = attempt > 0;
        const cacheBust = `v=${Date.now()}-${attempt}`;

        await loadScriptOnce(`/static/js/ChemDoodleWeb.js?${cacheBust}`, "api-builder-chemdoodle-core", { force });
        await loadScriptOnce(`/static/js/ChemDoodleWeb-uis.js?${cacheBust}`, "api-builder-chemdoodle-uis", { force });

        for (let i = 0; i < 30; i += 1) {
          if (chemDoodleReady()) {
            lockDownChemDoodle();
            debugLog("ChemDoodle became ready", { attempt, poll: i, diagnostics: chemDoodleDiagnostics() });
            return true;
          }
          await sleep(100);
        }

        debugWarn("ChemDoodle still not ready after load attempt", { attempt, diagnostics: chemDoodleDiagnostics() });
      } catch (error) {
        debugError("Failed to dynamically load ChemDoodle scripts", {
          attempt,
          error: formatError(error),
          diagnostics: chemDoodleDiagnostics(),
        });
      }
    }

    debugError("ChemDoodle unavailable after all dynamic load attempts", chemDoodleDiagnostics());
    return chemDoodleReady();
  }

  async function initSketchers(tries = 0) {
    const warheadNode = document.getElementById("warhead-editor");
    const ligaseNode = document.getElementById("ligase-editor");

    if (!warheadNode || !ligaseNode) {
      if (tries === 0) debugWarn("ChemDoodle editor containers not found yet", chemDoodleDiagnostics());
      if (tries < 100) {
        await sleep(100);
        return initSketchers(tries + 1);
      }

      debugError("ChemDoodle editor containers not found on API Builder page", chemDoodleDiagnostics());
      return false;
    }

    const ready = await ensureChemDoodleLoaded();

    if (!ready) {
      if (tries < 20) {
        await sleep(250);
        return initSketchers(tries + 1);
      }

      debugError("ChemDoodle unavailable on API Builder page after dynamic load attempt", chemDoodleDiagnostics());
      return false;
    }

    if (warheadSketcher && ligaseSketcher) {
      window.apiWarheadSketcher = warheadSketcher;
      window.apiLigaseSketcher = ligaseSketcher;
      debugLog("API Builder sketchers already initialized", chemDoodleDiagnostics());
      return true;
    }

    lockDownChemDoodle();

    try {
      const CD = getChemDoodleGlobal();
      if (!CD || typeof CD.SketcherCanvas !== "function") {
        throw new Error("ChemDoodle.SketcherCanvas is not available.");
      }

      warheadSketcher = new CD.SketcherCanvas("warhead-editor", 340, 340, {
        useServices: false,
      });

      ligaseSketcher = new CD.SketcherCanvas("ligase-editor", 340, 340, {
        useServices: false,
      });

      window.apiWarheadSketcher = warheadSketcher;
      window.apiLigaseSketcher = ligaseSketcher;
      window.apiBuilderChemDoodleReadyFlag = true;

      debugLog("API Builder ChemDoodle sketchers initialized", chemDoodleDiagnostics());
      return true;
    } catch (error) {
      debugError("Failed to initialize API Builder ChemDoodle sketchers", {
        error: formatError(error),
        diagnostics: chemDoodleDiagnostics(),
      });
      return false;
    }
  }

  async function ensureSketchersReady() {
    if (warheadSketcher && ligaseSketcher && chemDoodleReady()) return true;
    return initSketchers();
  }

  function setStatus(kind, ok, message) {
    const el = document.getElementById(`${kind}-status`);
    if (!el) return;

    el.classList.remove("status-ok", "status-bad");
    el.classList.add(ok ? "status-ok" : "status-bad");
    el.textContent = message;
  }

  function escapeHtml(value) {
    return String(value).replace(/[&<>"']/g, (match) => ({
      "&": "&amp;",
      "<": "&lt;",
      ">": "&gt;",
      '"': "&quot;",
      "'": "&#039;",
    })[match]);
  }

  function showError(error) {
    console.error(error);
    const message = typeof error === "string"
      ? error
      : (error && error.message) || "Unknown error";

    window.alert(message);
  }

  function getMolBlockFromResponse(data) {
    const molBlock = data?.mol_block || data?.molBlock || data?.mol || "";

    if (!String(molBlock).trim()) {
      console.error("No MOL block in backend response:", data);
      throw new Error("Backend response did not include mol_block.");
    }

    return molBlock;
  }

  function loadMolBlockIntoSketcher(kind, data) {
    const molBlock = getMolBlockFromResponse(data);
    const sketcher = kind === "warhead" ? warheadSketcher : ligaseSketcher;

    debugLog("render requested", {
      kind,
      molBlockLength: molBlock.length,
      molBlockPreview: molBlock.slice(0, 240),
      diagnostics: chemDoodleDiagnostics(),
    });

    if (!sketcher) {
      throw new Error(`${kind} sketcher not initialized.`);
    }

    if (!chemDoodleReady()) {
      throw new Error("ChemDoodle is not available.");
    }

    const CD = getChemDoodleGlobal();
    const mol = CD.readMOL(molBlock);

    if (!mol || !Array.isArray(mol.atoms) || mol.atoms.length === 0) {
      debugError("ChemDoodle parsed an empty molecule from MOL block", {
        kind,
        mol,
        molBlockPreview: molBlock.slice(0, 800),
      });
      throw new Error("ChemDoodle parsed an empty molecule from backend MOL.");
    }

    sketcher.clear();
    sketcher.loadMolecule(mol);
    sketcher.repaint();

    requestAnimationFrame(() => {
      if (typeof sketcher.center === "function") sketcher.center();
      sketcher.repaint();
    });

    debugLog("molecule rendered", {
      kind,
      atomCount: mol.atoms.length,
      bondCount: Array.isArray(mol.bonds) ? mol.bonds.length : null,
    });
  }

  async function safeJsonResponse(res, context = {}) {
    const contentType = res.headers.get("content-type") || "";
    const text = await res.text();
    const responseInfo = {
      context,
      status: res.status,
      ok: res.ok,
      statusText: res.statusText,
      redirected: res.redirected,
      url: res.url,
      contentType,
      headers: headersSummary(res.headers),
      textLength: text.length,
      textPreview: shortText(text, 1200),
      looksLikeHtml: looksLikeHtml(text),
    };

    debugLog("HTTP response", responseInfo);

    if (!text) {
      return res.ok
        ? {}
        : {
          success: false,
          error: `Server returned ${res.status} ${res.statusText || ""} with an empty body.`,
          details: "No response body was returned.",
          _debug: responseInfo,
        };
    }

    if (contentType.toLowerCase().includes("json")) {
      try {
        return JSON.parse(text);
      } catch (error) {
        debugError("JSON parse failed even though content-type was JSON", {
          error: formatError(error),
          responseInfo,
        });
        return {
          success: false,
          error: "Server returned invalid JSON.",
          details: shortText(text, 700),
          _debug: responseInfo,
        };
      }
    }

    try {
      // Sometimes Flask/Heroku forgets a JSON content-type. Accept parseable JSON anyway.
      const parsed = JSON.parse(text);
      debugWarn("Response parsed as JSON despite non-JSON content-type", responseInfo);
      return parsed;
    } catch (_error) {
      const message = responseInfo.looksLikeHtml
        ? `Server returned an HTML page instead of JSON for ${context.url || res.url || "this request"}.`
        : `Server returned ${contentType || "a non-JSON response"} instead of JSON.`;

      return {
        success: false,
        error: message,
        details: shortText(text, 900),
        _debug: responseInfo,
      };
    }
  }

  async function apiFetchJson(url, options = {}, label = "request") {
    const requestId = `api-builder-${Date.now()}-${FETCH_COUNTER += 1}`;
    const method = (options.method || "GET").toUpperCase();
    const bodySummary = formDataSummary(options.body);
    const fetchOptions = {
      cache: "no-store",
      credentials: "same-origin",
      ...options,
    };

    debugLog("HTTP request", {
      requestId,
      label,
      method,
      url,
      href: window.location.href,
      bodySummary,
      headers: options.headers || {},
    });

    try {
      const res = await fetch(url, fetchOptions);
      const data = await safeJsonResponse(res, { requestId, label, method, url });
      debugLog("HTTP parsed payload", { requestId, label, data });
      return { res, data, requestId };
    } catch (error) {
      debugError("HTTP fetch threw before response", {
        requestId,
        label,
        method,
        url,
        error: formatError(error),
      });
      throw error;
    }
  }

  async function uploadStructure(kind) {
    debugLog("uploadStructure called", { kind, diagnostics: chemDoodleDiagnostics() });

    const input = document.getElementById(`${kind}-file`);
    const file = input && input.files ? input.files[0] : null;

    if (!file) return window.alert(`Select a ${kind} file first.`);

    setStatus(kind, false, "Converting…");

    const ready = await ensureSketchersReady();
    if (!ready) {
      setStatus(kind, false, "Editor unavailable");
      printDiagnostics(`uploadStructure:${kind}:editor-unavailable`);
      return showError("ChemDoodle editor is unavailable. Please hard-refresh and try again.");
    }

    const fd = new FormData();
    fd.append("structure_file", file);

    const { res, data } = await apiFetchJson("/api/protac/structure/convert", {
      method: "POST",
      body: fd,
    }, `uploadStructure:${kind}`);

    if (!res.ok) {
      setStatus(kind, false, "Failed");
      return showError(data && data.error ? `${data.error}\n\n${data.details || ""}`.trim() : "Structure conversion failed.");
    }

    try {
      loadMolBlockIntoSketcher(kind, data);
      setStatus(kind, true, "Loaded");
      debugLog("structure upload loaded successfully", { kind });
      return true;
    } catch (error) {
      debugError("Structure render error", { kind, error: formatError(error), data, diagnostics: chemDoodleDiagnostics() });
      setStatus(kind, false, "Load error");
      return showError(error.message || "Backend returned MOL, but ChemDoodle could not render it.");
    }
  }

  async function pasteSmiles(kind) {
    const textarea = document.getElementById(`${kind}-smiles-paste`);
    const smiles = (textarea && textarea.value ? textarea.value : "").trim();

    debugLog("pasteSmiles called", {
      kind,
      smilesLength: smiles.length,
      smilesPreview: shortText(smiles, 240),
      diagnostics: chemDoodleDiagnostics(),
    });

    if (!smiles) return window.alert("Paste a SMILES first.");

    setStatus(kind, false, "Converting…");

    const ready = await ensureSketchersReady();
    if (!ready) {
      setStatus(kind, false, "Editor unavailable");
      printDiagnostics(`pasteSmiles:${kind}:editor-unavailable`);
      return showError("ChemDoodle editor is unavailable. Please hard-refresh and try again.");
    }

    const fd = new FormData();
    fd.append("smiles", smiles);

    const { res, data } = await apiFetchJson("/api/protac/structure/convert", {
      method: "POST",
      body: fd,
    }, `pasteSmiles:${kind}`);

    if (!res.ok) {
      setStatus(kind, false, "Failed");
      return showError(data && data.error ? `${data.error}\n\n${data.details || ""}`.trim() : "SMILES conversion failed.");
    }

    try {
      loadMolBlockIntoSketcher(kind, data);
      setStatus(kind, true, "Loaded");
      debugLog("SMILES loaded successfully", { kind });
      return true;
    } catch (error) {
      debugError("SMILES render error", { kind, error: formatError(error), data, diagnostics: chemDoodleDiagnostics() });
      setStatus(kind, false, "Load error");
      return showError(error.message || "Backend returned MOL, but ChemDoodle could not render it.");
    }
  }

  async function saveMappedSmiles(kind) {
    const ready = await ensureSketchersReady();
    if (!ready) return window.alert("Molecule editor is not ready.");

    const sketcher = kind === "warhead" ? warheadSketcher : ligaseSketcher;

    if (!sketcher) return window.alert("Molecule editor is not ready.");

    const mol = sketcher.getMolecule();
    if (!mol) return window.alert(`No ${kind} molecule loaded.`);

    const CD = getChemDoodleGlobal();
    if (!CD || typeof CD.writeMOL !== "function") return window.alert("ChemDoodle is not ready.");

    const molBlock = CD.writeMOL(mol);

    debugLog("saveMappedSmiles posting", {
      kind,
      molBlockLength: molBlock.length,
      molBlockPreview: molBlock.slice(0, 240),
    });

    const { res, data } = await apiFetchJson("/api/protac/structure/mapped-smiles", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ molBlock }),
    }, `saveMappedSmiles:${kind}`);

    if (!res.ok) {
      return showError(data && data.error ? data.error : "Failed to generate mapped SMILES.");
    }

    const smiles = (data.smiles || "").trim();
    if (!smiles) return showError("Mapped SMILES came back empty.");

    if (kind === "warhead") {
      WARHEAD_MAPPED_SMILES = smiles;

      const el = document.getElementById("warhead-smiles");
      if (el) el.textContent = smiles;

      setStatus("warhead", true, "Saved");
    } else {
      LIGASE_MAPPED_SMILES = smiles;

      const el = document.getElementById("ligase-smiles");
      if (el) el.textContent = smiles;

      setStatus("ligase", true, "Saved");
    }

    if (Array.isArray(data.warnings) && data.warnings.length) {
      console.warn("Mapping warnings:", data.warnings);
    }

    return true;
  }

  async function inspectLinkerCSV(file) {
    const fd = new FormData();
    fd.append("linker_csv", file);

    const { res, data } = await apiFetchJson("/api/protac/linkers/inspect", {
      method: "POST",
      body: fd,
    }, "inspectLinkerCSV");
    const errBox = document.getElementById("inspect-error");

    if (errBox) {
      errBox.style.display = "none";
      errBox.textContent = "";
    }

    if (!res.ok) {
      if (errBox) {
        errBox.style.display = "block";
        errBox.textContent = data && data.error ? data.error : "Inspect failed.";
      }

      LINKER_COLUMNS = [];
      CSV_PREVIEW_ROWS = [];

      throw new Error((data && data.error) || "Inspect failed");
    }

    LINKER_COLUMNS = data.columns || [];
    CSV_PREVIEW_ROWS = data.preview_rows || [];

    buildColumnModalUI(
      LINKER_COLUMNS,
      CSV_PREVIEW_ROWS,
      data.suggested_name_col || "",
      data.suggested_smiles_col || "",
    );
  }

  function buildColumnModalUI(columns, rows, suggestedName, suggestedSmiles) {
    const nameSel = document.getElementById("name-col-select");
    const smilesSel = document.getElementById("smiles-col-select");
    const nameSug = document.getElementById("name-col-suggest");
    const smilesSug = document.getElementById("smiles-col-suggest");

    if (!nameSel || !smilesSel) return;

    nameSel.innerHTML = "";
    smilesSel.innerHTML = "";

    columns.forEach((col) => {
      const opt1 = document.createElement("option");
      opt1.value = col;
      opt1.textContent = col;
      nameSel.appendChild(opt1);

      const opt2 = document.createElement("option");
      opt2.value = col;
      opt2.textContent = col;
      smilesSel.appendChild(opt2);
    });

    if (suggestedName && columns.includes(suggestedName)) nameSel.value = suggestedName;
    if (suggestedSmiles && columns.includes(suggestedSmiles)) smilesSel.value = suggestedSmiles;

    if (nameSug) {
      nameSug.innerHTML = suggestedName
        ? `<span class="badge-suggest">Suggested</span> ${escapeHtml(suggestedName)}`
        : "";
    }

    if (smilesSug) {
      smilesSug.innerHTML = suggestedSmiles
        ? `<span class="badge-suggest">Suggested</span> ${escapeHtml(suggestedSmiles)}`
        : "";
    }

    const previewCols = columns.slice(0, Math.min(columns.length, 6));
    const thead = document.getElementById("preview-head");
    const tbody = document.getElementById("preview-body");

    if (thead) thead.innerHTML = "";
    if (tbody) tbody.innerHTML = "";

    if (thead) {
      const trh = document.createElement("tr");

      previewCols.forEach((col) => {
        const th = document.createElement("th");
        th.textContent = col;
        trh.appendChild(th);
      });

      thead.appendChild(trh);
    }

    if (tbody) {
      rows.slice(0, 10).forEach((row) => {
        const tr = document.createElement("tr");

        previewCols.forEach((col) => {
          const td = document.createElement("td");
          td.textContent = row[col] ?? "";
          tr.appendChild(td);
        });

        tbody.appendChild(tr);
      });
    }
  }

  async function onLinkerSelected(input) {
    const file = input && input.files ? input.files[0] : null;
    const pill = document.getElementById("linker-status");
    const label = document.getElementById("linker-filename");
    const picked = document.getElementById("linker-picked");

    SELECTED_NAME_COL = "";
    SELECTED_SMILES_COL = "";

    if (picked) picked.textContent = "";

    if (!file) {
      if (pill) {
        pill.className = "status-pill status-bad";
        pill.textContent = "No file";
      }

      if (label) label.textContent = "";
      return;
    }

    LINKER_FILE = file;

    if (pill) {
      pill.className = "status-pill status-ok";
      pill.textContent = "Selected";
    }

    if (label) label.textContent = `📄 ${file.name}`;

    try {
      await inspectLinkerCSV(file);
      window.jQuery("#csvColumnModal").modal("show");
    } catch (error) {
      console.error("CSV inspect error:", error);

      if (pill) {
        pill.className = "status-pill status-bad";
        pill.textContent = "Inspect failed";
      }

      window.alert("Could not inspect this CSV. Check delimiter/format and try again.");
    }
  }

  function confirmCsvColumns() {
    const nameSel = document.getElementById("name-col-select");
    const smilesSel = document.getElementById("smiles-col-select");

    SELECTED_NAME_COL = nameSel ? nameSel.value || "" : "";
    SELECTED_SMILES_COL = smilesSel ? smilesSel.value || "" : "";

    if (!SELECTED_SMILES_COL) return window.alert("Select the linker SMILES column.");

    const picked = document.getElementById("linker-picked");

    if (picked) {
      picked.innerHTML = `
        <span class="badge-suggest">Ready</span>
        Name: <span class="mono">${escapeHtml(SELECTED_NAME_COL || "(auto)")}</span>
        | SMILES: <span class="mono">${escapeHtml(SELECTED_SMILES_COL)}</span>
      `;
    }

    setStatus("linker", true, "Configured");
    window.jQuery("#csvColumnModal").modal("hide");
  }

  function resetResultsUI() {
    const tbody = document.querySelector("#results-table tbody");
    if (tbody) tbody.innerHTML = "";

    const fbody = document.getElementById("failures-body");
    if (fbody) fbody.innerHTML = "";

    const fwrap = document.getElementById("failures-wrap");
    if (fwrap) fwrap.style.display = "none";

    const dfail = document.getElementById("download-fail-btn");
    if (dfail) dfail.style.display = "none";

    const dres = document.getElementById("download-btn");
    if (dres) dres.style.display = "none";

    const meta = document.getElementById("result-meta");
    if (meta) meta.textContent = "";

    const warn = document.getElementById("batch-warnings");
    if (warn) {
      warn.style.display = "none";
      warn.innerHTML = "";
    }

    LAST_RESULTS = [];
    LAST_FAILURES = [];
  }

  function renderWarnings(data) {
    const box = document.getElementById("batch-warnings");
    if (!box) return;

    box.style.display = "none";
    box.innerHTML = "";

    const warnings = Array.isArray(data.warnings) ? data.warnings : [];
    const message = data.message || "";

    if (!warnings.length && !message) return;

    let html = '<div class="ok-box">';

    if (message) html += `<div class="font-weight-bold mb-1">${escapeHtml(message)}</div>`;

    if (warnings.length) {
      html += '<div class="tiny">Warnings:</div><ul class="mb-0 tiny">';
      warnings.forEach((warning) => {
        html += `<li>${escapeHtml(warning)}</li>`;
      });
      html += "</ul>";
    }

    html += "</div>";

    box.innerHTML = html;
    box.style.display = "block";
  }

  function renderResults(rows, count, failed) {
    const tbody = document.querySelector("#results-table tbody");
    if (tbody) tbody.innerHTML = "";

    rows.forEach((row) => {
      const tr = document.createElement("tr");
      tr.innerHTML = `<td>${escapeHtml(row.name || "")}</td><td class="mono">${escapeHtml(row.smiles || "")}</td>`;

      if (tbody) tbody.appendChild(tr);
    });

    const meta = document.getElementById("result-meta");
    if (meta) meta.textContent = `Built: ${count} | Failed: ${failed} | Rendered: ${rows.length}`;

    const downloadBtn = document.getElementById("download-btn");
    if (downloadBtn) downloadBtn.style.display = rows.length ? "inline-block" : "none";
  }

  function renderFailures(failures) {
    const wrap = document.getElementById("failures-wrap");
    const btn = document.getElementById("download-fail-btn");
    const body = document.getElementById("failures-body");

    if (body) body.innerHTML = "";

    if (!failures || !failures.length) {
      if (wrap) wrap.style.display = "none";
      if (btn) btn.style.display = "none";
      return;
    }

    if (wrap) wrap.style.display = "block";
    if (btn) btn.style.display = "inline-block";

    failures.slice(0, 250).forEach((failure) => {
      const tr = document.createElement("tr");

      tr.innerHTML = `
        <td>${escapeHtml(failure.row)}</td>
        <td>${escapeHtml(failure.name || "")}</td>
        <td>${escapeHtml(failure.reason || "")}</td>
        <td class="mono">${escapeHtml(failure.linker_smiles || "")}</td>
      `;

      if (body) body.appendChild(tr);
    });
  }

  function setLoading(isLoading, message) {
    const overlay = document.getElementById("loadingOverlay");
    const btn = document.querySelector('button[onclick="runBatchProtac()"]');

    if (message && overlay) {
      const title = overlay.querySelector(".loading-title");
      if (title) title.textContent = message;
    }

    if (overlay) overlay.style.display = isLoading ? "flex" : "none";

    if (!btn) return;

    if (isLoading) {
      btn.classList.add("btn-loading");
      btn.disabled = true;
      btn.dataset.origText = btn.dataset.origText || btn.innerHTML;
      btn.innerHTML = "⏳ Building…";
    } else {
      btn.classList.remove("btn-loading");
      btn.disabled = false;

      if (btn.dataset.origText) btn.innerHTML = btn.dataset.origText;
    }
  }

  async function runBatchProtac() {
    if (window.__BATCH_RUNNING__) return;

    window.__BATCH_RUNNING__ = true;
    setLoading(true, "Building PROTAC library…");

    try {
      resetResultsUI();

      if (!WARHEAD_MAPPED_SMILES || !LIGASE_MAPPED_SMILES) {
        window.alert("Save both Warhead and Ligase first.");
        return;
      }

      if (!LINKER_FILE) {
        window.alert("Upload a linker CSV first.");
        return;
      }

      if (!SELECTED_SMILES_COL) {
        try {
          await inspectLinkerCSV(LINKER_FILE);
          window.jQuery("#csvColumnModal").modal("show");
        } catch (error) {
          console.error("CSV re-inspect failed:", error);
        }

        return;
      }

      setLoading(true, "Building PROTACs (running RDKit)…");

      const fd = new FormData();
      fd.append("warhead_smiles", WARHEAD_MAPPED_SMILES);
      fd.append("ligase_smiles", LIGASE_MAPPED_SMILES);
      fd.append("linker_csv", LINKER_FILE);
      fd.append("name_col", SELECTED_NAME_COL);
      fd.append("smiles_col", SELECTED_SMILES_COL);
      fd.append("source", "web-ui");

      const { res, data } = await apiFetchJson("/api/protac/builder/batch", {
        method: "POST",
        body: fd,
      }, "runBatchProtac");

      if (!res.ok) {
        showError(data && data.error ? data.error : "Batch build failed.");
        return;
      }

      LAST_RESULTS = Array.isArray(data.results) ? data.results : [];
      LAST_FAILURES = Array.isArray(data.failures) ? data.failures : [];

      renderResults(LAST_RESULTS, data.count || LAST_RESULTS.length, data.failed || LAST_FAILURES.length);
      renderWarnings(data);
      renderFailures(LAST_FAILURES);
    } catch (error) {
      showError(error);
    } finally {
      setLoading(false);
      window.__BATCH_RUNNING__ = false;
    }
  }

  function downloadResultsCSV() {
    if (!LAST_RESULTS.length) return;

    let csv = "PROTAC_Name,PROTAC_SMILES,WARHEAD_SMILES,LINKER_SMILES,LIGASE_SMILES\n";

    LAST_RESULTS.forEach((row) => {
      const name = String(row.name || "").replace(/"/g, '""');
      const smiles = String(row.smiles || "").replace(/"/g, '""');
      const warhead = String(row.warhead_smiles || "").replace(/"/g, '""');
      const linker = String(row.linker_smiles || "").replace(/"/g, '""');
      const ligase = String(row.ligase_smiles || "").replace(/"/g, '""');

      csv += `"${name}","${smiles}","${warhead}","${linker}","${ligase}"\n`;
    });

    const blob = new Blob([csv], { type: "text/csv" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");

    a.href = url;
    a.download = "PBuilder-Smiles.csv";

    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  }

  function downloadFailuresCSV() {
    if (!LAST_FAILURES.length) return;

    let csv = "row,name,reason,linker_smiles\n";

    LAST_FAILURES.forEach((failure) => {
      const row = String(failure.row ?? "").replace(/"/g, '""');
      const name = String(failure.name || "").replace(/"/g, '""');
      const reason = String(failure.reason || "").replace(/"/g, '""');
      const smiles = String(failure.linker_smiles || "").replace(/"/g, '""');

      csv += `"${row}","${name}","${reason}","${smiles}"\n`;
    });

    const blob = new Blob([csv], { type: "text/csv" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");

    a.href = url;
    a.download = "PBuilder-Failed-Linkers.csv";

    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  }

  function animateCountUpPretty(el, target, ms) {
    const startTime = performance.now();
    const safeTarget = Math.max(0, Number(target || 0));

    function easeOutCubic(t) {
      return 1 - Math.pow(1 - t, 3);
    }

    function tick(now) {
      const t = Math.min((now - startTime) / ms, 1);
      const eased = easeOutCubic(t);
      const value = Math.round(safeTarget * eased);

      el.textContent = value.toLocaleString();

      if (t < 1) {
        requestAnimationFrame(tick);
      } else {
        el.textContent = safeTarget.toLocaleString();
        el.classList.remove("pulse");
        void el.offsetWidth;
        el.classList.add("pulse");

        setTimeout(() => el.classList.add("usage-glow-cycle"), 350);
      }
    }

    requestAnimationFrame(tick);
  }

  async function updateApiUsageCounter() {
    try {
      const { res, data } = await apiFetchJson("/api/protac/builder/usage", {
        method: "GET",
        cache: "no-store",
      }, "updateApiUsageCounter");

      if (!res.ok) throw new Error("usage fetch failed");
      const counterEl = document.getElementById("api-counter");

      if (counterEl) animateCountUpPretty(counterEl, Number(data.total || 0), 1200);
    } catch (error) {
      console.warn("API usage counter error:", error);
    }
  }

  async function updateTemplateDownloadCount() {
    try {
      const { res, data } = await apiFetchJson("/api/protac/builder/template/download-count", {
        method: "GET",
        cache: "no-store",
      }, "updateTemplateDownloadCount");

      if (!res.ok) throw new Error("download count failed");
      const el = document.getElementById("api-linker-download-count");

      if (el && typeof data.downloads === "number") {
        el.textContent = data.downloads.toLocaleString();
      }
    } catch (error) {
      console.warn("Download count unavailable", error);
    }
  }

  function copyCodeBlock(blockId, btn) {
    try {
      const el = document.getElementById(blockId);
      if (!el) throw new Error("Code block not found");

      navigator.clipboard.writeText(el.innerText).then(() => {
        if (!btn) return;

        const original = btn.innerHTML;

        btn.innerHTML = "✅ Copied";
        btn.classList.add("btn-success");
        btn.classList.remove("btn-outline-info");

        setTimeout(() => {
          btn.innerHTML = original;
          btn.classList.remove("btn-success");
          btn.classList.add("btn-outline-info");
        }, 1200);
      }).catch((error) => {
        console.error("Clipboard error:", error);
        window.alert("Clipboard access failed. Try HTTPS or manual copy.");
      });
    } catch (error) {
      console.error("Copy failed:", error);
    }
  }

  function showApiWelcomeModal(tries = 0) {
    const modalEl = document.getElementById("apiWelcomeModal");

    if (!modalEl) {
      console.warn("API welcome modal element not found.");
      return;
    }

    if (
      window.jQuery &&
      window.jQuery.fn &&
      typeof window.jQuery.fn.modal === "function"
    ) {
      window.jQuery("#apiWelcomeModal").modal("show");
      return;
    }

    if (tries < 50) {
      return setTimeout(() => showApiWelcomeModal(tries + 1), 100);
    }

    console.warn("Bootstrap modal unavailable; API welcome popup not shown.");
  }

  function initModalAndVisibility() {
    showApiWelcomeModal();

    if (!VISIBILITY_LISTENER_REGISTERED) {
      VISIBILITY_LISTENER_REGISTERED = true;

      document.addEventListener("visibilitychange", () => {
        const el = document.getElementById("api-counter");
        if (!el) return;

        el.style.animationPlayState = document.hidden ? "paused" : "running";
      });
    }
  }

  

  async function apiBuilderTestConvert(smiles = "CCO", kind = "warhead") {
    const cleanKind = kind === "ligase" ? "ligase" : "warhead";
    const cleanSmiles = String(smiles || "").trim() || "CCO";

    printDiagnostics(`testConvert:${cleanKind}:before`);

    const ready = await ensureSketchersReady();
    if (!ready) {
      const diag = printDiagnostics(`testConvert:${cleanKind}:editor-unavailable`);
      throw new Error(`ChemDoodle editor is unavailable. Diagnostics: ${JSON.stringify(diag)}`);
    }

    const fd = new FormData();
    fd.append("smiles", cleanSmiles);

    const { res, data, requestId } = await apiFetchJson("/api/protac/structure/convert", {
      method: "POST",
      body: fd,
    }, `manualTestConvert:${cleanKind}`);

    if (!res.ok) {
      const message = data && data.error ? `${data.error}\n\n${data.details || ""}`.trim() : `Request failed with status ${res.status}`;
      debugError("manual test convert failed", { requestId, status: res.status, data });
      throw new Error(message);
    }

    loadMolBlockIntoSketcher(cleanKind, data);
    setStatus(cleanKind, true, "Loaded by test");
    printDiagnostics(`testConvert:${cleanKind}:after`);
    return { ok: true, requestId, status: res.status, data };
  }

  async function startApiBuilder() {
    if (API_BUILDER_STARTED) return;
    API_BUILDER_STARTED = true;

    debugLog("startApiBuilder", chemDoodleDiagnostics());

    // Show popup immediately. Do not wait for ChemDoodle.
    initModalAndVisibility();
    updateApiUsageCounter();
    updateTemplateDownloadCount();

    // Initialize editors separately so ChemDoodle cannot block the popup.
    initSketchers()
      .then((ready) => {
        debugLog("initSketchers completed", { ready, diagnostics: chemDoodleDiagnostics() });
      })
      .catch((error) => {
        debugError("API Builder sketcher initialization failed", formatError(error));
      });
  }

  window.apiBuilderDiagnostics = printDiagnostics;
  window.apiBuilderTestConvert = apiBuilderTestConvert;
  window.apiBuilderEnsureChemDoodle = ensureChemDoodleLoaded;
  window.apiBuilderEnsureSketchers = ensureSketchersReady;
  window.apiBuilderChemDoodleReady = chemDoodleReady;
  window.apiBuilderDebugVersion = API_BUILDER_DEBUG_VERSION;

  window.uploadStructure = uploadStructure;
  window.pasteSmiles = pasteSmiles;
  window.saveMappedSmiles = saveMappedSmiles;
  window.onLinkerSelected = onLinkerSelected;
  window.confirmCsvColumns = confirmCsvColumns;
  window.runBatchProtac = runBatchProtac;
  window.downloadResultsCSV = downloadResultsCSV;
  window.downloadFailuresCSV = downloadFailuresCSV;
  window.copyCodeBlock = copyCodeBlock;

  if (document.readyState === "complete") {
    startApiBuilder();
  } else {
    window.addEventListener("load", startApiBuilder, { once: true });
  }
})();