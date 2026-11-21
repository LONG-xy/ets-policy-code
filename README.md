# ETS Policy Code

Code for **Joint Optimization of Emission Caps and Auction Shares in
Emissions Trading Systems: A Bi-Level Simulation-Optimization Approach**,
accepted for publication in *IEEE Transactions on Engineering Management*.

**Authors:** Xiaoyi Long, Fanlin Meng, Xiao-Jun Zeng.  
**Corresponding author:** Fanlin Meng (F.Meng2@exeter.ac.uk).

## Release scope

This repository contains the lower-level agent-based ETS model, welfare
evaluation, and the upper-level differential-evolution (DE) search interface.
It excludes experiment drivers, algorithm-comparison studies, sensitivity
sweeps, plotting, notebooks, numerical input configurations, and generated
results. Obtain the study's numerical inputs and search settings from the
article and its supplementary material and supply them locally.

This release provides the model code. Numerical inputs are supplied separately
by the user based on the article and supplementary material. Numerical constants that define the existing
model implementation (for example, distribution shapes, clipping and numerical
safeguards) remain in the model; no experimental configuration file is bundled.

## Installation

Use Python 3.9 or later. From the repository directory:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install .
```

Windows activation: `.venv\Scripts\activate`.

Dependencies are NumPy and SciPy; the declared version ranges are installation
constraints, not a claim of testing every supported combination. Local numerical
verification used Python 3.11.8, NumPy 1.24.4 and SciPy 1.13.0. A separate record
of these verification versions is in `verification-environment.txt`.

## Layout

```text
ets_code/
  model/
    simulation_ets.py   # Parameters, firm heterogeneity, simulation sequence
    government.py      # Cap path, allocation, banking, compliance penalties
    exchange.py        # Primary auction and secondary trading
    sector.py          # Firms, abatement, production and commodity market
    helpers.py         # Timing, aggregation and welfare components
  objective.py         # Seed-averaged welfare and theoretical policy bounds
  optimization.py      # DE search with stagnation stopping
PARAMETERS.md          # Input interface, without numerical calibration
CITATION.cff           # Software citation metadata
LICENSE                # MIT license
```

## Model interface

The model accepts a caller-provided parameter dictionary. `PARAMETERS.md` lists
the keys, their meanings, and consistency requirements without assigning study
values. Keep local inputs under `local_inputs/`, which is ignored by Git.

```python
from ets_code import simulate_ets

def simulate_from_inputs(parameters):
    model, metrics = simulate_ets(parameters)
    bau_metrics, ets_metrics = metrics
    return model, bau_metrics, ets_metrics
```

`model` is the ETS state, with firms in `model.sec`, government in `model.gov`,
and allowance markets in `model.ex`. Metric dictionaries contain round-level
`profit_t`, `cs_t`, `govR_t`, `penalty_t`, `damage_t` and `sw_t`; index zero is
initialization. The returned state also contains `error` and `log` diagnostics.
Check these after direct simulation calls.

`simulate_ets` runs both `No_Policy` and `ETS` with the same firm heterogeneity
and returns the ETS state plus both metric dictionaries. It uses NumPy's global
random generator. For deterministic direct simulation, seed NumPy explicitly
before calling it; repeated calls otherwise draw new firm configurations and
market tie-breaks. Optional `fixed_random_par` controls firm heterogeneity, not
all market randomness. `run_model` is available for explicit scenario selection.

## Bi-level policy optimization interface

All numerical search settings and simulation seeds are supplied by the caller:

```python
from ets_code import evaluate_policy, policy_bounds
from ets_code.optimization import run_de

def optimize_from_inputs(parameters, simulation_seeds, search_settings):
    seeds = tuple(simulation_seeds)

    def objective(policy):
        return evaluate_policy(
            policy, parameters, seeds=seeds,
            window="observation", aggregation="mean",
        )

    result = run_de(
        objective,
        bounds=policy_bounds(parameters),
        population=search_settings["population"],
        seed=search_settings["seed"],
        max_iterations=search_settings["max_iterations"],
        min_delta=search_settings["min_delta"],
        patience=search_settings["patience"],
        mutation=search_settings["mutation"],
        recombination=search_settings["recombination"],
    )
    # result.x = (alpha, beta); the minimized objective is negative welfare.
    return result.x, -result.fun, result
```

`alpha` maps to `E_step` and `beta` maps to `auction_step`. The theoretical
bounds are `0 <= alpha <= 1/t_trans` and
`0 <= beta <= 1/(t_trans - 1)`, for integer `t_trans > 1`.

`evaluate_policy` returns negative mean welfare across the supplied seeds.
It regenerates the same firm configurations and market randomness for each
candidate and restores the caller's NumPy random state. Run it serially; it is
not thread-safe. The search uses `best1bin`, serial execution, no polishing,
and the original maximum-iteration/stagnation stopping mechanism. Numerical
population, mutation, crossover, seed and stopping settings are not embedded.

The `observation` window is the post-transition evaluation phase. `all` means
all post-baseline periods; `implementation` means the transition phase. An
integer window selects the last n periods. Welfare is aggregated as period
totals and then averaged or summed over the selected periods. No discounting
is added by the wrapper; the original model stores a `discount_rate` field
without applying it in the metric routine. Invalid policies, empty windows,
model diagnostics and non-finite objective values raise errors in this wrapper.

## Provenance and verification

The six files in `ets_code/model/` are byte-for-byte copies of the research
project's `code/model/` files, retaining the existing APIs and comments. The
objective coupling is extracted from `code/exp1_optimize.py`, with experimental
globals replaced by explicit inputs, random-state restoration and validation.
The DE wrapper is extracted from `code/optimization.py`; the PSO/GA comparison
termination class and `pymoo` dependency are excluded.

Local checks compared original and released simulation arrays and welfare
evaluation, and exercised the configurable DE wrapper. These checks used local
inputs outside this repository; experiment inputs and verification scripts are
not part of the public package. This verification checks extraction consistency,
not independent scientific validation of the model or all reported experiments.

## Citation and license

Use `CITATION.cff` to cite this software and cite the associated article by
Xiaoyi Long, Fanlin Meng and Xiao-Jun Zeng. Publication volume, pages and article
DOI should be added when assigned. After hosting, add the repository URL and,
if archived, the software version DOI to `CITATION.cff`.

The prepared license is MIT; its full terms are in `LICENSE`.
