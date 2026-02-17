"""
Conditional Filter Module

Parses and applies conditional filters for segmented analysis.
Supports up to 3 conditions with AND/OR logic.
"""

import pandas as pd
import numpy as np
from typing import List, Dict, Literal, Optional
from dataclasses import dataclass
import re


@dataclass
class Condition:
    """Single condition specification"""

    column: str
    operator: Literal["==", "!=", ">", "<", ">=", "<="]
    value: any
    column_type: Optional[str] = None


@dataclass
class ConditionalFilter:
    """Complete conditional filter specification"""

    conditions: List[Condition]
    logic: Literal["AND", "OR"]
    metric: Optional[str] = None
    hypothesis: Optional[str] = None


class ConditionParser:
    """Parse natural language conditions into structured format"""

    OPERATORS = ["==", "!=", ">=", "<=", ">", "<"]
    LOGIC_KEYWORDS = ["AND", "OR"]

    @staticmethod
    def parse_simple_condition(condition_str: str) -> Condition:
        """
        Parse a simple condition string

        Args:
            condition_str: e.g., "VIX > 20" or "regime == 'bull'"

        Returns:
            Condition object
        """
        # Pattern for: column operator value
        # Handles: numeric, string (quoted), boolean
        pattern = (
            r"(\w+)\s*(==|!=|>=|<=|>|<)\s*([0-9.]+|True|False|\'[^\']+\'|\"[^\"]+\")"
        )

        match = re.match(pattern, condition_str.strip())
        if not match:
            raise ValueError(f"Cannot parse condition: {condition_str}")

        column = match.group(1)
        operator = match.group(2)
        value_str = match.group(3)

        # Parse value based on type
        if value_str in ["True", "False"]:
            value = value_str == "True"
            column_type = "boolean"
        elif value_str.startswith(("'", '"')):
            value = value_str.strip("'\"")
            column_type = "string"
        else:
            try:
                value = float(value_str)
                column_type = "numeric"
            except ValueError:
                raise ValueError(f"Cannot parse value: {value_str}")

        return Condition(
            column=column, operator=operator, value=value, column_type=column_type
        )

    @staticmethod
    def parse_multiple_conditions(
        condition_str: str, max_conditions: int = 3
    ) -> ConditionalFilter:
        """
        Parse multiple conditions with AND/OR logic

        Args:
            condition_str: e.g., "VIX > 20 AND market_cap > 1000"
            max_conditions: Maximum number of conditions allowed

        Returns:
            ConditionalFilter object
        """
        # Split by AND/OR
        parts = re.split(r"\s+(AND|OR)\s+", condition_str.strip())

        # Extract conditions and logic operators
        conditions = []
        logic_operators = []

        for i, part in enumerate(parts):
            if part in ConditionParser.LOGIC_KEYWORDS:
                logic_operators.append(part)
            else:
                conditions.append(ConditionParser.parse_simple_condition(part))

        # Validate
        if len(conditions) > max_conditions:
            raise ValueError(
                f"Too many conditions ({len(conditions)}). "
                f"Maximum {max_conditions} allowed."
            )

        if len(conditions) == 0:
            raise ValueError("No valid conditions found")

        # Check logic consistency (all AND or all OR)
        if len(set(logic_operators)) > 1:
            raise ValueError(
                "Mixed AND/OR logic not supported. " "Use either all AND or all OR."
            )

        logic = logic_operators[0] if logic_operators else "AND"

        return ConditionalFilter(conditions=conditions, logic=logic)


class DataSegmenter:
    """Segment data based on conditional filters"""

    @staticmethod
    def validate_conditions(
        df: pd.DataFrame, conditional_filter: ConditionalFilter
    ) -> Dict[str, any]:
        """
        Validate conditions against dataframe

        Args:
            df: DataFrame to validate against
            conditional_filter: ConditionalFilter object

        Returns:
            Dictionary with validation results
        """
        errors = []
        warnings = []

        for cond in conditional_filter.conditions:
            # Check column exists
            if cond.column not in df.columns:
                errors.append(
                    f"Column '{cond.column}' not found. "
                    f"Available: {list(df.columns)}"
                )
                continue

            # Check type compatibility
            col_dtype = df[cond.column].dtype

            if cond.column_type == "numeric":
                if not pd.api.types.is_numeric_dtype(col_dtype):
                    errors.append(
                        f"Column '{cond.column}' is {col_dtype}, "
                        f"cannot use numeric operator '{cond.operator}'"
                    )
            elif cond.column_type == "string":
                if (
                    not pd.api.types.is_string_dtype(col_dtype)
                    and col_dtype != "object"
                ):
                    warnings.append(
                        f"Column '{cond.column}' may not be string type ({col_dtype})"
                    )

            # Check for missing values
            missing_pct = df[cond.column].isna().sum() / len(df) * 100
            if missing_pct > 0:
                warnings.append(
                    f"Column '{cond.column}' has {missing_pct:.1f}% missing values"
                )

        return {"valid": len(errors) == 0, "errors": errors, "warnings": warnings}

    @staticmethod
    def build_query_string(conditional_filter: ConditionalFilter) -> str:
        """
        Build pandas query string from conditions

        Args:
            conditional_filter: ConditionalFilter object

        Returns:
            Query string for df.query()
        """
        query_parts = []

        for cond in conditional_filter.conditions:
            if cond.column_type == "string":
                # String comparison needs quotes
                query_parts.append(f"{cond.column} {cond.operator} '{cond.value}'")
            else:
                query_parts.append(f"{cond.column} {cond.operator} {cond.value}")

        logic_str = " and " if conditional_filter.logic == "AND" else " or "
        return logic_str.join(query_parts)

    @staticmethod
    def segment_data(
        df: pd.DataFrame,
        conditional_filter: ConditionalFilter,
        min_observations: int = 30,
    ) -> Dict[str, any]:
        """
        Segment data based on conditions

        Args:
            df: DataFrame to segment
            conditional_filter: ConditionalFilter object
            min_observations: Minimum observations per group

        Returns:
            Dictionary with segmented data and metadata
        """
        # Validate first
        validation = DataSegmenter.validate_conditions(df, conditional_filter)
        if not validation["valid"]:
            raise ValueError(f"Validation failed: {validation['errors']}")

        # Build query
        query_str = DataSegmenter.build_query_string(conditional_filter)

        # Segment data
        try:
            group_true = df.query(query_str)
            group_false = df.query(f"not ({query_str})")
        except Exception as e:
            raise ValueError(f"Failed to apply filter: {e}")

        # Check for empty groups
        if len(group_true) == 0:
            raise ValueError(
                "Condition matches 0 observations. "
                "Please adjust condition thresholds."
            )

        if len(group_false) == 0:
            raise ValueError(
                "Condition matches ALL observations. " "No comparison group available."
            )

        # Check minimum observations
        warnings = []
        if len(group_true) < min_observations:
            warnings.append(
                f"Group TRUE has only {len(group_true)} observations "
                f"(recommended: ≥{min_observations})"
            )

        if len(group_false) < min_observations:
            warnings.append(
                f"Group FALSE has only {len(group_false)} observations "
                f"(recommended: ≥{min_observations})"
            )

        # Check for imbalance
        ratio = len(group_true) / len(group_false)
        if ratio > 10 or ratio < 0.1:
            warnings.append(
                f"Groups are imbalanced: {len(group_true)} vs {len(group_false)}. "
                f"Consider using non-parametric tests."
            )

        return {
            "group_true": group_true,
            "group_false": group_false,
            "n_true": len(group_true),
            "n_false": len(group_false),
            "query": query_str,
            "warnings": warnings,
            "validation_warnings": validation["warnings"],
        }


class ConditionalAnalyzer:
    """Analyze metrics across conditional segments"""

    @staticmethod
    def compare_metric(
        group_true: pd.DataFrame,
        group_false: pd.DataFrame,
        metric_column: str,
        metric_name: str = "metric",
    ) -> Dict[str, any]:
        """
        Compare a metric between two groups

        Args:
            group_true: DataFrame for condition=True
            group_false: DataFrame for condition=False
            metric_column: Column name containing the metric
            metric_name: Human-readable metric name

        Returns:
            Dictionary with comparison results
        """
        # Extract metric values
        values_true = group_true[metric_column].dropna().values
        values_false = group_false[metric_column].dropna().values

        # Calculate statistics
        stats_true = {
            "mean": np.mean(values_true),
            "median": np.median(values_true),
            "std": np.std(values_true, ddof=1),
            "n": len(values_true),
        }

        stats_false = {
            "mean": np.mean(values_false),
            "median": np.median(values_false),
            "std": np.std(values_false, ddof=1),
            "n": len(values_false),
        }

        # Calculate differences
        diff = {
            "mean": stats_true["mean"] - stats_false["mean"],
            "median": stats_true["median"] - stats_false["median"],
        }

        return {
            "metric_name": metric_name,
            "group_true": stats_true,
            "group_false": stats_false,
            "difference": diff,
        }


# Example usage
if __name__ == "__main__":
    # Create sample data
    np.random.seed(42)
    df = pd.DataFrame(
        {
            "date": pd.date_range("2020-01-01", periods=1000),
            "returns": np.random.normal(0.001, 0.02, 1000),
            "VIX": np.random.uniform(10, 50, 1000),
            "market_cap": np.random.uniform(500, 2000, 1000),
            "regime": np.random.choice(["bull", "bear"], 1000),
        }
    )

    # Parse single condition
    parser = ConditionParser()
    cond = parser.parse_simple_condition("VIX > 20")
    print(f"Parsed condition: {cond.column} {cond.operator} {cond.value}")
    print()

    # Parse multiple conditions
    cond_filter = parser.parse_multiple_conditions("VIX > 20 AND market_cap > 1000")
    print(
        f"Parsed {len(cond_filter.conditions)} conditions with {cond_filter.logic} logic"
    )
    print()

    # Segment data
    segmenter = DataSegmenter()
    result = segmenter.segment_data(df, cond_filter)
    print("Segmentation results:")
    print(f"  Group TRUE: {result['n_true']} observations")
    print(f"  Group FALSE: {result['n_false']} observations")
    print(f"  Query: {result['query']}")
    if result["warnings"]:
        print(f"  Warnings: {result['warnings']}")
    print()

    # Compare metric
    analyzer = ConditionalAnalyzer()
    comparison = analyzer.compare_metric(
        result["group_true"], result["group_false"], "returns", "Returns"
    )
    print("Metric Comparison:")
    print(f"  Group TRUE mean: {comparison['group_true']['mean']:.6f}")
    print(f"  Group FALSE mean: {comparison['group_false']['mean']:.6f}")
    print(f"  Difference: {comparison['difference']['mean']:.6f}")
