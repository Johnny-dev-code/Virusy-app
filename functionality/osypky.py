import random
import networkx as nx
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Patch, Wedge, Circle
from matplotlib.collections import PatchCollection
import io
import base64

colors = ['lime', 'salmon', 'darkgreen', 'grey']

def draw_infection_duration():
    return max(7, min(14, int(random.gauss(10, 2))))

class LiveSimulation:
    def __init__(self, params=None, *args, **kwargs):
        if params is None:
            params = {}

        self.num_people = int(params.get('num_people', 100))
        self.contact_probability = float(params.get('contact_probability', 0.04))
        self.transmission_probability = float(params.get('transmission_probability', 0.90))
        self.recovered_transmission_probability = float(params.get('recovered_transmission_probability', 0.0))
        self.vaccine_transmition = float(params.get('vaccine_transmition', 0.05))
        self.death_probability = float(params.get('death_probability', 0.02))
        self.vaccine_rate = float(params.get('vaccine_rate', 0.40))

        # Načítanie grafu podľa vašej pôvodnej logiky
        p_val = max(0.001, min(1.0, self.contact_probability))
        self.G = nx.erdos_renyi_graph(n=self.num_people, p=p_val)
        self.status = {i: 0 for i in range(self.num_people)}
        self.infection_timer = {}

        # Očkovanie
        num_vaccinated = int(self.num_people * self.vaccine_rate)
        if self.num_people > 0:
            self.vaccinated = set(random.sample(list(self.status.keys()), min(num_vaccinated, self.num_people)))
        else:
            self.vaccinated = set()

        # Patient Zero
        if self.num_people > 0:
            patient_zero = random.choice(list(self.status.keys()))
            self.status[patient_zero] = 1
            self.infection_timer[patient_zero] = draw_infection_duration()

        # Pozície uzlov
        self.pos = nx.spring_layout(self.G, k=1.5, iterations=100)

        # História pre graf SIRD
        self.history = [{n: self.status[n] for n in self.G.nodes}]

        # Matplotlib objekty
        self.fig1, self.ax1 = plt.subplots(figsize=(7, 7))
        self.fig2, self.ax2 = plt.subplots(figsize=(6, 4))

    def next_step(self):
        # Kontrola, či ešte existujú infikovaní
        infected_nodes = [n for n in self.G.nodes if self.status[n] == 1]
        if not infected_nodes:
            return self._generate_response(is_finished=True)

        # PÔVODNÁ LOGIKA SPREAD_VIRUS
        new_status = self.status.copy()

        for person in self.G.nodes:
            if self.status[person] == 3:
                continue

            if self.status[person] == 1:
                # Úmrtie na chorobu
                if random.random() < self.death_probability:
                    new_status[person] = 3
                    self.infection_timer.pop(person, None)
                    continue

                # Odpočítavanie trvania infekcie
                self.infection_timer[person] -= 1

                # Uzdravenie
                if self.infection_timer[person] <= 0:
                    new_status[person] = 2
                    self.infection_timer.pop(person, None)
                    continue

                # Infikovanie susedov
                for neighbor in self.G.neighbors(person):
                    if self.status[neighbor] == 3 or self.status[neighbor] == 1:
                        continue

                    if neighbor in self.vaccinated:
                        susceptibility = self.vaccine_transmition
                    elif self.status[neighbor] == 2:
                        susceptibility = self.recovered_transmission_probability
                    elif self.status[neighbor] == 0:
                        susceptibility = 1.0
                    else:
                        continue

                    if random.random() < self.transmission_probability * susceptibility:
                        new_status[neighbor] = 1
                        self.infection_timer[neighbor] = draw_infection_duration()

        self.status = new_status
        self.history.append({n: self.status[n] for n in self.G.nodes})

        # Zistenie, či po tomto kroku ešte ostal niekto infikovaný
        still_infected = any(s == 1 for s in self.status.values())
        return self._generate_response(is_finished=not still_infected)

    def _generate_response(self, is_finished):
        # Vyčistenie plochy bez porušenia osí Matplotlibu
        self.ax1.cla()

        # Vykreslenie hrán
        nx.draw_networkx_edges(self.G, self.pos, ax=self.ax1, edge_color='#64748b', width=1.0, alpha=0.5)

        # Vykreslenie uzlov (Wedge a Circle presne podľa pôvodného kódu)
        r = 0.05
        patches = []
        for n in self.G.nodes:
            x, y = self.pos[n]
            s = self.status[n]
            c_color = colors[s]

            if n in self.vaccinated:
                patches.append(Wedge((x, y), r, 0, 180, facecolor=c_color))
                patches.append(Wedge((x, y), r, 180, 360, facecolor="blue"))
                patches.append(Circle((x, y), r * 1.05, fill=False, edgecolor='blue', linewidth=1.5))
            else:
                patches.append(Circle((x, y), r, facecolor=c_color, edgecolor='black', linewidth=0.8))

        collection = PatchCollection(patches, match_original=True)
        self.ax1.add_collection(collection)

        # Nastavenie hraníc platna
        if self.pos:
            x_vals = [p[0] for p in self.pos.values()]
            y_vals = [p[1] for p in self.pos.values()]
            pad = 0.2
            self.ax1.set_xlim(min(x_vals) - pad, max(x_vals) + pad)
            self.ax1.set_ylim(min(y_vals) - pad, max(y_vals) + pad)

        self.ax1.set_aspect('equal')
        self.ax1.axis('off')

        legend_elements = [
            Patch(facecolor='lime', label='Susceptible'),
            Patch(facecolor='salmon', label='Infected'),
            Patch(facecolor='darkgreen', label='Recovered'),
            Patch(facecolor='grey', label='Dead'),
            Patch(facecolor='blue', label='Vaccinated')
        ]
        self.ax1.legend(handles=legend_elements, loc='upper right', fontsize=8)
        self.fig1.tight_layout()

        buf_net = io.BytesIO()
        self.fig1.savefig(buf_net, format='png', dpi=80)
        buf_net.seek(0)
        net_url = f"data:image/png;base64,{base64.b64encode(buf_net.read()).decode('utf-8')}"
        buf_net.close()

        # Vykreslenie SIRD dynamiky
        self.ax2.cla()
        infected_counts = [sum(1 for s in h.values() if s == 1) for h in self.history]
        recovered_counts = [sum(1 for s in h.values() if s == 2) for h in self.history]
        dead_counts = [sum(1 for s in h.values() if s == 3) for h in self.history]

        self.ax2.plot(infected_counts, label='Infected', color='salmon')
        self.ax2.plot(recovered_counts, label='Recovered', color='darkgreen')
        self.ax2.plot(dead_counts, label='Dead', color='grey')
        self.ax2.set_xlabel("Iteration", fontsize=8)
        self.ax2.set_ylabel("People", fontsize=8)
        self.ax2.set_title("SIRD Dynamics (Fixed Infection Duration)", fontsize=9)
        self.ax2.legend(loc='upper right', fontsize=7)
        self.ax2.grid(True, linestyle='--', alpha=0.5)
        self.fig2.tight_layout()

        buf_dyn = io.BytesIO()
        self.fig2.savefig(buf_dyn, format='png', dpi=80)
        buf_dyn.seek(0)
        dyn_url = f"data:image/png;base64,{base64.b64encode(buf_dyn.read()).decode('utf-8')}"
        buf_dyn.close()

        i_count = sum(1 for s in self.status.values() if s == 1)
        r_count = sum(1 for s in self.status.values() if s == 2)
        d_count = sum(1 for s in self.status.values() if s == 3)
        h_count = self.num_people - (i_count + r_count + d_count)

        return {
            "healthy": h_count,
            "infected": i_count,
            "recovered": r_count,
            "dead": d_count,
            "vaccinated": len(self.vaccinated),
            "network_graph": net_url,
            "dynamics_graph": dyn_url,
            "is_finished": is_finished
        }

    def __del__(self):
        try:
            plt.close(self.fig1)
            plt.close(self.fig2)
        except Exception:
            pass