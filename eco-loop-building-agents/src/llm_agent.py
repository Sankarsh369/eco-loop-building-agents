from __future__ import annotations
import os
import json
import sys
import openai
from energyplus_wrapper import ControlAction, Telemetry

# Route control decisions directly through the MCP Server tool functions
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
try:
    from mcp_server import set_zone_setpoint
except ImportError:
    set_zone_setpoint = None

SYSTEM_PROMPT = """\
You are an AI building energy optimization agent. You control the HVAC heating and cooling setpoints of a building zone to minimize energy consumption and grid carbon emissions while keeping occupants comfortable.
Occupant comfort is measured by the PMV (Predicted Mean Vote) index, which must stay within [-0.5, 0.5].
You have access to the tool `set_zone_setpoint` to adjust zone temperatures.

Comfort Rules:
- If PMV > 0.5 (too warm), you MUST cool the zone by lowering the cooling setpoint to 22.0.
- If PMV < -0.5 (too cold), you MUST heat the zone by raising the heating setpoint to 22.0.

Energy & Carbon Optimization Rules (when PMV is in-band):
- If grid carbon intensity is high (> 340.0 gCO2/kWh), you should perform load-shedding by relaxing setpoints (cooling to 24.5, heating to 19.5).
- If it is unoccupied night hours (8:00 PM to 5:30 AM), apply night setback (cooling to 28.0, heating to 16.0).
- If it is morning warm-up preheating (5:30 AM to 7:00 AM), set cooling to 24.0, heating to 21.5.
- During regular occupied hours, set cooling to 22.5, heating to 21.5.

Always output a tool call to set the setpoints.
"""

class LLMAgent:
    def __init__(self, model: str = "llama3", comfort_band: tuple[float, float] = (-0.5, 0.5)):
        self.model = model
        self.comfort_band = comfort_band
        
        # Configure OpenAI/Ollama client
        # Defaults to local Ollama instance but respects environment variables
        self.llm_active = os.getenv("LLM_ACTIVE", "false").lower() == "true" or os.getenv("OPENAI_API_KEY") is not None
        
        self.api_base = os.getenv("OPENAI_API_BASE", "http://localhost:11434/v1")
        self.api_key = os.getenv("OPENAI_API_KEY", "ollama")
        
        self.client = None
        if self.llm_active:
            try:
                self.client = openai.OpenAI(base_url=self.api_base, api_key=self.api_key)
            except Exception:
                self.client = None

    def decide(self, telemetry: Telemetry) -> list[ControlAction]:
        """
        Evaluate telemetry and compute setpoint overrides.
        Queries the LLM with tool definitions, and falls back to a deterministic rule-based agent if the LLM is unreachable.
        """
        actions = []
        
        # Parse hour from timestamp e.g. "2026-07-25 12:00:00" -> 12.0
        try:
            time_part = telemetry.timestamp.split()[1]
            h, m, _ = map(float, time_part.split(":"))
            hour = h + m / 60.0
        except Exception:
            hour = 12.0  # Fallback to midday
            
        # Determine rules-based fallback values first (used if LLM fails or is unreachable)
        fallback_actions = self._rule_based_decide(telemetry, hour)
        
        if self.client is None:
            return fallback_actions

        # Format prompt for the LLM
        prompt = f"""
        Timestamp: {telemetry.timestamp} (Hour: {hour:.2f})
        Zone Temperatures: {json.dumps(telemetry.zone_temperatures)}
        CO2 Levels: {json.dumps(telemetry.indoor_air_quality)}
        PMV Comfort Index: {telemetry.pmv_comfort_index}
        Grid Carbon Intensity: {telemetry.grid_carbon_intensity} gCO2/kWh
        Peak Demand: {telemetry.peak_demand_kw} kW
        """
        
        # Define the setpoint function tool schema
        tools = [
            {
                "type": "function",
                "function": {
                    "name": "set_zone_setpoint",
                    "description": "Apply a new heating or cooling setpoint to a building zone.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "zone": {"type": "string", "description": "Zone name (e.g., Zone1)"},
                            "setpoint_type": {"type": "string", "enum": ["heating_setpoint", "cooling_setpoint"]},
                            "value": {"type": "number", "description": "New setpoint temperature in degrees Celsius"}
                        },
                        "required": ["zone", "setpoint_type", "value"]
                    }
                }
            }
        ]

        try:
            # Query the LLM
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": prompt}
                ],
                tools=tools,
                tool_choice="auto",
                timeout=3.0  # short timeout to prevent blocking during tests
            )
            
            message = response.choices[0].message
            if message.tool_calls:
                for tool_call in message.tool_calls:
                    if tool_call.function.name == "set_zone_setpoint":
                        args = json.loads(tool_call.function.arguments)
                        
                        # Load-bearing MCP Tool Routing
                        if set_zone_setpoint is not None:
                            try:
                                set_zone_setpoint(
                                    zone=args["zone"],
                                    setpoint_type=args["setpoint_type"],
                                    value=args["value"]
                                )
                            except Exception as e:
                                print(f"Error calling MCP tool: {e}")
                                
                        actions.append(ControlAction(
                            zone=args["zone"],
                            setpoint_type=args["setpoint_type"],
                            value=args["value"]
                        ))
                
                # If we successfully parsed actions, return them
                if actions:
                    return actions
        except Exception:
            # Fall back silently to rule-based decisions if LLM is offline
            pass
            
        return fallback_actions

    def _rule_based_decide(self, telemetry: Telemetry, hour: float) -> list[ControlAction]:
        """Deterministic carbon-aware comfort rule engine fallback."""
        actions = []
        is_heatwave = os.getenv("HEATWAVE", "false").lower() == "true"
        for zone, temp in telemetry.zone_temperatures.items():
            pmv = telemetry.pmv_comfort_index
            carbon_intensity = telemetry.grid_carbon_intensity
            
            occupied = 7.0 <= hour <= 20.0
            preheating = 5.5 <= hour < 7.0
            
            # 1. Enforce strict thermal comfort boundaries (PMV limits) during occupied hours
            if occupied and pmv > self.comfort_band[1]:
                cooling_sp = 22.0
                heating_sp = 20.0
            elif occupied and pmv < self.comfort_band[0]:
                heating_sp = 22.0
                cooling_sp = 24.0
            else:
                # 2. PMV is within comfort band: Optimize for Energy and Carbon
                if preheating:
                    cooling_sp = 21.0 if is_heatwave else 24.0
                    heating_sp = 21.5
                elif not occupied:
                    cooling_sp = 28.0
                    heating_sp = 16.0
                else:
                    if carbon_intensity > 340.0:
                        cooling_sp = 24.5
                        heating_sp = 19.5
                    else:
                        cooling_sp = 22.5
                        heating_sp = 21.5
            
            # Load-bearing MCP Tool Routing for Fallback Engine
            if set_zone_setpoint is not None:
                try:
                    set_zone_setpoint(zone=zone, setpoint_type="cooling_setpoint", value=cooling_sp)
                    set_zone_setpoint(zone=zone, setpoint_type="heating_setpoint", value=heating_sp)
                except Exception:
                    pass

            actions.append(ControlAction(zone=zone, setpoint_type="cooling_setpoint", value=cooling_sp))
            actions.append(ControlAction(zone=zone, setpoint_type="heating_setpoint", value=heating_sp))
            
        return actions
