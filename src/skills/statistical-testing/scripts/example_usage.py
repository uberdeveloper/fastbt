"""
Example: Complete Statistical Testing Workflow

This script demonstrates how to use the statistical testing skill components
to analyze strategy returns.
"""

import numpy as np
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
    MultipleTestingCorrection,
)
from conditional_filter import (
    ConditionParser,
    DataSegmenter,
    ConditionalAnalyzer,
)  # noqa: E402
from reporter import TweetStyleReporter, DetailedReporter  # noqa: E402


def example_1_simple_alpha_test():
    """Example 1: Test if strategy has positive alpha"""
    print("=" * 60)
    print("EXAMPLE 1: Simple Alpha Test")
    print("=" * 60)

    # Generate sample strategy returns
    np.random.seed(42)
    n_days = 1000
    strategy_returns = np.random.normal(0.0012, 0.02, n_days)  # Positive mean

    # Step 1: Check distribution
    checker = DistributionChecker()
    dist_result = checker.check_normality(strategy_returns)
    print("\n1. Distribution Check:")
    print(f"   Is Normal: {dist_result['is_normal']}")
    print(f"   Recommendation: {dist_result['recommendation']}")

    # Step 2: Run hypothesis test
    tester = HypothesisTests()
    test_result = tester.one_sample_test(
        strategy_returns, mu=0.0, use_parametric=dist_result["is_normal"]
    )
    print("\n2. Hypothesis Test:")
    print(f"   Test: {test_result.test_name}")
    print(f"   p-value: {test_result.p_value:.4f}")
    print(f"   Significant: {test_result.significant}")

    # Step 3: Calculate performance metrics
    metrics = PerformanceMetrics.calculate_all_metrics(strategy_returns)
    print("\n3. Performance Metrics:")
    print(f"   Sharpe Ratio: {metrics['sharpe_ratio']:.2f}")
    print(f"   Max Drawdown: {metrics['max_drawdown']:.2%}")
    print(f"   Win Rate: {metrics['win_rate']:.2%}")

    # Step 4: Generate tweet-style summary
    reporter = TweetStyleReporter()
    test_dict = {
        "test_name": test_result.test_name,
        "p_value": test_result.p_value,
        "significant": test_result.significant,
        "distribution_type": test_result.distribution_type,
    }
    summary = reporter.performance_test_summary(test_dict, metrics)
    print("\n4. Tweet-Style Summary:")
    print(summary)

    print("\n" + "=" * 60 + "\n")


def example_2_benchmark_comparison():
    """Example 2: Compare strategy to benchmark"""
    print("=" * 60)
    print("EXAMPLE 2: Benchmark Comparison")
    print("=" * 60)

    # Generate sample data
    np.random.seed(42)
    n_days = 500
    # dates = pd.date_range("2023-01-01", periods=n_days)

    strategy_returns = np.random.normal(0.0015, 0.02, n_days)
    benchmark_returns = np.random.normal(0.0008, 0.015, n_days)

    # Step 1: Check distribution
    checker = DistributionChecker()
    dist_result = checker.check_normality(strategy_returns)
    print("\n1. Distribution Check:")
    print(f"   Recommendation: {dist_result['recommendation']}")

    # Step 2: Run paired test
    tester = HypothesisTests()
    test_result = tester.paired_test(
        strategy_returns, benchmark_returns, use_parametric=dist_result["is_normal"]
    )
    print("\n2. Paired Test:")
    print(f"   Test: {test_result.test_name}")
    print(f"   p-value: {test_result.p_value:.4f}")
    print(f"   Significant: {test_result.significant}")
    print(f"   Mean Difference: {test_result.additional_metrics['mean_diff']:.6f}")

    # Step 3: Calculate metrics for both
    strategy_metrics = PerformanceMetrics.calculate_all_metrics(strategy_returns)
    benchmark_metrics = PerformanceMetrics.calculate_all_metrics(benchmark_returns)

    print("\n3. Performance Comparison:")
    print(f"   Strategy Sharpe: {strategy_metrics['sharpe_ratio']:.2f}")
    print(f"   Benchmark Sharpe: {benchmark_metrics['sharpe_ratio']:.2f}")
    print(
        f"   Excess Sharpe: {strategy_metrics['sharpe_ratio'] - benchmark_metrics['sharpe_ratio']:.2f}"
    )

    # Step 4: Generate summary
    reporter = TweetStyleReporter()
    test_dict = {
        "test_name": test_result.test_name,
        "p_value": test_result.p_value,
        "significant": test_result.significant,
        "distribution_type": test_result.distribution_type,
    }
    summary = reporter.outperformance_test_summary(
        test_dict, strategy_metrics, benchmark_metrics, benchmark_name="SPY"
    )
    print("\n4. Tweet-Style Summary:")
    print(summary)

    print("\n" + "=" * 60 + "\n")


def example_3_conditional_analysis():
    """Example 3: Conditional analysis (segment comparison)"""
    print("=" * 60)
    print("EXAMPLE 3: Conditional Analysis")
    print("=" * 60)

    # Generate sample data with features
    np.random.seed(42)
    n_days = 1000

    df = pd.DataFrame(
        {
            "date": pd.date_range("2020-01-01", periods=n_days),
            "returns": np.random.normal(0.001, 0.02, n_days),
            "VIX": np.random.uniform(10, 50, n_days),
            "market_cap": np.random.uniform(500, 2000, n_days),
        }
    )

    # Step 1: Parse condition
    parser = ConditionParser()
    cond_filter = parser.parse_multiple_conditions("VIX > 20 AND market_cap > 1000")
    print("\n1. Parsed Conditions:")
    print(f"   Number of conditions: {len(cond_filter.conditions)}")
    print(f"   Logic: {cond_filter.logic}")
    for i, cond in enumerate(cond_filter.conditions, 1):
        print(f"   Condition {i}: {cond.column} {cond.operator} {cond.value}")

    # Step 2: Segment data
    segmenter = DataSegmenter()
    result = segmenter.segment_data(df, cond_filter)
    print("\n2. Data Segmentation:")
    print(f"   Group TRUE: {result['n_true']} observations")
    print(f"   Group FALSE: {result['n_false']} observations")
    print(f"   Query: {result['query']}")
    if result["warnings"]:
        for warning in result["warnings"]:
            print(f"   ⚠️ {warning}")

    # Step 3: Compare metric between groups
    analyzer = ConditionalAnalyzer()
    comparison = analyzer.compare_metric(
        result["group_true"], result["group_false"], "returns", "Returns"
    )
    print("\n3. Metric Comparison:")
    print(f"   Group TRUE mean: {comparison['group_true']['mean']:.6f}")
    print(f"   Group FALSE mean: {comparison['group_false']['mean']:.6f}")
    print(f"   Difference: {comparison['difference']['mean']:.6f}")

    # Step 4: Statistical test
    tester = HypothesisTests()
    test_result = tester.independent_test(
        result["group_true"]["returns"].values,
        result["group_false"]["returns"].values,
        use_parametric=False,  # Use non-parametric for safety
    )
    print("\n4. Statistical Test:")
    print(f"   Test: {test_result.test_name}")
    print(f"   p-value: {test_result.p_value:.4f}")
    print(f"   Significant: {test_result.significant}")

    # Step 5: Generate summary
    reporter = TweetStyleReporter()
    test_dict = {
        "test_name": test_result.test_name,
        "p_value": test_result.p_value,
        "significant": test_result.significant,
        "distribution_type": "non-normal",
    }
    summary = reporter.conditional_analysis_summary(
        "VIX > 20 AND market_cap > 1000", "Returns", comparison, test_dict
    )
    print("\n5. Tweet-Style Summary:")
    print(summary)

    print("\n" + "=" * 60 + "\n")


def example_4_multiple_testing_correction():
    """Example 4: Multiple testing correction"""
    print("=" * 60)
    print("EXAMPLE 4: Multiple Testing Correction")
    print("=" * 60)

    # Simulate running 5 tests
    np.random.seed(42)
    p_values = [0.03, 0.01, 0.15, 0.04, 0.002]

    print(f"\n1. Original p-values: {p_values}")

    # Apply Bonferroni correction
    correction = MultipleTestingCorrection.bonferroni(p_values, alpha=0.05)

    print("\n2. Bonferroni Correction:")
    print(f"   Number of tests: {correction['n_tests']}")
    print(f"   Original α: {correction['original_alpha']}")
    print(f"   Adjusted α: {correction['adjusted_alpha']:.4f}")

    print("\n3. Results:")
    for i, (p, sig) in enumerate(zip(p_values, correction["significant"]), 1):
        status = "✓ Significant" if sig else "✗ Not significant"
        print(f"   Test {i}: p={p:.3f} → {status}")

    print(f"\n⚠️ Applied Bonferroni correction for {correction['n_tests']} tests")
    print(f"   (adjusted α={correction['adjusted_alpha']:.3f})")

    print("\n" + "=" * 60 + "\n")


def example_5_full_report():
    """Example 5: Generate detailed markdown report"""
    print("=" * 60)
    print("EXAMPLE 5: Full Markdown Report")
    print("=" * 60)

    # Generate sample data
    np.random.seed(42)
    returns = np.random.normal(0.001, 0.02, 1000)

    # Run analysis
    checker = DistributionChecker()
    dist_result = checker.check_normality(returns)

    tester = HypothesisTests()
    test_result = tester.one_sample_test(
        returns, use_parametric=dist_result["is_normal"]
    )

    metrics = PerformanceMetrics.calculate_all_metrics(returns)

    # Generate detailed report
    reporter = DetailedReporter()
    test_dict = {
        "test_name": test_result.test_name,
        "statistic": test_result.statistic,
        "p_value": test_result.p_value,
        "significant": test_result.significant,
        "confidence_level": test_result.confidence_level,
        "interpretation": test_result.interpretation,
    }

    report = reporter.full_report(
        test_type="Performance Test",
        test_results=[test_dict],
        metrics=metrics,
        distribution_check=dist_result,
        warnings=["Returns not normally distributed"],
        additional_info={
            "data_source": "Simulated momentum strategy",
            "period": "2020-01-01 to 2025-12-31",
        },
    )

    print("\n" + report)

    # Save report
    filepath = reporter.save_report(report, output_dir="/tmp")
    print(f"\n✓ Report saved to: {filepath}")

    print("\n" + "=" * 60 + "\n")


if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("STATISTICAL TESTING SKILL - EXAMPLES")
    print("=" * 60 + "\n")

    # Run all examples
    example_1_simple_alpha_test()
    example_2_benchmark_comparison()
    example_3_conditional_analysis()
    example_4_multiple_testing_correction()
    example_5_full_report()

    print("=" * 60)
    print("ALL EXAMPLES COMPLETED")
    print("=" * 60)
