"""
Media transformation functions for MMM (Marketing Mix Modeling).

These functions are the single source of truth for:
- Adstock transformations (carryover effects)
- Saturation transformations (diminishing returns)

Parameters are calibrated in 05_causal_identification.ipynb
and applied in 06_feature_engineering.ipynb.
"""

import numpy as np
import pandas as pd
from typing import Dict, Any, Union


def geometric_adstock(x: Union[np.ndarray, pd.Series], decay_rate: float) -> np.ndarray:
    """
    Apply geometric adstock transformation.

    Adstock_t = x_t + decay_rate * Adstock_{t-1}

    Parameters
    ----------
    x : array-like or pd.Series
        Time series of spend (must be time-ordered)
    decay_rate : float
        Decay rate λ ∈ [0, 1]. Higher = longer memory.

    Returns
    -------
    np.ndarray
        Adstocked values

    Notes
    -----
    Half-life = log(0.5) / log(decay_rate) periods
    Steady-state gain = 1 / (1 - decay_rate)

    Examples
    --------
    >>> spend = np.array([100, 0, 0, 0])
    >>> geometric_adstock(spend, 0.5)
    array([100., 50., 25., 12.5])
    """
    x = np.asarray(x, dtype=float)
    adstocked = np.zeros_like(x)
    adstocked[0] = x[0]

    for t in range(1, len(x)):
        adstocked[t] = x[t] + decay_rate * adstocked[t-1]

    return adstocked


def hill_saturation(x: Union[np.ndarray, pd.Series], K: float, alpha: float = 2) -> np.ndarray:
    """
    Apply Hill saturation function (S-curve).

    y = x^α / (x^α + K^α)

    Parameters
    ----------
    x : array-like or pd.Series
        Adstocked spend values
    K : float
        Half-saturation point (spend level at 50% max effect)
    alpha : float, default=2
        Steepness parameter (higher = sharper curve)

    Returns
    -------
    np.ndarray
        Saturated values in [0, 1]

    Notes
    -----
    At x = K, the output is exactly 0.5 (half-saturation)
    At x = 0, the output is 0
    As x → ∞, the output approaches 1

    Examples
    --------
    >>> x = np.array([0, 100, 200, 1000])
    >>> hill_saturation(x, K=200, alpha=2)
    array([0.    , 0.2   , 0.5   , 0.9615])
    """
    x = np.asarray(x, dtype=float)
    return np.where(x > 0, x**alpha / (x**alpha + K**alpha), 0.0)


def log_saturation(x: Union[np.ndarray, pd.Series], scale: float = 1) -> np.ndarray:
    """
    Apply log saturation (simple diminishing returns).

    y = log(1 + x/scale)

    Parameters
    ----------
    x : array-like or pd.Series
        Adstocked spend values
    scale : float, default=1
        Scaling factor

    Returns
    -------
    np.ndarray
        Log-transformed values

    Notes
    -----
    This is a simpler saturation function than Hill.
    Returns are diminishing but never strictly reach a ceiling.

    Examples
    --------
    >>> x = np.array([0, 100, 1000])
    >>> log_saturation(x, scale=100)
    array([0.    , 0.6931, 2.3979])
    """
    x = np.asarray(x, dtype=float)
    return np.log1p(x / scale)


def power_saturation(x: Union[np.ndarray, pd.Series], beta: float = 0.5) -> np.ndarray:
    """
    Apply power saturation.

    y = x^β where 0 < β < 1

    Parameters
    ----------
    x : array-like or pd.Series
        Adstocked spend values
    beta : float, default=0.5
        Power parameter (< 1 for diminishing returns)

    Returns
    -------
    np.ndarray
        Power-transformed values

    Notes
    -----
    This transformation preserves the original scale better than log or Hill.
    Beta = 0.5 corresponds to square root transformation.

    Examples
    --------
    >>> x = np.array([0, 100, 400, 900])
    >>> power_saturation(x, beta=0.5)
    array([ 0., 10., 20., 30.])
    """
    x = np.asarray(x, dtype=float)
    return np.where(x > 0, np.power(x, beta), 0.0)


def hill_derivative(x: Union[np.ndarray, pd.Series], K: float, alpha: float) -> np.ndarray:
    """
    Derivative of Hill function w.r.t. x (for marginal effects).

    dH/dx = α * K^α * x^(α-1) / (x^α + K^α)^2

    Parameters
    ----------
    x : array-like or pd.Series
        Adstocked spend values
    K : float
        Half-saturation point
    alpha : float
        Steepness parameter

    Returns
    -------
    np.ndarray
        Marginal effect at each x value

    Notes
    -----
    This gives the instantaneous rate of change of the Hill function.
    Useful for calculating marginal ROI at current spend levels.

    Examples
    --------
    >>> x = np.array([100, 200, 300])
    >>> hill_derivative(x, K=200, alpha=2)
    array([0.0012, 0.0008, 0.0005])
    """
    x = np.asarray(x, dtype=float)
    denom = (x**alpha + K**alpha)**2
    numer = alpha * K**alpha * x**(alpha - 1)
    return np.where(denom > 0, numer / denom, 0.0)


def apply_transformations(df: pd.DataFrame,
                         channels: list,
                         params: Dict[str, Any]) -> pd.DataFrame:
    """
    Apply full transformation pipeline to media channels.

    Parameters
    ----------
    df : pd.DataFrame
        Data with raw media spend columns
    channels : list
        List of media channel column names (e.g., ['media_television', ...])
    params : dict
        Calibrated parameters with keys:
        - 'decay_rates': {channel: decay_rate}
        - 'saturation_functions': {channel: 'hill' or 'log' or 'power'}
        - 'saturation_params': {channel: {'K': value, 'alpha': value}}

    Returns
    -------
    pd.DataFrame
        DataFrame with added columns: {channel}_adstock, {channel}_saturated

    Examples
    --------
    >>> df = pd.DataFrame({'media_tv': [100, 200, 150]})
    >>> params = {
    ...     'decay_rates': {'media_tv': 0.5},
    ...     'saturation_functions': {'media_tv': 'hill'},
    ...     'saturation_params': {'media_tv': {'K': 100, 'alpha': 2}}
    ... }
    >>> result = apply_transformations(df, ['media_tv'], params)
    >>> 'media_tv_adstock' in result.columns
    True
    >>> 'media_tv_saturated' in result.columns
    True
    """
    df = df.copy()

    # Apply adstock to each channel
    for channel in channels:
        decay = params['decay_rates'].get(channel, 0.5)  # Default 0.5 if not found
        df[f'{channel}_adstock'] = geometric_adstock(
            df[channel].fillna(0).values, decay
        )

    # Apply saturation to each channel
    for channel in channels:
        adstock_col = f'{channel}_adstock'
        func_type = params['saturation_functions'].get(channel, 'hill')  # Default to Hill

        if func_type == 'hill':
            sat_params = params['saturation_params'].get(
                channel, {'K': 1, 'alpha': 2}
            )
            df[f'{channel}_saturated'] = hill_saturation(
                df[adstock_col].values,
                K=sat_params['K'],
                alpha=sat_params.get('alpha', 2)
            )
        elif func_type == 'log':
            scale = params['saturation_params'].get(
                channel, {}
            ).get('scale', 1)
            df[f'{channel}_saturated'] = log_saturation(
                df[adstock_col].values, scale
            )
        elif func_type == 'power':
            beta = params['saturation_params'].get(
                channel, {}
            ).get('beta', 0.5)
            df[f'{channel}_saturated'] = power_saturation(
                df[adstock_col].values, beta
            )
        else:
            raise ValueError(
                f"Unknown saturation function '{func_type}' for channel '{channel}'. "
                f"Must be 'hill', 'log', or 'power'."
            )

    return df


def calculate_half_life(decay_rate: float) -> float:
    """
    Calculate half-life (in periods) from decay rate.

    Parameters
    ----------
    decay_rate : float
        Decay rate λ ∈ [0, 1]

    Returns
    -------
    float
        Number of periods until effect reaches 50% of original

    Examples
    --------
    >>> calculate_half_life(0.7)
    1.9
    >>> calculate_half_life(0.5)
    1.0
    """
    if decay_rate <= 0 or decay_rate >= 1:
        return np.inf if decay_rate >= 1 else 0.0
    return np.log(0.5) / np.log(decay_rate)


def calculate_steady_state_gain(decay_rate: float) -> float:
    """
    Calculate steady-state gain from decay rate.

    The steady-state gain is the total cumulative effect of a unit impulse.

    Parameters
    ----------
    decay_rate : float
        Decay rate λ ∈ [0, 1]

    Returns
    -------
    float
        Total cumulative effect

    Notes
    -----
    For example, if decay_rate = 0.5, then a $1 spend eventually contributes
    $2 of total adstocked value over time (1 + 0.5 + 0.25 + 0.125 + ... = 2).

    Examples
    --------
    >>> calculate_steady_state_gain(0.5)
    2.0
    >>> calculate_steady_state_gain(0.7)
    3.33
    """
    if decay_rate >= 1:
        return np.inf
    return 1.0 / (1.0 - decay_rate)
