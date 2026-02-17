"""
Statistical Test Engine

Core statistical testing functionality using scipy.
Supports hypothesis tests, distribution checks, and metric calculations.
"""

import numpy as np
import pandas as pd
from scipy import stats
from typing import Dict, Tuple, Optional, Literal
from dataclasses import dataclass


@dataclass
class TestResult:
    """Container for statistical test results"""
    test_name: str
    statistic: float
    p_value: float
    significant: bool
    confidence_level: float
    distribution_type: Literal["normal", "non-normal"]
    interpretation: str
    additional_metrics: Dict[str, float]


class DistributionChecker:
    """Check if data follows normal distribution"""
    
    @staticmethod
    def check_normality(data: np.ndarray, alpha: float = 0.05) -> Dict[str, any]:
        """
        Run normality tests on data
        
        Args:
            data: Array of returns or values
            alpha: Significance level (default 0.05)
            
        Returns:
            Dictionary with test results and recommendation
        """
        # Remove NaN values
        data_clean = data[~np.isnan(data)]
        
        if len(data_clean) < 3:
            return {
                "is_normal": False,
                "reason": "Insufficient data for normality test",
                "shapiro_p": None,
                "jarque_bera_p": None,
                "recommendation": "non-parametric"
            }
        
        # Shapiro-Wilk test
        if len(data_clean) <= 5000:  # Shapiro-Wilk has sample size limits
            shapiro_stat, shapiro_p = stats.shapiro(data_clean)
        else:
            shapiro_p = None
            
        # Jarque-Bera test
        jarque_bera_stat, jarque_bera_p = stats.jarque_bera(data_clean)
        
        # Determine if normal
        tests_passed = []
        if shapiro_p is not None:
            tests_passed.append(shapiro_p > alpha)
        tests_passed.append(jarque_bera_p > alpha)
        
        is_normal = all(tests_passed)
        
        return {
            "is_normal": is_normal,
            "shapiro_p": shapiro_p,
            "jarque_bera_p": jarque_bera_p,
            "skewness": stats.skew(data_clean),
            "kurtosis": stats.kurtosis(data_clean),
            "recommendation": "parametric" if is_normal else "non-parametric"
        }


class HypothesisTests:
    """Statistical hypothesis tests"""
    
    @staticmethod
    def one_sample_test(
        data: np.ndarray,
        mu: float = 0.0,
        alpha: float = 0.05,
        use_parametric: bool = True
    ) -> TestResult:
        """
        Test if sample mean differs from population mean
        
        Args:
            data: Sample data
            mu: Population mean to test against (default 0)
            alpha: Significance level
            use_parametric: Use t-test (True) or Wilcoxon (False)
            
        Returns:
            TestResult object
        """
        data_clean = data[~np.isnan(data)]
        
        if use_parametric:
            # One-sample t-test
            statistic, p_value = stats.ttest_1samp(data_clean, mu)
            test_name = "One-sample t-test"
        else:
            # Wilcoxon signed-rank test
            statistic, p_value = stats.wilcoxon(data_clean - mu)
            test_name = "Wilcoxon signed-rank test"
        
        significant = p_value < alpha
        
        # Calculate additional metrics
        mean_return = np.mean(data_clean)
        median_return = np.median(data_clean)
        
        interpretation = (
            f"{'Significant' if significant else 'No significant'} evidence that "
            f"returns differ from {mu} (p={p_value:.4f})"
        )
        
        return TestResult(
            test_name=test_name,
            statistic=statistic,
            p_value=p_value,
            significant=significant,
            confidence_level=1 - alpha,
            distribution_type="normal" if use_parametric else "non-normal",
            interpretation=interpretation,
            additional_metrics={
                "mean": mean_return,
                "median": median_return,
                "std": np.std(data_clean),
                "n": len(data_clean)
            }
        )
    
    @staticmethod
    def paired_test(
        data1: np.ndarray,
        data2: np.ndarray,
        alpha: float = 0.05,
        use_parametric: bool = True
    ) -> TestResult:
        """
        Test if two paired samples differ (e.g., strategy vs benchmark)
        
        Args:
            data1: First sample (e.g., strategy returns)
            data2: Second sample (e.g., benchmark returns)
            alpha: Significance level
            use_parametric: Use t-test (True) or Wilcoxon (False)
            
        Returns:
            TestResult object
        """
        # Align data (remove NaN pairs)
        mask = ~(np.isnan(data1) | np.isnan(data2))
        data1_clean = data1[mask]
        data2_clean = data2[mask]
        
        if len(data1_clean) < 2:
            raise ValueError("Insufficient paired observations")
        
        if use_parametric:
            # Paired t-test
            statistic, p_value = stats.ttest_rel(data1_clean, data2_clean)
            test_name = "Paired t-test"
        else:
            # Wilcoxon signed-rank test
            statistic, p_value = stats.wilcoxon(data1_clean, data2_clean)
            test_name = "Wilcoxon signed-rank test (paired)"
        
        significant = p_value < alpha
        
        # Calculate differences
        diff = data1_clean - data2_clean
        mean_diff = np.mean(diff)
        median_diff = np.median(diff)
        
        interpretation = (
            f"{'Significant' if significant else 'No significant'} difference "
            f"between samples (p={p_value:.4f})"
        )
        
        return TestResult(
            test_name=test_name,
            statistic=statistic,
            p_value=p_value,
            significant=significant,
            confidence_level=1 - alpha,
            distribution_type="normal" if use_parametric else "non-normal",
            interpretation=interpretation,
            additional_metrics={
                "mean_diff": mean_diff,
                "median_diff": median_diff,
                "std_diff": np.std(diff),
                "n_pairs": len(data1_clean)
            }
        )
    
    @staticmethod
    def independent_test(
        data1: np.ndarray,
        data2: np.ndarray,
        alpha: float = 0.05,
        use_parametric: bool = True
    ) -> TestResult:
        """
        Test if two independent samples differ
        
        Args:
            data1: First sample
            data2: Second sample
            alpha: Significance level
            use_parametric: Use t-test (True) or Mann-Whitney U (False)
            
        Returns:
            TestResult object
        """
        data1_clean = data1[~np.isnan(data1)]
        data2_clean = data2[~np.isnan(data2)]
        
        if use_parametric:
            # Independent t-test
            statistic, p_value = stats.ttest_ind(data1_clean, data2_clean)
            test_name = "Independent t-test"
        else:
            # Mann-Whitney U test
            statistic, p_value = stats.mannwhitneyu(
                data1_clean, data2_clean, alternative='two-sided'
            )
            test_name = "Mann-Whitney U test"
        
        significant = p_value < alpha
        
        interpretation = (
            f"{'Significant' if significant else 'No significant'} difference "
            f"between groups (p={p_value:.4f})"
        )
        
        return TestResult(
            test_name=test_name,
            statistic=statistic,
            p_value=p_value,
            significant=significant,
            confidence_level=1 - alpha,
            distribution_type="normal" if use_parametric else "non-normal",
            interpretation=interpretation,
            additional_metrics={
                "group1_mean": np.mean(data1_clean),
                "group2_mean": np.mean(data2_clean),
                "group1_median": np.median(data1_clean),
                "group2_median": np.median(data2_clean),
                "n1": len(data1_clean),
                "n2": len(data2_clean)
            }
        )


class PerformanceMetrics:
    """Calculate performance metrics for strategy evaluation"""
    
    @staticmethod
    def sharpe_ratio(returns: np.ndarray, periods_per_year: int = 252) -> float:
        """
        Calculate annualized Sharpe ratio
        
        Args:
            returns: Array of returns
            periods_per_year: Number of periods in a year (252 for daily, 52 for weekly)
            
        Returns:
            Annualized Sharpe ratio
        """
        returns_clean = returns[~np.isnan(returns)]
        if len(returns_clean) == 0:
            return np.nan
        
        mean_return = np.mean(returns_clean)
        std_return = np.std(returns_clean, ddof=1)
        
        if std_return == 0:
            return np.nan
        
        sharpe = (mean_return / std_return) * np.sqrt(periods_per_year)
        return sharpe
    
    @staticmethod
    def max_drawdown(returns: np.ndarray) -> float:
        """
        Calculate maximum drawdown
        
        Args:
            returns: Array of returns
            
        Returns:
            Maximum drawdown (negative value)
        """
        returns_clean = returns[~np.isnan(returns)]
        cumulative = np.cumprod(1 + returns_clean)
        running_max = np.maximum.accumulate(cumulative)
        drawdown = (cumulative - running_max) / running_max
        return np.min(drawdown)
    
    @staticmethod
    def win_rate(returns: np.ndarray) -> float:
        """
        Calculate percentage of positive returns
        
        Args:
            returns: Array of returns
            
        Returns:
            Win rate (0 to 1)
        """
        returns_clean = returns[~np.isnan(returns)]
        if len(returns_clean) == 0:
            return np.nan
        return np.sum(returns_clean > 0) / len(returns_clean)
    
    @staticmethod
    def calculate_all_metrics(
        returns: np.ndarray,
        periods_per_year: int = 252
    ) -> Dict[str, float]:
        """
        Calculate all performance metrics
        
        Args:
            returns: Array of returns
            periods_per_year: Number of periods in a year
            
        Returns:
            Dictionary of metrics
        """
        returns_clean = returns[~np.isnan(returns)]
        
        return {
            "mean_return": np.mean(returns_clean),
            "median_return": np.median(returns_clean),
            "std_dev": np.std(returns_clean, ddof=1),
            "sharpe_ratio": PerformanceMetrics.sharpe_ratio(returns, periods_per_year),
            "max_drawdown": PerformanceMetrics.max_drawdown(returns),
            "win_rate": PerformanceMetrics.win_rate(returns),
            "skewness": stats.skew(returns_clean),
            "kurtosis": stats.kurtosis(returns_clean),
            "n_observations": len(returns_clean)
        }


class MultipleTestingCorrection:
    """Handle multiple testing correction"""
    
    @staticmethod
    def bonferroni(p_values: list, alpha: float = 0.05) -> Dict[str, any]:
        """
        Apply Bonferroni correction
        
        Args:
            p_values: List of p-values
            alpha: Family-wise error rate
            
        Returns:
            Dictionary with corrected results
        """
        n_tests = len(p_values)
        adjusted_alpha = alpha / n_tests
        
        significant = [p < adjusted_alpha for p in p_values]
        
        return {
            "n_tests": n_tests,
            "original_alpha": alpha,
            "adjusted_alpha": adjusted_alpha,
            "p_values": p_values,
            "significant": significant,
            "correction_method": "Bonferroni"
        }


# Example usage
if __name__ == "__main__":
    # Generate sample data
    np.random.seed(42)
    strategy_returns = np.random.normal(0.001, 0.02, 1000)  # Positive mean
    benchmark_returns = np.random.normal(0.0005, 0.015, 1000)
    
    # Check distribution
    checker = DistributionChecker()
    dist_result = checker.check_normality(strategy_returns)
    print("Distribution Check:")
    print(f"  Is Normal: {dist_result['is_normal']}")
    print(f"  Shapiro p-value: {dist_result['shapiro_p']:.4f}")
    print(f"  Recommendation: {dist_result['recommendation']}")
    print()
    
    # One-sample test
    tester = HypothesisTests()
    result = tester.one_sample_test(
        strategy_returns,
        use_parametric=dist_result['is_normal']
    )
    print(f"One-Sample Test: {result.test_name}")
    print(f"  p-value: {result.p_value:.4f}")
    print(f"  Significant: {result.significant}")
    print(f"  {result.interpretation}")
    print()
    
    # Paired test
    paired_result = tester.paired_test(
        strategy_returns,
        benchmark_returns,
        use_parametric=dist_result['is_normal']
    )
    print(f"Paired Test: {paired_result.test_name}")
    print(f"  p-value: {paired_result.p_value:.4f}")
    print(f"  Significant: {paired_result.significant}")
    print()
    
    # Performance metrics
    metrics = PerformanceMetrics.calculate_all_metrics(strategy_returns)
    print("Performance Metrics:")
    for key, value in metrics.items():
        print(f"  {key}: {value:.4f}")
