import os
import time
import hmac
import hashlib
import requests

from flask import Flask, jsonify
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

PHEMEX_API_KEY = os.environ.get("PHEMEX_API_KEY")
PHEMEX_API_SECRET = os.environ.get("PHEMEX_API_SECRET")

BASE_URL = "https://api.phemex.com"


def phemex_get(path, params=""):
    if not PHEMEX_API_KEY or not PHEMEX_API_SECRET:
        raise RuntimeError("Phemex API credentials are missing")

    expiry = str(int(time.time()) + 60)

    message = path + params + expiry

    signature = hmac.new(
        PHEMEX_API_SECRET.encode("utf-8"),
        message.encode("utf-8"),
        hashlib.sha256
    ).hexdigest()

    headers = {
        "x-phemex-access-token": PHEMEX_API_KEY,
        "x-phemex-request-expiry": expiry,
        "x-phemex-request-signature": signature
    }

    url = BASE_URL + path

    if params:
        url += "?" + params

    response = requests.get(url, headers=headers)
    response.raise_for_status()

    return response.json()


@app.route("/")
def home():
    return jsonify({
        "status": "ok",
        "service": "Rooted in Trades Phemex read-only bridge"
    })


@app.route("/api/phemex/positions")
def positions():
    try:
        data = phemex_get(
            "/g-accounts/positions",
            "currency=USDT"
        )

        if data.get("code") != 0:
            return jsonify(data), 400

        positions = data.get("data", {}).get("positions", [])

        btc_positions = []

        for p in positions:
            if p.get("symbol") != "BTCUSDT":
                continue

            size = float(p.get("sizeRq") or 0)

            if size == 0:
                continue

            pos_side = str(p.get("posSide") or "").lower()

            if pos_side == "long":
                side = "long"
            elif pos_side == "short":
                side = "short"
            else:
                side = "unknown"

            btc_positions.append({
                "symbol": "BTCUSDT",
                "side": side,
                "entryPrice": float(p.get("avgEntryPriceRp") or 0),
                "markPrice": float(p.get("markPriceRp") or 0),
                "sizeBTC": abs(size),
                "leverage": abs(float(p.get("leverageRr") or 0)),
                "unrealizedPnl": float(p.get("unRealisedPnlRv") or 0),
                "liquidationPrice": float(p.get("liquidationPriceRp") or 0)
            })

        if not btc_positions:
            return jsonify({
                "ok": True,
                "active": False,
                "position": None
            })

        return jsonify({
            "ok": True,
            "active": True,
            "position": btc_positions[0]
        })

    except Exception as e:
        return jsonify({
            "ok": False,
            "error": "Unable to retrieve Phemex position",
            "details": str(e)
        }), 500


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
