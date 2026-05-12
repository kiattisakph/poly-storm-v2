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
    signature_type=1,          # 1=Magic/email, 2=browser wallet proxy
    funder="0xProxyWallet",    # address ที่ถือ funds บน Polymarket
)
```

Signature type ต้องตรงกับ account type:

| Type | ใช้เมื่อไหร่ | funder |
|------|-------------|--------|
| `0` | standalone EOA/private wallet | EOA address หรือเว้นว่าง |
| `1` | Polymarket Magic/email/Google login | proxy wallet address |
| `2` | browser wallet/embedded wallet proxy | proxy wallet address |
| `3` | POLY_1271 | contract wallet address |

ถ้า `/order` ตอบ `invalid signature` ให้เช็คสามอย่างนี้ก่อน:

- private key ต้องเป็น key ของ signer ที่ Polymarket account ใช้จริง
- `signature_type` ต้องตรงกับ account type
- `funder` ต้องเป็น wallet ที่ถือ funds ใน Polymarket profile

หลังเปลี่ยน `signature_type` หรือ `funder` ให้ derive API credentials ใหม่
แล้วอัปเดต `POLY_API_KEY`, `POLY_SECRET`, `POLY_PASSPHRASE`.

### Troubleshooting: Order Signer vs API Key Address

CLOB API ต้องการให้ **order signer address ตรงกับ address ที่ผูก API key**

- API key ถูก derive จาก `signer.address()` (private key address) เสมอ
- `signature_type=0,1,2` → order signer = private key address ✓ (ตรงกับ API key)
- `signature_type=3` (POLY_1271) → order signer = funder/deposit wallet ✗ (ไม่ตรงกับ API key)

**ถ้าเจอ error `"the order signer address has to be the address of the API KEY"`:**
แปลว่า signature_type ทำให้ order signer ไม่ตรงกับ address ที่ผูก API key
→ ใช้ `signature_type=1` (POLY_PROXY) สำหรับ browser wallet / deposit proxy ทั่วไป

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
    signature_type=1,          # ต้องตรงกับ order client
    funder="0xProxyWallet",    # ใช้ EOA address/None เฉพาะ EOA
)

creds = client.create_or_derive_api_key()
# creds.api_key, creds.api_secret, creds.api_passphrase
```

> **หมายเหตุ:** API key จะผูกกับ `signer.address()` (private key address) เสมอ
> ไม่ว่าจะใช้ signature_type อะไร ดังนั้น order signer ต้องตรงกับ address นี้

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
| `client.create_or_derive_api_key()` | สร้าง API credentials |

---

## ข้อจำกัด Exchange

| Rule | ค่า |
|------|-----|
| Min order size | 5 shares |
| Min buy notional | $1.00 |
| Price range | 0.01 – 0.99 |
| Order type | GTC (Good-Til-Cancelled) |
