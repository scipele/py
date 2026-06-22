# calculator.py
import pandas as pd
import numpy as np

class RetirementPlanner:
    def __init__(self, params):
        self.inp = params  # renamed from self.params
        self.cd = None     # will hold detailed calculation data (list of dicts)

    def get_inflation_adjusted_expense(self, age):
        """Returns retirement expenses adjusted for inflation up to the given age."""
        years_elapsed = age - self.inp['current_age']
        inflation_factor = (1 + self.inp['expected_annual_inflation_rate']) ** years_elapsed
        return self.inp['expected_retirement_expenses'] * inflation_factor

    def run_projection(self, simulation_returns=None):
        """
        Generates cash flow projection.
        If simulation_returns (list of random rates) is provided, runs stochastic.
        Otherwise runs deterministic (flat rate).
        
        Populates self.cd with detailed yearly calculation data.
        """
        current_year = 2026
        age = self.inp['current_age']
        savings = self.inp['current_savings_other'] + self.inp['current_savings_401k']
        equity_payout_per_year = (self.inp['company_equity_value'] / self.inp['company_equity_payback_period_years'])
        
        self.cd = []
        year_idx = 0

        while age <= self.inp['expected_life_expectancy']:
            # 1. Equity Payout Dispersion

            if (current_year >= self.inp['company_equity_payout_initial_year'] 
                and year_idx < self.inp['company_equity_payback_period_years']):
                savings += equity_payout_per_year
            else:
                savings += self.inp['annual_contribution']

            # 3. Add home downsizing cash infusion if applicable
            if current_year == self.inp.get('home_downsizing_year', 0):
                savings += self.inp.get('home_downsizing_estim_cash_infusion', 0)

            # 4. Apply Childhood Expenses (only for duration input)
            if year_idx <= self.inp.get('expected_duration_of_child_expenses', 0):
                savings -= self.inp.get('expected_child_expenses', 0)

            # 5. Apply Investment Returns
            if age > self.inp['current_age']:
                rate = (simulation_returns[year_idx] 
                        if simulation_returns is not None 
                        else self.inp['expected_annual_return_rate'])
                savings *= (1 + rate)

            # 6. Social Security (only after eligibility age)
            ss_income = 0
            if age >= self.inp['expected_age_of_social_security_benefits']:
                # can you increase SS income with inflation?
                years_since_eligibility = age - self.inp['expected_age_of_social_security_benefits']
                ss_income = self.inp['expected_initial_income_social_security'] * (1 + self.inp['expected_annual_inflation_rate']) ** years_since_eligibility

            # 7. Expenses (inflation adjusted) and SS
            expenses = self.get_inflation_adjusted_expense(age)
            savings -= expenses
            savings += ss_income

            # 8. Store detailed calculation data for this year
            self.cd.append({
                "Age": age,
                "Year": current_year,
                "Home_Downsz": self.inp.get('home_downsizing_estim_cash_infusion', 0) if current_year == self.inp.get('home_downsizing_year', 0) else 0,
                "Child_Exp": self.inp.get('expected_child_expenses', 0) if year_idx <= self.inp.get('expected_duration_of_child_expenses', 0) else 0,
                "Equity_Pmt": equity_payout_per_year if (current_year >= self.inp['company_equity_payout_initial_year'] and year_idx < self.inp['company_equity_payback_period_years']) else self.inp['annual_contribution'],
                "Expenses": expenses,
                "SS_Income": ss_income,
                "Net_Val_EOY": savings
            })

            age += 1
            current_year += 1
            year_idx += 1

        return pd.DataFrame(self.cd)