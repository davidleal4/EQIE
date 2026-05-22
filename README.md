# EQIE: Equity Quantitative Inference Engine

![EQIE Demo]
**Fast Path Agent**
<img width="1710" height="1107" alt="image" src="https://github.com/user-attachments/assets/dd8883f8-dc08-400f-a29a-469be022ac19" />

**Slow Path Agent**
<img width="1710" height="226" alt="image" src="https://github.com/user-attachments/assets/8e860db0-5c77-4ba5-ae4d-56073b7a0edf" />


EQIE is a hybrid-path, ultra-low latency algorithmic trading architecture. It combines a sub-millisecond Rust execution backend with a "fast-path" Python micro-structural evaluator, governed by an asynchronous "slow-path" sovereign LLM that dynamically adjusts risk parameters.

## System Architecture

The architecture is split into three decoupled layers, communicating via zero-copy shared memory and deterministic state files to completely bypass the Python GIL and serialization bottlenecks.

1. **The Ingestion & Execution Backend (Rust / PyO3 / Tokio)**
   - Manages asynchronous WebSocket connections to live exchange data.
   - Maintains a rolling Level-2 order book and streams top-of-book metrics into zero-copy `Arc<Mutex>` memory slots.
   - Acts as the final deterministic gatekeeper, physically blocking trades that violate hardcoded prop-firm daily loss limits or max position sizes.

2. **The Fast-Path Evaluator (Python / NumPy)**
   - Polls the Rust shared memory buffer 20x a second.
   - Engineers micro-structural features (order book momentum, rolling spread volatility) on the fly.
   - Triggers execution signals in sub-milliseconds without interrupting the data feed.

3. **The Slow-Path Risk Agent (Apple MLX / Ollama / Local LLMs)**
   - **Privacy-First Enterprise Alignment:** To adhere to strict enterprise consulting and proprietary trading requirements, the slow-path agent is completely localized. By utilizing frameworks like Ollama and MLX, the system ensures zero data leakage to cloud APIs.
   - Evaluates macro-market conditions periodically and outputs strict JSON schemas (enforced via Pydantic).
   - Dynamically updates the fast-path's momentum thresholds, risk multipliers, and spread limits based on the detected market regime (Trending, Mean-Reverting, Volatile).

## Core Tech Stack
* **Rust:** `tokio`, `tungstenite`, `pyo3`
* **Python:** `numpy`, `pydantic`
* **AI/Inference:** `mlx-lm`, `ollama`, Qwen2.5-0.5B-Instruct (4-bit quantized)

---

## Quick Start / Installation

### 1. Build the Rust Engine
Ensure you have Rust and Cargo installed, then compile the Python bindings:
```bash
python -m venv .venv
source .venv/bin/activate
pip install maturin numpy pydantic mlx-lm
maturin develop --release
