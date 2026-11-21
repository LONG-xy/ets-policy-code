# Parameter interface (no numerical inputs)

Supply a Python dictionary populated from the article and supplementary
material. This file documents names and meanings only; it is not a numerical
configuration or experiment script. All keys below are required unless marked
optional. The original simulator does not comprehensively validate inputs.

## Time structure

| Key | Type | Meaning |
| --- | --- | --- |
| `TP` | integer | Total number of periods, including baseline, transition and evaluation |
| `t_period` | integer | Simulation rounds per period |
| `baseline_period` | integer | Number of baseline periods before ETS implementation |
| `t_trans` | integer | Number of transition periods over which policy changes |

Use positive integer time quantities and `TP > baseline_period + t_trans`
for the observation-window objective. A separate `t_eval` input is not read by
the model: evaluation length is `TP - baseline_period - t_trans`.
Policy optimization requires `t_trans > 1`.

## Economic and firm inputs

| Key | Type | Meaning |
| --- | --- | --- |
| `A` | positive number | Aggregate linear demand intercept |
| `b` | positive number | Aggregate linear demand price coefficient |
| `N` | integer | Number of firms; use at least two for heterogeneity standardization |
| `e0` | number | Mean initial emissions intensity |
| `c0` | number | Baseline unit production cost |
| `initial_markup` | number | Baseline markup |
| `markup_adjust_rate` | number | Markup adjustment rate |
| `market_selection_rate` | number | Market-share selection rate |
| `lr` | number | Baseline learning rate for allowance quotes |
| `heterogeneity_b` | nonnegative number | Relative heterogeneity range |
| `production_trend_weight` | number | Weight of demand trend in production planning |
| `w_price` | nonnegative number | Relative price weight in firm competitiveness |
| `w_emission` | nonnegative number | Relative emission-intensity weight |
| `w_delivery` | nonnegative number | Relative delivery-performance weight |

The three competitiveness weights must have a positive sum; the model
normalizes them. Firm-specific initial emissions intensity follows the original
normal-draw implementation; use economically meaningful input magnitudes.

## Abatement inputs

| Key | Type | Meaning |
| --- | --- | --- |
| `n_abatement_steps` | positive integer | Number of discrete abatement technologies/steps |
| `min_abatement_interval` | nonnegative integer | Minimum rounds between abatement adoptions |
| `max_abatement_ratio` | pair of numbers | Lower and upper bounds of firm abatement potential |
| `mac_slope` | number | Baseline marginal abatement cost slope |
| `tech_threshold` | number | Technology adoption threshold |

## Policy, market and welfare inputs

| Key | Type | Meaning |
| --- | --- | --- |
| `E_step` | nonnegative number | Cap reduction rate, alpha |
| `auction_step` | nonnegative number | Auction-share growth rate, beta |
| `floor_price` | nonnegative number | Primary auction reserve/floor price |
| `allow_banking` | boolean | Allow inter-period allowance banking |
| `bank_until_impl_end` | boolean | Restrict banking to the implementation window |
| `auctions_per_period` | positive integer | Auction rounds per period |
| `use_penalty` | boolean | Apply end-of-period compliance penalties |
| `penalty_rate` | nonnegative number | Penalty per unit of uncovered emissions |
| `damage_coeff` | nonnegative number | Environmental damage per unit of emissions |
| `discount_rate` | number | Retained model field; not applied by current welfare metrics |
| `tc_rate_b` | nonnegative number, optional | Buyer transaction-cost rate; original default is zero |
| `tc_rate_s` | nonnegative number, optional | Seller transaction-cost rate; original default is zero |

Use `auctions_per_period <= t_period` so the auction count is consistent with
distinct round positions. `evaluate_policy` replaces `E_step` and `auction_step`
with each candidate; direct `simulate_ets` calls require both keys. The original
simulator permits omitting `damage_coeff` and uses its internal fallback, but the
public objective requires an explicit coefficient to avoid an implicit calibration.

## Optimization inputs

`run_de` takes `objective`, `bounds` and explicit keyword arguments:

| Argument | Meaning |
| --- | --- |
| `population` | Total population, at least five and divisible by policy dimension |
| `seed` | Search random seed, distinct from the simulation seed set |
| `max_iterations` | Maximum number of generations after initialization |
| `min_delta` | Minimum welfare improvement counted as significant |
| `patience` | Generations without significant improvement before stopping |
| `mutation` | SciPy differential-evolution mutation setting |
| `recombination` | SciPy differential-evolution crossover probability |
| `callback` | Optional monitoring callback, receiving `(xk, convergence)` |
| `disp` | Optional SciPy progress output flag |

`evaluate_policy` additionally requires a nonempty iterable of simulation
`seeds`, `window`, and `aggregation`. Use the article and supplementary material
for experimental settings; no numerical seed list or calibration is bundled.
