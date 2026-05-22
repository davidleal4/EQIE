mod models;
mod orderbook;

use pyo3::prelude::*;
use std::sync::{Arc, Mutex};
use futures_util::StreamExt;
use tokio_tungstenite::connect_async;
use tokio::runtime::Runtime;
use models::GeminiMessage;
use orderbook::OrderBook;

#[pyclass]
pub struct LiveMetrics {
    best_bid: Arc<Mutex<f64>>,
    best_ask: Arc<Mutex<f64>>,
    current_position: Arc<Mutex<i64>>, 
    is_halted: Arc<Mutex<bool>>, // NEW: The Kill Switch lock
}

#[pymethods]
impl LiveMetrics {
    #[new]
    fn new() -> Self {
        Self {
            best_bid: Arc::new(Mutex::new(0.0)),
            best_ask: Arc::new(Mutex::new(0.0)),
            current_position: Arc::new(Mutex::new(0)),
            is_halted: Arc::new(Mutex::new(false)),
        }
    }

    fn get_snapshot(&self) -> PyResult<(f64, f64)> {
        let bid = *self.best_bid.lock().unwrap();
        let ask = *self.best_ask.lock().unwrap();
        Ok((bid, ask))
    }

    // NEW: The Emergency Flatten Command
    fn activate_kill_switch(&self) -> PyResult<String> {
        let mut halted = self.is_halted.lock().unwrap();
        *halted = true; // Lock the engine
        
        let mut pos = self.current_position.lock().unwrap();
        let flat_pos = *pos;
        *pos = 0; // Market close all positions
        
        Ok(format!("🛑 KILL SWITCH ACTIVATED. Engine locked. Flattened {} open contracts.", flat_pos))
    }

    fn execute_trade(&self, side: &str, size: i64) -> PyResult<String> {
        // Intercept and block trades if the kill switch was pulled
        let halted = self.is_halted.lock().unwrap();
        if *halted {
            return Ok("❌ BLOCKED: Trading halted by Kill Switch.".to_string());
        }

        let mut pos = self.current_position.lock().unwrap();
        let max_contracts = 3; 
        
        if side == "BUY" {
            if *pos + size > max_contracts {
                return Ok(format!("❌ BLOCKED: Exceeds max long position of {}", max_contracts));
            }
            *pos += size;
            return Ok(format!("✅ EXECUTED: Bought {} contracts. Net Position: {}", size, *pos));
        } 
        else if side == "SELL" {
            if *pos - size < -max_contracts {
                return Ok(format!("❌ BLOCKED: Exceeds max short position of -{}", max_contracts));
            }
            *pos -= size;
            return Ok(format!("✅ EXECUTED: Sold {} contracts. Net Position: {}", size, *pos));
        }
        
        Ok("INVALID SIDE".to_string())
    }
}

#[pyfunction]
fn start_ingestion(metrics: &LiveMetrics) -> PyResult<()> {
    let bid_clone = Arc::clone(&metrics.best_bid);
    let ask_clone = Arc::clone(&metrics.best_ask);

    std::thread::spawn(move || {
        let rt = Runtime::new().unwrap();
        rt.block_on(async {
            let url = "wss://api.gemini.com/v1/marketdata/BTCUSD";
            let (ws_stream, _) = connect_async(url).await.expect("Failed to connect");
            let (_, mut read) = ws_stream.split();
            let mut local_book = OrderBook::new();

            while let Some(message) = read.next().await {
                if let Ok(tokio_tungstenite::tungstenite::Message::Text(text)) = message {
                    if let Ok(gemini_msg) = serde_json::from_str::<GeminiMessage>(&text) {
                        if gemini_msg.msg_type == "update" {
                            if let Some(events) = gemini_msg.events {
                                for event in events {
                                    if event.event_type == "change" {
                                        if let (Some(side), Some(price_str), Some(remaining_str)) = (event.side, event.price, event.remaining) {
                                            let is_bid = side == "bid";
                                            let price: f64 = price_str.parse().unwrap_or(0.0);
                                            let size: f64 = remaining_str.parse().unwrap_or(0.0);
                                            local_book.update_level(is_bid, (price * 100.0) as i64, (size * 1000.0) as i64);
                                        }
                                    }
                                }
                                
                                if let (Some(bid), Some(ask)) = (local_book.best_bid(), local_book.best_ask()) {
                                    *bid_clone.lock().unwrap() = bid.0 as f64 / 100.0;
                                    *ask_clone.lock().unwrap() = ask.0 as f64 / 100.0;
                                }
                            }
                        }
                    }
                }
            }
        });
    });

    Ok(())
}

#[pymodule]
fn eqie_engine(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_class::<LiveMetrics>()?;
    m.add_function(wrap_pyfunction!(start_ingestion, m)?)?;
    Ok(())
}