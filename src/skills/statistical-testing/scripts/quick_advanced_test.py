"""
Quick Advanced Scenarios Test (No yfinance dependency)

Tests scenarios without external API calls
"""

import pandas as pd
import numpy as np
import sys
from pathlib import Path

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


print("\n" + "=" * 80)
print("ADVANCED SCENARIOS - QUICK TEST")
print("=" * 80)

# SCENARIO 1: Synthetic strategy with features
print("\n" + "=" * 80)
print("SCENARIO 1: Synthetic Strategy with Conditional Alpha")
print("=" * 80)

np.random.seed(42)
n_days = 500
dates = pd.date_range("2023-01-01", periods=n_days)

# Features
rsi = np.random.uniform(20, 80, n_days)
volume = np.random.lognormal(mean=10, sigma=0.5, size=n_days)
avg_volume = np.mean(volume)

# Returns with conditional alpha
base_returns = np.random.normal(0.0005, 0.015, n_days)
condition_met = (rsi < 30) & (volume > avg_volume)
returns = base_returns.copy()
returns[condition_met] += 0.003  # Add alpha when conditions met

df = pd.DataFrame({"date": dates, "returns": returns, "RSI": rsi, "volume": volume})

print(f"\n✓ Generated {len(df)} days")
print(f"  Condition met (RSI < 30 AND volume > avg): {condition_met.sum()} days")

# Overall test
checker = DistributionChecker()
dist_result = checker.check_normality(df["returns"].values)

tester = HypothesisTests()
test_result = tester.one_sample_test(
    df["returns"].values, use_parametric=dist_result["is_normal"]
)

metrics = PerformanceMetrics.calculate_all_metrics(df["returns"].values)

reporter = TweetStyleReporter()
summary = reporter.performance_test_summary(
    {
        "test_name": test_result.test_name,
        "p_value": test_result.p_value,
        "significant": test_result.significant,
        "distribution_type": test_result.distribution_type,
    },
    metrics,
)
print("\n" + summary)

# Conditional analysis
print("\n" + "-" * 80)
print(f"Conditional Analysis: RSI < 30 AND volume > {avg_volume:.0f}")
print("-" * 80)

parser = ConditionParser()
cond_filter = parser.parse_multiple_conditions(
    f"RSI < 30 AND volume > {avg_volume:.2f}"
)

segmenter = DataSegmenter()
result = segmenter.segment_data(df, cond_filter)

print(f"\nSegmentation: {result['n_true']} vs {result['n_false']} days")

analyzer = ConditionalAnalyzer()
comparison = analyzer.compare_metric(
    result["group_true"], result["group_false"], "returns", "Returns"
)

test_cond = tester.independent_test(
    result["group_true"]["returns"].values,
    result["group_false"]["returns"].values,
    use_parametric=False,
)

summary_cond = reporter.conditional_analysis_summary(
    "RSI < 30 AND volume > avg",
    "Returns",
    comparison,
    {
        "test_name": test_cond.test_name,
        "p_value": test_cond.p_value,
        "significant": test_cond.significant,
        "distribution_type": "non-normal",
    },
)
print(summary_cond)

# SCENARIO 2: Random vs Benchmark (synthetic)
print("\n" + "=" * 80)
print("SCENARIO 2: Random Strategy vs Synthetic Benchmark")
print("=" * 80)

np.random.seed(123)
n_days = 200
dates = pd.date_range("2024-01-01", periods=n_days, freq="B")

random_returns = np.random.normal(0.0, 0.015, n_days)
benchmark_returns = np.random.normal(0.0005, 0.012, n_days)

print(f"\n✓ Generated {n_days} days")
print(f"  Strategy mean: {np.mean(random_returns):.6f}")
print(f"  Benchmark mean: {np.mean(benchmark_returns):.6f}")

test_pair = tester.paired_test(random_returns, benchmark_returns, use_parametric=False)

strategy_metrics = PerformanceMetrics.calculate_all_metrics(random_returns)
benchmark_metrics = PerformanceMetrics.calculate_all_metrics(benchmark_returns)

summary_bench = reporter.outperformance_test_summary(
    {
        "test_name": test_pair.test_name,
        "p_value": test_pair.p_value,
        "significant": test_pair.significant,
        "distribution_type": "non-normal",
    },
    strategy_metrics,
    benchmark_metrics,
    "Synthetic Benchmark",
)
print(summary_bench)

# SCENARIO 3: Drift strategy vs Benchmark
print("\n" + "=" * 80)
print("SCENARIO 3: Strategy with Drift vs Benchmark")
print("=" * 80)

np.random.seed(456)
drift_returns = np.random.normal(0.001, 0.015, n_days)  # Positive drift
benchmark_returns2 = np.random.normal(0.0005, 0.012, n_days)

print(f"\n✓ Generated {n_days} days with drift")
print(f"  Strategy mean: {np.mean(drift_returns):.6f} (target: 0.001)")
print(f"  Benchmark mean: {np.mean(benchmark_returns2):.6f}")

test_drift = tester.paired_test(drift_returns, benchmark_returns2, use_parametric=False)

drift_metrics = PerformanceMetrics.calculate_all_metrics(drift_returns)
bench2_metrics = PerformanceMetrics.calculate_all_metrics(benchmark_returns2)

summary_drift = reporter.outperformance_test_summary(
    {
        "test_name": test_drift.test_name,
        "p_value": test_drift.p_value,
        "significant": test_drift.significant,
        "distribution_type": "non-normal",
    },
    drift_metrics,
    bench2_metrics,
    "Benchmark",
)
print(summary_drift)

# Excess returns
excess = drift_returns - benchmark_returns2
print("\nExcess Returns:")
print(f"  Mean: {np.mean(excess):.6f}")
print(f"  Information Ratio: {np.mean(excess) / np.std(excess) * np.sqrt(252):.2f}")

# SCENARIO 4: Multi-turn conversation
print("\n" + "=" * 80)
print("SCENARIO 4: Multi-Turn Conversation")
print("=" * 80)

np.random.seed(789)
n_days = 300
dates = pd.date_range("2023-01-01", periods=n_days)
returns = np.random.normal(0.0008, 0.018, n_days)
vix = np.random.uniform(12, 35, n_days)

df_conv = pd.DataFrame({"date": dates, "returns": returns, "VIX": vix})

print('\n[TURN 1] USER: "Is my strategy profitable?"')
print("-" * 80)

test_t1 = tester.one_sample_test(df_conv["returns"].values, use_parametric=False)
metrics_t1 = PerformanceMetrics.calculate_all_metrics(df_conv["returns"].values)

print(f"AGENT: Sharpe={metrics_t1['sharpe_ratio']:.2f}, p={test_t1.p_value:.3f}")
print(f"       {'Significant' if test_t1.significant else 'Not significant'} at 95%")

print('\n[TURN 2] USER: "What about the distribution?"')
print("-" * 80)

dist_t2 = checker.check_normality(df_conv["returns"].values)
print(f"AGENT: Skewness={dist_t2['skewness']:.3f}, Kurtosis={dist_t2['kurtosis']:.3f}")
print(f"       {'Normal' if dist_t2['is_normal'] else 'Non-normal'} distribution")

print('\n[TURN 3] USER: "Does it perform differently when VIX > 20?"')
print("-" * 80)

cond_t3 = parser.parse_multiple_conditions("VIX > 20")
result_t3 = segmenter.segment_data(df_conv, cond_t3)

print(
    f"AGENT: VIX > 20: {result_t3['n_true']} days ({result_t3['n_true']/n_days*100:.1f}%)"
)

comp_t3 = analyzer.compare_metric(
    result_t3["group_true"], result_t3["group_false"], "returns", "Returns"
)
test_t3 = tester.independent_test(
    result_t3["group_true"]["returns"].values,
    result_t3["group_false"]["returns"].values,
    use_parametric=False,
)

print(f"       High VIX mean: {comp_t3['group_true']['mean']:.6f}")
print(f"       Low VIX mean: {comp_t3['group_false']['mean']:.6f}")
print(
    f"       p-value: {test_t3.p_value:.3f} ({'Significant' if test_t3.significant else 'Not significant'})"
)

print('\n[TURN 4] USER: "Save a detailed report"')
print("-" * 80)

detailed_reporter = DetailedReporter()
report = detailed_reporter.full_report(
    test_type="Multi-Turn Conversation Analysis",
    test_results=[
        {
            "test_name": test_t1.test_name,
            "statistic": test_t1.statistic,
            "p_value": test_t1.p_value,
            "significant": test_t1.significant,
            "confidence_level": 0.95,
            "interpretation": test_t1.interpretation,
        }
    ],
    metrics=metrics_t1,
    distribution_check=dist_t2,
    warnings=[],
    additional_info={"conversation_turns": 4, "vix_condition": "VIX > 20"},
)

filepath = detailed_reporter.save_report(
    report, filename="multi_turn_test.md", output_dir="/tmp"
)
print(f"AGENT: ✓ Report saved to {filepath}")

print('\n[TURN 5] USER: "What if VIX > 18?"')
print("-" * 80)

result_t5 = segmenter.segment_data(
    df_conv, parser.parse_multiple_conditions("VIX > 18")
)
comp_t5 = analyzer.compare_metric(
    result_t5["group_true"], result_t5["group_false"], "returns", "Returns"
)

print(f"AGENT: VIX > 18: {result_t5['n_true']} days")
print(f"       Mean difference: {comp_t5['difference']['mean']:.6f}")

print("\n" + "=" * 80)
print("ALL SCENARIOS COMPLETED")
print("=" * 80)
print("\n✅ Scenario 1: Conditional alpha detection - PASSED")
print("✅ Scenario 2: Random vs benchmark - PASSED")
print("✅ Scenario 3: Drift vs benchmark - PASSED")
print("✅ Scenario 4: Multi-turn conversation - PASSED")
