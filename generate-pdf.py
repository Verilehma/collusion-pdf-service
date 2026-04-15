"""
Collusion Wine Group — PDF Invoice & Manifest Generator
Usage:
  python generate-pdf.py invoice --order-id <id>
  python generate-pdf.py manifest --order-id <id>
  python generate-pdf.py both --order-id <id>

For testing without a DB connection, run with --mock:
  python generate-pdf.py both --mock
"""
# -*- coding: utf-8 -*-
import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

import argparse
from datetime import date, timedelta
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import mm
from reportlab.lib.styles import ParagraphStyle
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    HRFlowable, KeepTogether, Flowable
)
from reportlab.lib.enums import TA_LEFT, TA_RIGHT, TA_CENTER

class HollowCheckbox(Flowable):
    """A small hollow square drawn directly on the canvas — no font glyph involved."""
    def __init__(self, size=4.5*mm):
        super().__init__()
        self.size   = size
        self.width  = size
        self.height = size

    def draw(self):
        s = self.size
        self.canv.saveState()
        self.canv.setStrokeColor(colors.HexColor("#1A1A1A"))
        self.canv.setLineWidth(0.75)
        self.canv.setFillColor(colors.white)
        self.canv.rect(0, 0, s, s, fill=1, stroke=1)
        self.canv.restoreState()

# ── Palette ────────────────────────────────────────────────────────────────────
BLACK       = colors.HexColor("#0D0D0D")
WHITE       = colors.HexColor("#FFFFFF")
GOLD        = colors.HexColor("#C8A96E")
LIGHT_GRAY  = colors.HexColor("#F5F5F5")
MID_GRAY    = colors.HexColor("#CCCCCC")
DARK_GRAY   = colors.HexColor("#555555")
TEXT        = colors.HexColor("#1A1A1A")

PAGE_W, PAGE_H = A4
MARGIN = 18 * mm

# ── Typography ─────────────────────────────────────────────────────────────────
def style(name, **kwargs):
    base = dict(fontName="Helvetica", fontSize=9, leading=13,
                textColor=TEXT, alignment=TA_LEFT)
    base.update(kwargs)
    return ParagraphStyle(name, **base)

S_TITLE        = style("title",   fontName="Helvetica-Bold", fontSize=22, leading=26, textColor=BLACK)
S_SUBTITLE     = style("sub",     fontName="Helvetica",      fontSize=11, textColor=DARK_GRAY)
S_LABEL        = style("label",   fontName="Helvetica-Bold", fontSize=7,  textColor=DARK_GRAY, leading=10)
S_VALUE        = style("value",   fontName="Helvetica",      fontSize=9,  textColor=TEXT)
S_VALUE_BOLD   = style("valueb",  fontName="Helvetica-Bold", fontSize=9,  textColor=TEXT)
S_SMALL        = style("small",   fontName="Helvetica",      fontSize=7,  textColor=DARK_GRAY, leading=10)
S_LABEL_C      = style("labelc",  fontName="Helvetica-Bold", fontSize=6,  textColor=DARK_GRAY, leading=7)
S_VALUE_C      = style("valuec",  fontName="Helvetica",      fontSize=7,  textColor=TEXT,      leading=9)
S_TH           = style("th",      fontName="Helvetica-Bold", fontSize=8,  textColor=WHITE)
S_TD           = style("td",      fontName="Helvetica",      fontSize=8,  textColor=TEXT, leading=11)
S_TD_RIGHT     = style("tdr",     fontName="Helvetica",      fontSize=8,  textColor=TEXT, leading=11, alignment=TA_RIGHT)
S_TD_BOLD      = style("tdb",     fontName="Helvetica-Bold", fontSize=8,  textColor=TEXT, leading=11)
S_TD_BOLD_R    = style("tdbr",    fontName="Helvetica-Bold", fontSize=8,  textColor=TEXT, leading=11, alignment=TA_RIGHT)
S_TOTAL_LABEL  = style("totl",    fontName="Helvetica-Bold", fontSize=10, textColor=TEXT, alignment=TA_RIGHT)
S_TOTAL_VALUE  = style("totv",    fontName="Helvetica-Bold", fontSize=10, textColor=BLACK)
S_FOOTER       = style("footer",  fontName="Helvetica",      fontSize=7,  textColor=DARK_GRAY, alignment=TA_CENTER)
S_GOLD_LABEL   = style("gold",    fontName="Helvetica-Bold", fontSize=7,  textColor=GOLD, leading=10)

# ── Mock data ──────────────────────────────────────────────────────────────────
MOCK_ORDER = {
    "id":           "ORD-2024-0042",
    "created_at":   date.today().isoformat(),
    "due_date":     (date.today() + timedelta(days=30)).isoformat(),
    "status":       "confirmed",
    "notes":        "Please deliver before 14:00. Ring bell at back entrance.",
    "agent": {
        "name":     "Collusion Wine Group",
        "business_id": "3456789-1",
        "address":  "Eteläesplanadi 20, 00130 Helsinki",
        "email":    "orders@collusion.fi",
        "phone":    "+358 50 123 4567",
        "iban":     "FI12 3456 7890 1234 56",
        "bic":      "OKOYFIHH",
    },
    "customer": {
        "name":         "Test Ravintola Oy",
        "business_id":  "1234567-8",
        "address":      "Mannerheimintie 12, 00100 Helsinki",
        "contact":      "Matti Meikäläinen",
        "email":        "tilaukset@testravintola.fi",
        "phone":        "+358 40 987 6543",
    },
    "delivery": {
        "address":      "Mannerheimintie 12, 00100 Helsinki",
        "date":         (date.today() + timedelta(days=3)).isoformat(),
        "driver":       "",
        "vehicle":      "",
    },
    "lines": [
        {
            "sku":          "COL-FR-BOR-001",
            "name":         "Château Margaux 2018",
            "producer":     "Château Margaux",
            "region":       "Margaux, Bordeaux",
            "vintage":      2018,
            "bottle_size":  "75cl",
            "cases":        2,
            "bottles_per_case": 6,
            "unit_price":   68.50,
            "vat_pct":      24,
        },
        {
            "sku":          "COL-FR-BUR-012",
            "name":         "Gevrey-Chambertin Villages 2020",
            "producer":     "Domaine Rossignol-Trapet",
            "region":       "Gevrey-Chambertin, Burgundy",
            "vintage":      2020,
            "bottle_size":  "75cl",
            "cases":        3,
            "bottles_per_case": 6,
            "unit_price":   34.00,
            "vat_pct":      24,
        },
        {
            "sku":          "COL-IT-PIE-007",
            "name":         "Barolo Ravera DOCG 2019",
            "producer":     "Elvio Cogno",
            "region":       "Novello, Piedmont",
            "vintage":      2019,
            "bottle_size":  "75cl",
            "cases":        1,
            "bottles_per_case": 6,
            "unit_price":   52.00,
            "vat_pct":      24,
        },
        {
            "sku":          "COL-ES-RIO-003",
            "name":         "La Rioja Alta Gran Reserva 890",
            "producer":     "La Rioja Alta",
            "region":       "Rioja Alta",
            "vintage":      2015,
            "bottle_size":  "75cl",
            "cases":        2,
            "bottles_per_case": 6,
            "unit_price":   41.50,
            "vat_pct":      24,
        },
    ],
}

# ── Helpers ────────────────────────────────────────────────────────────────────
def p(text, style=S_VALUE): return Paragraph(str(text), style)
def sp(h=4):                return Spacer(1, h * mm)
def hr(color=MID_GRAY, thickness=0.5): return HRFlowable(width="100%", thickness=thickness, color=color, spaceAfter=0, spaceBefore=0)

def label_value(label, value, label_style=S_LABEL, value_style=S_VALUE):
    return [p(label, label_style), p(value, value_style)]

def info_block(pairs):
    """pairs = [(label, value), ...]"""
    items = []
    for lbl, val in pairs:
        items += label_value(lbl, val)
        items.append(sp(1))
    return items

def two_col_table(left_items, right_items, col_widths=None):
    """Place two vertical stacks side by side."""
    cw = col_widths or [(PAGE_W - 2*MARGIN) * 0.5, (PAGE_W - 2*MARGIN) * 0.5]
    data = [[left_items, right_items]]
    t = Table(data, colWidths=cw)
    t.setStyle(TableStyle([
        ("VALIGN", (0,0), (-1,-1), "TOP"),
        ("LEFTPADDING",  (0,0), (-1,-1), 0),
        ("RIGHTPADDING", (0,0), (-1,-1), 0),
        ("TOPPADDING",   (0,0), (-1,-1), 0),
        ("BOTTOMPADDING",(0,0), (-1,-1), 0),
    ]))
    return t

def calc_lines(lines):
    """Add computed fields to each line."""
    for l in lines:
        l["bottles"]   = l["cases"] * l["bottles_per_case"]
        l["line_excl"] = l["bottles"] * l["unit_price"]
        l["vat_amt"]   = l["line_excl"] * l["vat_pct"] / 100
        l["line_incl"] = l["line_excl"] + l["vat_amt"]
    return lines

def totals(lines):
    excl  = sum(l["line_excl"] for l in lines)
    vat   = sum(l["vat_amt"]   for l in lines)
    incl  = excl + vat
    bottles = sum(l["bottles"] for l in lines)
    cases   = sum(l["cases"]   for l in lines)
    return excl, vat, incl, bottles, cases

# ── Shared header ──────────────────────────────────────────────────────────────
def build_header(order, doc_type_label):
    agent    = order["agent"]
    customer = order["customer"]
    story    = []

    # — Logo row —
    logo_col = [
        p("COLLUSION", ParagraphStyle("logo", fontName="Helvetica-Bold", fontSize=18,
                                       textColor=BLACK, leading=22)),
        p("WINE GROUP", ParagraphStyle("logo2", fontName="Helvetica", fontSize=9,
                                        textColor=DARK_GRAY, leading=12, tracking=3)),
    ]
    doc_col = [
        p(doc_type_label, ParagraphStyle("doctype", fontName="Helvetica-Bold", fontSize=14,
                                          textColor=BLACK, leading=18, alignment=TA_RIGHT)),
        p(f"#{order['id']}", ParagraphStyle("docid", fontName="Helvetica", fontSize=9,
                                             textColor=DARK_GRAY, leading=12, alignment=TA_RIGHT)),
        p(f"Date: {order['created_at']}", ParagraphStyle("docdate", fontName="Helvetica", fontSize=8,
                                                          textColor=DARK_GRAY, leading=12, alignment=TA_RIGHT)),
    ]
    story.append(two_col_table(logo_col, doc_col))
    story.append(sp(2))
    story.append(HRFlowable(width="100%", thickness=1.5, color=GOLD, spaceAfter=0, spaceBefore=0))
    story.append(sp(5))

    # — From / To / Delivery —
    from_items = info_block([
        ("FROM",           ""),
        ("Company",        agent["name"]),
        ("Business ID",    agent["business_id"]),
        ("Address",        agent["address"]),
        ("Email",          agent["email"]),
        ("Phone",          agent["phone"]),
    ])
    to_items = info_block([
        ("TO",             ""),
        ("Company",        customer["name"]),
        ("Business ID",    customer["business_id"]),
        ("Address",        customer["address"]),
        ("Contact",        customer["contact"]),
        ("Email",          customer["email"]),
    ])
    story.append(two_col_table(from_items, to_items))
    story.append(sp(6))

    return story

# ── INVOICE ────────────────────────────────────────────────────────────────────
def build_invoice(order, out_path):
    lines = calc_lines(order["lines"])
    excl, vat, incl, bottles, cases = totals(lines)
    agent = order["agent"]

    doc = SimpleDocTemplate(
        out_path, pagesize=A4,
        leftMargin=MARGIN, rightMargin=MARGIN,
        topMargin=MARGIN, bottomMargin=MARGIN + 10*mm,
    )

    story = build_header(order, "INVOICE")

    # — Payment details bar —
    pay_data = [[
        [p("PAYMENT DUE", S_GOLD_LABEL), p(order["due_date"], S_VALUE_BOLD)],
        [p("IBAN", S_GOLD_LABEL), p(agent["iban"], S_VALUE_BOLD)],
        [p("BIC", S_GOLD_LABEL), p(agent["bic"], S_VALUE_BOLD)],
        [p("REFERENCE", S_GOLD_LABEL), p(order["id"], S_VALUE_BOLD)],
    ]]
    cw = (PAGE_W - 2*MARGIN) / 4
    pay_table = Table(pay_data, colWidths=[cw]*4)
    pay_table.setStyle(TableStyle([
        ("BACKGROUND",   (0,0), (-1,-1), LIGHT_GRAY),
        ("VALIGN",       (0,0), (-1,-1), "TOP"),
        ("LEFTPADDING",  (0,0), (-1,-1), 6),
        ("RIGHTPADDING", (0,0), (-1,-1), 6),
        ("TOPPADDING",   (0,0), (-1,-1), 5),
        ("BOTTOMPADDING",(0,0), (-1,-1), 5),
        ("LINEABOVE",    (0,0), (-1,0),  0.5, GOLD),
        ("LINEBELOW",    (0,-1),(-1,-1), 0.5, GOLD),
    ]))
    story.append(pay_table)
    story.append(sp(6))

    # — Line items —
    headers = ["SKU", "Wine / Producer", "Vintage", "Size",
               "Cases", "Btls", "Unit (€)", "Excl. VAT (€)", "VAT %", "Total incl. (€)"]
    col_w = [
        20*mm, 62*mm, 14*mm, 10*mm,
        11*mm, 10*mm, 18*mm, 22*mm, 12*mm, 25*mm,
    ]

    table_data = [[p(h, S_TH) for h in headers]]
    for i, l in enumerate(lines):
        bg = WHITE if i % 2 == 0 else LIGHT_GRAY
        row = [
            p(l["sku"], S_TD),
            [p(l["name"], S_TD_BOLD), p(f"{l['producer']} · {l['region']}", S_SMALL)],
            p(str(l["vintage"]), S_TD),
            p(l["bottle_size"], S_TD),
            p(str(l["cases"]), S_TD),
            p(str(l["bottles"]), S_TD),
            p(f"{l['unit_price']:.2f}", S_TD_RIGHT),
            p(f"{l['line_excl']:.2f}", S_TD_RIGHT),
            p(f"{l['vat_pct']}%", S_TD),
            p(f"{l['line_incl']:.2f}", S_TD_RIGHT),
        ]
        table_data.append(row)

    items_table = Table(table_data, colWidths=col_w, repeatRows=1)
    items_table.setStyle(TableStyle([
        ("BACKGROUND",   (0,0),  (-1,0),  BLACK),
        ("ROWBACKGROUNDS",(0,1), (-1,-1), [WHITE, LIGHT_GRAY]),
        ("VALIGN",       (0,0),  (-1,-1), "TOP"),
        ("LEFTPADDING",  (0,0),  (-1,-1), 4),
        ("RIGHTPADDING", (0,0),  (-1,-1), 4),
        ("TOPPADDING",   (0,0),  (-1,-1), 4),
        ("BOTTOMPADDING",(0,0),  (-1,-1), 4),
        ("LINEBELOW",    (0,-1), (-1,-1), 0.5, MID_GRAY),
    ]))
    story.append(items_table)
    story.append(sp(5))

    # — Totals block —
    total_w = PAGE_W - 2*MARGIN
    totals_data = [
        [p("Subtotal excl. VAT", S_TOTAL_LABEL), p(f"€ {excl:,.2f}", S_TD_RIGHT)],
        [p("VAT (24%)",          S_TOTAL_LABEL), p(f"€ {vat:,.2f}",  S_TD_RIGHT)],
        [p("TOTAL INCL. VAT",   ParagraphStyle("tot", fontName="Helvetica-Bold", fontSize=11,
                                                textColor=BLACK, alignment=TA_RIGHT)),
         p(f"€ {incl:,.2f}", ParagraphStyle("totv", fontName="Helvetica-Bold", fontSize=11,
                                             textColor=BLACK, alignment=TA_RIGHT))],
    ]
    totals_table = Table(totals_data, colWidths=[total_w - 60*mm, 60*mm])
    totals_table.setStyle(TableStyle([
        ("VALIGN",       (0,0), (-1,-1), "MIDDLE"),
        ("LEFTPADDING",  (0,0), (-1,-1), 0),
        ("RIGHTPADDING", (0,0), (-1,-1), 0),
        ("TOPPADDING",   (0,0), (-1,-1), 3),
        ("BOTTOMPADDING",(0,0), (-1,-1), 3),
        ("LINEABOVE",    (0,2), (-1,2),  1.0, BLACK),
        ("LINEBELOW",    (0,2), (-1,2),  0.5, GOLD),
    ]))
    story.append(totals_table)

    # — Notes —
    if order.get("notes"):
        story.append(sp(6))
        story.append(hr())
        story.append(sp(3))
        story.append(p("NOTES", S_LABEL))
        story.append(sp(1))
        story.append(p(order["notes"], S_VALUE))

    # — Footer —
    def footer(canvas, doc):
        canvas.saveState()
        canvas.setFont("Helvetica", 7)
        canvas.setFillColor(DARK_GRAY)
        y = MARGIN / 2
        canvas.drawCentredString(PAGE_W / 2, y + 4*mm,
            f"{agent['name']} · {agent['address']} · {agent['email']} · {agent['phone']}")
        canvas.drawCentredString(PAGE_W / 2, y,
            f"Business ID {agent['business_id']} · IBAN {agent['iban']} · BIC {agent['bic']}")
        canvas.restoreState()

    doc.build(story, onFirstPage=footer, onLaterPages=footer)
    print(f"  OK Invoice saved: {out_path}")

# ── MANIFEST ───────────────────────────────────────────────────────────────────
def build_manifest(order, out_path):
    lines = calc_lines(order["lines"])
    excl, vat, incl, total_bottles, total_cases = totals(lines)
    agent    = order["agent"]
    customer = order["customer"]
    delivery = order["delivery"]

    # B&W palette for manifest
    BW_HEADER  = colors.HexColor("#1A1A1A")
    BW_STRIPE  = colors.HexColor("#EFEFEF")
    BW_RULE    = colors.HexColor("#888888")
    BW_TOTAL   = colors.HexColor("#D0D0D0")

    S_TH_BW    = style("thbw",  fontName="Helvetica-Bold", fontSize=8, textColor=WHITE)
    S_LABEL_BW = style("labbw", fontName="Helvetica-Bold", fontSize=7, textColor=colors.HexColor("#555555"), leading=10)

    doc = SimpleDocTemplate(
        out_path, pagesize=A4,
        leftMargin=MARGIN, rightMargin=MARGIN,
        topMargin=MARGIN, bottomMargin=MARGIN + 10*mm,
    )

    # — Build a B&W header (no gold) —
    story = []
    logo_col = [
        p("COLLUSION", ParagraphStyle("logo", fontName="Helvetica-Bold", fontSize=18,
                                       textColor=BLACK, leading=22)),
        p("WINE GROUP", ParagraphStyle("logo2", fontName="Helvetica", fontSize=9,
                                        textColor=DARK_GRAY, leading=12)),
    ]
    doc_col = [
        p("DELIVERY MANIFEST", ParagraphStyle("doctype", fontName="Helvetica-Bold", fontSize=14,
                                               textColor=BLACK, leading=18, alignment=TA_RIGHT)),
        p(f"#{order['id']}", ParagraphStyle("docid", fontName="Helvetica", fontSize=9,
                                             textColor=DARK_GRAY, leading=12, alignment=TA_RIGHT)),
        p(f"Date: {order['created_at']}", ParagraphStyle("docdate", fontName="Helvetica", fontSize=8,
                                                          textColor=DARK_GRAY, leading=12, alignment=TA_RIGHT)),
    ]
    story.append(two_col_table(logo_col, doc_col))
    story.append(sp(2))
    story.append(HRFlowable(width="100%", thickness=1.5, color=BLACK, spaceAfter=0, spaceBefore=0))
    story.append(sp(5))

    # — From / To (compact — less important, both parties know who they are) —
    def compact_block(pairs):
        items = []
        for lbl, val in pairs:
            if val:
                items += [p(lbl, S_LABEL_C), p(val, S_VALUE_C), Spacer(1, 1.2*mm)]
            else:
                items += [p(lbl, style("sec", fontName="Helvetica-Bold", fontSize=6.5,
                                       textColor=DARK_GRAY, leading=8))]
        return items

    from_items = compact_block([
        ("FROM",        ""),
        ("Company",     agent["name"]),
        ("Business ID", agent["business_id"]),
        ("Address",     agent["address"]),
        ("Email",       agent["email"]),
        ("Phone",       agent["phone"]),
    ])
    to_items = compact_block([
        ("TO",          ""),
        ("Company",     customer["name"]),
        ("Business ID", customer["business_id"]),
        ("Address",     customer["address"]),
        ("Contact",     customer["contact"]),
        ("Email",       customer["email"]),
    ])
    story.append(two_col_table(from_items, to_items))
    story.append(sp(3))

    # — Delivery details bar (date + address only, B&W) —
    total_w = PAGE_W - 2*MARGIN
    del_data = [[
        [p("DELIVERY DATE",    S_LABEL_BW), p(delivery["date"],    S_VALUE_BOLD)],
        [p("DELIVERY ADDRESS", S_LABEL_BW), p(delivery["address"], S_VALUE_BOLD)],
    ]]
    del_table = Table(del_data, colWidths=[total_w * 0.3, total_w * 0.7])
    del_table.setStyle(TableStyle([
        ("BACKGROUND",   (0,0), (-1,-1), BW_STRIPE),
        ("VALIGN",       (0,0), (-1,-1), "TOP"),
        ("LEFTPADDING",  (0,0), (-1,-1), 6),
        ("RIGHTPADDING", (0,0), (-1,-1), 6),
        ("TOPPADDING",   (0,0), (-1,-1), 5),
        ("BOTTOMPADDING",(0,0), (-1,-1), 5),
        ("LINEABOVE",    (0,0), (-1,0),  0.5, BLACK),
        ("LINEBELOW",    (0,-1),(-1,-1), 0.5, BLACK),
    ]))
    story.append(del_table)
    story.append(sp(6))

    # — Packing list (no SKU column) —
    headers = ["Wine / Producer", "Vintage", "Size", "Cases", "Btls/Case",
               "Total Btls", "Excl. VAT (€)", "Incl. VAT (€)", "✓"]
    col_w   = [74*mm, 14*mm, 12*mm, 14*mm, 16*mm, 16*mm, 22*mm, 22*mm, 10*mm]

    table_data = [[p(h, S_TH_BW) for h in headers]]
    for i, l in enumerate(lines):
        row = [
            [p(l["name"], S_TD_BOLD), p(f"{l['producer']} · {l['region']}", S_SMALL)],
            p(str(l["vintage"]), S_TD),
            p(l["bottle_size"], S_TD),
            p(str(l["cases"]), S_TD),
            p(str(l["bottles_per_case"]), S_TD),
            p(str(l["bottles"]), S_TD_BOLD),
            p(f"{l['line_excl']:.2f}", S_TD_RIGHT),
            p(f"{l['line_incl']:.2f}", S_TD_RIGHT),
            HollowCheckbox(),
        ]
        table_data.append(row)

    # Totals row
    table_data.append([
        p("TOTALS", S_TD_BOLD),
        p("", S_TD),
        p("", S_TD),
        p(str(total_cases),   S_TD_BOLD),
        p("", S_TD),
        p(str(total_bottles), S_TD_BOLD),
        p(f"{excl:.2f}",      S_TD_BOLD_R),
        p(f"{incl:.2f}",      S_TD_BOLD_R),
        p("", S_TD),
    ])

    pack_table = Table(table_data, colWidths=col_w, repeatRows=1)
    pack_table.setStyle(TableStyle([
        ("BACKGROUND",    (0,0),  (-1,0),   BW_HEADER),
        ("ROWBACKGROUNDS",(0,1),  (-1,-2),  [WHITE, BW_STRIPE]),
        ("BACKGROUND",    (0,-1), (-1,-1),  BW_TOTAL),
        ("VALIGN",        (0,0),  (-1,-1),  "MIDDLE"),
        ("LEFTPADDING",   (0,0),  (-1,-1),  4),
        ("RIGHTPADDING",  (0,0),  (-1,-1),  4),
        ("TOPPADDING",    (0,0),  (-1,-1),  4),
        ("BOTTOMPADDING", (0,0),  (-1,-1),  4),
        ("LINEABOVE",     (0,-1), (-1,-1),  1.0, BLACK),
        ("LINEBELOW",     (0,-1), (-1,-1),  1.0, BLACK),
        ("ALIGN",         (6,0),  (7,-1),   "RIGHT"),
        ("ALIGN",         (8,0),  (8,-1),   "CENTER"),
    ]))
    story.append(pack_table)

    # — Notes —
    if order.get("notes"):
        story.append(sp(6))
        story.append(HRFlowable(width="100%", thickness=0.5, color=BW_RULE, spaceAfter=0, spaceBefore=0))
        story.append(sp(3))
        story.append(p("DELIVERY NOTES", S_LABEL_BW))
        story.append(sp(1))
        story.append(p(order["notes"], S_VALUE))

    # — Footer —
    def footer(canvas, doc):
        canvas.saveState()
        canvas.setFont("Helvetica", 7)
        canvas.setFillColor(DARK_GRAY)
        y = MARGIN / 2
        canvas.drawCentredString(PAGE_W / 2, y + 4*mm,
            f"{agent['name']} · {agent['address']} · {agent['email']} · {agent['phone']}")
        canvas.drawCentredString(PAGE_W / 2, y,
            f"Order #{order['id']} · Manifest generated {date.today().isoformat()}")
        canvas.restoreState()

    doc.build(story, onFirstPage=footer, onLaterPages=footer)
    print(f"  OK Manifest saved: {out_path}")

# ── DB fetch (stub — wire to Prisma/Supabase) ──────────────────────────────────
def fetch_order(order_id):
    """
    Replace this with a real DB fetch, e.g. via Prisma JSON output or
    a direct psycopg2 / asyncpg query against Supabase.
    Example Prisma call:
        result = subprocess.run(
            ["npx", "tsx", "scripts/get-order.ts", order_id],
            capture_output=True, text=True
        )
        return json.loads(result.stdout)
    """
    raise NotImplementedError(
        f"fetch_order({order_id!r}) not yet implemented. "
        "Use --mock for testing, or wire up your DB call here."
    )

# ── CLI ────────────────────────────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(description="Generate Collusion Wine Group PDFs")
    parser.add_argument("doc", choices=["invoice", "manifest", "both"])
    parser.add_argument("--order-id", default="")
    parser.add_argument("--mock", action="store_true", help="Use built-in mock data")
    parser.add_argument("--json", default="", help="Path to order JSON file")
    parser.add_argument("--out-dir", default=".", help="Output directory")
    args = parser.parse_args()

    if args.mock:
        order = MOCK_ORDER
    elif args.json:
        import json as _json
        with open(args.json) as f:
            order = _json.load(f)
    else:
        order = fetch_order(args.order_id)
    oid   = order["id"].replace("/", "-")

    print(f"\nGenerating {args.doc} for order {oid}...")

    if args.doc in ("invoice", "both"):
        build_invoice(order, f"{args.out_dir}/{oid}-invoice.pdf")

    if args.doc in ("manifest", "both"):
        build_manifest(order, f"{args.out_dir}/{oid}-manifest.pdf")

    print("Done.\n")

if __name__ == "__main__":
    main()
