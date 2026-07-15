# HexaCare Supply inventory competition

Reproducible synthetic data and an instructor-side monthly simulator for the
CentraleSupélec inventory-management competition. It models a Europe-based B2B
distributor of non-perishable hospital supplies at one central DC and produces exactly 1,000 items.

## Quick start

```powershell
python scripts/generate.py
python scripts/validate.py
python scripts/simulate_round.py --team demo --round 1 --po submissions/sample_purchase_orders.csv --forecast submissions/sample_forecasts.csv
```

The generated files are under `data/public/` (safe to give students) and
`data/instructor/` (never distribute).  Generation uses seed `20260701` and
writes a SHA-256 manifest; removing `data/` and regenerating yields identical
CSV bytes.

## Modelling rules

Dates are ISO dates, quantities are base units, and all amounts are EUR
excluding VAT. Receipts are processed before demand allocation on a day.
`daily_stock_history` is derived directly from the movement and backlog event
stream. Lost demand is private; backorder-eligible shortages appear in public
order lines and are either later shipped or cancelled.

Historical POs are made by a deliberately imperfect weekly order-up-to policy
using trailing observed shipments, seasonality, stock, backlog and open POs.
Actual lead times use discrete log-normal/right-tail mixtures plus supplier,
route-week and Chinese-New-Year shocks. They are not Gaussian.

Forecasts must provide q05, q10, q25, q50, q75, q90 and q95. The simulator
uses weighted pinball loss against private uncensored monthly demand. Accepted
POs must match the primary supplier and meet MOQ/order-multiple constraints;
invalid lines are rejected without rounding. Supplier minimum order values are
checked across each submitted supplier order. Contribution includes sales,
receipt purchase cost, carrying cost, lost/backorder penalties, annual rebates,
and full-cost continuation value for ending inventory. Full-year rebate
agreement terms are held on the supplier master.

## Public tables

`item_master`, `supplier_master`, `customer_master`, `sales_orders`,
`sales_order_lines`, `purchase_orders`, `inventory_movements`,
`daily_stock_history`, and `current_inventory` are CSV files. The merged
`purchase_orders` table includes both received and open POs through `is_open`.
`DATA_DICTIONARY.md` documents fields.
The private folder contains historical latent demand and the fixed,
unconstrained daily item-demand path only. Future operations are created after
each team's PO submission, not generated in advance; POs are accepted only at
the start of each monthly round.
