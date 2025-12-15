import pandas as pd
from simulation_engine import JFKSimulation
from data_generator import generate_traffic_log # We reuse the generator from Phase 1

# Configuration
POLICIES = ["Baseline", "CostMin", "Occupancy"] # Focusing on top 3 for brevity

def run_scenario_a_baseline():
    """
    SCENARIO A: BLUE-SKY DAY (Validation)
    Load: 100% (6,000 vehicles)
    Condition: All lots open
    Ref: [cite: 229-233]
    """
    print("\n" + "="*40)
    print("SCENARIO A: BLUE-SKY DAY (Standard Load)")
    print("="*40)
    
    for policy in POLICIES:
        sim = JFKSimulation("parking_facilities.csv", "traffic_arrival_log.csv", "network_distances.csv")
        sim.load_events()
        sim.run(policy_name=policy)
        print(f"  > {policy}: Block Rate = {sim.blocked_vehicles/sim.total_vehicles:.2%}")

def run_scenario_b_peak():
    """
    SCENARIO B: SUMMER PEAK (Stress Test)
    Load: 120% (7,200 vehicles)
    Condition: All lots open
    Ref: [cite: 234-237]
    """
    print("\n" + "="*40)
    print("SCENARIO B: SUMMER PEAK (120% Load)")
    print("="*40)
    
    # 1. Generate Peak Data on the fly (120% of 6000 = 7200)
    print("Generating Peak Traffic Trace (7,200 vehicles)...")
    df_peak = generate_traffic_log(num_vehicles=7200, seed=99) # New seed for variety
    df_peak.to_csv("traffic_peak.csv", index=False)
    
    for policy in POLICIES:
        # Load the PEAK traffic file
        sim = JFKSimulation("parking_facilities.csv", "traffic_peak.csv", "network_distances.csv")
        sim.load_events()
        sim.run(policy_name=policy)
        print(f"  > {policy}: Block Rate = {sim.blocked_vehicles/sim.total_vehicles:.2%}")

def run_scenario_c_disruption():
    """
    SCENARIO C: LOT CLOSURE DISRUPTION
    Load: 100%
    Condition: Yellow Lot (Terminal 5) is CLOSED
    Ref: [cite: 238-242]
    """
    print("\n" + "="*40)
    print("SCENARIO C: DISRUPTION (Yellow Lot Closed)")
    print("="*40)
    
    for policy in POLICIES:
        sim = JFKSimulation("parking_facilities.csv", "traffic_arrival_log.csv", "network_distances.csv")
        
        # !!! TRIGGER THE DISRUPTION !!!
        sim.close_lot("Yellow") 
        
        sim.load_events()
        sim.run(policy_name=policy)
        print(f"  > {policy}: Block Rate = {sim.blocked_vehicles/sim.total_vehicles:.2%}")

if __name__ == "__main__":
    run_scenario_a_baseline()
    run_scenario_b_peak()
    run_scenario_c_disruption()