# Webhook Testing and Audit Checklist

## Test the Full Pipeline

### TradingView webhook:
```bash
# Success case
curl -X POST http://localhost:8080/webhook/tv?secret=YOUR_SECRET \
  -H "Content-Type: application/json" \
  -d '{"action": "buy", "symbol": "ETHUSD", "price": 3500.00}'

# Expected: 200 {"status": "received", "signal": {...}}

# Auth failure
curl -X POST http://localhost:8080/webhook/tv?secret=wrong \
  -H "Content-Type: application/json" \
  -d '{"action": "buy", "symbol": "ETHUSD"}'

# Expected: 401 {"error": "Unauthorized"}

# Missing required field
curl -X POST http://localhost:8080/webhook/tv?secret=YOUR_SECRET \
  -H "Content-Type: application/json" \
  -d '{"symbol": "ETHUSD"}'

# Expected: 400 {"error": "Missing required field: 'action' (buy/sell)"}
```

### Broker callback:
```bash
# Generate HMAC signature for testing
python -c "
import hmac, hashlib, json
body = json.dumps({'type': 'fill', 'order_id': '123', 'product_id': 'ETH-USD'})
sig = hmac.new(b'YOUR_BROKER_SECRET', body.encode(), hashlib.sha256).hexdigest()
print(f'Signature: sha256={sig}')
print(f'Body: {body}')
"
```

### Check MongoDB:
1. Run the app and send test webhooks
2. Check `webhook_events` collection for logged events
3. Verify auth failures are logged with IP
4. Verify payloads have secrets redacted
5. Check webhooks page in the dashboard

---

## Audit Mode (Gold Standard Checklist)

| Feature | TV Webhook | Broker Callback | Generic | Check |
|---|---|---|---|---|
| Flask route on `app.server` | Yes | Yes | Yes | |
| Authentication (secret/HMAC/bearer) | Yes (secret) | Yes (HMAC) | Yes (bearer) | |
| Constant-time comparison (`hmac.compare_digest`) | Yes | Yes | Yes | |
| Rate limiting per IP | Yes | Yes | Yes | |
| IP whitelist support | No | Yes | No | |
| JSON payload parsing | Yes | Yes | Yes | |
| Fallback for non-JSON bodies | Yes | No | Yes | |
| Structured signal/event parsing | Yes | Yes | No | |
| MongoDB event logging | Yes | Yes | Yes | |
| Payload sanitization (secrets redacted) | Yes | Yes | Yes | |
| Failed auth logged with IP | Yes | Yes | Yes | |
| Pipeline routing (queue or execute) | Yes | Yes | N/A | |
| Webhook events display page | Yes | Yes | Yes | |
| `BASE_URL` configured for external access | Yes | Yes | Yes | |
| Error handling (no crash on bad payload) | Yes | Yes | Yes | |
