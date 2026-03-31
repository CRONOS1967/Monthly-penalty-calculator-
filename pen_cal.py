"""
Penalty Calculator Module
========================
Calculates compounding monthly penalties based on a fixed rate table.
Useful for financial calculations, late payment processing, and data analysis.

Author: Cronos
Version: 1.0.0
"""

from typing import Dict, List, Optional, Union
from dataclasses import dataclass, asdict
from decimal import Decimal, ROUND_HALF_UP
import json


@dataclass
class MonthlyBreakdown:
    """Represents penalty breakdown for a single month"""
    month: int
    base_pay: float
    previous_unpaid: float
    rate: float
    penalty: float
    total_due: float
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for easy JSON/CSV export"""
        return asdict(self)
    
    def to_tuple(self) -> tuple:
        """Convert to tuple for database insertion"""
        return (self.month, self.base_pay, self.previous_unpaid, 
                self.rate, self.penalty, self.total_due)


@dataclass
class PenaltyResult:
    """Complete penalty calculation result"""
    monthly_breakdown: List[MonthlyBreakdown]
    total_penalty: float
    total_due: float
    base_monthly_pay: float
    number_of_months: int
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for JSON export"""
        return {
            'total_penalty': self.total_penalty,
            'total_due': self.total_due,
            'base_monthly_pay': self.base_monthly_pay,
            'number_of_months': self.number_of_months,
            'monthly_breakdown': [m.to_dict() for m in self.monthly_breakdown]
        }
    
    def to_dataframe_rows(self) -> List[Dict]:
        """Convert to list of dicts for pandas DataFrame"""
        return [m.to_dict() for m in self.monthly_breakdown]
    
    def get_summary(self) -> Dict:
        """Get summary statistics"""
        return {
            'total_penalty': self.total_penalty,
            'total_due': self.total_due,
            'effective_penalty_rate': (self.total_penalty / self.total_due * 100) if self.total_due > 0 else 0,
            'average_monthly_penalty': self.total_penalty / self.number_of_months,
            'max_monthly_penalty': max(m.penalty for m in self.monthly_breakdown),
            'min_monthly_penalty': min(m.penalty for m in self.monthly_breakdown)
        }


class PenaltyCalculator:
    """
    Main penalty calculator class with configurable rate table.
    
    Attributes:
        rate_table (Dict[int, float]): Late month -> penalty rate mapping
        monthly_pay (float): Base monthly payment amount
        decimal_precision (int): Number of decimal places for rounding
    """
    
    # Default rate table as defined in requirements
    DEFAULT_RATE_TABLE = {
        1: 8.0, 2: 7.0, 3: 6.0, 4: 5.0, 5: 5.0, 6: 5.0,
        7: 4.0, 8: 4.0, 9: 4.0, 10: 4.0, 11: 3.0, 12: 3.0,
        13: 3.0, 14: 3.0, 15: 3.0, 16: 2.0, 17: 2.0, 18: 2.0,
        19: 2.0, 20: 2.0, 21: 2.0, 22: 2.0, 23: 2.0, 24: 2.0,
        25: 2.0, 26: 2.0, 27: 2.0, 28: 2.0, 29: 2.0, 30: 2.0,
        31: 2.0, 32: 2.0, 33: 2.0, 34: 2.0, 35: 2.0, 36: 2.0
    }
    
    def __init__(self, 
                 monthly_pay: float = 0.0, 
                 rate_table: Optional[Dict[int, float]] = None,
                 decimal_precision: int = 2):
        """
        Initialize the penalty calculator.
        
        Args:
            monthly_pay: Base monthly payment amount
            rate_table: Custom rate table (uses default if None)
            decimal_precision: Number of decimal places for rounding
        """
        self.monthly_pay = monthly_pay
        self.rate_table = rate_table if rate_table is not None else self.DEFAULT_RATE_TABLE.copy()
        self.decimal_precision = decimal_precision
        
    def set_monthly_pay(self, monthly_pay: float) -> None:
        """Update the base monthly payment amount"""
        self.monthly_pay = monthly_pay
        
    def set_rate_table(self, rate_table: Dict[int, float]) -> None:
        """Update the penalty rate table"""
        self.rate_table = rate_table.copy()
        
    def update_rate(self, month: int, rate: float) -> None:
        """Update rate for a specific month"""
        self.rate_table[month] = rate
        
    def get_rate_for_month(self, month: int) -> float:
        """
        Get the penalty rate for a specific month.
        
        Args:
            month: The month number (1-indexed)
            
        Returns:
            Penalty rate as percentage (e.g., 8 for 8%)
        """
        # If month beyond defined table, use last available rate
        if month > max(self.rate_table.keys()):
            return self.rate_table[max(self.rate_table.keys())]
        return self.rate_table.get(month, 0.0)
    
    def _round_decimal(self, value: float) -> float:
        """
        Round a float to specified decimal precision.
        
        Args:
            value: Float value to round
            
        Returns:
            Rounded float
        """
        decimal_value = Decimal(str(value)).quantize(
            Decimal('0.' + '0' * self.decimal_precision), 
            rounding=ROUND_HALF_UP
        )
        return float(decimal_value)
    
    def calculate(self, months: int, start_from_month: int = 1) -> PenaltyResult:
        """
        Calculate penalties for a specified number of months.
        
        Args:
            months: Number of months to calculate (1-36+)
            start_from_month: Starting month number (default 1)
            
        Returns:
            PenaltyResult object containing complete calculation details
            
        Raises:
            ValueError: If months is less than 1 or monthly_pay is invalid
        """
        if months < 1:
            raise ValueError("Number of months must be at least 1")
        if self.monthly_pay <= 0:
            raise ValueError("Monthly pay must be greater than 0")
            
        total_unpaid = 0.0
        monthly_breakdown = []
        
        for i in range(months):
            current_month = start_from_month + i
            rate = self.get_rate_for_month(current_month)
            
            # Amount to calculate penalty on = base pay + all previous unpaid amounts
            amount_for_penalty = self.monthly_pay + total_unpaid
            
            # Calculate penalty for this month
            monthly_penalty = amount_for_penalty * (rate / 100)
            monthly_penalty = self._round_decimal(monthly_penalty)
            
            # Total due this month (including penalty)
            total_due_this_month = amount_for_penalty + monthly_penalty
            total_due_this_month = self._round_decimal(total_due_this_month)
            
            # Store breakdown
            breakdown = MonthlyBreakdown(
                month=current_month,
                base_pay=self._round_decimal(self.monthly_pay),
                previous_unpaid=self._round_decimal(total_unpaid),
                rate=rate,
                penalty=monthly_penalty,
                total_due=total_due_this_month
            )
            monthly_breakdown.append(breakdown)
            
            # Update total unpaid for next month
            total_unpaid = total_due_this_month
        
        # Calculate totals
        total_penalty = sum(m.penalty for m in monthly_breakdown)
        total_penalty = self._round_decimal(total_penalty)
        total_due = self._round_decimal(total_unpaid)
        
        return PenaltyResult(
            monthly_breakdown=monthly_breakdown,
            total_penalty=total_penalty,
            total_due=total_due,
            base_monthly_pay=self.monthly_pay,
            number_of_months=months
        )
    
    def calculate_batch(self, payment_amounts: List[float], months_list: List[int]) -> List[PenaltyResult]:
        """
        Calculate penalties for multiple scenarios.
        
        Args:
            payment_amounts: List of base monthly payment amounts
            months_list: List of number of months for each calculation
            
        Returns:
            List of PenaltyResult objects
        """
        results = []
        for pay, months in zip(payment_amounts, months_list):
            self.set_monthly_pay(pay)
            results.append(self.calculate(months))
        return results
    
    def get_validation_info(self) -> Dict:
        """
        Get validation information about the rate table.
        
        Returns:
            Dictionary with rate table statistics
        """
        return {
            'min_month': min(self.rate_table.keys()),
            'max_month': max(self.rate_table.keys()),
            'total_months_defined': len(self.rate_table),
            'rate_range': (min(self.rate_table.values()), max(self.rate_table.values())),
            'rate_table': self.rate_table
        }


# Convenience functions for simple use cases
def quick_calculate(monthly_pay: float, months: int) -> PenaltyResult:
    """
    Quick one-off calculation without creating a class instance.
    
    Args:
        monthly_pay: Base monthly payment amount
        months: Number of months to calculate
        
    Returns:
        PenaltyResult object
    """
    calculator = PenaltyCalculator(monthly_pay=monthly_pay)
    return calculator.calculate(months)


def calculate_for_dataframe(df, 
                           monthly_pay_column: str, 
                           months_column: str,
                           result_column_prefix: str = 'penalty_'):
    """
    Calculate penalties for a pandas DataFrame.
    
    Args:
        df: pandas DataFrame
        monthly_pay_column: Column name containing monthly payment amounts
        months_column: Column name containing number of months
        result_column_prefix: Prefix for result columns
        
    Returns:
        DataFrame with added penalty columns
    """
    try:
        import pandas as pd
    except ImportError:
        raise ImportError("pandas is required for DataFrame operations")
    
    calculator = PenaltyCalculator()
    results = []
    
    for _, row in df.iterrows():
        calculator.set_monthly_pay(row[monthly_pay_column])
        result = calculator.calculate(int(row[months_column]))
        results.append({
            f'{result_column_prefix}total_penalty': result.total_penalty,
            f'{result_column_prefix}total_due': result.total_due,
            f'{result_column_prefix}months': result.number_of_months
        })
    
    result_df = pd.DataFrame(results)
    return pd.concat([df, result_df], axis=1)


# Example usage and testing
if __name__ == "__main__":
    # Test the module with the example provided
    print("Testing Penalty Calculator Module\n")
    print("=" * 60)
    
    # Method 1: Using the class
    calculator = PenaltyCalculator(monthly_pay=20361.17)
    result = calculator.calculate(months=2)
    
    print("\nMethod 1 - Class-based calculation:")
    print(f"Total Penalty: ${result.total_penalty:,.2f}")
    print(f"Total Due: ${result.total_due:,.2f}")
    
    for month in result.monthly_breakdown:
        print(f"  Month {month.month}: Penalty ${month.penalty:,.2f}, Total Due ${month.total_due:,.2f}")
    
    # Method 2: Quick calculation function
    print("\nMethod 2 - Quick calculation function:")
    result2 = quick_calculate(monthly_pay=20361.17, months=2)
    print(f"Total Penalty: ${result2.total_penalty:,.2f}")
    print(f"Total Due: ${result2.total_due:,.2f}")
    
    # Get summary statistics
    print("\nSummary Statistics:")
    summary = result.get_summary()
    for key, value in summary.items():
        print(f"  {key}: {value:,.2f}" if isinstance(value, (int, float)) else f"  {key}: {value}")
    
    # Export to JSON
    print("\nJSON Export (first 2 months):")
    json_output = json.dumps(result.to_dict(), indent=2)
    print(json_output[:500] + "...")  # Truncated for display
    
    print("\n" + "=" * 60)
    print("Module ready for import and use with CSV/Excel/Power BI")