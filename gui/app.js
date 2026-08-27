// --- STAV APLIKÁCIE ---
let currentMode = 'live'; // 'live' alebo 'saved'
let isSimulating = false;
let isInitialized = false;
let simTimer = null;

let activeReplayMaxSteps = 0;
let currentReplayStep = 0;
let isReplayPlaying = false;
let replayTimer = null;
let loadedFilename = null;

// Pomocná funkcia na čakanie na PyWebView API
function waitForPywebview(callback) {
    if (window.pywebview && window.pywebview.api) {
        callback();
    } else {
        window.addEventListener('pywebviewready', callback);
    }
}

// Bezpečné nastavenie obrázkov grafov pre živé vysielanie aj prehrávač
function updateGraphImage(imageId, placeholderId, src) {
    let imgEl = document.getElementById(imageId);
    if (!imgEl) {
        // Záchrana ak HTML používa názvy 'img-network' / 'img-dynamics'
        const altId = imageId.includes('network') ? 'img-network' : 'img-dynamics';
        imgEl = document.getElementById(altId);
    }

    if (imgEl) {
        imgEl.src = src;
        imgEl.style.display = 'block';
    }

    const placeholderEl = document.getElementById(placeholderId);
    if (placeholderEl) {
        placeholderEl.style.display = 'none';
    }
}

// --- 1. PREPÍNANIE ZÁLOŽIEK (SIMULATION / SAVED) ---
function switchMode(mode) {
    currentMode = mode;

    const tabLive = document.getElementById('tab-live');
    const tabSaved = document.getElementById('tab-saved');
    if (tabLive) tabLive.classList.toggle('active', mode === 'live');
    if (tabSaved) tabSaved.classList.toggle('active', mode === 'saved');

    const panelLive = document.getElementById('panel-live');
    const panelSaved = document.getElementById('panel-saved');
    if (panelLive) panelLive.classList.toggle('active', mode === 'live');
    if (panelSaved) panelSaved.classList.toggle('active', mode === 'saved');

    const replayBar = document.getElementById('replay-controls');
    if (replayBar) {
        if (mode === 'saved' && activeReplayMaxSteps > 0) {
            replayBar.style.display = 'flex';
        } else {
            replayBar.style.display = 'none';
            pauseReplay();
        }
    }

    if (mode === 'saved') {
        if (isSimulating) toggleSimulation(false);
        fetchSavedList();
    } else if (mode === 'live') {
        pauseReplay();
    }
}

// --- 2. ŽIVÁ SIMULÁCIA (LIVE SIMULATION) ---
function getSliderParams() {
    const getVal = (id, def) => {
        const el = document.getElementById(id);
        return el ? parseFloat(el.value) : def;
    };

    return {
        num_people: parseInt(getVal('param-pop', 100)),
        contact_probability: getVal('param-contact', 0.05),
        transmission_probability: getVal('param-trans', 0.30),
        recovered_transmission_probability: getVal('param-rectrans', 0.05),
        vaccine_transmition: getVal('param-vactrans', 0.10),
        death_probability: getVal('param-death', 0.01),
        vaccine_rate: getVal('param-vacrate', 0.40)
    };
}

function updateSlidersFromMetadata(metadata) {
    if (!metadata) return;

    const setSlider = (id, val) => {
        const el = document.getElementById(id);
        if (el && val !== undefined) {
            el.value = val;
            updateVal(id.replace('param-', ''), val);
        }
    };

    setSlider('param-pop', metadata.num_people);
    setSlider('param-contact', metadata.contact_probability);
    setSlider('param-trans', metadata.transmission_probability);
    setSlider('param-rectrans', metadata.recovered_transmission_probability);
    setSlider('param-vactrans', metadata.vaccine_transmition);
    setSlider('param-death', metadata.death_probability);
    setSlider('param-vacrate', metadata.vaccine_rate);
}

function runStep() {
    if (!window.pywebview || !window.pywebview.api) {
        alert("Chyba: PyWebView API nie je dostupné!");
        toggleSimulation(false);
        return;
    }

    window.pywebview.api.trigger_next_step()
    .then(data => {
        if (!data || data.error) {
            alert("Chyba zo servera pri kroku simulácie: " + (data ? data.error : "Žiadne dáta"));
            toggleSimulation(false);
            return;
        }

        if (data.network_graph) {
            updateGraphImage('network-image', 'network-placeholder', data.network_graph);
        }

        if (data.dynamics_graph) {
            updateGraphImage('dynamics-image', 'dynamics-placeholder', data.dynamics_graph);
        }

        const btnSave = document.getElementById('btn-save-current');
        if (btnSave) btnSave.disabled = false;

        if (data.is_finished) {
            toggleSimulation(false);
        }
    })
    .catch(err => {
        alert("Zlyhalo volanie trigger_next_step: " + err);
        toggleSimulation(false);
    });
}

function toggleSimulation(forceState) {
    const btn = document.getElementById('btn-play');

    // 1. Zastavenie simulácie
    if (forceState === false || isSimulating) {
        isSimulating = false;
        if (btn) btn.innerText = '▶ Run';
        if (simTimer) {
            clearInterval(simTimer);
            simTimer = null;
        }
        return;
    }

    // Bezpečnostná kontrola prítomnosti PyWebView API
    if (!window.pywebview || !window.pywebview.api) {
        alert("Chyba: pywebview.api nie je dostupné!");
        return;
    }

    // 2. Spustenie simulácie
    if (!isSimulating) {
        // Vizuálne dáme ihneď vedieť, že sa niečo deje
        if (btn) btn.innerText = '⏳ Načítavam...';

        // Vetva A: Načítaná uložená simulácia
        if (!isInitialized && loadedFilename !== null) {
            
            // Kontrola, či metóda v Pythone vôbec existuje
            if (typeof window.pywebview.api.resume_simulation_from_saved_step !== 'function') {
                alert("Chyba: Python API neobsahuje metódu 'resume_simulation_from_saved_step'!");
                if (btn) btn.innerText = '▶ Run';
                return;
            }

            // Najprv prepneme záložku do Live režimu, aby sa zobrazili správne grafy
            if (currentMode === 'saved') {
                currentMode = 'live';
                document.getElementById('tab-live')?.classList.add('active');
                document.getElementById('tab-saved')?.classList.remove('active');
                document.getElementById('panel-live')?.classList.add('active');
                document.getElementById('panel-saved')?.classList.remove('active');
                document.getElementById('replay-controls') && (document.getElementById('replay-controls').style.display = 'none');
            }

            window.pywebview.api.resume_simulation_from_saved_step(loadedFilename, currentReplayStep)
            .then(res => {
                if (res && res.status === 'success') {
                    isInitialized = true;
                    startInterval();
                } else {
                    alert('Chyba pri nadväzovaní na simuláciu: ' + (res ? res.message : 'Neznáma chyba'));
                    toggleSimulation(false);
                }
            })
            .catch(err => {
                alert('Výnimka pri nadväzovaní na simuláciu: ' + err);
                toggleSimulation(false);
            });
        } 
        // Vetva B: Úplne nová simulácia
        else if (!isInitialized) {
            const params = getSliderParams();
            window.pywebview.api.init_simulation(params)
            .then(() => {
                isInitialized = true;
                startInterval();
            })
            .catch(err => {
                alert('Chyba pri inicializácii novej simulácie: ' + err);
                toggleSimulation(false);
            });
        } 
        // Vetva C: Pokračovanie v pauznutej simulácii
        else {
            startInterval();
        }
    }
}

function changeSpeed() {
    if (isSimulating) {
        startInterval();
    }
}

function startInterval() {
    isSimulating = true;
    const btn = document.getElementById('btn-play');
    if (btn) btn.innerText = '❚❚ Pause';
    
    const speedEl = document.getElementById('param-speed');
    const speed = speedEl ? (parseInt(speedEl.value) || 2500) : 2500;
    
    if (simTimer) clearInterval(simTimer);
    
    // Spustíme prvý krok okamžite
    runStep();
    simTimer = setInterval(runStep, speed);
}

function resetSim() {
    toggleSimulation(false);
    isInitialized = false;
    loadedFilename = null; // Zresetuje odkaz na uložený súbor
    
    const params = getSliderParams();
    window.pywebview.api.init_simulation(params)
    .then(() => {
        isInitialized = true;
        runStep();
    })
    .catch(err => alert('Chyba pri resete simulácie: ' + err));
}

// --- 3. UKLADANIE A NAČÍTANIE (SAVES) ---
function saveCurrentSimulation() {
    window.pywebview.api.save_current_simulation()
    .then(res => {
        if (res && res.status === 'success') {
            alert('Simulácia bola úspešne uložená: ' + res.filename);
            fetchSavedList();
        } else {
            alert('Chyba pri ukladaní: ' + (res ? res.message : 'Neznáma chyba'));
        }
    })
    .catch(err => alert('Chyba pri ukladaní: ' + err));
}

function fetchSavedList() {
    window.pywebview.api.get_saved_simulations()
    .then(files => {
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
    })
    .catch(err => alert('Chyba pri načítaní zoznamu uložení: ' + err));
}

function loadReplay(filename) {
    pauseReplay();
    loadedFilename = filename;
    isInitialized = false;

    window.pywebview.api.load_replay(filename)
    .then(res => {
        if (res && res.status === 'success') {
            activeReplayMaxSteps = res.max_steps;
            currentReplayStep = 0;

            if (res.metadata) {
                updateSlidersFromMetadata(res.metadata);
            }

            const timeline = document.getElementById('replay-timeline');
            if (timeline) {
                timeline.min = 0;
                timeline.max = activeReplayMaxSteps - 1;
                timeline.value = 0;
            }

            const replayBar = document.getElementById('replay-controls');
            if (replayBar) replayBar.style.display = 'flex';

            renderReplayFrame(0);
        } else {
            alert('Chyba pri načítaní uloženej simulácie: ' + (res ? res.message : 'Neznáma chyba'));
        }
    })
    .catch(err => alert('Chyba pri load_replay: ' + err));
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

    window.pywebview.api.render_replay_step(currentReplayStep)
    .then(data => {
        if (!data || data.error) return;

        if (data.network_graph) {
            updateGraphImage('network-image', 'network-placeholder', data.network_graph);
        }
        if (data.dynamics_graph) {
            updateGraphImage('dynamics-image', 'dynamics-placeholder', data.dynamics_graph);
        }
    })
    .catch(err => alert('Chyba pri vykreslení kroku replayu: ' + err));
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
        currentReplayStep = 0;
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
    if (!el) return;

    if (id === 'pop') {
        el.innerText = parseInt(val);
    } else {
        // Zabezpečí pekne formátované číslá na 2 desatinné miesta (napr. 0.40 namiesto 0.4)
        el.innerText = parseFloat(val).toFixed(2);
    }
}

function setPreset(name) {
    // Možné nastavenie presetov
}

// Inicializácia po štarte PyWebView
waitForPywebview(() => {
    // Pripravené
});