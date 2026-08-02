# Webhook Events Display Page (`pages/webhooks.py`)

Dashboard page to view webhook event history and status.

```python
"""
Webhooks page -- displays webhook event history with status tracking.
"""

import dash_bootstrap_components as dbc
from dash import html


def update_webhooks():
    return ""


def serve_webhooks(username="", color_mode="Dark"):
    """Display webhook event history from MongoDB."""
    from scripts.database_manager import connect_mongo
    from constants import WEBHOOK_EVENTS_COLLECTION

    text_color = "white" if color_mode == "Dark" else "#333333"

    db = connect_mongo()
    try:
        events = list(
            db.get_collection(WEBHOOK_EVENTS_COLLECTION)
            .find({})
            .sort("datetime", -1)
            .limit(100)
        )
    finally:
        db.client.close()

    # Build table
    table_header = html.Thead(html.Tr([
        html.Th("Time"), html.Th("Source"), html.Th("Status"),
        html.Th("Details"), html.Th("IP"),
    ]))

    status_colors = {
        "success": "green",
        "auth_failed": "red",
        "parse_error": "orange",
        "rate_limited": "yellow",
        "error": "red",
    }

    rows = []
    for event in events:
        status = event.get("status", "unknown")
        status_color = status_colors.get(status, "gray")

        # Build details summary
        details = ""
        metadata = event.get("metadata", {})
        signal = metadata.get("signal", {})
        if signal:
            details = f"{signal.get('action', '')} {signal.get('symbol', '')}".strip()
        elif event.get("error"):
            details = event["error"][:80]

        rows.append(html.Tr([
            html.Td(event.get("datetime", "")),
            html.Td(event.get("source", "")),
            html.Td(html.Span(status, style={"color": status_color, "fontWeight": "bold"})),
            html.Td(details, style={"maxWidth": "300px", "overflow": "hidden"}),
            html.Td(metadata.get("ip", "")),
        ]))

    table = dbc.Table(
        children=[table_header, html.Tbody(rows)],
        bordered=True, hover=True, responsive=True,
        className="table-dark" if color_mode == "Dark" else "",
    )

    page = html.Div(children=[
        dbc.Container(children=[
            html.H3("Webhook Events", style={"color": text_color, "marginBottom": "20px"}),
            table if events else html.P("No webhook events yet.", style={"color": text_color}),
            html.Div(className="page-footer-spacer"),
        ], fluid=True),
    ])

    return page
```

**Register** in `pages/__init__.py`, `display_page()`, `PAGE_TITLES`, `NAVBAR_PAGE_EMOJIS` (`"webhooks": "..."`).
