"""
MCP Server — Eco-Loop tool definitions
=======================================
Exposes agentic tools to the LLM via the Model Context Protocol so it can
parse simulation files, extract runtime errors, and apply control actions
without manual code changes.

Run standalone for local testing:
    python src/mcp_server.py
"""
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("eco-loop-building-agents")


@mcp.tool()
def read_simulation_log(path: str) -> str:
    """Read and return the tail of an EnergyPlus simulation log (.err/.eso)."""
    # TODO: implement log parsing / error extraction
    raise NotImplementedError


@mcp.tool()
def get_zone_telemetry(zone: str) -> dict:
    """Return the latest telemetry snapshot for a given zone."""
    # TODO: pull from the running EnergyPlusWrapper instance / shared state
    raise NotImplementedError


@mcp.tool()
def set_zone_setpoint(zone: str, setpoint_type: str, value: float) -> str:
    """Apply a new set-point to a zone (forward injection into EnergyPlus)."""
    # TODO: route to EnergyPlusWrapper.apply_control_actions
    raise NotImplementedError


if __name__ == "__main__":
    mcp.run()
