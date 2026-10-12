---
name: statistical-testing
description: Rigorous statistical evaluation of trading strategy returns to determine if alpha is real or a statistical artifact. Supports hypothesis testing, benchmark comparison, conditional analysis, temporal validation, and distribution checks. Use when validating backtest results, comparing strategies, testing performance claims, optimizing parameters, or analyzing performance across market conditions. On-request advanced tests: adversarial robustness battery (sign-flip permutation, path shuffle, regime stress, sub-period consistency, block bootstrap, parameter plateau) and robust statistics (trimmed mean/Yuen, edge concentration, robust Sharpe) — run only when explicitly requested.
license: MIT
metadata:
  version: "2.2.0"
  capabilities: "hypothesis_testing, intent_detection, temporal_validation, benchmark_comparison, conditional_analysis, distribution_checks, multiple_testing_correction, overfitting_detection, effect_size, autocorrelation_check, fdr_correction, advanced_tests, sign_flip_permutation, path_shuffle, regime_stress, sub_period_consistency, block_bootstrap, parameter_plateau, trimmed_mean_yuen, edge_concentration, robust_sharpe"
---

# Statistical Testing Skill

## Purpose

Answer the critical question: **"Is this alpha real or just a statistical artifact?"**

This skill provides rigorous statistical evaluation of trading strategy returns using classical hypothesis testing, distribution analysis, benchmark comparison, and conditional/segmented analysis.

---

## Core Principles

```xml
<principles>
  <principle id="1">NO AMBIGUITY - If anything is unclear, HALT and ask the user. Never guess.</principle>
  <principle id="2">SPEED FIRST - Use scipy for classical tests; statsforecast/statsmodels only on explicit request</principle>
  <principle id="3">GRACEFUL DEGRADATION - If benchmark fetch fails, continue analysis and inform user</principle>
  <principle id="4">TWEET-STYLE OUTPUT - Default to concise summaries; expand on request</principle>
  <principle id="5">SMART DEFAULTS - Use LLM inference for asset class detection and benchmark selection</principle>
</principles>
```

---

## Prerequisites

### Required Input
- **Data file** with `date` and `returns` columns
- **User hypothesis** (explicit or inferable from prompt)

### Optional Input
- Benchmark data (column in file OR fetch permission)
- Confidence level (default: 95%)
- Conditional filters (e.g., "when VIX > 20")
- Specific test selection (default: auto-select based on hypothesis)

---

## Workflow

### Step 1: Data Discovery

**Action:** Use `load-data` skill to peek at file

**Expected Output:** XML manifest with:
```xml
<data_manifest>
  <source>
    <file_path>...</file_path>
    <row_count>...</row_count>
  </source>
  <temporal_info>
    <date_column>...</date_column>
    <frequency>daily|weekly|monthly</frequency>
    <date_range>
      <start>YYYY-MM-DD</start>
      <end>YYYY-MM-DD</end>
    </date_range>
  </temporal_info>
  <columns>
    <column name="..." type="..." role="returns_candidate|feature|benchmark_candidate"/>
    ...
  </columns>
  <sample_data format="markdown">
    [5 rows in table format]
  </sample_data>
  <inferences>
    <primary_returns>column_name</primary_returns>
    <benchmark_available>true|false</benchmark_available>
    <benchmark_column>column_name or null</benchmark_column>
  </inferences>
</data_manifest>
```

**Validation:**
- Date column identified (HALT if missing/ambiguous)
- Returns column(s) identified (HALT if missing/ambiguous)
- Benchmark column detected (optional, proceed without if missing)

**Multiple Returns Columns:**
```
IF multiple returns columns detected:
  1. List all candidates to user
  2. Ask: "Which column should I test?"
  3. IF no response → use first column
  4. Inform user which column was selected
```

**Frequency Mismatch:**
```
IF user specifies frequency BUT data frequency differs:
  1. HALT and inform user
  2. Show: "You said 'weekly' but data appears to be 'daily'"
  3. Ask: "Should I proceed with your specified frequency or use detected frequency?"
  4. IF user insists → use user's frequency (user override)
```

---

### Step 2: Hypothesis & Intent Parsing

**Action:** Parse user prompt to determine test type AND user intent

**Supported Hypothesis Types:**

| Type | Example Prompt | Test Method |
|------|----------------|-------------|
| **Performance** | "Does my strategy have positive returns?" | One-sample t-test, Wilcoxon signed-rank |
| **Outperformance** | "Does my strategy beat NIFTY50?" | Paired t-test, Wilcoxon signed-rank |
| **Comparison** | "Is strategy A better than strategy B?" | Independent t-test, Mann-Whitney U |
| **Conditional** | "Does drawdown differ when VIX > 20?" | Mann-Whitney U, t-test (based on distribution) |
| **Stationarity** | "Are returns stationary over time?" | ADF, KPSS (statsmodels, on explicit request) |

**Intent Detection (CRITICAL for Trading Strategies):**

Parse BOTH hypothesis AND intent to determine if temporal validation is needed.

| Intent Type | Keywords | Validation Required | Examples |
|-------------|----------|---------------------|----------|
| **PRIORITY 1: Explicit Validation** | out of sample, oos, walk forward, cross validation, hold out | **YES** (auto-run) | "Show out of sample results" |
| **PRIORITY 2: Future/Deploy** | work in future, going forward, deploy, robust, predict future, forecast, tomorrow, live trading, production | **YES** (auto-run) | "Will this work in future?" |
| **PRIORITY 3: Optimization** | optimal, best, maximize, improve, enhance, find threshold, find parameter | **YES** (ask user) | "What's optimal threshold?" |
| **PRIORITY 4: Exploratory** | why, explain, understand, analyze, correlate, relationship, pattern, what happened | **NO** | "Why did Feb perform poorly?" |

**Implementation Logic:**

```python
def detect_intent_and_validation_need(user_prompt):
    """Determine if temporal validation is needed"""

    # Priority 1: Explicit validation requests (no confirmation)
    if contains_any(user_prompt, [
        "out of sample", "oos", "walk forward",
        "cross validation", "hold out", "test set"
    ]):
        return {
            'intent': 'VALIDATION',
            'validation': 'REQUIRED',
            'confirm': False,
            'message': "Running out-of-sample validation..."
        }

    # Priority 2: Future/performance prediction (no confirmation)
    if contains_any(user_prompt, [
        "work in future", "going forward", "deploy", "robust",
        "predict future", "forecast", "tomorrow", "next month",
        "real trading", "live trading", "production"
    ]):
        return {
            'intent': 'PREDICTION',
            'validation': 'REQUIRED',
            'confirm': False,
            'message': "Testing robustness on unseen data..."
        }

    # Priority 3: Parameter optimization (ask confirmation)
    if contains_any(user_prompt, [
        "optimal", "best", "maximize", "improve", "enhance",
        "find threshold", "find parameter", "best value"
    ]):
        return {
            'intent': 'OPTIMIZATION',
            'validation': 'REQUIRED',
            'confirm': True,
            'message': "Optimization requires validation (prevents overfitting)"
        }

    # Priority 4: Exploratory analysis (no validation)
    if contains_any(user_prompt, [
        "why", "explain", "understand", "analyze",
        "correlate", "relationship", "pattern",
        "what happened", "how did", "statistical test"
    ]):
        return {
            'intent': 'OBSERVATION',
            'validation': 'NOT_NEEDED',
            'confirm': False
        }

    # Default: Ask user
    return {
        'intent': 'UNCLEAR',
        'validation': 'ASK_USER',
        'confirm': True
    }
```

**User Interaction Flow:**

```python
intent_result = detect_intent_and_validation_need(user_prompt)

IF intent_result['confirm']:
    # Ask user for confirmation
    print(f"Intent: {intent_result['intent']}")
    print(f"{intent_result['message']}")
    user_confirms = ask("Proceed? [Y/n]: ")

    IF NOT user_confirms:
        Ask alternative approach
        return

IF intent_result['validation'] == 'REQUIRED':
    # Go to Step 6.5: Temporal Validation
    run_temporal_validation()
    return

IF intent_result['validation'] == 'NOT_NEEDED':
    # Continue with full dataset analysis
    proceed_with_full_dataset()
    return
```

**Example Interactions:**

```
User: "Does Feb differ from baseline?"
→ Intent: OBSERVATION
→ Action: Use full dataset (209 days)
→ No validation needed

User: "What's the optimal volatility threshold?"
→ Intent: OPTIMIZATION
→ Action: "Optimization requires validation (prevents overfitting)"
          "Run walk-forward validation? [Y/n]: "

User: "Will this work in future?"
→ Intent: PREDICTION
→ Action: Auto-run walk-forward validation
→ "Testing robustness on unseen data..."

User: "Show out of sample results"
→ Intent: VALIDATION
→ Action: Auto-run validation (no prompt needed)
```

**Ambiguity Rule:**
```
IF hypothesis unclear OR multiple interpretations possible:
  → HALT
  → Present possible interpretations to user
  → Ask user to clarify
  → NEVER proceed with ambiguity
```

**User-Specified Tests:**
```
IF user explicitly specifies test (e.g., "Run Mann-Whitney U test"):
  → Skip auto-selection
  → Use specified test
  → Validate test is appropriate for data
```

---

### Step 3: Benchmark Resolution

**Priority Order:**
1. Benchmark column exists in data → use it
2. User explicitly specified benchmark → use it
3. LLM infers asset class → ask permission to fetch
4. Graceful degradation → continue without benchmark

**Asset Class Inference (LLM-Powered):**
```
User mentions → LLM infers → Suggests benchmark

Examples:
- "India equity strategy" → NIFTY50 or SENSEX
- "US equity" → SPY or ^GSPC
- "crypto strategy" → Bitcoin (BTC-USD)
- "forex EUR/USD" → DXY or currency-specific index
- "gold trading" → GLD or GOLD

NO hardcoded mappings - rely on LLM context understanding
```

**Fetch Process:**
```xml
<benchmark_fetch>
  <step_1>Detect asset class from user prompt</step_1>
  <step_2>Suggest benchmark to user</step_2>
  <step_3>Ask: "May I fetch [BENCHMARK] data from yfinance for comparison?"</step_3>
  <step_4>
    IF user approves:
      → Fetch from yfinance
      → Match date range to strategy data
      → Calculate returns if price data
    ELSE:
      → Ask user to provide benchmark data
  </step_4>
  <step_5>
    IF fetch fails:
      → Inform: "⚠️ Could not fetch [BENCHMARK] from yfinance"
      → Ask: "Please provide benchmark data or continue without?"
      → IF no response → continue analysis
      → Skip benchmark-dependent metrics
      → Report: "⚠️ Benchmark metrics not available"
  </step_5>
</benchmark_fetch>
```

**Critical Rule:**
```
IF benchmark fetch fails AND test REQUIRES benchmark:
  → HALT
  → Ask user for benchmark data

IF benchmark fetch fails AND test is OPTIONAL:
  → WARN user
  → Continue with absolute performance tests
  → Omit benchmark comparison from report
```

---

### Step 4: Distribution Checks

**Action:** Always check distribution before selecting parametric vs non-parametric tests.
Also check for autocorrelation — inflated t-statistics are the most common error in trading strategy validation.

**Pre-Test: Autocorrelation Check (Always Run)**
```python
from scipy.stats import ljungbox

# Ljung-Box test for serial correlation (lags 1-10)
lb_result = ljungbox(returns, lags=10, return_df=True)
significant_lags = lb_result[lb_result['lb_pvalue'] < 0.05]

IF significant_lags is not empty:
    max_autocorr = returns.autocorr(lag=1)
    → WARN: "⚠️ Autocorrelation detected (lag 1: {max_autocorr:.2f}, Ljung-Box p={min_p:.3f})"
    → WARN: "   Standard errors may be underestimated. Switching to HAC-robust standard errors."
    use_hac = True
ELSE:
    use_hac = False  # Silent — no warning needed
```

**HAC-Robust Testing (when autocorrelation detected):**
```python
IF use_hac:
    # Use Newey-West HAC standard errors instead of standard t-test
    import statsmodels.api as sm
    from statsmodels.stats.sandwich_covariance import cov_hac

    model = sm.OLS(returns, np.ones(len(returns)))
    hac_result = model.fit(cov_type='HAC', cov_kwds={'maxlags': int(len(returns)**0.25)})
    p_value = hac_result.pvalues[0]
    # Report: "HAC-robust t-test" instead of standard t-test
```

**Normality Tests (scale-aware):**
```python
N = len(returns)

IF N <= 50:
    # Shapiro-Wilk: most powerful for small samples
    stat, p_sw = shapiro(returns)
    normality_p = p_sw
    normality_test_used = "Shapiro-Wilk"
ELSE:
    # Anderson-Darling: more powerful in tails for larger samples
    # Shapiro-Wilk loses meaning and almost always rejects for N > 2000
    from scipy.stats import anderson
    result = anderson(returns, dist='norm')
    # Use 5% critical value
    normality_p = None  # Anderson-Darling returns critical values, not p-values
    is_normal_ad = result.statistic < result.critical_values[2]  # index 2 = 5%
    normality_test_used = "Anderson-Darling"

# Always compute skewness and kurtosis regardless of N
skewness = returns.skew()
kurtosis = returns.kurtosis()  # excess kurtosis (normal = 0)

# Decision rule: non-normal if ANY of:
#   |skewness| > 1.0, OR
#   excess kurtosis > 7, OR
#   normality test rejects at 5%
is_non_normal = (abs(skewness) > 1.0) or (kurtosis > 7) or (not is_normal)

IF is_non_normal:
    distribution = "non-normal"
    use_parametric = False
    # Always show the reason
    reasons = []
    if abs(skewness) > 1.0: reasons.append(f"skewness={skewness:.2f}")
    if kurtosis > 7: reasons.append(f"excess kurtosis={kurtosis:.2f}")
    if not is_normal: reasons.append(f"{normality_test_used} rejected")
    print(f"⚠️ Non-normal distribution: {', '.join(reasons)}")
ELSE:
    distribution = "normal"
    use_parametric = True

# Auto-select appropriate tests
IF use_hac:
    tests = ["HAC-robust t-test (Newey-West)"]
ELIF use_parametric:
    tests = ["t-test", "paired t-test"]
ELSE:
    tests = ["Wilcoxon signed-rank", "Mann-Whitney U"]
```

**User Override:**
```
IF user explicitly requests parametric test BUT distribution is non-normal:
  → WARN: "Returns are not normally distributed ({reasons})"
  → Ask: "Proceed with parametric test anyway, or use non-parametric?"
  → Respect user's final decision
```

---

### Step 5: Conditional Analysis (Optional)

**Trigger:** User prompt contains conditional language

**Examples:**
- "when VIX > 20"
- "during high volatility periods"
- "when feature1 > 1 AND feature2 < 5"

**Supported Complexity (v1.0):**
```xml
<conditional_support>
  <single_condition>
    <example>when VIX > 20</example>
    <operators>==, !=, >, <, >=, <=</operators>
  </single_condition>

  <multiple_and max="3">
    <example>when VIX > 20 AND market_cap > 1000 AND regime == 'bull'</example>
    <restriction>All conditions must use AND (no mixing with OR)</restriction>
  </multiple_and>

  <multiple_or max="3">
    <example>when VIX > 20 OR regime == 'bear'</example>
    <restriction>All conditions must use OR (no mixing with AND)</restriction>
  </multiple_or>

  <not_supported>
    <mixed_logic>(A AND B) OR C</mixed_logic>
    <nested_conditions>NOT (A OR B)</nested_conditions>
    <range_syntax>feature1 BETWEEN 1 AND 5</range_syntax>
  </not_supported>
</conditional_support>
```

**Parsing Process:**
```xml
<conditional_parsing>
  <step_1>
    <action>LLM extracts conditions from natural language</action>
    <output_format>
      <conditional_test>
        <metric>max_drawdown|sharpe_ratio|returns|etc</metric>
        <hypothesis>lower_when_true|higher_when_true|different</hypothesis>
        <conditions>
          <condition id="1">
            <column>VIX</column>
            <operator>></operator>
            <value>20</value>
          </condition>
          <condition id="2">
            <column>market_cap</column>
            <operator>></operator>
            <value>1000</value>
          </condition>
          <logic>AND</logic>
        </conditions>
      </conditional_test>
    </output_format>
  </step_1>

  <step_2>
    <action>Validation</action>
    <checks>
      - All referenced columns exist in data
      - Operators match column types (numeric/string/boolean)
      - Values are appropriate type
      - Max 3 conditions enforced
      - Logic is consistent (all AND or all OR)
    </checks>
    <on_failure>HALT and ask user to clarify/fix</on_failure>
  </step_2>

  <step_3>
    <action>Data Segmentation</action>
    <method>
      # Generate pandas query
      IF logic == "AND":
          query = " and ".join([f"{col} {op} {val}" for col, op, val in conditions])
      ELSE:
          query = " or ".join([f"{col} {op} {val}" for col, op, val in conditions])

      # Segment data
      group_true = df.query(query)
      group_false = df.query(f"not ({query})")
    </method>
  </step_3>

  <step_4>
    <action>Validation Checks</action>
    <checks>
      - Each group has ≥30 observations (statistical validity)
      - No empty groups
      - No contradictory conditions (e.g., X > 10 AND X < 5)
    </checks>
    <warnings>
      IF group imbalance (e.g., 1000 vs 50):
        → WARN user about imbalance
        → Recommend non-parametric tests
    </warnings>
  </step_4>

  <step_5>
    <action>Run Statistical Tests on Each Segment</action>
    <method>
      FOR EACH segment:
          Run distribution checks
          Run hypothesis tests
          Calculate metrics (Sharpe, drawdown, etc.)

      Compare segments:
          Test: Mann-Whitney U or t-test (based on distribution)
          Calculate effect size
          Report statistical significance
    </method>
  </step_5>
</conditional_parsing>
```

**Edge Cases:**

| Case | Action |
|------|--------|
| Empty group (no observations match condition) | HALT + inform user + show column min/max |
| Imbalanced groups (e.g., 1000 vs 10) | WARN + proceed with non-parametric test |
| Contradictory conditions (X > 10 AND X < 5) | HALT + explain contradiction |
| Missing values in condition column | WARN + show % missing + ask to drop NaN or impute |
| Condition column doesn't exist | HALT + list available columns + ask user |
| Type mismatch (e.g., string column with > operator) | HALT + explain type error |

---

### Step 6: Statistical Testing

**Test Selection Matrix:**

| Hypothesis | Distribution | Test |
|------------|--------------|------|
| Positive returns | Normal | One-sample t-test |
| Positive returns | Non-normal | Wilcoxon signed-rank |
| Outperformance | Normal | Paired t-test |
| Outperformance | Non-normal | Wilcoxon signed-rank |
| Strategy comparison | Normal | Independent t-test |
| Strategy comparison | Non-normal | Mann-Whitney U |
| Conditional comparison | Normal | t-test |
| Conditional comparison | Non-normal | Mann-Whitney U |

**Effect Size (Always Compute)**
```python
# Compute alongside every hypothesis test — never omit
IF use_parametric:
    # Cohen's d for t-tests
    effect_size = (returns.mean() - mu0) / returns.std()
    effect_label = "Cohen's d"
ELSE:
    # Rank-biserial correlation for Wilcoxon / Mann-Whitney
    # r = 1 - (2W) / (n1 * n2)  for Mann-Whitney
    # r = Z / sqrt(N)            for Wilcoxon signed-rank
    effect_size = compute_rank_biserial(test_statistic, n)
    effect_label = "rank-biserial r"

# Magnitude labels (Cohen 1988)
IF abs(effect_size) < 0.2:
    magnitude = "negligible"
ELIF abs(effect_size) < 0.5:
    magnitude = "small"
ELIF abs(effect_size) < 0.8:
    magnitude = "medium"
ELSE:
    magnitude = "large"
```

**Multiple Testing Correction:**
```python
IF running multiple tests (>1):
    # Default: Benjamini-Hochberg FDR (preferred for exploratory trading analysis)
    # Controls false discovery rate — less conservative than Bonferroni
    from statsmodels.stats.multitest import multipletests
    reject, p_adjusted, _, _ = multipletests(p_values, method='fdr_bh')

    print(f"⚠️ Applied Benjamini-Hochberg FDR correction for {n} tests")
    # Use p_adjusted for significance decisions

    # Switch to Bonferroni only when user explicitly wants confirmatory testing
    IF user_requests_bonferroni:
        reject, p_adjusted, _, _ = multipletests(p_values, method='bonferroni')
        print(f"⚠️ Applied Bonferroni correction for {n} tests (adjusted α={0.05/n:.4f})")
```

**Additional Metrics:**
- **Sharpe Ratio** (annualized)
- **Maximum Drawdown**
- **Win Rate** (% positive returns)
- **Mean/Median Returns**

---

### Step 6.5: Temporal Validation (CRITICAL for Trading Strategies)

**WHY THIS IS CRITICAL:**

Statistical significance on full dataset ≠ Real trading performance

**Common Pitfall:** Optimizing parameters on entire dataset leads to overfitting

**CRITICAL RULE:**
```
IF testing trading strategy parameters (thresholds, filters, optimization):
  → MUST use temporal validation
  → NEVER test on entire dataset
  → ALWAYS report in-sample vs out-of-sample performance difference
  → Warn about overfitting if degradation > 20%
```

**When to Use:**

| Scenario | Validation Required | Reason |
|----------|---------------------|---------|
| Optimize parameters | **YES** | Prevents overfitting |
| Compare strategies | **YES** | Ensures robust winner |
| Deploy to production | **YES** | Must work on unseen data |
| Understand what happened | **NO** | Historical analysis OK |
| Test hypothesis | **NO** | Full dataset sufficient |
| Exploratory analysis | **NO** | Understanding patterns |

**Validation Methods:**

### 1. Train/Test Split (Basic)

Split data by time (e.g., 80/20)

**When to use:**
- Quick validation
- Limited data (<500 days)
- Initial parameter screening

**Example:**
```python
split_idx = int(len(data) * 0.8)
train = data.iloc[:split_idx]  # First 80%
test = data.iloc[split_idx:]   # Last 20%

# Optimize on TRAIN
optimal_threshold = find_best_threshold(train)

# Apply to TEST (unseen!)
test_performance = apply_filter(test, optimal_threshold)

# Check degradation
degradation = (train_sharpe - test_sharpe) / train_sharpe
IF degradation > 0.20:  # 20% threshold
    → "⚠️ OVERFITTING DETECTED"
    → "DO NOT IMPLEMENT"
```

### 2. Walk-Forward Validation (Recommended)

Rolling window approach - most realistic for trading

**When to use:**
- Parameter optimization
- Strategy comparison
- Production deployment decisions
- Most trading strategy validation

**Parameters:**
- `train_window`: Size of training period (default: 120 days ~ 6 months)
- `test_window`: Size of test period (default: 30 days ~ 1 month)
- `step_size`: How much to move forward each iteration (default: 30 days)

**Example:**
```python
window_size = 120  # 6 months
step_size = 30     # 1 month
results = []

for i in range(window_size, len(data), step_size):
    train = data[i-window_size:i]
    test = data[i:i+step_size]

    # Optimize on TRAIN
    optimal_param = optimize(train)

    # Test on TEST (unseen!)
    result = backtest(test, optimal_param)
    results.append(result)

# Analyze consistency
mean_return = np.mean(results)
std_return = np.std(results)

IF std_return > 0.5 * mean_return:
    → "⚠️ UNSTABLE PERFORMANCE"
    → "DO NOT DEPLOY"
```

### 3. Expanding Window (Alternative)

Train on all historical data, test on next period, expand training set

**When to use:**
- Limited data (< 2 years)
- Want maximum training data
- Long-only strategies

**Example:**
```python
min_train = 120  # Minimum 6 months to start
results = []

for i in range(min_train, len(data) - 30):
    train = data.iloc[:i]        # All history up to i
    test = data.iloc[i:i+30]    # Next 30 days

    optimal_param = optimize(train)
    result = backtest(test, optimal_param)
    results.append(result)
```

**Output Format for Temporal Validation:**

```markdown
📊 Temporal Validation: Walk-Forward (6mo train, 1mo test)

⚠️ OVERFITTING DETECTED:

Train Performance (In-Sample):
- Sharpe: 8.19
- Return: 0.180% per day
- Period: Apr 2025 - Dec 2025

Test Performance (Out-of-Sample):
- Sharpe: 3.25
- Return: 0.095% per day
- Period: Jan 2026 - Feb 2026

Degradation Metrics:
- Sharpe degradation: 60.3%
- Return degradation: 47.2%
- ⚠️ EXCEEDS 20% THRESHOLD

❌ CONCLUSION: DO NOT IMPLEMENT
   Massive overfitting detected
   In-sample performance does NOT generalize

Walk-Forward Fold Results:
- Fold 1 (Jan): Sharpe 2.14, Return: 0.082%
- Fold 2 (Feb): Sharpe 5.12, Return: 0.145%
- Inconsistent: Std dev = 1.92 × mean

Recommendation: Strategy parameters are overfit to historical data
              Use simpler approach or collect more data
```

**Error Handling:**

```python
IF user asks to optimize on full dataset:
  → WARNING: "Optimizing on full dataset will overfit"
  → SUGGEST: "Use walk-forward validation instead"
  → IF user insists:
    → Run analysis with full dataset
    → Add disclaimer: "⚠️ WARNING: Results may be overfit"
    → "   May not work in live trading"
    → "   Recommend: Validate with out-of-sample testing"
```

**Integration with Statistical Tests:**

**Always run temporal validation FIRST:**
```
1. Temporal validation → Check if strategy is robust
2. If robust: Run hypothesis testing → Check if alpha is real
3. If both pass: Strategy is ready for deployment
```

**Don't skip validation:**

❌ WRONG: "Does the 1.5% volatility filter improve Sharpe?"
→ Test on full dataset → Sharpe 7.05 (p=0.0064)
→ "Implement!" → Overfit!

✓ CORRECT: "Does the 1.5% volatility filter improve Sharpe?"
→ Detect intent: OPTIMIZATION
→ Run walk-forward validation
→ Train Sharpe: 8.19, Test Sharpe: 3.25
→ "60% degradation - DO NOT IMPLEMENT"

**Key Insight:**

- "Does it work?" → Can test on full dataset (historical)
- "Will it work in future?" → REQUIRES temporal validation
- These are DIFFERENT questions!

---

### Step 6.6: Advanced Tests (On Request ONLY)

**Reference implementation:** `references/advanced_tests.py` — canonical, verified functions for all tests below (A1–A6, B1–B3, `run_battery()`); numpy/pandas/scipy only. Prefer copying/importing from it over re-implementing from prose.

**Original references (Group A ports):** the adversarial tests are adapted from [QuantGPT](https://github.com/Miasyster/QuantGPT) (MIT License):
- https://github.com/Miasyster/QuantGPT/blob/main/quantgpt/adversarial_validator.py — label permutation, temporal shuffle, random universe, noise injection
- https://github.com/Miasyster/QuantGPT/blob/main/quantgpt/anti_overfit.py — IC stability, sub-sample stress, placebo, half-life

Port mapping (factor tests → returns-series analogs) is documented in fastbt issues #17–#19.

Two suites of advanced tests are available. **They are NEVER auto-run** — not by
intent detection, not by workflow logic, not as "helpful extras". Running any of
them is entirely the user's choice.

**CRITICAL RULES:**
```
1. Run an advanced test ONLY on explicit user request
2. Invocation ambiguous → list available tests (table below) and ask. NEVER guess.
3. Standard reports may append AT MOST a one-line footer:
   "Advanced tests available on request: adversarial battery, robust statistics."
   No prompts, no confirmations, no auto-runs.
```

#### Catalog

**Group A — Adversarial Robustness** *("does the edge survive attempts to destroy it?")*

| ID | Test | Answers | Pass criterion | Needs |
|----|------|---------|----------------|-------|
| A1 | Sign-flip permutation | Is the mean positive by chance? Exact-ish null, no normality assumption, fat-tail immune | p < 0.05 vs 1000 sign-flipped means | date + returns |
| A2 | Path shuffle (block) | Is my drawdown/streak sequencing luck? | real max drawdown not an outlier vs 1000 block-shuffled paths | date + returns |
| A3 | Regime stress | Does the edge hold across regimes (bull/bear/sideways, high/low vol)? | same-sign mean return in ≥60% of regimes (≥30 obs each) | benchmark |
| A4 | Sub-period consistency | Is the edge stable across years? | positive-day rate ≥55% AND no yearly sign reversal | date + returns |
| A5 | Block bootstrap stability | Is the edge stable across resampled histories? Also yields CIs on mean & Sharpe | ≥70% of resamples sign-consistent | date + returns |
| A6 | Parameter plateau | Is my optimum a plateau or an overfit spike? | neighbor metric at θ*±δ retains ≥50% of optimum | sweep table (param → metric) |

**Group B — Robust Statistics** *("is the edge outlier-dependent?")*

| ID | Test | Answers | Output | Needs |
|----|------|---------|--------|-------|
| B1 | Edge concentration | How much P&L comes from a few lucky days? | mean / 10%-trimmed mean / median trio + top-5-day % of cumulative return + verdict. Optional pass: trimmed mean ≥ 50% of mean | date + returns |
| B2 | Yuen's trimmed t-test | Is the typical-day mean positive, robust to tails? (middle rung: t-test → Yuen → Wilcoxon) | t, p on trimmed mean | date + returns |
| B3 | Robust Sharpe | Is my Sharpe tail-inflated? | trimmed mean / winsorized vol and median / (1.4826·MAD) variants vs standard Sharpe | date + returns |

#### Invocation Parsing

| User says (examples) | Runs |
|----------------------|------|
| "run A3", "run the sign-flip permutation test", "do a permutation test" | That single test |
| "run the adversarial battery", "stress test my strategy", "robustness tests" | Group A (A1–A5; A6 auto-included only if a sweep table is present or user provides one) |
| "run robust statistics", "robust stats suite", "trimmed mean analysis" | Group B (B1–B3) |
| "run everything", "full suite", "run both batteries" | Group A + Group B |
| "run A1, A3 and edge concentration" | Exactly those tests |

```
IF request names a known test/group → run it (those tests only)
IF request mentions a suite keyword but scope unclear → ask: "Both groups or just [A|B]?"
IF request mentions an unknown test name → list catalog + ask
```

#### Prerequisites

```
A3: benchmark required → resolve via existing Step 3 (column > user-specified > fetch w/ permission).
    Unavailable → ask user; skip only if user says so.
A6: sweep table required (param + metric columns, e.g. threshold → sharpe).
    Absent → inform + skip. NEVER fabricate/perturb data to simulate neighbors.
    (Engine-driven re-runs tracked in fastbt issue #19.)
All others: date + returns only.
```

#### Test Specifications

**A1 — Sign-flip permutation**
```python
B = 1000
rng = np.random.default_rng(seed)  # seed user-configurable, default 42
real_mean = returns.mean()
flips = rng.choice([-1, 1], size=(B, len(returns)))
null_means = (returns.values * flips).mean(axis=1)
p_perm = float((null_means >= real_mean).mean())  # one-sided positive-mean H1
# Exact under symmetric null. IF Ljung-Box flagged autocorrelation →
# use block sign-flip (flip whole ~10d blocks) or defer to A5 bootstrap.
```

**A2 — Path shuffle** ⚠️ *Only sequencing-sensitive statistics are testable — mean, vol, and Sharpe are INVARIANT under shuffling. Never use this test on Sharpe.*
```python
block, B = 10, 1000
n_blocks = len(returns) // block
blocks = returns.values[:n_blocks * block].reshape(n_blocks, block)
for _ in range(B):
    order = rng.permutation(n_blocks)
    path = blocks[order].ravel()
    mdd = max_drawdown(path)          # + worst streak / ulcer index
# Pass: real max drawdown within [5th, 95th] pctile of shuffled mdd distribution
```

**A3 — Regime stress** (reuses Step 3 benchmark + Step 5 machinery)
```python
cum = bench_ret.rolling(60, min_periods=30).sum()
vol = bench_ret.rolling(60, min_periods=30).std()
regimes = {"bull": cum > 0.05, "bear": cum < -0.05,
           "sideways": (cum.abs() <= 0.05),
           "high_vol": vol > vol.median(), "low_vol": vol <= vol.median()}
# Per regime with ≥30 obs: mean strategy return + effect size.
# Pass: ≥60% of qualifying regimes share the overall sign.
```

**A4 — Sub-period consistency**
```python
yearly = returns.groupby(returns.index.year)
# Pass: (positive-day rate ≥ 0.55) AND (every year's mean shares overall sign)
# <2 years of data → calendar halves; <6 months → HALT (insufficient)
```

**A5 — Block bootstrap** (keyed off existing Step 4 Ljung-Box pre-check)
```python
block = 10 if use_hac else 1          # moving-block if autocorrelated, else iid
B = 1000 → resampled mean & Sharpe per draw
# Outputs: sign-consistency rate (pass ≥ 0.70), percentile CIs on mean & Sharpe
```

**A6 — Parameter plateau** (data-only tier; engine tier = issue #19)
```python
# Locate optimum θ*, take available neighbors θ*±δ (±2δ if present)
retention = min(neighbor_metric) / optimal_metric
# Pass: retention ≥ 0.50. Also flag high local curvature (loess/quadratic fit).
# Output: ASCII neighborhood table + PLATEAU ✅ / SPIKE ⚠️ verdict
```

**B1 — Edge concentration**
```python
from scipy.stats import trim_mean
tm = trim_mean(returns, 0.1)          # trim FIXED at 10% (20% extreme tails);
                                       # NEVER tune trim for significance
top5_pct = returns.nlargest(5).sum() / returns.sum()
# Report trio + top5_pct + verdict:
#   mean ≈ trimmed → "edge spread across typical days" (robust)
#   mean ≫ trimmed or top5 dominant → "outlier-dependent edge" (fragile,
#   capacity-limited, cost-sensitive)
```

**B2 — Yuen's trimmed t-test** — two-sample: native `scipy.stats.ttest_ind(a, b, trim=0.1)`
One-sample (scipy's `ttest_1samp` has NO trim param — verified): manual impl:
```python
def yuen_1samp(x, trim=0.1, mu=0.0):
    n = len(x); g = int(np.floor(trim * n)); df = n - 2*g - 1
    xs = np.sort(x)
    w = xs.copy(); w[:g] = xs[g]; w[-g:] = xs[-g-1]      # Winsorize
    se = np.sqrt(np.sum((w - w.mean())**2) / df / ((1 - 2*trim)**2 * n))
    t = (xs[g:-g].mean() - mu) / se
    return t, 2 * stats.t.sf(abs(t), df)
```
Caveat: on skewed returns the trimmed mean estimates "mean of the middle 80% of days" — label it as such, never as "the mean".

**B3 — Robust Sharpe**
```python
from scipy.stats import trim_mean, mstats
winsor_vol = mstats.winsorize(returns, limits=[0.05, 0.05]).std()
robust_sharpe = trim_mean(returns, 0.1) / winsor_vol
mad_scale = np.median(np.abs(returns - np.median(returns))) * 1.4826
median_sharpe = np.median(returns) / mad_scale
# Report alongside standard Sharpe; flag large divergence as tail-inflation
```

#### Composite Scoring (groups / full suite only; single tests report individually)

```
score = passed / total × 100   (diagnostic-only outputs B1/B3 excluded from scoring
                               unless user opted into their pass criteria)
≥80 PASS | 60–79 CAUTION | 40–59 DOUBTFUL | <40 HIGH-RISK
Group A and B scored separately when both run; also report combined score.
```

**Output format:**
```markdown
🛡️ Advanced Tests: [Group A | Group B | Full Suite]

| Test | Result | Key Metric |
|------|--------|------------|
| A1 Sign-flip permutation | ✅ PASS | p = 0.012 |
| ...

Composite: 5/5 passed → 100 → PASS
🎯 Interpretation: [1-2 sentences]
⚠️ Notes: [autocorrelation/block settings, skipped tests + why]
```

---

### Step 7: Report Generation

**Default Output Format (Tweet-Style):**

```markdown
📊 Result: [One-line verdict]

Key Metrics:
- Sharpe: X.XX
- p-value: 0.XXX
- Effect size: X.XX ([Cohen's d | rank-biserial r]) — [negligible|small|medium|large]
- Test: [test name]
- Confidence: 95%

🎯 Interpretation: [Plain English, 1-2 sentences]

⚠️ Note: [Distribution warnings, autocorrelation warnings, if any]
```

**Two-Sample Comparison Output (always report both effect sizes):**

```markdown
📊 Result: [One-line verdict]

Key Metrics:
- p-value: 0.XXX
- Cohen's d: X.XX — [negligible|small|medium|large]  (mean-based)
- Rank-biserial r: X.XX — [negligible|small|medium|large]  (rank-based, robust)
- Test: [test name]
- Confidence: 95%

🎯 Interpretation: [Plain English, 1-2 sentences]

⚠️ Note: [Distribution warnings, autocorrelation warnings, if any]
```

**Conditional Analysis Output:**

```markdown
📊 Conditional Analysis: [Metric] when [Condition]

| Condition | N | Median | Mean | Std Dev | p-value | Cohen's d | Rank-biserial r |
|-----------|---|--------|------|---------|---------|-----------|-----------------|
| [Condition TRUE] | XXX | X.XX | X.XX | X.XX | - | - | - |
| [Condition FALSE] | XXX | X.XX | X.XX | X.XX | - | - | - |
| **Difference** | - | **X.XX** | **X.XX** | - | **0.XXX** | **X.XX ([mag])** | **X.XX ([mag])** |

🎯 Result: [Interpretation of statistical significance and practical magnitude]

Test: [Test name]
Confidence: 95%

⚠️ Notes: [Any warnings]
```

**File Persistence:**
```
Automatically save report to markdown file:
  Filename: {test_type}_{timestamp}.md
  Location: Current working directory or user-specified path

Example: performance_test_20260217_132537.md
```

**Detailed Output (On Request):**
```
IF user asks "explain more" OR "show details":
  → Include full test statistics
  → Show distribution plots (if visualization requested)
  → Include assumptions and violations
  → Show effect sizes
  → Include confidence intervals
```

**Visualization (On Request Only):**
```
IF user requests plots:
  Generate:
    - Distribution histogram
    - QQ plot (normality check)
    - Comparison charts (for conditional analysis)

  Save as PNG files alongside markdown report
```

---

## Example Workflows

### Example 1: Simple Alpha Test

**User Prompt:**
```
"Is my momentum strategy's alpha real? File: returns.csv"
```

**Execution:**
```xml
<workflow>
  <step_1 skill="load-data">
    peek_file("returns.csv")
    → Detects: date, strategy_returns columns
  </step_1>

  <step_2 skill="statistical-testing">
    Hypothesis: Performance test (positive returns)
    Distribution check: Non-normal (p=0.023)
    Test: Wilcoxon signed-rank
    Result: p=0.003 (significant)
  </step_2>

  <output>
    📊 Result: Your momentum strategy has statistically significant positive returns

    Key Metrics:
    - Median Return: 0.12% per day
    - p-value: 0.003
    - Effect size: 0.31 (rank-biserial r) — small
    - Test: Wilcoxon signed-rank
    - Confidence: 95%

    🎯 Strong evidence of real alpha (not a statistical artifact). Effect is small — ensure transaction costs don't erode it.

    ⚠️ Note: Returns not normally distributed (used non-parametric test)
  </output>
</workflow>
```

---

### Example 2: Benchmark Comparison with Fetch

**User Prompt:**
```
"Test if my India equity strategy beats the market. File: strategy.csv"
```

**Execution:**
```xml
<workflow>
  <step_1 skill="load-data">
    peek_file("strategy.csv")
    → Detects: date, returns columns
    → No benchmark column found
  </step_1>

  <step_2 skill="statistical-testing">
    Hypothesis: Outperformance test
    Asset class inference: "India equity" → NIFTY50

    Ask user: "May I fetch NIFTY50 data from yfinance for comparison?"
    User: "Yes"

    Fetch NIFTY50 (2020-01-01 to 2025-12-31)
    Calculate returns

    Distribution check: Both non-normal
    Test: Wilcoxon signed-rank (paired)
    Result: p=0.012 (significant)
  </step_2>

  <output>
    📊 Result: Your strategy significantly outperforms NIFTY50

    Key Metrics:
    - Strategy Sharpe: 1.45
    - NIFTY50 Sharpe: 0.89
    - Excess Sharpe: +0.56
    - p-value: 0.012
    - Effect size: 0.22 (rank-biserial r) — small
    - Test: Wilcoxon signed-rank (paired)
    - Confidence: 95%

    🎯 Strong evidence of outperformance, though effect size is small.

    ⚠️ Note: Returns not normally distributed (used non-parametric test)
  </output>
</workflow>
```

---

### Example 3: Conditional Analysis

**User Prompt:**
```
"Does my strategy have lower drawdown when VIX > 20? File: data.csv"
```

**Execution:**
```xml
<workflow>
  <step_1 skill="load-data">
    peek_file("data.csv")
    → Detects: date, strategy_returns, VIX columns
  </step_1>

  <step_2 skill="statistical-testing">
    Hypothesis: Conditional comparison
    Metric: max_drawdown
    Condition: VIX > 20

    Parse condition:
      <condition>
        <column>VIX</column>
        <operator>></operator>
        <value>20</value>
      </condition>

    Validate: VIX column exists ✓

    Segment data:
      Group TRUE (VIX > 20): 234 observations
      Group FALSE (VIX ≤ 20): 1016 observations

    Calculate drawdown for each group
    Test: Mann-Whitney U
    Result: p=0.002 (significant difference)
  </step_2>

  <output>
    📊 Conditional Analysis: Drawdown when VIX > 20

    | Condition | N | Median DD | Mean DD | p-value |
    |-----------|---|-----------|---------|---------|
    | VIX > 20  | 234 | -15.2% | -16.8% | - |
    | VIX ≤ 20  | 1016 | -8.3% | -9.1% | - |
    | **Difference** | - | **-6.9%** | **-7.7%** | **0.002** |

    🎯 Result: Drawdown is significantly WORSE when VIX > 20 (opposite of hypothesis)

    Test: Mann-Whitney U (non-parametric)
    Confidence: 95%

    ⚠️ Note: Returns not normally distributed in either group
  </output>
</workflow>
```

---

### Example 4: Multiple Conditions (AND)

**User Prompt:**
```
"Is Sharpe ratio better when VIX > 20 AND market_cap > 1000? File: features.csv"
```

**Execution:**
```xml
<workflow>
  <step_1 skill="load-data">
    peek_file("features.csv")
    → Detects: date, returns, VIX, market_cap columns
  </step_1>

  <step_2 skill="statistical-testing">
    Hypothesis: Conditional comparison
    Metric: sharpe_ratio
    Conditions:
      <condition id="1">VIX > 20</condition>
      <condition id="2">market_cap > 1000</condition>
      <logic>AND</logic>

    Validate: Both columns exist ✓

    Segment data:
      Group TRUE (VIX > 20 AND market_cap > 1000): 156 observations
      Group FALSE (NOT both conditions): 1094 observations

    Calculate Sharpe for each group
    Test: t-test (both groups normal)
    Result: p=0.234 (NOT significant)
  </step_2>

  <output>
    📊 Conditional Analysis: Sharpe when VIX > 20 AND market_cap > 1000

    | Condition | N | Sharpe | p-value |
    |-----------|---|--------|---------|
    | Both TRUE | 156 | 1.23 | - |
    | NOT both | 1094 | 1.15 | - |
    | **Difference** | - | **+0.08** | **0.234** |

    🎯 Result: No significant difference in Sharpe ratio (p=0.234)

    Test: Independent t-test
    Confidence: 95%
  </output>
</workflow>
```

---

## Advanced Features

### ARIMA Parameter Comparison (On Request)

**User Prompt:**
```
"Do ARIMA(3,1,2) parameters work better than ARIMA(2,1,1) on my returns?"
```

**Note:** This is NOT about fitting ARIMA models. User has already generated returns using different ARIMA parameters and wants to compare them.

**Execution:**
```
Requires: Two returns columns (arima_3_1_2_returns, arima_2_1_1_returns)
Test: Paired comparison (t-test or Wilcoxon)
Output: Which parameter set produces better risk-adjusted returns
```

---

## Error Handling

### Common Errors and Responses

| Error | Response |
|-------|----------|
| File not found | HALT + "File not found: {path}. Please check path and try again." |
| No date column | HALT + "Cannot identify date column. Available columns: {list}. Please specify." |
| No returns column | HALT + "Cannot identify returns column. Available columns: {list}. Please specify." |
| Insufficient data (<30 obs) | HALT + "Only {N} observations found. Need ≥30 for statistical validity." |
| Benchmark fetch fails | WARN + Continue without benchmark + "⚠️ Benchmark metrics unavailable" |
| Empty conditional group | HALT + "Condition '{cond}' matches 0 observations. Column range: [{min}, {max}]" |
| Type mismatch in condition | HALT + "Column '{col}' is {type}, cannot use operator '{op}'" |
| Contradictory conditions | HALT + "Conditions are contradictory: {explanation}" |

---

## Dependencies

### Python Libraries Required

```python
# Core statistical testing
import scipy.stats as stats
from scipy.stats import shapiro, anderson, ljungbox

# Data manipulation
import pandas as pd
import numpy as np

# Benchmark fetching
import yfinance as yf

# HAC standard errors, FDR correction, advanced time series
import statsmodels.api as sm
from statsmodels.stats.sandwich_covariance import cov_hac
from statsmodels.stats.multitest import multipletests
from statsmodels.tsa.stattools import adfuller, kpss  # on request

# Visualization (on request)
import matplotlib.pyplot as plt
import seaborn as sns
```

### Integration with load-data Skill

This skill REQUIRES the `load-data` skill for initial data discovery.

**Expected load-data capabilities:**
- `peek_file()`: Extract 5 sample rows
- Frequency detection
- Column type inference
- XML manifest generation

---

## Limitations (v2.2)

**Not Supported:**
- Mixed AND/OR conditions: `(A AND B) OR C`
- Nested conditions: `NOT (A OR B)`
- Range syntax: `feature BETWEEN 1 AND 5`
- Cross-sectional factor panel tests (IC half-life, label permutation on factor values) — tracked in fastbt #17
- Signal-column time-shift decay — tracked in fastbt #18
- Engine-driven parameter re-runs for plateau check — tracked in fastbt #19
- Jobson-Korkie test for Sharpe ratio equality (manual request only)

**Future Versions:**
- v2.3: Refactor to separate `conditional-analysis` skill
- v2.3: Support mixed logic conditions
- v3.0: Structural break tests (Chow test, change point detection, Cusum)
- v3.0: Automated parameter optimization with cross-validation

**Recently Added (v2.2):**
- ✅ Advanced Tests suite (Step 6.6) — strictly on-request: adversarial battery (A1–A6) + robust statistics (B1–B3), runnable as single tests, per-group, or full suite (user's choice)
- ✅ Sign-flip permutation, block path-shuffle, block bootstrap CIs, auto regime stress (delivers former v3.0 "regime detection" roadmap item)
- ✅ Yuen trimmed t-test, edge concentration, robust Sharpe variants

**Recently Added (v2.1):**
- ✅ Autocorrelation pre-check (Ljung-Box) — auto-switches to HAC when needed
- ✅ Effect size mandatory in all outputs (Cohen's d / rank-biserial r)
- ✅ Two-sample tests always report BOTH Cohen's d and rank-biserial r
- ✅ Scale-aware normality tests (Anderson-Darling for N>50, Shapiro-Wilk for N≤50)
- ✅ Multi-factor normality decision (skewness + kurtosis + test p-value)
- ✅ Benjamini-Hochberg FDR as default multiple testing correction

**Recently Added (v2.0):**
- ✅ Intent detection (distinguishes observation vs optimization)
- ✅ Temporal validation (train/test split, walk-forward, expanding window)
- ✅ Overfitting detection (degradation metrics)
- ✅ Smart defaults (auto-run validation when needed, ask when optional)

---

## References

See additional documentation:
- `references/DECISION_TREE.md` - Ambiguity resolution flowchart
- `references/TEST_CATALOG.md` - Detailed test descriptions
- `references/DISTRIBUTION_GUIDE.md` - Normality test interpretation
- `references/EXAMPLES.md` - Real-world scenarios
- `references/ARCHITECTURE_DECISIONS.md` - Design rationale

---

## Version History

- **v2.2.0** (2026-05-09): Advanced Tests (on request only)
  - Step 6.6: Group A adversarial robustness (sign-flip permutation, path shuffle, regime stress, sub-period consistency, block bootstrap, parameter plateau) + Group B robust statistics (trimmed mean/Yuen, edge concentration, robust Sharpe)
  - Invocation fully user-driven: single test / single group / both groups / custom subset; never auto-triggered
  - Composite scoring (PASS/CAUTION/DOUBTFUL/HIGH-RISK) for group runs
  - Unported cross-sectional factor tests tracked as fastbt issues #17, #18, #19

- **v2.1.0** (2026-04-07): Statistical validity improvements
  - Autocorrelation pre-check (Ljung-Box) with HAC fallback
  - Mandatory effect size in all output templates
  - Scale-aware normality: Anderson-Darling for N>50, Shapiro-Wilk for N≤50
  - Multi-factor normality decision (skewness, kurtosis, test)
  - Benjamini-Hochberg FDR replaces Bonferroni as default

- **v2.0.0-alpha** (2026-02-17): Temporal validation + intent detection
  - Intent detection (observation vs optimization vs deployment)
  - Walk-forward, train/test split, expanding window validation
  - Overfitting detection and degradation metrics

- **v1.0.0-alpha** (2026-02-17): Initial monolithic implementation
  - Core hypothesis tests
  - Conditional analysis (1-3 conditions, AND/OR)
  - Benchmark fetching
  - Distribution checks
  - Tweet-style output
