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
        raise RuntimeError("Phemex API credentials are not configured.")

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
        "x-phemex-request-signature": signature,
    }

    url = BASE_URL + path
    if params:
        url += "?" + params

    response = requests.get(url, headers=headers, timeout=10)
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
            "/g-accounts/accountPositions",
            "currency=USDT"
        )

        return jsonify(data)

    except Exception as e:
        return jsonify({
            "error": "Unable to retrieve Phemex positions",
            "details": str(e)
        }), 500


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
