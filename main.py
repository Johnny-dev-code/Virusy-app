import webview
import os
import sys
from functionality.osypky import LiveSimulation
from functionality.saves_handling import (
    save_simulation,
    list_saved_simulations,
    load_simulation_file,
    render_saved_frame,
    resume_simulation_from_saved_step  # <--- 1. Pridaný import
)

def get_gui_path():
    """ Správne zistí cestu k složke gui pre vývoj aj po zbalení cez PyInstaller """
    if hasattr(sys, '_MEIPASS'):
        return os.path.join(sys._MEIPASS, 'gui', 'index.html')
    return os.path.join(os.path.dirname(__file__), 'gui', 'index.html')


class SimulationBridge:
    def __init__(self):
        self.active_sim = LiveSimulation() if hasattr(LiveSimulation, '__call__') else None
        self.loaded_replay = None

    # --- LIVE SIMULÁCIA ---
    def init_simulation(self, params):
        self.active_sim = LiveSimulation(params=params)
        return self.active_sim._generate_response(is_finished=False)

    def trigger_next_step(self):
        if self.active_sim:
            return self.active_sim.next_step()
        return {"error": "Simulácia nebola inicializovaná"}

    # --- UKLADANIE A PREHRÁVAČ ---
    def save_current_simulation(self):
        if self.active_sim:
            return save_simulation(self.active_sim)
        return {"status": "error", "message": "Žiadna aktívna simulácia na uloženie"}

    def get_saved_simulations(self):
        return list_saved_simulations()

    def load_replay(self, filename):
        replay_data = load_simulation_file(filename)
        if replay_data:
            self.loaded_replay = replay_data
            return {
                "status": "success",
                "max_steps": len(replay_data["history"]),
                "metadata": replay_data["metadata"]
            }
        return {"status": "error", "message": "Súbor sa nepodarilo načítať"}

    def render_replay_step(self, step):
        if not self.loaded_replay:
            return {"error": "Žiadny replay nie je načítaný"}

        try:
            step = int(step)
        except (ValueError, TypeError):
            return {"error": "Neplatný index kroku"}

        history = self.loaded_replay.get("history", [])
        metadata = self.loaded_replay.get("metadata", {})

        if 0 <= step < len(history):
            step_data = history[step]
            cumulative_history = history[:step + 1]
            return render_saved_frame(metadata, step_data, cumulative_history)
        
        return {"error": "Krok je mimo rozsahu"}

    # --- 2. NOVÁ METÓDA PRE JS BRIDGE ---
    def resume_simulation_from_saved_step(self, filename, step_index):
        # Ak aktívna simulácia neexistuje, vytvoríme novú inštanciu
        if not self.active_sim:
            self.active_sim = LiveSimulation()
            
        return resume_simulation_from_saved_step(self.active_sim, filename, step_index)


def main():
    api = SimulationBridge()
    gui_path = get_gui_path()
    
    window = webview.create_window(
        title='Epidemiological Network Model Simulation',
        url=gui_path, 
        js_api=api, 
        width=1200, 
        height=850, 
        resizable=True
    )
    webview.start()

if __name__ == '__main__':
    main()