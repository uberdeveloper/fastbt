# Statistical Testing Skill

**Version:** 1.0.0-alpha
**Status:** Alpha Testing (Monolithic Implementation)
**License:** MIT

---

## Overview

A comprehensive LLM skill for rigorous statistical evaluation of trading strategy returns. Designed to answer the critical question: **"Is this alpha real or just a statistical artifact?"**

### Key Features

- ✅ **Hypothesis Testing**: Performance, outperformance, comparison tests
- ✅ **Distribution Checks**: Automatic normality testing with appropriate test selection
- ✅ **Benchmark Comparison**: Fetch benchmarks from yfinance with smart defaults
- ✅ **Conditional Analysis**: Compare metrics across segments (up to 3 conditions with AND/OR)
- ✅ **Tweet-Style Output**: Concise summaries with detailed reports on request
- ✅ **Graceful Error Handling**: Continue analysis when possible, halt when critical

---

## Quick Start

### For LLM Agents

1. Read `SKILL.md` for complete instructions
2. Use `load-data` skill first for data discovery
3. Parse user hypothesis and select appropriate tests
4. Generate tweet-style summary + save markdown report

### For Users

See `PROMPTS.md` for example prompts:

```
"Is my momentum strategy's alpha real? File: returns.csv"

"Test if my India equity strategy beats the market. File: strategy.csv"

"Does my strategy have lower drawdown when VIX > 20? File: data.csv"
```

---

## Architecture

### Current (v1.0 - Monolithic)

```
statistical-testing/
├── SKILL.md                    # Main LLM instructions
├── PROMPTS.md                  # User examples
├── README.md                   # This file
├── scripts/
│   ├── test_engine.py         # Core scipy tests
│   ├── conditional_filter.py  # Conditional analysis
│   ├── benchmark_fetcher.py   # yfinance integration
│   └── reporter.py            # Markdown output
└── references/
    └── ARCHITECTURE_DECISIONS.md  # Design rationale
```

### Future (v2.0 - Modular)

Will be refactored into:
- `statistical-testing` (core hypothesis tests)
- `conditional-analysis` (segmented comparison)

See `references/ARCHITECTURE_DECISIONS.md` for details.

---

## Dependencies

### Python Libraries

```python
# Core (required)
scipy
pandas
numpy

# Benchmark fetching (optional)
yfinance

# Advanced time series (on request)
statsmodels

# Visualization (on request)
matplotlib
seaborn
```

### Skills

- **load-data**: Required for initial data discovery

---

## Supported Tests

### Hypothesis Types

| Type | Example | Tests Used |
|------|---------|------------|
| Performance | "Does strategy have positive returns?" | t-test, Wilcoxon |
| Outperformance | "Does strategy beat benchmark?" | Paired t-test, Wilcoxon |
| Comparison | "Is strategy A better than B?" | Independent t-test, Mann-Whitney U |
| Conditional | "Does metric differ when condition?" | Mann-Whitney U, t-test |

### Distribution Checks

- Shapiro-Wilk test
- Jarque-Bera test
- Automatic parametric vs non-parametric selection

### Performance Metrics

- Sharpe Ratio (annualized)
- Maximum Drawdown
- Win Rate
- Mean/Median Returns
- Skewness & Kurtosis

---

## Conditional Analysis

Supports up to **3 conditions** with **AND/OR** logic:

### Examples

```python
# Single condition
"when VIX > 20"

# Multiple AND
"when VIX > 20 AND market_cap > 1000 AND regime == 'bull'"

# Multiple OR
"when VIX > 20 OR regime == 'bear'"
```

### Supported Operators

- Numeric: `>`, `<`, `>=`, `<=`, `==`, `!=`
- String: `==`, `!=`
- Boolean: `==`, `!=`

### Limitations (v1.0)

- ❌ Mixed AND/OR: `(A AND B) OR C`
- ❌ Nested conditions: `NOT (A OR B)`
- ❌ Range syntax: `BETWEEN 1 AND 5`

---

## Benchmark Fetching

### Smart Defaults (LLM-Inferred)

```
User mentions → LLM infers → Suggests
"India equity" → NIFTY50
"US equity" → SPY
"crypto" → Bitcoin
"forex" → DXY
```

### Graceful Degradation

```
IF yfinance fetch fails:
  1. Inform user
  2. Ask for benchmark data
  3. IF no response → continue without benchmark
  4. Skip benchmark-dependent metrics
  5. Report: "⚠️ Benchmark metrics unavailable"
```

---

## Output Format

### Tweet-Style (Default)

```markdown
📊 Result: Your strategy has significant positive returns

Key Metrics:
- Sharpe: 1.23
- p-value: 0.003
- Confidence: 95%

🎯 Strong evidence of real alpha

⚠️ Note: Returns not normally distributed
```

### Detailed (On Request)

- Full test statistics
- Distribution analysis
- Performance metrics table
- Warnings and assumptions
- Saved to markdown file

---

## Error Handling

### Ambiguity Resolution

**Rule:** HALT if unclear, NEVER guess

```
IF ambiguous:
  → Present options to user
  → Ask for clarification
  → Wait for response
```

### Common Errors

| Error | Response |
|-------|----------|
| File not found | HALT + ask for correct path |
| No date/returns column | HALT + list available columns |
| Insufficient data (<30 obs) | HALT + inform user |
| Benchmark fetch fails | WARN + continue without |
| Empty conditional group | HALT + show column range |

---

## Development Status

### v1.0 (Current - Alpha)

**Implemented:**
- ✅ Core hypothesis tests (scipy)
- ✅ Distribution checks
- ✅ Benchmark fetching (yfinance)
- ✅ Conditional analysis (1-3 conditions, AND/OR)
- ✅ Tweet-style output
- ✅ Markdown reports

**In Progress:**
- 🔄 User testing and feedback
- 🔄 Edge case handling
- 🔄 Performance optimization

### v2.0 (Planned)

**Refactoring:**
- Separate `conditional-analysis` skill
- Shared utilities module
- Enhanced error messages

**New Features:**
- Mixed AND/OR conditions
- Time-based filtering
- Bootstrap confidence intervals
- Walk-forward validation

---

## Contributing

This skill is in **alpha testing** with select users. Feedback is welcome!

### Reporting Issues

Please include:
1. User prompt
2. Data structure (columns, types)
3. Expected behavior
4. Actual behavior
5. Error messages (if any)

### Design Philosophy

See `references/ARCHITECTURE_DECISIONS.md` for:
- Design rationale
- Trade-offs considered
- Future roadmap

---

## Examples

### Example 1: Simple Alpha Test

**Input:**
```
"Is my momentum strategy's alpha real? File: returns.csv"
```

**Output:**
```markdown
📊 Result: Your strategy has statistically significant positive returns

Key Metrics:
- Median Return: 0.12% per day
- p-value: 0.003
- Confidence: 95%

🎯 Strong evidence of real alpha (not a statistical artifact)

⚠️ Note: Returns not normally distributed (used non-parametric test)
```

### Example 2: Benchmark Comparison

**Input:**
```
"Test if my India equity strategy beats the market. File: strategy.csv"
```

**Workflow:**
1. Detect asset class: "India equity"
2. Suggest benchmark: NIFTY50
3. Ask permission to fetch
4. Run paired test
5. Report outperformance

### Example 3: Conditional Analysis

**Input:**
```
"Does my strategy have lower drawdown when VIX > 20? File: data.csv"
```

**Output:**
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

## License

MIT License - See LICENSE file for details

---

## Contact

For questions or feedback, please refer to the main fastbt repository.

---

**Last Updated:** 2026-02-17
**Maintainer:** fastbt team
