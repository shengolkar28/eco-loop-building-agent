# System Architecture — Eco-Loop Building Agent

## The Problem

Traditional Building Management Systems run on fixed schedules. They don't adapt to occupancy changes, weather shifts, or grid conditions. This project replaces that static logic with an AI agent that observes, reasons, and acts in a continuous loop.

## High-Level Design

```
┌─────────────────────────────────────────────────────┐
│                  CLOSED LOOP PIPELINE               │
│                                                     │
│   ┌─────────────┐   metrics    ┌──────────────┐    │
│   │  EnergyPlus │ ──────────▶  │  LLM Agent   │    │
│   │  Simulation │              │ (LLaMA 3.1)  │    │
│   └─────────────┘ ◀──────────  └──────────────┘    │
│          ▲          setpoints          │             │
│          │                            ▼             │
│   Modified .idf ◀──── IDF Editor ◀───┘             │
└─────────────────────────────────────────────────────┘
```

## Components

### 1. Simulation Engine — EnergyPlus 23.2.0

EnergyPlus is an open-source building energy simulation engine developed by the US Department of Energy. It models heat transfer, HVAC systems, lighting, and occupancy across full annual weather cycles.

- **Building model**: 5ZoneAirCooled — a DOE reference commercial building with a VAV air-cooled system
- **Weather file**: Chicago O'Hare TMY3 (EPW format)
- **Python interface**: `subprocess` wrapper captures stdout, detects completion, reads output files
- **Key output**: `eplustbl.htm` — parsed with regex to extract site and source energy in GJ

### 2. Cognitive Engine — LLaMA 3.1 8B via Groq

The LLM acts as the decision-making layer. It receives simulation metrics and returns structured setpoint recommendations.

**Prompt strategy:**
- Metrics injected per iteration (site energy, source energy)
- Hard constraints specified: heating 18-22°C, cooling 24-28°C, comfort zone 20-26°C
- Structured output enforced: `HEATING_SETPOINT`, `COOLING_SETPOINT`, `REASONING`, `EXPECTED_SAVING`
- Regex parser extracts numeric values from response

**Why Groq:** Low latency (~300ms), free tier, runs LLaMA 3.1 without local GPU requirement — critical for a Celeron-class machine.

### 3. IDF Modification Layer

The IDF (Input Data File) is EnergyPlus's building description format. Setpoints are defined as `Schedule:Compact` objects.

Target schedules identified in `5ZoneAirCooled.idf`:
- `Htg-SetP-Sch` — heating setpoint schedule
- `Clg-SetP-Sch` — cooling setpoint schedule

The agent modifies `Until: HH:MM, VALUE` entries in these blocks using regex substitution, writes a new `.idf` file per iteration, and feeds it into the next simulation run.

### 4. Tool-Calling Architecture

Rather than a full MCP server, the agent uses direct Python function calls as tools — functionally equivalent for a single-agent system:

| Tool | Function | Purpose |
|------|----------|---------|
| `run_energyplus()` | Subprocess call | Execute simulation |
| `read_results()` | HTML parser | Extract metrics |
| `summarize_results()` | Regex | Structure data for LLM |
| `get_llm_recommendation()` | Groq API call | LLM reasoning |
| `parse_setpoints()` | Regex | Extract setpoints from LLM response |
| `modify_idf()` | File editor | Inject setpoints into building model |

### 5. Prompt Latency Management

Long simulation logs are never passed to the LLM. Only the summarized metrics dictionary is injected — keeping prompt size under 500 tokens and response time under 1 second.

Per-iteration timing:
- EnergyPlus simulation: ~28 seconds
- HTML parsing: <1 second
- Groq LLM call: ~300ms
- IDF modification: <1 second
- **Total per iteration: ~30 seconds**

### 6. Dashboard

Built with Streamlit and Matplotlib. Reads `agent_logs.json` after agent completes.

Displays:
- Baseline vs AI energy consumption (bar chart)
- Setpoint trajectory across iterations (line chart)
- Per-iteration LLM reasoning log (expandable)

## Data Flow

```
agent.py starts
    │
    ├── run_energyplus(baseline IDF) 
    │       └── writes baseline_output/eplustbl.htm
    │
    ├── read_results() + summarize_results()
    │       └── extracts {total_site_energy_GJ, total_source_energy_GJ}
    │
    └── for each iteration:
            ├── run_energyplus(current IDF)
            ├── read_results() → metrics
            ├── get_llm_recommendation(metrics) → LLM response
            ├── parse_setpoints() → heating_sp, cooling_sp
            ├── modify_idf() → new .idf file
            └── log everything to agent_logs.json
```

## Limitations and Future Work

- **Reward signal**: Currently the LLM has no memory of previous energy values across iterations. Adding a delta-energy signal in the prompt would drive consistent optimization.
- **Setpoint granularity**: Only heating and cooling setpoints are modified. Ventilation rates, lighting schedules, and occupancy patterns are additional control levers.
- **Real-time co-simulation**: BCVTB or PyEnergyPlus's runtime API would enable true timestep-level control rather than full annual reruns.
- **Multi-agent**: Separate agents per zone with a coordinator could optimize zone-level comfort vs energy tradeoffs.
```
