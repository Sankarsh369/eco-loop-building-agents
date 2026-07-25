"""
Eco-Loop Building Agents — entry point.

Starts the closed-loop pipeline:
    EnergyPlus (simulation) --feedback--> LLM Agent (reasoning)
                              <--control actions--

Usage:
    python src/main.py --idf models/baseline.idf --steps 288
"""
import argparse
import os
import pandas as pd
from energyplus_wrapper import EnergyPlusWrapper
from llm_agent import LLMAgent

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the Eco-Loop closed-loop pipeline.")
    parser.add_argument("--idf", default="models/baseline.idf", help="Path to the EnergyPlus .idf building model.")
    parser.add_argument("--epw", default=None, help="Path to the EnergyPlus weather (.epw) file.")
    parser.add_argument("--steps", type=int, default=288, help="Cap on simulation timesteps (default 288 for 24h).")
    parser.add_argument("--heatwave", action="store_true", help="Run heatwave stress-test scenario.")
    return parser.parse_args()

def main() -> None:
    args = parse_args()
    os.makedirs("data", exist_ok=True)

    epw = "heatwave" if args.heatwave else args.epw

    print("=" * 60)
    print("⚡ ECO-LOOP BUILDING AGENTS: STARTING COMPARATIVE SIMULATION")
    print(f"IDF Model: {args.idf}")
    print(f"Simulation Steps: {args.steps}")
    print(f"Heatwave Stress-Test Active: {args.heatwave}")
    print("=" * 60)

    # 1. Run Baseline Simulation (Static setpoints: heating=21.5C, cooling=22.0C)
    print("\n[1/2] Running baseline simulation...")
    sim_baseline = EnergyPlusWrapper(idf_path=args.idf, epw_path=epw)
    # Ensure baseline uses standard static setpoints
    sim_baseline.zone_setpoints = {
        "Zone1": {
            "heating_setpoint": 21.5,
            "cooling_setpoint": 22.0
        }
    }
    
    baseline_telemetry = list(sim_baseline.stream_telemetry(max_steps=args.steps))
    sim_baseline.close()
    print("Baseline run completed.")

    # 2. Run AI Closed-Loop Simulation (Dynamic, carbon-aware comfort setpoints)
    print("\n[2/2] Running AI closed-loop simulation...")
    if args.heatwave:
        os.environ["HEATWAVE"] = "true"
    else:
        os.environ["HEATWAVE"] = "false"
        
    sim_ai = EnergyPlusWrapper(idf_path=args.idf, epw_path=epw)
    agent = LLMAgent()
    
    ai_telemetry = []
    # Dynamic loop
    for telemetry in sim_ai.stream_telemetry(max_steps=args.steps):
        # AI Agent decides control actions based on live telemetry feedback
        actions = agent.decide(telemetry)
        # Apply those actions to the simulation
        sim_ai.apply_control_actions(actions)
        ai_telemetry.append(telemetry)
        
    sim_ai.close()
    print("AI closed-loop run completed.")

    # 3. Combine and analyze results
    records = []
    total_baseline_energy = 0.0
    total_ai_energy = 0.0
    total_baseline_carbon = 0.0
    total_ai_carbon = 0.0
    baseline_comfort_violations = 0
    ai_comfort_violations = 0

    for idx in range(args.steps):
        bt = baseline_telemetry[idx]
        at = ai_telemetry[idx]

        # Calculate carbon emissions: intensity * energy
        b_carbon = bt.energy_consumption_kwh * bt.grid_carbon_intensity
        a_carbon = at.energy_consumption_kwh * at.grid_carbon_intensity

        total_baseline_energy += bt.energy_consumption_kwh
        total_ai_energy += at.energy_consumption_kwh
        total_baseline_carbon += b_carbon
        total_ai_carbon += a_carbon

        # Comfort band checks (-0.5 to 0.5) during occupied hours
        try:
            time_part = bt.timestamp.split()[1]
            h, m, _ = map(float, time_part.split(":"))
            hour = h + m / 60.0
            occupied = 7.0 <= hour <= 20.0
        except Exception:
            occupied = True
            
        if occupied:
            if bt.pmv_comfort_index < -0.5 or bt.pmv_comfort_index > 0.5:
                baseline_comfort_violations += 1
            if at.pmv_comfort_index < -0.5 or at.pmv_comfort_index > 0.5:
                ai_comfort_violations += 1

        records.append({
            "Step": idx + 1,
            "Timestamp": bt.timestamp,
            "Baseline Energy (kWh)": bt.energy_consumption_kwh,
            "AI Closed-Loop Energy (kWh)": at.energy_consumption_kwh,
            "Baseline Temp (°C)": bt.zone_temperatures["Zone1"],
            "AI Closed-Loop Temp (°C)": at.zone_temperatures["Zone1"],
            "Baseline PMV": bt.pmv_comfort_index,
            "AI PMV": at.pmv_comfort_index,
            "Carbon Intensity (gCO2/kWh)": bt.grid_carbon_intensity,
            "Baseline Carbon (g)": round(b_carbon, 2),
            "AI Carbon (g)": round(a_carbon, 2)
        })

    # Save to CSV
    df = pd.DataFrame(records)
    results_path = "data/simulation_results_heatwave.csv" if args.heatwave else "data/simulation_results.csv"
    df.to_csv(results_path, index=False)
    print(f"\nSaved simulation comparison results to: {results_path}")

    # 4. Print Summary Statistics
    energy_saved = ((total_baseline_energy - total_ai_energy) / total_baseline_energy) * 100
    carbon_saved = ((total_baseline_carbon - total_ai_carbon) / total_baseline_carbon) * 100
    
    print("\n" + "=" * 60)
    print("📊 SIMULATION SUMMARY & RESULTS")
    print("=" * 60)
    print(f"Total Baseline Energy:   {total_baseline_energy:,.2f} kWh")
    print(f"Total AI Closed-Loop:    {total_ai_energy:,.2f} kWh")
    print(f"Net Energy Savings:      {energy_saved:.2f}% (Target: > 25%)")
    print(f"Total Baseline Carbon:   {total_baseline_carbon/1000:,.2f} kg")
    print(f"Total AI Carbon:         {total_ai_carbon/1000:,.2f} kg")
    print(f"Net Carbon reduction:    {carbon_saved:.2f}%")
    print("-" * 60)
    print(f"Baseline Comfort Violations: {baseline_comfort_violations} steps")
    print(f"AI Comfort Violations:       {ai_comfort_violations} steps")
    print(f"Thermal Comfort Target Band: [-0.5, 0.5] PMV")
    print("=" * 60)

if __name__ == "__main__":
    main()
