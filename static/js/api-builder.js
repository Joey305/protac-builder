(function () {
  if (document.body.dataset.page !== "api-builder") return;

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

  function lockDownChemDoodle() {
    if (!window.ChemDoodle) return;
    try {
      ChemDoodle.iChemLabsServer = null;
      ChemDoodle.servicesAllowed = false;
      ChemDoodle.monitoring = false;
      ChemDoodle.licenseCheck = false;
      if (!ChemDoodle.iChemLabs) ChemDoodle.iChemLabs = {};
      ChemDoodle.iChemLabs.server = null;
      ChemDoodle.iChemLabs.useServices = false;
      if (!ChemDoodle.feature) ChemDoodle.feature = {};
      if (!ChemDoodle.feature.uil) ChemDoodle.feature.uil = {};
      ChemDoodle.feature.uil.loadRemote = false;
    } catch (error) {
      console.warn("ChemDoodle lockdown warning:", error);
    }
  }

  function initSketchers() {
    if (!window.ChemDoodle) {
      console.warn("ChemDoodle unavailable on API Builder page.");
      return;
    }
    const warheadNode = document.getElementById("warhead-editor");
    const ligaseNode = document.getElementById("ligase-editor");
    if (!warheadNode || !ligaseNode) return;
    warheadSketcher = new ChemDoodle.SketcherCanvas("warhead-editor", 340, 340, { useServices: false });
    ligaseSketcher = new ChemDoodle.SketcherCanvas("ligase-editor", 340, 340, { useServices: false });
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
    const message = typeof error === "string" ? error : (error && error.message) || "Unknown error";
    window.alert(message);
  }

  async function uploadStructure(kind) {
    const input = document.getElementById(`${kind}-file`);
    const file = input && input.files ? input.files[0] : null;
    if (!file) return window.alert(`Select a ${kind} file first.`);
    setStatus(kind, false, "Converting…");
    const fd = new FormData();
    fd.append("structure_file", file);
    const res = await fetch("/api/protac/structure/convert", { method: "POST", body: fd });
    const data = await res.json();
    if (!res.ok) {
      setStatus(kind, false, "Failed");
      return showError(data && data.error ? data.error : "Structure conversion failed.");
    }
    try {
      const mol = ChemDoodle.readMOL(data.mol_block);
      const sketcher = kind === "warhead" ? warheadSketcher : ligaseSketcher;
      if (!sketcher) throw new Error("ChemDoodle sketcher not initialized.");
      sketcher.clear();
      sketcher.loadMolecule(mol);
      sketcher.repaint();
      setStatus(kind, true, "Loaded");
    } catch (_error) {
      setStatus(kind, false, "Load error");
      showError("Backend returned MOL, but ChemDoodle could not render it.");
    }
  }

  async function pasteSmiles(kind) {
    const textarea = document.getElementById(`${kind}-smiles-paste`);
    const smiles = (textarea && textarea.value ? textarea.value : "").trim();
    if (!smiles) return window.alert("Paste a SMILES first.");
    setStatus(kind, false, "Converting…");
    const fd = new FormData();
    fd.append("smiles", smiles);
    const res = await fetch("/api/protac/structure/convert", { method: "POST", body: fd });
    const data = await res.json();
    if (!res.ok) {
      setStatus(kind, false, "Failed");
      return showError(data && data.error ? data.error : "SMILES conversion failed.");
    }
    try {
      const mol = ChemDoodle.readMOL(data.mol_block);
      const sketcher = kind === "warhead" ? warheadSketcher : ligaseSketcher;
      if (!sketcher) throw new Error("ChemDoodle sketcher not initialized.");
      sketcher.clear();
      sketcher.loadMolecule(mol);
      sketcher.repaint();
      setStatus(kind, true, "Loaded");
    } catch (_error) {
      setStatus(kind, false, "Load error");
      showError("Backend returned MOL, but ChemDoodle could not render it.");
    }
  }

  async function saveMappedSmiles(kind) {
    const sketcher = kind === "warhead" ? warheadSketcher : ligaseSketcher;
    if (!sketcher) return window.alert("Molecule editor is not ready.");
    const mol = sketcher.getMolecule();
    if (!mol) return window.alert(`No ${kind} molecule loaded.`);
    const molBlock = ChemDoodle.writeMOL(mol);
    const res = await fetch("/api/protac/structure/mapped-smiles", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ molBlock }),
    });
    const data = await res.json();
    if (!res.ok) return showError(data && data.error ? data.error : "Failed to generate mapped SMILES.");
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
  }

  async function inspectLinkerCSV(file) {
    const fd = new FormData();
    fd.append("linker_csv", file);
    const res = await fetch("/api/protac/linkers/inspect", { method: "POST", body: fd });
    const data = await res.json();
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
      nameSug.innerHTML = suggestedName ? `<span class="badge-suggest">Suggested</span> ${escapeHtml(suggestedName)}` : "";
    }
    if (smilesSug) {
      smilesSug.innerHTML = suggestedSmiles ? `<span class="badge-suggest">Suggested</span> ${escapeHtml(suggestedSmiles)}` : "";
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
    } catch (_error) {
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
        } catch (_error) {
          // inspectLinkerCSV already surfaced the issue.
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
      const res = await fetch("/api/protac/builder/batch", { method: "POST", body: fd });
      const data = await res.json();
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
    const overshoot = Math.max(0, Math.round(target * 0.04));
    const peak = target + (target > 20 ? overshoot : 0);
    function easeOutBack(t) {
      const c1 = 1.70158;
      const c3 = c1 + 1;
      return 1 + c3 * Math.pow(t - 1, 3) + c1 * Math.pow(t - 1, 2);
    }
    function tick(now) {
      const t = Math.min((now - startTime) / ms, 1);
      const eased = easeOutBack(t);
      const value = Math.round((peak) * eased);
      el.textContent = Math.max(0, Math.min(value, peak)).toLocaleString();
      if (t < 1) {
        requestAnimationFrame(tick);
      } else {
        el.textContent = target.toLocaleString();
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
      const res = await fetch("/api/protac/builder/usage", { cache: "no-store" });
      if (!res.ok) throw new Error("usage fetch failed");
      const data = await res.json();
      const counterEl = document.getElementById("api-counter");
      if (counterEl) animateCountUpPretty(counterEl, Number(data.total || 0), 1200);
    } catch (error) {
      console.warn("API usage counter error:", error);
    }
  }

  async function updateTemplateDownloadCount() {
    try {
      const res = await fetch("/api/protac/builder/template/download-count");
      if (!res.ok) throw new Error("download count failed");
      const data = await res.json();
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

  function initModalAndVisibility() {
    window.jQuery(window).on("load", function () {
      window.jQuery("#apiWelcomeModal").modal("show");
    });
    document.addEventListener("visibilitychange", () => {
      const el = document.getElementById("api-counter");
      if (!el) return;
      el.style.animationPlayState = document.hidden ? "paused" : "running";
    });
  }

  window.uploadStructure = uploadStructure;
  window.pasteSmiles = pasteSmiles;
  window.saveMappedSmiles = saveMappedSmiles;
  window.onLinkerSelected = onLinkerSelected;
  window.confirmCsvColumns = confirmCsvColumns;
  window.runBatchProtac = runBatchProtac;
  window.downloadResultsCSV = downloadResultsCSV;
  window.downloadFailuresCSV = downloadFailuresCSV;
  window.copyCodeBlock = copyCodeBlock;

  document.addEventListener("DOMContentLoaded", () => {
    lockDownChemDoodle();
    initSketchers();
    initModalAndVisibility();
    updateApiUsageCounter();
    updateTemplateDownloadCount();
  });
})();
