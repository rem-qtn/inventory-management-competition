"""Create an inline FY2025 catalog revenue Pareto visualization."""
from __future__ import annotations
import json
from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
OUT = Path.home() / '.codex' / 'visualizations' / '2026' / '07' / '11' / '019f5199-c3e5-7a82-bebc-312b5a321a1f' / 'revenue-pareto.html'

def main() -> None:
    items = pd.read_csv(ROOT / 'data/public/item_master.csv', usecols=['item_id', 'item_name', 'department'])
    lines = pd.read_csv(ROOT / 'data/public/sales_order_lines.csv', usecols=['item_id', 'order_date', 'net_revenue_eur'])
    fy = lines[lines.order_date.str.startswith('2025')].groupby('item_id', as_index=False).net_revenue_eur.sum()
    df = items.merge(fy, on='item_id', how='left').fillna({'net_revenue_eur': 0}).sort_values('net_revenue_eur', ascending=False).reset_index(drop=True)
    total = float(df.net_revenue_eur.sum())
    df['cumulative_share'] = df.net_revenue_eur.cumsum() / total * 100
    df['rank'] = df.index + 1
    top20 = float(df.iloc[:200].net_revenue_eur.sum() / total * 100)
    rank80 = int((df.cumulative_share >= 80).idxmax() + 1)
    data = [{'rank': int(r['rank']), 'id': r.item_id, 'name': r.item_name, 'department': r.department, 'revenue': round(float(r.net_revenue_eur), 2), 'cum': round(float(r['cumulative_share']), 4)} for _, r in df.iterrows()]
    payload = json.dumps(data, ensure_ascii=False, separators=(',', ':'))
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(f'''<div id="revenue-pareto">
<style>
#revenue-pareto .pareto-wrap{{position:relative}} #revenue-pareto svg{{width:100%;height:auto;overflow:visible}} #revenue-pareto .axis,#revenue-pareto .guide{{stroke:var(--border);stroke-width:1}} #revenue-pareto .guide{{stroke-dasharray:4 4}} #revenue-pareto .curve{{fill:none;stroke:var(--viz-series-1);stroke-width:2.5}} #revenue-pareto .marker{{fill:var(--viz-series-2)}} #revenue-pareto .label{{fill:var(--muted-foreground);font-size:11px}} #revenue-pareto .tooltip{{position:absolute;display:none;pointer-events:none}} #revenue-pareto .pareto-caption{{margin-top:8px;color:var(--muted-foreground)}}
</style>
<div class="pareto-wrap"><svg id="pareto-chart" viewBox="0 0 720 350" role="img" aria-label="FY2025 cumulative revenue Pareto curve for all catalog items"><title>FY2025 revenue Pareto</title><desc>Cumulative share of revenue ordered by item revenue, with 20 percent and 80 percent reference lines.</desc></svg><div id="pareto-tip" class="tooltip"></div></div>
<div class="pareto-caption text-small" id="pareto-caption"></div>
</div><script>
(()=>{{const root=document.getElementById('revenue-pareto'),data={payload},svg=root.querySelector('#pareto-chart'),tip=root.querySelector('#pareto-tip'),caption=root.querySelector('#pareto-caption');const W=720,H=350,L=52,R=24,T=26,B=42;const x=r=>L+(r-1)/(data.length-1)*(W-L-R),y=v=>H-B-v/100*(H-T-B);const line=data.map((d,i)=>`${{i?'L':'M'}}${{x(d.rank).toFixed(2)}},${{y(d.cum).toFixed(2)}}`).join(' ');const rank80={rank80},top20={top20:.1f},total={total:.2f};const p80=data[rank80-1];svg.innerHTML=`<line class="axis" x1="${{L}}" y1="${{H-B}}" x2="${{W-R}}" y2="${{H-B}}"/><line class="axis" x1="${{L}}" y1="${{T}}" x2="${{L}}" y2="${{H-B}}"/><line class="guide" x1="${{x(200)}}" y1="${{T}}" x2="${{x(200)}}" y2="${{H-B}}"/><line class="guide" x1="${{L}}" y1="${{y(80)}}" x2="${{W-R}}" y2="${{y(80)}}"/><path class="curve" d="${{line}}"/><circle class="marker" cx="${{x(200)}}" cy="${{y(data[199].cum)}}" r="4"/><circle class="marker" cx="${{x(rank80)}}" cy="${{y(80)}}" r="4"/><text class="label" x="${{L}}" y="${{T-7}}">Cumulative revenue share</text><text class="label" x="${{L-8}}" y="${{y(100)+4}}" text-anchor="end">100%</text><text class="label" x="${{L-8}}" y="${{y(80)+4}}" text-anchor="end">80%</text><text class="label" x="${{L-8}}" y="${{y(0)+4}}" text-anchor="end">0%</text><text class="label" x="${{L}}" y="${{H-14}}">1</text><text class="label" x="${{x(200)}}" y="${{H-14}}" text-anchor="middle">top 20%</text><text class="label" x="${{W-R}}" y="${{H-14}}" text-anchor="end">1,000 items</text><text class="label" x="${{x(200)+7}}" y="${{y(data[199].cum)-8}}">${{top20.toFixed(1)}}% of revenue</text><text class="label" x="${{x(rank80)+7}}" y="${{y(80)-8}}">80% at rank ${{rank80}}</text>`;caption.textContent=`FY2025 catalog revenue: €${{(total/1e6).toFixed(1)}}M. Hover the curve to inspect an item.`;svg.addEventListener('mousemove',e=>{{const b=svg.getBoundingClientRect(),px=(e.clientX-b.left)/b.width*W;let rank=Math.round(1+(px-L)/(W-L-R)*(data.length-1));rank=Math.max(1,Math.min(data.length,rank));const d=data[rank-1];tip.style.display='block';tip.style.left=`${{Math.max(0,Math.min(b.width-180,e.clientX-b.left+12))}}px`;tip.style.top=`${{Math.max(0,e.clientY-b.top-44)}}px`;tip.textContent=`#${{d.rank}} · ${{d.id}} · €${{d.revenue.toLocaleString('en-GB',{{maximumFractionDigits:0}})}} · ${{d.cum.toFixed(1)}}% cumulative`}});svg.addEventListener('mouseleave',()=>tip.style.display='none')}})();</script>''', encoding='utf-8')
    print(OUT)

if __name__ == '__main__':
    main()
