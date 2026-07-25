# System Architecture — Eco-Loop Building Agents

> Deliverable #4: System Architecture Document. Fill in each section below
> with details specific to your implementation.

## 1. Overview

_One paragraph describing the closed-loop pipeline: EnergyPlus (simulation)
↔ LLM agent (reasoning) via MCP, and what the PoC proves._

## 2. Tool-Calling Architecture

- **MCP Server / tools exposed:** `read_simulation_log`, `get_zone_telemetry`,
  `set_zone_setpoint` (see `src/mcp_server.py`) — describe what each tool
  does and why the LLM needs it.
- **LLM ↔ EnergyPlus data flow diagram:** _add a diagram here (PNG/SVG in
  `docs/images/`)._

## 3. Prompt Engineering Strategy

- System prompt design and reasoning constraints (comfort band, energy
  targets, grid carbon intensity).
- How the agent is kept within safe/valid EnergyPlus set-point ranges.
- Any self-correction / retry loop used when a tool call or simulation
  step errors out.

## 4. Closed-Loop Control Flow

1. **Feedback (EnergyPlus → AI):** telemetry streamed per timestep.
2. **Reasoning:** LLM evaluates telemetry vs. targets.
3. **Control Actions (AI → EnergyPlus):** computed ECMs / set-points.
4. **Forward Injection:** actions applied to the live simulation.

## 5. Simulation Logs & Evaluation

- Link to / summarize the logs in `data/logs/`.
- Baseline vs. AI-driven results (energy consumption, PMV comfort index,
  peak demand) — link to the dashboard in `dashboard/`.

## 6. Known Limitations & Future Work
