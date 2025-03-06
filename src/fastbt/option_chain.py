import numpy as np
import pandas as pd
from scipy.stats import norm
import logging
from typing import List, Dict

# Set up logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)


def black_scholes_price(
    S: float, K: float, T: float, r: float, sigma: float, option_type: str = "call"
) -> float:
    """Calculate the Black-Scholes option price."""
    d1 = (np.log(S / K) + (r + 0.5 * sigma**2) * T) / (sigma * np.sqrt(T))
    d2 = d1 - sigma * np.sqrt(T)

    if option_type == "call":
        price = S * norm.cdf(d1) - K * np.exp(-r * T) * norm.cdf(d2)
    elif option_type == "put":
        price = K * np.exp(-r * T) * norm.cdf(-d2) - S * norm.cdf(-d1)

    return price


def black_scholes_greeks(
    S: float, K: float, T: float, r: float, sigma: float, option_type: str = "call"
) -> Dict[str, float]:
    """Calculate the Greeks for the Black-Scholes option price."""
    d1 = (np.log(S / K) + (r + 0.5 * sigma**2) * T) / (sigma * np.sqrt(T))
    d2 = d1 - sigma * np.sqrt(T)

    delta = norm.cdf(d1) if option_type == "call" else norm.cdf(d1) - 1
    gamma = norm.pdf(d1) / (S * sigma * np.sqrt(T))
    theta = -(S * norm.pdf(d1) * sigma) / (2 * np.sqrt(T)) - r * K * np.exp(
        -r * T
    ) * norm.cdf(d2 if option_type == "call" else -d2)
    vega = S * norm.pdf(d1) * np.sqrt(T)
    rho = K * T * np.exp(-r * T) * norm.cdf(d2 if option_type == "call" else -d2)

    return {"delta": delta, "gamma": gamma, "theta": theta, "vega": vega, "rho": rho}


def add_noise(price: float, noise_level: float = 0.02) -> float:
    """Add random noise to simulate real-time prices."""
    noise = np.random.normal(0, noise_level, size=price.shape)
    return price * (1 + noise)


def generate_option_chain(
    S: float,
    K_range: List[float],
    T: float,
    r: float,
    base_sigma: float,
    smile_params: Dict[str, float],
    noise_level: float = 0.02,
    generate_greeks: bool = True,
) -> pd.DataFrame:
    """Generate an option chain with simulated prices and optionally Greeks."""
    K = np.array(K_range)

    # Adjust the volatility based on the strike price to create a volatility smile
    sigma = base_sigma * (1 + smile_params["a"] * np.abs(K - S) / S)

    d1 = (np.log(S / K) + (r + 0.5 * sigma**2) * T) / (sigma * np.sqrt(T))
    d2 = d1 - sigma * np.sqrt(T)

    # Calculate option prices
    call_prices = S * norm.cdf(d1) - K * np.exp(-r * T) * norm.cdf(d2)
    put_prices = K * np.exp(-r * T) * norm.cdf(-d2) - S * norm.cdf(-d1)

    # Add noise to the prices to simulate real-time prices
    call_prices = add_noise(call_prices, noise_level)
    put_prices = add_noise(put_prices, noise_level)

    option_chain = {
        "Strike": K,
        "Call Price": call_prices,
        "Put Price": put_prices,
        "Volatility": sigma,  # Include the volatility for reference
    }

    if generate_greeks:
        # Calculate Greeks
        call_delta = norm.cdf(d1)
        put_delta = norm.cdf(d1) - 1
        gamma = norm.pdf(d1) / (S * sigma * np.sqrt(T))
        call_theta = -(S * norm.pdf(d1) * sigma) / (2 * np.sqrt(T)) - r * K * np.exp(
            -r * T
        ) * norm.cdf(d2)
        put_theta = -(S * norm.pdf(d1) * sigma) / (2 * np.sqrt(T)) - r * K * np.exp(
            -r * T
        ) * norm.cdf(-d2)
        vega = S * norm.pdf(d1) * np.sqrt(T)
        call_rho = K * T * np.exp(-r * T) * norm.cdf(d2)
        put_rho = -K * T * np.exp(-r * T) * norm.cdf(-d2)

        option_chain.update(
            {
                "Call Delta": call_delta,
                "Put Delta": put_delta,
                "Gamma": gamma,
                "Call Theta": call_theta,
                "Put Theta": put_theta,
                "Vega": vega,
                "Call Rho": call_rho,
                "Put Rho": put_rho,
            }
        )

    return pd.DataFrame(option_chain)


def generate_option_chains_for_expiries(
    S: float,
    K_range: List[float],
    expiries: List[float],
    r: float,
    base_sigma: float,
    smile_params: Dict[str, float],
    noise_level: float = 0.02,
    generate_greeks: bool = True,
) -> Dict[str, pd.DataFrame]:
    """Generate option chains for multiple expiries."""
    all_option_chains = {}

    for T in expiries:
        option_chain = generate_option_chain(
            S, K_range, T, r, base_sigma, smile_params, noise_level, generate_greeks
        )
        all_option_chains[f"Expiry {T} years"] = option_chain

    return all_option_chains


def validate_parameters(
    S: float,
    K_range: List[float],
    expiries: List[float],
    r: float,
    base_sigma: float,
    smile_params: Dict[str, float],
    noise_level: float,
) -> None:
    """Validate the input parameters."""
    if not all(T > 0 for T in expiries):
        raise ValueError("All expiries must be positive.")
    if not (0 <= noise_level <= 1):
        raise ValueError("Noise level must be between 0 and 1.")
    if base_sigma <= 0:
        raise ValueError("Base volatility must be positive.")
    if r < 0:
        raise ValueError("Risk-free rate cannot be negative.")
    if not isinstance(smile_params, dict) or "a" not in smile_params:
        raise ValueError("Smile parameters must be a dictionary with key 'a'.")
    logging.info("Parameters validated successfully.")
