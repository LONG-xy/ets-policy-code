"""Run one ETS simulation using the Experiment 1 baseline parameters."""

import numpy as np

from ets_code import c_parameters, simulate_ets, welfare_from_series


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
    'auction_step': 0.035093963347912135,
    'E_step': 0.042051779827747625,
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

SIMULATION_SEED = 1


def main():
    np.random.seed(SIMULATION_SEED)
    fixed_random_par = c_parameters(PARAMETERS).generate_random_parameter()
    np.random.seed(SIMULATION_SEED)
    model, metrics = simulate_ets(
        PARAMETERS,
        fixed_random_par=fixed_random_par,
    )
    if model.error:
        raise RuntimeError("; ".join(model.log))

    print(f"Simulation seed: {SIMULATION_SEED}")
    print(f"Cap reduction rate (alpha): {PARAMETERS['E_step']:.8f}")
    print(f"Auction-share growth rate (beta): {PARAMETERS['auction_step']:.8f}")
    for label, series in zip(("Business as usual", "ETS"), metrics):
        welfare = welfare_from_series(
            series, model, window="observation", aggregation="mean",
        )
        print(f"{label} mean welfare per observation period: {welfare:.6f}")
    return model, metrics


if __name__ == "__main__":
    main()
