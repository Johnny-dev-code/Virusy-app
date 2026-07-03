// gui/app.js
let currentPreset = 'showcase';
let isRunning = false;
let isInitialized = false;

function updateVal(id, value) {
    document.getElementById('val-' + id).innerText = parseFloat(value).toFixed(id === 'pop' ? 0 : 2);
}

function setPreset(name) {
    currentPreset = name;
    document.querySelectorAll('.preset-btn').forEach(btn => btn.classList.remove('active'));
    event.currentTarget.classList.add('active');

    if (name === 'showcase') {
        setSliders(100, 0.30, 0.99, 0.01, 0.01, 1.00, 0.99);
    } else if (name === 'random1') {
        setSliders(100, 0.30, 0.00, 0.00, 0.00, 0.10, 0.00);
    } else if (name === 'test_vaccine') {
        setSliders(100, 0.10, 1.00, 0.30, 0.01, 0.90, 0.10);
    }
    isInitialized = false; 
    stopSimulation();
}

function setSliders(pop, contact, trans, rectrans, death, vacrate, vactrans) {
    document.getElementById('param-pop').value = pop; updateVal('pop', pop);
    document.getElementById('param-contact').value = contact; updateVal('contact', contact);
    document.getElementById('param-trans').value = trans; updateVal('trans', trans);
    document.getElementById('param-rectrans').value = rectrans; updateVal('rectrans', rectrans);
    document.getElementById('param-death').value = death; updateVal('death', death);
    document.getElementById('param-vacrate').value = vacrate; updateVal('vacrate', vacrate);
    document.getElementById('param-vactrans').value = vactrans; updateVal('vactrans', vactrans);
}

function toggleSimulation() {
    if (!window.pywebview || !window.pywebview.api) return;

    if (isRunning) {
        stopSimulation();
    } else {
        isRunning = true;
        document.getElementById('btn-play').innerText = "⏸ Pause";
        
        if (!isInitialized) {
            const params = {
                num_people: parseInt(document.getElementById('param-pop').value),
                transmission_probability: parseFloat(document.getElementById('param-trans').value),
                recovered_transmission_probability: parseFloat(document.getElementById('param-rectrans').value),
                death_probability: parseFloat(document.getElementById('param-death').value),
                contact_probability: parseFloat(document.getElementById('param-contact').value),
                vaccine_rate: parseFloat(document.getElementById('param-vacrate').value),
                vaccine_transmition: parseFloat(document.getElementById('param-vactrans').value)
            };
            
            window.pywebview.api.init_simulation(params).then(() => {
                isInitialized = true;
                simulationLoop(); // Spustenie bezpečnej slučky
            });
        } else {
            simulationLoop();
        }
    }
}

function stopSimulation() {
    isRunning = false;
    document.getElementById('btn-play').innerText = "▶ Run";
}

// ASYNCHRÓNNA SLUČKA: Garantuje update po každej jednej iterácii bez sekania
async function simulationLoop() {
    while (isRunning) {
        // 1. Vypýtame si krok z Pythonu a počkáme na odpoveď (await)
        const response = await window.pywebview.api.trigger_next_step();
        
        // 2. Okamžite aktualizujeme čísla v GUI
        document.getElementById('stat-healthy').innerText = response.healthy ?? 0;
        document.getElementById('stat-infected').innerText = response.infected ?? 0;
        document.getElementById('stat-recovered').innerText = response.recovered ?? 0;
        document.getElementById('stat-dead').innerText = response.dead ?? 0;
        document.getElementById('stat-vaccinated').innerText = response.vaccinated ?? 0;

        // 3. Okamžite prekreslíme Sieť
        if (response.network_graph) {
            document.getElementById('network-placeholder').style.display = 'none';
            const img = document.getElementById('network-image');
            img.src = response.network_graph;
            img.style.display = 'block';
        }

        // 4. Okamžite prekreslíme Graf vývoja
        if (response.dynamics_graph) {
            document.getElementById('dynamics-placeholder').style.display = 'none';
            const imgDyn = document.getElementById('dynamics-image');
            imgDyn.src = response.dynamics_graph;
            imgDyn.style.display = 'block';
        }

        // 5. Kontrola konca simulácie
        if (response.is_finished) {
            stopSimulation();
            isInitialized = false;
            alert("Simulácia úspešne skončila. Nákaza sa prestala šíriť.");
            break;
        }

        // 6. Počkáme presne toľko miliseúnd, koľko je vybrané v menu Speed
        const speedMs = parseInt(document.getElementById('param-speed').value);
        await new Promise(resolve => setTimeout(resolve, speedMs));
    }
}

function resetSim() {
    stopSimulation();
    isInitialized = false;
    setPreset('showcase');
    
    document.getElementById('stat-healthy').innerText = "100";
    document.getElementById('stat-infected').innerText = "0";
    document.getElementById('stat-recovered').innerText = "0";
    document.getElementById('stat-dead').innerText = "0";
    document.getElementById('stat-vaccinated').innerText = "0";
    
    document.getElementById('network-image').style.display = 'none';
    document.getElementById('network-placeholder').style.display = 'block';
    
    document.getElementById('dynamics-image').style.display = 'none';
    document.getElementById('dynamics-placeholder').style.display = 'block';
}