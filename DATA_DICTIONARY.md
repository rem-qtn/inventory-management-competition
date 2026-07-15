# Data dictionary

All CSV files are UTF-8, comma-delimited and quoted as needed. There are no
blank values: `NOT_APPLICABLE` marks text that does not apply and numeric
inapplicability is zero.

| File | Grain | Purpose |
|---|---|---|
| item_master | item | Product, packaging, sourcing, cost, service and lifecycle attributes. |
| supplier_master | supplier | Origin, mode, lead-time, calendar, commercial and reliability terms. |
| customer_master | customer | B2B segment, channel and region. |
| sales_orders / sales_order_lines | order / line | Public attempts eligible to be filled or backordered. `fulfilled_quantity` and `cancelled_quantity` are known only once final. |
| purchase_orders | PO line | Incumbent replenishment and receipt history. Closed POs carry received/rejected quantities and actual receipt date; open POs have `is_open = 1`. |
| inventory_movements | event | Auditable receipt, shipment, return, rejection and adjustment ledger. Quantities are signed only through `direction`; `quantity` is positive. |
| daily_stock_history | item-day | Daily opening/closing stock and backlog. Receipts are available before allocation. |
| current_inventory | item | Opening state at 2026-07-01. |

`inventory_movements.source_transaction_id` references a PO line, sales
order line, return, or adjustment identifier. `stockout_flag` means demand
could not be fully served on the date; it does not disclose lost demand.

Instructor-only `latent_demand_history.csv` contains historical unconstrained
demand; `future_daily_demand.csv` contains only the fixed item-day demand
trajectory for July 2026–June 2027. No future receipt, shipment, stock, or
lead-time outcome is pre-generated. Do not release either file.

`purchase_orders` retains a one-year pre-period document lookback only where
needed to preserve receipt traceability at the start of the public history.

Annual supplier-rebate agreement terms are held in `supplier_master`: agreement
year, annual qualifying-spend threshold, rate, and qualifying definition.

The competition treats the business as continuing beyond June 2027. Ending
inventory is therefore valued at full current buy cost, not liquidated at a
discount. Receipt purchase cost is charged when stock arrives; the final
continuing-inventory adjustment offsets the reference-date inventory baseline.
