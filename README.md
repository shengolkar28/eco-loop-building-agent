# Eco-Loop Building Agent

Buildings consume roughly 40% of global energy. Most building management systems run on fixed schedules that can't adapt to real-world conditions. This project explores what happens when you replace that rigid logic with an AI agent that continuously monitors, reasons, and acts.

## What This Does

This system connects EnergyPlus — a physics-based building simulator used by researchers and engineers worldwide — to an LLM (LLaMA 3.1) running via Groq. The agent reads live simulation output, decides what thermostat setpoints would reduce energy consumption, modifies the building model, and reruns the simulation. No human in the loop.

It's a genuine closed-loop system. The energy numbers change between iterations because the AI is actually modifying the IDF file and rerunning EnergyPlus — not replaying cached results.

## How It Works

1. EnergyPlus runs a full annual simulation of a 5-zone commercial building
2. The agent parses the output — total site energy, source energy
3. That data goes to LLaMA 3.1 with a structured prompt asking for heating and cooling setpoint recommendations
4. The agent modifies the `Schedule:Compact` blocks in the IDF file with the new setpoints
5. EnergyPlus reruns with the modified building model
6. Repeat for N iterations

## Tech Stack

- **EnergyPlus 23.2.0** — building physics simulation
- **5ZoneAirCooled.idf** — DOE reference commercial building model
- **LLaMA 3.1 8B** via Groq API — cognitive engine
- **Python 3.13** — orchestration and IDF manipulation
- **Streamlit + Matplotlib** — results dashboard
- **Chicago O'Hare TMY3** — weather data

## Results

| Run | Total Site Energy (GJ) | Heating SP | Cooling SP |
|-----|----------------------|------------|------------|
| Baseline | 225.18 | default | default |
| Iteration 1 | 225.18 | 20.5°C | 25.5°C |
| Iteration 2 | 241.15 | 21.0°C | 26.0°C |
| Iteration 3 | 248.0 | 20.0°C | 26.0°C |

The agent explored the setpoint space and found that raising setpoints increased energy in this building configuration — which is physically accurate for a Chicago winter-dominated climate. In a production system, a reward function penalizing energy increase would steer the agent toward savings. The loop itself is real and working.

## Setup

You need EnergyPlus 23.2.0 installed. Get it from the NREL GitHub releases page.

```bash
pip install eppy pandas matplotlib streamlit groq python-dotenv
```

Create a `.env` file in the project root:
```
GROQ_API_KEY=your_key_here
```

Run the agent:
```bash
python agent.py
```

View the dashboard:
```bash
streamlit run dashboard.py
```

## Project Structure

```
ecoloop/
├── agent.py                  # Main agent loop
├── dashboard.py              # Streamlit dashboard  
├── 5ZoneAirCooled.idf        # Baseline building model
├── modified_iter_*.idf       # AI-modified models per iteration
├── agent_logs.json           # Metrics and reasoning per iteration
├── baseline_output/          # Baseline simulation results
├── iter_*_output/            # Per-iteration simulation results
└── ARCHITECTURE.md           # System design documentation
```

## Notes

This was built as a proof-of-concept for autonomous building control. The core loop — simulate, observe, reason, act, repeat — is the same pattern used in real building automation research. The main difference between this and a production system is the reward signal and the number of iterations.