# functionality/osypky.py
import matplotlib
matplotlib.use('Agg')  # Vypne otváranie samostatných okien
import matplotlib.pyplot as plt
import networkx as nx
import random
import io
import base64
from matplotlib.patches import Patch, Wedge, Circle

colors = ['lime', 'salmon', 'darkgreen', 'grey']

def draw_infection_duration():
    return max(7, min(14, int(random.gauss(10, 2))))

class LiveSimulation:
    def __init__(self, num_people, transmission_probability, recovered_transmission_probability,
                 death_probability, contact_probability, vaccine_rate, vaccine_transmition):
        
        self.num_people = num_people
        self.vaccine_rate = vaccine_rate
        
        # Inicializácia siete
        self.G = nx.erdos_renyi_graph(num_people, contact_probability)
        self.status = {i: 0 for i in range(num_people)}
        self.infection_timer = {}

        # Očkovanie
        num_vaccinated = int(num_people * vaccine_rate)
        self.vaccinated = set(random.sample(list(self.status.keys()), num_vaccinated))

        # Pacient nula
        patient_zero = random.choice(list(self.status.keys()))
        self.status[patient_zero] = 1
        self.infection_timer[patient_zero] = draw_infection_duration()

        # Fixná pozícia uzlov
        self.pos = nx.spring_layout(self.G, k=1.5, iterations=100)

        # Štatistiky v čase
        self.infected_counts = []
        self.recovered_counts = []
        self.dead_counts = []
        self.iteration = 0

        # Tvoja nedotknutá funkcia šírenia
        self.death_probability = death_probability
        self.transmission_probability = transmission_probability
        self.vaccine_transmition = vaccine_transmition
        self.recovered_transmission_probability = recovered_transmission_probability

        # OBLASŤ PRE ZRYCHLENIE: Vytvoríme objekty grafov IBA RAZ pri štarte
        self.fig1, self.ax1 = plt.subplots(figsize=(7, 7))
        self.fig2, self.ax2 = plt.subplots(figsize=(6, 4))

    def spread_virus(self):
        # Úplne tvoja pôvodná logika, bez zmeny
        new_status = self.status.copy()
        for person in self.G.nodes:
            if self.status[person] == 3:
                continue
            if self.status[person] == 1:
                if random.random() < self.death_probability:
                    new_status[person] = 3
                    self.infection_timer.pop(person, None)
                    continue
                self.infection_timer[person] -= 1
                if self.infection_timer[person] <= 0:
                    new_status[person] = 2
                    self.infection_timer.pop(person, None)
                    continue
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
        return new_status

    def next_step(self):
        """Vykoná presne JEDEN krok simulácie a vráti aktuálny stav a grafy"""
        has_infected = sum(1 for s in self.status.values() if s == 1) > 0
        
        if has_infected or self.iteration == 0:
            if self.iteration > 0:
                self.status = self.spread_virus()
            
            self.infected_counts.append(sum(1 for s in self.status.values() if s == 1))
            self.recovered_counts.append(sum(1 for s in self.status.values() if s == 2))
            self.dead_counts.append(sum(1 for s in self.status.values() if s == 3))
            self.iteration += 1

        # 1. BLESKOVÉ PREKRESLENIE SIETE
        self.ax1.clear()
        nx.draw_networkx_edges(self.G, self.pos, ax=self.ax1, edge_color='#cbd5e1', width=0.5)

        r = 0.05
        for n in self.G.nodes:
            x, y = self.pos[n]
            s = self.status[n]
            if n in self.vaccinated:
                self.ax1.add_patch(Wedge((x, y), r, 0, 180, facecolor=colors[s]))
                self.ax1.add_patch(Wedge((x, y), r, 180, 360, facecolor="blue"))
                self.ax1.add_patch(Circle((x, y), r * 1.05, fill=False, edgecolor='blue', linewidth=2))
            else:
                self.ax1.add_patch(Circle((x, y), r, facecolor=colors[s], edgecolor='black'))

        self.ax1.set_aspect('equal')
        self.ax1.axis('off')
        self.ax1.set_title(f"SIRD Network Topology - Iteration {self.iteration}", fontsize=10)

        # Uloženie do stringu (pamäte)
        buf_net = io.BytesIO()
        self.fig1.savefig(buf_net, format='png', bbox_inches='tight', dpi=100)
        buf_net.seek(0)
        net_url = f"data:image/png;base64,{base64.b64encode(buf_net.read()).decode('utf-8')}"

        # 2. BLESKOVÉ PREKRESLENIE HISTORICKÉHO GRAFU
        self.ax2.clear()
        self.ax2.plot(self.infected_counts, label='Infected', color='salmon', linewidth=2)
        self.ax2.plot(self.recovered_counts, label='Recovered', color='darkgreen', linewidth=2)
        self.ax2.plot(self.dead_counts, label='Dead', color='grey', linewidth=2)
        self.ax2.set_xlabel("Iteration", fontsize=9)
        self.ax2.set_ylabel("People", fontsize=9)
        self.ax2.set_title("SIRD Dynamics", fontsize=10)
        self.ax2.legend(loc='upper right', fontsize=8)
        self.ax2.grid(True, linestyle='--', alpha=0.5)

        buf_dyn = io.BytesIO()
        self.fig2.savefig(buf_dyn, format='png', bbox_inches='tight', dpi=100)
        buf_dyn.seek(0)
        dyn_url = f"data:image/png;base64,{base64.b64encode(buf_dyn.read()).decode('utf-8')}"

        # Výpočty čísiel pre štatistiky
        final_infected = sum(1 for s in self.status.values() if s == 1)
        final_recovered = sum(1 for s in self.status.values() if s == 2)
        final_dead = sum(1 for s in self.status.values() if s == 3)
        final_healthy = self.num_people - (final_infected + final_recovered + final_dead)

        # Na konci už nezatvárame okná cez plt.close(), figúry recyklujeme!
        return {
            "healthy": final_healthy,
            "infected": final_infected,
            "recovered": final_recovered,
            "dead": final_dead,
            "vaccinated": len(self.vaccinated),
            "network_graph": net_url,
            "dynamics_graph": dyn_url,
            "is_finished": not has_infected and self.iteration > 1
        }