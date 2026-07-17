"""Economic comparison: keep 2024 Ford F-150 vs buy a new Tesla Model Y.

The model computes annual ownership cash flows and discounts them to present
value using a 6% opportunity-cost rate (net growth rate of other investments).

Outputs:
- Console summary of assumptions, annual costs, and NPV totals
- A bar chart comparing total NPV cost of each option
- A markdown report with charts and detailed NPV component breakdown

Notes:
- Values below are editable assumptions. Update them as needed.
- This is a practical decision model from "today forward".
"""

from __future__ import annotations

from dataclasses import dataclass
import math
from pathlib import Path
from typing import Dict, List

import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages
import numpy as np


@dataclass
class VehicleScenario:
	name: str
	annual_miles: float
	years: float
	annual_insurance: float
	annual_registration: float
	annual_maintenance_base: float
	maintenance_growth_rate: float

	# Energy consumption and price assumptions.
	mpg_city: float | None = None
	gas_price_per_gallon: float | None = None
	mi_per_kwh: float | None = None
	electricity_price_per_kwh: float | None = None

	# Cash flows at time 0 and end of analysis.
	initial_cash_flow: float = 0.0
	residual_value_end: float = 0.0

	# Optional technology costs (e.g., self-driving package/subscription).
	upfront_option_cost: float = 0.0
	annual_option_cost: float = 0.0


def discounted_value(amount: float, year: float, discount_rate: float) -> float:
	"""Discount a future amount to present value at the given year index."""
	return amount / ((1 + discount_rate) ** year)


def annual_energy_cost(s: VehicleScenario) -> float:
	"""Compute annual fuel or electricity cost based on configured efficiency."""
	if s.mpg_city and s.gas_price_per_gallon:
		gallons = s.annual_miles / s.mpg_city
		return gallons * s.gas_price_per_gallon
	if s.mi_per_kwh and s.electricity_price_per_kwh:
		kwh = s.annual_miles / s.mi_per_kwh
		return kwh * s.electricity_price_per_kwh
	raise ValueError(f"Scenario '{s.name}' is missing energy assumptions.")


def build_annual_cost_breakdown(
	s: VehicleScenario,
) -> Dict[str, List[float]]:
	"""Build period-by-period nominal cost arrays by component.

	Supports a fractional final year when analysis horizon is not an integer.
	"""
	energy = annual_energy_cost(s)
	maintenance = []
	insurance = []
	registration = []
	option_cost = []
	period_end_years = []

	full_years = int(math.floor(s.years))
	partial_year = s.years - full_years

	for year in range(1, full_years + 1):
		growth_factor = (1 + s.maintenance_growth_rate) ** (year - 1)
		maintenance.append(s.annual_maintenance_base * growth_factor)
		insurance.append(s.annual_insurance)
		registration.append(s.annual_registration)
		option_cost.append(s.annual_option_cost)
		period_end_years.append(float(year))

	if partial_year > 1e-9:
		growth_factor = (1 + s.maintenance_growth_rate) ** full_years
		maintenance.append(s.annual_maintenance_base * growth_factor * partial_year)
		insurance.append(s.annual_insurance * partial_year)
		registration.append(s.annual_registration * partial_year)
		option_cost.append(s.annual_option_cost * partial_year)
		period_end_years.append(s.years)

	return {
		"energy": [energy] * full_years + ([energy * partial_year] if partial_year > 1e-9 else []),
		"maintenance": maintenance,
		"insurance": insurance,
		"registration": registration,
		"option_cost": option_cost,
		"period_end_years": period_end_years,
	}


def build_annual_net_components(s: VehicleScenario) -> Dict[str, List[float]]:
	"""Build time-indexed components used for net annual cost charts.

	Year 0 includes initial cash flow.
	Final period includes residual value as a negative cost (credit).
	"""
	base = build_annual_cost_breakdown(s)
	period_end_years = base["period_end_years"]
	time_years = [0.0] + period_end_years
	count = len(time_years)

	components = {
		"time_years": time_years,
		"initial": [0.0] * count,
		"energy": [0.0] * count,
		"maintenance": [0.0] * count,
		"insurance": [0.0] * count,
		"registration": [0.0] * count,
		"option_cost": [0.0] * count,
		"residual_credit": [0.0] * count,
	}

	components["initial"][0] = s.initial_cash_flow + s.upfront_option_cost

	for idx in range(1, count):
		components["energy"][idx] = base["energy"][idx - 1]
		components["maintenance"][idx] = base["maintenance"][idx - 1]
		components["insurance"][idx] = base["insurance"][idx - 1]
		components["registration"][idx] = base["registration"][idx - 1]
		components["option_cost"][idx] = base["option_cost"][idx - 1]

	components["residual_credit"][count - 1] = -s.residual_value_end
	return components


def npv_total_cost(
	s: VehicleScenario,
	discount_rate: float,
) -> Dict[str, float]:
	"""Return NPV totals by cost category and overall NPV total cost."""
	breakdown = build_annual_cost_breakdown(s)
	period_end_years = breakdown["period_end_years"]

	npv_components: Dict[str, float] = {
		"initial": s.initial_cash_flow + s.upfront_option_cost,
		"energy": 0.0,
		"maintenance": 0.0,
		"insurance": 0.0,
		"registration": 0.0,
		"option_cost": 0.0,
		"residual_credit": -discounted_value(s.residual_value_end, s.years, discount_rate),
	}

	for idx, period_end in enumerate(period_end_years):
		npv_components["energy"] += discounted_value(breakdown["energy"][idx], period_end, discount_rate)
		npv_components["maintenance"] += discounted_value(
			breakdown["maintenance"][idx], period_end, discount_rate
		)
		npv_components["insurance"] += discounted_value(breakdown["insurance"][idx], period_end, discount_rate)
		npv_components["registration"] += discounted_value(
			breakdown["registration"][idx], period_end, discount_rate
		)
		npv_components["option_cost"] += discounted_value(
			breakdown["option_cost"][idx], period_end, discount_rate
		)

	npv_components["total"] = sum(npv_components.values())
	return npv_components


def print_report(
	discount_rate: float,
	f150: VehicleScenario,
	tesla: VehicleScenario,
	f150_npv: Dict[str, float],
	tesla_npv: Dict[str, float],
) -> None:
	"""Print a concise text report for the comparison."""
	print("\nEconomic Evaluation: Keep F-150 vs Buy Tesla Model Y")
	print("=" * 62)
	print(f"Discount/Opportunity Rate (NPV): {discount_rate * 100:.2f}%")
	print(f"Analysis Horizon: {f150.years:.2f} years")
	print(f"Annual Miles: {f150.annual_miles:,.0f} (mostly city)")

	print("\nAssumptions in this run:")
	print(f"- Current truck: 2024 Ford F-150, VIN 1FTFW3L88RKF09640, purchase price was $60,000")
	print(f"- Keep F-150 initial opportunity cost (value kept in truck): ${f150.initial_cash_flow:,.0f}")
	print(f"- New Tesla Model Y purchase net cash outflow today: ${tesla.initial_cash_flow:,.0f}")
	if tesla.upfront_option_cost > 0 or tesla.annual_option_cost > 0:
		print(f"- Tesla self-driving upfront option cost: ${tesla.upfront_option_cost:,.0f}")
		print(f"- Tesla self-driving annual option cost: ${tesla.annual_option_cost:,.0f}")

	def show_npv(label: str, data: Dict[str, float]) -> None:
		print(f"\n{label} - NPV Cost Breakdown")
		print(f"  Initial cash flow:   ${data['initial']:>12,.0f}")
		print(f"  Energy (fuel/power): ${data['energy']:>12,.0f}")
		print(f"  Maintenance:         ${data['maintenance']:>12,.0f}")
		print(f"  Insurance:           ${data['insurance']:>12,.0f}")
		print(f"  Registration:        ${data['registration']:>12,.0f}")
		print(f"  Option cost:         ${data['option_cost']:>12,.0f}")
		print(f"  Less residual value: ${data['residual_credit']:>12,.0f}")
		print(f"  TOTAL NPV COST:      ${data['total']:>12,.0f}")

	show_npv(f150.name, f150_npv)
	show_npv(tesla.name, tesla_npv)

	difference = tesla_npv["total"] - f150_npv["total"]
	print("\nDecision signal (lower NPV cost is better):")
	if difference < 0:
		print(f"- Tesla is cheaper by ${abs(difference):,.0f} in NPV terms.")
	elif difference > 0:
		print(f"- Keeping F-150 is cheaper by ${difference:,.0f} in NPV terms.")
	else:
		print("- Both options are tied in NPV cost.")


def plot_yearly_stacked_comparison(
	f150: VehicleScenario,
	tesla: VehicleScenario,
	output_file: str,
) -> None:
	"""Create grouped stacked bars by year for both options."""
	f150_comp = build_annual_net_components(f150)
	tesla_comp = build_annual_net_components(tesla)
	years = np.array(f150_comp["time_years"], dtype=float)
	width = 0.42

	fig, ax = plt.subplots(figsize=(14, 7))

	categories = [
		("initial", "Initial", "#1B4F72"),
		("energy", "Energy", "#CB4335"),
		("maintenance", "Maintenance", "#148F77"),
		("insurance", "Insurance", "#9A7D0A"),
		("registration", "Registration", "#7D3C98"),
		("option_cost", "Option Cost", "#1F618D"),
		("residual_credit", "Residual Credit", "#566573"),
	]

	left_bottom = np.zeros_like(years, dtype=float)
	right_bottom = np.zeros_like(years, dtype=float)
	left_bottom_neg = np.zeros_like(years, dtype=float)
	right_bottom_neg = np.zeros_like(years, dtype=float)

	for key, label, color in categories:
		left_vals = np.array(f150_comp[key], dtype=float)
		right_vals = np.array(tesla_comp[key], dtype=float)

		left_pos = np.where(left_vals > 0, left_vals, 0.0)
		left_neg = np.where(left_vals < 0, left_vals, 0.0)
		right_pos = np.where(right_vals > 0, right_vals, 0.0)
		right_neg = np.where(right_vals < 0, right_vals, 0.0)

		ax.bar(years - width / 2, left_pos, width=width, bottom=left_bottom, color=color, alpha=0.9)
		ax.bar(years - width / 2, left_neg, width=width, bottom=left_bottom_neg, color=color, alpha=0.9)
		ax.bar(
			years + width / 2,
			right_pos,
			width=width,
			bottom=right_bottom,
			color=color,
			hatch="//",
			alpha=0.55,
		)
		ax.bar(
			years + width / 2,
			right_neg,
			width=width,
			bottom=right_bottom_neg,
			color=color,
			hatch="//",
			alpha=0.55,
		)

		left_bottom += left_pos
		left_bottom_neg += left_neg
		right_bottom += right_pos
		right_bottom_neg += right_neg

	legend_handles = [
		plt.Rectangle((0, 0), 1, 1, fc="#95A5A6", alpha=0.9, label="Keep F-150"),
		plt.Rectangle((0, 0), 1, 1, fc="#95A5A6", hatch="//", alpha=0.55, label="Buy Model Y"),
	]
	legend_handles.extend(
		[plt.Rectangle((0, 0), 1, 1, fc=color, label=label) for _, label, color in categories]
	)

	ax.legend(handles=legend_handles, ncol=2, fontsize=9)
	ax.set_title("Net Cost Per Year by Option (Stacked Components)")
	ax.set_xlabel("Year")
	ax.set_ylabel("Nominal Net Cost (USD)")
	ax.set_xticks(years)
	ax.set_xticklabels([f"{yr:.2f}" if abs(yr - round(yr)) > 1e-9 else f"{int(round(yr))}" for yr in years])
	ax.grid(axis="y", linestyle="--", alpha=0.35)
	ax.axhline(0, color="black", linewidth=0.9)

	fig.tight_layout()
	fig.savefig(output_file, dpi=140)
	print(f"Saved chart to: {output_file}")
	plt.close(fig)


def plot_yearly_stacked_option(
	scenario: VehicleScenario,
	output_file: str,
) -> None:
	"""Create a stacked annual net cost chart for one option."""
	comp = build_annual_net_components(scenario)
	years = np.array(comp["time_years"], dtype=float)

	fig, ax = plt.subplots(figsize=(12, 6))
	categories = [
		("initial", "Initial", "#1B4F72"),
		("energy", "Energy", "#CB4335"),
		("maintenance", "Maintenance", "#148F77"),
		("insurance", "Insurance", "#9A7D0A"),
		("registration", "Registration", "#7D3C98"),
		("option_cost", "Option Cost", "#1F618D"),
		("residual_credit", "Residual Credit", "#566573"),
	]

	bottom_pos = np.zeros_like(years, dtype=float)
	bottom_neg = np.zeros_like(years, dtype=float)
	for key, label, color in categories:
		vals = np.array(comp[key], dtype=float)
		vals_pos = np.where(vals > 0, vals, 0.0)
		vals_neg = np.where(vals < 0, vals, 0.0)
		ax.bar(years, vals_pos, bottom=bottom_pos, color=color, width=0.65, label=label)
		ax.bar(years, vals_neg, bottom=bottom_neg, color=color, width=0.65)
		bottom_pos += vals_pos
		bottom_neg += vals_neg

	ax.set_title(f"{scenario.name} - Net Cost Per Year (Stacked)")
	ax.set_xlabel("Year")
	ax.set_ylabel("Nominal Net Cost (USD)")
	ax.set_xticks(years)
	ax.set_xticklabels([f"{yr:.2f}" if abs(yr - round(yr)) > 1e-9 else f"{int(round(yr))}" for yr in years])
	ax.grid(axis="y", linestyle="--", alpha=0.35)
	ax.axhline(0, color="black", linewidth=0.9)
	ax.legend()

	fig.tight_layout()
	fig.savefig(output_file, dpi=140)
	print(f"Saved chart to: {output_file}")
	plt.close(fig)


def write_markdown_report(
	report_file: str,
	discount_rate: float,
	f150: VehicleScenario,
	tesla: VehicleScenario,
	f150_npv: Dict[str, float],
	tesla_npv: Dict[str, float],
	comparison_chart: str,
	f150_chart: str,
	tesla_chart: str,
) -> None:
	"""Write a markdown report with assumptions, results, and chart embeds."""
	diff = tesla_npv["total"] - f150_npv["total"]
	if diff < 0:
		decision_line = f"Tesla is cheaper by ${abs(diff):,.0f} in NPV terms."
	elif diff > 0:
		decision_line = f"Keeping the F-150 is cheaper by ${diff:,.0f} in NPV terms."
	else:
		decision_line = "Both options are tied in NPV cost."

	content = f"""# Economic Evaluation Report: F-150 vs Tesla Model Y

## Key Inputs
- Analysis horizon: **{f150.years:.2f} years**
- Annual mileage: **{f150.annual_miles:,.0f} miles/year** (mostly city)
- NPV discount/opportunity rate: **{discount_rate * 100:.2f}%**
- Current truck status: **Paid off (no loan payment included)**
- Tesla self-driving upfront option cost: **${tesla.upfront_option_cost:,.0f}**
- Tesla self-driving annual option cost: **${tesla.annual_option_cost:,.0f}/yr**

## Vehicle Context
- 2024 Ford F-150, 4WD, 3.6L V6, 36,543 miles
- VIN: 1FTFW3L88RKF09640
- Actual historical purchase price: $60,000

## NPV Result Summary
| Option | Total NPV Cost |
|---|---:|
| {f150.name} | ${f150_npv['total']:,.0f} |
| {tesla.name} | ${tesla_npv['total']:,.0f} |

**Decision signal (lower is better):** {decision_line}

## Comparison Chart
![Net Annual Cost Comparison]({comparison_chart})

## Option Chart: Keep F-150
![F-150 Net Annual Stacked]({f150_chart})

## Option Chart: Buy Tesla Model Y
![Tesla Net Annual Stacked]({tesla_chart})

## Chart Notes
- X-axis is year index (Year 0 to Year {f150.years:.2f}).
- Stacked segments show Initial, Energy, Maintenance, Insurance, Registration, and Residual Credit.
- Stacked segments show Initial, Energy, Maintenance, Insurance, Registration, Option Cost, and Residual Credit.
- Year 0 captures one-time initial cash flow; final year includes residual value credit.

## Detailed NPV Components
| Component | Keep F-150 | Buy Model Y |
|---|---:|---:|
| Initial cash flow | ${f150_npv['initial']:,.0f} | ${tesla_npv['initial']:,.0f} |
| Energy | ${f150_npv['energy']:,.0f} | ${tesla_npv['energy']:,.0f} |
| Maintenance | ${f150_npv['maintenance']:,.0f} | ${tesla_npv['maintenance']:,.0f} |
| Insurance | ${f150_npv['insurance']:,.0f} | ${tesla_npv['insurance']:,.0f} |
| Registration | ${f150_npv['registration']:,.0f} | ${tesla_npv['registration']:,.0f} |
| Option cost | ${f150_npv['option_cost']:,.0f} | ${tesla_npv['option_cost']:,.0f} |
| Residual credit | ${f150_npv['residual_credit']:,.0f} | ${tesla_npv['residual_credit']:,.0f} |
| **Total NPV cost** | **${f150_npv['total']:,.0f}** | **${tesla_npv['total']:,.0f}** |
"""

	Path(report_file).write_text(content, encoding="utf-8")
	print(f"Saved report to: {report_file}")


def write_pdf_report(
	report_file: str,
	discount_rate: float,
	f150: VehicleScenario,
	tesla: VehicleScenario,
	f150_npv: Dict[str, float],
	tesla_npv: Dict[str, float],
	comparison_chart_path: Path,
	f150_chart_path: Path,
	tesla_chart_path: Path,
) -> None:
	"""Write a multi-page PDF report with embedded chart images."""
	diff = tesla_npv["total"] - f150_npv["total"]
	if diff < 0:
		decision_line = f"Tesla is cheaper by ${abs(diff):,.0f} in NPV terms."
	elif diff > 0:
		decision_line = f"Keeping the F-150 is cheaper by ${diff:,.0f} in NPV terms."
	else:
		decision_line = "Both options are tied in NPV cost."

	with PdfPages(report_file) as pdf:
		# Page 1: summary text and key numbers.
		fig, ax = plt.subplots(figsize=(8.27, 11.69))
		ax.axis("off")

		summary_lines = [
			"Economic Evaluation Report: F-150 vs Tesla Model Y",
			"",
			f"Analysis horizon: {f150.years:.2f} years",
			f"Annual mileage: {f150.annual_miles:,.0f} miles/year",
			f"NPV discount rate: {discount_rate * 100:.2f}%",
			"",
			"Total NPV Cost",
			f"- {f150.name}: ${f150_npv['total']:,.0f}",
			f"- {tesla.name}: ${tesla_npv['total']:,.0f}",
			"",
			f"Decision signal: {decision_line}",
			"",
			"Detailed NPV Components",
			f"- Initial cash flow: ${f150_npv['initial']:,.0f} | ${tesla_npv['initial']:,.0f}",
			f"- Energy: ${f150_npv['energy']:,.0f} | ${tesla_npv['energy']:,.0f}",
			f"- Maintenance: ${f150_npv['maintenance']:,.0f} | ${tesla_npv['maintenance']:,.0f}",
			f"- Insurance: ${f150_npv['insurance']:,.0f} | ${tesla_npv['insurance']:,.0f}",
			f"- Registration: ${f150_npv['registration']:,.0f} | ${tesla_npv['registration']:,.0f}",
			f"- Option cost: ${f150_npv['option_cost']:,.0f} | ${tesla_npv['option_cost']:,.0f}",
			f"- Residual credit: ${f150_npv['residual_credit']:,.0f} | ${tesla_npv['residual_credit']:,.0f}",
		]

		ax.text(
			0.03,
			0.98,
			"\n".join(summary_lines),
			va="top",
			ha="left",
			fontsize=11,
			family="monospace",
		)
		pdf.savefig(fig, bbox_inches="tight")
		plt.close(fig)

		# Pages 2..N: embedded images for each chart.
		chart_pages = [
			("Net Annual Cost Comparison", comparison_chart_path),
			("Keep F-150: Net Cost Per Year", f150_chart_path),
			("Buy Tesla Model Y: Net Cost Per Year", tesla_chart_path),
		]

		for title, image_path in chart_pages:
			fig, ax = plt.subplots(figsize=(11, 8.5))
			ax.axis("off")
			ax.set_title(title, fontsize=14, pad=12)
			image = plt.imread(image_path)
			ax.imshow(image)
			pdf.savefig(fig, bbox_inches="tight")
			plt.close(fig)

	print(f"Saved PDF report to: {report_file}")


def main() -> None:
	# User-requested investment growth/discount rate for NPV.
	discount_rate = 0.06

	# Core usage assumption.
	annual_miles = 15_000
	years = 7

	# Assumptions for current truck value and Tesla purchase economics.
	# These are estimates and should be adjusted to your actual quotes.
	current_f150_market_value = 42_000
	tesla_purchase_price = 45_000
	tesla_fees_and_tax = 3_500
	home_charger_install = 1_500

	# Optional self-driving assumptions.
	# Set include_self_driving_feature = False to disable all option costs.
	include_self_driving_feature = True
	tesla_self_driving_upfront_cost = 0  # Example one-time package cost
	tesla_self_driving_annual_subscription = 999  # Example annual subscription cost

	# Insurance effect from self-driving (negative means savings, positive means increase).
	# Example: -150 means $150/year insurance savings.
	tesla_insurance_adjustment_with_self_driving = 0

	# If buying Tesla, this model assumes you can sell the F-150 now.
	tesla_net_initial_outflow = tesla_purchase_price + tesla_fees_and_tax + home_charger_install - current_f150_market_value

	keep_f150 = VehicleScenario(
		name="Keep 2024 Ford F-150",
		annual_miles=annual_miles,
		years=years,
		annual_insurance=2_100,
		annual_registration=300,
		annual_maintenance_base=1_250,
		maintenance_growth_rate=0.04,
		mpg_city=18.0,
		gas_price_per_gallon=3.70,
		# Paid off truck: no new initial cash outflow to keep it.
		initial_cash_flow=0.0,
		residual_value_end=12_000,
	)

	buy_tesla = VehicleScenario(
		name="Buy New Tesla Model Y",
		annual_miles=annual_miles,
		years=years,
		annual_insurance=2_500 + (tesla_insurance_adjustment_with_self_driving if include_self_driving_feature else 0),
		annual_registration=550,
		annual_maintenance_base=550,
		maintenance_growth_rate=0.03,
		mi_per_kwh=3.6,
		electricity_price_per_kwh=0.138,
		initial_cash_flow=tesla_net_initial_outflow,
		residual_value_end=18_000,
		upfront_option_cost=tesla_self_driving_upfront_cost if include_self_driving_feature else 0,
		annual_option_cost=tesla_self_driving_annual_subscription if include_self_driving_feature else 0,
	)

	f150_npv = npv_total_cost(keep_f150, discount_rate)
	tesla_npv = npv_total_cost(buy_tesla, discount_rate)

	print_report(discount_rate, keep_f150, buy_tesla, f150_npv, tesla_npv)

	comparison_chart = "tesla_vs_truck_npv.png"
	f150_chart = "f150_net_cost_by_year_stacked.png"
	tesla_chart = "tesla_net_cost_by_year_stacked.png"
	output_dir = Path("/home/dev/py/economics/output")
	output_dir.mkdir(parents=True, exist_ok=True)

	comparison_chart_path = output_dir / comparison_chart
	f150_chart_path = output_dir / f150_chart
	tesla_chart_path = output_dir / tesla_chart
	report_file = output_dir / "tesla_vs_truck_report.md"
	pdf_report_file = output_dir / "tesla_vs_truck_report.pdf"

	plot_yearly_stacked_comparison(keep_f150, buy_tesla, str(comparison_chart_path))
	plot_yearly_stacked_option(keep_f150, str(f150_chart_path))
	plot_yearly_stacked_option(buy_tesla, str(tesla_chart_path))
	write_markdown_report(
		str(report_file),
		discount_rate,
		keep_f150,
		buy_tesla,
		f150_npv,
		tesla_npv,
		comparison_chart,
		f150_chart,
		tesla_chart,
	)
	write_pdf_report(
		str(pdf_report_file),
		discount_rate,
		keep_f150,
		buy_tesla,
		f150_npv,
		tesla_npv,
		comparison_chart_path,
		f150_chart_path,
		tesla_chart_path,
	)


if __name__ == "__main__":
	main()
