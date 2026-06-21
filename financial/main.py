# main.py
import json
import os
import numpy as np
import matplotlib.pyplot as plt
from calculator import RetirementPlanner
from tabulate import tabulate


def load_inputs_from_json(filename="/home/ts/dev/py/financial/model_data.json"):
    """Loads configuration data directly from a JSON file."""
    if not os.path.exists(filename):
        raise FileNotFoundError(f"Could not find {filename} in the current directory.")
        
    with open(filename, 'r') as file:
        data = json.load(file)
    
    # Inject historical asset volatility metric if missing from JSON
    if 'expected_return_std_dev' not in data:
        data['expected_return_std_dev'] = 12.0
        
    return data


def run_monte_carlo(user_inputs, num_simulations=5000):
    planner = RetirementPlanner(user_inputs)
    
    # Calculate timeline boundaries
    years_to_simulate = user_inputs['expected_life_expectancy'] - user_inputs['current_age'] + 1
    final_balances = []
    
    print(f"Running {num_simulations} Monte Carlo simulations using JSON data...")
    
    for _ in range(num_simulations):
        # Build standard deviation curve based on user_inputs
        random_returns = np.random.normal(
            loc=user_inputs['expected_annual_return_rate'], 
            scale=user_inputs['expected_return_std_dev'], 
            size=years_to_simulate
        )
        
        df = planner.run_projection(simulation_returns=random_returns)
        final_balances.append(df.iloc[-1]['Net_Value_End_OfYear'])
        
    return np.array(final_balances)


def plot_results(balances):
    balances_in_millions = balances / 1_000_000
    
    plt.figure(figsize=(10, 6))
    plt.hist(balances_in_millions, bins=50, edgecolor='black', color='skyblue', alpha=0.7)
    
    plt.axvline(np.percentile(balances_in_millions, 50), color='red', linestyle='dashed', linewidth=2, label='Median Scenario')
    plt.axvline(np.percentile(balances_in_millions, 10), color='orange', linestyle='dotted', linewidth=2, label='Downside Risk (10th Percentile)')
    
    plt.title('Monte Carlo Simulation: Asset Value Distribution at Max Life Expectancy', fontsize=12)
    plt.xlabel('Net Value (In Millions $)', fontsize=10)
    plt.ylabel('Scenario Density Count', fontsize=10)
    plt.grid(axis='y', alpha=0.3)
    plt.legend()
    plt.show()


def gen_report(inputs, report_filename="/home/ts/dev/py/financial/results.md"):
    """
    Generates a deterministic financial report, completely overwriting old runs.
    Both tables are wrapped in markdown code blocks to preserve crisp visual spacing.
    """
    with open(report_filename, 'w') as f:
        
        # --- SECTION 1: WRITE HEADERS & INPUTS ---
        f.write("# Retirement Simulation Analysis Report\n\n")
        f.write("--- LOADED INPUTS FROM JSON ---\n")
        
        # Format the parameters into clean comma-separated strings
        formatted_inputs = [
            (key, f"{int(value):,d}" if isinstance(value, (int, float)) else str(value)) 
            for key, value in inputs.items()
        ]
        
        f.write("```text\n")
        f.write(tabulate(
            formatted_inputs, 
            headers=["Parameter", "Value"], 
            tablefmt="simple", 
            disable_numparse=True
        ))
        f.write("\n```\n\n")
        
        # --- SECTION 2: CALCULATE PROJECTIONS ---
        planner = RetirementPlanner(inputs)
        base_projection = planner.run_projection()
        
        # Get the original column names as headers
        headers = list(base_projection.columns)
        
        # Convert rows to absolute string matrices, escaping numeric auto-formatting
        formatted_rows = []
        for _, row in base_projection.iterrows():
            formatted_row = [f"{int(val):,d}" if isinstance(val, (int, float)) else str(val) for val in row]
            formatted_rows = formatted_rows + [formatted_row]
            
        # --- SECTION 3: WRITE OUT CLEAN TABLE ENCLOSED IN CODE BLOCKS ---
        f.write("--- BASE PROJECTION (Deterministic) ---\n")
        f.write("```text\n")
        
        f.write(tabulate(
            formatted_rows, 
            headers=headers, 
            tablefmt='simple', 
            showindex=False, 
            disable_numparse=True
        ))
        f.write("\n```\n")

    print(f"Success! Overwrote and updated report at: {report_filename}")


if __name__ == "__main__":
    # Generate report by calling gen_report() with inputs loaded from JSON
    inputs = load_inputs_from_json()
    gen_report(inputs)
    
    # 2. Run stochastic data loops. What does this mean? It means we are running a Monte Carlo simulation to generate a distribution of possible outcomes based on random variations in investment returns. This helps us understand the range of potential future financial scenarios and assess risk.
    final_net_worths = run_monte_carlo(inputs)
    
    # 3. Print output metrics
    print(f"\n--- SIMULATION METRICS FROM JSON ---")
    print(f"Median Expected Balance: ${np.median(final_net_worths):,.2f}")
    print(f"10th Percentile Risk Floor: ${np.percentile(final_net_worths, 10):,.2f}")
    print(f"Probability of Capital Depletion: {(final_net_worths < 0).mean() * 100:.2f}%")
    
    # 4. Display distribution chart
    plot_results(final_net_worths)

