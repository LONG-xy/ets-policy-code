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

From the repository directory, run:

```bash
python run.py
```

`run.py` calls `run_de` in `ets_code/optimization.py` to jointly optimize the emission cap reduction rate and auction-share growth rate. The optimizer evaluates candidate policies by calling the simulation in `ets_code/model/simulation_ets.py` through `evaluate_policy` in `ets_code/objective.py`.

The program prints optimization progress, the two optimized policy rates, and the mean social welfare across simulation seeds during the observation phase.

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
