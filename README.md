# ETS Policy Code

Code for **Joint Optimization of Emission Caps and Auction Shares in Emissions Trading Systems: A Bi-Level Simulation-Optimization Approach**, IEEE Transactions on Engineering Management.

Repository: https://github.com/LONG-xy/ets-policy-code

## Installation

Python 3.9 or later, with NumPy and SciPy. From the repository directory:

```bash
python -m pip install .
```

## File structure

```text
ets_code/
  model/
    simulation_ets.py   # Model parameters and simulation sequence
    sector.py          # Firm decisions, production, sales and abatement
    government.py      # Emission caps, allocation, banking and compliance
    exchange.py        # Primary auctions and secondary allowance trading
    helpers.py         # Timing, aggregation and welfare calculation
  objective.py         # Policy bounds and seed-averaged welfare objective
  optimization.py      # Differential evolution search
PARAMETERS.md          # Parameter definitions
pyproject.toml         # Package settings and dependencies
```

## Simulation

To evaluate a specified policy, call `simulate_ets` from `ets_code/model/simulation_ets.py`. The policy is defined by `E_step` (emission cap reduction rate) and `auction_step` (auction-share growth rate) in `parameters`.

Parameter names and definitions are listed in [PARAMETERS.md](PARAMETERS.md).

```python
from ets_code import simulate_ets

model, metrics = simulate_ets(parameters)
bau_metrics, ets_metrics = metrics
```

`model` contains the ETS simulation state: firms in `model.sec`, government in `model.gov`, and allowance markets in `model.ex`.

The two metric dictionaries contain round-level firm profits (`profit_t`), consumer surplus (`cs_t`), auction revenue (`govR_t`), penalties (`penalty_t`), environmental damage (`damage_t`) and social welfare (`sw_t`).

## Policy optimization

Policy optimization uses `run_de` in `ets_code/optimization.py` to search for the policy that maximizes mean social welfare. It calls `evaluate_policy` in `ets_code/objective.py`, which runs `simulate_ets` in `ets_code/model/simulation_ets.py` for each candidate policy and simulation seed. There is no need to run the simulation separately before optimization. To examine the optimized policy, set `E_step` and `auction_step` to the two values in `optimal_policy` and call `simulate_ets` again.

The policy vector is `(alpha, beta)`: the emission cap reduction rate and auction-share growth rate. `evaluate_policy` returns negative mean social welfare across the supplied simulation seeds for minimization by `run_de`.

```python
from functools import partial
from ets_code import evaluate_policy, policy_bounds
from ets_code.optimization import run_de

objective = partial(
    evaluate_policy,
    param_dict=parameters,
    seeds=simulation_seeds,
    window="observation",
    aggregation="mean",
)
result = run_de(objective, bounds=policy_bounds(parameters), **search_settings)
optimal_policy = result.x
optimal_welfare = -result.fun
```

`search_settings` supplies `population`, `seed`, `max_iterations`, `min_delta`, `patience`, `mutation` and `recombination`.

The welfare window can be `observation` (evaluation phase), `implementation` (transition phase), `all` (all post-baseline periods), or a positive integer selecting the last n periods. `aggregation` is `mean` or `sum` across period totals.

## Citation

If you use this work, please cite:

```bibtex
@article{long_ets_policy,
  title   = {Joint Optimization of Emission Caps and Auction Shares in Emissions Trading Systems: A Bi-Level Simulation-Optimization Approach},
  author  = {Long, Xiaoyi and Meng, Fanlin and Zeng, Xiao-Jun},
  journal = {IEEE Transactions on Engineering Management},
  note    = {Accepted for publication}
}
```
