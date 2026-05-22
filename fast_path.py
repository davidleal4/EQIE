import time
import json
import collections
import numpy as np
import eqie_engine
import os

class FastPathEvaluator:
    def __init__(self, window_size=20):
        self.spread_history = collections.deque(maxlen=window_size)
        self.bid_history = collections.deque(maxlen=window_size)
        self.ask_history = collections.deque(maxlen=window_size)
        
        self.momentum_threshold = 0.50
        self.max_spread = 0.05
        self.regime = "INITIALIZING"

        # NEW: Internal PnL Tracking
        self.cash = 0.0
        self.position = 0
        
    def update_parameters(self):
        if os.path.exists("regime_config.json"):
            try:
                with open("regime_config.json", "r") as f:
                    config = json.load(f)
                    self.momentum_threshold = config.get("momentum_threshold", self.momentum_threshold)
                    self.max_spread = config.get("max_spread", self.max_spread)
                    self.regime = config.get("regime", self.regime)
            except (json.JSONDecodeError, IOError):
                pass

    def engineer_features(self, current_bid, current_ask):
        self.bid_history.append(current_bid)
        self.ask_history.append(current_ask)
        self.spread_history.append(current_ask - current_bid)
        
        if len(self.bid_history) < 5:
            return None
            
        momentum = self.bid_history[-1] - self.bid_history[-5]
        avg_spread = np.mean(self.spread_history)
        return {"momentum": momentum, "avg_spread": avg_spread}

    def generate_signal(self, features):
        if features is None:
            return "WAITING_FOR_DATA"
            
        if features["momentum"] > self.momentum_threshold and features["avg_spread"] <= self.max_spread:
            return "EXECUTE_BUY_SIGNAL"
        elif features["momentum"] < -self.momentum_threshold and features["avg_spread"] <= self.max_spread:
            return "EXECUTE_SELL_SIGNAL"
            
        return "HOLD_POSITION"

    # NEW: Live PnL Mathematics
    def log_execution(self, side, price):
        if side == "BUY":
            self.position += 1
            self.cash -= price
        elif side == "SELL":
            self.position -= 1
            self.cash += price

    def calculate_pnl(self, current_bid, current_ask):
        # Calculate theoretical value if we liquidated right now
        if self.position > 0:
            return self.cash + (self.position * current_bid)
        elif self.position < 0:
            return self.cash + (self.position * current_ask)
        return self.cash

def main():
    print("=== EQIE Risk Management Setup ===")
    try:
        daily_profit_target = float(input("Enter Daily Profit Target ($): "))
        daily_loss_limit = float(input("Enter Daily Loss Limit ($): "))
    except ValueError:
        print("Invalid input. Defaulting to $500 Profit / $200 Loss.")
        daily_profit_target = 500.0
        daily_loss_limit = -200.0

    # Ensure the loss limit is a negative number for math comparison
    if daily_loss_limit > 0:
        daily_loss_limit = -daily_loss_limit
        
    print("\n🚀 Initializing EQIE Fast-Path Evaluator...")
    metrics = eqie_engine.LiveMetrics()
    eqie_engine.start_ingestion(metrics)
    
    evaluator = FastPathEvaluator(window_size=50)
    time.sleep(2)
    
    print("📈 Running fast-path evaluation loop...")
    try:
        loop_counter = 0
        while True:
            best_bid, best_ask = metrics.get_snapshot()
            features = evaluator.engineer_features(best_bid, best_ask)
            signal = evaluator.generate_signal(features)

            # Calculate live PnL at the current market prices
            current_pnl = evaluator.calculate_pnl(best_bid, best_ask)
            
            # Check Kill Switch Conditions
            if current_pnl >= daily_profit_target or current_pnl <= daily_loss_limit:
                print(f"\n⚠️ LIMIT REACHED! Current PnL: ${current_pnl:,.2f}")
                rust_response = metrics.activate_kill_switch()
                print(rust_response)
                print("\n🏁 Session complete. Shutting down trading algorithm.")
                break # Ends the Python loop entirely
            
            if signal == "EXECUTE_BUY_SIGNAL":
                result = metrics.execute_trade("BUY", 1)
                if "✅" in result:
                    evaluator.log_execution("BUY", best_ask)
                print(f"🟢 SIGNAL [BUY] -> Rust Response: {result} | PnL: ${current_pnl:,.2f}")
                time.sleep(1) 
                
            elif signal == "EXECUTE_SELL_SIGNAL":
                result = metrics.execute_trade("SELL", 1)
                if "✅" in result:
                    evaluator.log_execution("SELL", best_bid)
                print(f"🔴 SIGNAL [SELL] -> Rust Response: {result} | PnL: ${current_pnl:,.2f}")
                time.sleep(1) 
                
            elif signal != "WAITING_FOR_DATA":
                print(f"[Tracking {evaluator.regime}] PnL: ${current_pnl:,.2f} | Status: {signal}")
                
            loop_counter += 1
            if loop_counter % 20 == 0:
                evaluator.update_parameters()
                
            time.sleep(0.05)
            
    except KeyboardInterrupt:
        print("\nExiting Fast-Path Evaluator...")

if __name__ == "__main__":
    main()