from __future__ import annotations
import os
from energyplus_wrapper import ControlAction, Telemetry

SYSTEM_PROMPT = """\
You are a building energy optimization agent. Given live EnergyPlus
telemetry (zone temperatures, air quality, energy consumption, thermal
comfort index, peak demand, grid carbon intensity), decide whether any
zone set-points should change to reduce energy use and carbon impact
while keeping occupant comfort (PMV) within the target band of -0.5 to +0.5.
"""

class LLMAgent:
    def __init__(self, model: str = "llama3", comfort_band: tuple[float, float] = (-0.5, 0.5)):
        self.model = model
        self.comfort_band = comfort_band
        
        # In a real environment, we would initialize the client:
        # self.api_key = os.getenv("OPENAI_API_KEY")
        # self.client = ...

    def decide(self, telemetry: Telemetry) -> list[ControlAction]:
        """
        Evaluate telemetry and compute setpoint overrides.
        Prioritizes comfort boundary enforcement, and optimizes energy/carbon when comfortable.
        """
        actions = []
        
        # Parse hour from timestamp e.g. "2026-07-25 12:00:00" -> 12.0
        try:
            time_part = telemetry.timestamp.split()[1]
            h, m, _ = map(float, time_part.split(":"))
            hour = h + m / 60.0
        except Exception:
            hour = 12.0  # Fallback to midday
            
        for zone, temp in telemetry.zone_temperatures.items():
            pmv = telemetry.pmv_comfort_index
            carbon_intensity = telemetry.grid_carbon_intensity
            
            # Define occupancy schedule (Standard commercial office: occupied 7:00 AM - 8:00 PM)
            occupied = 7.0 <= hour <= 20.0
            preheating = 5.5 <= hour < 7.0
            
            # 1. Enforce strict thermal comfort boundaries (PMV limits) during occupied hours
            if occupied and pmv > self.comfort_band[1]:
                # Too warm! Force cooling to bring temperature down
                cooling_sp = 22.0
                heating_sp = 20.0
            elif occupied and pmv < self.comfort_band[0]:
                # Too cold! Force heating to bring temperature up
                heating_sp = 22.0
                cooling_sp = 24.0
            else:
                # 2. PMV is within comfort band: Optimize for Energy and Carbon
                if preheating:
                    # Morning warm-up preheating (5:30 AM to 7:00 AM)
                    # Gradually warm up the building so it's comfortable when occupants arrive
                    cooling_sp = 24.0
                    heating_sp = 21.5
                elif not occupied:
                    # Unoccupied hours night setback (8:00 PM to 5:30 AM)
                    # Set wider bands to minimize HVAC energy consumption
                    cooling_sp = 28.0
                    heating_sp = 16.0
                else:
                    # Occupied hours: Carbon-aware comfort optimization
                    if carbon_intensity > 340.0:
                        # High carbon intensity: slightly relax setpoints to shed load
                        cooling_sp = 24.5
                        heating_sp = 19.5
                    else:
                        # Low/moderate carbon intensity: prioritize occupant comfort deadband
                        cooling_sp = 22.5
                        heating_sp = 21.5
            
            actions.append(ControlAction(zone=zone, setpoint_type="cooling_setpoint", value=cooling_sp))
            actions.append(ControlAction(zone=zone, setpoint_type="heating_setpoint", value=heating_sp))
            
        return actions
