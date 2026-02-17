# Statistical Skill Stress Test Report

## Executive Summary
The `statistical-testing` skill provides a solid foundation for standard hypothesis testing on clean, well-structured data. It correctly navigates the decision tree between parametric and non-parametric tests based on distribution characteristics. However, under "stress test" conditions involving dirty data, ambiguous prompts, or edge-case logic, the skill exhibits significant fragility. It lacks robust error handling for missing values (NaNs), precise mechanisms for ambiguous query resolution, and flexibility in column inference.

## 1. Stress Test Scenarios & Results

| Scenario | Prompt | Data Characteristics | Result | Verdict |
|----------|--------|----------------------|--------|---------|
| **1. Standard Baseline** | "Do I have positive returns?" | Normal distribution, Clean | ✅ Passed. Correctly selected One-sample t-test. | **Pass** |
| **2. Non-Parametric** | "Do I have positive returns?" | Fat-tailed (t-dist), Clean | ✅ Passed. Correctly selected Wilcoxon signed-rank. | **Pass** |
| **3. Benchmark Missing** | "Does my strategy beat the benchmark?" | Benchmark column present but not identified | ❌ **Failed/Halted**. Skill logic halts if explicit "benchmark" column isn't found or mapped. No fuzzy matching logic observed. | **Fail** |
| **4. Small Sample** | "Does strategy perform worse when VIX > 25?" | High VIX group has N=18 | ⚠️ **Warning/Halt**. Logic dictates `HALT` if N<30. This prevents analysis of tail events which are inherently rare. | **Restrictive** |
| **5. Ambiguity** | "Is it good?" | Clean data | ❌ **Halted**. Correctly halts per ambiguity rule, but lacks a "did you mean..." suggestion mechanism. | **Pass/Improve** |
| **6. Text Condition** | "Better when regime == 'bull'?" | Text column 'regime' | ✅ Passed. Logic supports `==` operator for text strings. | **Pass** |
| **7. Dirty Data** | "Do I have positive returns?" | 10% Missing Data (NaNs) | ☠️ **Critical Failure**. `scipy.stats` functions return `nan` or crash. Skill has no explicit `dropna()` or cleaning step. | **Critical Fail** |
| **8. Complex Logic** | "VIX > 20 OR (VIX < 15 AND RSI > 70)" | Standard | ❌ **Unsupported**. Skill explicitly checks for mixed logic and halts. | **Limitation** |

## 2. Identified Shortcomings

### 🔴 Critical: Missing Data Handling
The skill assumes input data is pristine.
- **Issue:** Passing `NaN` values to `shapiro` or `ttest` results in `nan` statistics or crashes.
- **Impact:** Real-world data often has gaps. The skill will fail silently (returning garbage p-values like 1.0 or nan) or crash.
- **Fix:** Must verify/documents that `load-data` cleans NaNs, or explicitly add `dropna()` in the skill's data preparation step.

### 🟠 Major: Rigid Column Inference
The skill relies heavily on `load-data` to populate a manifest.
- **Issue:** If `load-data` misses a column (e.g., "strategy_pnl" instead of "returns"), the statistical skill halts immediately.
- **Impact:** Poor user experience.
- **Fix:** Implement fuzzy matching (e.g., columns containing 'ret', 'pnl', 'change') and an interactive confirmation step ("I found 'strategy_pnl', use this as returns?").

### 🟡 Minor: Sample Size Restrictions
- **Issue:** The `HALT if N < 30` rule is statistically safe but practically annoying for "Black Swan" analysis.
- **Impact:** Users cannot test extreme tail risks (e.g., "Performance during the 2020 crash" might be only 20 days).
- **Fix:** Change from HALT to WARNING ("Sample size < 30 (N=18). Results may be unreliable. Proceed?").

### 🟡 Minor: Ambiguity "Dead End"
- **Issue:** Identifying ambiguity halts the process without guiding the user.
- **Impact:** User hits a wall.
- **Fix:** When halting for ambiguity, propose specific valid hypotheses based on the data (e.g., "I can test for Positive Returns, Benchmark Comparison, or Stationarity. Which one?").

## 3. List of Prompts Tested
1. "Do I have positive returns?" (Normal Data)
2. "Do I have positive returns?" (Fat-tailed Data)
3. "Does my strategy beat the benchmark?" (Benchmark inference test)
4. "Does strategy perform worse when VIX > 25?" (Conditional/Rare event)
5. "Is it good?" (Ambiguous input)
6. "Does strategy perform better when regime == 'bull'?" (Text/Categorical condition)
7. "Do I have positive returns?" (Data with NaNs)
8. "Performance when VIX > 20 OR (VIX < 15 AND RSI > 70)" (Complex/Unsupported logic)

## 4. Recommendations
1. **Sanitize Inputs:** Add `df = df.dropna(subset=[returns_col])` immediately after column identification.
2. **Soft Failures:** Convert "HALT" instructions to "Confirm with User" dialogs where possible (especially for sample sizes and column ambiguity).
3. **Expand Vocabulary:** Add "good", "bad", "working" to a synonym list mapping to "Performance (One-Sample Test)".
4. **Interactive Fallback:** If benchmark fetch fails or column is missing, strictly default to a One-Sample test with a warning, rather than just halting on paired requests.
