mod models;
mod orderbook;

use futures_util::StreamExt;
use tokio_tungstenite::{connect_async, tungstenite::Message};
use models::GeminiMessage;
use orderbook::OrderBook;

#[tokio::main]
async fn main() {
    // Gemini BTC/USD public market data feed
    let url = "wss://api.gemini.com/v1/marketdata/BTCUSD";
    
    let (ws_stream, _) = connect_async(url).await.expect("Failed to connect to Gemini");
    println!("Connected to Gemini WebSocket! Data incoming...");

    let (_, mut read) = ws_stream.split();
    let mut order_book = OrderBook::new();

    while let Some(message) = read.next().await {
        match message {
            Ok(Message::Text(text)) => {
                match serde_json::from_str::<GeminiMessage>(&text) {
                    Ok(gemini_msg) => {
                        // We only care about "update" messages
                        if gemini_msg.msg_type == "update" {
                            if let Some(events) = gemini_msg.events {
                                for event in events {
                                    // Process "change" events to update the book
                                    if event.event_type == "change" {
                                        if let (Some(side), Some(price_str), Some(remaining_str)) = (event.side, event.price, event.remaining) {
                                            let is_bid = side == "bid";
                                            let price: f64 = price_str.parse().unwrap_or(0.0);
                                            let size: f64 = remaining_str.parse().unwrap_or(0.0);
                                            
                                            // Gemini gives us the 'remaining' size at that price level
                                            order_book.update_level(is_bid, (price * 100.0) as i64, (size * 1000.0) as i64);
                                        }
                                    }
                                }
                                
                                // Print the spread metrics once the initial snapshot finishes loading
                                if let (Some(bid), Some(ask)) = (order_book.best_bid(), order_book.best_ask()) {
                                    let spread = ask.0 - bid.0;
                                    println!(
                                        "Spread: {} ticks | Best Bid: ${:.2} | Best Ask: ${:.2}", 
                                        spread, 
                                        bid.0 as f64 / 100.0, 
                                        ask.0 as f64 / 100.0
                                    );
                                }
                            }
                        }
                    }
                    Err(_) => {} // Silently ignore heartbeat messages
                }
            }
            Err(e) => {
                eprintln!("Stream error: {:?}", e);
                break;
            }
            _ => {}
        }
    }
}