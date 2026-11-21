"""Emissions trading simulation and policy optimization code."""

from .model import baseline_E_per_round, c_parameters, run_model, simulate_ets
from .objective import evaluate_policy, policy_bounds, welfare_from_series

__version__ = "1.0.0"

__all__ = [
    "baseline_E_per_round", "c_parameters", "run_model", "simulate_ets",
    "evaluate_policy", "policy_bounds", "welfare_from_series",
]
