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
        
        self.cd = []          # ← Your requested calc data structure
        year_idx = 0

        while age <= self.inp['expected_life_expectancy']:
            # 1. Company Equity Payout (only during payback period)
            equity_payout = 0
            if current_year >= self.inp['company_equity_payout_initial_year']:
                years_since_start = current_year - self.inp['company_equity_payout_initial_year']
                if years_since_start < self.inp['company_equity_payback_period_years']:
                    equity_payout = (self.inp['company_equity_value'] 
                                     / self.inp['company_equity_payback_period_years'])

            # 2. Add Contributions or Equity Payout
            if (current_year >= self.inp['company_equity_payout_initial_year'] 
                and year_idx < self.inp['company_equity_payback_period_years']):
                savings += equity_payout
            else:
                savings += self.inp['annual_contribution']

            # Add home downsizing cash infusion if applicable
            if current_year == self.inp.get('home_downsizing_year', 0):
                savings += self.inp.get('home_downsizing_estim_cash_infusion', 0)

            # 3. Apply Investment Returns
            if age > self.inp['current_age']:
                rate = (simulation_returns[year_idx] 
                        if simulation_returns is not None 
                        else self.inp['expected_annual_return_rate'])
                savings *= (1 + rate)

            # 4. Social Security (only after eligibility age)
            ss_income = 0
            if age >= self.inp['expected_age_of_social_security_benefits']:
                ss_income = self.inp['expected_retirement_income_social_security']

            # 5. Expenses (inflation adjusted) and SS
            expenses = self.get_inflation_adjusted_expense(age)
            savings -= expenses
            savings += ss_income

            # Store detailed calculation data for this year
            self.cd.append({
                "Age": age,
                "Year": current_year,
                "Equity_Payout": equity_payout,
                "Home_Downsizing_Cash_Infusion": self.inp.get('home_downsizing_estim_cash_infusion', 0) if current_year == self.inp.get('home_downsizing_year', 0) else 0,
                "Contribution_Added": equity_payout if equity_payout > 0 else self.inp['annual_contribution'],
                "Return_Rate_Applied": rate if age > self.inp['current_age'] else 0,
                "Expenses": expenses,
                "SS_Income": ss_income,
                "Net_Value_End_OfYear": savings
            })

            age += 1
            current_year += 1
            year_idx += 1

        return pd.DataFrame(self.cd)