# Webhook Flask Routes

Register these routes on `app.server` (the underlying Flask instance of the Dash app).

## Imports

```python
"""
Add these imports at the top of app.py (or in a dedicated webhook_routes.py
that gets imported by app.py):
"""

import json
import traceback

from flask import request, jsonify

from constants import (
    WEBHOOK_SECRET_TV,
    WEBHOOK_SECRET_BROKER,
    WEBHOOK_TOKEN,
    WEBHOOKS_ENABLED,
)
from scripts.webhook_manager import (
    check_rate_limit,
    check_ip_whitelist,
    verify_secret,
    verify_hmac_signature,
    verify_bearer_token,
    log_webhook_event,
    parse_tradingview_alert,
    parse_broker_callback,
)
from scripts.database_manager import connect_mongo
```

## TradingView Webhook Route

```python
@app.server.route("/webhook/tv", methods=["POST"])
def webhook_tradingview():
    """
    Receive TradingView alert webhooks.

    Authentication: Secret in URL query param or in JSON body.
    URL format: https://your-app.com/webhook/tv?secret=YOUR_SECRET

    TradingView alert message body (configure in alert settings):
    {
        "action": "{{strategy.order.action}}",
        "symbol": "{{ticker}}",
        "price": {{close}},
        "timeframe": "{{interval}}",
        "strategy": "mean_revert",
        "comment": "{{strategy.order.comment}}"
    }
    """
    client_ip = request.remote_addr

    # Rate limit check
    if not check_rate_limit(client_ip):
        return jsonify({"error": "Rate limit exceeded"}), 429

    # Authentication: check URL param first, then body field
    secret = request.args.get("secret", "")
    if not secret:
        try:
            body = request.get_json(silent=True) or {}
            secret = body.get("secret", "")
        except Exception:
            pass

    if not verify_secret(secret, WEBHOOK_SECRET_TV):
        # Log failed auth attempt
        db = connect_mongo()
        try:
            log_webhook_event(db, "tradingview", {}, "auth_failed",
                              metadata={"ip": client_ip})
        finally:
            db.client.close()
        return jsonify({"error": "Unauthorized"}), 401

    # Parse payload
    try:
        payload = request.get_json(silent=True)
        if payload is None:
            # TradingView sometimes sends plain text
            raw = request.data.decode("utf-8", errors="replace")
            try:
                payload = json.loads(raw)
            except json.JSONDecodeError:
                payload = {"raw_text": raw}
    except Exception as e:
        return jsonify({"error": f"Invalid payload: {e}"}), 400

    # Parse into structured signal
    signal = parse_tradingview_alert(payload)

    # Log to MongoDB
    db = connect_mongo()
    try:
        status = "error" if "error" in signal else "success"
        log_webhook_event(
            db, "tradingview", payload, status,
            error=signal.get("error"),
            metadata={"ip": client_ip, "signal": signal},
        )

        if "error" in signal:
            print(f"Warning: TradingView webhook parse error -- {signal['error']}")
            return jsonify({"error": signal["error"]}), 400

        # === ROUTE TO ORDER PIPELINE ===
        # This is where you connect to your project's order execution.
        # Options:
        #
        # Option A: Queue in MongoDB for async processing (like Discord alerts)
        #   db.get_collection("alerts").insert_one({
        #       "datetime": dt.datetime.now(tz=dt.timezone.utc).strftime("%Y-%m-%d %X"),
        #       "handled": False,
        #       "source": "tradingview",
        #       "signal": signal,
        #       "text": json.dumps(payload),
        #   })
        #
        # Option B: Execute immediately (synchronous)
        #   from scripts.trade_manager import execute_signal
        #   result = execute_signal(signal)
        #
        # Option C: Just log and notify (monitoring only)
        #   from scripts.slack_manager import send_slack_message
        #   send_slack_message("webhook-alerts", f"TV Signal: {signal}")

        print(f"Info: TradingView webhook received -- {signal['action']} {signal.get('symbol', '')}")

    finally:
        db.client.close()

    return jsonify({"status": "received", "signal": signal}), 200
```

## Broker Callback Webhook Route

```python
@app.server.route("/webhook/broker", methods=["POST"])
def webhook_broker():
    """
    Receive broker callback/webhook notifications (order fills, status updates).

    Authentication: HMAC signature verification.
    The broker signs the payload with a shared secret and includes the
    signature in a request header (varies by broker).

    Common headers:
    - Coinbase: X-CB-SIGNATURE
    - Alpaca: X-Signature
    - Generic: X-Webhook-Signature
    """
    client_ip = request.remote_addr

    # Rate limit check
    if not check_rate_limit(client_ip):
        return jsonify({"error": "Rate limit exceeded"}), 429

    # IP whitelist check
    if not check_ip_whitelist(client_ip):
        return jsonify({"error": "Forbidden"}), 403

    # HMAC signature verification
    raw_body = request.get_data()
    signature = (
        request.headers.get("X-CB-SIGNATURE")
        or request.headers.get("X-Signature")
        or request.headers.get("X-Webhook-Signature")
        or ""
    )

    if not verify_hmac_signature(raw_body, signature, WEBHOOK_SECRET_BROKER):
        db = connect_mongo()
        try:
            log_webhook_event(db, "broker", {}, "auth_failed",
                              metadata={"ip": client_ip})
        finally:
            db.client.close()
        return jsonify({"error": "Invalid signature"}), 401

    # Parse payload
    try:
        payload = request.get_json(silent=True) or {}
    except Exception as e:
        return jsonify({"error": f"Invalid payload: {e}"}), 400

    # Determine broker from header or payload
    broker = "generic"
    if request.headers.get("X-CB-SIGNATURE"):
        broker = "coinbase"
    elif request.headers.get("X-Signature") and "order" in payload:
        broker = "alpaca"

    # Parse into structured event
    event = parse_broker_callback(payload, broker=broker)

    # Log to MongoDB
    db = connect_mongo()
    try:
        status = "error" if "error" in event else "success"
        log_webhook_event(
            db, "broker", payload, status,
            error=event.get("error"),
            metadata={"ip": client_ip, "broker": broker, "event": event},
        )

        if "error" not in event:
            # === PROCESS BROKER EVENT ===
            # Route based on event type:
            #
            # if event["event_type"] == "fill":
            #     update_position(event)
            #     send_fill_alert(event)
            # elif event["event_type"] == "cancel":
            #     handle_cancellation(event)
            # elif event["event_type"] == "reject":
            #     send_error_alert(event)

            print(f"Info: Broker webhook received -- {broker} {event.get('event_type', 'unknown')}")

    finally:
        db.client.close()

    return jsonify({"status": "received"}), 200
```

## Generic Webhook Route (Bearer Token Auth)

```python
@app.server.route("/webhook/generic", methods=["POST"])
def webhook_generic():
    """
    Generic webhook endpoint with Bearer token authentication.

    Use this for custom integrations, monitoring services, or any
    external service that sends HTTP POST notifications.

    Authentication: Authorization: Bearer <token>
    """
    client_ip = request.remote_addr

    # Rate limit check
    if not check_rate_limit(client_ip):
        return jsonify({"error": "Rate limit exceeded"}), 429

    # Bearer token verification
    auth_header = request.headers.get("Authorization", "")
    if not verify_bearer_token(auth_header, WEBHOOK_TOKEN):
        db = connect_mongo()
        try:
            log_webhook_event(db, "generic", {}, "auth_failed",
                              metadata={"ip": client_ip})
        finally:
            db.client.close()
        return jsonify({"error": "Unauthorized"}), 401

    # Parse payload
    try:
        payload = request.get_json(silent=True) or {}
    except Exception:
        payload = {"raw": request.data.decode("utf-8", errors="replace")}

    # Log to MongoDB
    db = connect_mongo()
    try:
        log_webhook_event(
            db, "generic", payload, "success",
            metadata={"ip": client_ip},
        )
        print(f"Info: Generic webhook received from {client_ip}")
    finally:
        db.client.close()

    return jsonify({"status": "received"}), 200
```

## Alternative: Separate Routes File

If the project prefers separation, create `scripts/webhook_routes.py` and import from `app.py`:

```python
# In app.py, after app = dash.Dash(...)
from scripts.webhook_routes import register_webhook_routes
register_webhook_routes(app)
```

With the routes defined as a function:

```python
# scripts/webhook_routes.py
def register_webhook_routes(app):
    @app.server.route("/webhook/tv", methods=["POST"])
    def webhook_tradingview():
        # ... same code as above
```
