# functionality/saves_handling.py
import os
import json
import io
import base64
from datetime import datetime
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import networkx as nx
from matplotlib.patches import Patch, Wedge, Circle
from matplotlib.collections import PatchCollection

# Konštanta pre priečinok a farby
REPLAYS_DIR = "replays"
os.makedirs(REPLAYS_DIR, exist_ok=True)
COLORS = ['lime', 'salmon', 'darkgreen', 'grey']


def save_simulation(sim_instance):
    """
    Uloží celú históriu simulácie do .jsonl súboru v priečinku replays.
    """
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    filename = f"sim_{timestamp}.jsonl"
    filepath = os.path.join(REPLAYS_DIR, filename)

    try:
        # 1. Metadáta hlavičky
        pos_serializable = {str(k): [float(v[0]), float(v[1])] for k, v in sim_instance.pos.items()}
        edges = [list(e) for e in sim_instance.G.edges()]
        vaccinated_list = list(sim_instance.vaccinated)

        metadata = {
            "type": "metadata",
            "timestamp": timestamp,
            "num_people": sim_instance.num_people,
            "vaccine_rate": sim_instance.vaccine_rate,
            "edges": edges,
            "vaccinated": vaccinated_list,
            "positions": pos_serializable
        }

        # 2. Zápis do JSONL súboru
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(json.dumps(metadata) + "\n")

            if hasattr(sim_instance, 'history'):
                for step_idx, status_snapshot in enumerate(sim_instance.history):
                    step_data = {
                        "step": step_idx,
                        "status": {str(k): v for k, v in status_snapshot.items()}
                    }
                    f.write(json.dumps(step_data) + "\n")

        return {"status": "success", "filename": filename}
    except Exception as e:
        print(f"Chyba pri ukladaní simulácie: {e}")
        return {"status": "error", "message": str(e)}


def list_saved_simulations():
    """Vráti zoznam všetkých uložených súborov v priečinku replays."""
    if not os.path.exists(REPLAYS_DIR):
        return []
    
    files = sorted([f for f in os.listdir(REPLAYS_DIR) if f.endswith(".jsonl")], reverse=True)
    return files


def load_simulation_file(filename):
    """
    Načíta vybraný .jsonl súbor z priečinka replays a vráti štruktúru
    očakávanú v main.py.
    """
    filepath = os.path.join(REPLAYS_DIR, filename)
    if not os.path.exists(filepath):
        return None

    history = []
    metadata = None

    try:
        with open(filepath, "r", encoding="utf-8") as f:
            for i, line in enumerate(f):
                line = line.strip()
                if not line:
                    continue
                data = json.loads(line)
                if i == 0 and data.get("type") == "metadata":
                    metadata = data
                elif "step" in data:
                    history.append(data)

        if not metadata or not history:
            return None

        return {"metadata": metadata, "history": history}
    except Exception as e:
        print(f"Chyba pri načítavaní súboru {filename}: {e}")
        return None


def render_saved_frame(metadata, step_data, cumulative_history):
    """
    Vykreslí konkrétny krok replayu na základe odovzdaných dát.
    Čistí pamäť pomocou plt.close().
    """
    # 1. Rekonštrukcia siete a pozícií
    G = nx.Graph()
    G.add_nodes_from(range(metadata["num_people"]))
    G.add_edges_from(metadata["edges"])
    
    pos = {int(k): v for k, v in metadata["positions"].items()}
    vaccinated = set(metadata.get("vaccinated", []))
    status = {int(k): v for k, v in step_data["status"].items()}

    fig1, ax1 = plt.subplots(figsize=(7, 7))
    fig2, ax2 = plt.subplots(figsize=(6, 4))

    try:
        # 2. Vykreslenie siete
        nx.draw_networkx_edges(G, pos, ax=ax1, edge_color='#cbd5e1', alpha=0.5)

        r = 0.05
        patches = []
        for n in G.nodes:
            x, y = pos[n]
            s = status.get(n, 0)

            if n in vaccinated:
                patches.append(Wedge((x, y), r, 0, 180, facecolor=COLORS[s]))
                patches.append(Wedge((x, y), r, 180, 360, facecolor="blue"))
                patches.append(Circle((x, y), r * 1.05, fill=False, edgecolor='blue', linewidth=2))
            else:
                patches.append(Circle((x, y), r, facecolor=COLORS[s], edgecolor='black'))

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

        # 3. Vykreslenie historického grafu (SIRD Dynamics)
        infected_counts = [sum(1 for s in h["status"].values() if s == 1) for h in cumulative_history]
        recovered_counts = [sum(1 for s in h["status"].values() if s == 2) for h in cumulative_history]
        dead_counts = [sum(1 for s in h["status"].values() if s == 3) for h in cumulative_history]

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
        # Dôkladné čistenie pamäte RAM
        plt.close(fig1)
        plt.close(fig2)