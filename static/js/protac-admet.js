const RDKIT_DESCRIPTOR_ORDER = [
  ["exact_molecular_weight", "Exact Molecular Weight"],
  ["molecular_weight", "Molecular Weight"],
  ["formal_charge", "Formal Charge"],
  ["hba", "HBA"],
  ["hbd", "HBD"],
  ["heavy_atom_count", "Heavy Atom Count"],
  ["lipinski_violations", "Lipinski Violations"],
  ["logp", "logP"],
  ["qed", "QED"],
  ["ring_count", "Ring Count"],
  ["rotatable_bonds", "Rotatable Bonds"],
  ["smiles", "SMILES"],
  ["tpsa", "TPSA"],
];

const DEEPPK_LOADING_MESSAGES = [
  {
    html: "Submitting your generated PROTAC SMILES to the DeepPK prediction workflow…",
  },
  {
    html: 'While DeepPK runs, you can explore viral ligand interactions at <a href="https://vlisemod.com" target="_blank" rel="noopener noreferrer">V-LiSEMOD</a>.',
  },
  {
    html: 'Looking for exposed warhead attachment points? Try <a href="https://warheadhunter.com" target="_blank" rel="noopener noreferrer">Warhead Hunter</a>.',
  },
  {
    html: 'Choosing an E3 recruiter? Compare recruiter ligands with <a href="https://e3ligandalyzer.com" target="_blank" rel="noopener noreferrer">E3 Ligandalyzer</a>.',
  },
  {
    html: 'For structural degrader design, read our <a href="https://www.nature.com/articles/s41598-025-21502-8" target="_blank" rel="noopener noreferrer">PRosettaC benchmarking work</a>.',
  },
  {
    html: "Parsing ADMET-style DeepPK predictions and preparing report files…",
  },
  {
    html: "Generating the downloadable PDF report…",
  },
  {
    html: "Almost there — large PROTAC-like molecules can take longer than small molecules.",
  },
];

function escapeHtml(value) {
  return String(value ?? "")
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/\"/g, "&quot;")
    .replace(/'/g, "&#39;");
}

function setParameterButton(button, text, disabled) {
  if (!button) return;
  button.textContent = text;
  button.disabled = Boolean(disabled);
}

async function readJsonResponse(response) {
  const text = await response.text();
  try {
    return text ? JSON.parse(text) : {};
  } catch (_error) {
    return {
      success: false,
      error: "Unexpected response from the DeepPK service.",
      details: text ? text.slice(0, 280) : "No response body was returned.",
    };
  }
}

function buildWarningList(warnings = []) {
  if (!warnings.length) return "";
  return `
    <div class="admet-warning-box">
      <div class="admet-warning-title">Property notes</div>
      <ul class="admet-warning-list">
        ${warnings.map((item) => `<li>${escapeHtml(item)}</li>`).join("")}
      </ul>
    </div>
  `;
}

function renderRdkitPanel(target, payload, title) {
  if (!target) return;
  const properties = payload.properties || payload.rdkit_descriptors || {};
  const warnings = payload.warnings || [];
  const rows = RDKIT_DESCRIPTOR_ORDER
    .filter(([key]) => Object.prototype.hasOwnProperty.call(properties, key))
    .map(
      ([key, label]) => `
        <tr>
          <th scope="row">${label}</th>
          <td>${escapeHtml(properties[key])}</td>
        </tr>
      `,
    )
    .join("");

  target.innerHTML = `
    <section class="admet-results-panel">
      <div class="admet-panel-header">
        <h4>${escapeHtml(title)}</h4>
        <p class="admet-panel-subtitle">Local RDKit descriptors are available immediately while the DeepPK workflow continues.</p>
      </div>
      <div class="admet-table-wrap">
        <table class="admet-parameter-table">
          <tbody>${rows}</tbody>
        </table>
      </div>
      ${buildWarningList(warnings)}
    </section>
  `;
}

function renderDeepPkReady(target, data) {
  if (!target) return;
  const deeppk = data.deeppk || {};
  const buttons = [
    deeppk.pdf_url ? `<a class="btn btn-success mr-2 mb-2" href="${deeppk.pdf_url}" target="_blank" rel="noopener noreferrer">Download PDF Report</a>` : "",
    deeppk.csv_url ? `<a class="btn btn-outline-info mr-2 mb-2" href="${deeppk.csv_url}" target="_blank" rel="noopener noreferrer">Download CSV</a>` : "",
    deeppk.clean_csv_url ? `<a class="btn btn-outline-info mr-2 mb-2" href="${deeppk.clean_csv_url}" target="_blank" rel="noopener noreferrer">Download Cleaned CSV</a>` : "",
    deeppk.json_url ? `<a class="btn btn-outline-info mr-2 mb-2" href="${deeppk.json_url}" target="_blank" rel="noopener noreferrer">Download JSON</a>` : "",
    deeppk.svg_url ? `<a class="btn btn-outline-info mr-2 mb-2" href="${deeppk.svg_url}" target="_blank" rel="noopener noreferrer">Download SVG</a>` : "",
  ]
    .filter(Boolean)
    .join("");

  target.innerHTML = `
    <section class="admet-results-panel admet-success-panel">
      <div class="admet-panel-header">
        <h4>DeepPK Report Ready</h4>
        <p class="admet-panel-subtitle">${escapeHtml(data.message || "DeepPK report files are ready to download.")}</p>
      </div>
      <div class="admet-download-row">${buttons}</div>
      ${buildWarningList(data.warnings || [])}
    </section>
  `;
}

function renderInlineError(target, title, lines) {
  if (!target) return;
  target.innerHTML = `
    <section class="inline-error-panel">
      <h4>${escapeHtml(title)}</h4>
      ${lines.map((line) => `<p>${line}</p>`).join("")}
    </section>
  `;
}

function renderDeepPkFailure(target, data) {
  const lines = [
    "The RDKit descriptor table was generated successfully and remains available below.",
    "DeepPK may be temporarily unavailable or the request may have exceeded the timeout.",
    "You can retry by clicking the button again.",
  ];

  if (data.details) {
    lines.push(`Backend message: ${escapeHtml(data.details)}`);
  }
  if (data.stage) {
    lines.push(`Stage: ${escapeHtml(data.stage)}`);
  }
  if (data.job_id) {
    lines.push(`Job ID: ${escapeHtml(data.job_id)}`);
  }

  renderInlineError(target, "DeepPK report generation failed", lines);
}

async function extractProtacSmiles() {
  if (typeof getSmilesFromSketcher !== "function") {
    throw new Error("The PROTAC sketcher is not ready yet.");
  }
  const smiles = await getSmilesFromSketcher();
  if (!smiles) {
    throw new Error("Could not extract SMILES from the generated PROTAC sketcher.");
  }
  return smiles;
}

async function requestRdkitDescriptors(smiles) {
  const response = await fetch("/api/admet/run", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ smiles, source: "builder" }),
  });
  const data = await readJsonResponse(response);
  if (!response.ok || !data.success) {
    throw new Error(data.error || data.details || "RDKit parameter generation failed.");
  }
  return data;
}

async function requestDeepPkReport(smiles) {
  const response = await fetch("/api/deeppk/run", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ smiles, source: "builder" }),
  });
  const data = await readJsonResponse(response);
  if (!response.ok || !data.success) {
    throw data;
  }
  return data;
}

async function getParameters() {
  const button = document.getElementById("get-parameters-button");
  const results = document.getElementById("pdf-download-container");
  const rdkitResults = document.getElementById("rdkit-parameters-container");
  const loaderTarget = "#deeppk-loader";

  if (results) results.innerHTML = "";

  try {
    setParameterButton(button, "Calculating RDKit…", true);
    const smiles = await extractProtacSmiles();

    const rdkitData = await requestRdkitDescriptors(smiles);
    renderRdkitPanel(rdkitResults, rdkitData, "Molecular Parameters");

    setParameterButton(button, "Running DeepPK…", true);
    window.ProtacLoader.show({
      mode: "inline",
      target: loaderTarget,
      title: "Running DeepPK molecular parameter workflow…",
      messages: DEEPPK_LOADING_MESSAGES,
      subtle: "DeepPK can take a moment if the external prediction server is busy. Your RDKit descriptor table is already available below.",
    });

    const deepPkData = await requestDeepPkReport(smiles);
    window.ProtacLoader.hide(loaderTarget);

    renderDeepPkReady(results, deepPkData);
    renderRdkitPanel(
      rdkitResults,
      { properties: deepPkData.rdkit_descriptors || rdkitData.properties, warnings: deepPkData.warnings || rdkitData.warnings },
      "Supplemental RDKit Molecular Parameters",
    );
    setParameterButton(button, "Report Ready", false);
  } catch (error) {
    window.ProtacLoader.hide(loaderTarget);

    if (error && typeof error === "object" && (error.error || error.details || error.stage || error.job_id)) {
      renderDeepPkFailure(results, error);
      setParameterButton(button, "DeepPK Retry Available", false);
      return;
    }

    renderInlineError(results, "Molecular parameter generation failed", [
      escapeHtml(error?.message || "The molecular parameter workflow could not start."),
    ]);
    setParameterButton(button, "Get Parameters", false);
  }
}
