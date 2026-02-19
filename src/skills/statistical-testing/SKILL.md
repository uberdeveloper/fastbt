---
name: statistical-testing
description: Rigorous statistical evaluation of trading strategy returns to determine if alpha is real or a statistical artifact. Supports hypothesis testing, benchmark comparison, conditional analysis, temporal validation, and distribution checks. Use when validating backtest results, comparing strategies, testing performance claims, optimizing parameters, or analyzing performance across market conditions.
license: MIT
metadata:
  version: "2.0.0-alpha"
  capabilities: ["hypothesis_testing", "intent_detection", "temporal_validation", "benchmark_comparison", "conditional_analysis", "distribution_checks", "multiple_testing_correction", "overfitting_detection"]
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

**Action:** Always check distribution before selecting parametric vs non-parametric tests

**Tests Performed:**
1. **Shapiro-Wilk Test** (normality)
2. **Jarque-Bera Test** (normality via skewness/kurtosis)

**Decision Logic:**
```python
IF p_value > 0.05 for both tests:
    distribution = "normal"
    use_parametric = True
ELSE:
    distribution = "non-normal"
    use_parametric = False

# Always inform user
print(f"⚠️ Returns distribution: {distribution}")

# Auto-select appropriate tests
IF use_parametric:
    tests = ["t-test", "paired t-test"]
ELSE:
    tests = ["Wilcoxon signed-rank", "Mann-Whitney U"]
```

**User Override:**
```
IF user explicitly requests parametric test BUT distribution is non-normal:
  → WARN: "Returns are not normally distributed (p=X.XXX)"
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

**Multiple Testing Correction:**
```
IF running multiple tests (>1):
  → Apply Bonferroni correction
  → Adjusted alpha = 0.05 / number_of_tests
  → Inform user in output:
      "⚠️ Applied Bonferroni correction for 3 tests (adjusted α=0.017)"
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

### Step 7: Report Generation

**Default Output Format (Tweet-Style):**

```markdown
📊 Result: [One-line verdict]

Key Metrics:
- Sharpe: X.XX
- p-value: 0.XXX
- Confidence: 95%

🎯 Interpretation: [Plain English, 1-2 sentences]

⚠️ Note: [Distribution warnings, if any]
```

**Conditional Analysis Output:**

```markdown
📊 Conditional Analysis: [Metric] when [Condition]

| Condition | N | Median | Mean | Std Dev | p-value |
|-----------|---|--------|------|---------|---------|
| [Condition TRUE] | XXX | X.XX | X.XX | X.XX | - |
| [Condition FALSE] | XXX | X.XX | X.XX | X.XX | - |
| **Difference** | - | **X.XX** | **X.XX** | - | **0.XXX** |

🎯 Result: [Interpretation of statistical significance]

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
    - Confidence: 95%

    🎯 Strong evidence of real alpha (not a statistical artifact)

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

    🎯 Strong evidence of outperformance

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

# Data manipulation
import pandas as pd
import numpy as np

# Benchmark fetching
import yfinance as yf

# Advanced time series (on request)
from statsmodels.tsa.stattools import adfuller, kpss

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

## Limitations (v2.0)

**Not Supported:**
- Mixed AND/OR conditions: `(A AND B) OR C`
- Nested conditions: `NOT (A OR B)`
- Range syntax: `feature BETWEEN 1 AND 5`
- Automatic regime detection
- Monte Carlo simulation
- Bootstrap confidence intervals (manual request only)

**Future Versions:**
- v2.1: Refactor to separate `conditional-analysis` skill
- v2.1: Support mixed logic conditions
- v3.0: Automatic regime detection (Chow test, change point detection)
- v3.0: Performance drift monitoring
- v3.0: Automated parameter optimization with cross-validation

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

- **v1.0.0-alpha** (2026-02-17): Initial monolithic implementation
  - Core hypothesis tests
  - Conditional analysis (1-3 conditions, AND/OR)
  - Benchmark fetching
  - Distribution checks
  - Tweet-style output
