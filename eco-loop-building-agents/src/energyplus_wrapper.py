import random
import math
import json
import os
from dataclasses import dataclass
from typing import Iterator

@dataclass
class Telemetry:
    timestamp: str
    zone_temperatures: dict
    indoor_air_quality: dict
    energy_consumption_kwh: float
    pmv_comfort_index: float
    peak_demand_kw: float
    grid_carbon_intensity: float

@dataclass
class ControlAction:
    zone: str
    setpoint_type: str  # e.g., "cooling_setpoint", "heating_setpoint"
    value: float

class EnergyPlusWrapper:
    def __init__(self, idf_path: str, epw_path: str | None = None):
        self.idf_path = idf_path
        self.epw_path = epw_path
        
        # Default comfort setpoints
        self.zone_setpoints = {
            "Zone1": {
                "heating_setpoint": 21.0,
                "cooling_setpoint": 23.0
            }
        }
        
        # Simulation internal state variables
        self.current_temp = 21.5
        self.co2_ppm = 450.0
        self.humidity = 50.0
        
        # Paths for MCP Server tool IPC
        os.makedirs("data", exist_ok=True)
        self.live_state_path = "data/live_state.json"
        self.control_actions_path = "data/control_actions.json"
        
        # Reset files
        if os.path.exists(self.control_actions_path):
            os.remove(self.control_actions_path)

    def stream_telemetry(self, max_steps: int | None = 288) -> Iterator[Telemetry]:
        """
        Simulate building thermodynamics timestep by timestep.
        Supports dynamic setpoint modification during simulation.
        Default max_steps is 288 steps (24 hours at 5-minute intervals).
        """
        steps = max_steps if max_steps is not None else 288
        
        for i in range(steps):
            # 1. Process control updates from MCP tools (Inter-process Communication)
            if os.path.exists(self.control_actions_path):
                try:
                    with open(self.control_actions_path, "r") as f:
                        actions_data = json.load(f)
                    # Convert list of dicts to ControlAction
                    actions = [
                        ControlAction(
                            zone=act["zone"],
                            setpoint_type=act["setpoint_type"],
                            value=act["value"]
                        )
                        for act in actions_data
                    ]
                    self.apply_control_actions(actions)
                    # Delete the file to consume actions
                    os.remove(self.control_actions_path)
                except Exception:
                    pass

            # 2. Time parameters (diurnal cycle)
            hour = (12.0 + (i * 5.0 / 60.0)) % 24.0
            minute = (i * 5) % 60
            timestamp = f"2026-07-25 {int(hour):02d}:{int(minute):02d}:00"

            # 3. Simulate outdoor temperature (peak in afternoon, cool at night)
            outdoor_temp = 18.0 + 8.0 * math.sin(math.pi * (hour - 8.0) / 12.0)

            # 4. Simulate indoor air quality (CO2 ppm)
            # Standard breathing increases CO2, ventilation clears it
            co2_generation = 15.0  # CO2 increase rate per step (occupancy)
            vent_rate = 0.08  # Air change rate
            self.co2_ppm = max(400.0, self.co2_ppm + co2_generation - vent_rate * (self.co2_ppm - 400.0))

            # 5. Simulate building thermodynamics & HVAC loads
            heating_setpoint = self.zone_setpoints["Zone1"].get("heating_setpoint", 21.0)
            cooling_setpoint = self.zone_setpoints["Zone1"].get("cooling_setpoint", 23.0)
            
            # Natural thermal heat transfer through envelope (U-value effect)
            envelope_heat_gain = 0.05 * (outdoor_temp - self.current_temp)
            self.current_temp += envelope_heat_gain

            heating_energy = 0.0
            cooling_energy = 0.0
            
            # Active conditioning
            if self.current_temp < heating_setpoint:
                # Heating turns on
                heating_load = heating_setpoint - self.current_temp
                heating_input = heating_load * 0.4
                self.current_temp += heating_input
                heating_energy = heating_input * 2.2  # HVAC heating COP factor
            elif self.current_temp > cooling_setpoint:
                # Cooling turns on
                cooling_load = self.current_temp - cooling_setpoint
                cooling_input = cooling_load * 0.4
                self.current_temp -= cooling_input
                cooling_energy = cooling_input * 1.8  # HVAC cooling COP factor

            # Base system power (auxiliary fans, lights, etc.)
            base_power = 0.15
            energy_consumption_kwh = heating_energy + cooling_energy + base_power
            
            # 6. PMV comfort index calculation (approximate Fanger model)
            # Comfort targets 21.5 - 22.5 C where PMV is close to 0
            pmv_comfort = 0.18 * (self.current_temp - 22.0) + random.uniform(-0.01, 0.01)
            # Clip PMV to realistic bounds (-3 to +3)
            pmv_comfort = max(-3.0, min(3.0, pmv_comfort))

            # 7. Demand & grid carbon intensity
            peak_kw = energy_consumption_kwh * 12.0  # Instantaneous power scaling (5 min step)
            grid_carbon_intensity = 300.0 + 120.0 * math.sin(math.pi * (hour - 14.0) / 12.0)

            telemetry = Telemetry(
                timestamp=timestamp,
                zone_temperatures={"Zone1": round(self.current_temp, 2)},
                indoor_air_quality={"CO2_ppm": round(self.co2_ppm, 1)},
                energy_consumption_kwh=round(energy_consumption_kwh, 3),
                pmv_comfort_index=round(pmv_comfort, 3),
                peak_demand_kw=round(peak_kw, 2),
                grid_carbon_intensity=round(grid_carbon_intensity, 1)
            )

            # 8. Export live state to JSON file for MCP Tool access
            state_data = {
                "timestamp": telemetry.timestamp,
                "zone_temperatures": telemetry.zone_temperatures,
                "indoor_air_quality": telemetry.indoor_air_quality,
                "energy_consumption_kwh": telemetry.energy_consumption_kwh,
                "pmv_comfort_index": telemetry.pmv_comfort_index,
                "peak_demand_kw": telemetry.peak_demand_kw,
                "grid_carbon_intensity": telemetry.grid_carbon_intensity,
                "active_setpoints": self.zone_setpoints["Zone1"]
            }
            try:
                with open(self.live_state_path, "w") as f:
                    json.dump(state_data, f)
            except Exception:
                pass

            yield telemetry

    def apply_control_actions(self, actions: list[ControlAction]) -> None:
        """Apply setpoint modifications to the active building zones."""
        for action in actions:
            zone = action.zone
            sp_type = action.setpoint_type
            val = action.value
            
            if zone not in self.zone_setpoints:
                self.zone_setpoints[zone] = {}
            
            # Apply setpoint restrictions to avoid invalid states
            if sp_type == "heating_setpoint":
                # Ensure heating setpoint is not higher than cooling setpoint (deadband constraint)
                cool_sp = self.zone_setpoints[zone].get("cooling_setpoint", 23.0)
                self.zone_setpoints[zone]["heating_setpoint"] = min(val, cool_sp - 0.5)
            elif sp_type == "cooling_setpoint":
                heat_sp = self.zone_setpoints[zone].get("heating_setpoint", 21.0)
                self.zone_setpoints[zone]["cooling_setpoint"] = max(val, heat_sp + 0.5)

    def close(self) -> None:
        """Cleanup live state file handles."""
        if os.path.exists(self.live_state_path):
            try:
                os.remove(self.live_state_path)
            except Exception:
                pass
