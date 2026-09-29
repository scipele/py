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
        # Generates cash flow projection.
        # If simulation_returns (list of random rates) is provided, runs stochastic.
        # Otherwise runs deterministic (flat rate).
        # Populates self.cd with detailed yearly calculation data.
        
        current_year = 2026
        age = self.inp['current_age']

        savings = (
            self.inp['current_savings_other'] +
            self.inp['current_savings_401k']
        )

        # Company equity payout calculation
        equity_value = self.inp['company_equity_value']
        equity_upfront_percent = self.inp.get(
            'company_equity_upfront_percent',
            0.25
        )
        equity_upfront_year = self.inp.get(
            'company_equity_upfront_year',
            2026
        )
        equity_remaining_payout_years = self.inp.get(
            'company_equity_remaining_payout_years',
            5
        )

        equity_upfront_payment = (
            equity_value * equity_upfront_percent
        )

        equity_remaining = (
            equity_value - equity_upfront_payment
        )

        equity_payout_per_year = (
            equity_remaining / equity_remaining_payout_years
        )

        self.cd = []
        year_idx = 0
        investment_return = 0

        tax_rate = self.inp.get(
            'estimated_retirement_tax_rate',
            0.0
        )

        # Use retirement age if provided, otherwise use current age
        retirement_age = self.inp.get(
            'expected_retirement_age',
            self.inp['current_age']
        )

        while age <= self.inp['expected_life_expectancy']:

            # --------------------------------------------------------
            # 1. Equity Payout
            # --------------------------------------------------------

            equity_payment = 0

            # 25% upfront payment in 2026
            if current_year == equity_upfront_year:

                equity_payment = equity_upfront_payment

            # Remaining 75% paid over the following 5 years
            elif (
                current_year > equity_upfront_year
                and current_year <= (
                    equity_upfront_year +
                    equity_remaining_payout_years
                )
            ):

                equity_payment = equity_payout_per_year

            else:

                equity_payment = self.inp['annual_contribution']

            savings += equity_payment

            # --------------------------------------------------------
            # 2. Home Downsizing Cash Infusion
            # --------------------------------------------------------

            home_downsize_cash = 0

            if current_year == self.inp.get(
                'home_downsizing_year',
                0
            ):

                home_downsize_cash = self.inp.get(
                    'home_downsizing_estim_cash_infusion',
                    0
                )

                savings += home_downsize_cash

            # --------------------------------------------------------
            # 3. Child Expenses
            # --------------------------------------------------------

            child_expenses = 0

            if year_idx <= self.inp.get(
                'expected_duration_of_child_expenses',
                0
            ):

                child_expenses = self.inp.get(
                    'expected_child_expenses',
                    0
                )

                savings -= child_expenses

            # --------------------------------------------------------
            # 4. Investment Returns
            # --------------------------------------------------------

            investment_return = 0

            if age > self.inp['current_age']:

                rate = (
                    simulation_returns[year_idx]
                    if simulation_returns is not None
                    else self.inp['expected_annual_return_rate']
                )

                investment_return = savings * rate

                savings *= (1 + rate)

            # --------------------------------------------------------
            # 5. Social Security
            # --------------------------------------------------------

            ss_income = 0

            if age >= self.inp[
                'expected_age_of_social_security_benefits'
            ]:

                years_since_eligibility = (
                    age -
                    self.inp[
                        'expected_age_of_social_security_benefits'
                    ]
                )

                ss_income = (
                    self.inp[
                        'expected_initial_income_social_security'
                    ]
                    *
                    (
                        1 +
                        self.inp[
                            'expected_annual_inflation_rate'
                        ]
                    )
                    ** years_since_eligibility
                )

            # --------------------------------------------------------
            # 6. Retirement Expenses
            # --------------------------------------------------------

            expenses = self.get_inflation_adjusted_expense(age)

            # Gross up withdrawal for taxes
            if age >= retirement_age and tax_rate > 0:

                gross_withdrawal = (
                    expenses / (1 - tax_rate)
                )

            else:

                gross_withdrawal = expenses

            savings -= gross_withdrawal

            savings += ss_income

            # --------------------------------------------------------
            # 7. Store Detailed Calculation Data
            # --------------------------------------------------------

            self.cd.append({
                "Age": age,
                "Year": current_year,

                "Home_Downsz": home_downsize_cash,

                "Child_Exp": child_expenses,

                "Equity_Pmt": equity_payment,

                "Expenses": expenses,

                "Gross_Withdrawal": gross_withdrawal,

                "SS_Income": ss_income,

                "Investment_Return": investment_return,

                "Net_Val_EOY": savings
            })

            # --------------------------------------------------------
            # 8. Move to Next Year
            # --------------------------------------------------------

            age += 1
            current_year += 1
            year_idx += 1

        return pd.DataFrame(self.cd)