"""Parameter-independent coupling between policy search and the lower-level ABM."""

from numbers import Integral

import numpy as np

from .model import c_parameters, simulate_ets
from .model.helpers import aggregate_by_period


def policy_bounds(param_dict):
    """Return theoretical bounds on (cap reduction, auction-share growth)."""
    transition = param_dict["t_trans"]
    if not isinstance(transition, Integral) or transition <= 1:
        raise ValueError("t_trans must be an integer greater than one")
    return (0.0, 1.0 / transition), (0.0, 1.0 / (transition - 1))


def welfare_from_series(metrics, p, *, window, aggregation):
    """Aggregate period welfare over an explicitly selected policy window.

    Windows are 'all' (post-baseline), 'implementation', 'observation',
    or a positive integer selecting the last n periods. Aggregation is
    'mean' or 'sum' across period totals. No discounting is added here.
    """
    if aggregation not in ("mean", "sum"):
        raise ValueError("aggregation must be 'mean' or 'sum'")
    profit = np.asarray(metrics["profit_t"], dtype=float)
    government = np.asarray(metrics["govR_t"], dtype=float)
    penalty = np.asarray(metrics.get("penalty_t", np.zeros_like(profit)), dtype=float)
    surplus = np.asarray(metrics["cs_t"], dtype=float)
    damage = np.asarray(metrics["damage_t"], dtype=float)
    _, economic = aggregate_by_period(profit + government + penalty + surplus, p, how="sum")
    _, environmental = aggregate_by_period(-damage, p, how="sum")

    start = p.baseline_period
    end = start + p.t_trans
    if isinstance(window, Integral) and not isinstance(window, bool):
        if window <= 0:
            raise ValueError("integer windows must be positive")
        selected = slice(-min(window, len(economic)), None)
    elif window == "all":
        selected = slice(start, None)
    elif window == "implementation":
        selected = slice(start, end)
    elif window == "observation":
        selected = slice(end, None)
    else:
        raise ValueError("unknown welfare window")

    economic, environmental = economic[selected], environmental[selected]
    if not len(economic):
        raise ValueError("the selected welfare window is empty")
    if not (np.all(np.isfinite(economic)) and np.all(np.isfinite(environmental))):
        raise ValueError("non-finite period welfare")
    aggregate = np.mean if aggregation == "mean" else np.sum
    return float(aggregate(economic) + aggregate(environmental))


def evaluate_policy(policy, param_dict, *, seeds, window, aggregation):
    """Return negative mean welfare for a minimizing optimizer.

    The caller supplies the input dictionary, seed set and welfare window.
    Firm heterogeneity and trading randomness follow the original evaluation
    sequence. NumPy's global random state is restored on exit. This interface
    is intended for serial calls, not concurrent threads.
    """
    if len(policy) != 2 or not np.all(np.isfinite(policy)):
        raise ValueError("policy must contain two finite values: alpha, beta")
    seeds = tuple(seeds)
    if not seeds:
        raise ValueError("at least one simulation seed is required")
    parameters = dict(param_dict)
    parameters["E_step"], parameters["auction_step"] = map(float, policy)
    for value, (lower, upper) in zip(policy, policy_bounds(parameters)):
        if not lower <= value <= upper:
            raise ValueError("policy lies outside the theoretical bounds")

    state = np.random.get_state()
    values = []
    try:
        for seed in seeds:
            np.random.seed(int(seed))
            fixed_parameters = c_parameters(parameters).generate_random_parameter()
            np.random.seed(int(seed))
            model, metrics = simulate_ets(
                parameters,
                damage_coeff=parameters["damage_coeff"],
                fixed_random_par=fixed_parameters,
            )
            if model.error:
                raise RuntimeError("; ".join(model.log))
            values.append(welfare_from_series(
                metrics[1], model, window=window, aggregation=aggregation,
            ))
    finally:
        np.random.set_state(state)
    return -float(np.mean(values))
