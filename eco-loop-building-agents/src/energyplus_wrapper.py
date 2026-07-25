"""
EnergyPlusWrapper
==================
Thin wrapper around the EnergyPlus simulation engine.

Bridges to EnergyPlus via one of:
  - `eppy`            (edit/read .idf files, run via the EnergyPlus CLI)
  - `pyenergyplus`     (EnergyPlus's built-in EMS Python API, for live co-simulation)
  - EMS/BCVTB          (for external co-simulation callbacks)

Fill in `_run_timestep` / EMS callback hooks with your actual simulation
integration.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Iterator


@dataclass
class Telemetry:
    """A single timestep of feedback data streamed from EnergyPlus."""
    timestamp: str
    zone_temperatures: dict
    indoor_air_quality: dict
    energy_consumption_kwh: float
    pmv_comfort_index: float
    peak_demand_kw: float
    grid_carbon_intensity: float


@dataclass
class ControlAction:
    """A control action computed by the LLM agent and injected back into EnergyPlus."""
    zone: str
    setpoint_type: str   # e.g. "cooling_setpoint", "heating_setpoint"
    value: float


class EnergyPlusWrapper:
    def __init__(self, idf_path: str, epw_path: str | None = None):
        self.idf_path = idf_path
        self.epw_path = epw_path
        # TODO: load the .idf via eppy, e.g.
        #   from eppy.modeleditor import IDF
        #   IDF.setiddname("<path to Energy+.idd>")
        #   self.idf = IDF(idf_path, epw_path)

    def stream_telemetry(self, max_steps: int | None = None) -> Iterator[Telemetry]:
        """Yield one Telemetry reading per simulation timestep."""
        # TODO: hook into the EMS Python API callback or run the simulation
        # and parse the .eso/.sql output timestep by timestep.
        raise NotImplementedError

    def apply_control_actions(self, actions: list[ControlAction]) -> None:
        """Forward-inject computed set-points / overrides into the live simulation."""
        # TODO: push values via the EMS actuator API, or update the .idf
        # and re-run for the next control horizon.
        raise NotImplementedError

    def close(self) -> None:
        """Clean up the simulation process/handles."""
        pass
