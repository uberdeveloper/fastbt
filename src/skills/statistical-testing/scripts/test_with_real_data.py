"""
Test Statistical Testing Skill with Real Data

This script demonstrates the complete workflow using real market data:
1. Load NIFTY 50 data
2. Calculate returns
3. Test for positive alpha
4. Compare with VIX conditions
5. Generate reports
"""

import pandas as pd
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
from reporter import TweetStyleReporter, DetailedReporter  # noqa: E402


def load_and_prepare_nifty_data():
    """Load NIFTY 50 data and calculate returns"""
    print("=" * 70)
    print("STEP 1: Loading NIFTY 50 Data")
    print("=" * 70)

    # Load NIFTY data
    nifty_df = pd.read_csv("/home/pi/data/nifty.csv")
    print(f"\n✓ Loaded {len(nifty_df)} rows from nifty.csv")
    print(f"  Columns: {list(nifty_df.columns)}")
    print("\nFirst 5 rows:")
    print(nifty_df.head())

    # Parse date and sort
    nifty_df["Date"] = pd.to_datetime(nifty_df["Date"], format="%d-%b-%y")
    nifty_df = nifty_df.sort_values("Date").reset_index(drop=True)

    # Calculate returns
    nifty_df["returns"] = nifty_df["Close"].pct_change()
    nifty_df = nifty_df.dropna()

    print("\n✓ Calculated returns")
    print(f"  Date range: {nifty_df['Date'].min()} to {nifty_df['Date'].max()}")
    print(f"  Total observations: {len(nifty_df)}")
    print(f"  Mean return: {nifty_df['returns'].mean():.6f}")
    print(f"  Std dev: {nifty_df['returns'].std():.6f}")

    return nifty_df


def test_1_nifty_alpha():
    """Test 1: Does NIFTY 50 have positive returns?"""
    print("\n\n" + "=" * 70)
    print("TEST 1: NIFTY 50 Alpha Test")
    print("=" * 70)
    print("\nHypothesis: NIFTY 50 has positive returns")

    # Load data
    nifty_df = load_and_prepare_nifty_data()
    returns = nifty_df["returns"].values

    # Distribution check
    print("\n" + "-" * 70)
    print("Distribution Analysis")
    print("-" * 70)
    checker = DistributionChecker()
    dist_result = checker.check_normality(returns)

    print("\nNormality Tests:")
    print(f"  Shapiro-Wilk p-value: {dist_result['shapiro_p']:.4f}")
    print(f"  Jarque-Bera p-value: {dist_result['jarque_bera_p']:.4f}")
    print(f"  Distribution: {'Normal' if dist_result['is_normal'] else 'Non-normal'}")
    print(f"  Skewness: {dist_result['skewness']:.4f}")
    print(f"  Kurtosis: {dist_result['kurtosis']:.4f}")
    print(f"  Recommendation: Use {dist_result['recommendation']} tests")

    # Hypothesis test
    print("\n" + "-" * 70)
    print("Hypothesis Test")
    print("-" * 70)
    tester = HypothesisTests()
    test_result = tester.one_sample_test(
        returns, mu=0.0, use_parametric=dist_result["is_normal"]
    )

    print(f"\nTest: {test_result.test_name}")
    print(f"  Test Statistic: {test_result.statistic:.4f}")
    print(f"  p-value: {test_result.p_value:.4f}")
    print(f"  Significant at 95%: {test_result.significant}")
    print(f"  Interpretation: {test_result.interpretation}")

    # Performance metrics
    print("\n" + "-" * 70)
    print("Performance Metrics")
    print("-" * 70)
    metrics = PerformanceMetrics.calculate_all_metrics(returns, periods_per_year=252)

    print("\nReturns:")
    print(f"  Mean (daily): {metrics['mean_return']:.4%}")
    print(f"  Median (daily): {metrics['median_return']:.4%}")
    print(f"  Std Dev: {metrics['std_dev']:.4%}")

    print("\nRisk-Adjusted:")
    print(f"  Sharpe Ratio: {metrics['sharpe_ratio']:.2f}")
    print(f"  Max Drawdown: {metrics['max_drawdown']:.2%}")
    print(f"  Win Rate: {metrics['win_rate']:.2%}")

    # Generate tweet summary
    print("\n" + "-" * 70)
    print("Tweet-Style Summary")
    print("-" * 70)
    reporter = TweetStyleReporter()
    test_dict = {
        "test_name": test_result.test_name,
        "p_value": test_result.p_value,
        "significant": test_result.significant,
        "distribution_type": test_result.distribution_type,
    }
    summary = reporter.performance_test_summary(test_dict, metrics)
    print("\n" + summary)

    # Save detailed report
    detailed_reporter = DetailedReporter()
    report = detailed_reporter.full_report(
        test_type="NIFTY 50 Performance Test",
        test_results=[
            {
                "test_name": test_result.test_name,
                "statistic": test_result.statistic,
                "p_value": test_result.p_value,
                "significant": test_result.significant,
                "confidence_level": test_result.confidence_level,
                "interpretation": test_result.interpretation,
            }
        ],
        metrics=metrics,
        distribution_check=dist_result,
        warnings=(
            [] if dist_result["is_normal"] else ["Returns not normally distributed"]
        ),
        additional_info={
            "data_source": "NIFTY 50 historical data",
            "period": f"{nifty_df['Date'].min().strftime('%Y-%m-%d')} to {nifty_df['Date'].max().strftime('%Y-%m-%d')}",
            "observations": len(nifty_df),
        },
    )

    filepath = detailed_reporter.save_report(
        report, filename="nifty50_alpha_test.md", output_dir="/tmp"
    )
    print(f"\n✓ Detailed report saved to: {filepath}")

    return nifty_df


def test_2_vix_conditional_analysis():
    """Test 2: Does NIFTY perform differently during high VIX?"""
    print("\n\n" + "=" * 70)
    print("TEST 2: Conditional Analysis - NIFTY Returns vs VIX")
    print("=" * 70)
    print("\nHypothesis: NIFTY returns differ when VIX > 20")

    # Load NIFTY data
    nifty_df = pd.read_csv("/home/pi/data/nifty.csv")
    nifty_df["Date"] = pd.to_datetime(nifty_df["Date"], format="%d-%b-%y")
    nifty_df = nifty_df.sort_values("Date").reset_index(drop=True)
    nifty_df["returns"] = nifty_df["Close"].pct_change()
    nifty_df = nifty_df.dropna()

    # Load VIX data
    vix_df = pd.read_csv("/home/pi/data/vix.csv")
    vix_df["date"] = pd.to_datetime(vix_df["date"], format="%d-%b-%y")
    vix_df = vix_df.rename(columns={"date": "Date", "close": "VIX"})

    # Merge
    merged_df = pd.merge(
        nifty_df[["Date", "returns"]], vix_df[["Date", "VIX"]], on="Date", how="inner"
    )

    print("\n✓ Merged NIFTY and VIX data")
    print(f"  Observations: {len(merged_df)}")
    print(f"  Date range: {merged_df['Date'].min()} to {merged_df['Date'].max()}")
    print(f"  VIX range: {merged_df['VIX'].min():.2f} to {merged_df['VIX'].max():.2f}")

    # Parse condition
    print("\n" + "-" * 70)
    print("Conditional Filter")
    print("-" * 70)
    parser = ConditionParser()
    cond_filter = parser.parse_multiple_conditions("VIX > 20")

    print(
        f"\nCondition: {cond_filter.conditions[0].column} {cond_filter.conditions[0].operator} {cond_filter.conditions[0].value}"
    )

    # Segment data
    segmenter = DataSegmenter()
    result = segmenter.segment_data(merged_df, cond_filter, min_observations=30)

    print("\nSegmentation Results:")
    print(
        f"  VIX > 20: {result['n_true']} observations ({result['n_true']/len(merged_df)*100:.1f}%)"
    )
    print(
        f"  VIX ≤ 20: {result['n_false']} observations ({result['n_false']/len(merged_df)*100:.1f}%)"
    )

    if result["warnings"]:
        for warning in result["warnings"]:
            print(f"  ⚠️ {warning}")

    # Compare returns
    print("\n" + "-" * 70)
    print("Metric Comparison")
    print("-" * 70)
    analyzer = ConditionalAnalyzer()
    comparison = analyzer.compare_metric(
        result["group_true"], result["group_false"], "returns", "Returns"
    )

    print("\nReturns Statistics:")
    print("  VIX > 20:")
    print(f"    Mean: {comparison['group_true']['mean']:.4%}")
    print(f"    Median: {comparison['group_true']['median']:.4%}")
    print(f"    Std Dev: {comparison['group_true']['std']:.4%}")

    print("\n  VIX ≤ 20:")
    print(f"    Mean: {comparison['group_false']['mean']:.4%}")
    print(f"    Median: {comparison['group_false']['median']:.4%}")
    print(f"    Std Dev: {comparison['group_false']['std']:.4%}")

    print("\n  Difference:")
    print(f"    Mean: {comparison['difference']['mean']:.4%}")
    print(f"    Median: {comparison['difference']['median']:.4%}")

    # Statistical test
    print("\n" + "-" * 70)
    print("Statistical Test")
    print("-" * 70)
    tester = HypothesisTests()
    test_result = tester.independent_test(
        result["group_true"]["returns"].values,
        result["group_false"]["returns"].values,
        use_parametric=False,  # Use non-parametric for safety
    )

    print(f"\nTest: {test_result.test_name}")
    print(f"  Test Statistic: {test_result.statistic:.4f}")
    print(f"  p-value: {test_result.p_value:.4f}")
    print(f"  Significant at 95%: {test_result.significant}")

    # Generate summary
    print("\n" + "-" * 70)
    print("Tweet-Style Summary")
    print("-" * 70)
    reporter = TweetStyleReporter()
    test_dict = {
        "test_name": test_result.test_name,
        "p_value": test_result.p_value,
        "significant": test_result.significant,
        "distribution_type": "non-normal",
    }
    summary = reporter.conditional_analysis_summary(
        "VIX > 20", "Returns", comparison, test_dict
    )
    print("\n" + summary)

    # Save report
    detailed_reporter = DetailedReporter()
    report = detailed_reporter.full_report(
        test_type="Conditional Analysis: NIFTY Returns vs VIX",
        test_results=[
            {
                "test_name": test_result.test_name,
                "statistic": test_result.statistic,
                "p_value": test_result.p_value,
                "significant": test_result.significant,
                "confidence_level": 0.95,
                "interpretation": f"{'Significant' if test_result.significant else 'No significant'} difference in returns when VIX > 20",
            }
        ],
        metrics={
            "vix_high_mean": comparison["group_true"]["mean"],
            "vix_low_mean": comparison["group_false"]["mean"],
            "difference": comparison["difference"]["mean"],
        },
        distribution_check=None,
        warnings=result["warnings"],
        additional_info={
            "condition": "VIX > 20",
            "n_high_vix": result["n_true"],
            "n_low_vix": result["n_false"],
        },
    )

    filepath = detailed_reporter.save_report(
        report, filename="nifty_vix_conditional_analysis.md", output_dir="/tmp"
    )
    print(f"\n✓ Detailed report saved to: {filepath}")


def test_3_regime_analysis():
    """Test 3: Performance across market regimes"""
    print("\n\n" + "=" * 70)
    print("TEST 3: Market Regime Analysis")
    print("=" * 70)

    # Load NIFTY data
    nifty_df = pd.read_csv("/home/pi/data/nifty.csv")
    nifty_df["Date"] = pd.to_datetime(nifty_df["Date"], format="%d-%b-%y")
    nifty_df = nifty_df.sort_values("Date").reset_index(drop=True)
    nifty_df["returns"] = nifty_df["Close"].pct_change()
    nifty_df = nifty_df.dropna()

    # Load regime data
    regime_df = pd.read_csv("/home/pi/data/regimes.csv")
    regime_df["date"] = pd.to_datetime(regime_df["date"])
    regime_df = regime_df.rename(columns={"date": "Date"})

    # Merge
    merged_df = pd.merge(
        nifty_df[["Date", "returns"]],
        regime_df[["Date", "regime"]],
        on="Date",
        how="inner",
    )

    # Remove empty regimes
    merged_df = merged_df[merged_df["regime"].notna() & (merged_df["regime"] != "")]

    print("\n✓ Merged NIFTY and regime data")
    print(f"  Observations: {len(merged_df)}")
    print(f"  Regimes found: {merged_df['regime'].unique()}")
    print("\nRegime distribution:")
    print(merged_df["regime"].value_counts())

    # Compare regimes
    print("\n" + "-" * 70)
    print("Performance by Regime")
    print("-" * 70)

    regime_stats = (
        merged_df.groupby("regime")["returns"]
        .agg(
            [("count", "count"), ("mean", "mean"), ("median", "median"), ("std", "std")]
        )
        .round(6)
    )

    print("\n" + regime_stats.to_string())

    print("\n✓ Regime analysis complete")
    print("  Note: Statistical tests require at least 2 regimes with sufficient data")


if __name__ == "__main__":
    print("\n" + "=" * 70)
    print("STATISTICAL TESTING SKILL - REAL DATA TESTS")
    print("=" * 70)

    try:
        # Test 1: NIFTY Alpha
        test_1_nifty_alpha()

        # Test 2: VIX Conditional Analysis
        test_2_vix_conditional_analysis()

        # Test 3: Regime Analysis
        test_3_regime_analysis()

        print("\n\n" + "=" * 70)
        print("ALL TESTS COMPLETED SUCCESSFULLY")
        print("=" * 70)
        print("\nReports saved to /tmp/:")
        print("  - nifty50_alpha_test.md")
        print("  - nifty_vix_conditional_analysis.md")

    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback

        traceback.print_exc()
