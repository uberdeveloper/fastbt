"""
Reporter Module

Generates tweet-style summaries and detailed markdown reports
for statistical test results.
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional
from datetime import datetime
from pathlib import Path


class TweetStyleReporter:
    """Generate concise tweet-style summaries"""
    
    @staticmethod
    def format_p_value(p_value: float) -> str:
        """Format p-value for display"""
        if p_value < 0.001:
            return "< 0.001"
        else:
            return f"{p_value:.3f}"
    
    @staticmethod
    def format_percentage(value: float) -> str:
        """Format percentage for display"""
        return f"{value * 100:.2f}%"
    
    @staticmethod
    def performance_test_summary(
        test_result: Dict,
        metrics: Dict,
        confidence_level: float = 0.95
    ) -> str:
        """
        Generate summary for performance test
        
        Args:
            test_result: TestResult from test_engine
            metrics: Performance metrics dictionary
            confidence_level: Confidence level used
            
        Returns:
            Markdown formatted summary
        """
        verdict = "significant positive returns" if test_result['significant'] else "no significant evidence of positive returns"
        
        summary = f"""📊 Result: Your strategy has {verdict}

Key Metrics:
- Mean Return: {TweetStyleReporter.format_percentage(metrics['mean_return'])} per period
- Median Return: {TweetStyleReporter.format_percentage(metrics['median_return'])} per period
- Sharpe Ratio: {metrics['sharpe_ratio']:.2f}
- p-value: {TweetStyleReporter.format_p_value(test_result['p_value'])}
- Confidence: {int(confidence_level * 100)}%

🎯 {'Strong evidence of real alpha (not a statistical artifact)' if test_result['significant'] else 'Insufficient evidence to claim alpha'}

⚠️ Note: Returns {'are' if test_result['distribution_type'] == 'normal' else 'are NOT'} normally distributed (used {test_result['test_name']})
"""
        return summary
    
    @staticmethod
    def outperformance_test_summary(
        test_result: Dict,
        strategy_metrics: Dict,
        benchmark_metrics: Dict,
        benchmark_name: str = "benchmark",
        confidence_level: float = 0.95
    ) -> str:
        """
        Generate summary for outperformance test
        
        Args:
            test_result: TestResult from test_engine
            strategy_metrics: Strategy performance metrics
            benchmark_metrics: Benchmark performance metrics
            benchmark_name: Name of benchmark
            confidence_level: Confidence level used
            
        Returns:
            Markdown formatted summary
        """
        verdict = f"significantly outperforms {benchmark_name}" if test_result['significant'] else f"does not significantly outperform {benchmark_name}"
        
        excess_sharpe = strategy_metrics['sharpe_ratio'] - benchmark_metrics['sharpe_ratio']
        
        summary = f"""📊 Result: Your strategy {verdict}

Key Metrics:
- Strategy Sharpe: {strategy_metrics['sharpe_ratio']:.2f}
- {benchmark_name} Sharpe: {benchmark_metrics['sharpe_ratio']:.2f}
- Excess Sharpe: {excess_sharpe:+.2f}
- p-value: {TweetStyleReporter.format_p_value(test_result['p_value'])}
- Confidence: {int(confidence_level * 100)}%

🎯 {'Strong evidence of outperformance' if test_result['significant'] else 'No significant outperformance detected'}

⚠️ Note: Returns {'are' if test_result['distribution_type'] == 'normal' else 'are NOT'} normally distributed (used {test_result['test_name']})
"""
        return summary
    
    @staticmethod
    def conditional_analysis_summary(
        condition_str: str,
        metric_name: str,
        comparison_result: Dict,
        test_result: Dict,
        confidence_level: float = 0.95
    ) -> str:
        """
        Generate summary for conditional analysis
        
        Args:
            condition_str: Human-readable condition
            metric_name: Name of metric being compared
            comparison_result: Comparison statistics
            test_result: TestResult from test_engine
            confidence_level: Confidence level used
            
        Returns:
            Markdown formatted summary
        """
        group_true = comparison_result['group_true']
        group_false = comparison_result['group_false']
        diff = comparison_result['difference']
        
        # Determine direction
        if diff['median'] > 0:
            direction = "higher"
        elif diff['median'] < 0:
            direction = "lower"
        else:
            direction = "the same"
        
        verdict = f"{metric_name} is significantly {direction} when {condition_str}" if test_result['significant'] else f"No significant difference in {metric_name}"
        
        summary = f"""📊 Conditional Analysis: {metric_name} when {condition_str}

| Condition | N | Median | Mean | Std Dev | p-value |
|-----------|---|--------|------|---------|---------|
| TRUE | {group_true['n']} | {group_true['median']:.4f} | {group_true['mean']:.4f} | {group_true['std']:.4f} | - |
| FALSE | {group_false['n']} | {group_false['median']:.4f} | {group_false['mean']:.4f} | {group_false['std']:.4f} | - |
| **Difference** | - | **{diff['median']:.4f}** | **{diff['mean']:.4f}** | - | **{TweetStyleReporter.format_p_value(test_result['p_value'])}** |

🎯 Result: {verdict}

Test: {test_result['test_name']}
Confidence: {int(confidence_level * 100)}%
"""
        return summary


class DetailedReporter:
    """Generate detailed markdown reports"""
    
    @staticmethod
    def full_report(
        test_type: str,
        test_results: List[Dict],
        metrics: Dict,
        distribution_check: Dict,
        warnings: List[str] = None,
        additional_info: Dict = None
    ) -> str:
        """
        Generate comprehensive markdown report
        
        Args:
            test_type: Type of test performed
            test_results: List of test result dictionaries
            metrics: Performance metrics
            distribution_check: Distribution check results
            warnings: List of warning messages
            additional_info: Additional information to include
            
        Returns:
            Detailed markdown report
        """
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        report = f"""# Statistical Analysis Report

**Generated:** {timestamp}  
**Test Type:** {test_type}

---

## Distribution Analysis

"""
        
        # Distribution check
        if distribution_check:
            report += f"""
**Normality Tests:**
- Shapiro-Wilk p-value: {distribution_check.get('shapiro_p', 'N/A')}
- Jarque-Bera p-value: {distribution_check.get('jarque_bera_p', 'N/A')}
- Distribution: {'Normal' if distribution_check.get('is_normal') else 'Non-normal'}
- Recommendation: Use {distribution_check.get('recommendation', 'N/A')} tests

**Distribution Characteristics:**
- Skewness: {distribution_check.get('skewness', 'N/A'):.4f}
- Kurtosis: {distribution_check.get('kurtosis', 'N/A'):.4f}

"""
        
        # Test results
        report += "## Statistical Tests\n\n"
        for i, result in enumerate(test_results, 1):
            report += f"""
### Test {i}: {result.get('test_name', 'Unknown')}

- Test Statistic: {result.get('statistic', 'N/A'):.4f}
- p-value: {TweetStyleReporter.format_p_value(result.get('p_value', 1.0))}
- Significant: {'Yes' if result.get('significant') else 'No'}
- Confidence Level: {int(result.get('confidence_level', 0.95) * 100)}%

**Interpretation:** {result.get('interpretation', 'N/A')}

"""
        
        # Performance metrics
        if metrics:
            report += "## Performance Metrics\n\n"
            report += "| Metric | Value |\n"
            report += "|--------|-------|\n"
            for key, value in metrics.items():
                if isinstance(value, (int, float)):
                    report += f"| {key.replace('_', ' ').title()} | {value:.4f} |\n"
                else:
                    report += f"| {key.replace('_', ' ').title()} | {value} |\n"
            report += "\n"
        
        # Warnings
        if warnings:
            report += "## Warnings\n\n"
            for warning in warnings:
                report += f"- ⚠️ {warning}\n"
            report += "\n"
        
        # Additional info
        if additional_info:
            report += "## Additional Information\n\n"
            for key, value in additional_info.items():
                report += f"**{key.replace('_', ' ').title()}:** {value}\n\n"
        
        report += "---\n\n*Report generated by Statistical Testing Skill v1.0*\n"
        
        return report
    
    @staticmethod
    def save_report(
        report: str,
        filename: Optional[str] = None,
        output_dir: str = "."
    ) -> str:
        """
        Save report to markdown file
        
        Args:
            report: Markdown report string
            filename: Output filename (auto-generated if None)
            output_dir: Output directory
            
        Returns:
            Path to saved file
        """
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"statistical_analysis_{timestamp}.md"
        
        output_path = Path(output_dir) / filename
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_path, 'w') as f:
            f.write(report)
        
        return str(output_path)


class ComparisonTableGenerator:
    """Generate comparison tables for conditional analysis"""
    
    @staticmethod
    def generate_comparison_table(
        groups: List[Dict],
        group_labels: List[str],
        metrics: List[str]
    ) -> str:
        """
        Generate markdown comparison table
        
        Args:
            groups: List of group statistics dictionaries
            group_labels: Labels for each group
            metrics: List of metric names to include
            
        Returns:
            Markdown table string
        """
        # Header
        table = "| Group | N |"
        for metric in metrics:
            table += f" {metric.title()} |"
        table += "\n"
        
        # Separator
        table += "|" + "---|" * (len(metrics) + 2) + "\n"
        
        # Data rows
        for label, group in zip(group_labels, groups):
            table += f"| {label} | {group.get('n', 'N/A')} |"
            for metric in metrics:
                value = group.get(metric, np.nan)
                if isinstance(value, (int, float)) and not np.isnan(value):
                    table += f" {value:.4f} |"
                else:
                    table += " N/A |"
            table += "\n"
        
        return table


# Example usage
if __name__ == "__main__":
    # Example test result
    test_result = {
        'test_name': 'Wilcoxon signed-rank test',
        'statistic': 123456.0,
        'p_value': 0.003,
        'significant': True,
        'confidence_level': 0.95,
        'distribution_type': 'non-normal',
        'interpretation': 'Significant positive returns detected'
    }
    
    # Example metrics
    metrics = {
        'mean_return': 0.0012,
        'median_return': 0.0011,
        'std_dev': 0.015,
        'sharpe_ratio': 1.23,
        'max_drawdown': -0.183,
        'win_rate': 0.542,
        'n_observations': 1000
    }
    
    # Example distribution check
    dist_check = {
        'is_normal': False,
        'shapiro_p': 0.023,
        'jarque_bera_p': 0.012,
        'skewness': -0.45,
        'kurtosis': 3.2,
        'recommendation': 'non-parametric'
    }
    
    # Generate tweet-style summary
    reporter = TweetStyleReporter()
    summary = reporter.performance_test_summary(test_result, metrics)
    print("=== Tweet-Style Summary ===")
    print(summary)
    print()
    
    # Generate detailed report
    detailed = DetailedReporter()
    report = detailed.full_report(
        test_type="Performance Test",
        test_results=[test_result],
        metrics=metrics,
        distribution_check=dist_check,
        warnings=["Returns not normally distributed"]
    )
    print("=== Detailed Report ===")
    print(report)
    
    # Save report
    filepath = detailed.save_report(report, output_dir="/tmp")
    print(f"\nReport saved to: {filepath}")
