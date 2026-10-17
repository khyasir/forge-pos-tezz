# Tezz POS User Guide

This guide is for the shop owner, the manager and the cashier.
Each section has short steps and a real example.

Open the app at `http://localhost:8120` (or the address your installer gave you).
API documentation for developers is at `/api/docs` (Swagger) and `/api/redoc`.

---

## 1. Logging in

Each person logs in with a 4-digit PIN.

Demo PINs (company "Lahore Karahi House"):

| Role | PIN | What they can do |
|---|---|---|
| Owner | `1111` | Everything, including Back Office and settings |
| Manager | `2222` | Back Office, refunds, shifts, Odoo import |
| Cashier | `3333` | Take orders, take payment, park orders |

Odoo staging company ("Camel Step (Odoo staging)"): manager PIN `4444`.
It uses the branch "Odoo Test Branch". Enter its branch id on the login screen.

**Steps**
1. Choose the branch (for example "Gulberg").
2. Choose the terminal (for example "Terminal 1"). This is optional.
3. Type your PIN on the keypad. You log in as soon as you type the 4th digit.

**Example:** Sana is a cashier. She picks "Gulberg", "Terminal 1" and types `3333`. The Cashier screen opens.

---

## 2. Taking a new order

**Steps**
1. Tap a product tile. It goes into the cart on the right.
2. Tap it again to add one more. Or use the `+` and `-` buttons in the cart.
3. If the product has options (for example size or extra cheese), a box opens. Pick the options and tap **Add**.
4. Pick the order type at the top of the cart: **Dine-in**, **Takeaway** or **Delivery**.
5. For Dine-in, pick a table.
6. Tap **Pay**. Choose **Cash**, **Card**, **JazzCash**, **Easypaisa** or **Raast QR**.
7. For cash, type the amount the customer gave. The app shows the change.
8. Tap **Confirm payment**. The receipt opens. Tap **Print** if you need paper.

**Example:** Table 4 orders 2 Chicken Biryani (Rs. 450 each).
Tap "Chicken Biryani" twice, choose Dine-in, pick Table 4, tap Pay, choose Cash, type 1100, tap Confirm payment.
The receipt shows the sales tax, the Rs. 1 POS fee and the FBR/PRA invoice number with a QR code.

Product pictures appear on the tiles. If a product has no picture, the tile shows its initials in a colour.

---

## 3. Keeping several orders open (park and switch)

Use this when a customer walks away before paying, and you need to serve the next person.

**Steps**
1. While an order is in the cart, tap **Park order** (top of the cart).
2. The cart is now empty and has a new number, for example `#2`. Take the next order.
3. The **Open orders** button at the top shows how many orders are open. When more than one is open, the number turns orange.
4. Tap **Open orders**. You see every open order with its items, total and time.
5. Tap an order to continue it. Tap **Discard** to throw it away (the app asks first).
6. Tap **+ New order** to start a fresh order.

Open orders are saved on the device. They stay after a page reload, a browser crash or a power cut. They also work with no internet.

**Example:**
1. Ali orders a Seekh Kabab, then says "wait, I will call my friend".
2. Tap **Park order**. Ali's order is `#1`.
3. Sara orders 2 Chicken Biryani. This is `#2`. The button shows **Open orders 2**.
4. Ali comes back. Tap **Open orders**, then tap `#1 Dine-in`. His Seekh Kabab is back in the cart.
5. Take Ali's payment. Sara's order `#2` is still waiting.

Note: two browser tabs on the same device share the same list of open orders.

---

## 4. Delivery orders

**Steps**
1. Add products to the cart.
2. Tap **Delivery** at the top of the cart.
3. The **Delivery fee** box shows the default fee (set by the owner, see section 8). Change it if needed.
4. Type the **Delivery address**.
5. Tap **Pay** and finish as usual.

The delivery fee is shown on the receipt as "Delivery Charges".
Sales tax is charged on the food and on the delivery fee, as PRA requires.
The address is printed on the receipt as "Deliver to".
The fee also goes to FBR/PRA as its own line ("Delivery Charges") and to Odoo.

**Example:** Kabuli Pulao Rs. 500, delivery fee Rs. 150, paid in cash (PRA 16%).
- Food: Rs. 500
- Delivery charges: Rs. 150
- Sales tax: 16% of 650 = Rs. 104
- POS fee: Rs. 1
- Total: Rs. 755

---

## 5. Working with no internet (offline orders)

The cashier screen keeps working when the internet is down.

**What happens**
1. The badge at the top shows **Offline**.
2. You take orders and payments as normal. The receipt says the sale will sync later.
3. Each order is saved on the device first.
4. When the internet comes back, the app sends the orders on its own. You do not need to press anything.
5. The server then sends the invoice to FBR/PRA and the order to Odoo.

**Checking sync**
1. Open **Sync Status** in the left menu.
2. The table "Not yet on the server" lists orders still on the device.
3. A failed row shows the reason and the time of the next automatic retry.
4. The app retries on its own after 5 seconds, then 10, 20, 40 seconds and so on, up to every 5 minutes.
5. You can still press **Retry** or **Retry all** to try at once.

**Example:** The internet drops at 1:00 pm. Sana sells 3 orders. The top badge says "3 pending".
At 1:20 pm the internet comes back. Within a few seconds the badge goes to 0 and Sync Status shows all 3 as synced, with FBR invoice numbers.

**Safe against duplicates.** Each order has a fixed id from the moment it is started.
Double-clicking Pay, a lost connection in the middle of payment, two tabs, or a crash during sync can never create the same order twice in Tezz, FBR or Odoo.

---

## 6. FBR / PRA and Odoo failures

Sometimes FBR or Odoo is down. The order is still paid and saved.

- The server retries FBR and Odoo by itself. It waits 30 seconds, then 1, 2, 4 minutes and so on, up to once an hour.
- Sync Status shows the order as "failed" with the reason until a retry works.
- You can press **Retry** to try at once.

---

## 7. Refunds and voids

There is no refund or void button on the screen yet. Today they are done through the API (for example from Swagger at `/api/docs`, or by your developer).

- **Void**: cancels an order that is not paid yet. `POST /api/v1/orders/{order_id}/void`
- **Refund**: for a paid order. `POST /api/v1/orders/{order_id}/refund` with `{"reason": "..."}`

**Example:** A customer returns a cold Karahi on order G-00031. The manager opens `/api/docs`, finds "refund", enters the order id and the reason "food was cold", and runs it. The order status becomes "refunded".

To keep an order that is not paid, use **Park order** (section 3), not void.

---

## 8. Back Office settings (owner and manager)

Open **Back Office** in the left menu.

| Tab | What you do there |
|---|---|
| Products | Add or delete products. Upload, change or remove a product picture. |
| Categories | Add categories such as "Karahi" or "BBQ". |
| Modifiers | Option groups such as "Spice level" or "Size". |
| Tables | Floors and tables. |
| API Keys | Keys for other software that uses the Tezz API. |
| Settings | Default delivery fee and Odoo product import. |

**Upload a product picture**
1. Open Back Office, then Products.
2. Find the product. Tap **Upload** (or **Change**) under Image.
3. Choose a PNG, JPG, WEBP or GIF file, up to 1.5 MB.
4. The picture appears in the list and on the cashier tiles after the cashier screen reloads.

**Set the default delivery fee**
1. Open Back Office, then Settings.
2. Type the fee, for example `150`.
3. Tap **Save**. New delivery orders will start with this fee.

---

## 9. Importing products from Odoo

Tezz can copy products from Odoo. It only reads from Odoo. It never changes Odoo products.

**What is imported**
- Every active product with "Available in POS" ticked (except gift cards and modifier items).
- Picture, POS price, POS category and barcode/code.
- Modifiers (for example "Extra cheese") as Tezz option groups.
- Variant attributes (for example "Zone: R" or "Size: 42"). They show under the product name.
- Customers with a mobile number.

Products that are no longer "Available in POS" in Odoo are hidden in Tezz, not deleted.
Pictures uploaded in Tezz are kept. They are not replaced by the Odoo picture.

**Steps**
1. The server must be set up with the Odoo settings (see `docs/odoo-wags.md`).
2. Log in as owner or manager of the Odoo company.
3. Open Back Office, then Settings, then tap **Import from Odoo now**.
4. Wait for the message, for example "Imported 420 products (66 with images), 44 modifiers, 10 categories, 200 customers".

You can run it again any time. It updates the same products and does not make copies.

**Orders to Odoo.** Each paid order is sent to Odoo as a draft quotation (`sale.order.wags`) on branch 24 "Test".
It is never confirmed and nothing is sent to ZATCA.
The quotation note starts with "TEZZ-TEST" and includes the order type and the delivery fee and address.

---

## 10. Shifts and Z report

1. At the start of the day open **Shifts** and tap **Open shift**. Type the cash in the drawer.
2. At the end tap **Close shift** and count the cash.
3. The Z report shows sales by payment type and any cash over or short.

---

## 11. Quick answers

- **The Open orders number is orange.** More than one order is open. Tap it to see them.
- **"pending" stays above 0.** Check the internet. Open Sync Status to see the reason.
- **A product has no picture.** Upload one in Back Office, Products. Or add it in Odoo and run the import.
- **I need the API.** Open `/api/docs`. Every endpoint, including product images (`PUT /api/v1/products/{id}/image`) and delivery fields on orders, is listed there.

## 12. Updating to a new version

Run these in the `forge-pos-tezz` folder:

```
git pull
docker compose up -d --build
```

Then open http://localhost:8120 and press **Cmd+Shift+R** (Mac) or **Ctrl+Shift+R** (Windows) once.

You do **not** need `docker compose down -v`. That command deletes all orders and resets the demo data.

**The cashier screen shows no products.** Versions before T6.1 kept an old login after the database was reset or the 12-hour login expired. Every catalog request was then refused, and the screen stayed empty. From T6.1 the app sends you back to the PIN screen with the message "Your session has expired". Enter your PIN again and the products load. Offline orders saved on the device are kept and sync after you log in.
