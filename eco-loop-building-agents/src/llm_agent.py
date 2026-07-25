"""
LLMAgent
========
Cognitive engine: evaluates EnergyPlus telemetry against comfort/energy
targets and computes Energy Conservation Measures (ECMs) as control actions.

Deploy any modern open-source LLM (Llama 3, Mistral, Qwen, ...) running
locally (e.g. via Ollama) or behind a self-hosted API, and route its tool
calls through the MCP server defined in `mcp_server.py`.
"""
from __future__ import annotations

from energyplus_wrapper import ControlAction, Telemetry

SYSTEM_PROMPT = """\
You are a building energy optimization agent. Given live EnergyPlus
telemetry (zone temperatures, air quality, energy consumption, thermal
comfort index, peak demand, grid carbon intensity), decide whether any
zone set-points should change to reduce energy use and carbon impact
while keeping occupant comfort (PMV) within the target band.
Use the available MCP tools to inspect logs and apply set-point changes.
"""


class LLMAgent:
    def __init__(self, model: str = "llama3", comfort_band: tuple[float, float] = (-0.5, 0.5)):
        self.model = model
        self.comfort_band = comfort_band
        # TODO: initialize your LLM client here, e.g.
        #   import ollama
        #   self.client = ollama.Client()
        # or an OpenAI-compatible client pointed at a self-hosted endpoint.

    def decide(self, telemetry: Telemetry) -> list[ControlAction]:
        """
        Reasoning step: evaluate telemetry against targets and return the
        control actions to forward-inject back into EnergyPlus.
        """
        # TODO: build a prompt from `telemetry`, call the LLM (with MCP
        # tools registered), parse its structured response into
        # ControlAction objects.
        raise NotImplementedError
