import os
import subprocess
import pandas as pd
import shutil
import re
from groq import Groq
from dotenv import load_dotenv

load_dotenv()
groq_client = Groq(api_key="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")

ENERGYPLUS_PATH = r"C:\EnergyPlusV23-2-0\EnergyPlus.exe"
IDF_FILE = r"C:\Users\ASUS\ecoloop\5ZoneAirCooled.idf"
EPW_FILE = r"C:\Users\ASUS\ecoloop\USA_IL_Chicago-OHare.Intl.AP.725300_TMY3.epw"
OUTPUT_DIR = r"C:\Users\ASUS\ecoloop\output"
BASELINE_DIR = r"C:\Users\ASUS\ecoloop\baseline_output"


def run_energyplus(idf_path, output_dir):
    """Run EnergyPlus simulation"""
    os.makedirs(output_dir, exist_ok=True)
    # Delete stale output files
    for f in ['eplustbl.csv', 'eplusout.csv', 'eplustbl.tab']:
        fp = os.path.join(output_dir, f)
        if os.path.exists(fp):
            os.remove(fp)
    cmd = [
        ENERGYPLUS_PATH,
        "-w", EPW_FILE,
        "-d", output_dir,
        idf_path
    ]
    print(f"Running EnergyPlus simulation...")
    result = subprocess.run(cmd, capture_output=True, text=True)
    if "EnergyPlus Completed Successfully" in result.stdout or "EnergyPlus Run Time" in result.stdout:
        print("Simulation completed successfully.")
        return True
    else:
        print("Simulation failed.")
        print(result.stdout[-2000:])
        return False

def read_results(output_dir):
    """Read EnergyPlus HTML output"""
    htm_file = os.path.join(output_dir, "eplustbl.htm")
    if not os.path.exists(htm_file):
        print(f"No eplustbl.htm found at {htm_file}")
        return None
    with open(htm_file, 'r', encoding='utf-8', errors='ignore') as f:
        content = f.read()
    return content

def summarize_results(content):
    """Extract key metrics from eplustbl.htm"""
    summary = {}
    if content is None:
        return {'note': 'No output file'}
    
    import re
    
    patterns = {
        'total_site_energy_GJ': r'Total Site Energy</td>\s*<td[^>]*>\s*([\d.]+)</td>',
        'total_source_energy_GJ': r'Total Source Energy</td>\s*<td[^>]*>\s*([\d.]+)</td>',
        'net_site_energy_GJ': r'Net Site Energy</td>\s*<td[^>]*>\s*([\d.]+)</td>',
    }
    
    for key, pattern in patterns.items():
        match = re.search(pattern, content, re.DOTALL)
        if match:
            summary[key] = float(match.group(1))

    if not summary:
        summary['note'] = 'Could not extract metrics'
    
    return summary

def get_llm_recommendation(summary, iteration):
    """Ask Claude to recommend setpoint adjustments"""
    prompt = f"""
You are an AI building energy optimization agent controlling a single-zone building via EnergyPlus simulation.

Current simulation results (iteration {iteration}):
{summary}

Your goals:
1. Reduce total energy consumption (kWh)
2. Maintain zone temperature between 20-26°C for occupant comfort
3. Suggest specific thermostat setpoint changes

Based on these metrics, recommend:
- Heating setpoint (°C) — typical range 18-22°C
- Cooling setpoint (°C) — typical range 24-28°C  
- Brief reasoning (2-3 sentences max)
- Expected energy saving (%)

Respond in this exact format:
HEATING_SETPOINT: <value>
COOLING_SETPOINT: <value>
REASONING: <text>
EXPECTED_SAVING: <percentage>
"""
    response = groq_client.chat.completions.create(
        model="llama-3.1-8b-instant",
        messages=[{"role": "user", "content": prompt}],
        max_tokens=300
    )
    return response.choices[0].message.content

def parse_setpoints(llm_response):
    """Parse LLM response for setpoint values"""
    heating = 20.0
    cooling = 26.0
    try:
        h_match = re.search(r"HEATING_SETPOINT:\s*([\d.]+)", llm_response)
        c_match = re.search(r"COOLING_SETPOINT:\s*([\d.]+)", llm_response)
        if h_match:
            heating = float(h_match.group(1))
        if c_match:
            cooling = float(c_match.group(1))
    except:
        pass
    return heating, cooling

def modify_idf(heating_sp, cooling_sp, iteration):
    """Modify IDF setpoints by directly editing named schedule blocks"""
    modified_idf = os.path.join(r"C:\Users\ASUS\ecoloop", f"modified_iter_{iteration}.idf")
    
    with open(IDF_FILE, 'r') as f:
        content = f.read()
    
    import re

    def replace_schedule_temps(text, schedule_name, new_temp):
        # Find the Schedule:Compact block with this name
        pattern = re.compile(
            r'(Schedule:Compact,\s*' + re.escape(schedule_name) + r'\s*,.*?;)',
            re.DOTALL | re.IGNORECASE
        )
        match = pattern.search(text)
        if not match:
            print(f"WARNING: Schedule '{schedule_name}' not found")
            return text
        block = match.group(1)
        # Replace all 'Until: HH:MM, VALUE' temperature entries
        new_block = re.sub(
            r'(Until:\s*\d+:\d+\s*,\s*)([-\d.]+)',
            lambda m: m.group(1) + str(new_temp),
            block
        )
        print(f"Updated schedule '{schedule_name}' -> {new_temp}°C")
        return text[:match.start()] + new_block + text[match.end():]

    content = replace_schedule_temps(content, 'Htg-SetP-Sch', heating_sp)
    content = replace_schedule_temps(content, 'Clg-SetP-Sch', cooling_sp)

    with open(modified_idf, 'w') as f:
        f.write(content)

    print(f"Modified IDF saved: {modified_idf}")
    return modified_idf

def run_baseline():
    """Run baseline simulation"""
    print("\n=== RUNNING BASELINE SIMULATION ===")
    success = run_energyplus(IDF_FILE, BASELINE_DIR)
    if success:
        df = read_results(BASELINE_DIR)
        if df is not None:
            return summarize_results(df)
    return {}

def main():
    print("=" * 50)
    print("ECO-LOOP BUILDING AGENT STARTING")
    print("=" * 50)

    # Step 1: Run baseline
    baseline = run_baseline()
    print(f"\nBaseline metrics: {baseline}")

    # Step 2: Closed loop iterations
    logs = []
    current_idf = IDF_FILE
    iterations = 3

    for i in range(1, iterations + 1):
        print(f"\n=== ITERATION {i}/{iterations} ===")

        # Run simulation
        iter_output = os.path.join(r"C:\Users\ASUS\ecoloop", f"iter_{i}_output")
        success = run_energyplus(current_idf, iter_output)

        if not success:
            print(f"Iteration {i} failed, stopping.")
            break

        # Read results
        df = read_results(iter_output)
        if df is None:
            break

        summary = summarize_results(df)
        print(f"Metrics: {summary}")

        # Get LLM recommendation
        print("Querying Claude for optimization recommendations...")
        llm_response = get_llm_recommendation(summary, i)
        print(f"\nClaude says:\n{llm_response}")

        # Parse setpoints
        heating_sp, cooling_sp = parse_setpoints(llm_response)
        print(f"\nNew setpoints -> Heating: {heating_sp}°C, Cooling: {cooling_sp}°C")

        # Log everything
        logs.append({
            "iteration": i,
            "metrics": summary,
            "llm_response": llm_response,
            "heating_setpoint": heating_sp,
            "cooling_setpoint": cooling_sp
        })

        # Modify IDF for next iteration
        current_idf = modify_idf(heating_sp, cooling_sp, i)

    # Step 3: Save logs
    import json
    with open(r"C:\Users\ASUS\ecoloop\agent_logs.json", "w") as f:
        json.dump({"baseline": baseline, "iterations": logs}, f, indent=2)

    print("\n=== AGENT RUN COMPLETE ===")
    print(f"Baseline: {baseline}")
    if logs:
        print(f"Final iteration metrics: {logs[-1]['metrics']}")
    print("Logs saved to agent_logs.json")

if __name__ == "__main__":
    main()