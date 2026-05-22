import time
# Import the native Rust engine we compiled with maturin
import eqie_engine

def main():
    print("🚀 Initializing Rust Engine...")
    
    # 1. Instantiate the zero-copy shared memory class from Rust
    metrics = eqie_engine.LiveMetrics()
    
    # 2. Kick off the asynchronous WebSocket ingestion in the background
    print("Connecting to live Gemini WebSocket stream via Rust...")
    eqie_engine.start_ingestion(metrics)
    
    # Pause for 2 seconds to let the WebSocket complete its handshake and download the initial book snapshot
    print("Waiting for initial data cache to populate...")
    time.sleep(2)
    
    print("Streaming data straight from shared memory slots:\n")
    
    # 3. Python loop reads the live shared metrics without interrupting the Rust thread
    try:
        while True:
            # Instantly pull the current best bid and ask prices from the Rust layer
            best_bid, best_ask = metrics.get_snapshot()
            
            # Calculate the spread directly inside Python to prove data integrity
            spread = best_ask - best_bid
            
            print(f"[Python Shared Memory View] Spread: {spread:,.2f} ticks | Best Bid: ${best_bid:,.2f} | Best Ask: ${best_ask:,.2f}")
            
            # Query the memory 10 times a second (every 100ms)
            time.sleep(0.1)
            
    except KeyboardInterrupt:
        print("\nStopping Python-Rust bridge gracefully...")

if __name__ == "__main__":
    main()