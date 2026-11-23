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
run.py                 # Policy optimization entry point
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

```bash
python run.py
```

`run.py` jointly optimizes the emission cap reduction rate and auction-share growth rate using differential evolution. For each candidate policy, the optimizer calls `evaluate_policy` in `ets_code/objective.py`, which runs the simulation using `simulate_ets` in `ets_code/model/simulation_ets.py`.

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
