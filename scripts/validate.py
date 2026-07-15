"""Fast integrity checks for generated public data."""
from pathlib import Path
import hashlib, json
import pandas as pd
R=Path(__file__).resolve().parents[1]; P=R/'data/public'; errors=[]
items=pd.read_csv(P/'item_master.csv'); stock=pd.read_csv(P/'daily_stock_history.csv'); moves=pd.read_csv(P/'inventory_movements.csv'); pos=pd.read_csv(P/'purchase_orders.csv'); future=pd.read_csv(R/'data/instructor/future_daily_demand.csv'); orders=pd.read_csv(P/'sales_orders.csv'); lines=pd.read_csv(P/'sales_order_lines.csv'); current=pd.read_csv(P/'current_inventory.csv')
def check(ok,msg):
 if not ok: errors.append(msg)
check(len(items)==1000,'item count is not 1,000')
check(not items.isna().any().any(),'item master has missing values')
check(items.department.value_counts().nunique()>2,'category hierarchy is artificially uniform')
check(not items.description.str.contains('stable|intermittent|lumpy|erratic|seasonal|trend',case=False,regex=True).any(),'hidden demand archetype leaked in public descriptions')
check(((items.units_per_case*items.cases_per_layer*items.layers_per_pallet)==items.units_per_pallet).all(),'packaging equation failed')
check((items.moq%items.order_multiple==0).all(),'MOQ/order multiple infeasible')
check(len(stock)==1000*1096,'stock history grain incorrect')
check(len(future)==1000*365,'future demand is not item-day grain for 12 months')
check(pd.to_datetime(future.demand_date).min().date().isoformat()=='2026-07-01' and pd.to_datetime(future.demand_date).max().date().isoformat()=='2027-06-30','future demand dates incorrect')
check(not any(pd.to_datetime(df[c]).max().date().isoformat()>='2026-07-01' for df,c in [(stock,'stock_date'),(moves,'movement_date')]),'public operational data leaks future outcomes')
eq=stock.opening_on_hand+stock.receipts+stock.customer_returns+stock.positive_adjustments-stock.shipments-stock.negative_adjustments
check((eq==stock.closing_on_hand).all(),'stock equation failed')
check((stock.closing_on_hand>=0).all(),'negative on hand')
beq=stock.opening_backlog+stock.new_backlog-stock.backlog_fulfilled-stock.backlog_cancelled
check((beq==stock.closing_backlog).all(),'backlog equation failed')
ordered=stock.sort_values(['item_id','stock_date']); prior=ordered.groupby('item_id').closing_on_hand.shift(); prior_bo=ordered.groupby('item_id').closing_backlog.shift()
check((ordered.opening_on_hand[prior.notna()].to_numpy()==prior[prior.notna()].to_numpy()).all(),'stock continuity failed')
check((ordered.opening_backlog[prior_bo.notna()].to_numpy()==prior_bo[prior_bo.notna()].to_numpy()).all(),'backlog continuity failed')
check((pos.is_open.isin([0,1])).all(),'PO is_open flag invalid')
check((pos[pos.is_open==0].received_quantity+pos[pos.is_open==0].rejected_quantity<=pos[pos.is_open==0].ordered_quantity).all(),'closed PO receipt quantity invalid')
check((pos[pos.is_open==1].received_quantity==0).all(),'open PO has recorded receipts')
sup=pd.read_csv(P/'supplier_master.csv')[['supplier_id','minimum_order_value_eur']]
check(((pos.ordered_quantity*pos.unit_buy_price_eur)>=pos.merge(sup,on='supplier_id').minimum_order_value_eur).all(),'historical PO below supplier minimum order value')
check(set(moves[moves.movement_type=='SUPPLIER_RECEIPT'].source_transaction_id).issubset(set(pos.po_line_id)),'receipt movement trace failed')
ship=moves[moves.movement_type.isin(['CUSTOMER_SHIPMENT','BACKORDER_SHIPMENT'])].groupby('source_transaction_id').quantity.sum()
line_ship=lines.sales_order_line_id.map(ship).fillna(0)
check((line_ship==lines.fulfilled_quantity).all(),'sales line and shipment quantities disagree')
check((line_ship<=lines.ordered_quantity).all(),'sales line overfulfilled')
check(moves[moves.movement_type.isin(['CUSTOMER_SHIPMENT','BACKORDER_SHIPMENT'])].source_transaction_id.isin(lines.sales_order_line_id).all(),'shipment references missing sales line')
check((lines.net_revenue_eur.round(2)==(lines.fulfilled_quantity*lines.net_unit_price_eur).round(2)).all(),'sales revenue does not reconcile')
check(lines.sales_order_id.isin(orders.sales_order_id).all(),'sales line references missing order header')
last=stock[stock.stock_date=='2026-06-30'][['item_id','closing_on_hand','closing_backlog']].merge(current,on='item_id')
check(((last.closing_on_hand==last.on_hand_quantity)&(last.closing_backlog==last.backorder_quantity)).all(),'current state does not equal last closing state')
print('VALIDATION FAILED: '+ '; '.join(errors) if errors else f'VALIDATION PASSED: {len(items)} items, {len(stock):,} item-days, {len(moves):,} movements')
raise SystemExit(bool(errors))
