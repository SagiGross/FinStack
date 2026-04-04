"""
FinStack CFO Command Center v5 — SQLite Persistence
=====================================================
All data stored in finstack.db. Survives restarts.
Seeds initial data on first run only.

INSTALL:  py -m pip install fastapi uvicorn
RUN:      py app.py
OPEN:     http://localhost:8000
DB FILE:  finstack.db (created automatically)
"""
from __future__ import annotations
import sqlite3, json, os
from contextlib import contextmanager
from datetime import date, timedelta
from pathlib import Path
from typing import Optional
from uuid import uuid4

from fastapi import FastAPI, Query
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

app = FastAPI(title="FinStack CFO API", version="5.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

ECF = 1.35
FY = 2026
ML = [f"{m:02d}-{FY}" for m in range(1, 13)]

DB_PATH = Path(__file__).parent / "finstack.db"

# ══════════════════════════════════════════
# DATABASE LAYER
# ══════════════════════════════════════════
@contextmanager
def get_db():
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()

def init_db():
    """Create tables if they don't exist."""
    with get_db() as db:
        db.executescript("""
        CREATE TABLE IF NOT EXISTS employees (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            dept TEXT NOT NULL,
            gross REAL NOT NULL,
            hire_date TEXT NOT NULL,
            term_date TEXT,
            is_ghost INTEGER DEFAULT 0
        );
        CREATE TABLE IF NOT EXISTS contracts (
            id TEXT PRIMARY KEY,
            client TEXT NOT NULL,
            country TEXT DEFAULT '',
            industry TEXT DEFAULT 'Enterprise',
            yr INTEGER,
            sm INTEGER,
            sd TEXT,
            val REAL NOT NULL,
            dso INTEGER DEFAULT 60,
            pm TEXT,
            monthly INTEGER DEFAULT 0,
            chance REAL,
            ap REAL
        );
        CREATE TABLE IF NOT EXISTS expenses (
            id TEXT PRIMARY KEY,
            dept TEXT NOT NULL,
            vendor TEXT NOT NULL,
            sub_cat TEXT DEFAULT '',
            is_cogs INTEGER DEFAULT 0,
            amounts TEXT DEFAULT '{}'
        );
        """)

def is_seeded():
    with get_db() as db:
        r = db.execute("SELECT COUNT(*) as c FROM employees").fetchone()
        return r["c"] > 0

def carry_forward(known: dict[str, float]) -> dict[str, float]:
    result = {}
    last = 0.0
    for m in ML:
        if m in known and known[m] is not None:
            last = known[m]
        result[m] = last
    return result

def seed_db():
    """Insert initial data from Excel — runs only once."""
    with get_db() as db:
        # Employees
        emps = [
            ("e01","Etti Berger","G&A",16487.46,"2024-01-01",None),
            ("e02","Shai Grumet","R&D",11314.92,"2024-01-01",None),
            ("e03","Arye Laskin","R&D",9051.94,"2024-01-01",None),
            ("e04","Oren Chappo","R&D",11961.49,"2024-01-01",None),
            ("e05","Eduardo Borotchin","S&M",10345.07,"2024-01-01",None),
            ("e06","Nitai Driel","R&D",387.94,"2024-01-01",None),
            ("e07","Elad Lev","S&M",8082.09,"2024-01-01",None),
            ("e08","Tiki Tavero","S&M",6465.67,"2024-01-01",None),
            ("e09","Meirav Zetz","G&A",2020.52,"2024-01-01",None),
            ("e10","Yaniv Barkai","R&D",19431.60,"2024-01-01","2026-01-31"),
            ("e11","Elad Sheskin","R&D",0,"2024-01-01","2025-12-31"),
        ]
        db.executemany("INSERT OR IGNORE INTO employees (id,name,dept,gross,hire_date,term_date) VALUES (?,?,?,?,?,?)", emps)

        # Contracts
        cons = [
            ("c01","Ministry of Defence","Indonesia","Government",2026,1,"2026-01-01",800000,60,"03-2026",0,0.75,None),
            ("c02","Ministry of Defence","Indonesia","Government",2026,1,"2026-01-01",150000,120,"05-2026",0,0.75,None),
            ("c03","Serbia","Serbia","Government",2025,10,"2025-10-01",90000,240,"05-2026",0,0.5,None),
            ("c04","Practical Cyber Academy","Singapore","Academy",2026,2,"2026-02-01",155000,240,"09-2026",0,0.75,None),
            ("c05","IAI","Israel","Enterprise",2025,11,"2025-11-01",200000,180,"04-2026",0,None,None),
            ("c06","Elta","Israel","Enterprise",2025,10,"2025-10-01",5000,180,"03-2026",0,1.0,3483.87),
            ("c07","Elta","Israel","Enterprise",2025,10,"2025-10-01",900000,270,"06-2026",0,0.5,None),
            ("c08","Elta","Israel","Enterprise",2026,2,"2026-02-01",480000,120,"06-2026",0,0.25,None),
            ("c09","Elta","Israel","Enterprise",2026,1,"2026-01-01",200000,270,"09-2026",0,0.25,None),
            ("c11","Schools","Israel","Academy",2025,10,"2025-10-01",15000,120,"01-2026",0,1.0,11231.94),
            ("c12","The Jewish Agency","Israel","Government",2026,2,"2026-02-01",4000,180,"07-2026",0,0.25,None),
            ("c13","Improvate","Israel","Academy",2026,5,"2026-05-01",150000,60,"06-2026",1,1.0,12108.06),
            ("c15","SPAN","Croatia","Enterprise",2025,12,"2025-12-01",29000,300,"09-2026",0,0.75,None),
            ("c16","Bank of Israel","Israel","Government",2026,1,"2026-01-01",15000,45,"02-2026",0,1.0,None),
            ("c17","Military Academy","Macedonia","Government",2026,1,"2026-01-01",32500,270,"09-2026",0,0.25,None),
            ("c18","DSA","Cyprus","Government",2025,10,"2025-10-01",56000,210,"04-2026",0,0.5,35404.52),
            ("c19","DSA","Cyprus","Government",2026,1,"2026-01-01",73000,360,"12-2026",0,0.5,None),
            ("c20","DSA","Cyprus","Government",2026,3,"2026-03-01",76000,240,"10-2026",0,0.75,None),
            ("c23","MAG","Nigeria","Enterprise",2026,1,"2026-01-01",30000,45,"02-2026",0,1.0,22800),
            ("c24","Future Smart","Greece","Academy",2025,12,"2025-12-01",2500,270,"08-2026",0,1.0,None),
            ("c25","Technion","Israel","Academy",2026,1,"2026-01-01",42000,270,"09-2026",1,1.0,3870.97),
            ("c28","EU Funding","Greece","Government",2026,1,"2026-01-01",300000,270,"09-2026",0,0.25,None),
            ("c31","Abu Dhabi","UAE","Government",2026,1,"2026-01-01",300000,270,"09-2026",0,0.75,None),
            ("c32","????","UAE","Government",2025,12,"2025-12-01",500000,300,"09-2026",0,0.25,None),
            ("c33","????","UAE","Government",2025,12,"2025-12-01",300000,300,"09-2026",0,0.25,None),
            ("c38","Synergy 7","Israel","Enterprise",2026,2,"2026-02-01",3000,60,"04-2026",0,1.0,None),
            ("c39","Gabon","Gabon","Government",2026,3,"2026-03-01",450000,120,"06-2026",0,0.5,None),
            ("c40","KSV/023","Kosovo","Government",2026,1,"2026-01-01",60000,60,"03-2026",0,1.0,None),
            ("c41","Alliance Bank","Malaysia","Enterprise",2026,1,"2026-01-01",42000,60,"03-2026",0,0.5,None),
            ("c42","Migdal","Israel","Enterprise",2026,1,"2026-01-01",20322.58,45,"02-2026",0,1.0,None),
            ("c44","Univ. of Botswana","Botswana","Academy",2026,1,"2026-01-01",100000,270,"09-2026",0,0.25,None),
            ("c45","CSIRT","Rwanda","Government",2026,1,"2026-01-01",200000,270,"09-2026",0,0.25,None),
            ("c46","NFSU","India","Academy",2026,2,"2026-02-01",90000,240,"09-2026",0,0.5,None),
            ("c47","Black Wall Global","Japan","Enterprise",2026,1,"2026-01-01",8200,60,"03-2026",0,1.0,None),
            ("c48","Ivory Coast","Ivory Coast","Government",2026,1,"2026-01-01",80000,60,"03-2026",0,0.75,None),
        ]
        db.executemany("INSERT OR IGNORE INTO contracts (id,client,country,industry,yr,sm,sd,val,dso,pm,monthly,chance,ap) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)", cons)

        # Expenses with carry-forward
        exps = [
            ("x01","R&D","Tera Sky","Cloud Services",1, carry_forward({"01-2026":2866.24,"02-2026":2500})),
            ("x02","G&A","Atidim","Office Rent",0, carry_forward({"01-2026":7006.37,"02-2026":6875})),
            ("x03","G&A","Tel Aviv","Municipal Taxes",0, carry_forward({"01-2026":1433.12,"02-2026":1406.25})),
            ("x04","G&A","Ilan","Accounting",0, carry_forward({"01-2026":1114.65,"02-2026":1093.75})),
            ("x05","G&A","Herzog","Legal",0, carry_forward({"01-2026":1592.36,"02-2026":1562.50})),
            ("x06","G&A","Misc.","Office Supplies",0, {m:300 for m in ML}),
            ("x07","R&D","Cellcom","Internet",1, carry_forward({"01-2026":254.78,"02-2026":257.99})),
            ("x08","G&A","Misc.","General & Admin",0, {m:300 for m in ML}),
            ("x09","G&A","Registrar","Tolls & Fees",0, carry_forward({"01-2026":445.86})),
            ("x10","Training","Misc.","Training",1, {m:20000 for m in ML}),
            ("x11","G&A","Misc.","Professional",0, {m:10000 for m in ML}),
            ("x12","R&D","Nir","Content Writing",1, carry_forward({"01-2026":11146.50,"02-2026":11286.86})),
            ("x13","G&A","Altshare","ESOP",0, carry_forward({"01-2026":1273.89})),
            ("x14","G&A","Misc.","Refreshments",0, {m:100 for m in ML}),
            ("x15","G&A","Misc.","Phone & Post",0, carry_forward({"01-2026":31.85,"02-2026":32.25})),
            ("x16","S&M","Misc.","Advertising",0, {m:1500 for m in ML}),
            ("x17","G&A","Misc.","Bank Fees",0, {m:800 for m in ML}),
            ("x18","R&D","Tzahi","Content Writing",1, carry_forward({"02-2026":5643.43})),
        ]
        for eid, dept, vendor, sub, cogs, amounts in exps:
            db.execute(
                "INSERT OR IGNORE INTO expenses (id,dept,vendor,sub_cat,is_cogs,amounts) VALUES (?,?,?,?,?,?)",
                (eid, dept, vendor, sub, cogs, json.dumps(amounts))
            )

# ══════════════════════════════════════════
# DATA ACCESS — Read from DB into dicts
# ══════════════════════════════════════════
def load_employees(include_ghosts=False):
    with get_db() as db:
        rows = db.execute("SELECT * FROM employees" + ("" if include_ghosts else " WHERE is_ghost=0")).fetchall()
        return [dict(r) for r in rows]

def load_contracts():
    with get_db() as db:
        return [dict(r) for r in db.execute("SELECT * FROM contracts").fetchall()]

def load_expenses():
    with get_db() as db:
        rows = db.execute("SELECT * FROM expenses").fetchall()
        result = []
        for r in rows:
            d = dict(r)
            d["amounts"] = json.loads(d["amounts"])
            result.append(d)
        return result

# ══════════════════════════════════════════
# FINANCIAL ENGINE (unchanged formulas)
# ══════════════════════════════════════════
def parse_pm(pm):
    try:
        p = pm.split("-")
        return int(p[0]) - 1 if int(p[1]) == FY and 1 <= int(p[0]) <= 12 else None
    except:
        return None

def shift_pm(pm, days):
    if not days: return pm
    try:
        p = pm.split("-")
        d = date(int(p[1]), int(p[0]), 15) + timedelta(days=days)
        return f"{d.month:02d}-{d.year}"
    except:
        return pm

def compute(delay=0, ghosts=0, gs=15000, w=True):
    employees = load_employees()
    contracts = load_contracts()
    expenses = load_expenses()

    # Add ghost employees (not persisted)
    for i in range(ghosts):
        employees.append({"id":f"g{i}","name":f"Ghost {i+1}","dept":"R&D",
                          "gross":gs,"hire_date":"2026-01-01","term_date":None,"is_ghost":1})

    data = []
    for mi, ml in enumerate(ML):
        p = ml.split("-")
        md = date(int(p[1]), int(p[0]), 1)
        lab = {"R&D": 0, "S&M": 0, "G&A": 0, "Training": 0}
        for e in employees:
            h = date.fromisoformat(e["hire_date"])
            t = date.fromisoformat(e["term_date"]) if e["term_date"] else None
            if md >= h and (not t or md <= t):
                lab[e["dept"]] += e["gross"] * ECF
        vd = {"R&D": 0, "S&M": 0, "G&A": 0, "Training": 0}
        vc = vo = 0
        for x in expenses:
            a = x["amounts"].get(ml, 0)
            vd[x["dept"]] += a
            if x["is_cogs"]: vc += a
            else: vo += a
        cogs = lab["R&D"] + vc
        opex = (sum(lab.values()) - lab["R&D"]) + vo
        data.append({"month": ml[:2],
            "lab": {k: round(v, 2) for k, v in lab.items()},
            "vd": {k: round(v, 2) for k, v in vd.items()},
            "cogs": round(cogs, 2), "opex": round(opex, 2),
            "totalExp": round(cogs + opex, 2), "revenue": 0.0, "cashIn": 0.0})

    for c in contracts:
        v = c["val"]
        if w:
            v = v * c["chance"] if c["chance"] is not None else 0
        sd = date.fromisoformat(c["sd"])
        if c["monthly"]:
            si = max(0, c["sm"] - 1 if sd.year == FY else 0)
            rem = 12 - si
            if rem <= 0: continue
            for i in range(si, 12):
                data[i]["revenue"] += v / rem
        else:
            if sd.year == FY:
                idx = c["sm"] - 1
                if 0 <= idx < 12:
                    data[idx]["revenue"] += v
            elif sd.year < FY:
                data[0]["revenue"] += v

    for c in contracts:
        if c["ap"] and c["ap"] > 0:
            idx = parse_pm(shift_pm(c["pm"], delay))
            if idx is not None:
                data[idx]["cashIn"] += c["ap"]
            continue
        v = c["val"]
        if w:
            v = v * c["chance"] if c["chance"] is not None else 0
        sd = date.fromisoformat(c["sd"])
        if c["monthly"]:
            si = max(0, c["sm"] - 1 if sd.year == FY else 0)
            rem = 12 - si
            if rem <= 0: continue
            for i in range(si, 12):
                pd = date(FY, i + 1, 15) + timedelta(days=c["dso"] + delay)
                if pd.year == FY:
                    data[pd.month - 1]["cashIn"] += v / rem
        else:
            idx = parse_pm(shift_pm(c["pm"], delay))
            if idx is not None:
                data[idx]["cashIn"] += v

    cum = 0
    for d in data:
        d["revenue"] = round(d["revenue"], 2)
        d["cashIn"] = round(d["cashIn"], 2)
        d["grossProfit"] = round(d["revenue"] - d["cogs"], 2)
        d["grossMargin"] = round(d["grossProfit"] / d["revenue"] * 100, 1) if d["revenue"] > 0 else 0
        d["netIncome"] = round(d["revenue"] - d["totalExp"], 2)
        d["cashOut"] = d["totalExp"]
        d["netCashflow"] = round(d["cashIn"] - d["cashOut"], 2)
        cum += d["netCashflow"]
        d["cumCash"] = round(cum, 2)
        d["burnRate"] = round(d["cashOut"] - d["cashIn"], 2) if d["cashOut"] > d["cashIn"] else 0
        d["runway"] = round(cum / d["burnRate"], 1) if d["burnRate"] > 0 else None
    return data

# ══════════════════════════════════════════
# API: Read
# ══════════════════════════════════════════
@app.get("/api/data")
def get_data(weighted: bool = True, delay: int = 0, ghosts: int = 0, salary: float = 15000):
    s = compute(delay, ghosts, salary, weighted)
    contracts = load_contracts()
    employees = load_employees()
    expenses = load_expenses()
    cs = [{"id": c["id"], "client": c["client"], "country": c["country"],
           "industry": c["industry"], "value": c["val"], "chance": c["chance"],
           "weighted": round(c["val"] * (c["chance"] or 0), 2),
           "dso": c["dso"], "pm": c["pm"], "monthly": bool(c["monthly"]),
           "signingDate": c["sd"]} for c in contracts]
    es = [{"id": e["id"], "name": e["name"], "dept": e["dept"],
           "gross": e["gross"], "laborCost": round(e["gross"] * ECF, 2),
           "hireDate": e["hire_date"],
           "termDate": e["term_date"]} for e in employees]
    xs = [{"id": x["id"], "dept": x["dept"], "vendor": x["vendor"],
           "subCat": x["sub_cat"], "isCogs": bool(x["is_cogs"]),
           "amount": round(sum(x["amounts"].values()) / max(len(x["amounts"]), 1), 2)}
          for x in expenses]
    return {"summary": s, "contracts": cs, "employees": es, "expenses": xs}

@app.get("/api/sales-analytics")
def sales_analytics(weighted: bool = True):
    """Revenue breakdown by customer type and country, responding to weighted toggle."""
    contracts = load_contracts()
    by_type = {}
    by_country = {}
    total = 0
    for c in contracts:
        v = c["val"]
        if weighted:
            v = v * c["chance"] if c["chance"] is not None else 0
        ind = c["industry"] or "Other"
        co = c["country"] or "Unknown"
        if ind not in by_type:
            by_type[ind] = {"total": 0, "count": 0, "deals": []}
        by_type[ind]["total"] += v
        by_type[ind]["count"] += 1
        by_type[ind]["deals"].append({"client": c["client"], "value": round(v, 2)})
        if co not in by_country:
            by_country[co] = {"total": 0, "count": 0}
        by_country[co]["total"] += v
        by_country[co]["count"] += 1
        total += v
    # Round and compute percentages
    for k in by_type:
        by_type[k]["total"] = round(by_type[k]["total"], 2)
        by_type[k]["pct"] = round(by_type[k]["total"] / total * 100, 1) if total > 0 else 0
    for k in by_country:
        by_country[k]["total"] = round(by_country[k]["total"], 2)
        by_country[k]["pct"] = round(by_country[k]["total"] / total * 100, 1) if total > 0 else 0
    # Top performers
    top_type = max(by_type.items(), key=lambda x: x[1]["total"])[0] if by_type else None
    top_country = max(by_country.items(), key=lambda x: x[1]["total"])[0] if by_country else None
    top_countries = sorted(by_country.items(), key=lambda x: -x[1]["total"])[:10]
    return {
        "total": round(total, 2),
        "byType": by_type,
        "byCountry": {k: v for k, v in top_countries},
        "topType": top_type,
        "topCountry": top_country,
        "dealCount": len(contracts),
        "weighted": weighted
    }

# ══════════════════════════════════════════
# API: Create
# ══════════════════════════════════════════
class ContractIn(BaseModel):
    client: str; country: str = ""; industry: str = "Enterprise"
    value: float; signingDate: str; dso: int = 60
    monthly: bool = False; chance: Optional[float] = None

class EmployeeIn(BaseModel):
    name: str; department: str = "R&D"; gross: float
    hireDate: str; termDate: Optional[str] = None

class ExpenseIn(BaseModel):
    vendor: str; department: str = "G&A"; subCategory: str = ""
    monthlyAmount: float = 0; isCogs: bool = False

@app.post("/api/contracts")
def add_contract(b: ContractIn):
    cid = str(uuid4())[:8]
    sd = date.fromisoformat(b.signingDate)
    pd = sd + timedelta(days=b.dso)
    pm = f"{pd.month:02d}-{pd.year}"
    with get_db() as db:
        db.execute(
            "INSERT INTO contracts (id,client,country,industry,yr,sm,sd,val,dso,pm,monthly,chance) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
            (cid, b.client, b.country, b.industry, sd.year, sd.month,
             b.signingDate, b.value, b.dso, pm, int(b.monthly), b.chance))
    return {"ok": True, "id": cid, "paymentMonth": pm}

@app.post("/api/employees")
def add_employee(b: EmployeeIn):
    eid = str(uuid4())[:8]
    with get_db() as db:
        db.execute(
            "INSERT INTO employees (id,name,dept,gross,hire_date,term_date) VALUES (?,?,?,?,?,?)",
            (eid, b.name, b.department, b.gross, b.hireDate, b.termDate))
    return {"ok": True, "id": eid, "laborCost": round(b.gross * ECF, 2)}

@app.post("/api/expenses")
def add_expense(b: ExpenseIn):
    xid = str(uuid4())[:8]
    amounts = json.dumps({m: b.monthlyAmount for m in ML})
    with get_db() as db:
        db.execute(
            "INSERT INTO expenses (id,dept,vendor,sub_cat,is_cogs,amounts) VALUES (?,?,?,?,?,?)",
            (xid, b.department, b.vendor, b.subCategory, int(b.isCogs), amounts))
    return {"ok": True, "id": xid}

# ══════════════════════════════════════════
# API: Delete
# ══════════════════════════════════════════
@app.delete("/api/contracts/{cid}")
def del_contract(cid: str):
    with get_db() as db:
        db.execute("DELETE FROM contracts WHERE id=?", (cid,))
    return {"ok": True}

@app.delete("/api/employees/{eid}")
def del_employee(eid: str):
    with get_db() as db:
        db.execute("DELETE FROM employees WHERE id=?", (eid,))
    return {"ok": True}

@app.delete("/api/expenses/{xid}")
def del_expense(xid: str):
    with get_db() as db:
        db.execute("DELETE FROM expenses WHERE id=?", (xid,))
    return {"ok": True}

# ══════════════════════════════════════════
# API: Update
# ══════════════════════════════════════════
class ContractUpdate(BaseModel):
    client: Optional[str] = None; country: Optional[str] = None
    industry: Optional[str] = None; value: Optional[float] = None
    dso: Optional[int] = None; chance: Optional[float] = None
    monthly: Optional[bool] = None

@app.put("/api/contracts/{cid}")
def upd_contract(cid: str, b: ContractUpdate):
    fields = []
    vals = []
    if b.client is not None: fields.append("client=?"); vals.append(b.client)
    if b.country is not None: fields.append("country=?"); vals.append(b.country)
    if b.industry is not None: fields.append("industry=?"); vals.append(b.industry)
    if b.value is not None: fields.append("val=?"); vals.append(b.value)
    if b.dso is not None: fields.append("dso=?"); vals.append(b.dso)
    if b.chance is not None: fields.append("chance=?"); vals.append(b.chance)
    if b.monthly is not None: fields.append("monthly=?"); vals.append(int(b.monthly))
    if not fields: return {"ok": True, "id": cid}
    vals.append(cid)
    with get_db() as db:
        db.execute(f"UPDATE contracts SET {','.join(fields)} WHERE id=?", vals)
        # Recalculate payment month if DSO changed
        if b.dso is not None:
            row = db.execute("SELECT sd, dso FROM contracts WHERE id=?", (cid,)).fetchone()
            if row:
                sd = date.fromisoformat(row["sd"])
                pd = sd + timedelta(days=row["dso"])
                pm = f"{pd.month:02d}-{pd.year}"
                db.execute("UPDATE contracts SET pm=? WHERE id=?", (pm, cid))
    return {"ok": True, "id": cid}

class EmployeeUpdate(BaseModel):
    name: Optional[str] = None; department: Optional[str] = None
    gross: Optional[float] = None; termDate: Optional[str] = None

@app.put("/api/employees/{eid}")
def upd_employee(eid: str, b: EmployeeUpdate):
    fields = []
    vals = []
    if b.name is not None: fields.append("name=?"); vals.append(b.name)
    if b.department is not None: fields.append("dept=?"); vals.append(b.department)
    if b.gross is not None: fields.append("gross=?"); vals.append(b.gross)
    if b.termDate is not None: fields.append("term_date=?"); vals.append(b.termDate if b.termDate else None)
    if not fields: return {"ok": True, "id": eid}
    vals.append(eid)
    with get_db() as db:
        db.execute(f"UPDATE employees SET {','.join(fields)} WHERE id=?", vals)
    lc = b.gross * ECF if b.gross else 0
    return {"ok": True, "id": eid, "laborCost": round(lc, 2)}

class ExpenseUpdate(BaseModel):
    vendor: Optional[str] = None; department: Optional[str] = None
    subCategory: Optional[str] = None; monthlyAmount: Optional[float] = None
    isCogs: Optional[bool] = None

@app.put("/api/expenses/{xid}")
def upd_expense(xid: str, b: ExpenseUpdate):
    fields = []
    vals = []
    if b.vendor is not None: fields.append("vendor=?"); vals.append(b.vendor)
    if b.department is not None: fields.append("dept=?"); vals.append(b.department)
    if b.subCategory is not None: fields.append("sub_cat=?"); vals.append(b.subCategory)
    if b.isCogs is not None: fields.append("is_cogs=?"); vals.append(int(b.isCogs))
    if b.monthlyAmount is not None:
        amounts = json.dumps({m: b.monthlyAmount for m in ML})
        fields.append("amounts=?")
        vals.append(amounts)
    if not fields: return {"ok": True, "id": xid}
    vals.append(xid)
    with get_db() as db:
        db.execute(f"UPDATE expenses SET {','.join(fields)} WHERE id=?", vals)
    return {"ok": True, "id": xid}

# ══════════════════════════════════════════
# Serve HTML
# ══════════════════════════════════════════
@app.get("/", response_class=HTMLResponse)
def serve():
    html_path = Path(__file__).parent / "index.html"
    return html_path.read_text(encoding="utf-8")

# ══════════════════════════════════════════
# Startup
# ══════════════════════════════════════════
@app.on_event("startup")
def startup():
    init_db()
    if not is_seeded():
        print("  \U0001f331 First run — seeding database with Excel data...")
        seed_db()
        print(f"  \u2705 Seeded: {len(load_employees())} employees, {len(load_contracts())} contracts, {len(load_expenses())} expenses")
    else:
        print(f"  \U0001f4be Database loaded: {len(load_employees())} employees, {len(load_contracts())} contracts, {len(load_expenses())} expenses")

if __name__ == "__main__":
    import uvicorn
    print("\n  \u26a1 FinStack CFO Command Center v5 (SQLite)")
    print("  " + "\u2500" * 40)
    print("  Dashboard:  http://localhost:8000")
    print("  API docs:   http://localhost:8000/docs")
    print("  Database:   " + str(DB_PATH) + "\n")
    uvicorn.run(app, host="127.0.0.1", port=8000)
