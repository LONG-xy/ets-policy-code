"""Optimize ETS policy using the Experiment 1 settings."""

from functools import partial

from ets_code import evaluate_policy, policy_bounds
from ets_code.optimization import run_de


PARAMETERS = {
    'TP': 21,
    't_period': 12,
    'baseline_period': 1,
    't_trans': 10,
    't_eval': 10,
    'A': 20,
    'e0': 1,
    'c0': 1,
    'b': 1,
    'n_abatement_steps': 20,
    'min_abatement_interval': 3,
    'floor_price': 0.05,
    'use_penalty': True,
    'penalty_rate': 15,
    'bank_until_impl_end': False,
    'auctions_per_period': 4,
    'allow_banking': True,
    'damage_coeff': 5,
    'discount_rate': 0,
    'tc_rate_b': 0.0,
    'tc_rate_s': 0.0,
    'N': 25,
    'initial_markup': 0.25,
    'markup_adjust_rate': 0.5,
    'market_selection_rate': 0.1,
    'lr': 0.1,
    'max_abatement_ratio': (0.25, 0.5),
    'mac_slope': 10,
    'tech_threshold': 0.05,
    'heterogeneity_b': 0.2,
    'w_price': 0.5,
    'w_emission': 0.2,
    'w_delivery': 0.3,
    'production_trend_weight': 0.01,
}

SIMULATION_SEEDS = list(range(1, 21))
SEARCH_SETTINGS = {
    "population": 40,
    "seed": 42,
    "max_iterations": 100,
    "min_delta": 1e-4,
    "patience": 10,
    "mutation": (0.5, 1.0),
    "recombination": 0.7,
}


def main():
    objective = partial(
        evaluate_policy,
        param_dict=PARAMETERS,
        seeds=SIMULATION_SEEDS,
        window="observation",
        aggregation="mean",
    )
    result = run_de(
        objective,
        bounds=policy_bounds(PARAMETERS),
        **SEARCH_SETTINGS,
        disp=True,
    )
    print(f"Optimal cap reduction rate (alpha): {result.x[0]:.16g}")
    print(f"Optimal auction-share growth rate (beta): {result.x[1]:.16g}")
    print(f"Mean social welfare: {-result.fun:.6f}")
    return result


if __name__ == "__main__":
    main()
