import os
import json
import io
import base64
import networkx as nx
import matplotlib.pyplot as plt
from matplotlib.patches import Circle, Wedge, Patch
from matplotlib.collections import PatchCollection

REPLAYS_DIR = os.path.join(os.path.dirname(__file__), "..", "replays")
COLORS = {0: "lime", 1: "salmon", 2: "darkgreen", 3: "grey"}


def list_saved_simulations():
    """
    Vráti zoznam všetkých uložených .jsonl súborov v priečinku replays.
    """
    replays_path = os.path.abspath(REPLAYS_DIR)
    if not os.path.exists(replays_path):
        os.makedirs(replays_path, exist_ok=True)
        return []
    
    files = [f for f in os.listdir(replays_path) if f.endswith(".jsonl")]
    files.sort(reverse=True)
    return files


def save_simulation(sim, filename=None):
    """
    Uloží aktuálnu simuláciu do .jsonl súboru.
    """
    replays_path = os.path.abspath(REPLAYS_DIR)
    if not os.path.exists(replays_path):
        os.makedirs(replays_path, exist_ok=True)

    if not filename:
        from datetime import datetime
        filename = f"sim_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jsonl"

    filepath = os.path.join(replays_path, filename)

    try:
        with open(filepath, "w", encoding="utf-8") as f:
            # 1. PRVÝ RIADOK: Metadáta
            metadata = {
                "type": "metadata",
                "timestamp": filename,
                "num_people": getattr(sim, 'num_people', len(sim.G.nodes) if hasattr(sim, 'G') else 50),
                "contact_probability": getattr(sim, 'contact_probability', 0.2),
                "transmission_probability": getattr(sim, 'transmission_probability', 0.3),
                "recovered_transmission_probability": getattr(sim, 'recovered_transmission_probability', 0.05),
                "vaccine_transmition": getattr(sim, 'vaccine_transmition', 0.1),
                "death_probability": getattr(sim, 'death_probability', 0.01),
                "vaccine_rate": getattr(sim, 'vaccine_rate', 0.2),
                "edges": list(sim.G.edges()) if hasattr(sim, 'G') else [],
                "vaccinated": list(getattr(sim, 'vaccinated', [])),
                "positions": {str(k): list(v) for k, v in sim.pos.items()} if hasattr(sim, 'pos') else {}
            }
            f.write(json.dumps(metadata) + "\n")

            # 2. ĎALŠIE RIADKY: História
            for step_data in sim.history:
                f.write(json.dumps(step_data) + "\n")

        return {"status": "success", "filename": filename}
    except Exception as e:
        print(f"Chyba pri ukladaní simulácie: {e}")
        return {"status": "error", "message": str(e)}


def load_simulation_file(filename):
    """
    Načíta vybraný .jsonl súbor z priečinka replays.
    """
    replays_path = os.path.abspath(REPLAYS_DIR)
    filepath = os.path.join(replays_path, filename)
    if not os.path.exists(filepath):
        return None

    history = []
    metadata = None

    try:
        with open(filepath, "r", encoding="utf-8") as f:
            step_idx = 0
            for i, line in enumerate(f):
                line = line.strip()
                if not line:
                    continue
                data = json.loads(line)
                
                # Načítanie metadát
                if i == 0 and isinstance(data, dict) and data.get("type") == "metadata":
                    metadata = data
                else:
                    # Spracovanie riadku histórie (normovanie do jednotného tvaru)
                    if isinstance(data, dict):
                        if "status" in data:
                            raw_status = data["status"]
                            step_num = data.get("step", step_idx)
                        else:
                            # Prípad, kedy je riadok priamo slovníkom stavov {"0": 0, "1": 1, ...}
                            raw_status = data
                            step_num = step_idx

                        # Prevedenie kľúčov zo stringu ("0") na int (0)
                        clean_status = {int(k): int(v) for k, v in raw_status.items()}
                        history.append({
                            "step": step_num,
                            "status": clean_status
                        })
                        step_idx += 1

        if not history:
            return None

        # Ak súbor nemal metadáta (starší tvar)
        if not metadata:
            first_status = history[0]["status"]
            num_people = len(first_status)
            metadata = {
                "type": "metadata",
                "timestamp": filename,
                "num_people": num_people,
                "contact_probability": 0.2,
                "transmission_probability": 0.3,
                "recovered_transmission_probability": 0.05,
                "vaccine_transmition": 0.1,
                "death_probability": 0.01,
                "vaccine_rate": 0.2,
                "edges": [],
                "vaccinated": [],
                "positions": {str(i): [0, 0] for i in range(num_people)}
            }

        return {"metadata": metadata, "history": history}
    except Exception as e:
        print(f"Chyba pri načítavaní súboru {filename}: {e}")
        return None


def resume_simulation_from_saved_step(sim, filename, step_index):
    data = load_simulation_file(filename)
    if not data:
        return {"status": "error", "message": "Súbor sa nepodarilo načítať."}

    metadata = data["metadata"]
    history = data["history"]

    if step_index < 0 or step_index >= len(history):
        step_index = 0

    target_step_data = history[step_index]

    # 1. Nastavenie parametrov zo súboru
    sim.num_people = metadata.get("num_people", getattr(sim, 'num_people', 50))
    sim.contact_probability = metadata.get("contact_probability", getattr(sim, 'contact_probability', 0.2))
    sim.transmission_probability = metadata.get("transmission_probability", getattr(sim, 'transmission_probability', 0.3))
    sim.recovered_transmission_probability = metadata.get("recovered_transmission_probability", getattr(sim, 'recovered_transmission_probability', 0.05))
    sim.vaccine_transmition = metadata.get("vaccine_transmition", getattr(sim, 'vaccine_transmition', 0.1))
    sim.death_probability = metadata.get("death_probability", getattr(sim, 'death_probability', 0.01))
    sim.vaccine_rate = metadata.get("vaccine_rate", getattr(sim, 'vaccine_rate', 0.2))

    # 2. Obnovenie grafu a pozícií
    sim.G = nx.Graph()
    sim.G.add_nodes_from(range(sim.num_people))
    
    edges = metadata.get("edges", [])
    if edges:
        sim.G.add_edges_from([(int(u), int(v)) for u, v in edges])

    raw_pos = metadata.get("positions", {})
    if raw_pos:
        sim.pos = {int(k): v for k, v in raw_pos.items()}
    else:
        sim.pos = nx.spring_layout(sim.G)

    sim.vaccinated = set(int(x) for x in metadata.get("vaccinated", []))

    # 3. Prevod stavov uzlov (kľúčov) zo stringu na int
    # Podpora pre číselné kódovanie (0=S, 1=I, 2=R) aj písmenové ('S', 'I', 'R')
    raw_status = target_step_data.get("status", target_step_data)
    sim.status = {}
    for k, v in raw_status.items():
        if k == "step":
            continue
        sim.status[int(k)] = v

    sim.step_count = target_step_data.get("step", step_index)

    # 4. REKONŠTRUKCIA infection_timer
    # Predpokladaná dĺžka infekcie v simulácii (napr. 14 dní alebo sim.infection_duration)
    default_duration = getattr(sim, 'infection_duration', 14)
    sim.infection_timer = {}

    for person, st in sim.status.items():
        # Ak je osoba v danom kroku infikovaná (stav 1 alebo 'I')
        if st in (1, 'I'):
            # Zistíme, pred koľkými krokmi sa nakazila
            steps_infected = 0
            for prev_step_idx in range(step_index, -1, -1):
                prev_status = history[prev_step_idx].get("status", history[prev_step_idx])
                if prev_status.get(str(person)) in (1, 'I') or prev_status.get(person) in (1, 'I'):
                    steps_infected += 1
                else:
                    break  # Tu infekcia začala
            
            # Nastavíme zostávajúci časovač
            remaining_time = max(1, default_duration - (steps_infected - 1))
            sim.infection_timer[person] = remaining_time

    # Obnovenie histórie
    sim.history = [h.get("status", h) for h in history[:step_index + 1]]

    return {"status": "success", "step": sim.step_count}

def render_saved_frame(metadata, step_data, cumulative_history):
    """
    Vykreslí konkrétny krok replayu na základe odovzdaných dát.
    """
    G = nx.Graph()
    G.add_nodes_from(range(metadata.get("num_people", 50)))
    
    edges = metadata.get("edges", [])
    if edges:
        G.add_edges_from([(int(u), int(v)) for u, v in edges])
    
    raw_pos = metadata.get("positions", {})
    pos = {int(k): v for k, v in raw_pos.items()} if raw_pos else nx.spring_layout(G)
    
    vaccinated = set(metadata.get("vaccinated", []))
    status = step_data.get("status", {})

    fig1, ax1 = plt.subplots(figsize=(7, 7))
    fig2, ax2 = plt.subplots(figsize=(6, 4))

    try:
        nx.draw_networkx_edges(G, pos, ax=ax1, edge_color='#cbd5e1', alpha=0.5)

        r = 0.05
        patches = []
        for n in G.nodes:
            x, y = pos.get(n, (0, 0))
            s = status.get(n, 0)

            if n in vaccinated:
                patches.append(Wedge((x, y), r, 0, 180, facecolor=COLORS.get(s, "grey")))
                patches.append(Wedge((x, y), r, 180, 360, facecolor="blue"))
                patches.append(Circle((x, y), r * 1.05, fill=False, edgecolor='blue', linewidth=2))
            else:
                patches.append(Circle((x, y), r, facecolor=COLORS.get(s, "grey"), edgecolor='black'))

        collection = PatchCollection(patches, match_original=True)
        ax1.add_collection(collection)

        if pos:
            x_vals = [p[0] for p in pos.values()]
            y_vals = [p[1] for p in pos.values()]
            pad = 0.2
            ax1.set_xlim(min(x_vals) - pad, max(x_vals) + pad)
            ax1.set_ylim(min(y_vals) - pad, max(y_vals) + pad)

        ax1.set_aspect('equal')
        ax1.axis('off')
        
        legend = [
            Patch(facecolor='lime', label='Susceptible'),
            Patch(facecolor='salmon', label='Infected'),
            Patch(facecolor='darkgreen', label='Recovered'),
            Patch(facecolor='grey', label='Dead'),
            Patch(facecolor='blue', label='Vaccinated')
        ]
        ax1.legend(handles=legend, loc='upper right')
        fig1.tight_layout()

        buf_net = io.BytesIO()
        fig1.savefig(buf_net, format='png', dpi=80)
        buf_net.seek(0)
        net_url = f"data:image/png;base64,{base64.b64encode(buf_net.read()).decode('utf-8')}"
        buf_net.close()

        # Výpočet dynamiky pre graf zo zoznamu histórie
        infected_counts = [sum(1 for s in h.get("status", {}).values() if s == 1) for h in cumulative_history]
        recovered_counts = [sum(1 for s in h.get("status", {}).values() if s == 2) for h in cumulative_history]
        dead_counts = [sum(1 for s in h.get("status", {}).values() if s == 3) for h in cumulative_history]

        ax2.plot(infected_counts, label='Infected', color='salmon', linewidth=2)
        ax2.plot(recovered_counts, label='Recovered', color='darkgreen', linewidth=2)
        ax2.plot(dead_counts, label='Dead', color='grey', linewidth=2)
        ax2.set_xlabel("Iteration")
        ax2.set_ylabel("People")
        ax2.set_title(f"SIRD Dynamics (Step {step_data.get('step', 0)})")
        ax2.legend(loc='upper left')
        ax2.grid(True, linestyle='--', alpha=0.5)
        fig2.tight_layout()

        buf_dyn = io.BytesIO()
        fig2.savefig(buf_dyn, format='png', dpi=80)
        buf_dyn.seek(0)
        dyn_url = f"data:image/png;base64,{base64.b64encode(buf_dyn.read()).decode('utf-8')}"
        buf_dyn.close()

        return {
            "network_graph": net_url,
            "dynamics_graph": dyn_url,
            "step": step_data.get("step", 0)
        }

    finally:
        plt.close(fig1)
        plt.close(fig2)