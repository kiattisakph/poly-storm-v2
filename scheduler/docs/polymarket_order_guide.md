# Polymarket CLOB Order API — วิธีส่ง Order ผ่าน py-clob-client-v2

---

## 1. สร้าง Client

```python
from py_clob_client_v2 import ClobClient, ApiCreds

creds = ApiCreds(
    api_key="xxx",
    api_secret="xxx",
    api_passphrase="xxx",
)

client = ClobClient(
    host="https://clob.polymarket.com",
    chain_id=137,
    key="0xYourPrivateKey",
    creds=creds,
    signature_type=2,          # 0=EOA, 1=POLY_PROXY, 2=GNOSIS_SAFE
    funder="0xProxyWallet",    # ถ้าใช้ proxy wallet
)
```

---

## 2. ดึง Tick Size (จำเป็นก่อนส่ง order)

```python
tick_size = client.get_tick_size(token_id)
# return: "0.01" หรือ "0.001"
```

---

## 3. ส่ง Order (Buy / Sell)

```python
from py_clob_client_v2 import OrderArgs, OrderType, PartialCreateOrderOptions, Side

args = OrderArgs(
    token_id="CONDITION_TOKEN_ID",   # token ID ของ outcome (YES/NO)
    price=0.55,                       # ราคา (0.01 - 0.99)
    size=10.0,                        # จำนวน shares (ขั้นต่ำ 5)
    side=Side.BUY,                    # Side.BUY หรือ Side.SELL
)

options = PartialCreateOrderOptions(tick_size=tick_size)

response = client.create_and_post_order(
    args,
    options=options,
    order_type=OrderType.GTC,         # Good-Til-Cancelled
)
```

**Response:**
```json
{
  "orderID": "0xabc123...",
  "status": "live"
}
```

---

## 4. Cancel Order

```python
response = client.cancel(order_id)
```

**Response:**
```json
{
  "canceled": ["0xabc123..."],
  "not_canceled": {}
}
```

---

## 5. Query Order Status

```python
response = client.get_order(order_id)
```

**Response fields:**
| Field | คำอธิบาย |
|-------|----------|
| `status` | `live`, `matched`, `filled`, `cancelled`, `rejected`, `expired` |
| `size_matched` | จำนวน shares ที่ fill แล้ว |
| `price` | ราคาเฉลี่ย |

---

## 6. ดึง Open Orders

```python
from py_clob_client_v2 import OpenOrderParams

orders = client.get_orders(OpenOrderParams())
```

---

## 7. ตรวจ Balance / Allowance

```python
from py_clob_client_v2 import AssetType, BalanceAllowanceParams

# ตรวจ USDC (สำหรับ BUY)
params = BalanceAllowanceParams(
    asset_type=AssetType.COLLATERAL,
    token_id=None,
    signature_type=2,
)

# ตรวจ Conditional Token (สำหรับ SELL)
params = BalanceAllowanceParams(
    asset_type=AssetType.CONDITIONAL,
    token_id="TOKEN_ID",
    signature_type=2,
)

response = client.get_balance_allowance(params)
# response: {"balance": ..., "allowance": ...}
```

---

## 8. Derive API Credentials (ครั้งแรก)

```python
from py_clob_client_v2 import ClobClient

client = ClobClient(
    host="https://clob.polymarket.com",
    key="0xYourPrivateKey",
    chain_id=137,
    signature_type=0,
    funder=None,
)

creds = client.create_or_derive_api_creds()
# creds.api_key, creds.api_secret, creds.api_passphrase
```

---

## สรุป API Methods ที่ใช้

| Method | หน้าที่ |
|--------|---------|
| `client.get_tick_size(token_id)` | ดึง tick size ของ token |
| `client.create_and_post_order(args, options, order_type)` | ส่ง limit order |
| `client.cancel(order_id)` | ยกเลิก order |
| `client.get_order(order_id)` | ดูสถานะ order |
| `client.get_orders(OpenOrderParams())` | ดึง open orders ทั้งหมด |
| `client.get_balance_allowance(params)` | ตรวจ balance/allowance |
| `client.create_or_derive_api_creds()` | สร้าง API credentials |

---

## ข้อจำกัด Exchange

| Rule | ค่า |
|------|-----|
| Min order size | 5 shares |
| Min buy notional | $1.00 |
| Price range | 0.01 – 0.99 |
| Order type | GTC (Good-Til-Cancelled) |
