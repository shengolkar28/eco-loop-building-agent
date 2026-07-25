import streamlit as st
import json
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches

st.set_page_config(page_title="Eco-Loop Building Agent", layout="wide")
st.title("🏢 Eco-Loop Building Agent Dashboard")
st.markdown("**AI-driven closed-loop building energy optimization using EnergyPlus + LLM**")

# Load logs
with open(r'C:\Users\ASUS\ecoloop\agent_logs.json', 'r') as f:
    logs = json.load(f)

baseline = logs['baseline']
iterations = logs['iterations']

# Metrics
baseline_energy = baseline.get('total_site_energy_GJ', 0)
final_energy = iterations[-1]['metrics'].get('total_site_energy_GJ', 0)
saving_pct = round((baseline_energy - final_energy) / baseline_energy * 100, 2)

col1, col2, col3, col4 = st.columns(4)
col1.metric("Baseline Energy", f"{baseline_energy} GJ")
col2.metric("Final Energy", f"{final_energy} GJ")
col3.metric("Change", f"{saving_pct}%", delta=f"{saving_pct}%", delta_color="inverse")
col4.metric("Iterations", len(iterations))

st.divider()

# Energy over iterations
energies = [baseline_energy] + [it['metrics'].get('total_site_energy_GJ', 0) for it in iterations]
labels = ['Baseline'] + [f"Iter {it['iteration']}" for it in iterations]
heating_sps = [None] + [it['heating_setpoint'] for it in iterations]
cooling_sps = [None] + [it['cooling_setpoint'] for it in iterations]

col_left, col_right = st.columns(2)

with col_left:
    st.subheader("Total Site Energy per Iteration")
    fig, ax = plt.subplots(figsize=(7, 4))
    colors = ['#2196F3'] + ['#4CAF50' if e <= baseline_energy else '#F44336' for e in energies[1:]]
    bars = ax.bar(labels, energies, color=colors)
    ax.axhline(y=baseline_energy, color='orange', linestyle='--', label='Baseline')
    ax.set_ylabel("Energy (GJ)")
    ax.set_title("Site Energy Consumption")
    ax.legend()
    for bar, val in zip(bars, energies):
        ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 1,
                f'{val}', ha='center', va='bottom', fontsize=9)
    st.pyplot(fig)

with col_right:
    st.subheader("LLM Setpoint Decisions")
    fig2, ax2 = plt.subplots(figsize=(7, 4))
    itr_labels = [f"Iter {it['iteration']}" for it in iterations]
    h_vals = [it['heating_setpoint'] for it in iterations]
    c_vals = [it['cooling_setpoint'] for it in iterations]
    x = range(len(itr_labels))
    ax2.plot(itr_labels, h_vals, 'r-o', label='Heating Setpoint (°C)')
    ax2.plot(itr_labels, c_vals, 'b-o', label='Cooling Setpoint (°C)')
    ax2.set_ylabel("Temperature (°C)")
    ax2.set_title("AI-Recommended Setpoints per Iteration")
    ax2.legend()
    ax2.set_ylim(15, 32)
    st.pyplot(fig2)

st.divider()
st.subheader("Agent Reasoning Log")
for it in iterations:
    with st.expander(f"Iteration {it['iteration']} — Energy: {it['metrics'].get('total_site_energy_GJ','N/A')} GJ | Heating: {it['heating_setpoint']}°C | Cooling: {it['cooling_setpoint']}°C"):
        st.text(it['llm_response'])