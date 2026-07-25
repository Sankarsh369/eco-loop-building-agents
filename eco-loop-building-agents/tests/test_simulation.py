import os
import sys

# Ensure src directory is in path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src")))

from energyplus_wrapper import EnergyPlusWrapper, ControlAction, Telemetry
from llm_agent import LLMAgent

def test_wrapper_thermodynamics():
    """Verify that setting heat/cool setpoints forces thermodynamic response."""
    sim = EnergyPlusWrapper(idf_path="models/baseline.idf")
    
    # 1. Force cooling
    sim.current_temp = 25.0
    sim.zone_setpoints = {
        "Zone1": {
            "heating_setpoint": 20.0,
            "cooling_setpoint": 21.0
        }
    }
    # Run 1 step
    telemetries = list(sim.stream_telemetry(max_steps=1))
    t = telemetries[0]
    
    # Indoor temp should cool down towards 21.0
    assert t.zone_temperatures["Zone1"] < 25.0
    assert t.energy_consumption_kwh > 0.15  # Should consume cooling energy

    # 2. Force heating
    sim.current_temp = 18.0
    sim.zone_setpoints = {
        "Zone1": {
            "heating_setpoint": 21.0,
            "cooling_setpoint": 22.0
        }
    }
    telemetries = list(sim.stream_telemetry(max_steps=1))
    t2 = telemetries[0]
    
    # Indoor temp should heat up towards 21.0
    assert t2.zone_temperatures["Zone1"] > 18.0
    assert t2.energy_consumption_kwh > 0.15  # Should consume heating energy

def test_agent_decisions():
    """Verify LLM Agent adjusts setpoints dynamically in response to comfort boundaries."""
    agent = LLMAgent()
    
    # Case A: Too Hot (PMV = 0.8 > 0.5) -> Cool down
    t_hot = Telemetry(
        timestamp="2026-07-25 14:00:00",
        zone_temperatures={"Zone1": 24.5},
        indoor_air_quality={"CO2_ppm": 450.0},
        energy_consumption_kwh=0.5,
        pmv_comfort_index=0.8,
        peak_demand_kw=6.0,
        grid_carbon_intensity=300.0
    )
    actions = agent.decide(t_hot)
    
    # cooling setpoint should be set to 22.0 to cool down
    cooling_sp = [a.value for a in actions if a.setpoint_type == "cooling_setpoint"][0]
    assert cooling_sp == 22.0

    # Case B: Too Cold (PMV = -0.7 < -0.5) -> Heat up
    t_cold = Telemetry(
        timestamp="2026-07-25 08:00:00",
        zone_temperatures={"Zone1": 19.5},
        indoor_air_quality={"CO2_ppm": 450.0},
        energy_consumption_kwh=0.5,
        pmv_comfort_index=-0.7,
        peak_demand_kw=6.0,
        grid_carbon_intensity=300.0
    )
    actions_cold = agent.decide(t_cold)
    
    # heating setpoint should be set to 22.0 to heat up
    heating_sp = [a.value for a in actions_cold if a.setpoint_type == "heating_setpoint"][0]
    assert heating_sp == 22.0

    # Case C: High Grid Carbon Intensity (PMV = 0.1, Carbon = 380) -> Load shedding (relax setpoints)
    t_peak = Telemetry(
        timestamp="2026-07-25 17:00:00",
        zone_temperatures={"Zone1": 22.2},
        indoor_air_quality={"CO2_ppm": 450.0},
        energy_consumption_kwh=0.3,
        pmv_comfort_index=0.1,
        peak_demand_kw=3.6,
        grid_carbon_intensity=380.0
    )
    actions_peak = agent.decide(t_peak)
    
    cool_sp_peak = [a.value for a in actions_peak if a.setpoint_type == "cooling_setpoint"][0]
    heat_sp_peak = [a.value for a in actions_peak if a.setpoint_type == "heating_setpoint"][0]
    
    # Setpoints should widen (cooling = 24.5, heating = 19.5) to avoid energy consumption
    assert cool_sp_peak == 24.5
    assert heat_sp_peak == 19.5

def test_closed_loop_savings():
    """Verify that running closed-loop optimization achieves energy savings compared to baseline."""
    # Run baseline (static)
    sim_baseline = EnergyPlusWrapper(idf_path="models/baseline.idf")
    sim_baseline.zone_setpoints = {
        "Zone1": {
            "heating_setpoint": 21.5,
            "cooling_setpoint": 22.0
        }
    }
    baseline_telemetry = list(sim_baseline.stream_telemetry(max_steps=100))
    sim_baseline.close()
    
    total_baseline_energy = sum(t.energy_consumption_kwh for t in baseline_telemetry)

    # Run AI closed-loop
    sim_ai = EnergyPlusWrapper(idf_path="models/baseline.idf")
    agent = LLMAgent()
    ai_telemetry = []
    
    for t in sim_ai.stream_telemetry(max_steps=100):
        actions = agent.decide(t)
        sim_ai.apply_control_actions(actions)
        ai_telemetry.append(t)
    sim_ai.close()
    
    total_ai_energy = sum(t.energy_consumption_kwh for t in ai_telemetry)
    
    # Calculate savings
    savings = (total_baseline_energy - total_ai_energy) / total_baseline_energy
    
    print(f"Baseline Energy: {total_baseline_energy:.2f} kWh, AI Energy: {total_ai_energy:.2f} kWh, Savings: {savings*100:.2f}%")
    
    # Verify significant energy savings (should be > 20%)
    assert savings > 0.20
