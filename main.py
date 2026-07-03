# main.py
import webview
import os
from functionality.osypky import LiveSimulation

class SimulationBridge:
    def __init__(self):
        self.active_sim = None

    def init_simulation(self, params):
        """Inicializuje novú simuláciu s poslanými premennými"""
        self.active_sim = LiveSimulation(
            params["num_people"], params["transmission_probability"],
            params["recovered_transmission_probability"], params["death_probability"],
            params["contact_probability"], params["vaccine_rate"], params["vaccine_transmition"]
        )
        return {"status": "initialized"}

    def trigger_next_step(self):
        """Spustí jeden krok a vráti dáta pre GUI"""
        if self.active_sim:
            return self.active_sim.next_step()
        return {"error": "Simulácia nebola inicializovaná"}

def main():
    api = SimulationBridge()
    gui_dir = os.path.join(os.path.dirname(__file__), 'gui', 'index.html')
    window = webview.create_window(
        title='Epidemiological Network Model Simulation',
        url=gui_dir, js_api=api, width=1200, height=850, resizable=True
    )
    webview.start()

if __name__ == '__main__':
    main()