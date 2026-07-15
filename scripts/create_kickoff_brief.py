"""Create the two-page client kick-off brief without external dependencies."""
from __future__ import annotations
from pathlib import Path
import textwrap

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'docs' / 'hexacare-kickoff-brief.pdf'
W, H, LEFT, TOP, BOTTOM = 595, 842, 54, 790, 54

def esc(s: str) -> str:
    return s.replace('\\', '\\\\').replace('(', '\\(').replace(')', '\\)')

def add_text(cmds: list[str], x: float, y: float, text: str, size: float = 10, bold: bool = False) -> None:
    font = 'F2' if bold else 'F1'
    cmds.append(f'BT /{font} {size} Tf {x:.1f} {y:.1f} Td ({esc(text)}) Tj ET')

def paragraph(cmds: list[str], y: float, text: str, *, size: float = 10, indent: float = 0) -> float:
    for line in textwrap.wrap(text, width=92):
        add_text(cmds, LEFT + indent, y, line, size)
        y -= 14
    return y - 5

def bullet(cmds: list[str], y: float, lead: str, text: str) -> float:
    add_text(cmds, LEFT, y, u'•', 10)
    add_text(cmds, LEFT + 14, y, lead, 10, True)
    wrapped = textwrap.wrap(text, width=75)
    if wrapped:
        add_text(cmds, LEFT + 14 + len(lead) * 5.2, y, wrapped[0], 10)
    for line in wrapped[1:]:
        y -= 14
        add_text(cmds, LEFT + 14, y, line, 10)
    return y - 19

def page_header(cmds: list[str], title: str, page: int) -> float:
    add_text(cmds, LEFT, TOP, 'HEXACARE SUPPLY', 9, True)
    add_text(cmds, 432, TOP, 'CLIENT KICK-OFF BRIEF', 9)
    cmds.append(f'{LEFT} {TOP-10} m {W-LEFT} {TOP-10} l S')
    add_text(cmds, LEFT, TOP - 42, title, 19, True)
    add_text(cmds, LEFT, TOP - 61, 'Confidential project background | Reference date: 1 July 2026', 9)
    add_text(cmds, LEFT, 30, f'HexaCare Supply | Page {page} of 2', 8)
    return TOP - 92

def make_page_one() -> list[str]:
    c: list[str] = []
    y = page_header(c, 'Business context', 1)
    add_text(c, LEFT, y, 'Who HexaCare Supply is', 12, True); y -= 21
    y = paragraph(c, y, 'HexaCare Supply is a Europe-based B2B distributor of non-perishable hospital supplies. It serves university hospitals, private clinics, care homes, medical laboratories and regional health networks from one central European distribution centre. The company sits between manufacturers and clinical users: it buys, stores, packages and delivers products that healthcare providers need to keep wards, laboratories and theatres operating.')
    y = paragraph(c, y, 'The business has matured to roughly EUR 100 million in annual net sales. Its value proposition is breadth of range, dependable availability, rapid delivery and administrative simplicity for procurement teams. Customers expect a reliable service partner, not merely a catalogue of products.')
    add_text(c, LEFT, y, 'Commercial and operating model', 12, True); y -= 21
    y = bullet(c, y, 'Portfolio: ', '1,000 active or historically relevant SKUs across clinical care, infection control, laboratory consumables, patient care, theatre supplies, medical equipment, facilities and medical logistics.')
    y = bullet(c, y, 'Customers: ', 'B2B accounts buy through contract and public-tender channels. Demand is fragmented across many locations, while a small number of high-value and clinically important products drive a disproportionate share of commercial risk.')
    y = bullet(c, y, 'Supply base: ', 'About 60 suppliers. Most products are sourced within Europe; selected PPE, equipment and furniture lines are imported from China. China provides cost and range advantages, but adds long and uncertain lead times.')
    y = bullet(c, y, 'Physical flow: ', 'All inventory is held in a single central DC. The DC receives supplier deliveries, fulfils customer orders and backorders, processes rare returns, and performs occasional cycle-count adjustments.')
    y = bullet(c, y, 'Commercial economics: ', 'Prices and purchase costs are managed in EUR. Annual supplier agreements can provide a rebate when full-year qualifying spend passes a threshold; the value of reaching a threshold must be assessed against holding, cash and obsolescence risk.')
    add_text(c, LEFT, y, 'What matters to the client', 12, True); y -= 21
    y = paragraph(c, y, 'Availability has a clinical and commercial dimension. A stockout of a low-value commodity may disrupt a ward and weaken trust, while a shortage of a device or procedure consumable can create an immediate customer-service escalation. Conversely, overstock consumes working capital, DC capacity and attention. The company therefore needs decisions that are economically sound at portfolio level, not a blanket attempt to maximise every item service level.')
    return c

def make_page_two() -> list[str]:
    c: list[str] = []
    y = page_header(c, 'Supply-chain challenges and project expectations', 2)
    add_text(c, LEFT, y, 'Why this is a difficult inventory business', 12, True); y -= 21
    y = bullet(c, y, 'Uneven demand: ', 'The portfolio combines regular ward consumables with intermittent laboratory needs, lumpy equipment demand, launches, declining lines and seasonal facilities purchases. Sales history is also censored when stock is unavailable, so observed sales are not always true demand.')
    y = bullet(c, y, 'Service versus capital: ', 'Recent service performance is near 90%, which is intentionally good but imperfect. The remaining shortages create backorders, lost demand and penalties. Raising service indiscriminately can create excess inventory in slow-moving and long-lead-time lines.')
    y = bullet(c, y, 'Procurement constraints: ', 'Orders must respect supplier-item approval, case and pallet conversions, MOQ, order multiples, supplier minimum order values and supplier order calendars. A mathematically attractive order that fails these constraints is not executable.')
    y = bullet(c, y, 'Lead-time uncertainty: ', 'European replenishment is comparatively short, while China-sourced products combine production, transit, customs and final-mile uncertainty. Chinese New Year can delay a cohort of orders placed in the affected production window, not just a single SKU.')
    y = bullet(c, y, 'Year-end trade-off: ', 'The final 2026 ordering rounds may determine whether an annual supplier rebate threshold is reached. A forward buy can be valuable, but only if future demand, inventory carrying cost, supplier lead time and working-capital impact justify it.')
    add_text(c, LEFT, y, 'What the project team is expected to do', 12, True); y -= 21
    y = paragraph(c, y, 'The project will run in twelve monthly planning rounds from July 2026 to June 2027. Each round begins with the information available at that date. Teams submit probabilistic demand forecasts and purchase orders; operations then progress daily until the next decision date.')
    y = bullet(c, y, 'Forecasting: ', 'Build forecasts from the public history, including uncertainty rather than only a single point estimate. Forecast evaluation uses uncensored demand and weighted quantile loss, so intermittent and lumpy products cannot be handled safely with MAPE alone.')
    y = bullet(c, y, 'Replenishment: ', 'Translate forecasts and the current state into valid purchase orders. Account for on-hand stock, open POs, backlog, lead time, packaging and supplier constraints. Use automated, reproducible logic rather than manual order lists.')
    y = bullet(c, y, 'Economic decisions: ', 'Balance fulfilled margin, carrying cost, shortage and delay penalties, supplier rebates, and year-end inventory value. The goal is risk-adjusted contribution, not the highest possible service rate or the largest possible order volume.')
    add_text(c, LEFT, y, 'Data and governance expectations', 12, True); y -= 21
    y = paragraph(c, y, 'The public data is an operational extract: masters, orders, the consolidated purchase-order and receipt history, movement ledger, daily inventory history and reference-date stock. The underlying event flow reconciles by item and day. Private files contain latent demand and are reserved for evaluation. Teams should treat data-quality checks, traceability and reproducibility as part of the supply-chain solution, not as administrative work.')
    return c

def build_pdf(pages: list[list[str]]) -> bytes:
    objects = ['<< /Type /Catalog /Pages 2 0 R >>', '<< /Type /Pages /Kids [' + ' '.join(f'{5+i*2} 0 R' for i in range(len(pages))) + f'] /Count {len(pages)} >>', '<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>', '<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica-Bold >>']
    for i, cmds in enumerate(pages):
        stream = ('0.35 w\n' + '\n'.join(cmds)).encode('latin-1', 'replace')
        page_obj = f'<< /Type /Page /Parent 2 0 R /MediaBox [0 0 {W} {H}] /Resources << /Font << /F1 3 0 R /F2 4 0 R >> >> /Contents {6+i*2} 0 R >>'
        objects.extend([page_obj, f'<< /Length {len(stream)} >>\nstream\n{stream.decode("latin-1")}\nendstream'])
    out = bytearray(b'%PDF-1.4\n%\xe2\xe3\xcf\xd3\n'); offsets=[0]
    for n,obj in enumerate(objects,1):
        offsets.append(len(out)); out.extend(f'{n} 0 obj\n{obj}\nendobj\n'.encode('latin-1'))
    xref=len(out); out.extend(f'xref\n0 {len(objects)+1}\n0000000000 65535 f \n'.encode())
    out.extend(b''.join(f'{o:010d} 00000 n \n'.encode() for o in offsets[1:])); out.extend(f'trailer\n<< /Size {len(objects)+1} /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF\n'.encode())
    return bytes(out)

if __name__ == '__main__':
    OUT.parent.mkdir(exist_ok=True)
    OUT.write_bytes(build_pdf([make_page_one(), make_page_two()]))
    print(OUT)
