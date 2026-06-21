# calculator.py
import pandas as pd
import numpy as np

class RetirementPlanner:
    def __init__(self, params):
        self.params = params

    def get_inflation_adjusted_expense(self, age, start_year):
        """Calculates future expenses adjusted for compound inflation."""
        years_elapsed = age - self.params['current_age']
        return self.params['expected_retirement_expenses'] * ((1 + self.params['expected_annual_inflation_rate'] / 100) ** years_elapsed)

    def run_projection(self, simulation_returns=None):
        """
        Generates cash flow. If simulation_returns (a list of random rates) 
        is provided, it runs a stochastic path. Otherwise, it runs a flat rate.
        """
        current_year = 2026
        age = self.params['current_age']
        savings = self.params['current_savings_other'] + self.params['current_savings_401k']
        
        data = []
        year_idx = 0
        
        while age <= self.params['expected_life_expectancy']:
            # 1. Company Equity Payouts
            equity_payout = 0
            if current_year >= self.params['company_equity_payout_initial_year']:
                years_since_payout = current_year - self.params['company_equity_payout_initial_year']
                if years_since_payout < self.params['company_equity_payback_period_years']:
                    equity_payout = self.params['company_equity_value'] / self.params['company_equity_payback_period_years']
            
            # 2. Add Contributions and Equity
            savings += self.params['annual_contribution'] + equity_payout
            
            # 3. Apply Investment Returns (Deterministic vs Random)
            if age > self.params['current_age']:
                if simulation_returns is not None:
                    rate = simulation_returns[year_idx]
                else:
                    rate = self.params['expected_annual_return_rate']
                
                savings *= (1 + rate / 100)
            
            # 4. Social Security
            ss_income = 0
            if age >= self.params['expected_age_of_social_security_benefits']:
                ss_income = self.params['expected_retirement_income_social_security']
            
            # 5. Subtract Expenses
            expenses = self.get_inflation_adjusted_expense(age, current_year)
            savings -= expenses
            savings += ss_income
            
            data.append({
                "Age": age,
                "Year": current_year,
                "Net_Value_End_OfYear": savings
            })
            
            age += 1
            current_year += 1
            year_idx += 1
            
        return pd.DataFrame(data)
