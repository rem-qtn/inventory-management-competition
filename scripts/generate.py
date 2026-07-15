"""Generate the deterministic HexaCare Supply history. Run from repository root."""
from __future__ import annotations
import csv, hashlib, json, math, random, shutil
from collections import defaultdict, deque
from datetime import date, timedelta
from pathlib import Path
import numpy as np

ROOT=Path(__file__).resolve().parents[1]; OUT=ROOT/'data'; SEED=20260701
PUBLIC_START=date(2023,7,1); REF=date(2026,7,1); BURN=date(2022,7,1); END=REF
Q=lambda x: round(float(x),2)
FIELDS={
'items':['item_id','item_name','description','department','category','subcategory','brand_family','product_family','lifecycle_stage','launch_date','active_at_reference','primary_supplier_id','sourcing_country','manufacturing_region','base_uom','sales_uom','purchase_uom','units_per_inner_pack','units_per_case','cases_per_layer','layers_per_pallet','units_per_pallet','moq','order_multiple','minimum_cases','minimum_pallets','unit_weight_kg','unit_volume_m3','storage_zone','handling_class','current_buy_price_eur','current_list_sell_price_eur','vat_category','stockout_penalty_eur','service_class','bulk_item_flag','catch_weight_flag','hazardous_or_fragile_flag','temperature_class','returnable_flag','substitution_group','annual_holding_rate'],
'suppliers':['supplier_id','supplier_name','country','region','currency','transport_mode','incoterm','order_weekday','contract_lead_days','minimum_order_value_eur','reliability_class','payment_terms_days','china_cny_sensitive','agreement_year','annual_rebate_threshold_eur','annual_rebate_rate','rebate_qualifying_definition'],
'customers':['customer_id','customer_name','segment','region','channel','patience_days'],
'orders':['sales_order_id','order_date','customer_id','channel','status'],
'lines':['sales_order_line_id','sales_order_id','item_id','order_date','ordered_quantity','fulfilled_quantity','cancelled_quantity','net_unit_price_eur','net_revenue_eur','line_status'],
'pos':['po_line_id','po_id','order_date','item_id','supplier_id','ordered_quantity','received_quantity','rejected_quantity','unit_buy_price_eur','promised_receipt_date','actual_receipt_date','is_open','qualifying_spend_eur'],
'moves':['movement_id','movement_date','item_id','movement_type','quantity','direction','source_transaction_id'],
'stock':['stock_date','item_id','opening_on_hand','receipts','shipments','customer_returns','positive_adjustments','negative_adjustments','closing_on_hand','opening_backlog','new_backlog','backlog_fulfilled','backlog_cancelled','closing_backlog','available_quantity','stockout_flag','inventory_value_eur'],
'current':['reference_date','item_id','on_hand_quantity','backorder_quantity','inventory_value_eur'],
'latent':['demand_date','item_id','customer_id','latent_quantity','demand_archetype','future_only'],
'future_daily':['demand_date','item_id','latent_demand_quantity']}

CAT=[
('Clinical care','Wound management','Dressings and bandages',['Sterile gauze pad','Foam dressing','Elastic bandage','Wound closure strip'],'France','ambient',1.0,20,1.35),
('Clinical care','Injection and infusion','Syringes and IV consumables',['Safety syringe','IV extension set','Infusion pump line','Needle-free connector'],'Germany','ambient',1.1,25,1.45),
('Infection control','PPE','Protective equipment',['Nitrile examination glove','FFP2 respirator','Isolation gown','Face shield'],'China','ambient',1.5,100,1.3),
('Infection control','Surface hygiene','Cleaning and disinfection',['Surface disinfectant wipe','Hand hygiene dispenser','Disinfectant concentrate','Spill response kit'],'France','ambient',.8,12,1.4),
('Laboratory','Specimen collection','Laboratory consumables',['Blood collection tube','Specimen container','Microscope slide','Centrifuge tube'],'Italy','ambient',.9,50,1.45),
('Patient care','Ward supplies','Daily patient care',['Patient wash basin','Bedpan','Clinical thermometer','Pressure relief cushion'],'Netherlands','ambient',.6,10,1.55),
('Theatre','Surgical supplies','Procedure consumables',['Surgical drape','Scalpel blade','Suture pack','Electrosurgical pencil'],'Germany','ambient',.55,10,1.65),
('Equipment','Monitoring equipment','Clinical devices',['Vital signs monitor','Pulse oximeter','Infusion pump','Mobile examination light'],'China','ambient',.16,1,2.0),
('Facilities','Medical furniture','Ward and mobility equipment',['Hospital trolley','Overbed table','Patient transfer chair','Clinical storage cabinet'],'China','ambient',.22,1,1.75),
('Administration','Medical logistics','Storage and identification',['Medication label roll','Specimen transport bag','Barcode wristband','Sharps container'],'Belgium','ambient',.85,25,1.45),
]
CATEGORY_COUNTS=[165,145,140,125,110,95,80,60,45,35]
CATEGORY_INDEX=[j for j,n in enumerate(CATEGORY_COUNTS) for _ in range(n)]
ADJ=['Classic','ProLine','Select','Signature','Eco','Grand','Nordic','Essential','Prime','Terra']
def wd(d): return d.strftime('%A')
def daterange(a,b):
 d=a
 while d<b: yield d; d+=timedelta(days=1)
def write(path,fields):
 path.parent.mkdir(parents=True,exist_ok=True); f=open(path,'w',newline='',encoding='utf-8'); w=csv.DictWriter(f,fields,quoting=csv.QUOTE_MINIMAL); w.writeheader(); return f,w
def cny_delay(d,country,rng):
 if country!='China': return 0
 for x in [date(2024,2,10),date(2025,1,29),date(2026,2,17),date(2027,2,6)]:
  if x-timedelta(days=28)<=d<=x+timedelta(days=20): return rng.randint(12,35)
 return 0
def stable_mod(mod,*parts): return int(hashlib.sha256('|'.join(map(str,parts)).encode('utf-8')).hexdigest()[:16],16)%mod
def main():
 if OUT.exists(): shutil.rmtree(OUT)
 pub=OUT/'public'; inst=OUT/'instructor'; rng=random.Random(SEED); nr=np.random.default_rng(SEED)
 # suppliers
 sf,sw=write(pub/'supplier_master.csv',FIELDS['suppliers']); suppliers=[]
 countries=['France']*15+['Germany']*8+['Italy']*7+['Spain']*6+['Netherlands']*5+['Turkey']*5+['China']*10+['Belgium']*4
 prefixes={'France':'Maison','Germany':'Rhein','Italy':'Luce','Spain':'Iberia','Netherlands':'Delta','Turkey':'Anatolia','China':'Jade','Belgium':'Arden'}
 for i,country in enumerate(countries,1):
  mode='Ocean' if country=='China' else ('Road' if country!='Turkey' else 'Road')
  lead=(rng.randint(6,16) if country in ['France','Belgium'] else rng.randint(10,25) if country not in ['China','Turkey'] else rng.randint(28,48) if country=='Turkey' else rng.randint(65,92))
  rebate=rng.random()<.28; s={'supplier_id':f'SUP-{i:03d}','supplier_name':f"{prefixes[country]} {rng.choice(['Medical','Clinical','Health','Care','Hospital'])} Supply {i}",'country':country,'region':'Asia' if country=='China' else 'Europe','currency':'EUR','transport_mode':mode,'incoterm':'DAP European DC' if country!='China' else 'FOB Shanghai','order_weekday':rng.choice(['Monday','Tuesday','Wednesday','Thursday','Friday']),'contract_lead_days':lead,'minimum_order_value_eur':rng.choice([300,500,750,1000,1500,2500]),'reliability_class':rng.choice(['A','A','B','B','C']),'payment_terms_days':rng.choice([30,45,60]),'china_cny_sensitive':int(country=='China'),'agreement_year':2026 if rebate else 0,'annual_rebate_threshold_eur':rng.choice([25000,50000,75000,100000]) if rebate else 0,'annual_rebate_rate':rng.choice([.01,.015,.02,.03]) if rebate else 0,'rebate_qualifying_definition':'Accepted non-cancellable PO spend in agreement year' if rebate else 'NOT_APPLICABLE'}; suppliers.append(s); sw.writerow(s)
 sf.close()
 # items
 itf,iw=write(pub/'item_master.csv',FIELDS['items']); items=[]
 for i in range(1000):
  dep,cat,sub,names,origin,temp,rate,case,margin=CAT[CATEGORY_INDEX[i]]; base=names[(i//len(CAT))%len(names)]
  china=origin=='China'; supplier=rng.choice([s for s in suppliers if s['country']==origin] or suppliers)
  equipment=dep=='Equipment'; outdoor=dep=='Facilities'; fresh=False; pack=dep in ['Infection control','Administration']
  units_case=1 if equipment or outdoor else case; layers=1 if units_case==1 else rng.choice([4,5,6,8]); cases_layer=1 if units_case==1 else rng.choice([4,5,6]); pallet=units_case*layers*cases_layer
  buy=Q((rng.uniform(15,180) if equipment else rng.uniform(2,25) if outdoor else rng.uniform(.35,8))* (1+i%7*.03)); sell=Q(buy*margin*rng.uniform(.93,1.12)*1.18)
  launch=date(2022,1,1)+timedelta(days=rng.randrange(0,1450)); lifecycle='Mature'; active=1
  z=i%100
  if z<7: lifecycle='Launch'; launch=date(2025,7,1)+timedelta(days=rng.randrange(0,360))
  elif z<13: lifecycle='Decline'; launch=date(2022,1,1)+timedelta(days=rng.randrange(0,450))
  elif z==13: lifecycle='Phase-out'; active=0
  service='A' if i<18 else ('B' if i<250 else 'C'); archetype=['stable','intermittent','lumpy','erratic','seasonal','trend'][i%6]
  item_name=f'{rng.choice(ADJ)} {base} {100+i//10}'; brand_family=rng.choice(['HexaCare','Clinica Pro','MedSupply','CareLine'])
  unit_weight=Q(rng.uniform(.02,4) if not equipment else rng.uniform(8,55)); unit_volume=Q(rng.uniform(.0001,.03))
  holding_rate=.17 if pack else .19
  if dep=='Facilities': holding_rate=.26
  if equipment: holding_rate=.30
  if unit_weight>=8 or unit_volume>=.015: holding_rate+=.03
  if china: holding_rate+=.01
  holding_rate=Q(min(.36,holding_rate))
  item={'item_id':f'HX-{i+1:04d}','item_name':item_name,'description':f'{sub.lower()} for hospitals, clinics and care networks.','department':dep,'category':cat,'subcategory':sub,'brand_family':brand_family,'product_family':base,'lifecycle_stage':lifecycle,'launch_date':launch.isoformat(),'active_at_reference':active,'primary_supplier_id':supplier['supplier_id'],'sourcing_country':origin,'manufacturing_region':'Asia' if china else 'Europe','base_uom':'EA','sales_uom':'EA','purchase_uom':'CASE' if units_case>1 else 'EA','units_per_inner_pack':1,'units_per_case':units_case,'cases_per_layer':cases_layer,'layers_per_pallet':layers,'units_per_pallet':pallet,'moq':units_case*(rng.choice([1,2,3]) if not equipment else 1),'order_multiple':units_case,'minimum_cases':1,'minimum_pallets':0,'unit_weight_kg':unit_weight,'unit_volume_m3':unit_volume,'storage_zone':'AMBIENT','handling_class':'FRAGILE' if dep=='Equipment' else ('BULK' if pack else 'STANDARD'),'current_buy_price_eur':buy,'current_list_sell_price_eur':sell,'vat_category':'STANDARD','stockout_penalty_eur':Q((sell-buy)*rng.uniform(1.1,3.0)),'service_class':service,'bulk_item_flag':int(pack),'catch_weight_flag':0,'hazardous_or_fragile_flag':int(dep in ['Infection control','Equipment']),'temperature_class':'AMBIENT','returnable_flag':int(dep in ['Equipment','Facilities']),'substitution_group':f'SUB-{i%20:02d}' if dep in ['Infection control','Administration'] else 'NOT_APPLICABLE','annual_holding_rate':holding_rate}
  # Calibrated to a roughly €100M annual hospital-supplies distributor at
  # mature scale; quantities, rather than arbitrary price inflation, carry it.
  item['_rate']=76.0*rate*(rng.uniform(.25,3.5))*(.35 if equipment else 1); item['_arch']=archetype; items.append(item); iw.writerow({k:item[k] for k in FIELDS['items']})
 itf.close()
 # customers
 cf,cw=write(pub/'customer_master.csv',FIELDS['customers']); customers=[]; segs=[('University hospital',2.2,10),('Private clinic',1.4,7),('Care home',1.1,8),('Medical laboratory',1.0,5),('Regional health network',1.8,12)]
 for i in range(240):
  seg,scale,pat=rng.choice(segs); c={'customer_id':f'CUST-{i+1:03d}','customer_name':f'{rng.choice(["Centre Hospitalier","Clinique","Réseau Santé","Laboratoire","Groupe Médical"])} {rng.choice(["Rivoli","Lumière","Atlantique","Mistral","Bastille"])} {i+1}','segment':seg,'region':rng.choice(['Île-de-France','Auvergne-Rhône-Alpes','Provence-Alpes-Côte d’Azur','Nouvelle-Aquitaine','Occitanie']),'channel':'Public tender' if seg in ['University hospital','Regional health network'] else 'Contract','patience_days':pat}; c['_scale']=scale; customers.append(c); cw.writerow({k:c[k] for k in FIELDS['customers']})
 cf.close()
 # output streams
 streams={}; writers={}
 for n in ['orders','lines','pos','moves','stock','current','latent','future_daily']:
  folder=inst if n in ['latent','future_daily'] else pub; streams[n],writers[n]=write(folder/({'orders':'sales_orders','lines':'sales_order_lines','pos':'purchase_orders','moves':'inventory_movements','stock':'daily_stock_history','current':'current_inventory','latent':'latent_demand_history','future_daily':'future_daily_demand'}[n]+'.csv'),FIELDS[n])
 inv=np.array([max(x['moq']*2,int(x['_rate']*30)) for x in items],dtype=int); backlog=np.zeros(1000,dtype=int); openpos=[]; backorders=defaultdict(deque); oid=lid=poid=receiptid=moveid=0
 def move(d,ix,typ,qty,src):
  nonlocal moveid
  if PUBLIC_START<=d<REF: moveid+=1; writers['moves'].writerow({'movement_id':f'MOV-{moveid:08d}','movement_date':d.isoformat(),'item_id':items[ix]['item_id'],'movement_type':typ,'quantity':int(qty),'direction':'IN' if typ in ['SUPPLIER_RECEIPT','CUSTOMER_RETURN','POSITIVE_ADJUSTMENT'] else 'OUT','source_transaction_id':src})
 def lead(s,d):
  base=int(s['contract_lead_days']); tail=int(nr.lognormal(math.log(max(base*.22,1)),.42)); weekshock=stable_mod(8,SEED,s['supplier_id'],d.isocalendar().year,d.isocalendar().week); return base+tail+weekshock+cny_delay(d,s['country'],rng)
 def issue_po(d,ix,qty,tag='INCUMBENT'):
  nonlocal poid
  it=items[ix]; s=next(x for x in suppliers if x['supplier_id']==it['primary_supplier_id']); qty=max(it['moq'],int(math.ceil(qty/it['order_multiple']))*it['order_multiple']); min_qty=int(math.ceil(float(s['minimum_order_value_eur'])/it['current_buy_price_eur']/it['order_multiple']))*it['order_multiple']; qty=max(qty,min_qty); poid+=1; pl=f'POL-{poid:08d}'; actual=d+timedelta(days=lead(s,d)); promised=d+timedelta(days=int(s['contract_lead_days']*1.08)); recqty=max(0,qty-(rng.randint(1,max(1,qty//15)) if rng.random()<.035 else 0)); is_open=int(actual>=REF); r={'po_line_id':pl,'po_id':f'PO-{poid:07d}','order_date':d.isoformat(),'item_id':it['item_id'],'supplier_id':s['supplier_id'],'ordered_quantity':qty,'received_quantity':recqty if not is_open else 0,'rejected_quantity':qty-recqty if not is_open else 0,'unit_buy_price_eur':it['current_buy_price_eur'],'promised_receipt_date':promised.isoformat(),'actual_receipt_date':actual.isoformat() if not is_open else 'NOT_APPLICABLE','is_open':is_open,'qualifying_spend_eur':Q(qty*it['current_buy_price_eur'])}; openpos.append((actual,ix,recqty,qty-recqty,r));
  # Foundation POs immediately before the public window are retained solely
  # when a public receipt needs its source document; normal history ends at REF.
  if PUBLIC_START-timedelta(days=366)<=d<REF: writers['pos'].writerow(r)
 # warm initial orders and operation
 for ix in range(1000):
  if rng.random()<.65: issue_po(BURN+timedelta(days=rng.randint(0,60)),ix,items[ix]['_rate']*35)
 for d in daterange(BURN,END):
  # Opening state is before receipts; receipts are then usable for same-day allocation.
  opening=inv.copy(); openingb=backlog.copy(); daily=defaultdict(lambda:defaultdict(int))
  # receipts before allocation
  for p in list(openpos):
   actual,ix,rq,rejected,r=p
   if actual==d:
    inv[ix]+=rq; openpos.remove(p); receiptid+=1; daily[ix]['receipts']+=rq; move(d,ix,'SUPPLIER_RECEIPT',rq,r['po_line_id']); 
    if rejected: move(d,ix,'RECEIPT_REJECTION',rejected,r['po_line_id'])
  # Backorders inherited from the burn-in are made explicit at the public
  # cutoff, preserving the source transaction for subsequent shipments.
  if d==PUBLIC_START:
   for ix,queue in backorders.items():
    for sl,created,patience,remaining in list(queue):
     oid+=1; so=f'SO-{oid:08d}'; price=Q(items[ix]['current_list_sell_price_eur']*.90)
     writers['orders'].writerow({'sales_order_id':so,'order_date':d.isoformat(),'customer_id':'CUST-001','channel':'Contract','status':'OPEN_BACKORDER_AT_CUTOFF'})
     writers['lines'].writerow({'sales_order_line_id':sl,'sales_order_id':so,'item_id':items[ix]['item_id'],'order_date':d.isoformat(),'ordered_quantity':remaining,'fulfilled_quantity':0,'cancelled_quantity':0,'net_unit_price_eur':price,'net_revenue_eur':0,'line_status':'OPEN_BACKORDER_AT_CUTOFF'})
  # existing backlog allocation and cancellation
  for ix,q in enumerate(backlog):
   if q and inv[ix]:
    z=min(int(q),int(inv[ix])); inv[ix]-=z; backlog[ix]-=z; daily[ix]['backlog_fulfilled']+=z
    to_ship=z
    while to_ship and backorders[ix]:
     sl,created,patience,remaining=backorders[ix][0]; allocated=min(to_ship,remaining)
     move(d,ix,'BACKORDER_SHIPMENT',allocated,sl); to_ship-=allocated
     if allocated==remaining: backorders[ix].popleft()
     else: backorders[ix][0]=(sl,created,patience,remaining-allocated)
    if to_ship: move(d,ix,'BACKORDER_SHIPMENT',to_ship,'UNKNOWN')
   while backorders[ix] and (d-backorders[ix][0][1]).days>backorders[ix][0][2]:
    _,_,_,rem=backorders[ix].popleft(); rem=min(rem,int(backlog[ix])); backlog[ix]-=rem; daily[ix]['backlog_cancelled']+=rem
  # latent customer demand; correlated tourism/event multipliers
  monthmult=1.35 if d.month in [5,6,7,8] else 1.28 if d.month==12 else .82 if d.month==1 else 1
  shared=1+(0.20 if (d.day%19==0) else 0)+(0.15 if d.weekday() in [3,4] else 0)
  order_for_customer={}
  for ix,it in enumerate(items):
   if d<date.fromisoformat(it['launch_date']) or (it['lifecycle_stage']=='Phase-out' and d>date(2025,10,1)): continue
   ar=it['_arch']; rate=it['_rate']*shared*(.55 if d.weekday()==6 else 1)*monthmult
   if it['department']=='Facilities': rate*=1.35 if d.month in [5,6,7,8,9] else .75
   if ar=='intermittent': occur=rng.random()<min(.18,rate*.12); qty=(rng.randint(1,6)*it['units_per_case']) if occur else 0
   elif ar=='lumpy': qty=(rng.randint(8,60)*it['units_per_case'] if rng.random()<min(.035,rate*.025) else 0)
   else: qty=int(nr.negative_binomial(2,max(.04,min(.95,2/(2+rate)))))
   if ar=='trend': qty=int(qty*(1+max(0,(d-PUBLIC_START).days)/1200))
   if ar=='erratic' and rng.random()<.08: qty*=rng.randint(2,6)
   if qty<=0: continue
   cust=rng.choice(customers); writers['latent'].writerow({'demand_date':d.isoformat(),'item_id':it['item_id'],'customer_id':cust['customer_id'],'latent_quantity':qty,'demand_archetype':ar,'future_only':int(d>=REF)})
   available=min(qty,int(inv[ix])); inv[ix]-=available; daily[ix]['shipments']+=available
   if available: move(d,ix,'CUSTOMER_SHIPMENT',available,f'SOL-{lid+1:09d}')
   shortage=qty-available
   lostprob=.18 if it['department'] in ['Infection control','Administration'] else .08 if it['department'] in ['Equipment','Facilities'] else .28
   bo=int(shortage*(1-lostprob)) if shortage else 0; lost=shortage-bo
   if shortage: daily[ix]['stockout']=1
   if bo: backlog[ix]+=bo; daily[ix]['new_backlog']+=bo
   # public only when something fulfilled or backorder eligible
   if available or bo:
    lid+=1; sl=f'SOL-{lid:09d}'; price=Q(it['current_list_sell_price_eur']*(.82+rng.random()*.14)); status='FULFILLED' if bo==0 else 'OPEN_BACKORDER';
    if cust['customer_id'] not in order_for_customer:
     oid+=1; order_for_customer[cust['customer_id']]=f'SO-{oid:08d}'
     if PUBLIC_START<=d<REF: writers['orders'].writerow({'sales_order_id':order_for_customer[cust['customer_id']],'order_date':d.isoformat(),'customer_id':cust['customer_id'],'channel':cust['channel'],'status':'OPEN_OR_FULFILLED'})
    so=order_for_customer[cust['customer_id']]
    if PUBLIC_START<=d<REF: writers['lines'].writerow({'sales_order_line_id':sl,'sales_order_id':so,'item_id':it['item_id'],'order_date':d.isoformat(),'ordered_quantity':available+bo,'fulfilled_quantity':available,'cancelled_quantity':0,'net_unit_price_eur':price,'net_revenue_eur':Q(available*price),'line_status':status})
    if bo: backorders[ix].append((sl,d,cust['patience_days'],bo))
  # rare returns and adjustments
  for ix,it in enumerate(items):
   if daily[ix]['shipments'] and it['returnable_flag'] and rng.random()<.0015:
    q=1; inv[ix]+=q; daily[ix]['returns']+=q; move(d,ix,'CUSTOMER_RETURN',q,f'RET-{d:%Y%m%d}-{ix:04d}')
   if rng.random()<.00008:
    q=1; positive=rng.random()<.5; q=q if positive else min(q,inv[ix]); inv[ix]+=q if positive else -q; daily[ix]['pos' if positive else 'neg']+=q; 
    if q: move(d,ix,'POSITIVE_ADJUSTMENT' if positive else 'NEGATIVE_ADJUSTMENT',q,f'ADJ-{d:%Y%m%d}-{ix:04d}')
  # weekly incumbent ordering; sales + backlog signal only, deliberately imperfect
  if d.weekday()==0:
   for ix,it in enumerate(items):
    s=next(x for x in suppliers if x['supplier_id']==it['primary_supplier_id']); pipeline=sum(p[2] for p in openpos if p[1]==ix); target=it['_rate']*(s['contract_lead_days']+7)*(.85 if it['_arch']!='erratic' else .65); gap=target-(inv[ix]+pipeline-backlog[ix])
    if gap>it['moq']*.6 and rng.random()<.72: issue_po(d,ix,gap*(.78+rng.random()*.30))
  if d>=PUBLIC_START and d<REF:
   for ix,it in enumerate(items):
    a=daily[ix]; writers['stock'].writerow({'stock_date':d.isoformat(),'item_id':it['item_id'],'opening_on_hand':int(opening[ix]),'receipts':a['receipts'],'shipments':a['shipments']+a['backlog_fulfilled'],'customer_returns':a['returns'],'positive_adjustments':a['pos'],'negative_adjustments':a['neg'],'closing_on_hand':int(inv[ix]),'opening_backlog':int(openingb[ix]),'new_backlog':a['new_backlog'],'backlog_fulfilled':a['backlog_fulfilled'],'backlog_cancelled':a['backlog_cancelled'],'closing_backlog':int(backlog[ix]),'available_quantity':int(inv[ix]),'stockout_flag':a['stockout'],'inventory_value_eur':Q(inv[ix]*it['current_buy_price_eur'])})
 # Draw only the exogenous future item-day demand path. Future operations are
 # deliberately absent: daily receipts and allocation occur in the simulator.
 for d in daterange(REF,date(2027,7,1)):
  monthmult=1.35 if d.month in [5,6,7,8] else 1.28 if d.month==12 else .82 if d.month==1 else 1
  shared=1+(0.20 if (d.day%19==0) else 0)+(0.15 if d.weekday() in [3,4] else 0)
  for ix,it in enumerate(items):
   rate=it['_rate']*shared*(.55 if d.weekday()==6 else 1)*monthmult
   if it['department']=='Facilities': rate*=1.35 if d.month in [5,6,7,8,9] else .75
   ar=it['_arch']
   if ar=='intermittent': qty=(rng.randint(1,6)*it['units_per_case']) if rng.random()<min(.18,rate*.12) else 0
   elif ar=='lumpy': qty=(rng.randint(8,60)*it['units_per_case']) if rng.random()<min(.035,rate*.025) else 0
   else: qty=int(nr.negative_binomial(2,max(.04,min(.95,2/(2+rate)))))
   if ar=='trend': qty=int(qty*(1+max(0,(d-PUBLIC_START).days)/1200))
   if ar=='erratic' and rng.random()<.08: qty*=rng.randint(2,6)
   writers['future_daily'].writerow({'demand_date':d.isoformat(),'item_id':it['item_id'],'latent_demand_quantity':qty})
 # Reference state and public transaction values are reconstructed from the
 # causal ledger at the cutoff (not from independently sampled snapshots).
 for ix,it in enumerate(items): writers['current'].writerow({'reference_date':REF.isoformat(),'item_id':it['item_id'],'on_hand_quantity':0,'backorder_quantity':0,'inventory_value_eur':0})
 for f in streams.values(): f.close()
 # repair current/open PO deterministically from last public stock/PO rows
 import pandas as pd
 st=pd.read_csv(pub/'daily_stock_history.csv'); last=st[st.stock_date=='2026-06-30'][['item_id','closing_on_hand','closing_backlog','inventory_value_eur']]
 pd.DataFrame({'reference_date':REF.isoformat(),'item_id':last.item_id,'on_hand_quantity':last.closing_on_hand,'backorder_quantity':last.closing_backlog,'inventory_value_eur':last.inventory_value_eur}).to_csv(pub/'current_inventory.csv',index=False)
 po=pd.read_csv(pub/'purchase_orders.csv')
 lines=pd.read_csv(pub/'sales_order_lines.csv'); mm=pd.read_csv(pub/'inventory_movements.csv'); shipped=mm[mm.movement_type.isin(['CUSTOMER_SHIPMENT','BACKORDER_SHIPMENT'])].groupby('source_transaction_id').quantity.sum()
 lines['fulfilled_quantity']=lines.sales_order_line_id.map(shipped).fillna(0).astype(int); lines['net_revenue_eur']=(lines.fulfilled_quantity*lines.net_unit_price_eur).round(2); lines['line_status']=np.where(lines.fulfilled_quantity>=lines.ordered_quantity,'FULFILLED','OPEN_OR_CANCELLED'); lines.to_csv(pub/'sales_order_lines.csv',index=False)
 manifest={}
 for p in sorted(OUT.rglob('*.csv')): manifest[str(p.relative_to(OUT)).replace('\\','/')]=hashlib.sha256(p.read_bytes()).hexdigest()
 (OUT/'manifest.json').write_text(json.dumps(manifest,indent=2,sort_keys=True)+'\n',encoding='utf-8')
 print(f'Generated {len(items)} items; {len(st):,} public item-days; manifest {len(manifest)} files')
if __name__=='__main__': main()
