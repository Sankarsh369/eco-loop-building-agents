"""
Eco-Loop Building Agents — entry point.

Starts the closed-loop pipeline:
    EnergyPlus (simulation) --feedback--> LLM Agent (reasoning)
                              <--control actions--

Usage:
    python src/main.py --idf models/baseline.idf
"""
import argparse

from energyplus_wrapper import EnergyPlusWrapper
from llm_agent import LLMAgent


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the Eco-Loop closed-loop pipeline.")
    parser.add_argument("--idf", required=True, help="Path to the EnergyPlus .idf building model.")
    parser.add_argument("--epw", default=None, help="Path to the EnergyPlus weather (.epw) file.")
    parser.add_argument("--steps", type=int, default=None, help="Optional cap on simulation timesteps.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    sim = EnergyPlusWrapper(idf_path=args.idf, epw_path=args.epw)
    agent = LLMAgent()

    # TODO: replace with the real EnergyPlus callback / timestep loop
    # (e.g. via the EMS Python API or a co-simulation callback).
    for telemetry in sim.stream_telemetry(max_steps=args.steps):
        # 1. Feedback: EnergyPlus -> AI
        # 2. Reasoning: agent evaluates telemetry against comfort/energy targets
        actions = agent.decide(telemetry)
        # 3. Control actions: AI -> EnergyPlus (forward injection)
        sim.apply_control_actions(actions)

    sim.close()


if __name__ == "__main__":
    main()
