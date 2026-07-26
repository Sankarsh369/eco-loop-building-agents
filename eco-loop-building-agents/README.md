# Eco-Loop Building Agents

An autonomous, closed-loop building energy management system that pairs a
physics-based simulation engine (**EnergyPlus**) with an open-source LLM
agent (via **MCP**) to continuously optimize building energy consumption,
thermal comfort, and carbon impact — without hard-coded rule-based logic.

> Built for Smart India Hackathon (SIH) — Idea Submission.

## Problem Background

Buildings consume roughly 40% of global energy and are a major driver of
carbon emissions. Traditional Building Management Systems (BMS) rely on
rigid, rule-based schedules that fail to adapt in real time to changing
weather, occupancy, and grid conditions. By pairing physics-based energy
simulation with open-source LLMs and standardized communication protocols
(like the Model Context Protocol), a building can become an active,
self-correcting agent rather than a passive energy consumer.

## Technical Core Requirements

### 1. Simulation Engine (EnergyPlus)
- Runs high-fidelity building energy simulations.
- Bridges Python to the simulation via libraries such as `eppy`,
  `pyenergyplus`, or EMS/BCVTB, using the Input Data File (`.idf`) or
  Functional Mock-up Units (`.fmu`).

### 2. Cognitive Engine & Protocol (Open-Source LLM + MCP)
- Deploys an open-source LLM (e.g., Llama 3, Mistral, Qwen) running
  locally or via a self-hosted API.
- Implements an MCP server / custom agentic tools so the LLM can parse
  files, extract runtime errors, and execute tasks without manual code
  changes.

### 3. Closed-Loop Execution Framework
- **Feedback (EnergyPlus → AI):** Streams live performance metrics
  (zone temperatures, indoor air quality, energy consumption, Predicted
  Mean Vote / thermal comfort indices).
- **Reasoning:** The LLM evaluates telemetry against target occupancy
  comfort ranges, peak demand thresholds, and local carbon-grid intensity.
- **Control Actions (AI → EnergyPlus):** The LLM computes optimal Energy
  Conservation Measures (ECMs) and updated dynamic set-points.
- **Forward Injection:** Computed set-points and supervisory overrides
  are fed directly back into the live EnergyPlus instance.

## Hackathon Objective

Build a live, operational Physical AI Proof-of-Concept (PoC) that
automates smart building operations through an autonomous closed-loop
control pipeline. Using EnergyPlus as the digital building sandbox and an
open-source LLM (or MCP server configuration) as the brain, the system
ingests real-time sensor data from the simulation, evaluates variables,
and continuously injects forward control actions back into EnergyPlus to
prove quantifiable energy and cost savings.

## Deliverables

1. **Fully Functional Source Code** — unified Python codebase managing the
   EnergyPlus API wrapper, the LLM agent orchestration logic, and the MCP
   communication layer.
2. **Building Models (`.idf` files)** — baseline building file plus the
   modified versions generated during runtime evaluation.
3. **Quantitative Savings Dashboard** — visual dashboard or final data
   export comparing baseline operation vs. AI-driven operation
   (energy consumed vs. thermal comfort boundaries maintained).
4. **System Architecture Document** — short Markdown report explaining
   tool-calling architecture, prompt engineering strategy, and simulation
   logs.
5. **PoC Demonstration Video** — Watch the [Loom PoC Demonstration Video](https://www.loom.com/share/64d0edbda82149529c16521392173ecb). Shows the operational closed-loop control system and Streamlit analytics dashboard.

## Evaluation Criteria

| Criterion | Weight |
|---|---|
| System Integration — robustness/reliability of the closed loop over an extended simulation horizon | 30% |
| Energy Efficiency Realized — net energy reduction vs. baseline | 25% |
| Thermal Comfort & Constraints — energy saved without sacrificing occupant comfort | 20% |
| Agentic Autonomy & Code Elegance — creative use of open-source LLM tool-calling, MCP protocols, and self-correction loops | 15% |
| Presentation & Documentation — clarity of architecture, visualizations, and delivery | 10% |

## Project Structure

```
eco-loop-building-agents/
├── README.md
├── requirements.txt
├── .gitignore
├── LICENSE
├── src/                    # Application source code
│   ├── __init__.py
│   ├── main.py             # Entry point — starts the closed-loop pipeline
│   ├── energyplus_wrapper.py   # EnergyPlus API wrapper (eppy / pyenergyplus / EMS)
│   ├── llm_agent.py         # LLM reasoning + prompt engineering
│   └── mcp_server.py        # MCP server / tool definitions exposed to the LLM
├── models/                  # EnergyPlus building models
│   ├── baseline.idf
│   └── modified/             # Runtime-modified .idf versions
├── data/
│   └── logs/                 # Simulation run logs, telemetry exports
├── dashboard/                # Savings dashboard app or exported charts/CSVs
├── docs/
│   ├── architecture.md       # System architecture write-up (deliverable #4)
│   └── images/                # Screenshots, diagrams, dashboard snaps
├── notebooks/                 # Exploratory analysis / prototyping notebooks
├── tests/                     # Unit / integration tests
├── presentation/               # SIH Idea PPT/PDF submission
└── video/                       # PoC demo video or a link to it (README/VIDEO_LINK.md)
```

## Getting Started

```bash
# 1. Clone the repo
git clone https://github.com/<your-username>/eco-loop-building-agents.git
cd eco-loop-building-agents

# 2. Create a virtual environment
python -m venv venv
source venv/bin/activate      # Windows: venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Run the closed-loop pipeline
python src/main.py --idf models/baseline.idf
```

## License

See [LICENSE](LICENSE).
