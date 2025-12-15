import pandas as pd
import numpy as np
import random

# --- TABLE 1: PARKING FACILITIES [cite: 104] ---
def get_parking_facilities():
    data = [
        {"LotID": "Blue", "AssociatedTerminals": ["T4"], "TotalCapacity": 2500, "BaseRate30Min": 15, "DailyMaxRate": 80, "LotType": "Terminal Garage"},
        {"LotID": "Yellow", "AssociatedTerminals": ["T5"], "TotalCapacity": 2200, "BaseRate30Min": 12, "DailyMaxRate": 75, "LotType": "Terminal Garage"},
        {"LotID": "Red", "AssociatedTerminals": ["T1", "T8"], "TotalCapacity": 6000, "BaseRate30Min": 10, "DailyMaxRate": 70, "LotType": "Terminal Garage"},
        {"LotID": "Orange", "AssociatedTerminals": ["T7"], "TotalCapacity": 500, "BaseRate30Min": 10, "DailyMaxRate": 65, "LotType": "Terminal Garage"},
        {"LotID": "Lot9", "AssociatedTerminals": ["T1", "T4", "T5", "T8"], "TotalCapacity": 4000, "BaseRate30Min": 8, "DailyMaxRate": 50, "LotType": "Long-Term"},
        {"LotID": "OffAirport", "AssociatedTerminals": ["ALL"], "TotalCapacity": 5000, "BaseRate30Min": 5, "DailyMaxRate": 35, "LotType": "Private/Remote"}
    ]
    return pd.DataFrame(data)

# --- TABLE 2: NETWORK DISTANCE MATRIX [cite: 115] ---
def get_network_distances():
    # Defines travel times between Lots and Terminals
    data = [
        # Blue Lot
        {"OriginLotID": "Blue", "DestinationTerminal": "T4", "TransitMode": "Walk", "TransitTimeMin": 5, "WalkingDistanceM": 400},
        {"OriginLotID": "Blue", "DestinationTerminal": "T5", "TransitMode": "AirTrain", "TransitTimeMin": 15, "WalkingDistanceM": 0},
        # Yellow Lot
        {"OriginLotID": "Yellow", "DestinationTerminal": "T5", "TransitMode": "Walk", "TransitTimeMin": 5, "WalkingDistanceM": 350},
        {"OriginLotID": "Yellow", "DestinationTerminal": "T4", "TransitMode": "Walk", "TransitTimeMin": 8, "WalkingDistanceM": 650},
        # Lot 9 (Long Term)
        {"OriginLotID": "Lot9", "DestinationTerminal": "T4", "TransitMode": "AirTrain", "TransitTimeMin": 20, "WalkingDistanceM": 0},
        {"OriginLotID": "Lot9", "DestinationTerminal": "T1", "TransitMode": "AirTrain", "TransitTimeMin": 22, "WalkingDistanceM": 0},
        # Off Airport
        {"OriginLotID": "OffAirport", "DestinationTerminal": "T4", "TransitMode": "Shuttle", "TransitTimeMin": 30, "WalkingDistanceM": 0},
        {"OriginLotID": "OffAirport", "DestinationTerminal": "T5", "TransitMode": "Shuttle", "TransitTimeMin": 30, "WalkingDistanceM": 0},
    ]
    return pd.DataFrame(data)

# --- TABLE 3: TRAFFIC ARRIVAL LOG (Dynamic) [cite: 90] ---
def generate_traffic_log(num_vehicles=6000, seed=42):
    np.random.seed(seed)
    random.seed(seed)
    
    vehicles = []
    current_time = 0
    vehicle_id_counter = 10001
    
    # Probabilities from design doc [cite: 72-74]
    user_types = ["Short-Term", "Business", "Vacationer", "Staff"]
    
    print(f"Generating {num_vehicles} vehicle arrivals...")
    
    for _ in range(num_vehicles):
        # 1. Arrival Process (Poisson)
        hour = (current_time // 60) % 24
        rate = 3000/60 if (7<=hour<=10 or 16<=hour<=19) else 1500/60
        inter_arrival = np.random.exponential(1/rate)
        current_time += inter_arrival
        
        # 2. Attributes
        u_type = np.random.choice(user_types, p=[0.4, 0.3, 0.2, 0.1])
        dest = np.random.choice(["T1", "T4", "T5", "T8"])
        has_res = np.random.choice([True, False], p=[0.1, 0.9])
        
        # 3. Duration
        if u_type == "Short-Term": duration = np.random.uniform(30, 120)
        elif u_type == "Business": duration = np.random.uniform(120, 480)
        elif u_type == "Vacationer": duration = np.random.uniform(360, 4320)
        else: duration = 480
        
        vehicles.append({
            "AgentID": vehicle_id_counter,
            "Date": "8/1/25", # Fixed placeholder date as per sample
            "ArrivalTime": round(current_time, 2),
            "EntryPoint": "Van Wyck Expressway", # Simplified
            "TargetTerminal": dest,
            "UserType": u_type,
            "ReservationStatus": has_res,
            "DisabilityStatus": False, # Default
            # The following are initialized to empty/zero, to be filled by the sim
            "LotID": None, 
            "ParkingFee": 0,
            "ParkingDurationForecast": round(duration, 0)
        })
        vehicle_id_counter += 1
        
    return pd.DataFrame(vehicles)

# if __name__ == "__main__":
#     df_facilities = get_parking_facilities()
#     df_distances = get_network_distances()
#     df_traffic = generate_traffic_log()
    
#     print(f"Generated Facilities Table: {len(df_facilities)} rows")
#     print(f"Generated Distances Table: {len(df_distances)} rows")
#     print(f"Generated Traffic Table: {len(df_traffic)} rows")

# for csv
if __name__ == "__main__":
    # 1. Generate the DataFrames
    df_facilities = get_parking_facilities()
    df_distances = get_network_distances()
    df_traffic = generate_traffic_log(num_vehicles=100000)
    
    # 2. Save them to CSV files
    df_facilities.to_csv("parking_facilities.csv", index=False)
    df_distances.to_csv("network_distances.csv", index=False)
    df_traffic.to_csv("traffic_arrival_log.csv", index=False)
    
    print("Success! The following files have been created:")
    print(f"1. parking_facilities.csv ({len(df_facilities)} lots)")
    print(f"2. network_distances.csv ({len(df_distances)} routes)")
    print(f"3. traffic_arrival_log.csv ({len(df_traffic)} vehicle arrivals)")