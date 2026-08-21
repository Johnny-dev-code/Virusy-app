// --- STAV APLIKÁCIE ---
let currentMode = 'live'; // 'live' alebo 'saved'
let isSimulating = false;
let isInitialized = false;
let simTimer = null;

let activeReplayMaxSteps = 0;
let currentReplayStep = 0;
let isReplayPlaying = false;
let replayTimer = null;

// Pomocná funkcia na čakanie na PyWebView API
function waitForPywebview(callback) {
    if (window.pywebview && window.pywebview.api) {
        callback();
    } else {
        window.addEventListener('pywebviewready', callback);
    }
}

// --- 1. PREPÍNANIE ZÁLOŽIEK (SIMULATION / SAVED) ---
function switchMode(mode) {
    currentMode = mode;

    // Zmena aktívnych záložiek v hlavičke
    document.getElementById('tab-live').classList.toggle('active', mode === 'live');
    document.getElementById('tab-saved').classList.toggle('active', mode === 'saved');

    // Zmena aktívnych panelov vľavo
    document.getElementById('panel-live').classList.toggle('active', mode === 'live');
    document.getElementById('panel-saved').classList.toggle('active', mode === 'saved');

    // Replay lišta pod grafom
    const replayBar = document.getElementById('replay-controls');
    if (mode === 'saved' && activeReplayMaxSteps > 0) {
        replayBar.style.display = 'flex';
    } else {
        replayBar.style.display = 'none';
        pauseReplay();
    }

    // Pozastavenie simulácií pri prepínaní
    if (mode === 'saved') {
        if (isSimulating) toggleSimulation(false); // Pozastaví živú simuláciu
        fetchSavedList();
    } else if (mode === 'live') {
        pauseReplay(); // Pozastaví prehrávač uložených simulácií
    }
}

// --- 2. ŽIVÁ SIMULÁCIA (LIVE SIMULATION) ---
function getSliderParams() {
    return {
        num_people: parseInt(document.getElementById('param-pop').value),
        contact_probability: parseFloat(document.getElementById('param-contact').value),
        transmission_probability: parseFloat(document.getElementById('param-trans').value),
        recovered_transmission_probability: parseFloat(document.getElementById('param-rectrans').value),
        vaccine_transmition: parseFloat(document.getElementById('param-vactrans').value),
        death_probability: parseFloat(document.getElementById('param-death').value),
        vaccine_rate: parseFloat(document.getElementById('param-vacrate').value)
    };
}

function runStep() {
    window.pywebview.api.trigger_next_step().then(data => {
        if (!data || data.error) {
            console.error(data ? data.error : "Žiadne dáta z Pythonu");
            toggleSimulation(false);
            return;
        }

        // Vykreslenie obrázku siete
        if (data.network_graph) {
            const netImg = document.getElementById('network-image');
            netImg.src = data.network_graph;
            netImg.style.display = 'block';
            document.getElementById('network-placeholder').style.display = 'none';
        }

        // Vykreslenie obrázku grafu
        if (data.dynamics_graph) {
            const dynImg = document.getElementById('dynamics-image');
            dynImg.src = data.dynamics_graph;
            dynImg.style.display = 'block';
            document.getElementById('dynamics-placeholder').style.display = 'none';
        }

        // Sprístupníme tlačidlo na uloženie
        const btnSave = document.getElementById('btn-save-current');
        if (btnSave) btnSave.disabled = false;

        // Zastavíme, ak v populácii nezostali nakazení
        if (data.is_finished) {
            toggleSimulation(false);
        }
    });
}

function toggleSimulation(forceState) {
    const btn = document.getElementById('btn-play');

    // Ak vynucujeme vypnutie (napr. pri pauze alebo dobehnutí)
    if (forceState === false) {
        isSimulating = false;
        if (btn) btn.innerText = '▶ Run';
        if (simTimer) {
            clearInterval(simTimer);
            simTimer = null;
        }
        return;
    }

    if (!isSimulating) {
        // Ak spúšťame prvýkrát, najprv inicializujeme
        if (!isInitialized) {
            const params = getSliderParams();
            window.pywebview.api.init_simulation(params).then(() => {
                isInitialized = true;
                startInterval();
            });
        } else {
            // Ak len pokračujeme po pauze
            startInterval();
        }
    } else {
        // PAUZA
        isSimulating = false;
        if (btn) btn.innerText = '▶ Run';
        if (simTimer) {
            clearInterval(simTimer);
            simTimer = null;
        }
    }
}

// Funkcia pre okamžitú reakciu pri zmene v menu počas behu simulácie
function changeSpeed() {
    if (isSimulating) {
        startInterval();
    }
}

function startInterval() {
    isSimulating = true;
    const btn = document.getElementById('btn-play');
    if (btn) btn.innerText = '❚❚ Pause';
    
    // Načíta priamo hodnotu z value (5000, 2500 alebo 1000)
    const speed = parseInt(document.getElementById('param-speed').value) || 5000;
    
    if (simTimer) clearInterval(simTimer);
    simTimer = setInterval(runStep, speed);
}

function resetSim() {
    toggleSimulation(false);
    isInitialized = false;
    
    // Inicializujeme novú simuláciu s aktuálnymi hodnotami sliderov
    const params = getSliderParams();
    window.pywebview.api.init_simulation(params).then(() => {
        isInitialized = true;
        runStep(); // Zobrazí nultý/prvý krok
    });
}

// --- 3. UKLADANIE A NAČÍTANIE (SAVES) ---
function saveCurrentSimulation() {
    window.pywebview.api.save_current_simulation().then(res => {
        if (res && res.status === 'success') {
            alert('Simulácia bola úspešne uložená: ' + res.filename);
            fetchSavedList();
        } else {
            alert('Chyba pri ukladaní: ' + (res ? res.message : 'Neznáma chyba'));
        }
    });
}

function fetchSavedList() {
    window.pywebview.api.get_saved_simulations().then(files => {
        const listEl = document.getElementById('saved-list');
        if (!listEl) return;

        if (!files || files.length === 0) {
            listEl.innerHTML = '<div class="empty-state">Zatiaľ žiadne uložené simulácie.</div>';
            return;
        }

        listEl.innerHTML = files.map(file => `
            <div class="preset-card" style="margin-bottom:8px; cursor:pointer;" onclick="loadReplay('${file}')">
                <strong>${file}</strong>
                <p>Klikni pre načítanie</p>
            </div>
        `).join('');
    });
}

function loadReplay(filename) {
    pauseReplay(); // Zastaví rozbehané prehrávanie predchádzajúceho súboru

    window.pywebview.api.load_replay(filename).then(res => {
        if (res && res.status === 'success') {
            activeReplayMaxSteps = res.max_steps;
            currentReplayStep = 0;

            const timeline = document.getElementById('replay-timeline');
            if (timeline) {
                timeline.min = 0;
                timeline.max = activeReplayMaxSteps - 1;
                timeline.value = 0;
            }

            document.getElementById('replay-controls').style.display = 'flex';
            renderReplayFrame(0);
        } else {
            alert('Chyba pri načítaní: ' + (res ? res.message : 'Neznáma chyba'));
        }
    });
}

// --- 4. PREHRÁVAČ (REPLAY CONTROLLER) ---
function renderReplayFrame(step) {
    currentReplayStep = parseInt(step);
    
    const timeline = document.getElementById('replay-timeline');
    if (timeline) timeline.value = currentReplayStep;
    
    const counter = document.getElementById('replay-step-counter');
    if (counter) {
        counter.innerText = `Iter: ${currentReplayStep}/${activeReplayMaxSteps - 1}`;
    }

    window.pywebview.api.render_replay_step(currentReplayStep).then(data => {
        if (!data || data.error) return;

        if (data.network_graph) {
            const netImg = document.getElementById('network-image');
            netImg.src = data.network_graph;
            netImg.style.display = 'block';
            document.getElementById('network-placeholder').style.display = 'none';
        }
        if (data.dynamics_graph) {
            const dynImg = document.getElementById('dynamics-image');
            dynImg.src = data.dynamics_graph;
            dynImg.style.display = 'block';
            document.getElementById('dynamics-placeholder').style.display = 'none';
        }
    });
}

function replayStep(direction) {
    let nextStep = currentReplayStep + direction;
    if (nextStep >= 0 && nextStep < activeReplayMaxSteps) {
        renderReplayFrame(nextStep);
    }
}

function onTimelineSeek(val) {
    renderReplayFrame(val);
}

function toggleReplayPlay() {
    if (isReplayPlaying) {
        pauseReplay();
    } else {
        startReplay();
    }
}

function startReplay() {
    if (currentReplayStep >= activeReplayMaxSteps - 1) {
        currentReplayStep = 0; // Prehrá znova od začiatku, ak sme na konci
    }

    isReplayPlaying = true;
    const btn = document.getElementById('btn-replay-play');
    if (btn) btn.innerText = '❚❚ Pause';

    if (replayTimer) clearInterval(replayTimer);
    replayTimer = setInterval(() => {
        if (currentReplayStep < activeReplayMaxSteps - 1) {
            renderReplayFrame(currentReplayStep + 1);
        } else {
            pauseReplay();
        }
    }, 400);
}

function pauseReplay() {
    isReplayPlaying = false;
    if (replayTimer) {
        clearInterval(replayTimer);
        replayTimer = null;
    }
    const btn = document.getElementById('btn-replay-play');
    if (btn) btn.innerText = '▶ Play';
}

// --- POMOCNÉ FUNKCIE ---
function updateVal(id, val) {
    const el = document.getElementById(`val-${id}`);
    if (el) el.innerText = val;
}

function setPreset(name) {
    console.log("Preset chosen:", name);
}

// Inicializácia po štarte PyWebView
waitForPywebview(() => {
    // Aplikácia je pripravená
});