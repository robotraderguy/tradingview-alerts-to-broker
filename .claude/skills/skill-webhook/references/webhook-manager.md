# Webhook Manager (`scripts/webhook_manager.py`)

Full implementation of the webhook manager module with request authentication, payload parsing, MongoDB event logging, and rate limiting.

```python
"""
Webhook manager for processing inbound webhook requests.

Provides:
- Request authentication (secret, HMAC, bearer token)
- Payload parsing and validation
- MongoDB event logging
- Rate limiting
- Signal routing to order pipeline
"""

import datetime as dt
import hashlib
import hmac
import json
import time
import traceback
from collections import defaultdict
from functools import wraps

from flask import request, jsonify, abort

from constants import (
    WEBHOOK_SECRET_TV,
    WEBHOOK_SECRET_BROKER,
    WEBHOOK_TOKEN,
    WEBHOOK_EVENTS_COLLECTION,
    WEBHOOK_RATE_LIMIT,
    WEBHOOK_ALLOWED_IPS,
)


# =============================================================================
# RATE LIMITING
# =============================================================================

_rate_limit_store = defaultdict(list)


def check_rate_limit(ip, max_per_minute=None):
    """
    Check if an IP has exceeded the rate limit.

    Args:
        ip (str): Client IP address.
        max_per_minute (int): Max requests per minute (default: WEBHOOK_RATE_LIMIT).

    Returns:
        bool: True if within limit, False if exceeded.
    """
    limit = max_per_minute or WEBHOOK_RATE_LIMIT
    now = time.time()
    window = 60  # 1 minute

    # Clean old entries
    _rate_limit_store[ip] = [t for t in _rate_limit_store[ip] if now - t < window]

    if len(_rate_limit_store[ip]) >= limit:
        return False

    _rate_limit_store[ip].append(now)
    return True


# =============================================================================
# AUTHENTICATION HELPERS
# =============================================================================

def verify_secret(provided_secret, expected_secret):
    """
    Constant-time comparison of webhook secrets.

    Args:
        provided_secret (str): Secret from the request.
        expected_secret (str): Expected secret from env var.

    Returns:
        bool: True if secrets match.
    """
    if not expected_secret:
        return False
    return hmac.compare_digest(str(provided_secret), str(expected_secret))


def verify_hmac_signature(payload_body, signature, secret, algorithm="sha256"):
    """
    Verify HMAC signature on a webhook payload.

    Args:
        payload_body (bytes): Raw request body.
        signature (str): Signature from request header (e.g., "sha256=abc123...").
        secret (str): Shared HMAC secret.
        algorithm (str): Hash algorithm (default: sha256).

    Returns:
        bool: True if signature is valid.
    """
    if not secret or not signature:
        return False

    # Strip algorithm prefix if present (e.g., "sha256=...")
    if "=" in signature:
        sig_algorithm, sig_hash = signature.split("=", 1)
    else:
        sig_hash = signature

    expected = hmac.new(
        secret.encode("utf-8"),
        payload_body,
        getattr(hashlib, algorithm),
    ).hexdigest()

    return hmac.compare_digest(sig_hash, expected)


def verify_bearer_token(auth_header, expected_token):
    """
    Verify a Bearer token from the Authorization header.

    Args:
        auth_header (str): Authorization header value.
        expected_token (str): Expected token from env var.

    Returns:
        bool: True if token matches.
    """
    if not expected_token or not auth_header:
        return False

    if not auth_header.startswith("Bearer "):
        return False

    provided = auth_header[7:]  # Strip "Bearer "
    return hmac.compare_digest(provided, expected_token)


def check_ip_whitelist(ip):
    """
    Check if client IP is in the allowed list.

    Args:
        ip (str): Client IP address.

    Returns:
        bool: True if allowed (or if whitelist is empty = allow all).
    """
    if not WEBHOOK_ALLOWED_IPS:
        return True  # No whitelist = allow all
    return ip in WEBHOOK_ALLOWED_IPS


# =============================================================================
# EVENT LOGGING
# =============================================================================

def log_webhook_event(db, source, payload, status, error=None, metadata=None):
    """
    Log a webhook event to MongoDB.

    Args:
        db: MongoDB connection.
        source (str): Webhook source ("tradingview", "broker", "generic").
        payload (dict): Parsed request payload.
        status (str): "success", "auth_failed", "parse_error", "rate_limited", "error".
        error (str, optional): Error message if failed.
        metadata (dict, optional): Additional context (IP, headers, etc.).
    """
    now = dt.datetime.now(tz=dt.timezone.utc)

    document = {
        "datetime": now.strftime("%Y-%m-%d %X"),
        "timestamp": now.isoformat(),
        "source": source,
        "status": status,
        "payload": _sanitize_payload(payload),
        "handled": status == "success",
    }

    if error:
        document["error"] = str(error)[:500]  # Truncate long errors

    if metadata:
        document["metadata"] = metadata

    try:
        db.get_collection(WEBHOOK_EVENTS_COLLECTION).insert_one(document)
    except Exception as e:
        print(f"Error: Failed to log webhook event: {e}")


def _sanitize_payload(payload):
    """Remove sensitive fields from payload before logging."""
    if not isinstance(payload, dict):
        return payload

    sanitized = dict(payload)
    sensitive_keys = {"secret", "token", "password", "api_key", "apiKey", "key"}
    for key in list(sanitized.keys()):
        if key.lower() in sensitive_keys:
            sanitized[key] = "***REDACTED***"
    return sanitized


# =============================================================================
# TRADINGVIEW PAYLOAD PARSER
# =============================================================================

def parse_tradingview_alert(payload):
    """
    Parse a TradingView webhook alert payload into structured signal data.

    TradingView alerts send JSON in the message body. The format is configured
    by the user when creating the alert.

    Args:
        payload (dict): Parsed JSON payload from TradingView.

    Returns:
        dict: Structured signal data, or {"error": "description"} if parsing fails.

    Expected payload format (configured in TradingView alert message):
    {
        "action": "buy",           # Required: "buy" or "sell"
        "symbol": "ETHUSD",        # Required: trading pair / ticker
        "price": 3500.00,          # Optional: entry price (market order if omitted)
        "quantity": 0.5,           # Optional: size (uses default if omitted)
        "stop_loss": 3400.00,      # Optional: stop loss price
        "take_profit": 3700.00,    # Optional: take profit price
        "order_type": "limit",     # Optional: "market" or "limit" (default: market)
        "timeframe": "1H",         # Optional: chart timeframe
        "strategy": "mean_revert", # Optional: strategy name
        "comment": "MA crossover"  # Optional: signal description
    }
    """
    if not isinstance(payload, dict):
        return {"error": "Payload must be a JSON object"}

    # Required fields
    action = payload.get("action", "").lower().strip()
    symbol = payload.get("symbol", payload.get("ticker", "")).upper().strip()

    if not action:
        return {"error": "Missing required field: 'action' (buy/sell)"}
    if action not in ("buy", "sell", "long", "short", "close", "flatten"):
        return {"error": f"Invalid action: '{action}'. Expected: buy, sell, long, short, close, flatten"}
    if not symbol and action not in ("close", "flatten"):
        return {"error": "Missing required field: 'symbol'"}

    # Normalize action
    if action == "long":
        action = "buy"
    elif action == "short":
        action = "sell"

    # Optional fields with type coercion
    signal = {
        "action": action,
        "symbol": symbol,
        "source": "tradingview",
    }

    # Price fields
    for field in ("price", "stop_loss", "take_profit", "stopLoss", "takeProfit"):
        value = payload.get(field)
        if value is not None:
            try:
                # Normalize field names to snake_case
                key = field.replace("stopLoss", "stop_loss").replace("takeProfit", "take_profit")
                signal[key] = float(value)
            except (ValueError, TypeError):
                pass

    # Quantity
    qty = payload.get("quantity", payload.get("qty", payload.get("size")))
    if qty is not None:
        try:
            signal["quantity"] = float(qty)
        except (ValueError, TypeError):
            pass

    # Order type
    order_type = payload.get("order_type", payload.get("orderType", "market")).lower()
    if order_type in ("market", "limit"):
        signal["order_type"] = order_type
    else:
        signal["order_type"] = "market"

    # If price specified but order_type not explicitly set, default to limit
    if "price" in signal and "order_type" not in payload:
        signal["order_type"] = "limit"

    # Pass-through metadata
    for field in ("timeframe", "strategy", "comment", "interval", "exchange"):
        value = payload.get(field)
        if value:
            signal[field] = str(value)

    return signal


# =============================================================================
# BROKER CALLBACK PARSER
# =============================================================================

def parse_broker_callback(payload, broker="generic"):
    """
    Parse a broker callback/webhook payload into a structured event.

    Args:
        payload (dict): Parsed JSON payload from broker.
        broker (str): Broker name for format-specific parsing.

    Returns:
        dict: Structured event data with "event_type" key.
    """
    if not isinstance(payload, dict):
        return {"error": "Payload must be a JSON object"}

    event = {
        "source": "broker",
        "broker": broker,
        "raw": payload,
    }

    # Coinbase Advanced Trade callbacks
    if broker == "coinbase":
        event["event_type"] = payload.get("type", "unknown")
        event["order_id"] = payload.get("order_id", "")
        event["product_id"] = payload.get("product_id", "")
        event["side"] = payload.get("side", "")
        event["status"] = payload.get("status", "")

        if payload.get("filled_size"):
            event["filled_size"] = payload["filled_size"]
        if payload.get("filled_value"):
            event["filled_value"] = payload["filled_value"]
        if payload.get("average_filled_price"):
            event["fill_price"] = payload["average_filled_price"]

    # Alpaca callbacks
    elif broker == "alpaca":
        event["event_type"] = payload.get("event", "unknown")
        order = payload.get("order", {})
        event["order_id"] = order.get("id", "")
        event["symbol"] = order.get("symbol", "")
        event["side"] = order.get("side", "")
        event["status"] = order.get("status", "")

        if order.get("filled_qty"):
            event["filled_qty"] = order["filled_qty"]
        if order.get("filled_avg_price"):
            event["fill_price"] = order["filled_avg_price"]

    # Generic / unknown broker
    else:
        event["event_type"] = payload.get("event", payload.get("type", "unknown"))

    return event
```

**Customization points:**
- Add broker-specific callback parsers for your project's broker
- Extend `parse_tradingview_alert()` with additional fields your strategy uses
- Adjust `WEBHOOK_RATE_LIMIT` based on expected signal frequency
- Add IP whitelist entries for your broker's callback servers
