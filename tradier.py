"""
Tradier broker module - the only thing in this project that talks to a broker.

PAPER TRADING ONLY
------------------
The base URL below is Tradier's SANDBOX host, hard-coded on purpose. It is
deliberately NOT configurable: there is no environment variable, no flag and no
code path that can point this build at a live-money account. If you ever want
that, it should be a considered change to this file, not a setting someone can
flip by accident.

What it does
------------
    place_order()     send one plain market order for whole shares
    get_balances()    what is in the account
    get_orders()      recent orders
    get_positions()   what is currently held
    fetch_raw()       dump an endpoint's raw response, for verifying shapes

Two rules shape everything here:

  * Placing an order may fail LOUDLY, and when the broker refuses, the refusal
    comes back word for word. The broker's own wording is the most valuable
    string in this system - the difference between "something went wrong" and
    "this account isn't approved for that symbol". It is never replaced with
    our own phrasing, never reduced to "failed", never dropped.

  * Reading may NOT fail loudly. If Tradier is unreachable or answers with
    something unexpected, the read functions return empty. Whatever is calling
    them has to survive a bad day at the broker.

Field names and endpoints here were taken from Tradier's documentation
(https://docs.tradier.com) and cross-checked against the tradier_api Python
package's source. Response SHAPES still deserve confirmation against a real
reply from your own paper account - use fetch_raw() for that.
"""

import json

import requests

import config


# Tradier's paper-money host. See the note at the top of this file: not a
# setting, on purpose.
SANDBOX_BASE_URL = "https://sandbox.tradier.com/v1"


class BrokerNotConfigured(RuntimeError):
    """Raised when the Tradier credentials are missing or still placeholders."""


class BrokerError(RuntimeError):
    """Raised when a call to Tradier could not be completed at all."""


# =============================================================================
#  CREDENTIALS
# =============================================================================

# The values shipped in .env.example. If these are still in place, nothing has
# been filled in yet, and saying so beats a puzzling 401 from Tradier.
_PLACEHOLDERS = {
    "your_sandbox_access_token_here",
    "your_sandbox_account_id_here",
    "",
}


def _credentials():
    """
    Fetch the sandbox token and account id from the environment.

    Deliberately called at request time, never at import time: a missing
    credential must produce a clear complaint when an order is attempted, not
    stop the whole app from starting.
    """
    token = config.TRADIER_TOKEN
    account_id = config.TRADIER_ACCOUNT_ID

    missing = []
    if token in _PLACEHOLDERS:
        missing.append("TRADIER_TOKEN")
    if account_id in _PLACEHOLDERS:
        missing.append("TRADIER_ACCOUNT_ID")

    if missing:
        raise BrokerNotConfigured(
            f"Tradier credentials not set: {', '.join(missing)} "
            f"{'is' if len(missing) == 1 else 'are'} missing or still the "
            f"placeholder value from .env.example. Set them in .env locally, "
            f"or in the host's environment settings once deployed. "
            f"Use SANDBOX (paper) credentials only."
        )

    return token, account_id


def is_configured():
    """True when usable credentials are present. Never raises."""
    try:
        _credentials()
        return True
    except BrokerNotConfigured:
        return False


def _headers(token):
    return {
        "Authorization": f"Bearer {token}",
        "Accept": "application/json",
    }


# =============================================================================
#  TALKING TO TRADIER
# =============================================================================
#  Answer fast, or fail fast. TradingView gives a webhook only a few seconds
#  before it gives up, so this module must give up FIRST and say why. A slow
#  failure here is worse than a quick one - the alert is lost either way, but a
#  quick one leaves a usable log line instead of a timeout at the far end.

def _request(method, path, params=None, timeout=None):
    """
    Make one HTTP call to Tradier.

    Returns (status_code, parsed_json_or_None, raw_text).
    Raises BrokerError only when no response was obtained at all.
    """
    token, _ = _credentials()
    url = f"{SANDBOX_BASE_URL}{path}"
    timeout = timeout or config.BROKER_TIMEOUT_SECONDS

    try:
        response = requests.request(
            method,
            url,
            headers=_headers(token),
            data=params if method == "POST" else None,
            params=params if method == "GET" else None,
            timeout=timeout,
        )
    except requests.Timeout as exc:
        raise BrokerError(
            f"Tradier did not answer within {timeout}s ({method} {path}): {exc}"
        ) from exc
    except requests.RequestException as exc:
        raise BrokerError(
            f"Could not reach Tradier ({method} {path}): {exc}"
        ) from exc

    raw_text = response.text or ""
    try:
        payload = response.json()
    except ValueError:
        payload = None

    return response.status_code, payload, raw_text


def _broker_message(status_code, payload, raw_text):
    """
    Pull the broker's own words out of a failed response, verbatim.

    Tradier refuses in more than one shape:
      {"errors": {"error": "message"}}
      {"errors": {"error": ["message one", "message two"]}}
      {"fault": {"faultstring": "...", "detail": {...}}}   <- API gateway, e.g. bad token

    If none of those match, the raw body is returned untouched rather than
    replaced with a guess. Whatever comes back is the broker's wording, not
    ours - we only add the HTTP status so the log says how it failed too.
    """
    detail = None

    if isinstance(payload, dict):
        errors = payload.get("errors")
        if isinstance(errors, dict):
            error = errors.get("error")
            if isinstance(error, list):
                detail = "; ".join(str(item) for item in error)
            elif error is not None:
                detail = str(error)
        elif isinstance(errors, list):
            detail = "; ".join(str(item) for item in errors)
        elif errors is not None:
            detail = str(errors)

        if detail is None:
            fault = payload.get("fault")
            if isinstance(fault, dict):
                detail = str(fault.get("faultstring") or json.dumps(fault))

    if detail is None:
        detail = raw_text.strip() or "(empty response body)"

    # Tradier refuses a bad symbol with HTTP 200 and an errors body, so an
    # "HTTP 200:" prefix would read as nonsense. Only mention the status when
    # the call itself failed. The full status and raw body are recorded on the
    # result either way, so nothing is lost from the audit trail.
    if status_code == 200:
        return detail
    return f"HTTP {status_code}: {detail}"


def _as_list(value, key):
    """
    Normalise one of Tradier's collection envelopes into a list.

    Two shapes bite here, and both are verified behaviour rather than defensive
    guessing:
      * a SINGLE item comes back as an object, not a one-item array
      * an EMPTY collection comes back as the string "null", not [] or None
    """
    if not isinstance(value, dict):
        return []

    inner = value.get(key)
    if isinstance(inner, list):
        return [item for item in inner if isinstance(item, dict)]
    if isinstance(inner, dict):
        return [inner]
    return []


# =============================================================================
#  PLACING AN ORDER  (may fail loudly)
# =============================================================================

def place_order(symbol, side, quantity, preview=False):
    """
    Place one plain market order, good for the day, in whole shares.

    Args:
        symbol (str):   ticker, e.g. "AAPL"
        side (str):     "buy" or "sell"
        quantity (int): whole shares, greater than zero
        preview (bool): ask Tradier to validate WITHOUT placing it. Nothing
                        reaches the account. Useful for a dry run.

    Returns a dict, always with the same keys:
        ok          (bool)  did the broker accept it
        order_id    (int|None)  the id, for finding it afterwards
        status      (str|None)  Tradier's own status word
        error       (str|None)  the broker's refusal, VERBATIM, when ok is False
        http_status (int|None)
        raw         (str)   the response body as received, for the audit log
        request     (dict)  exactly what was sent

    Raises BrokerNotConfigured when credentials are missing. Every other
    failure comes back as ok=False with the reason filled in - including a
    timeout, so the caller always gets something worth logging.
    """
    _, account_id = _credentials()

    # The six parameters Tradier requires for an equity order. Form-encoded.
    params = {
        "class": "equity",
        "symbol": str(symbol).strip().upper(),
        "side": str(side).strip().lower(),
        "quantity": str(int(quantity)),
        "type": "market",
        "duration": "day",
    }
    if preview:
        params["preview"] = "true"

    result = {
        "ok": False,
        "order_id": None,
        "status": None,
        "error": None,
        "http_status": None,
        "raw": "",
        "request": dict(params),
        "preview": bool(preview),
    }

    try:
        status_code, payload, raw_text = _request(
            "POST", f"/accounts/{account_id}/orders", params=params
        )
    except BrokerError as exc:
        # Could not even get a reply. Say so plainly - never silently.
        result["error"] = str(exc)
        return result

    result["http_status"] = status_code
    result["raw"] = raw_text[:2000]

    order = payload.get("order") if isinstance(payload, dict) else None

    if status_code == 200 and isinstance(order, dict):
        result["ok"] = True
        result["order_id"] = order.get("id")
        result["status"] = order.get("status")
        return result

    # Anything else is a refusal. Hand back what the broker actually said.
    result["error"] = _broker_message(status_code, payload, raw_text)
    return result


# =============================================================================
#  READING THE ACCOUNT  (must never blow up)
# =============================================================================

def get_balances():
    """
    What is in the account. Returns {} if anything at all goes wrong.

    NOTE ON THE MONEY FIELDS. A Tradier balances payload carries several
    numbers that all plausibly mean "how much money is in here" - total_equity,
    total_cash, and, depending on whether the account is cash or margin, a
    nested cash.cash_available or margin buying-power figure. They are NOT
    interchangeable, and on a sandbox account one of them can read 0 while the
    real figure sits right beside it under a different name.

    So this deliberately does not pick one and call it "the balance". It hands
    back Tradier's payload untouched, plus a "money_fields" map of every
    candidate it actually found, each with its real field name. Whatever
    displays this can then show a number it can name.
    """
    try:
        _, account_id = _credentials()
        status_code, payload, _ = _request("GET", f"/accounts/{account_id}/balances")
    except (BrokerNotConfigured, BrokerError):
        return {}

    if status_code != 200 or not isinstance(payload, dict):
        return {}

    balances = payload.get("balances")
    if not isinstance(balances, dict):
        return {}

    # Collect EVERY numeric field Tradier actually sent, under its real name -
    # rather than a hand-written list of names we expect. A fixed list quietly
    # misses whatever it did not anticipate, and the miss looks like a zero.
    #
    # A real sandbox reply makes the point: it carries BOTH `equity` (0) and
    # `total_equity` (the actual figure). Pick by the name that "looks right"
    # and the account reads as empty while the real number sits beside it.
    money_fields = {}
    for name, value in balances.items():
        if isinstance(value, bool):
            continue
        if isinstance(value, (int, float)):
            money_fields[name] = value
        elif isinstance(value, dict):
            # cash / margin / pdt - whichever this account type returns.
            for sub_name, sub_value in value.items():
                if isinstance(sub_value, (int, float)) and not isinstance(sub_value, bool):
                    money_fields[f"{name}.{sub_name}"] = sub_value

    result = dict(balances)
    result["money_fields"] = money_fields
    return result


def get_profile():
    """
    The account's own record - number, type, and status.

    Balances does NOT carry a status field; the user profile does. Returns {}
    if anything goes wrong, like every other read here.
    """
    try:
        _, account_id = _credentials()
        status_code, payload, _ = _request("GET", "/user/profile", timeout=None)
    except (BrokerNotConfigured, BrokerError):
        return {}

    if status_code != 200 or not isinstance(payload, dict):
        return {}

    profile = payload.get("profile")
    if not isinstance(profile, dict):
        return {}

    # Same envelope quirk as orders and positions: one account comes back as an
    # object, several come back as a list.
    accounts = profile.get("account")
    if isinstance(accounts, dict):
        accounts = [accounts]
    elif not isinstance(accounts, list):
        accounts = []

    for account in accounts:
        if isinstance(account, dict) and str(account.get("account_number")) == str(account_id):
            return account

    return accounts[0] if accounts and isinstance(accounts[0], dict) else {}


def get_orders():
    """Recent orders, newest as Tradier returns them. Returns [] on any failure."""
    try:
        _, account_id = _credentials()
        status_code, payload, _ = _request(
            "GET", f"/accounts/{account_id}/orders", params={"includeTags": "true"}
        )
    except (BrokerNotConfigured, BrokerError):
        return []

    if status_code != 200 or not isinstance(payload, dict):
        return []

    return _as_list(payload.get("orders"), "order")


def get_positions():
    """What is currently held. Returns [] on any failure."""
    try:
        _, account_id = _credentials()
        status_code, payload, _ = _request("GET", f"/accounts/{account_id}/positions")
    except (BrokerNotConfigured, BrokerError):
        return []

    if status_code != 200 or not isinstance(payload, dict):
        return []

    return _as_list(payload.get("positions"), "position")


# =============================================================================
#  VERIFYING SHAPES AGAINST A REAL ACCOUNT
# =============================================================================

def fetch_raw(path):
    """
    Call an account endpoint and hand back the untouched response body.

    Documentation and SDK source are starting points, not the finish line. When
    a response shape matters, this is how you confirm it against a real reply
    instead of writing code against a guess.

        fetch_raw("/balances")   fetch_raw("/orders")   fetch_raw("/positions")

    Returns (status_code, raw_text). Read-only endpoints only - it cannot place
    an order, since it only ever issues GET.
    """
    _, account_id = _credentials()
    status_code, _, raw_text = _request("GET", f"/accounts/{account_id}{path}")
    return status_code, raw_text
