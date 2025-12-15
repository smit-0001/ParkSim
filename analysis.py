import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from scipy import stats
from simulation_engine import JFKSimulation

# Configuration
POLICIES = ["Baseline", "Nearest", "CostMin", "Occupancy", "Reservation"]
TRAFFIC_FILE = "traffic_arrival_log.csv"

def run_experiment_suite():
    """Runs simulation for ALL policies and collects granular data."""
    print(f"--- PHASE 5: Running Analysis Suite on {TRAFFIC_FILE} ---")
    all_records = []
    
    for policy in POLICIES:
        print(f"  > Simulating Policy: {policy}...")
        sim = JFKSimulation("parking_facilities.csv", TRAFFIC_FILE, "network_distances.csv")
        sim.load_events()
        sim.run(policy_name=policy)
        
        # Extract Per-Vehicle Data
        for v_id, vehicle in sim.vehicle_registry.items():
            if vehicle.status == "Blocked":
                travel_time = 60.0 # Penalty
                is_blocked = 1
                parking_fee = 0.0
            else:
                travel_time = sim.get_travel_time(vehicle.assigned_lot, vehicle.target_terminal)
                is_blocked = 0
                
                # ESTIMATE REVENUE:
                # We calculate this manually here since the simplified simulation 
                # stores revenue on the Lot, not the Vehicle.
                # Average rate approx $10 per 30 mins for calculation purposes
                parking_fee = (vehicle.duration / 30) * 10 
            
            all_records.append({
                "VehicleID": v_id,
                "UserType": vehicle.user_type,
                "Policy": policy,
                "TravelTime": travel_time,
                "IsBlocked": is_blocked,
                "ParkingFee": parking_fee,  # <--- This is the key column you were missing
                "Duration": vehicle.duration
            })
            
    return pd.DataFrame(all_records)

def generate_comprehensive_plots(df):
    """Generates 7 distinct visualizations."""
    print("\nGenerating Comprehensive Visualizations...")
    sns.set_theme(style="whitegrid")
    
    # --- 1. OPERATIONAL: Blocking Probability (Bar Chart) ---
    plt.figure(figsize=(10, 6))
    block_rates = df.groupby("Policy")["IsBlocked"].mean() * 100
    
    # FIX: Assigned 'hue' to x variable to fix Seaborn warning
    ax = sns.barplot(x=block_rates.index, y=block_rates.values, hue=block_rates.index, palette="viridis", legend=False)
    plt.title("KPI 1: Blocking Probability (Lower is Better)")
    plt.ylabel("Blocking Rate (%)")
    for i in ax.containers: ax.bar_label(i, fmt='%.2f%%')
    plt.savefig("chart_1_blocking_rate.png")
    print("  > Saved: chart_1_blocking_rate.png")

    # --- 2. SERVICE: Travel Time Distribution (Box Plot) ---
    success_df = df[df["IsBlocked"] == 0]
    plt.figure(figsize=(10, 6))
    sns.boxplot(data=success_df, x="Policy", y="TravelTime", hue="Policy", palette="Set2", legend=False)
    plt.title("KPI 2: Distribution of Terminal Access Times")
    plt.ylabel("Minutes (Walk/Shuttle)")
    plt.savefig("chart_2_travel_time_dist.png")
    print("  > Saved: chart_2_travel_time_dist.png")

    # --- 2. SERVICE: Travel Time Distribution (Box Plot) ---
    success_df = df[df["IsBlocked"] == 0] 
    plt.figure(figsize=(10, 6))
    sns.boxplot(data=success_df, x="Policy", y="TravelTime", hue="Policy", palette="Set2", legend=False, showfliers=False)
    plt.title("KPI 2: Distribution of Terminal Access Times (Successful Parks Only)")
    plt.ylabel("Minutes (Walk/Shuttle)")
    plt.ylim(0, 45) 
    
    plt.savefig("chart_2_travel_time_dist.png")
    print("  > Saved: chart_2_travel_time_dist.png")

    # --- 3. FINANCIAL: Total Revenue Estimate (Bar Chart) ---
    plt.figure(figsize=(10, 6))
    revenue = df.groupby("Policy")["ParkingFee"].sum()
    ax = sns.barplot(x=revenue.index, y=revenue.values, hue=revenue.index, palette="magma", legend=False)
    plt.title("KPI 3: Total Estimated Revenue Comparison")
    plt.ylabel("Total Revenue ($)")
    plt.savefig("chart_3_revenue_total.png")
    print("  > Saved: chart_3_revenue_total.png")

    # --- 4. EFFICIENCY: Cost vs. Time Frontier (Scatter Plot) ---
    plt.figure(figsize=(10, 6))
    summary = df[df["IsBlocked"]==0].groupby("Policy")[["TravelTime", "ParkingFee"]].mean()
    sns.scatterplot(data=summary, x="TravelTime", y="ParkingFee", s=200, hue=summary.index, palette="deep")
    for policy, row in summary.iterrows():
        plt.text(row["TravelTime"]+0.1, row["ParkingFee"], policy)
    plt.title("KPI 4: Efficiency Frontier (Cost vs. Time Trade-off)")
    plt.xlabel("Avg Access Time (min)")
    plt.ylabel("Avg Parking Cost ($)")
    plt.savefig("chart_4_efficiency_frontier.png")
    print("  > Saved: chart_4_efficiency_frontier.png")

    # --- 5. DETAILED: Blocking by User Type (Grouped Bar) ---
    plt.figure(figsize=(12, 6))
    user_blocking = df.groupby(["Policy", "UserType"])["IsBlocked"].mean().reset_index()
    sns.barplot(data=user_blocking, x="Policy", y="IsBlocked", hue="UserType", palette="muted")
    plt.title("KPI 5: Who gets blocked? (Blocking by User Type)")
    plt.ylabel("Blocking Rate (0-1)")
    plt.savefig("chart_5_blocking_by_user.png")
    print("  > Saved: chart_5_blocking_by_user.png")

    # --- 6. DURATION: Average Stay Duration (Sanity Check) ---
    plt.figure(figsize=(10, 6))
    sns.violinplot(data=df, x="UserType", y="Duration", hue="UserType", palette="pastel", legend=False)
    plt.title("KPI 6: Parking Duration Distribution by User Type")
    plt.ylabel("Minutes Parked")
    plt.yscale("log")
    plt.savefig("chart_6_duration_sanity_check.png")
    print("  > Saved: chart_6_duration_sanity_check.png")

    # --- 7. HEATMAP: Policy Performance Matrix ---
    metrics = df.groupby("Policy")[["IsBlocked", "TravelTime", "ParkingFee"]].mean()
    normalized = (metrics - metrics.min()) / (metrics.max() - metrics.min())
    normalized["IsBlocked"] = 1 - normalized["IsBlocked"]
    normalized["TravelTime"] = 1 - normalized["TravelTime"]
    
    plt.figure(figsize=(8, 6))
    sns.heatmap(normalized, annot=True, cmap="RdYlGn", center=0.5)
    plt.title("KPI 7: Policy Scorecard (Green = Better Performance)")
    plt.savefig("chart_7_policy_scorecard.png")
    print("  > Saved: chart_7_policy_scorecard.png")

if __name__ == "__main__":
    results_df = run_experiment_suite()
    generate_comprehensive_plots(results_df)
    print("\nAnalysis Complete. Check your folder for 7 chart images.")