use serde::Deserialize;

#[derive(Deserialize, Debug)]
pub struct GeminiMessage {
    #[serde(rename = "type")]
    pub msg_type: String,
    pub events: Option<Vec<GeminiEvent>>,
}

#[derive(Deserialize, Debug)]
pub struct GeminiEvent {
    #[serde(rename = "type")]
    pub event_type: String,
    pub side: Option<String>,
    pub price: Option<String>,
    pub remaining: Option<String>,
}