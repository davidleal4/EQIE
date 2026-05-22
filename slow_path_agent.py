import time
import json
from pydantic import BaseModel, Field
from mlx_lm import load, generate
from mlx_lm.sample_utils import make_sampler

# 1. UPDATED: Strict Mathematical Guardrails
class MarketRegime(BaseModel):
    regime: str = Field(description="Must be exactly 'TRENDING', 'MEAN_REVERTING', or 'VOLATILE'")
    momentum_threshold: float = Field(ge=0.1, le=1.0, description="Momentum to trigger a trade")
    max_spread: float = Field(ge=0.01, le=0.10, description="Max allowable spread")
    risk_multiplier: float = Field(ge=0.5, le=1.0, description="Position sizing multiplier")

def main():
    print("🧠 Initializing EQIE Slow-Path Agent (Apple MLX)...")
    model_id = "mlx-community/Qwen2.5-0.5B-Instruct-4bit"
    model, tokenizer = load(model_id)

    schema_str = json.dumps(MarketRegime.model_json_schema(), indent=2)

    try:
        while True:
            mock_macro_data = "The market has experienced a sudden 2% drop with expanding spreads."
            messages = [
                {"role": "system", "content": f"You are a risk officer. Output ONLY valid JSON matching this schema:\n{schema_str}"},
                {"role": "user", "content": mock_macro_data}
            ]
            
            prompt = tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
            sampler = make_sampler(temp=0.1)
            
            response_text = generate(model, tokenizer, prompt=prompt, max_tokens=150, sampler=sampler, verbose=False)
            
            try:
                clean_json = response_text.replace("```json", "").replace("```", "").strip()
                regime_config = json.loads(clean_json)
                
                # 2. NEW: Write the configuration to the shared state file
                with open("regime_config.json", "w") as f:
                    json.dump(regime_config, f)
                
                print(f"📊 SAVED CONFIG -> Regime: {regime_config.get('regime')} | Risk: {regime_config.get('risk_multiplier')}")
            except json.JSONDecodeError:
                print("🚨 LLM Hallucination Error: Output was not valid JSON.")
            
            time.sleep(10)

    except KeyboardInterrupt:
        print("\nShutting down Slow-Path Agent...")

if __name__ == "__main__":
    main()