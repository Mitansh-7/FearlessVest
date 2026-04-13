"""
Fearlessvest — Unified Backend API Server
Serves all pages: analysis.html, chatbot.html, market-today.html
Proxies Groq (VERA chatbot + AI analysis) and Finnhub (live market data).
API keys live ONLY in .env — never in the frontend code.
"""

import os
import json
from flask import Flask, request, jsonify, Response
from flask_cors import CORS
import requests as http_requests
from dotenv import load_dotenv

# Load .env from root directory
load_dotenv()

app = Flask(__name__)

# Allow requests from any origin (file://, localhost, etc.)
CORS(app)

# ── API Configuration ────────────────────────────────────────────
GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"
GROQ_MODEL_CHAT = "llama-3.1-8b-instant"         # Fast model for chatbot
GROQ_MODEL_ANALYSIS = "llama-3.3-70b-versatile"   # Larger model for deep analysis
FINNHUB_URL = "https://finnhub.io/api/v1"

# Keep it light to avoid Yahoo throttling
INDIAN_STOCKS = ["RELIANCE.NS", "TCS.NS", "INFY.NS"]

# VERA system prompt for the chatbot
SYSTEM_PROMPT = """You are VERA, a highly advanced Quantitative Technical Market Analyst for the platform Fearlessvest.

Your Objective:
- Provide technical analysis, hypothetical trade setups, and trend predictions based on standard market indicators.
- When asked for a trade prediction, clearly output a hypothetical scenario including:
  1. Entry Zone
  2. Take Profit (TP) Targets
  3. Stop Loss (SL)
  4. Reasoning (RSI, MACD, Volume, Support/Resistance).
- Adopt a professional, analytical, and sharp trader persona.
- Format numbers cleanly. Use bolding (**text**) for key price levels and targets.
- ALWAYS include a brief, one-sentence disclaimer at the very end stating that this is an AI simulation and not actual financial advice.
- Keep your responses under 200 words. Be concise and actionable."""


# ── Helper: Get Groq API key ─────────────────────────────────────
def get_groq_key():
    return os.getenv("GROQ_API_KEY", "")


# ════════════════════════════════════════════════════════════════
# STOCK DATA ENDPOINT (used by market-today.html via yfinance)
# ════════════════════════════════════════════════════════════════

def fetch_stock_data(symbols):
    """Fetch stock data via yfinance with fallback."""
    import yfinance as yf
    results = []

    for symbol in symbols:
        try:
            hist = yf.download(symbol, period="5d", interval="1d", progress=False)

            if hist.empty:
                print("No data:", symbol)
                continue

            close = float(hist["Close"].iloc[-1])
            open_price = float(hist["Open"].iloc[-1])

            change = round(close - open_price, 2)
            percent = round((change / open_price) * 100, 2)

            results.append({
                "symbol": symbol.replace(".NS", ""),
                "price": round(close, 2),
                "change": change,
                "percent": percent
            })

        except Exception as e:
            print("Error:", symbol, e)

    # fallback (VERY IMPORTANT)
    if not results:
        results = [
            {"symbol": "RELIANCE", "price": 2800, "change": 10, "percent": 0.5},
            {"symbol": "TCS", "price": 3900, "change": -20, "percent": -0.5}
        ]

    return results


@app.route("/stocks")
def get_stocks():
    return jsonify(fetch_stock_data(INDIAN_STOCKS))


# ════════════════════════════════════════════════════════════════
# AI ANALYSIS ENDPOINT — Streaming (used by analysis.html)
# ════════════════════════════════════════════════════════════════

@app.route("/ai-report", methods=["POST"])
def ai_report():
    """Generate AI portfolio report using Groq API with streaming."""
    api_key = get_groq_key()
    if not api_key:
        return jsonify({"error": "GROQ_API_KEY not set in .env"}), 500

    data = request.get_json()
    prompt = data.get("prompt", "")

    if not prompt:
        return jsonify({"error": "No prompt provided"}), 400

    def generate():
        try:
            resp = http_requests.post(
                GROQ_API_URL,
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": GROQ_MODEL_ANALYSIS,
                    "messages": [{"role": "user", "content": prompt}],
                    "max_tokens": 1024,
                    "temperature": 0.7,
                    "stream": True,
                },
                stream=True,
            )

            if resp.status_code != 200:
                error_body = resp.text
                yield f"data: {json.dumps({'error': f'Groq API error {resp.status_code}: {error_body}'})}\n\n"
                return

            for line in resp.iter_lines():
                if line:
                    decoded = line.decode("utf-8")
                    if decoded.startswith("data: "):
                        chunk_str = decoded[6:]
                        if chunk_str.strip() == "[DONE]":
                            yield "data: [DONE]\n\n"
                            return
                        try:
                            chunk = json.loads(chunk_str)
                            delta = chunk["choices"][0].get("delta", {})
                            content = delta.get("content", "")
                            if content:
                                yield f"data: {json.dumps({'content': content})}\n\n"
                        except (json.JSONDecodeError, KeyError, IndexError):
                            pass

            yield "data: [DONE]\n\n"

        except Exception as e:
            yield f"data: {json.dumps({'error': str(e)})}\n\n"

    return Response(generate(), mimetype="text/event-stream",
                    headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})


# ════════════════════════════════════════════════════════════════
# CHAT ENDPOINT (used by chatbot.html)
# ════════════════════════════════════════════════════════════════

@app.route("/api/chat", methods=["POST"])
def chat():
    """
    Accepts: { "messages": [ {"role": "user", "content": "..."}, ... ] }
    Returns: { "reply": "...", "model": "..." }
    """
    api_key = get_groq_key()
    if not api_key:
        return jsonify({"error": "GROQ_API_KEY not set in .env"}), 500

    body = request.get_json(silent=True)
    if not body or "messages" not in body:
        return jsonify({"error": "Request body must contain a 'messages' array"}), 400

    payload = {
        "model": GROQ_MODEL_CHAT,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            *body["messages"],
        ],
        "temperature": 0.7,
        "max_tokens": 300,
    }

    try:
        resp = http_requests.post(
            GROQ_API_URL,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {api_key}",
            },
            json=payload,
            timeout=30,
        )
        resp.raise_for_status()
        reply = resp.json()["choices"][0]["message"]["content"]
        return jsonify({"reply": reply, "model": GROQ_MODEL_CHAT})

    except http_requests.exceptions.HTTPError as e:
        return jsonify({"error": f"Groq error {e.response.status_code}: {e.response.text}"}), e.response.status_code
    except http_requests.exceptions.RequestException as e:
        return jsonify({"error": f"Network error: {str(e)}"}), 503


# ════════════════════════════════════════════════════════════════
# MARKET DATA ENDPOINTS (used by market-today.html via Finnhub)
# ════════════════════════════════════════════════════════════════

def finnhub_get(path, params=None):
    """Internal helper — calls Finnhub with the server-side key."""
    key = os.getenv("FINNHUB_API_KEY", "")
    if not key:
        raise ValueError("FINNHUB_API_KEY not set in .env")
    p = params or {}
    p["token"] = key
    resp = http_requests.get(f"{FINNHUB_URL}{path}", params=p, timeout=10)
    resp.raise_for_status()
    return resp.json()


@app.route("/api/market/quote", methods=["GET"])
def market_quote():
    """
    Proxy a single Finnhub stock quote.
    Query param: symbol (e.g. RELIANCE.NS, ^NSEI)
    Returns Finnhub quote object: { c, d, dp, h, l, o, pc, t }
    """
    symbol = request.args.get("symbol", "").strip()
    if not symbol:
        return jsonify({"error": "symbol query param required"}), 400
    try:
        data = finnhub_get("/quote", {"symbol": symbol})
        return jsonify(data)
    except ValueError as e:
        return jsonify({"error": str(e)}), 500
    except http_requests.exceptions.HTTPError as e:
        return jsonify({"error": f"Finnhub error {e.response.status_code}"}), e.response.status_code
    except http_requests.exceptions.RequestException as e:
        return jsonify({"error": f"Network error: {str(e)}"}), 503


@app.route("/api/market/batch", methods=["POST"])
def market_batch():
    """
    Fetch multiple quotes in one backend call to reduce frontend requests.
    Accepts: { "symbols": ["RELIANCE.NS", "TCS.NS", ...] }
    Returns: { "RELIANCE.NS": { c, d, dp, ... }, "TCS.NS": {...}, ... }
    """
    body = request.get_json(silent=True)
    if not body or "symbols" not in body:
        return jsonify({"error": "Body must contain 'symbols' array"}), 400

    symbols = body["symbols"][:20]  # cap at 20 to be safe
    results = {}

    for sym in symbols:
        try:
            results[sym] = finnhub_get("/quote", {"symbol": sym})
        except Exception as e:
            results[sym] = {"error": str(e), "c": 0, "d": 0, "dp": 0}

    return jsonify(results)


# ════════════════════════════════════════════════════════════════
# HEALTH CHECK
# ════════════════════════════════════════════════════════════════

@app.route("/api/health", methods=["GET"])
def health():
    """Ping endpoint — frontend checks this to show backend status badge."""
    return jsonify({
        "status": "ok",
        "groq_configured":    bool(os.getenv("GROQ_API_KEY")),
        "finnhub_configured": bool(os.getenv("FINNHUB_API_KEY")),
    })


# ════════════════════════════════════════════════════════════════
# ENTRY POINT
# ════════════════════════════════════════════════════════════════
if __name__ == "__main__":
    port = int(os.getenv("PORT", 5000))
    groq_ok    = bool(os.getenv("GROQ_API_KEY"))
    finnhub_ok = bool(os.getenv("FINNHUB_API_KEY"))
    print(f"\n  ✅  Fearlessvest unified backend → http://localhost:{port}")
    print(f"  🤖  GROQ_API_KEY    : {'✓ configured' if groq_ok    else '✗ MISSING — set in .env'}")
    print(f"  📈  FINNHUB_API_KEY : {'✓ configured' if finnhub_ok else '✗ MISSING — set in .env'}\n")
    print(f"  Endpoints:")
    print(f"    /stocks              — yfinance stock data")
    print(f"    /ai-report           — AI portfolio analysis (streaming)")
    print(f"    /api/chat            — VERA chatbot")
    print(f"    /api/market/quote    — Finnhub single quote")
    print(f"    /api/market/batch    — Finnhub batch quotes")
    print(f"    /api/health          — Health check\n")
    app.run(host="0.0.0.0", port=port, debug=True)