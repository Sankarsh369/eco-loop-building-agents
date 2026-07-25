import json
import os
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("eco-loop-building-agents")

# Paths for inter-process communication
LIVE_STATE_PATH = "data/live_state.json"
CONTROL_ACTIONS_PATH = "data/control_actions.json"

@mcp.tool()
def read_simulation_log(path: str) -> str:
    """Read and return the tail of an EnergyPlus simulation log or results file (.err/.eso/.csv)."""
    if not os.path.exists(path):
        return f"Error: log file at '{path}' not found."
    try:
        with open(path, "r", encoding="utf-8") as f:
            lines = f.readlines()
        tail_lines = lines[-50:]  # Get the last 50 lines
        return "".join(tail_lines)
    except Exception as e:
        return f"Error reading log file: {str(e)}"

@mcp.tool()
def get_zone_telemetry(zone: str) -> dict:
    """Return the latest telemetry snapshot for a given zone from the live simulation."""
    if not os.path.exists(LIVE_STATE_PATH):
        return {"error": f"No active simulation state found. Ensure simulation is running."}
    
    try:
        with open(LIVE_STATE_PATH, "r") as f:
            state = json.load(f)
        
        # Verify zone is present in state
        if zone not in state.get("zone_temperatures", {}):
            return {"error": f"Zone '{zone}' not found in the latest telemetry snapshot. Available zones: {list(state.get('zone_temperatures', {}).keys())}"}
        
        # Return state
        return state
    except Exception as e:
        return {"error": f"Failed to read live state: {str(e)}"}

@mcp.tool()
def set_zone_setpoint(zone: str, setpoint_type: str, value: float) -> str:
    """Apply a new heating or cooling setpoint to a zone (forward injection into the running simulation)."""
    valid_setpoints = ["heating_setpoint", "cooling_setpoint"]
    if setpoint_type not in valid_setpoints:
        return f"Error: setpoint_type must be one of {valid_setpoints}"
        
    try:
        actions = []
        if os.path.exists(CONTROL_ACTIONS_PATH):
            try:
                with open(CONTROL_ACTIONS_PATH, "r") as f:
                    actions = json.load(f)
                    if not isinstance(actions, list):
                        actions = []
            except Exception:
                actions = []
                
        # Update setpoint if it already exists in the queue, else add new action
        updated = False
        for action in actions:
            if action.get("zone") == zone and action.get("setpoint_type") == setpoint_type:
                action["value"] = value
                updated = True
                break
                
        if not updated:
            actions.append({
                "zone": zone,
                "setpoint_type": setpoint_type,
                "value": value
            })
            
        # Write actions queue back to file
        os.makedirs(os.path.dirname(CONTROL_ACTIONS_PATH), exist_ok=True)
        with open(CONTROL_ACTIONS_PATH, "w") as f:
            json.dump(actions, f)
            
        return f"Successfully queued action: set {setpoint_type} to {value} in zone {zone}."
    except Exception as e:
        return f"Error applying control action: {str(e)}"

if __name__ == "__main__":
    mcp.run()
