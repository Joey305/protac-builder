let sketcher;
let linkerSketcher;
let chemDoodleInitialized = false; // Track ChemDoodle initialization
let selectedSmiles = null; // Store the selected SMILES
ChemDoodle.iChemLabsServer = null; // ✅ Prevent cloud requests


// Track how many save buttons have been clicked
let saveClicks = {
    warhead: false,
    linker: false,
    ligase: false
};

// Disable all ChemDoodle cloud lookups
ChemDoodle.iChemLabs = {
    server: null,
    useServices: false
};
ChemDoodle.feature = {
    uil: { loadRemote: false }
};
console.log("🛑 ChemDoodle cloud disabled fully.");




// ✅ Get linker SMILES from the template
const linkerSmiles = "{{ linker_smiles }}".trim();
// ✅ Get BASE of Liganadlyzer Files
const LIGANDALYZER_BASE = "/static/ligases/";





$(document).ready(function () {
    console.log("🔄 Initializing ChemDoodle editors...");

    try {
        if (typeof ChemDoodle !== "undefined") {

            console.log("✅ ChemDoodle successfully loaded.");
            ChemDoodle.iChemLabs.server = null;

            // Initialize sketchers
            sketcher = new ChemDoodle.SketcherCanvas("ligand-editor", 300, 300, { useServices: false });
            linkerSketcher = new ChemDoodle.SketcherCanvas("linker-editor", 300, 300, { useServices: false });
            ligaseSketcher = new ChemDoodle.SketcherCanvas("ligase-editor", 300, 300, { useServices: false });

            chemDoodleInitialized = true;

            // ✅ publish for other functions that check window.*
            window.chemDoodleInitialized = true;
            window.sketcher = sketcher;
            window.linkerSketcher = linkerSketcher;
            window.ligaseSketcher = ligaseSketcher;

            window.ChemDoodleEditorsReady = true;
            console.log("🟢 ChemDoodle editors ready.");



            // ✅ Auto-load ligase from URL if present
            const urlParams = new URLSearchParams(window.location.search);
            const ligaseCode = urlParams.get("ligase");

            if (ligaseCode) {
                console.log(`🔄 Auto-loading Ligase from URL: ${ligaseCode}`);
                renderLigase(ligaseCode);
            }
        } else {
            throw new Error("❌ ChemDoodle is not defined.");
        }
    } catch (error) {
        console.error("Error initializing ChemDoodle editors:", error.message);
    }
});




// =========================================================
// 🔥 URL HANDOFF: ?smiles=... → auto-load into Warhead editor
// =========================================================
function getWarheadSmilesFromURL() {
    const params = new URLSearchParams(window.location.search);

    const val =
        params.get("smiles") ||
        params.get("lig_smi") ||
        params.get("warhead_smiles") ||
        params.get("warheadSmiles");

    console.log("🌐 PROTAC Builder URL debug:", {
        href: window.location.href,
        search: window.location.search,
        smiles: params.get("smiles"),
        lig_smi: params.get("lig_smi"),
        resolved: val
    });

    return val;
}

async function loadWarheadSmilesFromURL(rawSmiles) {
    if (!rawSmiles || !rawSmiles.trim()) return false;

    // URLSearchParams already decodes encodeURIComponent().
    // Do NOT decodeURIComponent() again here.
    const smiles = rawSmiles.trim();

    if (!chemDoodleInitialized || !sketcher) {
        console.warn("⚠ ChemDoodle not ready for URL SMILES. Retrying...");
        setTimeout(() => loadWarheadSmilesFromURL(smiles), 200);
        return false;
    }

    console.log("🚀 URL handoff detected. Loading warhead SMILES:", smiles);

    // Prevent stale previous warhead from being used when Generate PROTAC is clicked.
    sessionStorage.removeItem("modifiedLigand");
    sessionStorage.removeItem("savedMolecule");
    sessionStorage.removeItem("combinedMOL");
    sessionStorage.removeItem("generatedSMILES");

    if (saveClicks && Object.prototype.hasOwnProperty.call(saveClicks, "warhead")) {
        saveClicks.warhead = false;
    }

    // Clear dropdown selection because this warhead is coming from URL, not V-LiSEMOD dropdown.
    const warheadDropdown = document.getElementById("warhead");
    if (warheadDropdown) warheadDropdown.value = "";

    // Put SMILES visibly into the manual input box.
    const input = document.getElementById("warhead-smiles-input");
    if (input) input.value = smiles;

    // Open the SMILES panel so the user can see what was imported.
    const panel = document.getElementById("warhead-smiles-panel");
    if (panel) panel.classList.add("open");

    const toggleBtn = document.querySelector("[onclick*='warhead-smiles-panel']");
    if (toggleBtn) {
        toggleBtn.classList.add("active");
        toggleBtn.textContent = "Hide SMILES";
    }

    // Load directly into the warhead/ligand editor.
    const ok = await loadSmilesIntoEditor(
        smiles,
        sketcher,
        "#ligand-container",
        "warhead from Target Builder"
    );

    if (ok) {
        sessionStorage.setItem("warheadSource", "url-smiles");
        sessionStorage.setItem("warheadHandoffSmiles", smiles);

        if (typeof showAlert === "function") {
            showAlert("✅ Warhead loaded from Target Builder SMILES. Add your U attachment atom, then click Save.", "success");
        }

        console.log("✅ URL SMILES successfully loaded into Warhead editor.");
    }

    return ok;
}


$(document).ready(function () {
    console.log("🔄 Initializing ligand, linker, ligase, and URL handoff SMILES...");

    const urlParams = new URLSearchParams(window.location.search);

    const warheadSmiles = getWarheadSmilesFromURL();
    const ligandCode    = urlParams.get("ligand");
    const linkerSmiles  = urlParams.get("linker");
    const ligaseCode    = urlParams.get("ligase");

    // Highest priority: direct SMILES handoff from Target Builder.
    // This must win over ligandCode so the handoff molecule is not overwritten.
    if (warheadSmiles) {
        loadWarheadSmilesFromURL(warheadSmiles);
    } else if (ligandCode) {
        console.log(`🔄 Auto-loading Ligand: ${ligandCode}`);
        loadLigandFromCode(ligandCode);
    }

    if (linkerSmiles) {
        console.log(`🔄 Auto-loading Linker: ${linkerSmiles}`);
        openLinkerEditor(linkerSmiles);
    }

    if (ligaseCode) {
        console.log(`🔄 Auto-loading Ligase: ${ligaseCode}`);
        renderLigase(ligaseCode);
    }
});

// ============================================================================
// LIGASE DROPDOWN LOADER
// ============================================================================
async function loadLigaseDropdown() {
    try {
        const res = await fetch("/api/ligases");
        const ligases = await res.json();

        const dropdown = document.getElementById("ligase-dropdown");
        if (!dropdown) {
            console.error("❌ ligase-dropdown element not found.");
            return;
        }

        dropdown.innerHTML = '<option value="">Select a Ligase Recruiter</option>';

        ligases.forEach(name => {
            const opt = document.createElement("option");
            opt.value = name;
            opt.textContent = name;
            dropdown.appendChild(opt);
        });

        console.log("✅ Ligase dropdown loaded:", ligases.length, "items");

    } catch (err) {
        console.error("❌ Error loading ligase dropdown:", err);
    }
}

document.addEventListener("DOMContentLoaded", () => {
    console.log("📥 DOM ready → loading ligase dropdown…");

    loadLigaseDropdown();

    const ligaseDropdown = document.getElementById("ligase-dropdown");

    if (!ligaseDropdown) {
        console.warn("⚠ ligase-dropdown not found; skipping dropdown listener.");
        return;
    }

    ligaseDropdown.addEventListener("change", async (e) => {
        const ligase = e.target.value;
        if (!ligase) return;

        console.log("🧪 Loading ligase:", ligase);

        try {
            const res = await fetch(`/api/ligase/raw/${encodeURIComponent(ligase)}`);
            const data = await res.json();

            if (data.error) {
                console.error("❌ Ligase backend error:", data.error);
                return;
            }

            if (!data.mol_block) {
                console.error("❌ No MOL block returned for ligase:", data);
                return;
            }

            const mol = ChemDoodle.readMOL(data.mol_block);

            ligaseSketcher.clear();
            ligaseSketcher.loadMolecule(mol);
            ligaseSketcher.repaint();

            console.log("✅ Ligase loaded into editor:", ligase);

        } catch (err) {
            console.error("❌ Error loading ligase:", err);
        }
    });
});


// 2️⃣ On page load, initialize the dropdown
document.addEventListener("DOMContentLoaded", () => {
    console.log("📥 DOM ready → loading ligase dropdown…");
    loadLigaseDropdown();
});

document.addEventListener("DOMContentLoaded", () => {
    const ligaseDropdown = document.getElementById("ligase-dropdown");

    if (!ligaseDropdown) {
        console.warn("⚠ ligase-dropdown not found; skipping dropdown listener.");
        return;
    }

    ligaseDropdown.addEventListener("change", async (e) => {
        const ligase = e.target.value;
        if (!ligase) return;

        console.log("🧪 Loading ligase:", ligase);

        const res = await fetch(`/api/ligase/raw/${encodeURIComponent(ligase)}`);
        const data = await res.json();

        if (data.error) {
            console.error(data.error);
            return;
        }

        const mol = ChemDoodle.readMOL(data.mol_block);
        ligaseSketcher.clear();
        ligaseSketcher.loadMolecule(mol);
        ligaseSketcher.repaint();
    });
});












$(document).ready(function () {
    console.log("🔄 Initializing ligand selection in COPYindex...");

    function getLigandFromURL() {
        const params = new URLSearchParams(window.location.search);
        return params.get("ligand"); // ✅ Extract ligand code
    }

    function initializeLigand() {
        if (!chemDoodleInitialized) {
            console.warn("⚠ ChemDoodle not ready. Retrying...");
            setTimeout(initializeLigand, 200);
            return;
        }

        const urlSmiles = getWarheadSmilesFromURL();
        if (urlSmiles) {
            console.log("✅ URL SMILES handoff active; skipping ligand-code auto-load.");
            return;
        }

        const ligandCode = getLigandFromURL();
        if (ligandCode) {
            console.log("✅ Auto-loading ligand in COPYindex:", ligandCode);
            loadLigandFromCode(ligandCode);
        }
    }

    setTimeout(initializeLigand, 500); // ✅ Delay initialization

    // ✅ Handle dropdown changes (manual selection)
    $("#warhead").on("change", function () {
        const selectedSmiles = $(this).val();
        if (selectedSmiles) {
            console.log("✅ New ligand selected:", selectedSmiles);
            loadLigand(selectedSmiles);
        }
    });
});


// ✅ Function to load ligand from backend (URL or dropdown)
function loadLigandFromCode(ligandCode) {
    console.log("🔄 Fetching Ligand:", ligandCode);

    if (!chemDoodleInitialized) {
        console.warn("⚠ ChemDoodle not ready. Retrying...");
        setTimeout(() => loadLigandFromCode(ligandCode), 200);
        return;
    }

    // ✅ Ensure the ligand container is visible
    $("#ligand-container").show();

    // ✅ Fetch ligand's SMILES from the backend
    $.ajax({
        url: `/api/ligand/data?ligand=${ligandCode}`, // Flask API endpoint
        type: "GET",
        success: function (data) {
            if (data.mol_block) {
                console.log("✅ Received MOL block, loading into ChemDoodle...");
                const molecule = ChemDoodle.readMOL(data.mol_block);
                sketcher.clear();
                sketcher.loadMolecule(molecule);
                console.log("✅ Ligand loaded into ChemDoodle.");

                // ✅ Open a second window with the same ligand
                // openNewLigandEditor(ligandCode);

            } else {
                console.error("❌ Failed to load ligand.");
            }
        },
        error: function (xhr) {
            console.error("❌ Error fetching ligand data.");

            const fallbackValue = String(ligandCode || "").trim();
            if (xhr && xhr.status === 404 && fallbackValue) {
                console.log("↩️ Ligand code lookup missed; retrying incoming value as raw SMILES:", fallbackValue);
                loadLigand(fallbackValue);
            }
        }
    });
}


// ✅ Load ligand into ChemDoodle Editor, prioritizing stored modification
function loadLigand(smiles) {
    console.log("🔄 Loading Ligand:", smiles);

    if (!chemDoodleInitialized) {
        console.warn("⚠ ChemDoodle not ready. Retrying...");
        setTimeout(() => loadLigand(smiles), 200);
        return;
    }

    // ✅ Check if modified ligand exists in sessionStorage
    const savedMolBlock = sessionStorage.getItem("modifiedLigand");
    if (savedMolBlock) {
        console.log("✅ Found modified ligand in storage. Loading into ChemDoodle...");
        const molecule = ChemDoodle.readMOL(savedMolBlock);
        sketcher.clear();
        sketcher.loadMolecule(molecule);
        $("#ligand-container").show();
        return; // ✅ Stop here! Don't send AJAX request.
    }

    // ✅ Ensure the container is visible
    $("#ligand-container").show();

    // ✅ Fetch ligand if no modified version exists
    $.ajax({
        url: "/api/ligand/modify",
        type: "POST",
        contentType: "application/json",
        data: JSON.stringify({ smiles: smiles }),
        success: function (data) {
            if (data.mol_block) {
                console.log("✅ Received MOL block, loading into ChemDoodle...");
                const molecule = ChemDoodle.readMOL(data.mol_block);
                sketcher.clear(); // ✅ Clear previous molecule
                sketcher.loadMolecule(molecule);
                console.log("✅ Ligand loaded into ChemDoodle.");
            } else {
                console.error("❌ Failed to load ligand.");
            }
        },
        error: function () {
            console.error("❌ Error loading ligand.");
        }
    });
}




// Function to open and populate the ChemDoodle linker editor
function openLinkerEditor(smiles = null) {
    

    $("#linker-container").show(); // Ensure ChemDoodle is visible

    if (smiles) {
        // ✅ Ensure SMILES are properly encoded
        const safeSmiles = encodeURIComponent(smiles);

        console.log(`🔄 Loading Linker: ${smiles}`);

        $.ajax({
            url: "/api/molecule/smiles-to-mol",
            type: "POST",
            contentType: "application/json",
            data: JSON.stringify({ smiles: smiles }), // No encoding here, send as-is
            success: function (data) {
                if (data.mol_block) {
                    const molecule = ChemDoodle.readMOL(data.mol_block);
                    linkerSketcher.clear(); // Clear existing molecule
                    linkerSketcher.loadMolecule(molecule); // Load new linker
                    console.log("✅ Linker loaded successfully!");
                } else {
                    console.error("❌ Failed to convert SMILES to MOL.");
                }
            },
            error: function (xhr, status, error) {
                console.error("❌ Error converting SMILES:", error);
            }
        });
    } else {
        linkerSketcher.clear();
        console.log("🆕 'Design Your Own' mode activated - ChemDoodle cleared.");
    }
}





// Event listener for linker dropdown selection
$("#linker").on("change", function () {
    const selectedOption = $(this).val();  

    if (selectedOption === "design-your-own") {
        console.log("🆕 'Design Your Own' selected - clearing ChemDoodle.");
        openLinkerEditor(null);  // ✅ Clears the ChemDoodle container
        return;
    }

    let sortBy;
    let sortOrder = "desc"; // Default sorting order

    switch (selectedOption) {
        case "filter-weight":
            sortBy = "Molecular Weight";
            sortOrder = "asc";
            break;
        case "filter-flexibility":
            sortBy = "Rotatable Bond Count";
            sortOrder = "desc";
            break;
        case "filter-rigidity":
            sortBy = "Rotatable Bond Count";
            sortOrder = "asc";
            break;
        case "filter-polarity":
            sortBy = "Topological Polar Surface Area";
            sortOrder = "desc";
            break;
        case "filter-xlogp":
            sortBy = "XLogP3";
            sortOrder = "desc";
            break;
        default:
            return;
    }

    fetchCuratedLinkers(1, sortBy, sortOrder);
});





// ✅ Function to fetch curated linkers with sorting and filters
/// ✅ Global state to track sorting and filtering
let currentPage = 1;
let currentSortBy = "Molecular Weight";
let currentSortOrder = "asc";

// ✅ Mapping frontend dropdown values to Flask-compatible backend sorting keys
const sortOptionsMap = {
    "Molecular Weight": "Molecular Weight",
    "Rotatable Bond Count": "Rotatable Bond Count",
    "Topological Polar Surface Area": "Topological Polar Surface Area",
    "XLogP3": "XLogP3",
    "Ring Count": "Ring Count" // ✅ Matches backend
};

// ✅ Function to fetch curated linkers with sorting and filters
function fetchCuratedLinkers(page, sortBy = "Molecular Weight", sortOrder = "asc") {
    console.log(`Fetching curated linkers for page: ${page} | Sorting: ${sortBy} (${sortOrder})`);

    // ✅ Ensure correct mapping of sort keys
    const mappedSortBy = sortOptionsMap[sortBy] || "Molecular Weight"; 

    let queryString = `?page=${page}&sort_by=${encodeURIComponent(mappedSortBy)}&sort_order=${sortOrder}`;
    
    // ✅ Apply correct filter parameter names
    const minMW = $("#min-mw").val();
    const maxMW = $("#max-mw").val();
    const minXLogP3 = $("#min-xlogp3").val();
    const maxXLogP3 = $("#max-xlogp3").val();
    const minRingCount = $("#min-ring-count").val();
    const maxRingCount = $("#max-ring-count").val();

    if (minMW) queryString += `&min_Molecular%20Weight=${minMW}`;
    if (maxMW) queryString += `&max_Molecular%20Weight=${maxMW}`;
    if (minXLogP3) queryString += `&min_XLogP3=${minXLogP3}`;
    if (maxXLogP3) queryString += `&max_XLogP3=${maxXLogP3}`;
    if (minRingCount) queryString += `&min_Ring%20Count=${minRingCount}`;
    if (maxRingCount) queryString += `&max_Ring%20Count=${maxRingCount}`;

    // ✅ AJAX Call to Flask Backend
    $.ajax({
        url: `/api/linkers/curated${queryString}`,
        type: "GET",
        beforeSend: function () {
            $("#linkers-list").html("<p>Loading...</p>");
        },
        success: function (data) {
            const linkersList = $("#linkers-list");
            linkersList.empty();

            if (data.length === 0) {
                console.warn("⚠️ No linkers found. Reverting to previous page.");
                currentPage = Math.max(1, currentPage - 1);
                fetchCuratedLinkers(currentPage, currentSortBy, currentSortOrder);
                return;
            }

            data.forEach(linker => {
                linkersList.append(`
                    <div class="linker-item" data-smiles="${linker.smiles}">
                        <div class="svg-thumb" style="width:120px; height:120px;">
                            ${linker.svg}
                        </div>
                        <p><strong>Compound ID:</strong> ${linker.id}<br><strong>MW:</strong> ${linker.molecular_weight.toFixed(2)}</p>
                    </div>
                `);
            });

            $("#curatedLinkersModal").modal("show");

            $("#prev-page").prop("disabled", page === 1);
            $("#next-page").prop("disabled", data.length === 0);
        },
        error: function () {
            console.error("❌ Error fetching curated linkers.");
            $("#linkers-list").html("<p>Error loading linkers. Please try again.</p>");
        }
    });
}




// ✅ Update Sort Selection Dropdown to Modify Sorting State
$("#sort-by").on("change", function () {
    const selectedSort = $(this).val();
    currentSortBy = selectedSort;
    fetchCuratedLinkers(1, currentSortBy, currentSortOrder); // Reset to page 1
});

// ✅ Update Sort Order Selection
$("#sort-order").on("change", function () {
    currentSortOrder = $(this).val();
    fetchCuratedLinkers(1, currentSortBy, currentSortOrder);
});

// ✅ Apply Filters and Reload Data
$("#apply-filters").on("click", function () {
    currentPage = 1; // Reset to first page when filters change
    fetchCuratedLinkers(currentPage, currentSortBy, currentSortOrder);
});

// ✅ Pagination Controls
$("#prev-page").on("click", function () {
    if (currentPage > 1) {
        currentPage--;
        fetchCuratedLinkers(currentPage, currentSortBy, currentSortOrder);
    }
});

$("#next-page").on("click", function () {
    currentPage++;
    fetchCuratedLinkers(currentPage, currentSortBy, currentSortOrder);
});

// ✅ Enable "Select Linker" Button when a Linker is Selected
$(document).on("click", ".linker-item", function () {
    $(".linker-item").removeClass("selected"); // Deselect all items
    $(this).addClass("selected"); // Highlight the selected linker
    selectedSmiles = $(this).data("smiles");

    console.log(`Selected SMILES: ${selectedSmiles}`);
    $("#select-linker").prop("disabled", false); // Enable button after selection
});

// ✅ Event Listener for "Select Linker" Button
$("#select-linker").on("click", function () {
    if (!selectedSmiles) {
        alert("Please select a linker!");
        return;
    }

    $("#curatedLinkersModal").modal("hide");
    console.log(`✅ Selected linker: ${selectedSmiles}`);

    // ✅ Open ChemDoodle Editor and Load SMILES
    openLinkerEditor(selectedSmiles);
});








// Function to render ligase in the ChemDoodle container
function renderLigase(ligaseCode) {
    if (!ligaseSketcher) {
        alert("Please wait for the ChemDoodle ligase editor to load.");
        return;
    }

    console.log(`🔄 Fetching Ligase: ${ligaseCode}`);

    $.ajax({
        url: `/api/ligase/render?ligase=${encodeURIComponent(ligaseCode)}`, // ✅ Use GET instead of POST
        type: "GET",  // ✅ Change from POST to GET
        success: function (data) {
            if (data.mol_block) {
                console.log("✅ Received MOL block, rendering in ChemDoodle...");
                const molecule = ChemDoodle.readMOL(data.mol_block);
                ligaseSketcher.clear(); // ✅ Clear existing molecule
                ligaseSketcher.loadMolecule(molecule); // ✅ Load new molecule
                $("#ligase-container").show(); // ✅ Show the ligase container
                console.log("✅ Ligase successfully loaded!");
            } else {
                console.error("❌ Failed to load MOL block for ligase.");
            }
        },
        error: function (xhr, status, error) {
            console.error(`❌ Error fetching ligase (${ligaseCode}):`, error);
        }
    });
}


// Event listener for ligase dropdown
$("#ligase").on("change", function () {
    const selectedLigase = $(this).val();
    if (selectedLigase) {
        console.log(`Selected Ligase: ${selectedLigase}`);
        renderLigase(selectedLigase);
    } else {
        console.error("❌ No ligase selected.");
    }
});

// Function to save ligase with V -> R2 conversion





// Function to save the Ligand (Warhead) component
function saveLigand() {
    if (!chemDoodleInitialized) {
        alert("Please wait for the ChemDoodle editor to load.");
        return;
    }

    try {
        const molecule = sketcher.getMolecule();
        if (!molecule) {
            alert("❌ No molecule loaded to save!");
            return;
        }

        molecule.atoms.forEach(atom => {
            if (atom.label === "U") {
                atom.label = "R1";
                console.log(`✅ Updated atom label: U -> R1`);
            }
        });

        const molBlock = ChemDoodle.writeMOL(molecule);
        sessionStorage.setItem("savedMolecule", molBlock);
        console.log("✅ Warhead MOL Block saved.");

        saveClicks.warhead = true; // Mark warhead as saved
        saveButtonFeedback("ligandSaveButton");
        checkAllSaved(); 

    } catch (error) {
        console.error("❌ Error saving ligand:", error.message);
    }
}





// Function to save the Linker component
function saveLinker() {
    if (!chemDoodleInitialized) {
        alert("Please wait for the ChemDoodle editor to load.");
        return;
    }

    try {
        const molecule = linkerSketcher.getMolecule();
        if (!molecule) {
            alert("❌ No molecule loaded to save!");
            return;
        }

        molecule.atoms.forEach(atom => {
            if (atom.label === "U") {
                atom.label = "R1";
                console.log(`✅ Updated atom label: U -> R1`);
            }
            if (atom.label === "V") {
                atom.label = "R2";
                console.log(`✅ Updated atom label: V -> R2`);
            }
        });

        const molBlock = ChemDoodle.writeMOL(molecule);
        sessionStorage.setItem("savedLinker", molBlock);
        console.log("✅ Linker MOL Block saved.");

        saveClicks.linker = true; // Mark linker as saved
        saveButtonFeedback("linkerSaveButton");
        checkAllSaved(); 

    } catch (error) {
        console.error("❌ Error saving linker:", error.message);
    }
}



// Function to save the Ligase component
function saveLigase() {
    if (!chemDoodleInitialized) {
        alert("Please wait for the ChemDoodle editor to load.");
        return;
    }

    try {
        const molecule = ligaseSketcher.getMolecule();
        if (!molecule) {
            alert("❌ No molecule loaded to save!");
            return;
        }

        molecule.atoms.forEach(atom => {
            if (atom.label === "V") {
                atom.label = "R2";
                console.log(`✅ Updated atom label: V -> R2`);
            }
        });

        const molBlock = ChemDoodle.writeMOL(molecule);
        sessionStorage.setItem("savedLigase", molBlock);
        console.log("✅ Ligase MOL Block saved.");

        saveClicks.ligase = true; // Mark ligase as saved
        saveButtonFeedback("ligaseSaveButton");
        checkAllSaved(); 

    } catch (error) {
        console.error("❌ Error saving ligase:", error.message);
    }
}




// Function for Save Button UI Feedback
function saveButtonFeedback(buttonId) {
    const button = document.getElementById(buttonId);
    if (!button) {
        console.error(`❌ Error: Button with ID '${buttonId}' not found.`);
        return;
    }

    button.innerText = "✅ Saved!";
    button.style.backgroundColor = "#28a745"; // Green for success

    setTimeout(() => {
        button.innerText = "Save";
        button.style.backgroundColor = ""; // Reset to default
    }, 2000); // Reset after 2 seconds
}









function toggleVisibility(containerId) {
    const container = document.getElementById(containerId);
    if (container) {
        container.style.display = "block";
    }
}


// Function to remove ChemDoodle toolbars
function removeChemDoodleToolbars() {
    const toolbars = document.querySelectorAll('.ChemDoodleToolbar');
    toolbars.forEach(toolbar => toolbar.remove());
    console.log('✅ ChemDoodle toolbars removed.');
}

// Call this function after ChemDoodle editors are initialized
$(document).ready(function () {
    setTimeout(removeChemDoodleToolbars, 100); // Delay to ensure editors are initialized
});


// Event listener for selecting a linker
$(document).on("click", ".linker-item", function () {
    // Remove 'selected' class from all linker items
    $(".linker-item").removeClass("selected");

    // Add 'selected' class to the clicked item
    $(this).addClass("selected");

    // Store the selected SMILES
    selectedSmiles = $(this).data("smiles");

    // Log the selected SMILES for debugging
    console.log(`Selected SMILES: ${selectedSmiles}`);
});




function downloadProtac(smiles) {
    const blob = new Blob([smiles], { type: "text/plain" });
    const a = document.createElement("a");
    a.href = URL.createObjectURL(blob);
    a.download = "vlsmod-protac.smiles";
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
}



function getMolFromCanvas(canvasId) {
    // Determine which editor corresponds to the given canvasId
    let editor;
    if (canvasId === "ligand-editor") {
        editor = sketcher;
    } else if (canvasId === "linker-editor") {
        editor = linkerSketcher;
    } else if (canvasId === "ligase-editor") {
        editor = ligaseSketcher;
    } else {
        console.error(`No editor found for canvasId: ${canvasId}`);
        return null;
    }

    // Retrieve the molecule and return it as a MOL block
    const molecule = editor.getMolecule();
    if (!molecule) {
        console.error(`No molecule found in canvas: ${canvasId}`);
        return null;
    }
    return ChemDoodle.writeMOL(molecule);
}



let protacSketcher; // Global variable to hold the PROTAC sketcher instance

$(document).ready(function () {
    protacSketcher = new ChemDoodle.SketcherCanvas("protac-sketcher", 600, 400, {
        useServices: false,
        includeToolbar: true,  // Enable the toolbar for editing
        oneMolecule: true      // Optimize for single-molecule sketching
    });
    console.log("✅ PROTAC SketcherCanvas initialized.");
});









async function logProtacToServer(warheadMol, linkerMol, ligaseMol, protacMol, protacSmiles) {
    try {
        const response = await fetch('/api/protac/log', {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                source: "web",
                count_usage: true,
                warhead_mol: warheadMol,
                linker_mol: linkerMol,
                ligase_mol: ligaseMol,
                protac_mol: protacMol,
                protac_smiles: protacSmiles
            })
        });

        const data = await response.json();
        if (data.success) {
            console.log("📁 PROTAC logged successfully.");
        } else {
            console.warn("⚠️ Logging returned an error:", data);
        }
    } catch (error) {
        console.error("❌ Error logging PROTAC:", error);
    }
}


window.combineMolecules = async function () {
    const warheadMolBlock = sessionStorage.getItem("savedMolecule");
    const linkerMolBlock = sessionStorage.getItem("savedLinker");
    const ligaseMolBlock = sessionStorage.getItem("savedLigase");

    if (!warheadMolBlock || !linkerMolBlock || !ligaseMolBlock) {
        alert("❌ Please save all components (Warhead, Linker, Ligase) before combining.");
        return;
    }

    // Show loader while processing
    const loader = document.getElementById("loader");
    if (loader) loader.style.display = "block";

    try {
        // Parse MOL blocks
        const warhead = ChemDoodle.readMOL(warheadMolBlock);
        const linker = ChemDoodle.readMOL(linkerMolBlock);
        const ligase = ChemDoodle.readMOL(ligaseMolBlock);

        console.log("✅ Loaded all molecules.");

        /*** Step 1: Merge Warhead and Linker at R1 ***/
        const warheadAnchor = warhead.atoms.find(a => a.label === 'R1');
        const linkerAnchorR1 = linker.atoms.find(a => a.label === 'R1');

        if (!warheadAnchor || !linkerAnchorR1) {
            showAlert("❌ R1 not found in Warhead or Linker.");
            return;
        }

        // Find atoms bonded to R1
        const warheadBond = warhead.bonds.find(b => b.a1 === warheadAnchor || b.a2 === warheadAnchor);
        const linkerBondR1 = linker.bonds.find(b => b.a1 === linkerAnchorR1 || b.a2 === linkerAnchorR1);

        if (!warheadBond || !linkerBondR1) {
            showAlert("❌ Could not locate bonds for R1.");
            return;
        }

        // Get atoms that should be bonded after R1 removal
        const warheadAtomToBond = warheadBond.a1 === warheadAnchor ? warheadBond.a2 : warheadBond.a1;
        const linkerAtomToBondR1 = linkerBondR1.a1 === linkerAnchorR1 ? linkerBondR1.a2 : linkerBondR1.a1;

        // Remove R1 atoms & their bonds
        warhead.atoms = warhead.atoms.filter(a => a !== warheadAnchor);
        linker.atoms = linker.atoms.filter(a => a !== linkerAnchorR1);
        warhead.bonds = warhead.bonds.filter(b => b !== warheadBond);
        linker.bonds = linker.bonds.filter(b => b !== linkerBondR1);

        // Create new bond between warhead and linker
        const newBond1 = new ChemDoodle.structures.Bond(warheadAtomToBond, linkerAtomToBondR1, 1);
        linker.bonds.push(newBond1);

        // Create intermediate molecule
        const intermediateMolecule = new ChemDoodle.structures.Molecule();
        intermediateMolecule.atoms = [...warhead.atoms, ...linker.atoms];
        intermediateMolecule.bonds = [...warhead.bonds, ...linker.bonds];

        sessionStorage.setItem("intermediateMOL", ChemDoodle.writeMOL(intermediateMolecule));
        console.log("✅ intermediate.mol stored in session.");

        /*** Step 2: Merge Intermediate and Ligase at R2 ***/
        const linkerAnchorR2 = intermediateMolecule.atoms.find(a => a.label === 'R2');
        const ligaseAnchor = ligase.atoms.find(a => a.label === 'R2');

        if (!linkerAnchorR2 || !ligaseAnchor) {
            showAlert("❌ R2 not found in Intermediate or Ligase.");
            return;
        }

        // Find atoms bonded to R2
        const linkerBondR2 = intermediateMolecule.bonds.find(b => b.a1 === linkerAnchorR2 || b.a2 === linkerAnchorR2);
        const ligaseBond = ligase.bonds.find(b => b.a1 === ligaseAnchor || b.a2 === ligaseAnchor);

        if (!linkerBondR2 || !ligaseBond) {
            showAlert("❌ Could not locate bonds for R2.");
            return;
        }

        // Get atoms bonded to R2 for proper bonding
        const linkerAtomToBondR2 = linkerBondR2.a1 === linkerAnchorR2 ? linkerBondR2.a2 : linkerBondR2.a1;
        const ligaseAtomToBond = ligaseBond.a1 === ligaseAnchor ? ligaseBond.a2 : ligaseBond.a1;

        // Remove R2 atoms & their bonds
        intermediateMolecule.atoms = intermediateMolecule.atoms.filter(a => a !== linkerAnchorR2);
        ligase.atoms = ligase.atoms.filter(a => a !== ligaseAnchor);
        intermediateMolecule.bonds = intermediateMolecule.bonds.filter(b => b !== linkerBondR2);
        ligase.bonds = ligase.bonds.filter(b => b !== ligaseBond);

        // Create new bond between intermediate and ligase
        const newBond2 = new ChemDoodle.structures.Bond(linkerAtomToBondR2, ligaseAtomToBond, 1);
        ligase.bonds.push(newBond2);

        // Create final molecule
        const finalMolecule = new ChemDoodle.structures.Molecule();
        finalMolecule.atoms = [...intermediateMolecule.atoms, ...ligase.atoms];
        finalMolecule.bonds = [...intermediateMolecule.bonds, ...ligase.bonds];

        // Remove orphaned atoms (leftover R1 or R2 references)
        finalMolecule.atoms = finalMolecule.atoms.filter(a => a.label !== 'R1' && a.label !== 'R2');

        console.log("✅ Removed orphaned atoms and bonds.");

        // Save final cleaned molecule
        sessionStorage.setItem("combinedMOL", ChemDoodle.writeMOL(finalMolecule));
        console.log("✅ Cleaned combined.mol stored in session.");

        // Generate SMILES
        console.log("⏳ Converting `combined.mol` to SMILES...");
        // const smiles = await convertMolToSmiles(sessionStorage.getItem("combinedMOL"));
        let smiles = await convertMolToSmiles(sessionStorage.getItem("combinedMOL"));

        // Fallback to ChemDoodle SMILES if RDKit fails
        if (!smiles || smiles.trim() === "") {
            console.warn("⚠️ RDKit failed to generate SMILES — using Sketcher fallback.");
            try {
                smiles = protacSketcher.getSmiles();
            } catch (e) {
                console.error("❌ Sketcher fallback failed:", e);
            }
        }


        const finalMolBlock = ChemDoodle.writeMOL(finalMolecule);

        await logProtacToServer(
            warheadMolBlock,
            linkerMolBlock,
            ligaseMolBlock,
            finalMolBlock,
            smiles
        );

        
        if (!smiles) {
            alert("❌ Failed to generate SMILES. Please make sure that there are no issues with valence electrons (e.g. nitrogens bound to 4 atoms, oxygens bound to 3 atoms, etc)");
            return;
        }

        sessionStorage.setItem("generatedSMILES", smiles);
        document.getElementById("smiles-output").textContent = `Generated SMILES: ${smiles}`;
        document.getElementById("download-smiles-button").style.display = "inline-block";
        document.getElementById("get-parameters-button").style.display = "inline-block";
        document.getElementById("generate-files-button").style.display = "inline-block";
        console.log("✅ SMILES generated and displayed.");
        // ✅ SHOW THE PROTAC SKETCHER CONTAINER
        document.getElementById("protac-container").style.display = "block";
        // ✅ SCROLL DOWN TO IT SMOOTHLY
        document.getElementById("protac-container").scrollIntoView({ behavior: "smooth", block: "start" });

        // **Display the SMILES in the PROTAC Sketcher**
        console.log("⏳ Converting SMILES to MOL for visualization...");
        await renderProtacFromSmiles(smiles);

    } catch (error) {
        console.error("❌ Error generating PROTAC: ", error);
    } finally {
        if (loader) loader.style.display = "none";
    }
};


async function renderProtacFromSmiles(smiles) {
    try {
        const response = await fetch('/api/molecule/smiles-to-mol', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ smiles })
        });

        const data = await response.json();
        if (data.error) {
            console.error("❌ Error converting SMILES to MOL:", data.error);
            return;
        }

        console.log("✅ MOL block successfully generated from SMILES.");

        const protacMolecule = ChemDoodle.readMOL(data.mol_block);
        protacSketcher.clear();
        protacSketcher.loadMolecule(protacMolecule);
        console.log("✅ PROTAC rendered in Sketcher from SMILES.");
    } catch (error) {
        console.error("❌ Error rendering PROTAC from SMILES:", error);
    }
}



// Convert MOL to SMILES by calling the Flask backend
window.convertMolToSmiles = async function (molBlock) {
    try {
        const response = await fetch('/api/molecule/mol-to-smiles', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ molBlock })
        });
        const data = await response.json();
        if (data.error) {
            console.error("❌ Error converting MOL to SMILES:", data.error);
            return null;
        }
        console.log("✅ SMILES successfully generated:", data.smiles);
        return data.smiles;
    } catch (error) {
        console.error("❌ Error in convertMolToSmiles:", error);
        return null;
    }
};




async function generateProtac() {
    const loader = document.getElementById("loader");
    if (loader) loader.style.display = "block";

    try {
        const response = await fetch("/api/molecule/mol-to-smiles", {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
            },
            body: JSON.stringify({ molBlock: molBlockData }), // Ensure molBlockData is defined
        });

        const data = await response.json();

        if (response.ok && data.smiles) {
            const smiles = data.smiles;
            sessionStorage.setItem("generatedSMILES", smiles);
            window.LAST_GENERATED_SMILES = smiles;
            document.getElementById("smiles-output").textContent = `Generated SMILES: ${smiles}`;
            document.getElementById("download-smiles-button").style.display = "inline-block";
            document.getElementById("get-parameters-button").style.display = "inline-block";
            console.log("✅ SMILES generated and displayed.");

            // ✅ SHOW THE PROTAC SKETCHER CONTAINER
            document.getElementById("protac-container").style.display = "block";
            document.getElementById("protac-container").scrollIntoView({ behavior: "smooth", block: "start" });

            // **Display the SMILES in the PROTAC Sketcher**
            console.log("⏳ Converting SMILES to MOL for visualization...");
            await renderProtacFromSmiles(smiles);
            try {
                await fetch("/api/protac/log", {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({
                        source: "web",
                        count_usage: true,
                        warhead_mol: sessionStorage.getItem("savedMolecule") || "",
                        linker_mol: sessionStorage.getItem("savedLinker") || "",
                        ligase_mol: sessionStorage.getItem("savedLigase") || "",
                        protac_mol: molBlockData || "",
                        protac_smiles: smiles
                    })
                });
                console.log("✅ Builder usage logged.");
            } catch (logError) {
                console.warn("⚠️ PROTAC usage log failed, but generation succeeded:", logError);
            }

        } else {
            console.warn("❌ No SMILES generated. Possible issue with attachment points.");
            document.getElementById("smiles-output").textContent = "⚠️ No SMILES generated.";
            alert("⚠️ Make sure that attachment points have been added to all PROTAC pieces.\n\n✅ One 'U' in the Target\n✅ One 'U' and one 'V' in the Linker\n✅ One 'V' in the Ligase Recruiter.");
        }
    } catch (error) {
        console.error("❌ Error generating PROTAC: ", error);
        alert("❌ Error generating PROTAC. Please check your input and try again.");
    } finally {
        if (loader) loader.style.display = "none";
    }
}







// Download SMILES file
window.downloadSMILES = function () {
    let smiles = sessionStorage.getItem("generatedSMILES");

    if (!smiles) {
        smiles = window.LAST_GENERATED_SMILES;
    }



    if (!smiles) {
        // final fallback: read from ChemDoodle
        if (typeof sketcher !== "undefined") {
            try {
                const mol = sketcher.getMolecule();
                smiles = ChemDoodle.writeSMILES(mol);
                sessionStorage.setItem("generatedSMILES", smiles);
            } catch {}
        }
    }

    if (!smiles) {
        alert("❌ No SMILES data available to download.");
        return;
    }

    const blob = new Blob([smiles], { type: "text/plain" });
    const link = document.createElement("a");
    link.href = URL.createObjectURL(blob);
    link.download = "JARI.smiles";
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);

    console.log("✅ SMILES file downloaded.");
};


// Function to display alert messages dynamically
function showAlert(message, type = "info") {
    const alertBox = document.getElementById("alert-box");
    alertBox.textContent = message;
    alertBox.className = `alert alert-${type} text-center`;
    alertBox.style.display = "block";

    setTimeout(() => {
        alertBox.style.display = "none";
    }, 3000); // Hide after 3 seconds
}


// Function to check if all three components are saved and enable the Generate button
function checkAllSaved() {
    const generateButton = document.querySelector(".btn-success");

    // Ensure all three components have been saved at least once
    if (saveClicks.warhead && saveClicks.linker && saveClicks.ligase) {
        generateButton.disabled = false;
        showAlert("🛡️ PROTAC Warrior Assembled! Click 'Generate PROTAC'.", "success");
    } else {
        generateButton.disabled = true;
    }
}

// Add event listeners to track button clicks properly
document.getElementById("ligandSaveButton").addEventListener("click", function () {
    const molBlock = ChemDoodle.writeMOL(sketcher.getMolecule());
    if (!molBlock) {
        alert("❌ No molecule loaded to save!");
        return;
    }
    sessionStorage.setItem("savedMolecule", molBlock);
    checkAllSaved();
});

document.getElementById("linkerSaveButton").addEventListener("click", function () {
    const molBlock = ChemDoodle.writeMOL(linkerSketcher.getMolecule());
    if (!molBlock) {
        alert("❌ No molecule loaded to save!");
        return;
    }
    sessionStorage.setItem("savedLinker", molBlock);
    checkAllSaved();
});

document.getElementById("ligaseSaveButton").addEventListener("click", function () {
    const molBlock = ChemDoodle.writeMOL(ligaseSketcher.getMolecule());
    if (!molBlock) {
        alert("❌ No molecule loaded to save!");
        return;
    }
    sessionStorage.setItem("savedLigase", molBlock);
    checkAllSaved();
});




document.querySelectorAll('.info-icon').forEach(icon => {
    icon.addEventListener('mouseover', function () {
        // Remove any existing tooltip container
        let existingTooltip = this.querySelector(".tooltip-container");
        if (existingTooltip) existingTooltip.remove();

        // Create tooltip container
        let tooltip = document.createElement("div");
        tooltip.className = "tooltip-container";
        tooltip.style.position = "absolute";
        tooltip.style.left = "50%";
        tooltip.style.bottom = "220%";
        tooltip.style.transform = "translateX(-50%)";
        tooltip.style.background = "rgba(0, 0, 0, 0.95)";
        tooltip.style.color = "#fff";
        tooltip.style.padding = "10px";
        tooltip.style.borderRadius = "8px";
        tooltip.style.boxShadow = "0px 4px 10px rgba(0, 0, 0, 0.3)";
        tooltip.style.textAlign = "center";
        tooltip.style.whiteSpace = "nowrap";
        tooltip.style.opacity = "0";
        tooltip.style.transition = "opacity 0.3s ease-in-out";
        tooltip.style.zIndex = "9999";
        tooltip.style.pointerEvents = "auto";
        tooltip.style.display = "flex";
        tooltip.style.flexDirection = "column";
        tooltip.style.alignItems = "center";
        tooltip.style.justifyContent = "center";

        // Add tooltip text
        let text = document.createElement("p");
        text.innerText = this.getAttribute("data-tooltip");
        text.style.margin = "0 0 5px 0";
        text.style.fontSize = "14px";

        // Create an image element for GIF
        let gif = document.createElement("img");
        gif.src = `/static/images/${this.getAttribute("data-gif")}`;
        gif.className = "tooltip-image";
        gif.style.width = "200px";
        gif.style.borderRadius = "5px";

        // Append elements
        tooltip.appendChild(text);
        tooltip.appendChild(gif);
        this.appendChild(tooltip);

        // Fade-in effect
        setTimeout(() => {
            tooltip.style.opacity = "1";
        }, 10);
    });

    icon.addEventListener('mouseleave', function () {
        let tooltip = this.querySelector(".tooltip-container");
        if (tooltip) tooltip.remove();  // Remove the tooltip when the mouse leaves
    });
});

function loadWarheadIntoEditor(smiles) {
    if (!window.chemDoodleInitialized) {
        console.warn("⚠ Waiting for ChemDoodle to initialize...");
        setTimeout(() => loadWarheadIntoEditor(smiles), 500);
        return;
    }

    $.ajax({
        url: "/api/molecule/smiles-to-mol",  // Flask API to convert SMILES → MOL
        type: "POST",
        contentType: "application/json",
        data: JSON.stringify({ smiles: smiles }),
        success: function (data) {
            if (data.mol_block) {
                const molecule = ChemDoodle.readMOL(data.mol_block);
                window.sketcher.clear();
                window.sketcher.loadMolecule(molecule);
                $("#ligand-container").show();
                console.log("✅ Warhead ligand loaded into ChemDoodle.");
            } else {
                console.error("❌ Failed to convert SMILES to MOL.");
            }
        },
        error: function (xhr, status, error) {
            console.error("Error converting SMILES to MOL:", error);
        }
    });
}



// Redirect to main page (index)
function redirectToHome() {
    window.location.href = "/";  // Change URL if needed
}







async function getSmilesFromSketcher() {
    try {
        const molecule = protacSketcher.getMolecule();

        if (!molecule) {
            console.error("❌ No molecule found in PROTAC sketcher.");
            return null;
        }

        // Convert molecule → MOLBLOCK
        const molBlock = ChemDoodle.writeMOL(molecule);

        // Convert MOLBLOCK → SMILES via backend
        const resp = await fetch("/api/molecule/mol-to-smiles", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ molBlock })
        });

        const data = await resp.json();

        if (data.smiles) {
            console.log("🔬 Extracted SMILES from sketcher:", data.smiles);
            return data.smiles;
        }

        console.error("❌ Backend could not convert MOL to SMILES:", data.error);
        return null;

    } catch (err) {
        console.error("❌ Error reading molecule from sketcher:", err);
        return null;
    }
}




async function getParameters() {
    const btn = document.getElementById("get-parameters-button");   // ✅ NEW
    const originalText = btn.innerText;                              // ✅ NEW

    // Update button state
    btn.innerText = "Computing parameters…";                          // ✅ NEW
    btn.disabled = true;                                              // ✅ NEW

    // 🔍 Step 1: Extract SMILES directly from ChemDoodle sketcher
    const smiles = await getSmilesFromSketcher();

    if (!smiles) {
        alert("❌ Could not extract SMILES from PROTAC sketcher. Please make sure the PROTAC is drawn.");

        // 🔁 Restore button state on early exit
        btn.innerText = originalText;                                 // ✅ NEW
        btn.disabled = false;                                         // ✅ NEW
        return;
    }

    console.log("📤 Sending SMILES to backend:", smiles);


    startAsyncLoader({
    title: "Computing molecular parameters…",
    messages: [
        { html: "Extracting SMILES from sketcher…" },
        { html: "Computing physicochemical descriptors…" },
        { html: "Checking Lipinski-style property flags…" },
        { html: "Preparing downloadable files…" }
    ],
    subtle: "Large molecules may take longer to evaluate."
    });

    // document.getElementById("loading-spinner").style.display = "block";
    document.getElementById("pdf-download-container").innerHTML = "";

    try {
        const response = await fetch("/api/admet/run", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ smiles })
        });

        const data = await response.json();

        if (data.success) {
            const files = data.files || {};
            const links = Object.entries(files)
                .filter(([, href]) => href)
                .map(([label, href]) => `<a href="${href}" target="_blank" class="btn btn-success mr-2">${label.toUpperCase()}</a>`)
                .join("");
            document.getElementById("loading-spinner").style.display = "none";
            document.getElementById("pdf-download-container").innerHTML = `
                <div>${links || "Parameter report ready."}</div>
            `;
        } else {
            throw new Error(data.error || "Parameter generation failed.");
        }

    } catch (error) {
        console.error("❌ Error in getParameters():", error);
        if (typeof showAlert === "function") {
            showAlert(`❌ ${error.message || "Parameter generation failed."}`, "error");
        }

    } finally {
        // 🔁 ALWAYS restore button state
        btn.innerText = originalText;                                 // ✅ NEW
        btn.disabled = false;                                         // ✅ NEW
        document.getElementById("loading-spinner").style.display = "none";
    }
}





// ============================================================================
// ✅ PROTAC Wizard Flow (Back + Reset + 3 Start Routes)
// Replace your existing modal-related functions with this block.
// ============================================================================

(() => {
  // --------------------------------------------------------------------------
  // 0) DOM Helpers
  // --------------------------------------------------------------------------
  const $id = (id) => document.getElementById(id);

  function setDisplay(id, show) {
    const el = $id(id);
    if (el) el.style.display = show ? "block" : "none";
  }

  function clearValue(id) {
    const el = $id(id);
    if (el) el.value = "";
  }

  function clearHTML(id) {
    const el = $id(id);
    if (el) el.innerHTML = "";
  }

  function clearText(id) {
    const el = $id(id);
    if (el) el.textContent = "";
  }

  // --------------------------------------------------------------------------
  // 1) Wizard State + Step Stack
  // --------------------------------------------------------------------------
  const Wizard = {
    current: "step-route",
    stack: []
  };

  function updateBackButton() {
    const backBtn = $id("wizard-back");
    if (!backBtn) return;
    backBtn.style.display = Wizard.stack.length ? "inline-block" : "none";
  }

  function hideAllSteps() {
    // NEW step ids (hunter-mode removed)
    const ids = [
      "step-route",
      "step-target",
      "assisted-mode",
      "manual-mode",
      "warhead-section"
    ];
    ids.forEach((id) => setDisplay(id, false));
  }

  function updateRouteScreenHints() {
    // If a warhead was imported already, make route screen guide E3 selection next.
    const hasImportedWarhead =
      (sessionStorage.getItem("warheadSource") === "hunter") &&
      !!sessionStorage.getItem("savedMolecule") &&
      !!sessionStorage.getItem("warheadPdbFile");

    // Target Builder route button (use ID for reliable selection)
    const targetBtn = $id("route-target-btn");
    if (targetBtn) targetBtn.style.display = hasImportedWarhead ? "none" : "";

    // Add/update a note at top of step-route
    const routeBox = $id("step-route");
    if (!routeBox) return;

    let note = $id("route-note");
    if (!note) {
      note = document.createElement("div");
      note.id = "route-note";
      note.style.marginBottom = "10px";
      note.style.opacity = "0.9";
      routeBox.prepend(note);
    }

    if (hasImportedWarhead) {
      note.innerHTML = "✅ Warhead imported. Now choose how to select your E3 ligase:";
    } else {
      note.innerHTML = "";
    }
  }

  function showStep(stepId, pushHistory = true) {
    if (!stepId) return;

    if (pushHistory && Wizard.current && Wizard.current !== stepId) {
      Wizard.stack.push(Wizard.current);
    }

    Wizard.current = stepId;
    hideAllSteps();
    setDisplay(stepId, true);

    if (stepId === "step-route") {
      updateRouteScreenHints();
    }

    updateBackButton();
  }

  // Expose these globally (used by modal header buttons)
  window.wizardBack = function wizardBack() {
    if (!Wizard.stack.length) return;
    const prev = Wizard.stack.pop();
    showStep(prev, false);
  };

  window.wizardReset = function wizardReset(clearSession = true) {
    // Clear wizard history
    Wizard.stack = [];
    Wizard.current = "step-route";

    // Clear UI state
    hideAllSteps();
    setDisplay("step-route", true);
    updateBackButton();

    // Clear status + previews (both target route + hunter route)
    clearHTML("target-status");
    setDisplay("target-preview", false);
    const timg = $id("target-warhead-img"); if (timg) timg.src = "";
    clearText("target-files");

    clearHTML("hunter-status");
    setDisplay("hunter-preview", false);
    const himg = $id("hunter-warhead-img"); if (himg) himg.src = "";
    clearText("hunter-files");

    // Clear form fields
    [
      "targetJobId",
      "hunterJobId",
      "ligasePdb",
      "ligaseLigand",
      "warheadPdb",
      "warheadLigand",
      "manual-ligasePdb",
      "manual-ligaseLigand",
      "manual-warheadPdb",
      "manual-warheadLigand"
    ].forEach(clearValue);

    // Reset selects safely
    const ligaseSelect = $id("ligase-select");
    if (ligaseSelect) ligaseSelect.innerHTML = "<option value=''>Select an E3 Ligase</option>";

    const pdbSelect = $id("ligase-pdb-select");
    if (pdbSelect) pdbSelect.innerHTML = "<option value=''>Select a PDB</option>";

    const recSelect = $id("recruiter-select");
    if (recSelect) recSelect.innerHTML = "<option value=''>Select a Recruiter</option>";

    // Hide assisted sub-rows
    setDisplay("ligase-pdb-row", false);
    setDisplay("or-divider", false);
    setDisplay("recruiter-row", false);
    setDisplay("ligase-final", false);

    // Hide warhead section until ligase confirmed
    setDisplay("warhead-section", false);

    // Clear session keys only if requested
    if (clearSession) {
      clearWizardSession();
    }

    updateRouteScreenHints();
  };

  function revokeIfBlobUrl(key) {
    const v = sessionStorage.getItem(key);
    if (v && typeof v === "string" && v.startsWith("blob:")) {
      try { URL.revokeObjectURL(v); } catch (e) {}
    }
  }

  function clearWizardSession() {
    // Revoke blobs we created
    revokeIfBlobUrl("warheadPdbFile");
    revokeIfBlobUrl("ligasePdbFile");

    // Clear warhead import (your existing logic, slightly expanded)
    clearHunterImport();

    // Clear ligase selections
    sessionStorage.removeItem("selectedLigase");
    sessionStorage.removeItem("ligaseLocalPath");
    sessionStorage.removeItem("ligasePdb");
    sessionStorage.removeItem("ligandHead1");
    sessionStorage.removeItem("ligaseAtom");

    // Clear warhead selections
    sessionStorage.removeItem("warheadPdb");
    sessionStorage.removeItem("ligandHead2");
    sessionStorage.removeItem("warheadAtom");

    // Optional: if you want reset to also clear these outputs
    // sessionStorage.removeItem("generatedSMILES");
    // sessionStorage.removeItem("savedLigase");
    // sessionStorage.removeItem("savedMolecule");

    // Clear globals
    delete window.HUNTER_IMPORT;
    delete window.TARGET_IMPORT;
  }

  // --------------------------------------------------------------------------
  // 2) Route Choosers (3 Start Routes)
  // --------------------------------------------------------------------------
  window.chooseTargetRoute = function chooseTargetRoute() {
    showStep("step-target", true);
  };

  // IMPORTANT: chooseAssistedMode is now wizard-aware and can still populate ligase-select
  window.chooseAssistedMode = async function chooseAssistedMode() {
    showStep("assisted-mode", true);

    // Populate ligase dropdown if ligaseData exists or can be fetched
    await ensureLigaseDataLoaded();

    const ligaseSelect = $id("ligase-select");
    if (!ligaseSelect) return;

    ligaseSelect.innerHTML = "<option value=''>Select an E3 Ligase</option>";
    const keys = Object.keys(window.ligaseData || {});
    if (!keys.length) {
      console.warn("[chooseAssistedMode] ligaseData empty — check /static/data/ligases.json");
    }
    keys.forEach(ligase => {
      ligaseSelect.innerHTML += `<option value="${ligase}">${ligase}</option>`;
    });
  };

  window.chooseManualMode = function chooseManualMode() {
    showStep("manual-mode", true);
  };

  // When assisted ligase confirmed -> warhead section step
  // (This replaces your old "just display warhead-section" behavior with wizard history)
  window.confirmAssistedLigase = function confirmAssistedLigase() {
    showStep("warhead-section", true);
  };

  // --------------------------------------------------------------------------
  // 3) ligaseData loader (safe, idempotent)
  // --------------------------------------------------------------------------
  window.ligaseData = window.ligaseData || {};
  let ligaseDataLoading = null;

  async function ensureLigaseDataLoaded() {
    if (Object.keys(window.ligaseData).length) return;
    if (ligaseDataLoading) return ligaseDataLoading;

    ligaseDataLoading = fetch("/static/data/ligases.json")
      .then(r => r.json())
      .then(json => {
        window.ligaseData = json || {};
      })
      .catch(err => {
        console.error("Failed to load /static/data/ligases.json", err);
        window.ligaseData = {};
      })
      .finally(() => {
        ligaseDataLoading = null;
      });

    return ligaseDataLoading;
  }

  // --------------------------------------------------------------------------
  // 4) Warhead Source State (RCSB vs Hunter/Local)
  // --------------------------------------------------------------------------
  window.setWarheadSource = function setWarheadSource(src) {
    sessionStorage.setItem("warheadSource", src); // "rcsb" | "hunter"
  };

  window.getWarheadSource = function getWarheadSource() {
    return sessionStorage.getItem("warheadSource") || "rcsb";
  };

  window.clearHunterImport = function clearHunterImport() {
    // revoke blob url (warhead)
    const warheadPdbFile = sessionStorage.getItem("warheadPdbFile");
    if (warheadPdbFile && typeof warheadPdbFile === "string" && warheadPdbFile.startsWith("blob:")) {
      try { URL.revokeObjectURL(warheadPdbFile); } catch (e) {}
    }

    sessionStorage.removeItem("warheadPdbFile");
    sessionStorage.removeItem("savedMolecule");
    sessionStorage.removeItem("warheadHunterJobId");
    sessionStorage.removeItem("warheadSource");

    // Clear globals
    delete window.HUNTER_IMPORT;
    delete window.TARGET_IMPORT;
  };

  // --------------------------------------------------------------------------
  // 5) Hunter/Target Import Helpers
  // --------------------------------------------------------------------------
  function _basename(p) {
    return String(p || "").split("/").pop();
  }

  // Extract from filenames like: 8vb5_A_A00_1101.sdf  or  8vb5_A_A00.pdb
  window.parseHunterName = function parseHunterName(pathOrName) {
    const name = _basename(pathOrName);
    const clean = name.replace(/\.(sdf|mol|pdb)$/i, "");
    const parts = clean.split("_");
    return {
      pdb_id: (parts[0] || "").toUpperCase(),
      chain:  (parts[1] || "").toUpperCase(),
      ligand: (parts[2] || "").toUpperCase(),
      resid:  (parts[3] || "").toUpperCase()
    };
  };

  window.normalizeLigandCode = function normalizeLigandCode(code) {
    return String(code || "")
      .trim()
      .toUpperCase()
      .replace(/\.PDB$/i, "")
      .replace(/[^A-Z0-9]/g, "");
  };


  async function _loadJobGeneric({ inputId, statusId, previewId, imgId, filesId, globalStoreKey }) {

    const jobId = (document.getElementById(inputId)?.value || "").trim();
    const status = document.getElementById(statusId);
    const preview = document.getElementById(previewId);

    if (preview) preview.style.display = "none";
    if (status) status.innerHTML = "Loading job…";

    if (!jobId) {
        if (status) status.innerHTML = "❌ Please enter a job id.";
        return;
    }

    try {
        const r = await fetch(`/api/warheadhunter/job/${encodeURIComponent(jobId)}`)
        const text = await r.text();
        let data = {};
        try {
          data = text ? JSON.parse(text) : {};
        } catch (_error) {
          data = {
            ok: false,
            error: "The Target Builder handoff returned a non-JSON response. Check deployed route/domain configuration.",
          };
        }

        if (!r.ok || !data.ok) {
          const guidance = data.guidance ? `<br><small>${data.guidance}</small>` : "";
          const sources = data.sources_checked?.length ? `<br><small>Sources checked: ${data.sources_checked.join(", ")}</small>` : "";
          const hint = data.hint ? `<br><small>${data.hint}</small>` : "";
          if (status) status.innerHTML = `❌ ${data.error || "Failed to load job"}${sources}${hint}${guidance}`;
          return;
        }

        window[globalStoreKey] = data;

        if (status) status.innerHTML = `✅ Loaded job ${data.job_id}`;

        const img = document.getElementById(imgId);
        const filesBox = document.getElementById(filesId);

        const first = data.options?.[0];

        if (!first) {
        if (status) status.innerHTML = "❌ No warhead options found.";
        return;
        }

        if (img && first.svg_plain) {
        img.src = `${data.public_base}/${first.svg_plain}`;
        }

        if (filesBox) {
        filesBox.textContent = JSON.stringify(first, null, 2);
        }

        if (preview) preview.style.display = "block";

    } catch (e) {
        if (status) status.innerHTML = `❌ Network error: ${e}`;
    }
}


  async function _confirmImportGeneric({ globalStoreKey, statusId, afterConfirmStep }) {
    const data = window[globalStoreKey];
    const status = document.getElementById(statusId);

    if (!data) {
      if (status) status.innerHTML = "❌ No loaded job to import.";
      return;
    }

    // Normalize API response: backend returns options[] + public_base; frontend expects detected + warhead
    const first = data.options?.[0];
    if (first && data.public_base && !data.detected) {
      const base = (data.public_base.replace(/\/+$/, "") + "/");
      data.detected = {
        target_pdb: (base + (first.pdb_file || "")).replace(/^\/+/, ""),
        warhead_sdf: (base + (first.sdf || "")).replace(/^\/+/, "")
      };
      data.warhead = {
        pdb_id: (first.pdb || "").toUpperCase(),
        ligand: (first.ligand || "").toUpperCase()
      };
    }

    try {
      if (status) status.innerHTML = "Importing job files…";

      // Infer pdb+ligand from detected warhead_sdf
      const sdfPath = data?.detected?.warhead_sdf || "";
      const parsed = window.parseHunterName(sdfPath);

      const pdbId = (data.warhead?.pdb_id || parsed.pdb_id || "").toUpperCase();
      const lig   = window.normalizeLigandCode(data.warhead?.ligand || parsed.ligand || "");

      // Autofill warhead UI fields (even if warhead-section hidden)
      const warheadPdbEl = document.getElementById("warheadPdb");
      const warheadLigEl = document.getElementById("warheadLigand");
      if (warheadPdbEl && pdbId) warheadPdbEl.value = pdbId;
      if (warheadLigEl && lig)   warheadLigEl.value = lig;

      // Also set sessionStorage used later
      sessionStorage.setItem("warheadPdb", pdbId);
      sessionStorage.setItem("ligandHead2", lig);

      // Build local URLs from static paths
      const pdbRel = data?.detected?.target_pdb || "";
      const sdfRel = data?.detected?.warhead_sdf || "";

      if (!pdbRel) throw new Error("Backend payload missing detected.target_pdb");
      if (!sdfRel) throw new Error("Backend payload missing detected.warhead_sdf");

      const pdbUrl = /^https?:\/\//i.test(pdbRel) ? pdbRel : "/" + pdbRel.replace(/^\/+/, "");
      const sdfUrl = /^https?:\/\//i.test(sdfRel) ? sdfRel : "/" + sdfRel.replace(/^\/+/, "");

      // Fetch local PDB -> store blob URL
      const pdbResp = await fetch(pdbUrl);
      if (!pdbResp.ok) throw new Error(`Failed local PDB download (${pdbResp.status})`);
      const pdbBlob = await pdbResp.blob();

      // Revoke previous blob if exists
      const prev = sessionStorage.getItem("warheadPdbFile");
      if (prev && prev.startsWith("blob:")) {
        try { URL.revokeObjectURL(prev); } catch (e) {}
      }
      sessionStorage.setItem("warheadPdbFile", URL.createObjectURL(pdbBlob));

      // Fetch local SDF -> store text directly (NO conversion)
      const sdfResp = await fetch(sdfUrl);
      if (!sdfResp.ok) throw new Error(`Failed local SDF download (${sdfResp.status})`);
      const sdfText = await sdfResp.text();
      sessionStorage.setItem("savedMolecule", sdfText);

      // Mark source
      sessionStorage.setItem("warheadHunterJobId", data.job_id);
      sessionStorage.setItem("warheadSource", "hunter");

      if (status) status.innerHTML = `✅ Imported job ${data.job_id}. Local PDB/SDF will be used.`;

      // Update route screen hints now that warhead is imported
      updateRouteScreenHints();

      // Go where you want after confirm
      if (afterConfirmStep) showStep(afterConfirmStep, true);

    } catch (e) {
      console.error(e);
      if (status) status.innerHTML = `❌ Import failed: ${e.message || e}`;
    }
  }

  // --------------------------------------------------------------------------
  // 6) Target Route API (uses the same backend as warheadhunter/job/load)
  // --------------------------------------------------------------------------
  window.loadTargetJob = async function loadTargetJob() {
    return _loadJobGeneric({
      inputId: "targetJobId",
      statusId: "target-status",
      previewId: "target-preview",
      imgId: "target-warhead-img",
      filesId: "target-files",
      globalStoreKey: "TARGET_IMPORT"
    });
  };

  window.confirmTargetImport = async function confirmTargetImport() {
    // After confirming target import, send them back to route chooser
    // (now it will hide the Target button and tell them to pick E3 method next)
    return _confirmImportGeneric({
      globalStoreKey: "TARGET_IMPORT",
      statusId: "target-status",
      afterConfirmStep: "step-route"
    });
  };

  // --------------------------------------------------------------------------
  // 7) Warhead Hunter UI inside Warhead section (existing ids)
  // --------------------------------------------------------------------------
  window.loadHunterJob = async function loadHunterJob() {
    return _loadJobGeneric({
      inputId: "hunterJobId",
      statusId: "hunter-status",
      previewId: "hunter-preview",
      imgId: "hunter-warhead-img",
      filesId: "hunter-files",
      globalStoreKey: "HUNTER_IMPORT"
    });
  };

  window.confirmHunterImport = async function confirmHunterImport() {
    // After confirming from warhead-section, remain on warhead-section (user might still edit)
    return _confirmImportGeneric({
      globalStoreKey: "HUNTER_IMPORT",
      statusId: "hunter-status",
      afterConfirmStep: "warhead-section"
    });
  };

  // --------------------------------------------------------------------------
  // 8) Keep your Params + ZIP export functions UNCHANGED
  // (You already pasted them; no changes required here)
  // --------------------------------------------------------------------------

  // --------------------------------------------------------------------------
  // 9) Optional: When modal opens, force wizard to start at route screen
  // --------------------------------------------------------------------------
document.addEventListener("DOMContentLoaded", () => {
  const modalEl = document.getElementById("protacModal");
  if (!modalEl) return;

modalEl.addEventListener("show.bs.modal", () => {
  wizardReset(false); // UI reset only, keep sessionStorage
});

modalEl.addEventListener("hidden.bs.modal", () => {
  wizardReset(false); // UI reset only, keep sessionStorage
});

});


  // Initialize route hints on first load
  document.addEventListener("DOMContentLoaded", () => {
    updateRouteScreenHints();
    updateBackButton();
  });

})();



// =========================================================
// 🧾 Params + ZIP export (unchanged logic, minor safety)
// =========================================================
function generateProtacParams() {
  const ligasePdb   = sessionStorage.getItem("ligasePdb");
  const warheadPdb  = sessionStorage.getItem("warheadPdb");
  const ligaseAtom  = sessionStorage.getItem("ligaseAtom");
  const warheadAtom = sessionStorage.getItem("warheadAtom");

  const ligandHead1 = sessionStorage.getItem("ligandHead1");
  const ligandHead2 = sessionStorage.getItem("ligandHead2");

  if (!ligasePdb || !warheadPdb || !ligaseAtom || !warheadAtom || !ligandHead1 || !ligandHead2) {
    alert("❌ Missing necessary input data.");
    return "";
  }

  return `Structures: ${ligasePdb.toLowerCase()} ${warheadPdb.toLowerCase()}
Chains: A B
Heads: ${ligandHead1}.sdf ${ligandHead2}.sdf
Anchor atoms: ${ligaseAtom} ${warheadAtom}
Protac: JARI.smiles
Full: True
RMSD: 4
cutoff_local: 200
num_rosetta: 50

RosettaDockMemory: 8000
ProtacModelMemory: 6000`;
}

function saveFile(blob, fileName) {
  const link = document.createElement("a");
  link.href = URL.createObjectURL(blob);
  link.download = fileName;
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
}


async function createZipFile(ligaseAtom, warheadAtom, protacParams) {
  const ligaseSDF  = sessionStorage.getItem("savedLigase");
  const warheadSDF = sessionStorage.getItem("savedMolecule");
  const smiles     = sessionStorage.getItem("generatedSMILES");

  if (!ligaseSDF || !warheadSDF || !smiles) {
    throw new Error("Missing Ligase.sdf / Warhead.sdf / SMILES. Make sure you saved ligase + warhead and generated SMILES.");
  }

  if (typeof JSZip === "undefined") {
    throw new Error("JSZip is not loaded on this page.");
  }

  const folder = new JSZip();

  // Add PDBs (blobs)
  const ligasePdbFile  = sessionStorage.getItem("ligasePdbFile");
  const warheadPdbFile = sessionStorage.getItem("warheadPdbFile");

  if (ligasePdbFile) {
    const ligBlob = await (await fetch(ligasePdbFile)).blob();
    folder.file("Ligase.pdb", ligBlob);
  }

  if (warheadPdbFile) {
    const warBlob = await (await fetch(warheadPdbFile)).blob();
    folder.file("Warhead.pdb", warBlob);
  }

  // Add SDF + smiles + params
  folder.file("Warhead.sdf", warheadSDF);
  folder.file("Ligase.sdf", ligaseSDF);
  folder.file("JARI.smiles", smiles);
  folder.file("Protac_params.txt", protacParams);

  // Add PrepFiles.py
  const prepResp = await fetch("/static/python/PrepFiles.py");
  if (!prepResp.ok) {
    throw new Error(`PrepFiles.py fetch failed (${prepResp.status}). Check /static/python/PrepFiles.py path.`);
  }
  folder.file("PrepFiles.py", await prepResp.text());

  // Generate ZIP blob
  const zipBlob = await folder.generateAsync({ type: "blob" });

  // Trigger download (use your helper)
  saveFile(zipBlob, "JARIpcs.zip");
}



// =========================================================
// 🔧 Disable ChemDoodle cloud requests (safety)
// =========================================================
function disableChemDoodleCloud() {
    if (window.ChemDoodle && ChemDoodle.feature && ChemDoodle.feature.uil) {
        ChemDoodle.feature.uil.loadRemote = false;
        console.log("🔧 ChemDoodle cloud rendering disabled.");
    } else {
        setTimeout(disableChemDoodleCloud, 50);
    }
}
disableChemDoodleCloud();

// =========================================================
// 💡 Utility: Extract ?param=value from URL
// =========================================================
function getParam(k) {
    return new URLSearchParams(window.location.search).get(k);
}


// =========================================================
// 🟢 Wait until ChemDoodle editors are ready
// =========================================================
function waitForEditorsReady(callback) {
    if (
        window.ChemDoodleEditorsReady === true &&
        window.ligaseSketcher &&
        typeof window.ligaseSketcher.loadMolecule === "function"
    ) {
        console.log("🟢 Editors ready — loading recruiter now.");
        callback();
    } else {
        setTimeout(() => waitForEditorsReady(callback), 50);
    }
}

// =========================================================
// 🔬 Parse SDF → extract first MOL block
// =========================================================
function parseSDFtoMol(sdfText) {
    if (!sdfText || typeof sdfText !== "string") {
        console.error("parseSDFtoMol received invalid SDF text.");
        return null;
    }

    const firstMol = sdfText.split("$$$$")[0].trim();
    return ChemDoodle.readMOL(firstMol);
}




// =========================================================
// 🔄 Fetch recruiter MOL block and load into ligase editor
// =========================================================
function loadRecruiterMolecule(recruiterName) {
    console.log("🔍 Fetching recruiter:", recruiterName);

    fetch(`/api/recruiter/${recruiterName}`)
        .then(res => res.json())
        .then(data => {
            if (data.error) {
                console.error("❌ Backend error:", data.error);
                return;
            }

            if (!data.mol_block) {
                console.error("❌ Backend returned no MOL block:", data);
                return;
            }

            waitForEditorsReady(() => {
                try {
                    console.log("📦 Received MOL block, loading into ChemDoodle...");

                    const mol = ChemDoodle.readMOL(data.mol_block);

                    if (!mol) {
                        console.error("❌ ChemDoodle failed to parse MOL block.");
                        return;
                    }

                    ligaseSketcher.clear();
                    ligaseSketcher.loadMolecule(mol);
                    ligaseSketcher.repaint();

                    console.log("✅ Recruiter loaded into ligase editor (MOL mode).");

                } catch (err) {
                    console.error("❌ Exception while loading recruiter molecule:", err);
                }
            });
        })
        .catch(err => {
            console.error("⚠ Error fetching recruiter:", err);
        });
}


// =========================================================
// 🚀 Auto-load recruiter from URL (?recruiter=CRBN_EF2)
// =========================================================
document.addEventListener("DOMContentLoaded", () => {
    const recruiter = getParam("recruiter");
    if (!recruiter) return;

    console.log("🔎 Auto-loading recruiter from URL:", recruiter);
    loadRecruiterMolecule(recruiter);
});

// =========================================================
// 🧬 Auto-load converted ligase from ?session=UUID
// =========================================================
document.addEventListener("DOMContentLoaded", () => {
    const sessionID = String(window.convertedSession || "").trim();

    if (!sessionID || ["none", "null", "undefined"].includes(sessionID.toLowerCase())) {
        console.log("ℹ️ No session ID, skipping converted ligase loader.");
        return;
    }

    console.log("🧪 Found session ID:", sessionID);

    // Wait until ligaseSketcher exists
    function waitForSketcher() {
        if (!window.ligaseSketcher) {
            console.log("⏳ Waiting for ligaseSketcher...");
            setTimeout(waitForSketcher, 200);
            return;
        }

        console.log("📡 Fetching converted SDF:", sessionID);

        fetch(`/api/recruiter/converted/${sessionID}`)
            .then(res => res.json())
            .then(data => {
                if (data.error) {
                    console.error("❌ Backend error:", data.error);
                    return;
                }

                if (!data.mol_block) {
                    console.error("❌ No mol block returned:", data);
                    return;
                }

                console.log("📦 Loading converted ligase MOL block...");
                const mol = ChemDoodle.readMOL(data.mol_block);

                ligaseSketcher.clear();
                ligaseSketcher.loadMolecule(mol);
                ligaseSketcher.repaint();

                console.log("✅ Converted ligase successfully loaded!");
            })
            .catch(err => console.error("⚠ Error loading converted ligase:", err));
    }

    waitForSketcher();
});

document.addEventListener("DOMContentLoaded", () => {
    
    // === LIGASE GUIDE BUTTON (🔍 ICON) ===
    const infoBtn = document.getElementById("ligase-info-btn");
    if (infoBtn) {
        infoBtn.addEventListener("click", () => {
            console.log("📖 Opening Ligase Ligandalyzer...");
            window.open("/ligase-ligandalyzer", "_blank");
        });
    } else {
        console.error("❌ ligase-info-btn not found!");
    }

});








document.querySelectorAll('.dockq-premium').forEach(el => {
    el.addEventListener('mousemove', (e) => {
        const box = el.querySelector('.dockq-premium-box');
        if (!box) return;

        const rect = el.getBoundingClientRect();
        const offsetX = (e.clientX - rect.left - rect.width / 2) * 0.03;

        box.style.transform = `translateX(calc(-50% + ${offsetX}px)) translateY(4px) scale(1)`;
    });

    el.addEventListener('mouseleave', () => {
        const box = el.querySelector('.dockq-premium-box');
        if (!box) return;

        box.style.transform = "translateX(-50%) translateY(4px) scale(1)";
    });
});

function disableRecruiterDropdown() {
    const rec = document.getElementById("recruiter-select");
    rec.value = "";
    rec.disabled = true;
    rec.classList.add("disabled-select");
}

function disablePdbDropdown() {
    const pdb = document.getElementById("ligase-pdb-select");
    pdb.value = "";
    pdb.disabled = true;
    pdb.classList.add("disabled-select");
}

function enableBothDropdowns() {
    document.getElementById("ligase-pdb-select").disabled = false;
    document.getElementById("recruiter-select").disabled = false;

    document.getElementById("ligase-pdb-select").classList.remove("disabled-select");
    document.getElementById("recruiter-select").classList.remove("disabled-select");
}








function generateFiles() {
    // All this does now is open your new modal
    $('#protacModal').modal('show');
}



let ligaseData = {};
fetch("/static/data/ligases.json")
    .then(r => r.json())
    .then(json => ligaseData = json);

function openProtacModal() {
    $('#protacModal').modal('show');
}



// --------------------------------------------------------------------------
// ✅ Assisted Mode (unified) — uses window.ligaseData from the wizard loader
// --------------------------------------------------------------------------

// Make sure these exist (wizard already defines ensureLigaseDataLoaded + showStep)
window.onLigaseSelected = async function onLigaseSelected() {
  const ligaseSelect = document.getElementById("ligase-select");
  const ligase = (ligaseSelect?.value || "").trim();
  sessionStorage.setItem("selectedLigase", ligase);
  if (window.recruiterMapPromise) await window.recruiterMapPromise;


  const pdbRow     = document.getElementById("ligase-pdb-row");
  const pdbSelect  = document.getElementById("ligase-pdb-select");
  const orDivider  = document.getElementById("or-divider");
  const recruiterRow = document.getElementById("recruiter-row");
  const recSelect  = document.getElementById("recruiter-select");

  if (!pdbSelect || !recSelect) {
    console.warn("[onLigaseSelected] Missing selects", { pdbSelect: !!pdbSelect, recSelect: !!recSelect });
    return;
  }

  // Reset dropdowns
  pdbSelect.disabled = false;
  recSelect.disabled = false;
  pdbSelect.classList.remove("disabled-select");
  recSelect.classList.remove("disabled-select");

  pdbSelect.innerHTML = "<option value=''>Select a PDB</option>";
  recSelect.innerHTML = "<option value=''>Select a Recruiter</option>";

  // Hide final row until a PDB is chosen
  const finalRow = document.getElementById("ligase-final");
  if (finalRow) finalRow.style.display = "none";

  // Populate PDB list from window.ligaseData (wizard’s canonical source)
  const data = window.ligaseData || {};
  const list = data[ligase] || [];

  list.forEach(file => {
    if (String(file).endsWith(".pdb")) {
      pdbSelect.innerHTML += `<option value="${file}">${file}</option>`;
    }
  });

  if (pdbRow) pdbRow.style.display = "block";

  // Recruiter dropdown (optional, only if recruiterMap exists)
  if (typeof window.recruiterMap !== "undefined" && window.recruiterMap && ligase) {
    // Clear any previous options beyond placeholder
    recSelect.innerHTML = "<option value=''>Select a Recruiter</option>";

    for (const [code, entry] of Object.entries(window.recruiterMap)) {
      if (entry.ligase === ligase) {
        const opt = document.createElement("option");
        opt.value = code;
        opt.textContent = `${code} (${entry.pdb_id} – ${entry.ligand})`;
        recSelect.appendChild(opt);
      }
    }

    if (orDivider) orDivider.style.display = "block";
    if (recruiterRow) recruiterRow.style.display = "block";
  } else {
    if (orDivider) orDivider.style.display = "none";
    if (recruiterRow) recruiterRow.style.display = "none";
  }

  console.log("Ligase selected:", ligase);
};


window.onLigasePdbChosen = function onLigasePdbChosen() {
  const pdbFile = document.getElementById("ligase-pdb-select")?.value || "";
  const ligase  = sessionStorage.getItem("selectedLigase") || "";

  if (!pdbFile || !ligase) return;

  // ✅ If you have LIGANDALYZER_BASE defined globally, keep this:
  // fullPath like `${LIGANDALYZER_BASE}${ligase}/PDB/${pdbFile}`;
  // Guard for missing constant
  if (typeof window.LIGANDALYZER_BASE !== "undefined") {
    const fullPath = `${window.LIGANDALYZER_BASE}${ligase}/PDB/${pdbFile}`;
    sessionStorage.setItem("ligaseLocalPath", fullPath);
  } else {
    console.warn("[onLigasePdbChosen] LIGANDALYZER_BASE undefined. Will use RCSB for ligase PDB fetch.");
    sessionStorage.removeItem("ligaseLocalPath");
  }

  // Parse: "4CI3_Y70.pdb" -> ligasePdb="4CI3", ligaseLigand="Y70"
  const parts = pdbFile.split("_");
  const ligasePdb    = (parts[0] || "").toUpperCase();
  const ligaseLigand = normalizeLigandCode((parts[1] || "").replace(/\.pdb$/i, ""));

  // Autofill fields
  const ligasePdbEl = document.getElementById("ligasePdb");
  const ligaseLigEl = document.getElementById("ligaseLigand");
  if (ligasePdbEl) ligasePdbEl.value = ligasePdb;
  if (ligaseLigEl) ligaseLigEl.value = ligaseLigand;

  // Show final row
  const finalRow = document.getElementById("ligase-final");
  if (finalRow) finalRow.style.display = "block";

  // Optional: visually disable recruiter select once PDB chosen
  const recSelect = document.getElementById("recruiter-select");
  if (recSelect) {
    recSelect.disabled = true;
    recSelect.classList.add("disabled-select");
  }
};









function confirmAssistedLigase() {
  const warheadSection = document.getElementById("warhead-section");
  if (warheadSection) warheadSection.style.display = "block";

  // ✅ If a warhead is already saved, reflect it in UI and do NOT reprompt
  if (hasSavedWarhead()) {
    hydrateWarheadUIFromSession();   // optional but recommended (below)
    unlockNextStepAfterWarhead();    // whatever you do when warhead is "done"
    return;
  }

  // Otherwise, proceed with normal “choose a warhead” behavior
  showWarheadPickerUI?.();
}

// Manual mode remains exactly as your old workflow.



window.finalizeProtac = function finalizeProtac() {
  const ligasePdbEl  = document.getElementById("ligasePdb");
  const ligaseLigEl  = document.getElementById("ligaseLigand");
  const warheadPdbEl = document.getElementById("warheadPdb");
  const warheadLigEl = document.getElementById("warheadLigand");

  // UI values
  const ligasePdbUI     = (ligasePdbEl?.value || "").trim().toUpperCase();
  const ligaseLigandUI  = normalizeLigandCode(ligaseLigEl?.value || "");
  const warheadPdbUI    = (warheadPdbEl?.value || "").trim().toUpperCase();
  const warheadLigandUI = normalizeLigandCode(warheadLigEl?.value || "");

  // Session fallbacks (from target/hunter import)
  const warheadPdbSS    = (sessionStorage.getItem("warheadPdb") || "").toUpperCase();
  const warheadLigSS    = normalizeLigandCode(sessionStorage.getItem("ligandHead2") || "");

  // Final chosen values
  const ligasePdb     = ligasePdbUI;
  const ligaseLigand  = ligaseLigandUI;
  const warheadPdb    = warheadPdbUI || warheadPdbSS;
  const warheadLigand = warheadLigandUI || warheadLigSS;

  // ✅ Guard only what truly matters
  if (!ligasePdb || !ligaseLigand) {
    console.warn("[finalizeProtac] missing ligase:", { ligasePdb, ligaseLigand });
    alert("❌ Please confirm your ligase (PDB + ligand code).");
    return;
  }

  if (!warheadPdb || !warheadLigand) {
    console.warn("[finalizeProtac] missing warhead:", { warheadPdb, warheadLigand, warheadPdbUI, warheadPdbSS });
    alert("❌ Please confirm your warhead (PDB + ligand code) or import from Target Builder.");
    return;
  }

  // Persist selections
  sessionStorage.setItem("ligasePdb", ligasePdb);
  sessionStorage.setItem("ligandHead1", ligaseLigand);
  sessionStorage.setItem("warheadPdb", warheadPdb);
  sessionStorage.setItem("ligandHead2", warheadLigand);

  // TODO: real atom picking later
  sessionStorage.setItem("ligaseAtom", sessionStorage.getItem("ligaseAtom") || "1");
  sessionStorage.setItem("warheadAtom", sessionStorage.getItem("warheadAtom") || "1");

  // Determine warhead source
  const warheadSource  = sessionStorage.getItem("warheadSource") || "rcsb";
  const warheadPdbFile = sessionStorage.getItem("warheadPdbFile"); // blob URL if hunter/target import confirmed
  const warheadSDF     = sessionStorage.getItem("savedMolecule");  // SDF text if hunter import confirmed

  // If hunter source, ensure we actually have the SDF
  if (warheadSource === "hunter" && !warheadSDF) {
    alert("❌ Warhead import is set to local, but no SDF is stored. Re-confirm the Target/Hunter import.");
    return;
  }

  const ligaseLocalPath = sessionStorage.getItem("ligaseLocalPath");

  // Fetch ligase PDB (Ligandalyzer local preferred, else RCSB)
  const ligasePromise = ligaseLocalPath
    ? fetch(ligaseLocalPath).then(r => {
        if (!r.ok) throw new Error(`Ligase local fetch failed (${r.status})`);
        return r.blob();
      })
    : fetch(`https://files.rcsb.org/download/${ligasePdb}.pdb`).then(r => {
        if (!r.ok) throw new Error(`Ligase RCSB fetch failed (${r.status})`);
        return r.blob();
      });

  // Fetch warhead PDB (hunter uses blob already stored, else RCSB)
  const warheadPromise =
    (warheadSource === "hunter" && warheadPdbFile)
      ? fetch(warheadPdbFile).then(r => {
          if (!r.ok) throw new Error(`Warhead blob fetch failed (${r.status})`);
          return r.blob();
        })
      : fetch(`https://files.rcsb.org/download/${warheadPdb}.pdb`).then(r => {
          if (!r.ok) throw new Error(`Warhead RCSB fetch failed (${r.status})`);
          return r.blob();
        });

  Promise.all([ligasePromise, warheadPromise])
    .then(([ligaseBlob, warheadBlob]) => {
      // Revoke old blobs first
      const prevLig = sessionStorage.getItem("ligasePdbFile");
      if (prevLig && prevLig.startsWith("blob:")) try { URL.revokeObjectURL(prevLig); } catch (e) {}

      const prevWar = sessionStorage.getItem("warheadPdbFile");
      if (prevWar && prevWar.startsWith("blob:")) { try { URL.revokeObjectURL(prevWar); } catch (e) {} }


      sessionStorage.setItem("ligasePdbFile", URL.createObjectURL(ligaseBlob));
      sessionStorage.setItem("warheadPdbFile", URL.createObjectURL(warheadBlob));

      const protacParams = generateProtacParams();
      if (!protacParams) return; // generateProtacParams already alerted

      createZipFile("1", "1", protacParams);

      // Close modal
      try { $('#protacModal').modal('hide'); } catch (e) {}

      alert("✅ PROTAC package generated!");
    })
    .catch(err => {
      console.error(err);
      alert("❌ Error fetching PDB data: " + (err?.message || err));
    });
};





// ✅ Manual mode finalize — supports:
// - Full manual (ligase+warhead typed)
// - Target/Hunter import first (warhead comes from sessionStorage)
// - warheadSource === "hunter" uses local blob PDB when available
async function finalizeManualProtac() {
  const ligasePdbUI     = (document.getElementById("manual-ligasePdb")?.value || "").trim().toUpperCase();
  const ligaseLigandUI  = normalizeLigandCode(document.getElementById("manual-ligaseLigand")?.value || "");

  const warheadPdbUI    = (document.getElementById("manual-warheadPdb")?.value || "").trim().toUpperCase();
  const warheadLigandUI = normalizeLigandCode(document.getElementById("manual-warheadLigand")?.value || "");

  const warheadPdbSS    = (sessionStorage.getItem("warheadPdb") || "").trim().toUpperCase();
  const warheadLigandSS = normalizeLigandCode(sessionStorage.getItem("ligandHead2") || "");

  const ligasePdb     = ligasePdbUI;
  const ligaseLigand  = ligaseLigandUI;
  const warheadPdb    = warheadPdbUI || warheadPdbSS;
  const warheadLigand = warheadLigandUI || warheadLigandSS;

  if (!ligasePdb || !ligaseLigand) {
    alert("❌ Please fill ligase PDB + ligase ligand code.");
    return;
  }
  if (!warheadPdb || !warheadLigand) {
    alert("❌ Please fill warhead PDB + warhead ligand code (or import warhead first).");
    return;
  }

  // Store params keys
  sessionStorage.setItem("ligasePdb", ligasePdb);
  sessionStorage.setItem("ligandHead1", ligaseLigand);
  sessionStorage.setItem("warheadPdb", warheadPdb);
  sessionStorage.setItem("ligandHead2", warheadLigand);

  // TODO: real atom picking later
  sessionStorage.setItem("ligaseAtom", sessionStorage.getItem("ligaseAtom") || "1");
  sessionStorage.setItem("warheadAtom", sessionStorage.getItem("warheadAtom") || "1");

  // Fetch/refresh PDB blobs
  const warheadSource  = sessionStorage.getItem("warheadSource") || "rcsb";
  const warheadPdbFile = sessionStorage.getItem("warheadPdbFile");

  const ligaseBlob = await (await fetch(`https://files.rcsb.org/download/${ligasePdb}.pdb`)).blob();

  const warheadBlob =
    (warheadSource === "hunter" && warheadPdbFile)
      ? await (await fetch(warheadPdbFile)).blob()
      : await (await fetch(`https://files.rcsb.org/download/${warheadPdb}.pdb`)).blob();

  // Store blob URLs (cleanup old)
  const prevLig = sessionStorage.getItem("ligasePdbFile");
  if (prevLig && prevLig.startsWith("blob:")) try { URL.revokeObjectURL(prevLig); } catch {}
  const prevWar = sessionStorage.getItem("warheadPdbFile");
  if (prevWar && prevWar.startsWith("blob:")) try { URL.revokeObjectURL(prevWar); } catch {}

  sessionStorage.setItem("ligasePdbFile", URL.createObjectURL(ligaseBlob));
  sessionStorage.setItem("warheadPdbFile", URL.createObjectURL(warheadBlob));

  const protacParams = generateProtacParams();
  if (!protacParams) return;

  try {
    await createZipFile("1", "1", protacParams);
    try { $('#protacModal').modal('hide'); } catch {}
    alert("✅ ZIP downloaded: JARIpcs.zip");
  } catch (e) {
    console.error(e);
    alert("❌ ZIP generation failed: " + (e?.message || e));
  }
}




function validatePdbInput(input) {
    // must be exactly 4 characters, letters/numbers
    const regex = /^[A-Za-z0-9]{4}$/;

    if (regex.test(input.value.trim())) {
        input.classList.remove("invalid");
        input.classList.add("valid");
    } else {
        input.classList.remove("valid");
        input.classList.add("invalid");
    }
}

function validateLigandInput(input) {
    // Accept the ligand code formats currently used by upstream sources.
    const regex = /^(?:[A-Z0-9]{3}|[A-Z0-9]{5})$/;

    if (regex.test(input.value.trim())) {
        input.classList.remove("invalid");
        input.classList.add("valid");
    } else {
        input.classList.remove("valid");
        input.classList.add("invalid");
    }
}



// ✅ Put recruiter map on window so onLigaseSelected can see it
window.recruiterMap = {};

window.recruiterMapPromise = fetch("/static/data/recruiter_pdb_map.json")
  .then(r => r.json())
  .then(data => {
    window.recruiterMap = data;
    console.log("Recruiter map loaded", window.recruiterMap);
    return data;
  })
  .catch(err => {
    console.error("❌ recruiter_pdb_map.json failed to load", err);
    window.recruiterMap = {};
    return {};
  });





function onRecruiterSelected() {
    const code = document.getElementById("recruiter-select").value;
    const pdbSelect = document.getElementById("ligase-pdb-select");
    const recruiterSelect = document.getElementById("recruiter-select");

    if (!code) return;

    const info = recruiterMap[code];
    if (!info) return;

    // ------------------------------
    //  LOCK PDB SELECT + Glow flash
    // ------------------------------
    pdbSelect.classList.add("disabled-select", "glow-flash");
    setTimeout(() => pdbSelect.classList.remove("glow-flash"), 700);

    // ------------------------------
    //  Auto-fill PDB & Ligand
    // ------------------------------
    document.getElementById("ligasePdb").value = info.pdb_id;
    document.getElementById("ligaseLigand").value = info.ligand;

    // If recruiter has a PDB filename, pre-select it
    if (info.pdb_file) {
        pdbSelect.value = info.pdb_file;
    }

    // ------------------------------
    //  Build full local path
    // ------------------------------
    const ligase = sessionStorage.getItem("selectedLigase");
    const fullPath = `${LIGANDALYZER_BASE}${ligase}/PDB/${info.pdb_file}`;
    sessionStorage.setItem("ligaseLocalPath", fullPath);

    // ------------------------------
    //  SHOW NEXT SECTION
    // ------------------------------
    const finalRow = document.getElementById("ligase-final");
    finalRow.style.display = "block";
    finalRow.classList.add("fade-in");
    setTimeout(() => finalRow.classList.remove("fade-in"), 600);

    console.log("Recruiter chosen:", code, info);
}


window.buildProssetacMailto = function buildProssetacMailto() {
  const to = "jxs794@miami.edu"; // <-- change to your address
  const subject = encodeURIComponent("PROTAC Builder help");
  const body = encodeURIComponent(
    `Hi Joseph-Michael,

I'm seeing an issue in PROTAC Builder.

URL: ${location.href}

Thanks!`
  );
  return `mailto:${to}?subject=${subject}&body=${body}`;
};


// ===============================
// 🌐 Universal Async Loader
// ===============================
let asyncMsgTimer = null;
let asyncMsgIndex = 0;

// Default rotating messages (can be overridden per task)
const defaultAsyncMessages = [
  { html: "Crunching molecular descriptors…" },
  { html: "Evaluating ADMET properties…" },
  { html: "Generating analysis report…" },
  {
    html: `Need help?<br>
           <a class="pv-mini-btn" href="${buildProssetacMailto()}">
             Email Joseph-Michael
           </a>`
  }
];

function startAsyncLoader({
  title = "Working…",
  messages = defaultAsyncMessages,
  subtle = "This may take a moment. Please don’t close the page."
} = {}) {

  asyncMsgIndex = 0;

  $("#async-loading-title").text(title);
  $("#async-loading-message").html(messages[0].html);
  $("#async-loading-subtle").text(subtle);

  $("#async-loading").removeClass("d-none");

  clearInterval(asyncMsgTimer);
  asyncMsgTimer = setInterval(() => {
    asyncMsgIndex = (asyncMsgIndex + 1) % messages.length;
    $("#async-loading-message").fadeOut(150, function () {
      $(this).html(messages[asyncMsgIndex].html).fadeIn(150);
    });
  }, 5000);
}

function stopAsyncLoader() {
  clearInterval(asyncMsgTimer);
  asyncMsgTimer = null;

  $("#async-loading").addClass("d-none");
  $("#async-loading-message").empty();
}




// =========================================================
// 🧬 NEW URL LOADER: ?lig_smi= (SMILES or ligand code)
// =========================================================
(function () {
  // decode safely (handles % encoding + '+' spaces)
  function decodeParam(x) {
    try { return decodeURIComponent(String(x || "").replace(/\+/g, "%20")); }
    catch { return String(x || ""); }
  }

  // Common ligand code shapes used by upstream tools.
  function isLigandCode(x) {
    return /^[A-Za-z0-9]{3}$|^[A-Za-z0-9]{5}$/.test(String(x || "").trim());
  }

  // wait until ChemDoodle editors exist + sketcher is ready
  function waitForChemDoodleReady(cb) {
    const ok =
      (window.chemDoodleInitialized === true || window.ChemDoodleEditorsReady === true) &&
      window.sketcher &&
      typeof window.sketcher.loadMolecule === "function" &&
      typeof ChemDoodle !== "undefined";

    if (ok) return cb();
    setTimeout(() => waitForChemDoodleReady(cb), 50);
  }

  // main loader: accepts SMILES or code
  function loadWarheadFromLigSmi(rawVal) {
    const val = decodeParam(rawVal).trim();
    if (!val) return;

    console.log("🧬 lig_smi detected:", val);
    $("#ligand-container").show();

    // Guard: only run once per page load
    if (window.__LIG_SMI_LOADED) return;
    window.__LIG_SMI_LOADED = true;

    if (isLigandCode(val)) {
      console.log("✅ lig_smi treated as ligand code → get_ligand_data:", val);
      loadLigandFromCode(val);          // uses /api/ligand/data
    } else {
      console.log("✅ lig_smi treated as SMILES → convert_smiles_to_mol");
      loadWarheadIntoEditor(val);       // uses /api/molecule/smiles-to-mol
    }
  }

  // listener
  document.addEventListener("DOMContentLoaded", () => {
    const ligSmi = new URLSearchParams(window.location.search).get("lig_smi");
    if (!ligSmi) return;

    waitForChemDoodleReady(() => loadWarheadFromLigSmi(ligSmi));
  });
})();




function useWarheadCodes() {
  const pdb = (document.getElementById("warheadPdb")?.value || "").trim().toUpperCase();
  const lig = (document.getElementById("warheadLigand")?.value || "").trim().toUpperCase();
  const status = document.getElementById("warhead-code-status");
  const ligandCodePattern = /^(?:[0-9A-Z]{3}|[0-9A-Z]{5})$/;

  // Basic validation
  if (!/^[0-9A-Z]{4}$/.test(pdb)) {
    if (status) status.textContent = "❌ Warhead PDB must be 4 characters (e.g., 3EKY).";
    return;
  }
  if (!ligandCodePattern.test(lig)) {
    if (status) status.textContent = "❌ Ligand code must be 3 or 5 characters (e.g., DR7 or A1A00).";
    return;
  }

  // If user is using codes, we must NOT use stale local job files
  sessionStorage.removeItem("warheadPdbFile");
  sessionStorage.removeItem("savedMolecule");
  sessionStorage.setItem("warheadSource", "rcsb");
  sessionStorage.setItem("warheadPdb", pdb);
  sessionStorage.setItem("warheadLigand", lig);

  if (status) status.textContent = `✅ Using RCSB download: ${pdb} / ${lig}`;
}



function wizardGo(stepId) {
  if (WizardState.current && WizardState.current !== stepId) {
    WizardState.stack.push(WizardState.current);
  }
  showStep(stepId);
}

function wizardBack() {
  const prev = WizardState.stack.pop();
  if (prev) showStep(prev);
}

function updateBackButton() {
  const backBtn = document.getElementById("wizard-back");
  if (!backBtn) return;
  backBtn.style.display = WizardState.stack.length ? "" : "none";
}


function hasSavedWarhead() {
  return Boolean(
    sessionStorage.getItem("savedMolecule") ||       // Warhead.sdf/molblock (Hunter import)
    sessionStorage.getItem("warheadPdbFile") ||      // blob url (Hunter or fetched)
    sessionStorage.getItem("warheadPdb")             // manual / RCSB path
  );
}



function hydrateWarheadUIFromSession() {
  const pdb    = (sessionStorage.getItem("warheadPdb") || "").toUpperCase();
  const lig    = (sessionStorage.getItem("ligandHead2") || "").toUpperCase();
  const source = sessionStorage.getItem("warheadSource") || "";

  const status = document.getElementById("warhead-status"); // add a small div in HTML
  if (status) {
    status.textContent = pdb || lig
      ? `✅ Warhead loaded ${source ? `(${source})` : ""}: ${pdb} ${lig}`.trim()
      : "✅ Warhead loaded.";
  }

  // If you have a “Change warhead” button, relabel it instead of prompting
  const changeBtn = document.getElementById("change-warhead-btn");
  if (changeBtn) changeBtn.style.display = "inline-block";
}

function clearLigaseOnly() {
  // clear ligase-side keys only
  sessionStorage.removeItem("selectedLigase");
  sessionStorage.removeItem("ligaseLocalPath");
  sessionStorage.removeItem("ligasePdb");
  sessionStorage.removeItem("ligandHead1");
  sessionStorage.removeItem("ligasePdbFile");
}

 



// ============================================================================
// 🧬 PROTAC BUILDER BOOTSTRAP + URL/HASH HANDOFF LOADER
// Restores old ?lig_smi= behavior while also supporting:
//   ?smiles=
//   ?warhead_smiles=
//   ?warheadSmiles=
//   #lig_smi=
//   #smiles=
//   sessionStorage/localStorage fallback
// ============================================================================

(function PROTACBuilderHandoffSystem() {
    "use strict";

    // ------------------------------------------------------------------------
    // 0) Small helpers
    // ------------------------------------------------------------------------
    function safeDecode(value) {
        if (value == null) return "";
        try {
            return decodeURIComponent(String(value).replace(/\+/g, "%20")).trim();
        } catch {
            return String(value).trim();
        }
    }

    function isLikelyLigandCode(value) {
        return /^[A-Za-z0-9]{3}$|^[A-Za-z0-9]{5}$/.test(String(value || "").trim());
    }

    function isProbablySmiles(value) {
        const v = String(value || "").trim();

        if (!v) return false;
        if (isLikelyLigandCode(v)) return false;

        // Loose SMILES detector.
        // Avoid being too strict because your ligands include stereochemistry,
        // aromatic atoms, brackets, charges, etc.
        return /[=#@+\-\[\]\(\)\\/]|[cnospCNOSP]/.test(v) && v.length > 3;
    }

    function getHashParams() {
        const rawHash = window.location.hash || "";
        const cleaned = rawHash.startsWith("#") ? rawHash.slice(1) : rawHash;

        // Supports:
        // #lig_smi=...
        // #smiles=...
        // #lig_smi=...&other=...
        return new URLSearchParams(cleaned);
    }

    function getAllIncomingParams() {
        const query = new URLSearchParams(window.location.search || "");
        const hash = getHashParams();

        const resolved = {
            href: window.location.href,
            pathname: window.location.pathname,
            search: window.location.search,
            hash: window.location.hash,

            // Warhead / ligand inputs
            lig_smi:
                query.get("lig_smi") ||
                hash.get("lig_smi") ||
                query.get("ligand_smiles") ||
                hash.get("ligand_smiles"),

            smiles:
                query.get("smiles") ||
                hash.get("smiles") ||
                query.get("warhead_smiles") ||
                hash.get("warhead_smiles") ||
                query.get("warheadSmiles") ||
                hash.get("warheadSmiles"),

            ligand:
                query.get("ligand") ||
                hash.get("ligand"),

            // Optional other pieces
            linker:
                query.get("linker") ||
                hash.get("linker"),

            ligase:
                query.get("ligase") ||
                hash.get("ligase"),

            recruiter:
                query.get("recruiter") ||
                hash.get("recruiter"),

            session:
                query.get("session") ||
                hash.get("session")
        };

        // Storage fallback:
        // This helps only when handoff happens on the same domain,
        // but it does not hurt cross-domain usage.
        const stored =
            sessionStorage.getItem("incomingWarheadSmiles") ||
            localStorage.getItem("incomingWarheadSmiles") ||
            "";

        resolved.storageSmiles = stored;

        resolved.warheadValue =
            resolved.lig_smi ||
            resolved.smiles ||
            resolved.ligand ||
            stored ||
            "";

        console.log("🌐 PROTAC Builder handoff debug:", resolved);

        return resolved;
    }

    function waitForChemDoodleReady(callback, tries = 0) {
        const ok =
            (window.chemDoodleInitialized === true || window.ChemDoodleEditorsReady === true || chemDoodleInitialized === true) &&
            window.sketcher &&
            window.linkerSketcher &&
            window.ligaseSketcher &&
            typeof window.sketcher.loadMolecule === "function" &&
            typeof ChemDoodle !== "undefined";

        if (ok) {
            callback();
            return;
        }

        if (tries > 150) {
            console.error("❌ Timed out waiting for ChemDoodle editors.");
            return;
        }

        setTimeout(() => waitForChemDoodleReady(callback, tries + 1), 100);
    }

    function setInputValue(id, value) {
        const el = document.getElementById(id);
        if (el) el.value = value;
    }

    function openSmilesPanel(panelId) {
        const panel = document.getElementById(panelId);
        if (panel) panel.classList.add("open");

        const button = document.querySelector(`[onclick*="${panelId}"]`);
        if (button) {
            button.classList.add("active");
            button.textContent = "Hide SMILES";
        }
    }

    function clearWarheadStateForIncomingHandoff() {
        // Clear only warhead/generated output state.
        // Do NOT clear saved linker/ligase because user may already have selected them.
        sessionStorage.removeItem("modifiedLigand");
        sessionStorage.removeItem("savedMolecule");
        sessionStorage.removeItem("combinedMOL");
        sessionStorage.removeItem("generatedSMILES");

        sessionStorage.removeItem("warheadPdbFile");
        sessionStorage.removeItem("warheadPdb");
        sessionStorage.removeItem("warheadLigand");
        sessionStorage.removeItem("ligandHead2");

        if (window.saveClicks && Object.prototype.hasOwnProperty.call(window.saveClicks, "warhead")) {
            window.saveClicks.warhead = false;
        } else if (typeof saveClicks !== "undefined" && saveClicks.warhead !== undefined) {
            saveClicks.warhead = false;
        }

        const warheadDropdown = document.getElementById("warhead");
        if (warheadDropdown) warheadDropdown.value = "";
    }

    // ------------------------------------------------------------------------
    // 1) Canonical SMILES loader used by manual buttons and URL handoff
    // ------------------------------------------------------------------------
    window.loadSmilesIntoEditor = async function loadSmilesIntoEditor(smiles, editor, containerSelector, name = "molecule") {
        const cleanSmiles = String(smiles || "").trim();

        if (!cleanSmiles) {
            alert(`Please enter a ${name} SMILES.`);
            return false;
        }

        if (!editor || typeof editor.loadMolecule !== "function") {
            console.warn(`⚠ ${name} editor not ready. Retrying...`);
            setTimeout(() => loadSmilesIntoEditor(cleanSmiles, editor, containerSelector, name), 200);
            return false;
        }

        try {
            console.log(`📤 Converting ${name} SMILES through backend:`, cleanSmiles);

            const response = await fetch("/api/molecule/smiles-to-mol", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ smiles: cleanSmiles })
            });

            const data = await response.json();

            if (!response.ok || data.error || !data.mol_block) {
                console.error(`❌ Failed to convert ${name} SMILES:`, data);
                alert(`Failed to load ${name} SMILES.`);
                return false;
            }

            const molecule = ChemDoodle.readMOL(data.mol_block);

            editor.clear();
            editor.loadMolecule(molecule);
            if (typeof editor.repaint === "function") editor.repaint();

            if (containerSelector && window.$) {
                $(containerSelector).show();
            } else if (containerSelector) {
                const container = document.querySelector(containerSelector);
                if (container) container.style.display = "block";
            }

            console.log(`✅ ${name} loaded from SMILES.`);
            return true;

        } catch (err) {
            console.error(`❌ Error loading ${name} SMILES:`, err);
            alert(`Error loading ${name} SMILES.`);
            return false;
        }
    };

    // ------------------------------------------------------------------------
    // 2) Manual SMILES buttons — preserve these names from your HTML
    // ------------------------------------------------------------------------
    window.loadWarheadSmilesFromInput = function loadWarheadSmilesFromInput() {
        const smiles = document.getElementById("warhead-smiles-input")?.value || "";
        window.loadSmilesIntoEditor(smiles, window.sketcher, "#ligand-container", "warhead");
    };

    window.loadLinkerSmilesFromInput = function loadLinkerSmilesFromInput() {
        const smiles = document.getElementById("linker-smiles-input")?.value || "";
        window.loadSmilesIntoEditor(smiles, window.linkerSketcher, "#linker-container", "linker");
    };

    window.loadLigaseSmilesFromInput = function loadLigaseSmilesFromInput() {
        const smiles = document.getElementById("ligase-smiles-input")?.value || "";
        window.loadSmilesIntoEditor(smiles, window.ligaseSketcher, "#ligase-container", "ligase");
    };

    window.toggleSmilesPanel = function toggleSmilesPanel(panelId, buttonEl) {
        const panel = document.getElementById(panelId);
        if (!panel) return;

        const isOpen = panel.classList.contains("open");
        panel.classList.toggle("open", !isOpen);

        if (buttonEl) {
            buttonEl.classList.toggle("active", !isOpen);
            buttonEl.textContent = isOpen ? "Load from SMILES" : "Hide SMILES";
        }
    };

    // ------------------------------------------------------------------------
    // 3) Warhead handoff loader
    // ------------------------------------------------------------------------
    async function loadIncomingWarhead(rawValue) {
        const value = safeDecode(rawValue);

        if (!value) {
            console.log("ℹ️ No incoming warhead value detected.");
            return false;
        }

        if (window.__WARHEAD_HANDOFF_LOADED) {
            console.log("⚠️ Warhead handoff already loaded once; skipping duplicate.");
            return false;
        }

        window.__WARHEAD_HANDOFF_LOADED = true;

        clearWarheadStateForIncomingHandoff();

        // Put whatever came in into the visible warhead SMILES box.
        // If it is a ligand code, this still helps debugging.
        setInputValue("warhead-smiles-input", value);
        openSmilesPanel("warhead-smiles-panel");

        console.log("🧬 Incoming warhead handoff detected:", value);

        // Preserve older system:
        // ?lig_smi=HFY or ?lig_smi=A1A00 should behave as a ligand code.
        // ?lig_smi=c1ccc... should behave as raw SMILES.
        if (isLikelyLigandCode(value) && !isProbablySmiles(value)) {
            console.log("✅ Incoming warhead treated as ligand code:", value);

            if (typeof window.loadLigandFromCode === "function") {
                window.loadLigandFromCode(value);
            } else if (typeof loadLigandFromCode === "function") {
                loadLigandFromCode(value);
            } else {
                console.error("❌ loadLigandFromCode is not defined.");
                return false;
            }

            sessionStorage.setItem("warheadSource", "url-ligand-code");
            sessionStorage.setItem("ligandHead2", value.toUpperCase());

            return true;
        }

        console.log("✅ Incoming warhead treated as raw SMILES.");

        const ok = await window.loadSmilesIntoEditor(
            value,
            window.sketcher,
            "#ligand-container",
            "warhead"
        );

        if (ok) {
            sessionStorage.setItem("warheadSource", "url-smiles");
            sessionStorage.setItem("warheadHandoffSmiles", value);
            sessionStorage.setItem("incomingWarheadSmiles", value);

            if (typeof showAlert === "function") {
                showAlert("✅ Warhead loaded from SMILES. Add your U attachment atom, then click Save.", "success");
            }

            console.log("✅ URL/hash SMILES successfully loaded into Warhead editor.");
        }

        return ok;
    }

    // ------------------------------------------------------------------------
    // 4) Optional linker / ligase / recruiter URL loaders
    // ------------------------------------------------------------------------
    function loadOptionalLinker(rawLinker) {
        const linker = safeDecode(rawLinker);
        if (!linker) return;

        console.log("🔗 Incoming linker detected:", linker);

        if (typeof window.openLinkerEditor === "function") {
            window.openLinkerEditor(linker);
        } else if (typeof openLinkerEditor === "function") {
            openLinkerEditor(linker);
        } else {
            console.warn("⚠ openLinkerEditor not defined yet.");
        }
    }

    function loadOptionalLigase(rawLigase) {
        const ligase = safeDecode(rawLigase);
        if (!ligase) return;

        console.log("🧲 Incoming ligase detected:", ligase);

        if (typeof window.renderLigase === "function") {
            window.renderLigase(ligase);
        } else if (typeof renderLigase === "function") {
            renderLigase(ligase);
        } else {
            console.warn("⚠ renderLigase not defined yet.");
        }
    }

    function loadOptionalRecruiter(rawRecruiter) {
        const recruiter = safeDecode(rawRecruiter);
        if (!recruiter) return;

        console.log("🔎 Incoming recruiter detected:", recruiter);

        if (typeof window.loadRecruiterMolecule === "function") {
            window.loadRecruiterMolecule(recruiter);
        } else if (typeof loadRecruiterMolecule === "function") {
            loadRecruiterMolecule(recruiter);
        } else {
            console.warn("⚠ loadRecruiterMolecule not defined yet.");
        }
    }


    // ============================================================================
    // 🔌 PUBLIC HANDOFF API
    // Allows another same-origin page/tab to inject a warhead SMILES into the
    // currently open PROTAC Builder without losing the loaded ligase/session.
    // ============================================================================
    window.PROTACBuilderHandoff = window.PROTACBuilderHandoff || {};

    window.PROTACBuilderHandoff.loadWarheadSmiles = function loadWarheadSmiles(smiles) {
        const cleanSmiles = String(smiles || "").trim();

        if (!cleanSmiles) {
            console.error("❌ PROTACBuilderHandoff.loadWarheadSmiles received empty SMILES.");
            return;
        }

        console.log("📡 Direct handoff received inside active PROTAC Builder:", cleanSmiles);

        waitForChemDoodleReady(async () => {
            // Allow replacing/updating the warhead in the same builder page.
            window.__WARHEAD_HANDOFF_LOADED = false;

            await loadIncomingWarhead(cleanSmiles);
        });
    };

    window.PROTACBuilderHandoff.getActiveSession = function getActiveSession() {
        const query = new URLSearchParams(window.location.search || "");
        const hash = new URLSearchParams((window.location.hash || "").replace(/^#/, ""));

        return (
            query.get("session") ||
            hash.get("session") ||
            window.convertedSession ||
            sessionStorage.getItem("convertedSession") ||
            ""
        );
    };

    // ------------------------------------------------------------------------
    // 5) Main boot
    // ------------------------------------------------------------------------
    function bootHandoffLoader() {
        const incoming = getAllIncomingParams();

        waitForChemDoodleReady(async () => {
            console.log("🚦 ChemDoodle ready → running handoff loader.");

            await loadIncomingWarhead(incoming.warheadValue);

            if (incoming.linker) {
                loadOptionalLinker(incoming.linker);
            }

            if (incoming.ligase) {
                loadOptionalLigase(incoming.ligase);
            }

            if (incoming.recruiter) {
                loadOptionalRecruiter(incoming.recruiter);
            }
        });
    }

    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", bootHandoffLoader);
    } else {
        bootHandoffLoader();
    }

})();




// ============================================================================
// WARHEAD DROPDOWN HANDLER
// Does not overwrite incoming URL/hash SMILES.
// ============================================================================
$(document).ready(function () {
    console.log("🔄 Initializing warhead dropdown selection in COPYindex...");

    function hasIncomingHandoff() {
        const q = new URLSearchParams(window.location.search || "");
        const h = new URLSearchParams((window.location.hash || "").replace(/^#/, ""));

        return Boolean(
            q.get("lig_smi") ||
            q.get("smiles") ||
            q.get("warhead_smiles") ||
            q.get("warheadSmiles") ||
            h.get("lig_smi") ||
            h.get("smiles") ||
            h.get("warhead_smiles") ||
            h.get("warheadSmiles") ||
            sessionStorage.getItem("incomingWarheadSmiles")
        );
    }

    // Manual dropdown selection still works.
    $("#warhead").off("change.protacWarhead").on("change.protacWarhead", function () {
        const selectedSmiles = $(this).val();

        if (!selectedSmiles) return;

        console.log("✅ New warhead dropdown selected:", selectedSmiles);

        // If the user manually changes dropdown, it should override imported handoff.
        window.__WARHEAD_HANDOFF_LOADED = false;
        sessionStorage.removeItem("incomingWarheadSmiles");
        sessionStorage.removeItem("warheadHandoffSmiles");

        loadLigand(selectedSmiles);
    });

    // Older ligand-code URL path still works, but only if there is no SMILES handoff.
    setTimeout(() => {
        if (hasIncomingHandoff()) {
            console.log("✅ Incoming SMILES handoff exists; skipping ligand-code auto-load.");
            return;
        }

        const params = new URLSearchParams(window.location.search || "");
        const ligandCode = params.get("ligand");

        if (ligandCode) {
            console.log("✅ Auto-loading ligand code from URL:", ligandCode);
            loadLigandFromCode(ligandCode);
        }
    }, 500);
});


// ============================================================================
// 🧠 ACTIVE PROTAC BUILDER SESSION REGISTRY + LIVE SMILES INJECTION
// This lets Target Builder send a warhead SMILES into the already-open builder.
// ============================================================================
(function registerActiveProtacBuilderSession() {
    "use strict";

    function getCurrentSessionID() {
        const query = new URLSearchParams(window.location.search || "");
        const hash = new URLSearchParams((window.location.hash || "").replace(/^#/, ""));

        return (
            query.get("session") ||
            hash.get("session") ||
            window.convertedSession ||
            sessionStorage.getItem("convertedSession") ||
            ""
        );
    }

    function rememberActiveBuilder() {
        const sessionID = getCurrentSessionID();

        localStorage.setItem("protacBuilder.activeHref", window.location.href);
        localStorage.setItem("protacBuilder.activePath", window.location.pathname);

        if (sessionID) {
            localStorage.setItem("protacBuilder.activeSession", sessionID);
            console.log("💾 Registered active PROTAC Builder session:", sessionID);
        } else {
            console.log("💾 Registered active PROTAC Builder page without converted session.");
        }
    }

    // Register once now.
    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", rememberActiveBuilder);
    } else {
        rememberActiveBuilder();
    }

    // Keep session fresh if URL changes through browser history.
    window.addEventListener("pageshow", rememberActiveBuilder);
    window.addEventListener("focus", rememberActiveBuilder);

    // Same-origin live injection channel.
    // Works when sender and builder are both on kyle.rove-vernier.ts.net.
    try {
        const channel = new BroadcastChannel("protac_builder_handoff");

        channel.addEventListener("message", (event) => {
            const data = event.data || {};

            if (data.type !== "LOAD_WARHEAD_SMILES") return;

            const smiles = String(data.smiles || "").trim();
            if (!smiles) return;

            console.log("📨 BroadcastChannel received warhead SMILES:", smiles);

            if (
                window.PROTACBuilderHandoff &&
                typeof window.PROTACBuilderHandoff.loadWarheadSmiles === "function"
            ) {
                window.PROTACBuilderHandoff.loadWarheadSmiles(smiles);
            } else {
                console.warn("⚠ PROTACBuilderHandoff API not ready yet; retrying...");
                setTimeout(() => {
                    window.PROTACBuilderHandoff?.loadWarheadSmiles?.(smiles);
                }, 500);
            }
        });

        console.log("📡 PROTAC Builder BroadcastChannel listener active.");
    } catch (err) {
        console.warn("⚠ BroadcastChannel unavailable:", err);
    }
})();


// ============================================================================
// 📬 CROSS-WINDOW WARHEAD SMILES RECEIVER
// Lets another tool inject SMILES into THIS already-open PROTAC Builder tab.
// Works across subdomains using window.postMessage.
// ============================================================================
(function installProtacBuilderMessageReceiver() {
    "use strict";

    if (window.__PROTAC_BUILDER_MESSAGE_RECEIVER_INSTALLED) {
        console.log("⚠️ PROTAC Builder message receiver already installed; skipping duplicate.");
        return;
    }

    window.__PROTAC_BUILDER_MESSAGE_RECEIVER_INSTALLED = true;

    const ALLOWED_ORIGINS = new Set([
        "https://kyle.rove-vernier.ts.net",
        "https://stan.rove-vernier.ts.net",
        "https://protacbuilder.com",
        "https://vlisemod.com",
        "http://127.0.0.1:5069",
        "http://localhost:5069",
        "http://127.0.0.1:5000",
        "http://127.0.0.1:5002",
        "http://localhost:5000",
        "http://localhost:5002"
    ]);

    function waitForBuilderReady(callback, tries = 0) {
        const ready =
            typeof ChemDoodle !== "undefined" &&
            (window.chemDoodleInitialized === true || window.ChemDoodleEditorsReady === true || chemDoodleInitialized === true) &&
            (window.sketcher || typeof sketcher !== "undefined");

        if (ready) {
            callback();
            return;
        }

        if (tries > 150) {
            console.error("❌ Timed out waiting for PROTAC Builder ChemDoodle editor.");
            return;
        }

        setTimeout(() => waitForBuilderReady(callback, tries + 1), 100);
    }

    async function injectWarheadSmiles(smiles) {
        const cleanSmiles = String(smiles || "").trim();

        if (!cleanSmiles) {
            console.error("❌ Empty SMILES received by PROTAC Builder.");
            return false;
        }

        console.log("📬 Injecting incoming warhead SMILES into active builder:", cleanSmiles);

        // Allow replacing the warhead multiple times in the same open builder.
        window.__WARHEAD_HANDOFF_LOADED = false;

        // Preferred path if your newer handoff object exists.
        if (
            window.PROTACBuilderHandoff &&
            typeof window.PROTACBuilderHandoff.loadWarheadSmiles === "function"
        ) {
            window.PROTACBuilderHandoff.loadWarheadSmiles(cleanSmiles);
            return true;
        }

        // Existing path from your current file.
        if (typeof window.loadWarheadSmilesFromURL === "function") {
            await window.loadWarheadSmilesFromURL(cleanSmiles);
            return true;
        }

        if (typeof loadWarheadSmilesFromURL === "function") {
            await loadWarheadSmilesFromURL(cleanSmiles);
            return true;
        }

        // Final fallback: use the universal SMILES editor loader.
        const editor = window.sketcher || sketcher;

        if (typeof window.loadSmilesIntoEditor === "function") {
            await window.loadSmilesIntoEditor(
                cleanSmiles,
                editor,
                "#ligand-container",
                "warhead from live handoff"
            );
            return true;
        }

        console.error("❌ No warhead SMILES loader found in PROTAC Builder.");
        return false;
    }

    window.addEventListener("message", (event) => {
        const data = event.data || {};

        if (!data || data.type !== "PROTAC_BUILDER_LOAD_WARHEAD_SMILES") {
            return;
        }

        if (!ALLOWED_ORIGINS.has(event.origin)) {
            console.warn("⚠️ Ignoring PROTAC Builder message from unapproved origin:", event.origin);
            return;
        }

        const smiles = String(data.smiles || "").trim();

        waitForBuilderReady(async () => {
            const ok = await injectWarheadSmiles(smiles);

            try {
                event.source?.postMessage(
                    {
                        type: "PROTAC_BUILDER_WARHEAD_ACK",
                        ok,
                        received: smiles,
                        href: window.location.href
                    },
                    event.origin
                );
            } catch (err) {
                console.warn("⚠️ Could not send ACK back to opener:", err);
            }
        });
    });

    console.log("📬 PROTAC Builder cross-window SMILES receiver installed.");
})();

// ============================================================================
// 📡 PROTAC BUILDER SESSION BUS
// Allows an already-open /builder?session=... tab to receive
// warhead SMILES directly without reload and without opening a new window.
// ============================================================================
(function installProtacBuilderSessionBus() {
    "use strict";

    if (window.__PROTAC_BUILDER_SESSION_BUS_INSTALLED) {
        console.log("⚠️ PROTAC Builder session bus already installed; skipping.");
        return;
    }

    window.__PROTAC_BUILDER_SESSION_BUS_INSTALLED = true;

    const CHANNEL_NAME = "protac_builder_session_bus";
    const CLIENT_ID = crypto.randomUUID ? crypto.randomUUID() : String(Date.now());

    function getBuilderSessionID() {
        const q = new URLSearchParams(window.location.search || "");
        const h = new URLSearchParams((window.location.hash || "").replace(/^#/, ""));

        return (
            q.get("session") ||
            h.get("session") ||
            window.convertedSession ||
            sessionStorage.getItem("convertedSession") ||
            ""
        );
    }

    function rememberThisBuilderAsActive() {
        const sessionID = getBuilderSessionID();

        localStorage.setItem("protacBuilder.activeHref", window.location.href);
        localStorage.setItem("protacBuilder.activeClientId", CLIENT_ID);

        if (sessionID) {
            localStorage.setItem("protacBuilder.activeSession", sessionID);
        }

        console.log("💾 Active PROTAC Builder registered:", {
            clientId: CLIENT_ID,
            session: sessionID || "(no session)",
            href: window.location.href
        });
    }

    function waitForChemDoodleReady(callback, tries = 0) {
        const ready =
            typeof ChemDoodle !== "undefined" &&
            (
                window.chemDoodleInitialized === true ||
                window.ChemDoodleEditorsReady === true ||
                typeof chemDoodleInitialized !== "undefined" && chemDoodleInitialized === true
            ) &&
            (
                window.sketcher ||
                typeof sketcher !== "undefined"
            );

        if (ready) {
            callback();
            return;
        }

        if (tries > 150) {
            console.error("❌ Timed out waiting for ChemDoodle in active builder.");
            return;
        }

        setTimeout(() => waitForChemDoodleReady(callback, tries + 1), 100);
    }

    async function loadIncomingWarheadIntoThisBuilder(smiles) {
        const cleanSmiles = String(smiles || "").trim();

        if (!cleanSmiles) {
            console.error("❌ Empty SMILES received by active builder.");
            return false;
        }

        console.log("🧬 Active builder loading incoming warhead SMILES:", cleanSmiles);

        // Allow replacing the warhead repeatedly in the same tab.
        window.__WARHEAD_HANDOFF_LOADED = false;

        // Preferred newer API, if present.
        if (
            window.PROTACBuilderHandoff &&
            typeof window.PROTACBuilderHandoff.loadWarheadSmiles === "function"
        ) {
            await window.PROTACBuilderHandoff.loadWarheadSmiles(cleanSmiles);
            return true;
        }

        // Your current/simple URL loader path.
        if (typeof window.loadWarheadSmilesFromURL === "function") {
            await window.loadWarheadSmilesFromURL(cleanSmiles);
            return true;
        }

        if (typeof loadWarheadSmilesFromURL === "function") {
            await loadWarheadSmilesFromURL(cleanSmiles);
            return true;
        }

        // Fallback direct editor loader.
        const editor = window.sketcher || sketcher;

        if (typeof window.loadSmilesIntoEditor === "function") {
            await window.loadSmilesIntoEditor(
                cleanSmiles,
                editor,
                "#ligand-container",
                "warhead from active session bus"
            );
            return true;
        }

        console.error("❌ No compatible warhead loader found in active builder.");
        return false;
    }

    let channel = null;

    try {
        channel = new BroadcastChannel(CHANNEL_NAME);
    } catch (err) {
        console.error("❌ BroadcastChannel unavailable:", err);
        return;
    }

    channel.addEventListener("message", (event) => {
        const msg = event.data || {};

        if (msg.type === "PROTAC_BUILDER_PING") {
            const sessionID = getBuilderSessionID();

            channel.postMessage({
                type: "PROTAC_BUILDER_PONG",
                requestId: msg.requestId || "",
                clientId: CLIENT_ID,
                session: sessionID,
                href: window.location.href,
                ts: Date.now()
            });

            return;
        }

        if (msg.type !== "PROTAC_APPEND_WARHEAD_SMILES") return;

        const mySession = getBuilderSessionID();
        const requestedSession = String(msg.session || "").trim();

        // If sender asked for a specific session, only that session should accept.
        if (requestedSession && mySession && requestedSession !== mySession) {
            console.log("⏭️ Ignoring SMILES handoff for different builder session:", {
                requestedSession,
                mySession
            });
            return;
        }

        // If sender addressed a specific client, only that client should accept.
        if (msg.clientId && msg.clientId !== CLIENT_ID) {
            console.log("⏭️ Ignoring SMILES handoff for different builder client.");
            return;
        }

        waitForChemDoodleReady(async () => {
            const ok = await loadIncomingWarheadIntoThisBuilder(msg.smiles);

            channel.postMessage({
                type: "PROTAC_APPEND_WARHEAD_ACK",
                requestId: msg.requestId || "",
                ok,
                clientId: CLIENT_ID,
                session: mySession,
                href: window.location.href,
                ts: Date.now()
            });
        });
    });

    rememberThisBuilderAsActive();

    window.addEventListener("focus", rememberThisBuilderAsActive);
    window.addEventListener("pageshow", rememberThisBuilderAsActive);

    console.log("📡 PROTAC Builder session bus installed:", {
        clientId: CLIENT_ID,
        session: getBuilderSessionID() || "(no session)"
    });
})();
