"""
Interactive Quant Testing Session

Simulating a quant user asking questions to test the statistical testing skill.
This demonstrates realistic use cases and validates the skill's responses.
"""

import pandas as pd
import numpy as np
import sys
from pathlib import Path

# Add scripts directory to path
script_dir = Path(__file__).parent
sys.path.insert(0, str(script_dir))

from test_engine import (  # noqa: E402
    DistributionChecker,
    HypothesisTests,
    PerformanceMetrics,
)
from conditional_filter import (
    ConditionParser,
    DataSegmenter,
    ConditionalAnalyzer,
)  # noqa: E402
from reporter import TweetStyleReporter  # noqa: E402


def quant_question_1():
    """
    QUANT ASKS: "I backtested a momentum strategy on NIFTY 50.
    Is the alpha real or just luck? File: nifty.csv"
    """
    print("\n" + "=" * 80)
    print("QUANT QUESTION 1")
    print("=" * 80)
    print('\nUSER: "I backtested a momentum strategy on NIFTY 50.')
    print('       Is the alpha real or just luck? File: nifty.csv"')
    print("\n" + "-" * 80)

    # Load and prepare data
    df = pd.read_csv("/home/pi/data/nifty.csv")
    df["Date"] = pd.to_datetime(df["Date"], format="%d-%b-%y")
    df = df.sort_values("Date").reset_index(drop=True)
    df["returns"] = df["Close"].pct_change()
    df = df.dropna()

    print("\nAGENT: I'll analyze your NIFTY 50 data.")
    print(
        f"       Found {len(df)} observations from {df['Date'].min().date()} to {df['Date'].max().date()}"
    )

    # Check distribution
    checker = DistributionChecker()
    dist_result = checker.check_normality(df["returns"].values)

    print(
        f"\n       Distribution check: {'Normal' if dist_result['is_normal'] else 'Non-normal'}"
    )
    print(f"       → Using {dist_result['recommendation']} tests")

    # Run test
    tester = HypothesisTests()
    test_result = tester.one_sample_test(
        df["returns"].values, use_parametric=dist_result["is_normal"]
    )

    # Calculate metrics
    metrics = PerformanceMetrics.calculate_all_metrics(df["returns"].values)

    # Generate response
    reporter = TweetStyleReporter()
    test_dict = {
        "test_name": test_result.test_name,
        "p_value": test_result.p_value,
        "significant": test_result.significant,
        "distribution_type": test_result.distribution_type,
    }
    summary = reporter.performance_test_summary(test_dict, metrics)

    print("\nAGENT RESPONSE:")
    print(summary)

    return df


def quant_question_2():
    """
    QUANT ASKS: "Does my strategy perform worse during high volatility?
    I have VIX data. Can you test if returns are lower when VIX > 15?"
    """
    print("\n" + "=" * 80)
    print("QUANT QUESTION 2")
    print("=" * 80)
    print('\nUSER: "Does my strategy perform worse during high volatility?')
    print('       I have VIX data. Can you test if returns are lower when VIX > 15?"')
    print("\n" + "-" * 80)

    # Load data
    nifty_df = pd.read_csv("/home/pi/data/nifty.csv")
    nifty_df["Date"] = pd.to_datetime(nifty_df["Date"], format="%d-%b-%y")
    nifty_df = nifty_df.sort_values("Date").reset_index(drop=True)
    nifty_df["returns"] = nifty_df["Close"].pct_change()
    nifty_df = nifty_df.dropna()

    vix_df = pd.read_csv("/home/pi/data/vix.csv")
    vix_df["date"] = pd.to_datetime(vix_df["date"], format="%d-%b-%y")
    vix_df = vix_df.rename(columns={"date": "Date", "close": "VIX"})

    merged_df = pd.merge(
        nifty_df[["Date", "returns"]], vix_df[["Date", "VIX"]], on="Date", how="inner"
    )

    print("\nAGENT: I'll test the condition 'VIX > 15'")
    print(f"       Merged {len(merged_df)} observations")

    # Parse and segment
    parser = ConditionParser()
    cond_filter = parser.parse_multiple_conditions("VIX > 15")

    segmenter = DataSegmenter()
    result = segmenter.segment_data(merged_df, cond_filter, min_observations=10)

    print(
        f"\n       VIX > 15: {result['n_true']} observations ({result['n_true']/len(merged_df)*100:.1f}%)"
    )
    print(
        f"       VIX ≤ 15: {result['n_false']} observations ({result['n_false']/len(merged_df)*100:.1f}%)"
    )

    # Compare
    analyzer = ConditionalAnalyzer()
    comparison = analyzer.compare_metric(
        result["group_true"], result["group_false"], "returns", "Returns"
    )

    # Test
    tester = HypothesisTests()
    test_result = tester.independent_test(
        result["group_true"]["returns"].values,
        result["group_false"]["returns"].values,
        use_parametric=False,
    )

    # Generate response
    reporter = TweetStyleReporter()
    test_dict = {
        "test_name": test_result.test_name,
        "p_value": test_result.p_value,
        "significant": test_result.significant,
        "distribution_type": "non-normal",
    }
    summary = reporter.conditional_analysis_summary(
        "VIX > 15", "Returns", comparison, test_dict
    )

    print("\nAGENT RESPONSE:")
    print(summary)

    # Additional insight
    if comparison["group_true"]["mean"] < comparison["group_false"]["mean"]:
        print("💡 INSIGHT: Returns are indeed lower during high VIX periods,")
        print(
            f"   but {'NOT statistically significant' if not test_result.significant else 'statistically significant'}."
        )

    return merged_df


def quant_question_3():
    """
    QUANT ASKS: "I'm skeptical about the Sharpe ratio.
    What's the actual distribution of my returns? Are there fat tails?"
    """
    print("\n" + "=" * 80)
    print("QUANT QUESTION 3")
    print("=" * 80)
    print("\nUSER: \"I'm skeptical about the Sharpe ratio.")
    print("       What's the actual distribution of my returns? Are there fat tails?\"")
    print("\n" + "-" * 80)

    # Load data
    df = pd.read_csv("/home/pi/data/nifty.csv")
    df["Date"] = pd.to_datetime(df["Date"], format="%d-%b-%y")
    df = df.sort_values("Date").reset_index(drop=True)
    df["returns"] = df["Close"].pct_change()
    df = df.dropna()

    returns = df["returns"].values

    print("\nAGENT: Let me analyze the distribution characteristics...")

    # Distribution analysis
    checker = DistributionChecker()
    dist_result = checker.check_normality(returns)

    # Calculate additional stats

    print("\n" + "-" * 80)
    print("DISTRIBUTION ANALYSIS")
    print("-" * 80)

    print("\nNormality Tests:")
    print(f"  Shapiro-Wilk p-value: {dist_result['shapiro_p']:.6f}")
    print(f"  Jarque-Bera p-value: {dist_result['jarque_bera_p']:.6f}")
    print(f"  → {'NORMAL' if dist_result['is_normal'] else 'NOT NORMAL'} distribution")

    print("\nDistribution Shape:")
    print(f"  Skewness: {dist_result['skewness']:.4f}")
    if dist_result["skewness"] > 0.5:
        print("    → Positive skew (right tail is longer)")
    elif dist_result["skewness"] < -0.5:
        print("    → Negative skew (left tail is longer)")
    else:
        print("    → Roughly symmetric")

    print(f"\n  Excess Kurtosis: {dist_result['kurtosis']:.4f}")
    if dist_result["kurtosis"] > 1:
        print("    → FAT TAILS (leptokurtic) - more extreme events than normal")
    elif dist_result["kurtosis"] < -1:
        print("    → THIN TAILS (platykurtic) - fewer extreme events")
    else:
        print("    → Similar to normal distribution")

    # Tail analysis
    print("\nTail Events:")
    mean = np.mean(returns)
    std = np.std(returns)

    # Count events beyond 2 and 3 standard deviations
    beyond_2std = np.sum(np.abs(returns - mean) > 2 * std)
    beyond_3std = np.sum(np.abs(returns - mean) > 3 * std)

    # Expected for normal distribution
    expected_2std = len(returns) * 0.0455  # ~4.55% for normal
    expected_3std = len(returns) * 0.0027  # ~0.27% for normal

    print(f"  Beyond 2σ: {beyond_2std} ({beyond_2std/len(returns)*100:.1f}%)")
    print(
        f"    Expected (normal): {expected_2std:.1f} ({expected_2std/len(returns)*100:.1f}%)"
    )

    print(f"  Beyond 3σ: {beyond_3std} ({beyond_3std/len(returns)*100:.1f}%)")
    print(
        f"    Expected (normal): {expected_3std:.1f} ({expected_3std/len(returns)*100:.1f}%)"
    )

    if beyond_2std > expected_2std * 1.5:
        print("\n  ⚠️ WARNING: Significantly more tail events than expected!")
        print("     Sharpe ratio may underestimate risk.")

    # Percentiles
    print("\nReturn Percentiles:")
    percentiles = [1, 5, 25, 50, 75, 95, 99]
    for p in percentiles:
        val = np.percentile(returns, p)
        print(f"  {p:2d}th: {val:7.4%}")

    print("\n" + "-" * 80)
    print("AGENT SUMMARY:")
    print("-" * 80)

    if dist_result["kurtosis"] > 1:
        print("\n🎯 Your returns have FAT TAILS - there are more extreme events")
        print("   than a normal distribution would predict.")
        print("\n💡 IMPLICATIONS:")
        print("   - Sharpe ratio may underestimate risk")
        print("   - Consider using downside deviation or CVaR")
        print("   - Tail risk hedging may be important")
    else:
        print("\n✓ Returns distribution is relatively well-behaved")
        print("  Sharpe ratio is a reasonable risk metric")


def quant_question_4():
    """
    QUANT ASKS: "Quick question - what's my win rate and max drawdown?
    Just the numbers, no fancy stats needed."
    """
    print("\n" + "=" * 80)
    print("QUANT QUESTION 4")
    print("=" * 80)
    print("\nUSER: \"Quick question - what's my win rate and max drawdown?")
    print('       Just the numbers, no fancy stats needed."')
    print("\n" + "-" * 80)

    # Load data
    df = pd.read_csv("/home/pi/data/nifty.csv")
    df["Date"] = pd.to_datetime(df["Date"], format="%d-%b-%y")
    df = df.sort_values("Date").reset_index(drop=True)
    df["returns"] = df["Close"].pct_change()
    df = df.dropna()

    # Calculate metrics
    metrics = PerformanceMetrics.calculate_all_metrics(df["returns"].values)

    print("\nAGENT: Here are your key metrics:")
    print(f"\n  Win Rate: {metrics['win_rate']:.2%}")
    print(f"  Max Drawdown: {metrics['max_drawdown']:.2%}")
    print(
        f"\n  (Also calculated Sharpe: {metrics['sharpe_ratio']:.2f} - in case you need it)"
    )


def quant_question_5():
    """
    QUANT ASKS: "I want to compare performance across different market regimes.
    I have a regime column. Can you break down returns by regime?"
    """
    print("\n" + "=" * 80)
    print("QUANT QUESTION 5")
    print("=" * 80)
    print('\nUSER: "I want to compare performance across different market regimes.')
    print('       I have a regime column. Can you break down returns by regime?"')
    print("\n" + "-" * 80)

    # Load data
    nifty_df = pd.read_csv("/home/pi/data/nifty.csv")
    nifty_df["Date"] = pd.to_datetime(nifty_df["Date"], format="%d-%b-%y")
    nifty_df = nifty_df.sort_values("Date").reset_index(drop=True)
    nifty_df["returns"] = nifty_df["Close"].pct_change()
    nifty_df = nifty_df.dropna()

    regime_df = pd.read_csv("/home/pi/data/regimes.csv")
    regime_df["date"] = pd.to_datetime(regime_df["date"])
    regime_df = regime_df.rename(columns={"date": "Date"})

    merged_df = pd.merge(
        nifty_df[["Date", "returns"]],
        regime_df[["Date", "regime"]],
        on="Date",
        how="inner",
    )
    merged_df = merged_df[merged_df["regime"].notna() & (merged_df["regime"] != "")]

    print(
        f"\nAGENT: Found {len(merged_df)} observations across {merged_df['regime'].nunique()} regimes"
    )
    print(f"       Regimes: {', '.join(merged_df['regime'].unique())}")

    # Calculate stats by regime
    print("\n" + "-" * 80)
    print("PERFORMANCE BY REGIME")
    print("-" * 80)

    regime_stats = merged_df.groupby("regime")["returns"].agg(
        [
            ("N", "count"),
            ("Mean", lambda x: f"{x.mean():.4%}"),
            ("Median", lambda x: f"{x.median():.4%}"),
            ("Std", lambda x: f"{x.std():.4%}"),
            (
                "Sharpe",
                lambda x: (
                    f"{(x.mean() / x.std() * np.sqrt(252)):.2f}"
                    if x.std() > 0
                    else "N/A"
                ),
            ),
            ("Win Rate", lambda x: f"{(x > 0).sum() / len(x):.2%}"),
        ]
    )

    print("\n" + regime_stats.to_string())

    # Best/worst regimes
    mean_by_regime = merged_df.groupby("regime")["returns"].mean()
    best_regime = mean_by_regime.idxmax()
    worst_regime = mean_by_regime.idxmin()

    print("\n" + "-" * 80)
    print("KEY INSIGHTS")
    print("-" * 80)
    print(
        f"\n  Best Regime: {best_regime} ({mean_by_regime[best_regime]:.4%} mean return)"
    )
    print(
        f"  Worst Regime: {worst_regime} ({mean_by_regime[worst_regime]:.4%} mean return)"
    )

    # Statistical test between best and worst
    best_returns = merged_df[merged_df["regime"] == best_regime]["returns"].values
    worst_returns = merged_df[merged_df["regime"] == worst_regime]["returns"].values

    if len(best_returns) >= 10 and len(worst_returns) >= 10:
        tester = HypothesisTests()
        test_result = tester.independent_test(
            best_returns, worst_returns, use_parametric=False
        )

        print(f"\n  Statistical Test ({best_regime} vs {worst_regime}):")
        print(f"    p-value: {test_result.p_value:.4f}")
        print(
            f"    Significant difference: {'Yes' if test_result.significant else 'No'}"
        )


if __name__ == "__main__":
    print("\n" + "=" * 80)
    print("INTERACTIVE QUANT TESTING SESSION")
    print("Statistical Testing Skill - Real User Scenarios")
    print("=" * 80)

    try:
        quant_question_1()
        quant_question_2()
        quant_question_3()
        quant_question_4()
        quant_question_5()

        print("\n\n" + "=" * 80)
        print("SESSION COMPLETE")
        print("=" * 80)
        print("\n✓ All quant questions answered successfully")
        print("✓ Skill demonstrated flexibility and appropriate responses")
        print("✓ Both concise and detailed outputs provided as needed")

    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback

        traceback.print_exc()
