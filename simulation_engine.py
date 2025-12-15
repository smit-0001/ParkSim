import pandas as pd
import heapq
from dataclasses import dataclass, field
from typing import List, Dict, Optional

# --- CORE CLASSES ---

class ParkingLot:
    """Manages capacity, occupancy, and revenue for a single lot."""
    def __init__(self, row):
        self.lot_id = row['LotID']
        self.name = row['LotType']
        self.capacity = int(row['TotalCapacity'])
        self.rate_30min = float(row['BaseRate30Min'])
        self.daily_max = float(row['DailyMaxRate'])
        
        self.current_occupancy = 0
        self.revenue = 0.0
        
    def has_spot(self) -> bool:
        return self.current_occupancy < self.capacity

    def occupy_spot(self):
        if self.has_spot():
            self.current_occupancy += 1
            return True
        return False

    def release_spot(self, duration_min):
        if self.current_occupancy > 0:
            self.current_occupancy -= 1
            self.calculate_revenue(duration_min)
            
    def calculate_revenue(self, duration_min):
        units = (duration_min / 30)
        cost = units * self.rate_30min
        # Cap at daily max if needed
        final_cost = min(cost, self.daily_max * (duration_min/1440 if duration_min > 1440 else 1))
        self.revenue += final_cost

@dataclass(order=True)
class Event:
    timestamp: float
    priority: int 
    type: str = field(compare=False)
    vehicle_id: int = field(compare=False)
    payload: Optional[str] = field(default=None, compare=False) 

class Vehicle:
    def __init__(self, row):
        self.id = row['AgentID']
        self.user_type = row['UserType']
        self.target_terminal = row['TargetTerminal']
        self.reservation = row['ReservationStatus']
        self.duration = float(row['ParkingDurationForecast'])
        self.arrival_time = float(row['ArrivalTime'])
        self.assigned_lot = None
        self.status = "EnRoute" 

# --- SIMULATION CONTROLLER ---

class JFKSimulation:
    def __init__(self, facilities_file, traffic_file, distance_file):
        self.lots_df = pd.read_csv(facilities_file)
        self.traffic_df = pd.read_csv(traffic_file)
        self.dist_df = pd.read_csv(distance_file)
        self.lots = {row['LotID']: ParkingLot(row) for _, row in self.lots_df.iterrows()}
        self.events = [] 
        self.clock = 0.0
        
        # --- FIX IS HERE: Initialize the logger variable ---
        self.last_log_time = -10.0 
        self.history = [] 
        
        self._build_distance_lookup()
        self.blocked_vehicles = 0
        self.total_vehicles = 0

    def _build_distance_lookup(self):
        self.dist_lookup = {}
        for _, row in self.dist_df.iterrows():
            key = (row['OriginLotID'], row['DestinationTerminal'])
            self.dist_lookup[key] = float(row['TransitTimeMin'])

    def get_travel_time(self, lot_id, terminal_id):
        return self.dist_lookup.get((lot_id, terminal_id), 999.0)

    def load_events(self):
        print("Loading vehicle arrivals into event queue...")
        for _, row in self.traffic_df.iterrows():
            veh = Vehicle(row)
            if not hasattr(self, 'vehicle_registry'): self.vehicle_registry = {}
            self.vehicle_registry[veh.id] = veh
            evt = Event(timestamp=veh.arrival_time, priority=1, type="ARRIVAL", vehicle_id=veh.id)
            heapq.heappush(self.events, evt)
            self.total_vehicles += 1

    def log_state(self):
        """Records current occupancy only if 10 minutes have passed since last log."""
        # Check against self.last_log_time which is now properly initialized
        if self.clock - self.last_log_time >= 10.0:
            snapshot = {"Time": self.clock}
            for lot_id, lot in self.lots.items():
                snapshot[lot_id] = lot.current_occupancy
            self.history.append(snapshot)
            self.last_log_time = self.clock

    def run(self, policy_name="Baseline"):
        self.active_policy = policy_name
        print(f"--- Starting Simulation: {self.active_policy} Policy ---")
        
        while self.events:
            current_event = heapq.heappop(self.events)
            self.clock = current_event.timestamp
            
            if current_event.type == "ARRIVAL":
                self.handle_arrival(current_event)
            elif current_event.type == "DEPARTURE":
                self.handle_departure(current_event)
            
            self.log_state() 

    def handle_arrival(self, event):
        vehicle = self.vehicle_registry[event.vehicle_id]
        assigned_lot_id = self.find_parking_spot(vehicle, self.active_policy)
        
        if assigned_lot_id:
            lot = self.lots[assigned_lot_id]
            lot.occupy_spot()
            vehicle.assigned_lot = assigned_lot_id
            vehicle.status = "Parked"
            departure_time = self.clock + vehicle.duration
            dept_evt = Event(timestamp=departure_time, priority=2, type="DEPARTURE", 
                             vehicle_id=vehicle.id, payload=assigned_lot_id)
            heapq.heappush(self.events, dept_evt)
        else:
            vehicle.status = "Blocked"
            self.blocked_vehicles += 1

    def handle_departure(self, event):
        lot_id = event.payload
        vehicle = self.vehicle_registry[event.vehicle_id]
        self.lots[lot_id].release_spot(vehicle.duration)
        vehicle.status = "Departed"

    def close_lot(self, lot_id):
        if lot_id in self.lots:
            self.lots[lot_id].capacity = 0
            self.lots[lot_id].current_occupancy = 0

    # --- POLICIES ---
    def find_parking_spot(self, vehicle, policy_name):
        if policy_name == "Baseline": return self._policy_baseline(vehicle)
        elif policy_name == "Nearest": return self._policy_nearest(vehicle)
        elif policy_name == "CostMin": return self._policy_cost_minimizing(vehicle)
        elif policy_name == "Occupancy": return self._policy_occupancy_aware(vehicle)
        elif policy_name == "Reservation": return self._policy_reservation_priority(vehicle)
        else: raise ValueError(f"Unknown policy: {policy_name}")

    def _policy_baseline(self, vehicle):
        candidates = []
        if vehicle.user_type == "Short-Term":
            if vehicle.target_terminal == "T4": candidates = ['Blue', 'Red', 'Yellow']
            elif vehicle.target_terminal == "T5": candidates = ['Yellow', 'Blue', 'Red']
            else: candidates = ['Red', 'Blue', 'Yellow']
        elif vehicle.user_type in ["Business", "Vacationer"]: candidates = ['Lot9', 'OffAirport']
        else: candidates = ['Lot9']
        for lot_id in candidates:
            if self.lots[lot_id].has_spot(): return lot_id
        if self.lots['OffAirport'].has_spot(): return 'OffAirport'
        return None 

    def _policy_nearest(self, vehicle):
        valid_lots = []
        for lot_id, lot in self.lots.items():
            if lot.capacity == 0: continue
            if lot.has_spot():
                time = self.get_travel_time(lot_id, vehicle.target_terminal)
                valid_lots.append((time, lot_id))
        valid_lots.sort(key=lambda x: x[0])
        return valid_lots[0][1] if valid_lots else None

    def _policy_cost_minimizing(self, vehicle):
        alpha, beta = 1.0, 0.5
        best_lot, min_score = None, float('inf')
        for lot_id, lot in self.lots.items():
            if lot.capacity == 0: continue
            if lot.has_spot():
                hours = vehicle.duration / 60
                est_cost = min(lot.rate_30min * 2 * hours, lot.daily_max)
                access_time = self.get_travel_time(lot_id, vehicle.target_terminal)
                score = (alpha * access_time) + (beta * est_cost)
                if score < min_score:
                    min_score = score
                    best_lot = lot_id
        return best_lot

    def _policy_occupancy_aware(self, vehicle):
        valid_lots = []
        for lot_id, lot in self.lots.items():
            if lot.capacity == 0: continue
            occupancy_pct = lot.current_occupancy / lot.capacity
            if lot.has_spot() and occupancy_pct < 0.90:
                time = self.get_travel_time(lot_id, vehicle.target_terminal)
                valid_lots.append((time, lot_id))
        valid_lots.sort(key=lambda x: x[0])
        if valid_lots: return valid_lots[0][1]
        return self._policy_nearest(vehicle)

    def _policy_reservation_priority(self, vehicle):
        candidates = self.lots.keys()
        best_lot, min_time = None, float('inf')
        for lot_id in candidates:
            lot = self.lots[lot_id]
            if lot.capacity == 0: continue
            time = self.get_travel_time(lot_id, vehicle.target_terminal)
            is_accessible = False
            if vehicle.reservation:
                if lot.current_occupancy < lot.capacity: is_accessible = True
            else:
                if lot.current_occupancy < int(lot.capacity * 0.90): is_accessible = True
            if is_accessible and time < min_time:
                min_time = time
                best_lot = lot_id
        return best_lot