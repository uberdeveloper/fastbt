"""Reference implementations — Advanced Tests (SKILL.md v2.2.0, Step 6.6)

Group A — Adversarial robustness: A1 sign-flip permutation, A2 path shuffle,
A3 regime stress, A4 sub-period consistency, A5 block bootstrap,
A6 parameter plateau.
Group B — Robust statistics: B1 edge concentration, B2 Yuen trimmed t-test,
B3 robust Sharpe.

ON REQUEST ONLY — these are never auto-run by the skill; invocation is the
user's choice (single test / single group / both groups / custom subset).

Dependencies: numpy, pandas, scipy only. No engine integration, no I/O.

Attribution (Group A): adapted from QuantGPT (MIT License, Copyright (c) 2026 Miasyster):
  https://github.com/Miasyster/QuantGPT/blob/main/quantgpt/adversarial_validator.py
  https://github.com/Miasyster/QuantGPT/blob/main/quantgpt/anti_overfit.py
Ported from cross-sectional factor tests to single-series returns analogs;
unported remainder tracked in fastbt issues #17-#19.

Conventions:
- `returns`: pd.Series of simple returns, DatetimeIndex, no NaNs.
- Each test returns dict(name, passed, details). `passed` is None for
  diagnostic-only outputs (excluded from composite scoring).
- Seeds are parameters, not hardcoded behaviour (default 42 for reproducibility).
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from scipy import stats as sps


# ---------------------------------------------------------------- helpers


def max_drawdown(path: np.ndarray) -> float:
    """Positive magnitude of worst peak-to-trough decline (input in return units)."""
    wealth = np.cumsum(path)  # cumulative return path (additive)
    peak = np.maximum.accumulate(np.concatenate([[0.0], wealth]))[1:]
    return float(np.max(peak - wealth)) if len(path) else 0.0


def annualized_sharpe(r: np.ndarray) -> float:
    sd = np.std(r, ddof=1)
    return float(np.mean(r) / sd * np.sqrt(252)) if sd > 1e-12 else 0.0


# ---------------------------------------------------------------- Group A


def sign_flip_permutation(
    returns: pd.Series, B: int = 1000, seed: int = 42, block: int = 1
) -> dict:
    """A1 — Is the mean return positive by chance?

    Exact under a symmetric null. If Ljung-Box flagged autocorrelation,
    pass block~10 (flip whole blocks) or defer to block_bootstrap().
    """
    x = returns.to_numpy()
    rng = np.random.default_rng(seed)
    real = float(x.mean())
    n = len(x)
    nb = n // block if block > 1 else 1
    eff = nb * block if block > 1 else n
    signs = rng.choice([-1.0, 1.0], size=(B, nb))
    if block > 1:
        signs = np.repeat(signs, block, axis=1)
    null_means = (x[:eff] * signs).mean(axis=1)
    p = float((null_means >= real).mean())  # one-sided H1: mean > 0
    return {
        "name": "A1 sign-flip permutation",
        "passed": p < 0.05,
        "details": {
            "real_mean": round(real, 6),
            "p_perm": round(p, 4),
            "B": B,
            "block": block,
            "null_mean_p95": round(float(np.percentile(null_means, 95)), 6),
        },
    }


def path_shuffle(
    returns: pd.Series, B: int = 1000, block: int = 10, seed: int = 42
) -> dict:
    """A2 — Is my drawdown/worst streak sequencing luck?

    WARNING: mean, vol and Sharpe are INVARIANT under shuffling — this test is
    valid ONLY for path-dependent statistics. Never use it on Sharpe.
    """
    x = returns.to_numpy()
    rng = np.random.default_rng(seed)
    nb = len(x) // block
    if nb < 3:
        return {
            "name": "A2 path shuffle",
            "passed": None,
            "details": {"error": f"insufficient data: {nb} blocks (<3)"},
        }
    blocks = x[: nb * block].reshape(nb, block)
    real_mdd = max_drawdown(x)
    mdds = np.array(
        [max_drawdown(blocks[rng.permutation(nb)].ravel()) for _ in range(B)]
    )
    lo, hi = np.percentile(mdds, [5, 95])
    within = bool(lo <= real_mdd <= hi)
    return {
        "name": "A2 path shuffle",
        "passed": within,
        "details": {
            "real_max_drawdown": round(real_mdd, 5),
            "shuffled_mdd_p5": round(float(lo), 5),
            "shuffled_mdd_p95": round(float(hi), 5),
            "B": B,
            "block": block,
            "note": "real drawdown inside shuffled 90% band "
            + (
                "(sequencing not unusual)"
                if within
                else "(OUTLIER: path-dependent luck)"
            ),
        },
    }


def regime_stress(returns: pd.Series, bench_ret: pd.Series) -> dict:
    """A3 — Does the edge hold across regimes? (needs benchmark returns)"""
    df = pd.concat([returns.rename("ret"), bench_ret.rename("bench")], axis=1).dropna()
    if len(df) < 60:
        return {
            "name": "A3 regime stress",
            "passed": None,
            "details": {"error": "insufficient overlapping data (<60 obs)"},
        }
    cum = df["bench"].rolling(60, min_periods=30).sum()
    vol = df["bench"].rolling(60, min_periods=30).std()
    masks = {
        "bull": cum > 0.05,
        "bear": cum < -0.05,
        "sideways": cum.abs() <= 0.05,
        "high_vol": vol > vol.median(),
        "low_vol": vol <= vol.median(),
    }
    overall_sign = np.sign(df["ret"].mean())
    sub, qualified = {}, []
    for name, m in masks.items():
        seg = df["ret"][m.fillna(False)]
        if len(seg) >= 30:
            sub[name] = {"n": int(len(seg)), "mean": round(float(seg.mean()), 6)}
            qualified.append(np.sign(seg.mean()))
    if not qualified:
        return {
            "name": "A3 regime stress",
            "passed": None,
            "details": {"error": "no regime with >=30 observations"},
        }
    consistency = sum(1 for s in qualified if s == overall_sign) / len(qualified)
    return {
        "name": "A3 regime stress",
        "passed": consistency >= 0.6,
        "details": {
            "overall_sign": int(overall_sign),
            "regimes": sub,
            "consistency": round(consistency, 4),
        },
    }


def subperiod_consistency(returns: pd.Series) -> dict:
    """A4 — Is the edge stable across years (calendar halves if <2yrs)?"""
    if len(returns) < 126:  # ~6 months
        return {
            "name": "A4 sub-period consistency",
            "passed": None,
            "details": {"error": "insufficient data (<~6 months)"},
        }
    if returns.index.year.nunique() >= 2:
        segs = returns.groupby(returns.index.year)
    else:
        half = len(returns) // 2
        segs = {"h1": returns.iloc[:half], "h2": returns.iloc[half:]}
        segs = pd.Series(segs).groupby(level=0)  # keep uniform interface
    per = {
        str(k): {
            "mean": round(float(g.mean()), 6),
            "positive_day_rate": round(float((g > 0).mean()), 4),
        }
        for k, g in segs
    }
    overall_sign = np.sign(returns.mean())
    pos_rate = float((returns > 0).mean())
    signs_ok = all(np.sign(v["mean"]) == overall_sign for v in per.values())
    passed = bool(pos_rate >= 0.55 and signs_ok and overall_sign != 0)
    return {
        "name": "A4 sub-period consistency",
        "passed": passed,
        "details": {
            "positive_day_rate": round(pos_rate, 4),
            "segments": per,
            "no_reversal": signs_ok,
        },
    }


def block_bootstrap(
    returns: pd.Series, B: int = 1000, block: int = 1, seed: int = 42
) -> dict:
    """A5 — Sign stability across resampled histories + percentile CIs.

    Use block~10 when Ljung-Box flags autocorrelation (moving-block), else 1 (iid).
    """
    x = returns.to_numpy()
    rng = np.random.default_rng(seed)
    n, nb = len(x), max(1, len(x) // block)
    means, sharpes = np.empty(B), np.empty(B)
    for b in range(B):
        starts = rng.integers(0, n - block + 1, size=nb)
        sample = np.concatenate([x[s : s + block] for s in starts])[:n]
        means[b] = sample.mean()
        sharpes[b] = annualized_sharpe(sample)
    sign_rate = float(np.mean(np.sign(means) == np.sign(x.mean())))
    return {
        "name": "A5 block bootstrap",
        "passed": sign_rate >= 0.7,
        "details": {
            "sign_consistency": round(sign_rate, 4),
            "mean_CI95": [
                round(float(np.percentile(means, 2.5)), 6),
                round(float(np.percentile(means, 97.5)), 6),
            ],
            "sharpe_CI95": [
                round(float(np.percentile(sharpes, 2.5)), 3),
                round(float(np.percentile(sharpes, 97.5)), 3),
            ],
            "B": B,
            "block": block,
        },
    }


def parameter_plateau(
    sweep: pd.DataFrame, param_col: str, metric_col: str, optimum: str = "max"
) -> dict:
    """A6 — Is the optimum a plateau or an overfit spike?

    sweep: parameter-sweep table (one row per evaluated parameter value).
    Uses nearest evaluated neighbours on each side of theta* (never fabricates
    untested values). Engine-driven re-runs: fastbt issue #19.
    """
    s = sweep.sort_values(param_col).reset_index(drop=True)
    if len(s) < 3:
        return {
            "name": "A6 parameter plateau",
            "passed": None,
            "details": {"error": "sweep needs >=3 evaluated points"},
        }
    i_star = s[metric_col].idxmax() if optimum == "max" else s[metric_col].idxmin()
    best = float(s.loc[i_star, metric_col])
    neigh = s.loc[[j for j in (i_star - 1, i_star + 1) if 0 <= j < len(s)]]
    if neigh.empty or len(neigh) < 2:
        return {
            "name": "A6 parameter plateau",
            "passed": None,
            "details": {"error": "optimum at sweep edge; needs neighbours both sides"},
        }
    retention = float(neigh[metric_col].min() / best) if best != 0 else 0.0
    spread = float(s[metric_col].std() / abs(best)) if best else 0.0
    return {
        "name": "A6 parameter plateau",
        "passed": retention >= 0.5,
        "details": {
            "optimum_param": float(s.loc[i_star, param_col]),
            "optimum_metric": round(best, 4),
            "neighbours": neigh[[param_col, metric_col]].round(4).to_dict("records"),
            "retention": round(retention, 4),
            "metric_cv": round(spread, 4),
            "verdict": "PLATEAU" if retention >= 0.5 else "SPIKE",
        },
    }


# ---------------------------------------------------------------- Group B


def edge_concentration(returns: pd.Series, trim: float = 0.1, top_n: int = 5) -> dict:
    """B1 — How much P&L comes from a few lucky days? (diagnostic)

    Trim is FIXED at 0.1 (0.2 for extreme tails). NEVER tune trim for significance.
    On skewed returns the trimmed mean estimates 'mean of the middle 80% of days'.
    """
    from scipy.stats import trim_mean

    x = returns
    mean, med = float(x.mean()), float(x.median())
    tmean = float(trim_mean(x, trim))
    total = x.sum()
    top_n_sum = x.nlargest(top_n).sum()
    top_pct = float(top_n_sum / total) if abs(total) > 1e-15 else np.nan
    frag = (mean > 0 and 0 < tmean < 0.5 * mean) or (
        top_pct == top_pct and top_pct > 0.5
    )
    return {
        "name": "B1 edge concentration",
        "passed": None,  # diagnostic-only
        "details": {
            "mean": round(mean, 6),
            f"trimmed_mean_{int(trim*100)}pct": round(tmean, 6),
            "median": round(med, 6),
            f"top{top_n}_day_share_of_cum_return": (
                round(top_pct, 4) if top_pct == top_pct else None
            ),
            "verdict": (
                "OUTLIER-DEPENDENT edge (fragile, capacity-limited)"
                if frag
                else "edge spread across typical days"
            ),
        },
    }


def yuen_1samp(x, trim: float = 0.1, mu: float = 0.0) -> tuple[float, float]:
    """B2 (one-sample) — Yuen's test. scipy's ttest_1samp has NO trim param."""
    x = np.asarray(x, float)
    n = len(x)
    g = int(np.floor(trim * n))
    df = n - 2 * g - 1
    if df < 1 or n - g <= g:
        raise ValueError("sample too small for this trim level")
    xs = np.sort(x)
    w = xs.copy()
    w[:g] = xs[g]
    w[-g:] = xs[-g - 1]  # Winsorize
    se = np.sqrt(np.sum((w - w.mean()) ** 2) / df / ((1 - 2 * trim) ** 2 * n))
    t = (xs[g:-g].mean() - mu) / se
    return float(t), float(2 * sps.t.sf(abs(t), df))


def yuen_test(
    returns: pd.Series, other: pd.Series | None = None, trim: float = 0.1
) -> dict:
    """B2 — Yuen's trimmed t-test: one-sample vs 0, or two-sample via native scipy."""
    if other is None:
        t, p = yuen_1samp(returns.to_numpy(), trim=trim)
        label = f"one-sample Yuen (trim={trim}), mu=0"
    else:
        r = sps.ttest_ind(returns.dropna(), other.dropna(), trim=trim, equal_var=False)
        t, p = float(r.statistic), float(r.pvalue)
        label = f"two-sample Yuen (trim={trim}, Welch)"
    return {
        "name": "B2 Yuen trimmed t-test",
        "passed": p < 0.05,
        "details": {
            "test": label,
            "t": round(t, 3),
            "p": round(p, 4),
            "estimand": f"mean of the middle {int((1-2*trim)*100)}% of days",
        },
    }


def robust_sharpe(returns: pd.Series, trim: float = 0.1) -> dict:
    """B3 — Is my Sharpe tail-inflated? Robust variants alongside standard."""
    from scipy.stats import trim_mean
    from scipy.stats import mstats

    x = returns.to_numpy()
    std_sharpe = annualized_sharpe(x)
    wins_vol = float(
        np.asarray(mstats.winsorize(x, limits=[0.05, 0.05]), dtype=float).std(ddof=1)
    )
    rob = (
        float(trim_mean(x, trim) / wins_vol * np.sqrt(252)) if wins_vol > 1e-12 else 0.0
    )
    mad = float(np.median(np.abs(x - np.median(x))) * 1.4826)
    med_sharpe = float(np.median(x) / mad * np.sqrt(252)) if mad > 1e-12 else 0.0
    diverge = abs(std_sharpe) > 1e-9 and min(abs(rob), abs(med_sharpe)) < 0.5 * abs(
        std_sharpe
    )
    return {
        "name": "B3 robust Sharpe",
        "passed": None,  # diagnostic-only
        "details": {
            "standard_sharpe": round(std_sharpe, 3),
            "trimmed_winsorized_sharpe": round(rob, 3),
            "median_mad_sharpe": round(med_sharpe, 3),
            "note": (
                "robust variants <50% of standard → tail-inflated Sharpe"
                if diverge
                else "standard and robust Sharpes broadly consistent"
            ),
        },
    }


# ---------------------------------------------------------------- battery

_VERDICTS = [(80, "PASS"), (60, "CAUTION"), (40, "DOUBTFUL"), (0, "HIGH-RISK")]


def _score(results: list[dict]) -> dict:
    scored = [r for r in results if r["passed"] is not None]
    if not scored:
        return {"score": None, "verdict": "DIAGNOSTIC-ONLY"}
    passed = sum(1 for r in scored if r["passed"])
    score = passed / len(scored) * 100
    verdict = next(v for cut, v in _VERDICTS if score >= cut)
    return {
        "score": score,
        "verdict": verdict,
        "passed_count": passed,
        "total_count": len(scored),
    }


def run_battery(
    returns: pd.Series,
    group: str = "AB",
    bench_ret: pd.Series | None = None,
    sweep: pd.DataFrame | None = None,
    param_col: str = "param",
    metric_col: str = "metric",
    autocorr_block: int | None = None,
) -> dict:
    """Run Group A, Group B, or both (user's choice; never auto-invoked).

    autocorr_block: pass ~10 when Ljung-Box flagged autocorrelation
    (switches A1 to block sign-flips and A5 to moving-block bootstrap).
    """
    blk = autocorr_block or 1
    out: dict[str, list[dict] | dict] = {}
    if group in ("A", "AB"):
        a = [
            sign_flip_permutation(returns, block=blk),
            path_shuffle(returns),
            (
                regime_stress(returns, bench_ret)
                if bench_ret is not None
                else {
                    "name": "A3 regime stress",
                    "passed": None,
                    "details": {"skipped": "no benchmark provided"},
                }
            ),
            subperiod_consistency(returns),
            block_bootstrap(returns, block=blk),
        ]
        if sweep is not None:
            a.append(parameter_plateau(sweep, param_col, metric_col))
        else:
            a.append(
                {
                    "name": "A6 parameter plateau",
                    "passed": None,
                    "details": {
                        "skipped": "no sweep table (engine re-runs: fastbt #19)"
                    },
                }
            )
        out["group_a"], out["group_a_score"] = a, _score(a)
    if group in ("B", "AB"):
        b = [edge_concentration(returns), yuen_test(returns), robust_sharpe(returns)]
        out["group_b"], out["group_b_score"] = b, _score(b)
    if group == "AB":
        out["combined_score"] = _score(out["group_a"] + out["group_b"])
    return out


# ---------------------------------------------------------------- demo

if __name__ == "__main__":
    rng = np.random.default_rng(7)
    idx = pd.bdate_range("2022-01-03", periods=750)
    rets = pd.Series(rng.standard_t(4, 750) * 0.008 + 0.0006, index=idx)
    bench = pd.Series(rng.normal(0.0003, 0.010, 750), index=idx)
    sweep = pd.DataFrame(
        {"param": [0.5, 0.75, 1.0, 1.25, 1.5], "metric": [1.1, 1.4, 1.5, 1.45, 1.2]}
    )

    import json

    res = run_battery(rets, "AB", bench_ret=bench, sweep=sweep, autocorr_block=10)
    for grp in ("group_a", "group_b"):
        print(f"--- {grp} ---")
        for t in res[grp]:
            print(
                f"  {t['name']}: passed={t['passed']} {json.dumps(t['details'], default=str)[:160]}"
            )
        print(f"  score: {res[grp + '_score']}")
    print("combined:", res["combined_score"])
