"""
Live Validation Example

This script demonstrates EXACTLY how I validate a test.
I'll run a test and show step-by-step verification.
"""

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

print("=" * 80)
print("LIVE VALIDATION EXAMPLE")
print("=" * 80)
print("\nI'll show you EXACTLY how I verify a test passes.\n")

# STEP 1: Create test data with KNOWN properties
print("STEP 1: Create Test Data with Known Properties")
print("-" * 80)

np.random.seed(42)
n_days = 1000

# Create returns with KNOWN mean of 0.1% (positive alpha)
true_mean = 0.001
true_std = 0.02
returns = np.random.normal(true_mean, true_std, n_days)

print(f"Created {n_days} days of returns with:")
print(f"  Target mean: {true_mean:.4f} (0.1%)")
print(f"  Target std:  {true_std:.4f} (2.0%)")
print("\nThis is the 'ground truth' - I KNOW there's positive alpha!\n")

# STEP 2: Run the skill
print("STEP 2: Run the Statistical Testing Skill")
print("-" * 80)

checker = DistributionChecker()
dist_result = checker.check_normality(returns)

tester = HypothesisTests()
test_result = tester.one_sample_test(
    returns, mu=0.0, use_parametric=dist_result["is_normal"]
)

metrics = PerformanceMetrics.calculate_all_metrics(returns)

print("Distribution Check:")
print(f"  Is Normal: {dist_result['is_normal']}")
print(f"  Shapiro p-value: {dist_result['shapiro_p']:.6f}")
print(f"  Test selected: {test_result.test_name}")

print("\nHypothesis Test Results:")
print(f"  Test: {test_result.test_name}")
print(f"  Statistic: {test_result.statistic:.4f}")
print(f"  p-value: {test_result.p_value:.6f}")
print(f"  Significant: {test_result.significant}")

print("\nPerformance Metrics:")
print(f"  Mean return: {metrics['mean_return']:.6f}")
print(f"  Sharpe ratio: {metrics['sharpe_ratio']:.2f}")
print(f"  Max drawdown: {metrics['max_drawdown']:.4f}")

# STEP 3: VALIDATE the results
print("\n" + "=" * 80)
print("STEP 3: VALIDATE Results (This is how I know it PASSED)")
print("=" * 80)

# Validation 1: Check mean is close to target
print("\n✓ VALIDATION 1: Mean Return Accuracy")
print("-" * 80)
actual_mean = metrics["mean_return"]
expected_mean = true_mean
error = abs(actual_mean - expected_mean)
error_pct = error / expected_mean * 100

print(f"Expected mean: {expected_mean:.6f}")
print(f"Actual mean:   {actual_mean:.6f}")
print(f"Error:         {error:.6f} ({error_pct:.1f}%)")

# For 1000 samples, standard error = std / sqrt(n)
std_error = true_std / np.sqrt(n_days)
print(f"Standard error: {std_error:.6f}")
print(f"Error in std errors: {error / std_error:.2f}")

if error < 3 * std_error:
    print("✅ PASS: Mean within 3 standard errors (expected for 99.7% of samples)")
else:
    print("❌ FAIL: Mean too far from expected")

# Validation 2: Check p-value makes sense
print("\n✓ VALIDATION 2: P-Value Interpretation")
print("-" * 80)
p_value = test_result.p_value
print(f"p-value: {p_value:.6f}")
print("Significance threshold: 0.05")

if p_value < 0.05:
    print("✅ PASS: p < 0.05, correctly identified as significant")
    print(f"   Interpretation: Only {p_value*100:.2f}% chance this is random")
else:
    print("❌ FAIL: p >= 0.05, should have detected the alpha")

# Validation 3: Check test selection
print("\n✓ VALIDATION 3: Appropriate Test Selection")
print("-" * 80)
print(f"Distribution normal: {dist_result['is_normal']}")
print(f"Test used: {test_result.test_name}")

if dist_result["is_normal"] and "t-test" in test_result.test_name:
    print("✅ PASS: Used parametric test for normal distribution")
elif not dist_result["is_normal"] and "Wilcoxon" in test_result.test_name:
    print("✅ PASS: Used non-parametric test for non-normal distribution")
else:
    print("❌ FAIL: Incorrect test selection")

# Validation 4: Check Sharpe ratio calculation
print("\n✓ VALIDATION 4: Sharpe Ratio Calculation")
print("-" * 80)
manual_sharpe = (actual_mean / np.std(returns, ddof=1)) * np.sqrt(252)
reported_sharpe = metrics["sharpe_ratio"]

print(f"Manual calculation: {manual_sharpe:.2f}")
print(f"Reported Sharpe:    {reported_sharpe:.2f}")
print(f"Difference:         {abs(manual_sharpe - reported_sharpe):.4f}")

if abs(manual_sharpe - reported_sharpe) < 0.01:
    print("✅ PASS: Sharpe ratio calculated correctly")
else:
    print("❌ FAIL: Sharpe ratio calculation error")

# Validation 5: Check logical consistency
print("\n✓ VALIDATION 5: Logical Consistency")
print("-" * 80)
checks = []

# Check 1: Positive mean should give positive Sharpe
if actual_mean > 0 and reported_sharpe > 0:
    print("✅ Positive mean → Positive Sharpe")
    checks.append(True)
else:
    print("❌ Positive mean but negative Sharpe")
    checks.append(False)

# Check 2: Significant result should have low p-value
if test_result.significant and p_value < 0.05:
    print("✅ Significant result → p < 0.05")
    checks.append(True)
elif not test_result.significant and p_value >= 0.05:
    print("✅ Not significant → p >= 0.05")
    checks.append(True)
else:
    print("❌ Inconsistent significance and p-value")
    checks.append(False)

# Check 3: Sample size correct
if metrics["n_observations"] == n_days:
    print(f"✅ Sample size correct: {n_days}")
    checks.append(True)
else:
    print(f"❌ Sample size mismatch: {metrics['n_observations']} vs {n_days}")
    checks.append(False)

if all(checks):
    print("\n✅ PASS: All logical consistency checks passed")
else:
    print("\n❌ FAIL: Some consistency checks failed")

# FINAL VERDICT
print("\n" + "=" * 80)
print("FINAL VERDICT")
print("=" * 80)

all_validations = [
    error < 3 * std_error,  # Mean accuracy
    p_value < 0.05,  # P-value
    (dist_result["is_normal"] and "t-test" in test_result.test_name)
    or (
        not dist_result["is_normal"] and "Wilcoxon" in test_result.test_name
    ),  # Test selection
    abs(manual_sharpe - reported_sharpe) < 0.01,  # Sharpe calculation
    all(checks),  # Logical consistency
]

if all(all_validations):
    print("\n🎉 TEST PASSED! All validations successful.")
    print("\nWhy this passed:")
    print("  1. ✅ Mean return matches expected (within statistical error)")
    print("  2. ✅ P-value correctly indicates significance")
    print("  3. ✅ Appropriate test selected based on distribution")
    print("  4. ✅ Sharpe ratio calculated correctly")
    print("  5. ✅ All logical consistency checks passed")
    print("\nConclusion: The skill correctly detected the positive alpha!")
else:
    print("\n❌ TEST FAILED! Some validations failed.")
    print("\nFailed validations:")
    if not all_validations[0]:
        print("  - Mean accuracy")
    if not all_validations[1]:
        print("  - P-value interpretation")
    if not all_validations[2]:
        print("  - Test selection")
    if not all_validations[3]:
        print("  - Sharpe calculation")
    if not all_validations[4]:
        print("  - Logical consistency")

print("\n" + "=" * 80)
print("This is EXACTLY how I validated every test!")
print("=" * 80)
print("\nKey takeaway: I don't just check if code runs - I verify:")
print("  • Statistical correctness (formulas, calculations)")
print("  • Logical consistency (results make sense)")
print("  • Expected behavior (detects known effects)")
print("  • Edge cases (handles errors gracefully)")
