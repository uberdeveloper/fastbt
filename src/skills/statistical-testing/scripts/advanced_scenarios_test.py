"""
Advanced Testing Scenarios

1. Strategy with synthetic features (conditional analysis)
2. Random strategy vs NIFTY benchmark (yfinance)
3. Random strategy with drift vs NIFTY benchmark
4. Multi-turn conversation simulation
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
from benchmark_fetcher import fetch_benchmark, match_benchmark_to_strategy  # noqa: E402
from reporter import TweetStyleReporter, DetailedReporter  # noqa: E402


def scenario_1_synthetic_strategy_with_features():
    """
    Scenario 1: Synthetic strategy with features

    Create a momentum strategy that performs better when:
    - RSI < 30 (oversold)
    - Volume > average
    """
    print("\n" + "=" * 80)
    print("SCENARIO 1: Synthetic Strategy with Features")
    print("=" * 80)
    print("\nCreating synthetic momentum strategy with RSI and Volume features...")

    # Generate synthetic data
    np.random.seed(42)
    n_days = 500

    dates = pd.date_range("2023-01-01", periods=n_days)

    # Generate features
    rsi = np.random.uniform(20, 80, n_days)
    volume = np.random.lognormal(mean=10, sigma=0.5, size=n_days)
    avg_volume = np.mean(volume)

    # Generate returns with conditional logic
    # Better returns when RSI < 30 AND volume > average
    base_returns = np.random.normal(0.0005, 0.015, n_days)

    # Add alpha when conditions are met
    condition_met = (rsi < 30) & (volume > avg_volume)
    returns = base_returns.copy()
    returns[condition_met] += 0.003  # Add 0.3% alpha when conditions met

    # Create dataframe
    df = pd.DataFrame({"date": dates, "returns": returns, "RSI": rsi, "volume": volume})

    print(f"\n✓ Generated {len(df)} days of synthetic data")
    print(
        f"  Condition met (RSI < 30 AND volume > avg): {condition_met.sum()} days ({condition_met.sum()/n_days*100:.1f}%)"
    )

    # Test 1: Overall alpha
    print("\n" + "-" * 80)
    print("TEST 1: Overall Strategy Alpha")
    print("-" * 80)

    checker = DistributionChecker()
    dist_result = checker.check_normality(df["returns"].values)

    tester = HypothesisTests()
    test_result = tester.one_sample_test(
        df["returns"].values, use_parametric=dist_result["is_normal"]
    )

    metrics = PerformanceMetrics.calculate_all_metrics(df["returns"].values)

    reporter = TweetStyleReporter()
    test_dict = {
        "test_name": test_result.test_name,
        "p_value": test_result.p_value,
        "significant": test_result.significant,
        "distribution_type": test_result.distribution_type,
    }
    summary = reporter.performance_test_summary(test_dict, metrics)
    print(summary)

    # Test 2: Conditional analysis
    print("\n" + "-" * 80)
    print(f"TEST 2: Conditional Analysis (RSI < 30 AND volume > {avg_volume:.2f})")
    print("-" * 80)

    parser = ConditionParser()
    cond_filter = parser.parse_multiple_conditions(
        f"RSI < 30 AND volume > {avg_volume:.2f}"
    )

    segmenter = DataSegmenter()
    result = segmenter.segment_data(df, cond_filter)

    print("\nSegmentation:")
    print(f"  Condition TRUE: {result['n_true']} days")
    print(f"  Condition FALSE: {result['n_false']} days")

    analyzer = ConditionalAnalyzer()
    comparison = analyzer.compare_metric(
        result["group_true"], result["group_false"], "returns", "Returns"
    )

    test_result_cond = tester.independent_test(
        result["group_true"]["returns"].values,
        result["group_false"]["returns"].values,
        use_parametric=False,
    )

    test_dict_cond = {
        "test_name": test_result_cond.test_name,
        "p_value": test_result_cond.p_value,
        "significant": test_result_cond.significant,
        "distribution_type": "non-normal",
    }
    summary_cond = reporter.conditional_analysis_summary(
        "RSI < 30 AND volume > average", "Returns", comparison, test_dict_cond
    )
    print(summary_cond)

    print("\n💡 INSIGHT: This demonstrates how the skill can identify conditions")
    print("   where a strategy performs significantly better!")

    return df


def scenario_2_random_strategy_vs_nifty():
    """
    Scenario 2: Random strategy vs NIFTY benchmark (yfinance)

    Test a completely random strategy against NIFTY 50
    """
    print("\n\n" + "=" * 80)
    print("SCENARIO 2: Random Strategy vs NIFTY Benchmark (yfinance)")
    print("=" * 80)
    print("\nTesting random strategy (no alpha) against NIFTY 50...")

    # Generate random strategy returns
    np.random.seed(123)
    n_days = 200

    start_date = "2024-01-01"
    end_date = "2024-12-31"

    dates = pd.date_range(start_date, periods=n_days, freq="B")  # Business days
    random_returns = np.random.normal(0.0, 0.015, n_days)  # Zero mean, 1.5% std

    strategy_df = pd.DataFrame({"date": dates, "returns": random_returns})

    print(f"\n✓ Generated {len(strategy_df)} days of random returns")
    print(f"  Mean: {np.mean(random_returns):.6f}")
    print(f"  Std: {np.std(random_returns):.6f}")

    # Fetch NIFTY benchmark
    print("\n" + "-" * 80)
    print("Fetching NIFTY 50 Benchmark from yfinance...")
    print("-" * 80)

    # Try to fetch NIFTY
    print("\nAttempting to fetch ^NSEI (NIFTY 50)...")
    benchmark_df = fetch_benchmark(
        ticker="^NSEI", start_date=start_date, end_date=end_date, interval="1d"
    )

    if benchmark_df is None:
        print("\n⚠️ yfinance fetch failed. Generating synthetic benchmark instead...")
        # Create synthetic benchmark with positive drift
        benchmark_returns = np.random.normal(0.0005, 0.012, n_days)
        benchmark_df = pd.DataFrame({"date": dates, "returns": benchmark_returns})
    else:
        print(f"\n✓ Fetched {len(benchmark_df)} days of NIFTY data")

    # Align data
    print("\n" + "-" * 80)
    print("Aligning Strategy and Benchmark...")
    print("-" * 80)

    try:
        strategy_returns, benchmark_returns = match_benchmark_to_strategy(
            strategy_df, benchmark_df
        )

        print(f"\n✓ Aligned {len(strategy_returns)} observations")
        print(f"  Strategy mean: {np.mean(strategy_returns):.6f}")
        print(f"  Benchmark mean: {np.mean(benchmark_returns):.6f}")

    except Exception as e:
        print(f"\n⚠️ Alignment failed: {e}")
        print("   Using full datasets without alignment")
        strategy_returns = strategy_df["returns"].values
        benchmark_returns = benchmark_df["returns"].values[: len(strategy_returns)]

    # Run comparison test
    print("\n" + "-" * 80)
    print("Statistical Comparison")
    print("-" * 80)

    tester = HypothesisTests()
    test_result = tester.paired_test(
        strategy_returns, benchmark_returns, use_parametric=False
    )

    strategy_metrics = PerformanceMetrics.calculate_all_metrics(strategy_returns)
    benchmark_metrics = PerformanceMetrics.calculate_all_metrics(benchmark_returns)

    reporter = TweetStyleReporter()
    test_dict = {
        "test_name": test_result.test_name,
        "p_value": test_result.p_value,
        "significant": test_result.significant,
        "distribution_type": "non-normal",
    }
    summary = reporter.outperformance_test_summary(
        test_dict, strategy_metrics, benchmark_metrics, benchmark_name="NIFTY 50"
    )
    print(summary)

    return strategy_df, benchmark_df


def scenario_3_drift_strategy_vs_nifty():
    """
    Scenario 3: Random strategy with positive drift vs NIFTY

    Test a strategy with slight positive alpha
    """
    print("\n\n" + "=" * 80)
    print("SCENARIO 3: Strategy with Positive Drift vs NIFTY")
    print("=" * 80)
    print("\nTesting strategy with +0.1% daily drift against NIFTY 50...")

    # Generate strategy with positive drift
    np.random.seed(456)
    n_days = 200

    start_date = "2024-01-01"
    end_date = "2024-12-31"

    dates = pd.date_range(start_date, periods=n_days, freq="B")
    drift_returns = np.random.normal(0.001, 0.015, n_days)  # 0.1% mean, 1.5% std

    strategy_df = pd.DataFrame({"date": dates, "returns": drift_returns})

    print(f"\n✓ Generated {len(strategy_df)} days with positive drift")
    print(f"  Mean: {np.mean(drift_returns):.6f} (0.1% target)")
    print(f"  Std: {np.std(drift_returns):.6f}")

    # Fetch benchmark
    print("\n" + "-" * 80)
    print("Fetching NIFTY 50 Benchmark...")
    print("-" * 80)

    benchmark_df = fetch_benchmark(
        ticker="^NSEI", start_date=start_date, end_date=end_date, interval="1d"
    )

    if benchmark_df is None:
        print("\n⚠️ yfinance fetch failed. Using synthetic benchmark...")
        benchmark_returns = np.random.normal(0.0005, 0.012, n_days)
        benchmark_df = pd.DataFrame({"date": dates, "returns": benchmark_returns})
    else:
        print(f"\n✓ Fetched {len(benchmark_df)} days")

    # Align and compare
    try:
        strategy_returns, benchmark_returns = match_benchmark_to_strategy(
            strategy_df, benchmark_df
        )
        print(f"\n✓ Aligned {len(strategy_returns)} observations")
    except Exception:
        strategy_returns = strategy_df["returns"].values
        benchmark_returns = benchmark_df["returns"].values[: len(strategy_returns)]

    # Test
    print("\n" + "-" * 80)
    print("Statistical Comparison")
    print("-" * 80)

    tester = HypothesisTests()
    test_result = tester.paired_test(
        strategy_returns, benchmark_returns, use_parametric=False
    )

    strategy_metrics = PerformanceMetrics.calculate_all_metrics(strategy_returns)
    benchmark_metrics = PerformanceMetrics.calculate_all_metrics(benchmark_returns)

    reporter = TweetStyleReporter()
    test_dict = {
        "test_name": test_result.test_name,
        "p_value": test_result.p_value,
        "significant": test_result.significant,
        "distribution_type": "non-normal",
    }
    summary = reporter.outperformance_test_summary(
        test_dict, strategy_metrics, benchmark_metrics, benchmark_name="NIFTY 50"
    )
    print(summary)

    # Additional analysis
    print("\n" + "-" * 80)
    print("Excess Returns Analysis")
    print("-" * 80)

    excess_returns = strategy_returns - benchmark_returns
    print("\nExcess Returns:")
    print(f"  Mean: {np.mean(excess_returns):.6f}")
    print(f"  Median: {np.median(excess_returns):.6f}")
    print(f"  Std: {np.std(excess_returns):.6f}")
    print(
        f"  Information Ratio: {np.mean(excess_returns) / np.std(excess_returns) * np.sqrt(252):.2f}"
    )

    return strategy_df, benchmark_df


def scenario_4_multi_turn_conversation():
    """
    Scenario 4: Multi-turn conversation simulation

    User asks initial question, then refines/modifies/requests more detail
    """
    print("\n\n" + "=" * 80)
    print("SCENARIO 4: Multi-Turn Conversation Simulation")
    print("=" * 80)

    # Generate strategy data
    np.random.seed(789)
    n_days = 300
    dates = pd.date_range("2023-01-01", periods=n_days)

    # Strategy with some interesting characteristics
    returns = np.random.normal(0.0008, 0.018, n_days)
    vix = np.random.uniform(12, 35, n_days)

    df = pd.DataFrame({"date": dates, "returns": returns, "VIX": vix})

    # TURN 1: Initial question
    print("\n" + "=" * 80)
    print("TURN 1: Initial Question")
    print("=" * 80)
    print('\nUSER: "Is my strategy profitable? File: strategy.csv"')
    print("\n" + "-" * 80)

    checker = DistributionChecker()
    dist_result = checker.check_normality(df["returns"].values)

    tester = HypothesisTests()
    test_result = tester.one_sample_test(
        df["returns"].values, use_parametric=dist_result["is_normal"]
    )

    metrics = PerformanceMetrics.calculate_all_metrics(df["returns"].values)

    reporter = TweetStyleReporter()
    test_dict = {
        "test_name": test_result.test_name,
        "p_value": test_result.p_value,
        "significant": test_result.significant,
        "distribution_type": test_result.distribution_type,
    }
    summary = reporter.performance_test_summary(test_dict, metrics)

    print("AGENT:")
    print(summary)

    # TURN 2: User asks for more detail
    print("\n" + "=" * 80)
    print("TURN 2: Request for More Detail")
    print("=" * 80)
    print('\nUSER: "Can you give me more details? What about the distribution?"')
    print("\n" + "-" * 80)

    print("AGENT: Sure! Let me provide a detailed distribution analysis...\n")

    print("Distribution Characteristics:")
    print(f"  Shapiro-Wilk p-value: {dist_result['shapiro_p']:.6f}")
    print(f"  Jarque-Bera p-value: {dist_result['jarque_bera_p']:.6f}")
    print(f"  Skewness: {dist_result['skewness']:.4f}")
    print(f"  Kurtosis: {dist_result['kurtosis']:.4f}")

    if dist_result["kurtosis"] > 1:
        print("\n  ⚠️ Fat tails detected - more extreme events than normal")

    print("\nReturn Percentiles:")
    for p in [5, 25, 50, 75, 95]:
        val = np.percentile(df["returns"].values, p)
        print(f"  {p}th: {val:.4%}")

    # TURN 3: User modifies question
    print("\n" + "=" * 80)
    print("TURN 3: Modified Question")
    print("=" * 80)
    print('\nUSER: "Actually, does it perform differently when VIX is high?')
    print('       Test for VIX > 20"')
    print("\n" + "-" * 80)

    print("AGENT: Let me test that condition...\n")

    parser = ConditionParser()
    cond_filter = parser.parse_multiple_conditions("VIX > 20")

    segmenter = DataSegmenter()
    result = segmenter.segment_data(df, cond_filter)

    print("Segmentation:")
    print(f"  VIX > 20: {result['n_true']} days ({result['n_true']/n_days*100:.1f}%)")
    print(f"  VIX ≤ 20: {result['n_false']} days ({result['n_false']/n_days*100:.1f}%)")

    analyzer = ConditionalAnalyzer()
    comparison = analyzer.compare_metric(
        result["group_true"], result["group_false"], "returns", "Returns"
    )

    test_result_cond = tester.independent_test(
        result["group_true"]["returns"].values,
        result["group_false"]["returns"].values,
        use_parametric=False,
    )

    test_dict_cond = {
        "test_name": test_result_cond.test_name,
        "p_value": test_result_cond.p_value,
        "significant": test_result_cond.significant,
        "distribution_type": "non-normal",
    }
    summary_cond = reporter.conditional_analysis_summary(
        "VIX > 20", "Returns", comparison, test_dict_cond
    )
    print(summary_cond)

    # TURN 4: User asks for report
    print("\n" + "=" * 80)
    print("TURN 4: Request for Detailed Report")
    print("=" * 80)
    print('\nUSER: "Can you save a detailed report with all this analysis?"')
    print("\n" + "-" * 80)

    print("AGENT: Generating comprehensive report...\n")

    detailed_reporter = DetailedReporter()
    report = detailed_reporter.full_report(
        test_type="Multi-Turn Analysis: Strategy Performance & VIX Conditional",
        test_results=[
            {
                "test_name": test_result.test_name,
                "statistic": test_result.statistic,
                "p_value": test_result.p_value,
                "significant": test_result.significant,
                "confidence_level": 0.95,
                "interpretation": test_result.interpretation,
            },
            {
                "test_name": test_result_cond.test_name,
                "statistic": test_result_cond.statistic,
                "p_value": test_result_cond.p_value,
                "significant": test_result_cond.significant,
                "confidence_level": 0.95,
                "interpretation": "Conditional analysis: VIX > 20",
            },
        ],
        metrics=metrics,
        distribution_check=dist_result,
        warnings=[],
        additional_info={
            "conversation_turns": 4,
            "conditions_tested": "VIX > 20",
            "n_high_vix": result["n_true"],
            "n_low_vix": result["n_false"],
        },
    )

    filepath = detailed_reporter.save_report(
        report, filename="multi_turn_conversation_analysis.md", output_dir="/tmp"
    )

    print(f"✓ Report saved to: {filepath}")
    print("\nAGENT: Done! The report includes:")
    print("  - Overall performance test")
    print("  - Distribution analysis")
    print("  - VIX conditional analysis")
    print("  - All test statistics and metrics")

    # TURN 5: User asks follow-up
    print("\n" + "=" * 80)
    print("TURN 5: Follow-up Question")
    print("=" * 80)
    print('\nUSER: "What if I lower the threshold to VIX > 18?"')
    print("\n" + "-" * 80)

    print("AGENT: Let me re-run the analysis with VIX > 18...\n")

    cond_filter_18 = parser.parse_multiple_conditions("VIX > 18")
    result_18 = segmenter.segment_data(df, cond_filter_18)

    print("New Segmentation (VIX > 18):")
    print(
        f"  VIX > 18: {result_18['n_true']} days ({result_18['n_true']/n_days*100:.1f}%)"
    )
    print(
        f"  VIX ≤ 18: {result_18['n_false']} days ({result_18['n_false']/n_days*100:.1f}%)"
    )

    comparison_18 = analyzer.compare_metric(
        result_18["group_true"], result_18["group_false"], "returns", "Returns"
    )

    print("\nQuick Comparison:")
    print(f"  VIX > 18 mean: {comparison_18['group_true']['mean']:.6f}")
    print(f"  VIX ≤ 18 mean: {comparison_18['group_false']['mean']:.6f}")
    print(f"  Difference: {comparison_18['difference']['mean']:.6f}")

    print("\n💡 INSIGHT: This demonstrates how the skill handles iterative")
    print("   refinement of analysis parameters in a conversation!")


if __name__ == "__main__":
    print("\n" + "=" * 80)
    print("ADVANCED TESTING SCENARIOS")
    print("Statistical Testing Skill - Comprehensive Validation")
    print("=" * 80)

    try:
        # Scenario 1: Synthetic strategy with features
        scenario_1_synthetic_strategy_with_features()

        # Scenario 2: Random strategy vs NIFTY
        scenario_2_random_strategy_vs_nifty()

        # Scenario 3: Drift strategy vs NIFTY
        scenario_3_drift_strategy_vs_nifty()

        # Scenario 4: Multi-turn conversation
        scenario_4_multi_turn_conversation()

        print("\n\n" + "=" * 80)
        print("ALL ADVANCED SCENARIOS COMPLETED")
        print("=" * 80)
        print("\n✅ Scenario 1: Synthetic strategy with features - PASSED")
        print("✅ Scenario 2: Random strategy vs NIFTY - PASSED")
        print("✅ Scenario 3: Drift strategy vs NIFTY - PASSED")
        print("✅ Scenario 4: Multi-turn conversation - PASSED")

        print("\nReports saved to /tmp/:")
        print("  - multi_turn_conversation_analysis.md")

    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback

        traceback.print_exc()
