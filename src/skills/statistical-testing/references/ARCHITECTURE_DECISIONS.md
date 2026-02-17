# Statistical Testing Skill - Architecture Decisions

**Date:** 2026-02-17
**Status:** Alpha Testing (v1.0 - Monolithic)
**Future Plan:** Refactor to separate skills (v2.0)

---

## Executive Summary

This document captures the architectural decisions made during the design of the statistical testing skill for quantitative strategy evaluation.

**Current Implementation (v1.0):** Monolithic skill with conditional analysis built-in
**Future Architecture (v2.0):** Separate into `statistical-testing` + `conditional-analysis` skills

---

## Design Principles

```xml
<core_principles>
  <principle id="1">No Ambiguity - HALT if unclear, never guess</principle>
  <principle id="2">Speed First - scipy for classical tests, statsforecast/statsmodels on request</principle>
  <principle id="3">Graceful Degradation - Continue with warnings if non-critical failures</principle>
  <principle id="4">Tweet-Style Output - Concise by default, detailed on request</principle>
  <principle id="5">LLM-Powered Inference - Use LLM for smart defaults and parsing</principle>
</core_principles>
```

---

## Key Decisions

### 1. Data Discovery Strategy

**Decision:** Use `load-data` skill for initial file inspection

**Details:**
- `load-data` peeks at 5 rows (fixed, not configurable)
- Sends sample + column metadata to LLM context
- Infers date column, returns columns, features, benchmark
- NO full-file statistics (avoid memory overhead)
- Frequency detection handled by `load-data`

**Frequency Mismatch Handling:**
```
IF user says "weekly" BUT data is daily:
  1. HALT and inform user of mismatch
  2. Show detected frequency vs user-specified
  3. Ask user to confirm or correct
  4. IF user insists on their frequency → use it (user override)
```

---

### 2. Benchmark Resolution Strategy

**Decision:** Multi-tier fallback with graceful degradation

**Priority Order:**
1. Benchmark column in data file
2. User-specified benchmark
3. LLM-inferred benchmark (ask permission to fetch from yfinance)
4. Graceful degradation (continue without benchmark)

**Asset Class Inference:**
- Rely on LLM to infer from context (no hardcoded mappings)
- Examples: "India equity" → NIFTY50, "US equity" → SPY, "crypto" → BTC

**Fetch Failure Handling:**
```
IF yfinance fetch fails:
  1. Inform user: "Could not fetch [BENCHMARK]"
  2. Ask: "Provide benchmark data or continue without?"
  3. IF no user response → continue analysis
  4. Skip benchmark-dependent metrics
  5. Report: "⚠️ Benchmark metrics not available"
```

---

### 3. Statistical Testing Approach

**Decision:** Classical hypothesis tests with automatic distribution checks

**Test Selection:**
- Start with scipy (classical tests)
- statsforecast/statsmodels only on explicit user request
- Auto-select parametric vs non-parametric based on distribution

**Distribution Checks:**
- Always run: Shapiro-Wilk, Jarque-Bera
- Inform user if not normal/lognormal
- Proceed with appropriate tests (non-parametric if needed)

**Multiple Testing Correction:**
- Auto-apply Bonferroni correction if >1 test
- Inform user in output

---

### 4. Conditional Analysis Design (v1.0)

**Decision:** Support 1-3 conditions with AND/OR logic (monolithic implementation)

**Supported Complexity:**
```xml
<conditional_support>
  <level_1>Single condition: "when VIX > 20"</level_1>
  <level_2>Multiple AND: "when VIX > 20 AND market_cap > 1000"</level_2>
  <level_3>Multiple OR: "when VIX > 20 OR regime == 'bear'"</level_3>
  <limit>Max 3 conditions</limit>
  <restriction>All AND or all OR (no mixing in v1.0)</restriction>
</conditional_support>
```

**Parsing Strategy:**
- LLM generates structured XML from natural language
- Validation layer checks column existence, types, operators
- Fallback: Ask user to rephrase if parsing fails

**Validation Rules:**
1. Column existence check
2. Data type compatibility (numeric/string/boolean)
3. Sufficient data (≥30 observations per group)
4. Max 3 conditions enforced
5. Consistent logic (all AND or all OR)

**Edge Cases:**
- Empty group → HALT + inform
- Imbalanced groups → WARN + proceed with non-parametric
- Contradictory conditions → HALT + explain
- Missing values → WARN + ask to drop or impute

---

### 5. Output Format

**Decision:** Markdown reports with tweet-style summaries

**Default Output:**
```markdown
📊 Result: [One-line verdict]

Key Metrics:
- Sharpe: X.XX
- p-value: 0.XXX
- Confidence: 95%

🎯 Interpretation: [Plain English, 1-2 sentences]

⚠️ Note: [Distribution warnings, if any]
```

**Persistence:**
- Save to markdown file automatically
- Filename: `{test_type}_{timestamp}.md`

**Visualizations:**
- Generate plots ONLY on request
- Types: Distribution, QQ plots, comparison charts

---

### 6. Communication Format (Inter-Skill)

**Decision:** XML manifests for better LLM parsing

**Example Manifest (load-data → statistical-testing):**
```xml
<data_manifest>
  <source>
    <file_path>strategy_returns.csv</file_path>
    <row_count>1250</row_count>
  </source>

  <temporal_info>
    <date_column>date</date_column>
    <date_range>
      <start>2020-01-01</start>
      <end>2025-12-31</end>
    </date_range>
    <frequency>daily</frequency>
  </temporal_info>

  <columns>
    <column name="date" type="datetime64" role="index"/>
    <column name="strategy_returns" type="float64" role="returns_candidate"/>
    <column name="feature1" type="float64" role="feature"/>
    <column name="spy_returns" type="float64" role="benchmark_candidate"/>
  </columns>

  <sample_data format="markdown">
    [5 rows in table format]
  </sample_data>

  <inferences>
    <primary_returns>strategy_returns</primary_returns>
    <benchmark_available>true</benchmark_available>
    <benchmark_column>spy_returns</benchmark_column>
  </inferences>
</data_manifest>
```

---

### 7. Multiple Returns Columns

**Decision:** Ask user, default to first column for auto-test

**Logic:**
```
IF multiple returns columns detected:
  1. List all candidates
  2. Ask user which to test
  3. IF no response → use first column
  4. Inform user which column was used
```

---

## Future Architecture (v2.0)

### Planned Refactoring: Separate Skills

**Rationale for Separation:**
1. **Clear Responsibility:**
   - `statistical-testing`: Single dataset hypothesis tests
   - `conditional-analysis`: Multi-segment comparison

2. **Reusability:**
   - `conditional-analysis` can be used for portfolio analysis, walk-forward, etc.

3. **Maintainability:**
   - Each skill stays focused (~150-200 lines)
   - Independent evolution

4. **Composition:**
   ```
   conditional-analysis:
     1. Parse conditions
     2. Segment data
     3. FOR EACH segment: invoke statistical-testing
     4. Compare results
   ```

**Migration Path:**
```
v1.0 (Current): Monolithic skill
  ↓
v1.5 (Transition): Extract conditional logic to separate module
  ↓
v2.0 (Refactor): Two separate skills with clear interfaces
```

**Dependency Graph:**
```
load-data
    ↓
statistical-testing (core tests)
    ↓
conditional-analysis (segments + comparison)
```

---

## Design Critiques Considered

### Why Not Start with Separate Skills?

**Arguments For Separation:**
- Cleaner architecture
- Better separation of concerns
- Easier to maintain long-term

**Arguments For Monolithic (Chosen for v1.0):**
- ✅ Faster to implement for alpha testing
- ✅ Easier to iterate based on user feedback
- ✅ Less skill coordination complexity initially
- ✅ Can refactor later without breaking user workflows (alpha users)

**Decision:** Start monolithic, refactor when stable.

---

## Conditional Analysis: Complexity Decisions

### What We Support (v1.0)

| Feature | Supported | Notes |
|---------|-----------|-------|
| Single condition | ✅ Yes | `feature1 > 1` |
| Multiple AND (≤3) | ✅ Yes | `A > 1 AND B < 5 AND C == 2` |
| Multiple OR (≤3) | ✅ Yes | `A > 1 OR B < 5 OR C == 2` |
| Mixed AND/OR | ❌ No | Defer to v2.0 |
| Nested conditions | ❌ No | Defer to v2.0 |
| Range/between | ❌ No | Can rewrite as compound |
| Time-based filters | ❌ No | Defer to v2.0 |
| String comparisons | ✅ Yes | `regime == 'bull'` |
| Boolean comparisons | ✅ Yes | `high_vol == True` |
| Negation (NOT) | ❌ No | Use opposite operators |

### Parsing Approach: Hybrid

**Step 1:** LLM extracts intent → structured XML
**Step 2:** Validation layer checks XML
**Step 3:** Generate pandas query string
**Fallback:** Ask user to rephrase in simple format

---

## Test Catalog

### Hypothesis Types Supported (v1.0)

1. **Performance Test:** "Does strategy have positive returns?"
   - Tests: One-sample t-test, Wilcoxon signed-rank

2. **Outperformance Test:** "Does strategy beat benchmark?"
   - Tests: Paired t-test, Wilcoxon signed-rank

3. **Comparison Test:** "Is strategy A better than strategy B?"
   - Tests: Independent t-test, Mann-Whitney U

4. **Conditional Test:** "Does metric differ when condition is true?"
   - Tests: Mann-Whitney U, t-test (based on distribution)

5. **Stationarity Test:** "Are returns stationary?"
   - Tests: ADF, KPSS (statsmodels, on request)

---

## Ambiguity Resolution Rules

### Decision Tree Location

**Decision:** Rules live in `statistical-testing/references/DECISION_TREE.md`

**Key Rules:**

| Ambiguity | Resolution |
|-----------|------------|
| No date column specified | Check common names → Ask LLM → HALT if unclear |
| Multiple returns columns | User specifies → Default to first → Inform user |
| Benchmark needed but missing | Check data → Auto-detect → Ask permission → Fetch → Graceful fail |
| Distribution not normal | Inform user + use non-parametric tests |
| Multiple testing (>5 tests) | Auto-apply Bonferroni + inform user |
| Conditional syntax unclear | LLM parse → Validate → HALT if ambiguous |
| Frequency mismatch | HALT → Show mismatch → Ask user → User override allowed |

---

## Implementation Priorities

### v1.0 (Alpha - Monolithic)

**P0 (Must Have):**
- [ ] Core hypothesis tests (scipy)
- [ ] Distribution checks (normality)
- [ ] Benchmark resolution (yfinance)
- [ ] Single condition support
- [ ] Multiple AND conditions (≤3)
- [ ] Tweet-style output
- [ ] Markdown report generation
- [ ] Integration with load-data skill

**P1 (Should Have):**
- [ ] Multiple OR conditions (≤3)
- [ ] String/boolean comparisons
- [ ] Multiple testing correction
- [ ] Sharpe ratio comparison
- [ ] Drawdown analysis

**P2 (Nice to Have):**
- [ ] Bootstrap confidence intervals
- [ ] Visualization on request
- [ ] ARIMA parameter comparison (statsforecast)

### v2.0 (Separate Skills)

**Refactoring Tasks:**
- [ ] Extract conditional logic to separate skill
- [ ] Define skill interface contracts
- [ ] Update SKILL.md for both skills
- [ ] Create skill coordination examples
- [ ] Migration guide for users

---

## Open Questions (To Be Resolved)

1. **Condition syntax enforcement:** Specific format or free-form LLM parsing?
2. **Condition preview:** Show data split before running tests?
3. **Frequency mismatch:** Offer to resample data automatically?
4. **Shared utilities:** Where to put common reporting/plotting code?

---

## References

- Agent Skills Specification: https://agentskills.io/specification
- Existing `load-data` skill: `/home/pi/fastbt/src/skills/load-data/SKILL.md`
- scipy.stats documentation: https://docs.scipy.org/doc/scipy/reference/stats.html
- statsmodels time series: https://www.statsmodels.org/stable/tsa.html

---

## Changelog

- **2026-02-17:** Initial architecture document created
- **Future:** Track major design changes here
