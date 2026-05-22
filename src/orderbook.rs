use std::collections::BTreeMap;
use std::cmp::Reverse;

#[derive(Debug, Default)]
pub struct OrderBook {
    bids: BTreeMap<Reverse<i64>, i64>, 
    asks: BTreeMap<i64, i64>,          
}

impl OrderBook {
    pub fn new() -> Self {
        Self::default()
    }

    pub fn update_level(&mut self, is_bid: bool, price: i64, size: i64) {
        if is_bid {
            if size == 0 {
                self.bids.remove(&Reverse(price));
            } else {
                self.bids.insert(Reverse(price), size);
            }
        } else {
            if size == 0 {
                self.asks.remove(&price);
            } else {
                self.asks.insert(price, size);
            }
        }
    }

    pub fn best_bid(&self) -> Option<(i64, i64)> {
        self.bids.iter().next().map(|(Reverse(p), s)| (*p, *s))
    }

    pub fn best_ask(&self) -> Option<(i64, i64)> {
        self.asks.iter().next().map(|(p, s)| (*p, *s))
    }
}