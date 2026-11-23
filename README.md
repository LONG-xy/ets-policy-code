# ETS Policy Code

Code for **Joint Optimization of Emission Caps and Auction Shares in Emissions Trading Systems: A Bi-Level Simulation-Optimization Approach**, IEEE Transactions on Engineering Management.

Repository: https://github.com/LONG-xy/ets-policy-code

## Installation

Requires Python 3.9 or later. NumPy and SciPy are installed with the package.

```bash
git clone https://github.com/LONG-xy/ets-policy-code.git
cd ets-policy-code
python -m pip install .
```

## File structure

```text
run.py                 # Runnable simulation example with Experiment 1 parameters
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

## Usage

From the repository directory, run:

```bash
python run.py
```

`run.py` contains the Experiment 1 baseline parameters and uses simulation seed 1. It calls `simulate_ets` in `ets_code/model/simulation_ets.py` to run the business-as-usual and ETS scenarios, then prints their mean social welfare per period during the observation phase.

To evaluate another policy, change `E_step` (emission cap reduction rate) and `auction_step` (auction-share growth rate) in `PARAMETERS` at the top of `run.py`. Parameter definitions are listed in [PARAMETERS.md](PARAMETERS.md).

The simulation returns `model` (the ETS model state) and `metrics` (the business-as-usual and ETS results). The results include firm profits (`profit_t`), consumer surplus (`cs_t`), auction revenue (`govR_t`), penalties (`penalty_t`), environmental damage (`damage_t`), and social welfare (`sw_t`).

For policy optimization, `run_de` in `ets_code/optimization.py` searches over the two policy rates. It calls `evaluate_policy` in `ets_code/objective.py`, which automatically runs the simulation for each candidate policy and simulation seed.

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
