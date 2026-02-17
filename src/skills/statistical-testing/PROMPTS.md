# AI & Agent Prompt Examples

This guide provides examples of how users can prompt an AI agent to use the **Statistical Testing** skill effectively. These prompts are designed to trigger the correct hypothesis tests, conditional analysis, and benchmark comparisons.

---

## 1. Simple Alpha Testing

### Example 1.1: Basic Performance Test

**User Prompt:**
```
"Is my momentum strategy's alpha real? File: returns.csv"
```

**Agent Reasoning:**
- Hypothesis type: Performance test (positive returns)
- Use load-data to peek at file
- Check distribution (normality)
- Run appropriate test (t-test or Wilcoxon)
- Output tweet-style summary

**Expected Output:**
```markdown
📊 Result: Your momentum strategy has statistically significant positive returns

Key Metrics:
- Median Return: 0.12% per day
- p-value: 0.003
- Confidence: 95%

🎯 Strong evidence of real alpha (not a statistical artifact)

⚠️ Note: Returns not normally distributed (used non-parametric test)
```

---

### Example 1.2: User Specifies Test

**User Prompt:**
```
"Run a Wilcoxon signed-rank test on my strategy returns. File: backtest_results.csv, returns column: daily_pnl"
```

**Agent Reasoning:**
- User explicitly specified test → skip auto-selection
- User specified returns column → use it directly
- Validate test is appropriate
- Run test and report

---

### Example 1.3: Ambiguous Case (Agent Should Ask)

**User Prompt:**
```
"Test my strategy. File: data.csv"
```

**Agent Response:**
```
I need clarification to proceed:

1. What hypothesis should I test?
   - Does the strategy have positive returns? (performance test)
   - Does it beat a benchmark? (outperformance test)
   - Compare to another strategy? (comparison test)
   - Something else?

2. Which column contains the returns to test?
   Available columns: date, strategy_a, strategy_b, spy_returns, vix

Please clarify so I can run the appropriate test.
```

---

## 2. Benchmark Comparison

### Example 2.1: Benchmark in Data

**User Prompt:**
```
"Does my strategy beat SPY? File: comparison.csv"
```

**Agent Reasoning:**
- Hypothesis: Outperformance test
- Check if SPY data exists in file (spy_returns column)
- If found → use it directly
- Run paired test
- Calculate excess Sharpe ratio

**Expected Output:**
```markdown
📊 Result: Your strategy significantly outperforms SPY

Key Metrics:
- Strategy Sharpe: 1.45
- SPY Sharpe: 0.89
- Excess Sharpe: +0.56
- p-value: 0.012

🎯 Strong evidence of outperformance
```

---

### Example 2.2: Fetch Benchmark from yfinance

**User Prompt:**
```
"Test if my India equity strategy beats the market. File: strategy.csv"
```

**Agent Reasoning:**
- Hypothesis: Outperformance test
- No benchmark in data
- Infer asset class: "India equity" → NIFTY50
- Ask permission to fetch

**Agent Response:**
```
I detected you're testing an India equity strategy.

May I fetch NIFTY50 data from yfinance (2020-01-01 to 2025-12-31) for benchmark comparison?

Alternatives:
- Provide your own benchmark data
- Run absolute performance test (no benchmark)
```

---

### Example 2.3: Benchmark Fetch Fails

**User Prompt:**
```
"Compare my crypto strategy to Bitcoin. File: crypto_returns.csv"
```

**Agent Execution:**
```
1. Attempt to fetch BTC-USD from yfinance
2. IF fetch fails:
   → "⚠️ Could not fetch Bitcoin data from yfinance"
   → "Please provide benchmark data or I'll continue with absolute performance test"
3. IF user provides nothing:
   → Continue with performance test only
   → Report: "⚠️ Benchmark comparison unavailable"
```

---

## 3. Conditional Analysis

### Example 3.1: Single Condition

**User Prompt:**
```
"Does my strategy have lower drawdown when VIX > 20? File: data.csv"
```

**Agent Reasoning:**
- Hypothesis: Conditional comparison
- Metric: max_drawdown
- Condition: VIX > 20
- Validate VIX column exists
- Segment data into two groups
- Compare drawdown between groups
- Test significance

**Expected Output:**
```markdown
📊 Conditional Analysis: Drawdown when VIX > 20

| Condition | N | Median DD | Mean DD | p-value |
|-----------|---|-----------|---------|---------|
| VIX > 20  | 234 | -15.2% | -16.8% | - |
| VIX ≤ 20  | 1016 | -8.3% | -9.1% | - |
| **Difference** | - | **-6.9%** | **-7.7%** | **0.002** |

🎯 Result: Drawdown is significantly WORSE when VIX > 20

Test: Mann-Whitney U (non-parametric)
Confidence: 95%
```

---

### Example 3.2: Multiple AND Conditions

**User Prompt:**
```
"Is Sharpe ratio better when VIX > 20 AND market_cap > 1000 AND regime == 'bull'? File: features.csv"
```

**Agent Reasoning:**
- Hypothesis: Conditional comparison
- Metric: sharpe_ratio
- Conditions: 3 conditions with AND logic
- Validate all columns exist
- Segment data: (all 3 true) vs (not all true)
- Calculate Sharpe for each group
- Test significance

---

### Example 3.3: Multiple OR Conditions

**User Prompt:**
```
"Does my strategy perform better during high volatility OR bear markets? File: regime_data.csv"
```

**Agent Reasoning:**
- Conditions: high_volatility == True OR market_regime == 'bear'
- Segment: (either condition true) vs (both false)
- Compare performance metrics

---

### Example 3.4: Conditional with Missing Column (Agent Should Halt)

**User Prompt:**
```
"Test performance when RSI > 70. File: simple_returns.csv"
```

**Agent Execution:**
```
1. Load data
2. Check for RSI column
3. NOT FOUND

Agent Response:
"⚠️ Column 'RSI' not found in data.

Available columns: date, returns, volume, close_price

Please either:
1. Specify a different condition using available columns
2. Provide a file that includes RSI data
"
```

---

## 4. Strategy Comparison

### Example 4.1: Compare Two Strategies

**User Prompt:**
```
"Is momentum strategy better than mean reversion? File: comparison.csv, columns: momentum_returns, mean_reversion_returns"
```

**Agent Reasoning:**
- Hypothesis: Comparison test
- Two independent return series
- Check distribution
- Run independent t-test or Mann-Whitney U
- Compare Sharpe ratios

**Expected Output:**
```markdown
📊 Strategy Comparison: Momentum vs Mean Reversion

| Strategy | Sharpe | Mean Return | Std Dev | p-value |
|----------|--------|-------------|---------|---------|
| Momentum | 1.23 | 0.08% | 1.2% | - |
| Mean Reversion | 0.87 | 0.05% | 1.5% | - |
| **Difference** | **+0.36** | **+0.03%** | - | **0.045** |

🎯 Result: Momentum strategy significantly outperforms mean reversion

Test: Mann-Whitney U (non-parametric)
Confidence: 95%
```

---

## 5. Distribution Checks

### Example 5.1: Check Normality

**User Prompt:**
```
"Are my strategy returns normally distributed? File: returns.csv"
```

**Agent Reasoning:**
- Run Shapiro-Wilk test
- Run Jarque-Bera test
- Generate QQ plot (if visualization requested)
- Report results

**Expected Output:**
```markdown
📊 Distribution Analysis

Tests:
- Shapiro-Wilk: p=0.023 (reject normality)
- Jarque-Bera: p=0.012 (reject normality)

🎯 Result: Returns are NOT normally distributed

Implications:
- Use non-parametric tests (Wilcoxon, Mann-Whitney U)
- Consider log-normal or other distributions
- Outliers may be present

Recommendation: Use robust statistical methods for hypothesis testing.
```

---

## 6. Advanced Use Cases

### Example 6.1: ARIMA Parameter Comparison

**User Prompt:**
```
"Do ARIMA(3,1,2) parameters produce better returns than ARIMA(2,1,1)? File: arima_comparison.csv, columns: arima_312_returns, arima_211_returns"
```

**Agent Reasoning:**
- This is a comparison test (not fitting ARIMA)
- User has already generated returns using different parameters
- Compare the two return series
- Test: Paired comparison (same time periods)

---

### Example 6.2: Frequency Mismatch Handling

**User Prompt:**
```
"Test my weekly returns strategy. File: daily_data.csv"
```

**Agent Execution:**
```
1. Load data → detect frequency = daily
2. User said "weekly" but data is daily

Agent Response:
"⚠️ Frequency mismatch detected

You specified: weekly returns
Data frequency: daily (detected from timestamps)

Options:
1. I can resample daily data to weekly
2. Proceed with daily data (ignore 'weekly' label)
3. You provide weekly data

Which would you prefer?"
```

---

### Example 6.3: Multiple Returns Columns

**User Prompt:**
```
"Test my strategies for alpha. File: multi_strategy.csv"
```

**Agent Execution:**
```
1. Load data
2. Detect columns: date, strategy_a, strategy_b, strategy_c, spy_benchmark

Agent Response:
"I found multiple strategy columns:
- strategy_a
- strategy_b
- strategy_c

Which strategy should I test? Or should I test all and compare?"
```

---

## 7. Error Scenarios (Agent Should Handle Gracefully)

### Example 7.1: Insufficient Data

**User Prompt:**
```
"Test my strategy. File: small_sample.csv"
```

**Agent Execution:**
```
1. Load data → only 15 observations

Agent Response:
"⚠️ Insufficient data for statistical testing

Found: 15 observations
Required: ≥30 observations for statistical validity

Please provide more data or acknowledge that results may not be reliable."
```

---

### Example 7.2: Empty Conditional Group

**User Prompt:**
```
"Test performance when VIX > 100. File: data.csv"
```

**Agent Execution:**
```
1. Parse condition: VIX > 100
2. Filter data → 0 observations match

Agent Response:
"⚠️ Condition 'VIX > 100' matches 0 observations

VIX column range: [10.2, 45.8]

Please adjust your condition threshold."
```

---

### Example 7.3: Contradictory Conditions

**User Prompt:**
```
"Test when feature1 > 10 AND feature1 < 5"
```

**Agent Response:**
```
"⚠️ Contradictory conditions detected

Condition 1: feature1 > 10
Condition 2: feature1 < 5

These conditions cannot both be true simultaneously.

Please revise your conditions."
```

---

## 8. Requesting Detailed Output

### Example 8.1: Ask for More Details

**User Prompt (Initial):**
```
"Test my strategy alpha. File: returns.csv"
```

**Agent Output (Tweet-style):**
```markdown
📊 Result: Significant positive alpha detected

Key Metrics:
- Sharpe: 1.23
- p-value: 0.003

🎯 Strong evidence of real alpha
```

**User Follow-up:**
```
"Explain more"
```

**Agent Output (Detailed):**
```markdown
# Detailed Statistical Analysis

## Hypothesis Test
- Null Hypothesis: Strategy returns = 0
- Alternative: Strategy returns > 0
- Test: Wilcoxon signed-rank (non-parametric)

## Results
- Test Statistic: 45678
- p-value: 0.003
- Significance Level: 0.05
- Decision: Reject null hypothesis

## Distribution Analysis
- Shapiro-Wilk: p=0.023 (non-normal)
- Skewness: -0.45
- Kurtosis: 3.2

## Performance Metrics
- Mean Return: 0.11% per day
- Median Return: 0.12% per day
- Std Dev: 1.5%
- Sharpe Ratio: 1.23 (annualized)
- Max Drawdown: -18.3%
- Win Rate: 54.2%

## Interpretation
The strategy demonstrates statistically significant positive returns with 95% confidence. The non-normal distribution (negative skew) suggests occasional large losses, but overall performance is robust.
```

---

### Example 8.2: Request Visualization

**User Prompt:**
```
"Test my strategy and show me distribution plots. File: returns.csv"
```

**Agent Execution:**
```
1. Run statistical tests
2. Generate plots:
   - Distribution histogram
   - QQ plot
   - Returns over time
3. Save plots as PNG files
4. Include in markdown report
```

---

## 9. Best Practices for Users

### Clear Prompts Get Better Results

**Good Prompt:**
```
"Test if my momentum strategy beats NIFTY50 with 99% confidence.
File: india_equity.csv,
returns column: strategy_returns,
benchmark column: nifty_returns"
```

**Why it's good:**
- Clear hypothesis (outperformance)
- Specified confidence level
- Explicit file and column names
- No ambiguity

---

**Vague Prompt:**
```
"Check my data"
```

**Why it's bad:**
- No hypothesis specified
- No file specified
- Agent must ask multiple clarifying questions

---

### When to Specify Tests vs Let Agent Choose

**Let Agent Choose (Recommended):**
```
"Does my strategy have real alpha? File: returns.csv"
```
→ Agent will check distribution and select appropriate test

**Specify Test (Advanced Users):**
```
"Run Mann-Whitney U test comparing my strategy to SPY. File: data.csv"
```
→ Use when you know exactly which test is appropriate

---

## 10. Integration with Other Skills

### Example 10.1: Load Data First, Then Test

**User Workflow:**
```
User: "Show me the first few rows of my data. File: strategy.csv"
→ Uses load-data skill

Agent: [Shows 5 rows with columns: date, returns, vix, regime]

User: "Now test if returns are higher when regime == 'bull'"
→ Uses statistical-testing skill with conditional analysis
```

---

### Example 10.2: Test After Simulation

**User Workflow:**
```
User: "Simulate 1000 price paths with GBM"
→ Uses simulation skill

Agent: [Generates simulated returns]

User: "Test if the simulated returns are normally distributed"
→ Uses statistical-testing skill for distribution check
```

---

## Summary

The Statistical Testing skill is designed to:
1. **Minimize ambiguity** - Agent asks clarifying questions when needed
2. **Provide smart defaults** - LLM infers asset class, benchmark, test type
3. **Gracefully handle failures** - Continue analysis when possible, halt when critical
4. **Output concise summaries** - Tweet-style by default, detailed on request
5. **Support complex analysis** - Conditional comparisons with multiple filters

For best results, provide clear hypotheses and specify file/column names when possible.
