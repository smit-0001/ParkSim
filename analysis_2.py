import matplotlib
matplotlib.use('Agg') # FIX: Force non-interactive backend (prevents freezing)
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from simulation_engine import JFKSimulation

# Configuration
POLICIES = ["Baseline", "Nearest", "CostMin", "Occupancy", "Reservation"]
TRAFFIC_FILE = "traffic_arrival_log.csv"

def run_experiment_suite():
    print(f"--- PHASE 5: Running Analysis Suite on {TRAFFIC_FILE} ---")
    all_records = []
    occupancy_history = {} # Store time-series data per policy
    
    for policy in POLICIES:
        print(f"  > Simulating Policy: {policy}...")
        sim = JFKSimulation("parking_facilities.csv", TRAFFIC_FILE, "network_distances.csv")
        sim.load_events()
        sim.run(policy_name=policy)
        
        # 1. Capture Time-Series Log
        occupancy_history[policy] = pd.DataFrame(sim.history)

        # 2. Capture Per-Vehicle Data
        for v_id, vehicle in sim.vehicle_registry.items():
            if vehicle.status == "Blocked":
                travel_time = 60.0 # Penalty
                is_blocked = 1
                parking_fee = 0.0
                assigned_lot = "Blocked"
            else:
                travel_time = sim.get_travel_time(vehicle.assigned_lot, vehicle.target_terminal)
                is_blocked = 0
                parking_fee = (vehicle.duration / 30) * 10 # Estimate
                assigned_lot = vehicle.assigned_lot
            
            all_records.append({
                "Policy": policy,
                "VehicleID": v_id,
                "TravelTime": travel_time,
                "IsBlocked": is_blocked,
                "ParkingFee": parking_fee,
                "AssignedLot": assigned_lot
            })
            
    return pd.DataFrame(all_records), occupancy_history

def generate_requested_charts(df, history_dict):
    print("\nGenerating Requested Charts...")
    sns.set_theme(style="whitegrid")
    
    # 1. Line chart – Lot Occupancy vs Time (Using 'CostMin' as representative)
    # [cite_start]Ref: [cite: 41-42]
    plt.figure(figsize=(12, 6))
    hist_df = history_dict['CostMin']
    # Melt to long format for plotting
    melted = hist_df.melt('Time', var_name='Lot', value_name='Occupancy')
    sns.lineplot(data=melted, x='Time', y='Occupancy', hue='Lot')
    plt.title("Chart 1: Lot Occupancy vs. Time (Cost-Minimizing Policy)")
    plt.xlabel("Simulation Time (min)")
    plt.ylabel("Vehicles Parked")
    plt.savefig("chart_1_occupancy_time.png")
    print("  > Saved: chart_1_occupancy_time.png")

    # 2. Bar chart – Blocking Probability per Policy
    # [cite_start]Ref: [cite: 277]
    plt.figure(figsize=(10, 6))
    block_rates = df.groupby("Policy")["IsBlocked"].mean() * 100
    ax = sns.barplot(x=block_rates.index, y=block_rates.values, hue=block_rates.index, palette="viridis", legend=False)
    plt.title("Chart 2: Blocking Probability per Policy")
    plt.ylabel("Blocking Rate (%)")
    for i in ax.containers: ax.bar_label(i, fmt='%.1f%%')
    plt.savefig("chart_2_blocking_prob.png")
    print("  > Saved: chart_2_blocking_prob.png")

    # 3. Grouped Bar Chart – Search and Access Times per Policy
    # [cite_start]Ref: [cite: 278-279]
    # Filter out blocked cars to show actual access times
    success_df = df[df["IsBlocked"] == 0]
    plt.figure(figsize=(10, 6))
    sns.barplot(data=success_df, x="Policy", y="TravelTime", hue="Policy", palette="Set2", legend=False)
    plt.title("Chart 3: Average Access Time per Policy")
    plt.ylabel("Time (minutes)")
    plt.savefig("chart_3_access_times.png")
    print("  > Saved: chart_3_access_times.png")

    # 4. Bar Chart – Revenue per Policy
    # [cite_start]Ref: [cite: 283]
    plt.figure(figsize=(10, 6))
    revenue = df.groupby("Policy")["ParkingFee"].sum()
    sns.barplot(x=revenue.index, y=revenue.values, hue=revenue.index, palette="magma", legend=False)
    plt.title("Chart 4: Total Revenue per Policy")
    plt.ylabel("Revenue ($)")
    plt.savefig("chart_4_revenue.png")
    print("  > Saved: chart_4_revenue.png")

    # 5. Scatter Plot – Efficiency Frontier (Service vs Revenue)
    # [cite_start]Ref: [cite: 42]
    plt.figure(figsize=(10, 6))
    summary = df[df["IsBlocked"]==0].groupby("Policy")[["TravelTime", "ParkingFee"]].mean()
    sns.scatterplot(data=summary, x="TravelTime", y="ParkingFee", s=300, hue=summary.index, palette="deep")
    for policy, row in summary.iterrows():
        plt.text(row["TravelTime"]+0.2, row["ParkingFee"], policy, fontsize=11)
    plt.title("Chart 5: Efficiency Frontier (Time vs. Revenue)")
    plt.xlabel("Avg Access Time (min) [Lower is Better]")
    plt.ylabel("Avg Revenue per Car ($) [Higher is Better]")
    plt.savefig("chart_5_efficiency.png")
    print("  > Saved: chart_5_efficiency.png")

    # 6. Policy Impact by Lot (Load Distribution) - Stacked Bar
    # [cite_start]Ref: [cite: 265]
    # Shows which lots are being used by which policy
    plt.figure(figsize=(12, 6))
    # Count how many cars ended up in each lot per policy
    load_dist = df[df["IsBlocked"]==0].groupby(["Policy", "AssignedLot"]).size().reset_index(name='Count')
    # Pivot for stacked plotting
    load_pivot = load_dist.pivot(index='Policy', columns='AssignedLot', values='Count').fillna(0)
    load_pivot.plot(kind='bar', stacked=True, figsize=(12, 6), colormap='tab20')
    plt.title("Chart 6: Load Distribution (Cars Assigned per Lot)")
    plt.ylabel("Number of Vehicles")
    plt.savefig("chart_6_lot_load.png")
    print("  > Saved: chart_6_lot_load.png")
    
    # 7. Stacked Bar – Arrival vs Served vs Blocked
    # [cite_start]Ref: [cite: 277]
    # Composition of demand outcomes
    plt.figure(figsize=(10, 6))
    outcome_counts = df.groupby(["Policy", "IsBlocked"]).size().unstack(fill_value=0)
    outcome_counts.columns = ["Served", "Blocked"]
    outcome_counts.plot(kind='bar', stacked=True, color=['green', 'red'], figsize=(10, 6))
    plt.title("Chart 7: Demand Composition (Served vs. Blocked)")
    plt.ylabel("Total Vehicles")
    plt.savefig("chart_7_demand_outcomes.png")
    print("  > Saved: chart_7_demand_outcomes.png")

if __name__ == "__main__":
    results_df, history = run_experiment_suite()
    generate_requested_charts(results_df, history)
    print("\nAll 7 charts generated successfully.")