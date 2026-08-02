"""
Configuration for the TradingView -> Tradier bridge.

EVERYTHING here comes from environment variables. There is deliberately no
settings file, and that is not a stylistic preference:

Once this app is deployed to a cloud host, the files sitting on that host are
whatever was last published from the repository. They are effectively frozen -
the app cannot rewrite them (the container is ephemeral, so any edit vanishes
on the next restart or redeploy), and you cannot edit them from the host's
dashboard either. A "settings file" would therefore be a file you must edit,
commit, and redeploy just to change a value, which is not configuration at all.

Environment variables are the one thing a host lets you change without
republishing the code.

Every variable read below is listed in `.env.example` with a placeholder, and
every one has a sensible default here so the app starts with nothing set.
"""

import os

# Load a local .env file if one is present. On a cloud host there is no .env -
# the host injects the real environment - so this is a no-op there.
try:
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:  # pragma: no cover - dotenv is in requirements.txt
    pass


def _str(name: str, default: str = "") -> str:
    """Read a string setting, falling back to `default` when unset or blank."""
    value = os.environ.get(name)
    if value is None:
        return default
    value = value.strip()
    return value if value else default


def _int(name: str, default: int) -> int:
    """Read a whole-number setting, falling back to `default` if it isn't one."""
    raw = os.environ.get(name, "")
    try:
        return int(str(raw).strip())
    except (TypeError, ValueError):
        return default


def _csv_set(name: str, default: str) -> frozenset:
    """Read a comma-separated list into a lowercase set."""
    raw = _str(name, default)
    return frozenset(item.strip().lower() for item in raw.split(",") if item.strip())


# --- Shared secret -----------------------------------------------------------
# OPTIONAL. When set, every alert must carry a matching "token" field or it is
# rejected. When left empty the check is skipped entirely, and the only thing
# protecting the endpoint is that nobody else knows its address - so treat that
# URL like a password.
WEBHOOK_TOKEN = _str("WEBHOOK_TOKEN")

# --- Audit trail -------------------------------------------------------------
# This project has no database. This file IS the record of every alert.
LOG_FILE = _str("WEBHOOK_LOG_FILE", "webhook.log")

# --- What counts as a valid instruction --------------------------------------
ALLOWED_ACTIONS = _csv_set("ALLOWED_ACTIONS", "buy,sell")

# How long (seconds) to ignore an identical repeat of an alert we just handled.
# TradingView can retry a webhook it thinks failed, and a duplicate would become
# a second real order. Set to 0 to accept every alert, repeats included.
DUPLICATE_WINDOW_SECONDS = _int("DUPLICATE_WINDOW_SECONDS", 5)

# --- Broker (Tradier PAPER account) ------------------------------------------
# Read by the broker module. Missing values are not fatal at startup - they
# produce a clear complaint when an order is actually attempted.
# These must be SANDBOX credentials. The broker module cannot reach a live
# account: its base URL is hard-coded to Tradier's paper host.
TRADIER_TOKEN = _str("TRADIER_TOKEN")
TRADIER_ACCOUNT_ID = _str("TRADIER_ACCOUNT_ID")

# How long to wait on Tradier before giving up, in seconds. Keep this SHORT.
# TradingView abandons a webhook after only a few seconds, so this app has to
# give up first and log why - a slow failure is worse than a quick one.
BROKER_TIMEOUT_SECONDS = _int("BROKER_TIMEOUT_SECONDS", 4)

# --- Local development only --------------------------------------------------
# On a cloud host the production web server binds the port the host hands it;
# this is only used by the built-in development server.
PORT = _int("PORT", 5000)

