"""Differential evolution with caller-supplied settings and stagnation stopping."""

from numbers import Integral

import numpy as np
from scipy.optimize import differential_evolution


def run_de(
    objective, bounds, *, population, seed, max_iterations, min_delta,
    patience, mutation, recombination, callback=None, disp=False,
):
    """Minimize an objective (negative welfare) with the original DE strategy.

    Population is the total population size, not SciPy's per-dimension factor.
    All numerical search settings are provided by the caller. The optional
    callback receives (xk, convergence) for monitoring only. Stops after the
    iteration limit or 'patience' generations without a welfare improvement
    greater than 'min_delta'. SciPy's dispersion stopping is disabled.
    """
    dimension = len(bounds)
    if not dimension:
        raise ValueError("bounds cannot be empty")
    if (not isinstance(population, Integral) or population < 5
            or population % dimension):
        raise ValueError("population must be >= 5 and divisible by dimension")
    if not isinstance(max_iterations, Integral) or max_iterations < 1:
        raise ValueError("max_iterations must be a positive integer")
    if not isinstance(patience, Integral) or patience < 1:
        raise ValueError("patience must be a positive integer")
    if not np.isfinite(min_delta) or min_delta < 0:
        raise ValueError("min_delta must be finite and nonnegative")
    best = -np.inf
    significant_best = -np.inf
    waiting = 0

    def tracked_objective(x):
        nonlocal best
        value = float(objective(x))
        if not np.isfinite(value):
            raise ValueError("objective must return a finite value")
        best = max(best, -value)
        return value

    def record_and_stop(xk, convergence):
        nonlocal significant_best, waiting
        if callback is not None:
            callback(xk, convergence)
        if best - significant_best > min_delta:
            significant_best, waiting = best, 0
        else:
            waiting += 1
        return waiting >= patience

    return differential_evolution(
        tracked_objective, bounds=bounds, strategy="best1bin",
        maxiter=max_iterations, popsize=population // dimension,
        tol=0.0, atol=-np.inf, mutation=mutation,
        recombination=recombination, seed=seed, workers=1,
        polish=False, disp=disp, callback=record_and_stop,
    )
