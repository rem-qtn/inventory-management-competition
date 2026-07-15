"""Instructor-only 12-round simulator with deterministic shared demand truth."""
from __future__ import annotations
import argparse, calendar, hashlib
from datetime import date, timedelta
from pathlib import Path
import numpy as np
import pandas as pd

R=Path(__file__).resolve().parents[1]; P=R/'data/public'; I=R/'data/instructor'
QUANTILES=[('q05',.05),('q10',.10),('q25',.25),('q50',.50),('q75',.75),('q90',.90),('q95',.95)]
def month_end(d): return date(d.year,d.month,calendar.monthrange(d.year,d.month)[1])
def pinball(y,q,a): return max(a*(y-q),(a-1)*(y-q))
ap=argparse.ArgumentParser(description='Run one monthly team simulation.')
ap.add_argument('--team',required=True); ap.add_argument('--round',type=int,choices=range(1,13),required=True); ap.add_argument('--po',required=True); ap.add_argument('--forecast',required=True); a=ap.parse_args()
decision=date(2026,6+a.round if a.round<=6 else a.round-6,1) if a.round>6 else date(2026,6+a.round,1)
# The expression above is deliberately explicit for the July 2026–June 2027 schedule.
decision=date(2026+(a.round-1)//6, ((6+a.round-1)%12)+1, 1)
end=month_end(decision); team=R/'results'/a.team; team.mkdir(parents=True,exist_ok=True)
items=pd.read_csv(P/'item_master.csv').set_index('item_id'); suppliers=pd.read_csv(P/'supplier_master.csv').set_index('supplier_id')
initial_inventory_value=float(pd.read_csv(P/'current_inventory.csv').inventory_value_eur.sum())
po=pd.read_csv(a.po); fc=pd.read_csv(a.forecast)
expected=['round','order_date','item_id','supplier_id','quantity']
if list(po.columns)!=expected: raise SystemExit('Invalid PO schema: '+', '.join(expected))
if set(fc.columns)!=set(['round','item_id','horizon_month',*[x[0] for x in QUANTILES]]): raise SystemExit('Invalid forecast schema.')
if not (po['round']==a.round).all() or not (fc['round']==a.round).all(): raise SystemExit('Submission round does not match --round.')
# State carries on-hand, backlog and already accepted open POs forward team-by-team.
if a.round==1:
 state=pd.read_csv(P/'current_inventory.csv').set_index('item_id')[['on_hand_quantity','backorder_quantity']]
 prior_open=pd.read_csv(P/'purchase_orders.csv').query('is_open==1')[['item_id','supplier_id','ordered_quantity','promised_receipt_date']].rename(columns={'ordered_quantity':'quantity','promised_receipt_date':'arrival_date'})
else:
 state=pd.read_csv(team/f'state_round_{a.round-1}.csv').set_index('item_id')[['on_hand_quantity','backorder_quantity']]
 prior_open=pd.read_csv(team/f'open_pos_round_{a.round-1}.csv')
state=state.reindex(items.index).fillna(0).astype(int)
valid=[]
for _,x in po.iterrows():
 reason='ACCEPTED'
 if x.item_id not in items.index: reason='unknown item'
 else:
  it=items.loc[x.item_id]
  if x.supplier_id!=it.primary_supplier_id: reason='supplier is not approved primary supplier'
  elif x.order_date!=decision.isoformat(): reason='order date is not this round decision date'
  elif x.quantity<=0: reason='quantity must be positive'
  elif x.quantity<it.moq: reason='below MOQ'
  elif x.quantity%it.order_multiple: reason='not an order multiple'
 valid.append({**x.to_dict(),'validation':reason})
valid=pd.DataFrame(valid)
# Supplier-MOV rule is applied after line validity, so each rejection has a clear reason.
for sid,g in valid[valid.validation=='ACCEPTED'].groupby('supplier_id'):
 spend=sum(float(r.quantity)*items.loc[r.item_id,'current_buy_price_eur'] for _,r in g.iterrows())
 if spend<suppliers.loc[sid,'minimum_order_value_eur']:
  valid.loc[g.index,'validation']='supplier minimum order value not met'
accepted=valid[valid.validation=='ACCEPTED'].copy()
new_open=[]
for _,x in accepted.iterrows():
 s=suppliers.loc[x.supplier_id]; extra=int(hashlib.sha256(f'{a.round}|{x.supplier_id}|{x.item_id}'.encode()).hexdigest()[:16],16)%8
 arrival=decision+timedelta(days=int(s.contract_lead_days)+extra)
 # The deterministic CNY window is shared for all teams, but remains instructor-only.
 if s.country=='China' and date(2027,1,9)<=arrival<=date(2027,2,26): arrival+=timedelta(days=21)
 new_open.append({'item_id':x.item_id,'supplier_id':x.supplier_id,'quantity':int(x.quantity),'arrival_date':arrival.isoformat()})
openpos=pd.concat([prior_open,pd.DataFrame(new_open)],ignore_index=True) if new_open else prior_open.copy()
due=openpos[pd.to_datetime(openpos.arrival_date).dt.date<=end]; future=openpos[pd.to_datetime(openpos.arrival_date).dt.date>end]
receipt_purchase_cost=float(sum(float(x.quantity)*float(items.loc[x.item_id,'current_buy_price_eur']) for _,x in due.iterrows()))
latent=pd.read_csv(I/'future_daily_demand.csv'); latent['d']=pd.to_datetime(latent.demand_date).dt.date
month=latent[(latent.d>=decision)&(latent.d<=end)].pivot(index='d',columns='item_id',values='latent_demand_quantity').reindex(columns=items.index,fill_value=0).fillna(0).astype(int); month.index=month.index.map(lambda x:x.date() if hasattr(x,'date') else x)
received=due.assign(d=pd.to_datetime(due.arrival_date).dt.date).groupby(['d','item_id']).quantity.sum()
fulfilled=pd.Series(0,index=items.index,dtype=float); newback=fulfilled.copy(); lost=fulfilled.copy(); holding=0.0
# Operations remain daily; only order placement is monthly. Receipts are made
# available before that day's demand and outstanding backorders have priority.
for d in pd.date_range(decision,end).date:
 for iid in items.index:
  on=int(state.loc[iid,'on_hand_quantity'])+int(received.get((d,iid),0)); old=int(state.loc[iid,'backorder_quantity'])
  bf=min(on,old); on-=bf; old-=bf; demand=int(month.loc[d,iid]) if d in month.index else 0
  sale=min(on,demand); on-=sale; shortage=demand-sale; it=items.loc[iid]
  lost_share=.18 if it.department in ['Infection control','Administration'] else .08 if it.department in ['Equipment','Facilities'] else .28
  bo=round(shortage*(1-lost_share)); state.loc[iid,'on_hand_quantity']=on; state.loc[iid,'backorder_quantity']=old+bo
  fulfilled.loc[iid]+=sale+bf; newback.loc[iid]+=bo; lost.loc[iid]+=shortage-bo; holding+=on*it.current_buy_price_eur*it.annual_holding_rate/365
# Proper weighted quantile score, evaluated only for submitted horizons that have truth.
fscore=0.0; nscore=0
for _,x in fc.iterrows():
 target=(decision.replace(day=1)+pd.DateOffset(months=int(x.horizon_month)-1)).date()
 y=latent[(latent.demand_date.str[:7]==target.strftime('%Y-%m'))&(latent.item_id==x.item_id)].latent_demand_quantity.sum()
 w=float(items.loc[x.item_id,'current_list_sell_price_eur']) if x.item_id in items.index else 1.0
 for col,q in QUANTILES: fscore+=w*pinball(float(y),float(x[col]),q); nscore+=1
revenue=float(np.dot(fulfilled,items.current_list_sell_price_eur)); cogs=float(np.dot(fulfilled,items.current_buy_price_eur)); penalty=float(np.dot(lost,items.stockout_penalty_eur)+np.dot(newback,items.stockout_penalty_eur)*.15); hold=float(holding)
# 2026 retroactive rebate is recognized once per cumulative tier: current historical YTD plus accepted team spend.
hist=pd.read_csv(P/'purchase_orders.csv'); hist_spend=hist[(hist.order_date>='2026-01-01')&(hist.order_date<='2026-06-30')].groupby('supplier_id').qualifying_spend_eur.sum()
prior_frames=[pd.read_csv(team/f'round_{r}_po_validation.csv').query("validation=='ACCEPTED'") for r in range(1,a.round) if (team/f'round_{r}_po_validation.csv').exists()]
prior_all=pd.concat(prior_frames,ignore_index=True) if prior_frames else pd.DataFrame(columns=accepted.columns)
allteam=pd.concat([prior_all,accepted],ignore_index=True)
def spend_by_supplier(frame): return frame.assign(spend=lambda x:x.quantity*[items.loc[i,'current_buy_price_eur'] for i in x.item_id]).groupby('supplier_id').spend.sum() if len(frame) else pd.Series(dtype=float)
prior_team_spend=spend_by_supplier(prior_all); team_spend=spend_by_supplier(allteam)
rebate=0.0
if decision.year==2026:
 for sid,s in suppliers.iterrows():
  if int(s.agreement_year)!=2026 or float(s.annual_rebate_threshold_eur)<=0: continue
  before=float(hist_spend.get(sid,0)+prior_team_spend.get(sid,0)); after=float(hist_spend.get(sid,0)+team_spend.get(sid,0)); threshold=float(s.annual_rebate_threshold_eur); rate=float(s.annual_rebate_rate)
  rebate+=(after*rate if after>=threshold else 0)-(before*rate if before>=threshold else 0)
terminal=0.0
if a.round==12:
 terminal=float(np.dot(state.on_hand_quantity,items.current_buy_price_eur)-initial_inventory_value)
result={'team':a.team,'round':a.round,'decision_date':decision.isoformat(),'accepted_lines':len(accepted),'rejected_lines':len(valid)-len(accepted),'fulfilled_revenue_eur':round(revenue,2),'cogs_eur':round(cogs,2),'purchase_receipts_cost_eur':round(receipt_purchase_cost,2),'holding_cost_eur':round(hold,2),'stockout_and_backorder_penalty_eur':round(penalty,2),'rebate_eur':round(rebate,2),'continuing_inventory_adjustment_eur':round(terminal,2),'operational_contribution_eur':round(revenue-receipt_purchase_cost-hold-penalty+rebate+terminal,2),'weighted_pinball_loss':round(fscore,4),'forecast_observations':nscore}
valid.to_csv(team/f'round_{a.round}_po_validation.csv',index=False); pd.DataFrame([result]).to_csv(team/f'round_{a.round}_kpis.csv',index=False)
state.reset_index().to_csv(team/f'state_round_{a.round}.csv',index=False); future.to_csv(team/f'open_pos_round_{a.round}.csv',index=False)
print('Wrote '+str(team/f'round_{a.round}_kpis.csv'))
