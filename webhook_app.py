"""
TradingView -> Tradier bridge: the inbound alert receiver.

This is the application's entry point. It runs a small Flask web server that
receives TradingView alerts, checks them, places the matching order on the
Tradier PAPER account, and writes every step into an audit log.

Talking to the broker is the job of tradier.py, beside this file. This module
decides WHETHER to act; that one carries it out.

Routes
------
    POST /webhook   the address TradingView sends alerts to
    GET  /          a plain status page, so you can confirm the app is alive

The alert shape
---------------
It matches exactly what pinescript/supertrend_webhook_strategy.pine sends -
four labelled values and nothing else:

    {"symbol":"AAPL","action":"buy","quantity":10,"token":""}

Anything else TradingView attaches is ignored rather than rejected. That
matters: TradingView adds its own metadata beyond the message you configured,
so a validator that refuses unexpected fields passes every test you write by
hand and then turns away the first real alert.
"""

import hmac
import json
import logging
import os
import time
import uuid
from datetime import datetime, timezone

from flask import Flask, g, jsonify, render_template, request

import config
import tradier

app = Flask(__name__)


# =============================================================================
#  THE AUDIT TRAIL
# =============================================================================
#  There is no database in this project. This log file is the record, so every
#  alert lands in it - accepted or rejected - with a timestamp and, when it was
#  rejected, exactly WHY. "Rejected" on its own is useless at 3am; the reason is
#  the entire value of keeping the trail.

_log = logging.getLogger("webhook")
_log.setLevel(logging.INFO)
_log.propagate = False

if not _log.handlers:
    _formatter = logging.Formatter("%(asctime)sZ %(message)s")
    _formatter.converter = time.gmtime

    _file_handler = logging.FileHandler(config.LOG_FILE, encoding="utf-8")
    _file_handler.setFormatter(_formatter)
    _log.addHandler(_file_handler)

    # Also to stdout, so the entries show up in the cloud host's live log view.
    _stream_handler = logging.StreamHandler()
    _stream_handler.setFormatter(_formatter)
    _log.addHandler(_stream_handler)


SENSITIVE_KEYS = {"token", "secret", "password", "api_key", "apikey", "key"}


def _redact(payload):
    """Blank out the shared secret so the log never becomes a place it leaks."""
    if not isinstance(payload, dict):
        return payload
    clean = {}
    for key, value in payload.items():
        clean[key] = "***REDACTED***" if str(key).lower() in SENSITIVE_KEYS else value
    return clean


def _record(outcome, reason, payload=None, signal=None, broker=None):
    """Write one line of the audit trail and return the entry."""
    entry = {
        "time": datetime.now(timezone.utc).isoformat(),
        # One id per inbound alert, shared by every line that alert produces.
        # Without it the Alerts page could only guess which order came from
        # which alert by reading the lines in order - which stops being true
        # the moment two alerts overlap.
        "alert_id": getattr(g, "alert_id", None),
        "ip": request.remote_addr,
        "outcome": outcome,
        "reason": reason,
    }
    if payload is not None:
        entry["payload"] = _redact(payload)
    if signal is not None:
        entry["signal"] = signal
    if broker is not None:
        # What the broker said, kept as received - id and status on success,
        # the refusal in full on failure.
        entry["broker"] = broker

    _log.info(json.dumps(entry, default=str))
    return entry


# =============================================================================
#  READING THE ALERT
# =============================================================================

def _read_payload():
    """
    Turn the request body into a dict.

    TradingView does not reliably set Content-Type: application/json, so the
    body often arrives as plain text that merely happens to be JSON. Parse the
    raw bytes ourselves rather than trusting the header.

    Returns (payload, error). Exactly one of them is None.
    """
    payload = request.get_json(silent=True)
    if isinstance(payload, dict):
        return payload, None

    raw = request.get_data(as_text=True) or ""
    if not raw.strip():
        return None, "empty request body"

    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError as exc:
        return None, f"body is not valid JSON ({exc.msg} at position {exc.pos})"

    if not isinstance(parsed, dict):
        return None, f"body must be a JSON object, got {type(parsed).__name__}"

    return parsed, None


def _validate(payload):
    """
    Check the four fields we actually use, and let every other field through
    untouched.

    Returns (signal, error). Exactly one of them is None.
    """
    # --- which stock ---
    symbol = str(payload.get("symbol") or "").strip().upper()
    if not symbol:
        return None, "missing 'symbol'"

    # --- buy or sell ---
    action = str(payload.get("action") or "").strip().lower()
    if not action:
        return None, "missing 'action'"
    if action not in config.ALLOWED_ACTIONS:
        allowed = ", ".join(sorted(config.ALLOWED_ACTIONS))
        return None, f"invalid 'action' {action!r} (allowed: {allowed})"

    # --- how many shares ---
    raw_qty = payload.get("quantity")
    if raw_qty is None or (isinstance(raw_qty, str) and not raw_qty.strip()):
        return None, "missing 'quantity'"
    try:
        qty = float(raw_qty)
    except (TypeError, ValueError):
        return None, f"'quantity' is not a number: {raw_qty!r}"
    if qty != qty or qty in (float("inf"), float("-inf")):  # NaN / infinity
        return None, f"'quantity' is not a usable number: {raw_qty!r}"
    if qty <= 0:
        return None, f"'quantity' must be greater than zero, got {qty:g}"
    if qty != int(qty):
        # This build trades plain shares in whole numbers only.
        return None, f"'quantity' must be a whole number of shares, got {qty:g}"

    return {"symbol": symbol, "action": action, "quantity": int(qty)}, None


def _token_ok(payload):
    """
    Check the shared secret, in constant time.

    If no token is configured the check is skipped entirely - at that point the
    only protection is that nobody else knows this endpoint's address.
    """
    if not config.WEBHOOK_TOKEN:
        return True
    supplied = str(payload.get("token") or "")
    return hmac.compare_digest(supplied, config.WEBHOOK_TOKEN)


# --- duplicate suppression ---------------------------------------------------
# TradingView retries a webhook it believes failed, and an identical repeat
# would become a second real order. Held in memory, so it resets on restart and
# is per-process; that is fine for a single-worker single-user bridge.
_recent = {}


def _is_duplicate(signal):
    if config.DUPLICATE_WINDOW_SECONDS <= 0:
        return False

    key = (signal["symbol"], signal["action"], signal["quantity"])
    now = time.monotonic()

    # Drop anything already outside the window so this cannot grow forever.
    for stale in [k for k, seen in _recent.items()
                  if now - seen > config.DUPLICATE_WINDOW_SECONDS]:
        del _recent[stale]

    if key in _recent:
        return True

    _recent[key] = now
    return False


# =============================================================================
#  ROUTES
# =============================================================================

@app.route("/webhook", methods=["POST"])
def webhook():
    """
    Receive one TradingView alert.

    Nothing is acted on until it has passed every check below, and every alert
    is written to the audit log whichever way it goes.

        200  accepted - and the order result, whatever it was
        400  the message was garbled or a field was wrong
        401  the shared secret did not match
        503  no broker credentials, so nothing was sent

    On why a refused order still answers 200: the alert itself was valid and an
    order attempt was genuinely made. An error code invites TradingView to
    retry, and a retry after an order that may have landed is how you end up
    holding twice what you meant to. 503 is reserved for the one case where
    nothing whatsoever was sent, which is the only case safe to repeat.
    """
    g.alert_id = uuid.uuid4().hex[:12]

    payload, error = _read_payload()
    if error:
        # Log the raw text - if it did not parse, that text is all the evidence
        # there is about what actually arrived.
        raw = (request.get_data(as_text=True) or "")[:500]
        _record("rejected", error, payload={"raw_body": raw})
        return jsonify({"status": "rejected", "reason": error}), 400

    # Authenticate before validating, so a stranger poking at the endpoint
    # learns nothing about which fields it expects.
    if not _token_ok(payload):
        _record("rejected", "token missing or does not match", payload=payload)
        return jsonify({"status": "rejected", "reason": "unauthorized"}), 401

    signal, error = _validate(payload)
    if error:
        _record("rejected", error, payload=payload)
        return jsonify({"status": "rejected", "reason": error}), 400

    if _is_duplicate(signal):
        reason = (f"identical alert already handled within "
                  f"{config.DUPLICATE_WINDOW_SECONDS}s")
        _record("ignored", reason, payload=payload, signal=signal)
        return jsonify({"status": "ignored", "reason": reason}), 200

    # ACCEPTED - the alert is sound. Record that before going anywhere near the
    # broker, so the trail shows what arrived even if the order attempt dies.
    _record("accepted", "passed all checks", payload=payload, signal=signal)

    # --- place the order ------------------------------------------------------
    try:
        outcome = tradier.place_order(
            signal["symbol"], signal["action"], signal["quantity"]
        )
    except tradier.BrokerNotConfigured as exc:
        # Nothing was sent, so a retry is safe. 503 says exactly that.
        _record("order_not_attempted", str(exc), signal=signal)
        return jsonify({"status": "broker_not_configured", "reason": str(exc)}), 503
    except Exception as exc:  # never let an unexpected fault vanish
        reason = f"{type(exc).__name__}: {exc}"
        _record("order_failed", reason, signal=signal)
        return jsonify({"status": "order_failed", "reason": reason}), 200

    if outcome["ok"]:
        _record("order_placed", f"broker accepted, order id {outcome['order_id']}",
                signal=signal, broker=outcome)
        return jsonify({
            "status": "accepted",
            "signal": signal,
            "order_id": outcome["order_id"],
            "order_status": outcome["status"],
        }), 200

    # The broker refused, or we could not reach it. Its wording goes into the
    # log and back to the caller untouched - that string is the whole reason
    # anyone can tell later WHY nothing was bought.
    _record("order_rejected", outcome["error"], signal=signal, broker=outcome)
    return jsonify({
        "status": "order_rejected",
        "signal": signal,
        "reason": outcome["error"],
    }), 200


@app.route("/status", methods=["GET"])
def status():
    """A machine-readable health check, for confirming the app is up."""
    return jsonify({
        "app": "TradingView -> Tradier bridge (paper trading)",
        "status": "listening",
        "webhook_path": "/webhook",
        "token_required": bool(config.WEBHOOK_TOKEN),
        "broker": "Tradier sandbox (paper)",
        "broker_configured": tradier.is_configured(),
        "log_file": config.LOG_FILE,
        "time": datetime.now(timezone.utc).isoformat(),
    }), 200


# =============================================================================
#  THE DASHBOARD
# =============================================================================
#  Five read-only pages. Server-rendered, no JavaScript, no auto-refresh - a
#  reload IS the refresh. Nothing on these pages can be clicked to change
#  anything.
#
#  The rule that matters: EVERY PAGE ALWAYS LOADS. If the broker is
#  unreachable, or the log file is missing, or nothing has happened yet, the
#  page still draws and says so plainly. No stack trace ever reaches a viewer.

# Menu order is alphabetical, which is also the order these appear on screen.
PAGES = [
    ("accounts", "Accounts", "/accounts"),
    ("alerts", "Alerts", "/"),
    ("orders", "Orders", "/orders"),
    ("positions", "Positions", "/positions"),
    ("settings", "Settings", "/settings"),
]

MAX_ALERT_ROWS = 200


def _broker_state():
    """
    One description of whether the broker can be reached, shown on every page.

    Returns (state, message) where state is "ok", "unconfigured" or "down".
    """
    if not tradier.is_configured():
        return "unconfigured", "No Tradier credentials set"
    if tradier.get_profile():
        return "ok", "Tradier sandbox reachable"
    return "down", "Tradier sandbox not answering"


def _read_alert_rows():
    """
    Turn the audit log into one row per ALERT - not one row per line written.

    A single alert writes several lines: it is accepted, then an order is
    placed or refused. Those share an alert_id, so they collapse back into one
    row that can be read at a glance and followed through to its order.

    Returns (rows, note). `note` explains an empty result in plain words.
    Never raises: a missing or half-written log must not take the page down.
    """
    path = config.LOG_FILE
    if not os.path.exists(path):
        return [], f"No log file yet ({path}). Rows appear here once an alert arrives."

    try:
        with open(path, "r", encoding="utf-8", errors="replace") as handle:
            lines = handle.readlines()
    except OSError as exc:
        return [], f"Could not read {path}: {exc}"

    rows = {}
    order = []
    last_legacy = None  # see the legacy note below

    for line in lines:
        brace = line.find("{")
        if brace == -1:
            continue
        try:
            entry = json.loads(line[brace:])
        except (json.JSONDecodeError, ValueError):
            continue  # a partly-written final line is normal, not an error
        if not isinstance(entry, dict):
            continue

        outcome = entry.get("outcome")
        if outcome == "startup":
            continue

        # Group by alert id.
        #
        # Lines written before the id existed don't have one. Those were all
        # written by a single worker handling one alert at a time, so an order
        # result belongs to the alert immediately above it - pair them that way
        # rather than leaving every old alert split across two rows. It is a
        # reconstruction, and it would be wrong for overlapping alerts; every
        # line written from now on carries an id and needs no guessing.
        key = entry.get("alert_id")
        if not key:
            if outcome in ("order_placed", "order_rejected", "order_failed",
                           "order_not_attempted") and last_legacy is not None:
                key = last_legacy
            else:
                key = f"legacy:{entry.get('time')}"
                last_legacy = key if outcome == "accepted" else None

        row = rows.get(key)
        if row is None:
            row = {
                "time": entry.get("time", ""),
                "symbol": "-", "action": "-", "quantity": "-",
                "state": "pending", "detail": "", "order_id": None,
            }
            rows[key] = row
            order.append(key)

        signal = entry.get("signal") or {}
        payload = entry.get("payload") or {}
        for field, source in (("symbol", "symbol"), ("action", "action"),
                              ("quantity", "quantity")):
            value = signal.get(source, payload.get(source))
            if value not in (None, ""):
                row[field] = value

        reason = entry.get("reason", "")

        if outcome == "rejected":
            row["state"] = "rejected"
            row["detail"] = reason
        elif outcome == "ignored":
            row["state"] = "ignored"
            row["detail"] = reason
        elif outcome == "accepted":
            # Only a staging post - an order result usually follows.
            if row["state"] == "pending":
                row["detail"] = "Accepted, awaiting broker"
        elif outcome == "order_placed":
            row["state"] = "placed"
            row["order_id"] = (entry.get("broker") or {}).get("order_id")
            row["detail"] = f"order {row['order_id']}"
        elif outcome in ("order_rejected", "order_failed", "order_not_attempted"):
            row["state"] = "failed"
            row["detail"] = reason

    result = [rows[key] for key in reversed(order)][:MAX_ALERT_ROWS]
    if not result:
        return [], "No alerts received yet. They appear here as TradingView sends them."
    return result, None


def _render(template, page, **context):
    """Render a dashboard page with the shell context every page needs."""
    state, message = _broker_state()
    return render_template(
        template,
        pages=PAGES,
        current=page,
        broker_state=state,
        broker_message=message,
        **context,
    )


@app.route("/", methods=["GET"])
def page_alerts():
    """The front door: every alert received, newest first."""
    rows, note = _read_alert_rows()
    return _render("alerts.html", "alerts", rows=rows, note=note)


@app.route("/accounts", methods=["GET"])
def page_accounts():
    balances = tradier.get_balances()
    profile = tradier.get_profile()
    money = balances.get("money_fields", {}) if balances else {}

    # Buying power sits under a different name depending on account type, so
    # take the first that is actually present rather than assuming one.
    buying_power_field = next(
        (name for name in ("margin.stock_buying_power", "cash.cash_available",
                           "stock_buying_power", "total_cash")
         if name in money),
        None,
    )

    return _render(
        "accounts.html", "accounts",
        balances=balances, profile=profile, money=money,
        buying_power_field=buying_power_field,
    )


@app.route("/orders", methods=["GET"])
def page_orders():
    orders = tradier.get_orders()
    # Newest first. Tradier's ids ascend, so they order reliably even when a
    # date field is missing.
    orders = sorted(orders, key=lambda o: o.get("id") or 0, reverse=True)
    return _render("orders.html", "orders", orders=orders)


@app.route("/positions", methods=["GET"])
def page_positions():
    positions = tradier.get_positions()
    positions = sorted(positions, key=lambda p: str(p.get("symbol") or ""))
    return _render("positions.html", "positions", positions=positions)


@app.route("/settings", methods=["GET"])
def page_settings():
    """
    A read-only summary of how this build is configured.

    Never renders a secret's VALUE - only whether it is set.
    """
    return _render(
        "settings.html", "settings",
        token_set=bool(config.WEBHOOK_TOKEN),
        broker_configured=tradier.is_configured(),
        allowed_actions=sorted(config.ALLOWED_ACTIONS),
        duplicate_window=config.DUPLICATE_WINDOW_SECONDS,
        broker_timeout=config.BROKER_TIMEOUT_SECONDS,
        log_file=config.LOG_FILE,
    )


@app.errorhandler(500)
def page_error(error):
    """Even a fault renders as a page, never as a stack trace."""
    return _render("error.html", "alerts", detail=str(error)), 500


if __name__ == "__main__":
    # Development server only. In production a real web server runs this app;
    # that is handled in the deployment step.
    _log.info(json.dumps({
        "time": datetime.now(timezone.utc).isoformat(),
        "outcome": "startup",
        "reason": f"development server on port {config.PORT}",
        "token_required": bool(config.WEBHOOK_TOKEN),
    }))
    app.run(host="0.0.0.0", port=config.PORT, debug=False)
