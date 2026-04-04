"""
FinStack CFO v6 — Auth + CRM + Sales Pipeline
================================================
INSTALL:  py -m pip install fastapi uvicorn pyjwt
RUN:      py app.py
"""
from __future__ import annotations
import sqlite3, json, os, time, hashlib, secrets
from contextlib import contextmanager
from datetime import date, timedelta, datetime
from pathlib import Path
from typing import Optional
from uuid import uuid4

import jwt
from fastapi import FastAPI, Query, Header, HTTPException, Depends
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# Simple password hashing (no bcrypt dependency needed)
def hash_pw(password: str) -> str:
    salt = secrets.token_hex(16)
    h = hashlib.sha256((salt + password).encode()).hexdigest()
    return salt + ":" + h

def verify_pw(password: str, stored: str) -> bool:
    if ":" not in stored: return False
    salt, h = stored.split(":", 1)
    return hashlib.sha256((salt + password).encode()).hexdigest() == h

app = FastAPI(title="FinStack CFO API", version="6.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

ECF = 1.35; FY = 2026
ML = [f"{m:02d}-{FY}" for m in range(1, 13)]
JWT_SECRET = os.environ.get("JWT_SECRET", "finstack-secret-key-change-in-production")
STAGES = ["Initial Contact", "Email Sent", "Demo", "Negotiation", "Signed"]
DB_PATH = Path(__file__).parent / "finstack.db"

# ══════════════════════════════════════════
# DATABASE
# ══════════════════════════════════════════
@contextmanager
def get_db():
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    try: yield conn; conn.commit()
    finally: conn.close()

def init_db():
    with get_db() as db:
        db.executescript("""
        CREATE TABLE IF NOT EXISTS users (
            id TEXT PRIMARY KEY, username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL, role TEXT NOT NULL DEFAULT 'sales',
            display_name TEXT, dept TEXT DEFAULT 'S&M',
            can_see_all INTEGER DEFAULT 0
        );
        CREATE TABLE IF NOT EXISTS app_settings (
            key TEXT PRIMARY KEY, value TEXT
        );
        CREATE TABLE IF NOT EXISTS monthly_rates (
            month TEXT PRIMARY KEY, rate REAL NOT NULL, locked INTEGER DEFAULT 0
        );
        CREATE TABLE IF NOT EXISTS employees (
            id TEXT PRIMARY KEY, name TEXT NOT NULL, dept TEXT NOT NULL,
            gross REAL NOT NULL, position_pct REAL DEFAULT 100,
            bonus REAL DEFAULT 0, currency TEXT DEFAULT 'ILS',
            hire_date TEXT NOT NULL, term_date TEXT, is_ghost INTEGER DEFAULT 0
        );
        CREATE TABLE IF NOT EXISTS contracts (
            id TEXT PRIMARY KEY, client TEXT NOT NULL, country TEXT DEFAULT '',
            industry TEXT DEFAULT 'Enterprise', yr INTEGER, sm INTEGER, sd TEXT,
            val REAL NOT NULL, dso INTEGER DEFAULT 60, pm TEXT,
            monthly INTEGER DEFAULT 0, chance REAL, ap REAL,
            currency TEXT DEFAULT 'USD',
            stage TEXT DEFAULT 'Initial Contact', stage_updated_at TEXT,
            salesperson_id TEXT, notes TEXT DEFAULT '[]',
            contact_name TEXT DEFAULT '', contact_phone TEXT DEFAULT '',
            contact_email TEXT DEFAULT '', contact_linkedin TEXT DEFAULT '',
            payment_splits TEXT DEFAULT '[]',
            created_at TEXT, updated_at TEXT,
            FOREIGN KEY (salesperson_id) REFERENCES users(id)
        );
        CREATE TABLE IF NOT EXISTS expenses (
            id TEXT PRIMARY KEY, dept TEXT NOT NULL, vendor TEXT NOT NULL,
            sub_cat TEXT DEFAULT '', is_cogs INTEGER DEFAULT 0, amounts TEXT DEFAULT '{}',
            currency TEXT DEFAULT 'ILS',
            vendor_contact TEXT DEFAULT '', vendor_email TEXT DEFAULT '',
            vendor_phone TEXT DEFAULT '', service_desc TEXT DEFAULT '',
            frequency TEXT DEFAULT 'monthly'
        );
        CREATE TABLE IF NOT EXISTS audit_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT, entity_type TEXT, entity_id TEXT,
            field TEXT, old_value TEXT, new_value TEXT, changed_by TEXT, changed_at TEXT
        );
        """)

def carry_forward(known):
    result = {}; last = 0.0
    for m in ML:
        if m in known and known[m] is not None: last = known[m]
        result[m] = last
    return result

def get_exchange_rate():
    """Get current USD/ILS rate. Try live API, fallback to stored."""
    # Try stored rate first
    with get_db() as db:
        r = db.execute("SELECT value FROM app_settings WHERE key='usd_ils_rate'").fetchone()
        stored = float(r["value"]) if r else 3.12
    # Try to fetch live rate (cache for 1 hour)
    with get_db() as db:
        cache = db.execute("SELECT value FROM app_settings WHERE key='rate_cache_time'").fetchone()
        cache_time = float(cache["value"]) if cache else 0
    import time as _time
    if _time.time() - cache_time < 3600:  # Use cache if less than 1 hour old
        return stored
    try:
        import urllib.request
        req = urllib.request.Request("https://api.frankfurter.app/latest?from=USD&to=ILS",
                                     headers={"User-Agent":"FinStack/1.0"})
        with urllib.request.urlopen(req, timeout=5) as resp:
            data = json.loads(resp.read().decode())
            rate = data["rates"]["ILS"]
            with get_db() as db:
                db.execute("INSERT OR REPLACE INTO app_settings VALUES ('usd_ils_rate',?)", (str(rate),))
                db.execute("INSERT OR REPLACE INTO app_settings VALUES ('rate_cache_time',?)", (str(_time.time()),))
            return rate
    except:
        return stored

def set_exchange_rate(rate):
    import time as _time
    with get_db() as db:
        db.execute("INSERT OR REPLACE INTO app_settings (key,value) VALUES ('usd_ils_rate',?)", (str(rate),))
        db.execute("INSERT OR REPLACE INTO app_settings (key,value) VALUES ('rate_cache_time',?)", (str(_time.time()),))

def get_rate_for_month(month_str):
    """Locked months use stored rate. Current/future use live."""
    with get_db() as db:
        r = db.execute("SELECT rate, locked FROM monthly_rates WHERE month=?", (month_str,)).fetchone()
        if r and r["locked"]:
            return r["rate"]
    return get_exchange_rate()

def lock_past_months():
    """Lock rates for past months on startup."""
    now = datetime.now()
    current_month = f"{now.month:02d}-{now.year}"
    rate = get_exchange_rate()
    with get_db() as db:
        for m in ML:
            if m < current_month:
                existing = db.execute("SELECT locked FROM monthly_rates WHERE month=?", (m,)).fetchone()
                if not existing:
                    db.execute("INSERT INTO monthly_rates (month, rate, locked) VALUES (?,?,1)", (m, rate))
                elif not existing["locked"]:
                    db.execute("UPDATE monthly_rates SET locked=1 WHERE month=?", (m,))

def to_usd(amount, currency, month_str=None):
    if currency == 'USD' or not currency: return amount
    if currency == 'ILS':
        rate = get_rate_for_month(month_str) if month_str else get_exchange_rate()
        return amount / rate
    return amount

def is_seeded():
    with get_db() as db: return db.execute("SELECT COUNT(*) c FROM employees").fetchone()["c"] > 0

def seed_db():
    with get_db() as db:
        # Exchange rate default
        db.execute("INSERT OR IGNORE INTO app_settings VALUES ('usd_ils_rate','3.12')")
        # Users
        admin_hash = hash_pw("admin123")
        sales_hash = hash_pw("sales123")
        db.execute("INSERT OR IGNORE INTO users VALUES (?,?,?,?,?,?,?)", ("u-admin","admin",admin_hash,"admin","Admin Manager","G&A",1))
        db.execute("INSERT OR IGNORE INTO users VALUES (?,?,?,?,?,?,?)", ("u-eduardo","eduardo",sales_hash,"sales_manager","Eduardo Borotchin","S&M",1))
        db.execute("INSERT OR IGNORE INTO users VALUES (?,?,?,?,?,?,?)", ("u-elad","elad",sales_hash,"sales","Elad Lev","S&M",0))
        db.execute("INSERT OR IGNORE INTO users VALUES (?,?,?,?,?,?,?)", ("u-tiki","tiki",sales_hash,"sales","Tiki Tavero","S&M",0))

        # Employees
        emps = [
            ("e01","Etti Berger","G&A",16487.46,100,0,"2024-01-01",None),
            ("e02","Shai Grumet","R&D",11314.92,100,0,"2024-01-01",None),
            ("e03","Arye Laskin","R&D",9051.94,100,0,"2024-01-01",None),
            ("e04","Oren Chappo","R&D",11961.49,100,0,"2024-01-01",None),
            ("e05","Eduardo Borotchin","S&M",10345.07,100,0,"2024-01-01",None),
            ("e06","Nitai Driel","R&D",387.94,25,0,"2024-01-01",None),
            ("e07","Elad Lev","S&M",8082.09,100,0,"2024-01-01",None),
            ("e08","Tiki Tavero","S&M",6465.67,100,0,"2024-01-01",None),
            ("e09","Meirav Zetz","G&A",2020.52,50,0,"2024-01-01",None),
            ("e10","Yaniv Barkai","R&D",19431.60,100,0,"2024-01-01","2026-01-31"),
            ("e11","Elad Sheskin","R&D",0,0,0,"2024-01-01","2025-12-31"),
        ]
        db.executemany("INSERT OR IGNORE INTO employees (id,name,dept,gross,position_pct,bonus,hire_date,term_date) VALUES (?,?,?,?,?,?,?,?)", emps)

        now = datetime.now().isoformat()
        cons = [
            ("c01","Ministry of Defence","Indonesia","Government",2026,1,"2026-01-01",800000,60,"03-2026",0,0.75,None,"Demo",now,"u-eduardo","[]",now,now),
            ("c02","Ministry of Defence","Indonesia","Government",2026,1,"2026-01-01",150000,120,"05-2026",0,0.75,None,"Email Sent",now,"u-eduardo","[]",now,now),
            ("c03","Serbia","Serbia","Government",2025,10,"2025-10-01",90000,240,"05-2026",0,0.5,None,"Negotiation",now,"u-elad","[]",now,now),
            ("c04","Practical Cyber Academy","Singapore","Academy",2026,2,"2026-02-01",155000,240,"09-2026",0,0.75,None,"Demo",now,"u-tiki","[]",now,now),
            ("c06","Elta","Israel","Enterprise",2025,10,"2025-10-01",5000,180,"03-2026",0,1.0,3483.87,"Signed",now,"u-elad","[]",now,now),
            ("c07","Elta","Israel","Enterprise",2025,10,"2025-10-01",900000,270,"06-2026",0,0.5,None,"Negotiation",now,"u-eduardo","[]",now,now),
            ("c11","Schools","Israel","Academy",2025,10,"2025-10-01",15000,120,"01-2026",0,1.0,11231.94,"Signed",now,"u-tiki","[]",now,now),
            ("c13","Improvate","Israel","Academy",2026,5,"2026-05-01",150000,60,"06-2026",1,1.0,12108.06,"Signed",now,"u-eduardo","[]",now,now),
            ("c16","Bank of Israel","Israel","Government",2026,1,"2026-01-01",15000,45,"02-2026",0,1.0,None,"Signed",now,"u-elad","[]",now,now),
            ("c18","DSA","Cyprus","Government",2025,10,"2025-10-01",56000,210,"04-2026",0,0.5,35404.52,"Demo",now,"u-tiki","[]",now,now),
            ("c23","MAG","Nigeria","Enterprise",2026,1,"2026-01-01",30000,45,"02-2026",0,1.0,22800,"Signed",now,"u-eduardo","[]",now,now),
            ("c25","Technion","Israel","Academy",2026,1,"2026-01-01",42000,270,"09-2026",1,1.0,3870.97,"Negotiation",now,"u-tiki","[]",now,now),
            ("c28","EU Funding","Greece","Government",2026,1,"2026-01-01",300000,270,"09-2026",0,0.25,None,"Initial Contact",now,"u-elad","[]",now,now),
            ("c31","Abu Dhabi","UAE","Government",2026,1,"2026-01-01",300000,270,"09-2026",0,0.75,None,"Demo",now,"u-eduardo","[]",now,now),
            ("c39","Gabon","Gabon","Government",2026,3,"2026-03-01",450000,120,"06-2026",0,0.5,None,"Email Sent",now,"u-tiki","[]",now,now),
            ("c40","KSV/023","Kosovo","Government",2026,1,"2026-01-01",60000,60,"03-2026",0,1.0,None,"Signed",now,"u-elad","[]",now,now),
            ("c42","Migdal","Israel","Enterprise",2026,1,"2026-01-01",20322.58,45,"02-2026",0,1.0,None,"Negotiation",now,"u-eduardo","[]",now,now),
            ("c48","Ivory Coast","Ivory Coast","Government",2026,1,"2026-01-01",80000,60,"03-2026",0,0.75,None,"Demo",now,"u-tiki","[]",now,now),
        ]
        for c in cons:
            db.execute("INSERT OR IGNORE INTO contracts (id,client,country,industry,yr,sm,sd,val,dso,pm,monthly,chance,ap,stage,stage_updated_at,salesperson_id,notes,created_at,updated_at) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)", c)

        exps = [
            ("x01","R&D","Tera Sky","Cloud",1,carry_forward({"01-2026":2866.24,"02-2026":2500})),
            ("x02","G&A","Atidim","Rent",0,carry_forward({"01-2026":7006.37,"02-2026":6875})),
            ("x06","G&A","Misc.","Supplies",0,{m:300 for m in ML}),
            ("x07","R&D","Cellcom","Internet",1,carry_forward({"01-2026":254.78,"02-2026":257.99})),
            ("x10","Training","Misc.","Training",1,{m:20000 for m in ML}),
            ("x11","G&A","Misc.","Professional",0,{m:10000 for m in ML}),
            ("x12","R&D","Nir","Content",1,carry_forward({"01-2026":11146.50,"02-2026":11286.86})),
            ("x16","S&M","Misc.","Advertising",0,{m:1500 for m in ML}),
            ("x17","G&A","Misc.","Bank Fees",0,{m:800 for m in ML}),
            ("x18","R&D","Tzahi","Content",1,carry_forward({"02-2026":5643.43})),
        ]
        for eid,dept,vendor,sub,cogs,amounts in exps:
            db.execute("INSERT OR IGNORE INTO expenses (id,dept,vendor,sub_cat,is_cogs,amounts) VALUES (?,?,?,?,?,?)",
                       (eid,dept,vendor,sub,cogs,json.dumps(amounts)))

# ══════════════════════════════════════════
# AUTH
# ══════════════════════════════════════════
class LoginReq(BaseModel):
    username: str; password: str

@app.post("/api/login")
def login(body: LoginReq):
    with get_db() as db:
        u = db.execute("SELECT * FROM users WHERE username=?", (body.username,)).fetchone()
    if not u or not verify_pw(body.password, u["password_hash"]):
        raise HTTPException(401, "Invalid credentials")
    token = jwt.encode({"sub": u["id"], "role": u["role"], "name": u["display_name"],
                        "canSeeAll": bool(u["can_see_all"]),
                        "exp": time.time() + 86400*7}, JWT_SECRET, algorithm="HS256")
    return {"token": token, "role": u["role"], "name": u["display_name"],
            "userId": u["id"], "canSeeAll": bool(u["can_see_all"])}

def get_current_user(authorization: str = Header(None)):
    if not authorization: raise HTTPException(401, "Not authenticated")
    token = authorization.replace("Bearer ", "")
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=["HS256"])
        return payload
    except: raise HTTPException(401, "Invalid token")

def require_admin(user=Depends(get_current_user)):
    if user["role"] != "admin": raise HTTPException(403, "Admin only")
    return user

def require_manager(user=Depends(get_current_user)):
    if user["role"] not in ("admin", "sales_manager"): raise HTTPException(403, "Manager only")
    return user

class VisibilityUpdate(BaseModel):
    userId: str
    canSeeAll: bool

@app.put("/api/users/visibility")
def set_visibility(b: VisibilityUpdate, user=Depends(require_manager)):
    with get_db() as db:
        db.execute("UPDATE users SET can_see_all=? WHERE id=?", (int(b.canSeeAll), b.userId))
    return {"ok": True}

@app.get("/api/team")
def get_team(user=Depends(get_current_user)):
    """Get sales team members with their visibility settings."""
    if user["role"] not in ("admin", "sales_manager"):
        raise HTTPException(403)
    with get_db() as db:
        rows = db.execute("SELECT id, display_name, username, role, can_see_all FROM users WHERE dept='S&M'").fetchall()
    return [dict(r) for r in rows]

# ══════════════════════════════════════════
# DATA ACCESS
# ══════════════════════════════════════════
def load_employees():
    with get_db() as db: return [dict(r) for r in db.execute("SELECT * FROM employees WHERE is_ghost=0").fetchall()]

def load_contracts():
    with get_db() as db:
        rows = db.execute("""SELECT c.*, u.display_name as salesperson_name
                             FROM contracts c LEFT JOIN users u ON c.salesperson_id=u.id""").fetchall()
        return [dict(r) for r in rows]

def load_expenses():
    with get_db() as db:
        rows = db.execute("SELECT * FROM expenses").fetchall()
        return [dict(r) | {"amounts": json.loads(dict(r)["amounts"])} for r in rows]

def load_salespeople():
    with get_db() as db:
        return [dict(r) for r in db.execute("SELECT id,display_name,username,role,can_see_all FROM users WHERE role IN ('sales','sales_manager') OR dept='S&M'").fetchall()]

def log_audit(entity_type, entity_id, field, old_val, new_val, user_id):
    with get_db() as db:
        db.execute("INSERT INTO audit_log (entity_type,entity_id,field,old_value,new_value,changed_by,changed_at) VALUES (?,?,?,?,?,?,?)",
                   (entity_type, entity_id, field, str(old_val), str(new_val), user_id, datetime.now().isoformat()))

# ══════════════════════════════════════════
# FINANCIAL ENGINE (unchanged)
# ══════════════════════════════════════════
def parse_pm(pm):
    try: p=pm.split("-"); return int(p[0])-1 if int(p[1])==FY and 1<=int(p[0])<=12 else None
    except: return None

def shift_pm(pm, days):
    if not days: return pm
    try: p=pm.split("-"); d=date(int(p[1]),int(p[0]),15)+timedelta(days=days); return f"{d.month:02d}-{d.year}"
    except: return pm

def compute(delay=0, ghosts=0, gs=15000, w=True):
    employees=load_employees(); contracts=load_contracts(); expenses=load_expenses()
    for i in range(ghosts):
        employees.append({"id":f"g{i}","name":f"Ghost {i+1}","dept":"R&D","gross":gs,"hire_date":"2026-01-01","term_date":None})
    data=[]
    for mi,ml in enumerate(ML):
        p=ml.split("-"); md=date(int(p[1]),int(p[0]),1)
        lab={"R&D":0,"S&M":0,"G&A":0,"Training":0}
        for e in employees:
            h=date.fromisoformat(e["hire_date"]); t=date.fromisoformat(e["term_date"]) if e["term_date"] else None
            if md>=h and (not t or md<=t):
                pct=e.get("position_pct",100)/100.0
                bonus=e.get("bonus",0)
                raw=(e["gross"]+bonus)*ECF*pct
                lab[e["dept"]]+=to_usd(raw, e.get("currency","ILS"), ml)
        vd={"R&D":0,"S&M":0,"G&A":0,"Training":0}; vc=vo=0
        for x in expenses:
            a=to_usd(x["amounts"].get(ml,0), x.get("currency","ILS"), ml)
            vd[x["dept"]]+=a
            if x["is_cogs"]: vc+=a
            else: vo+=a
        cogs=lab["R&D"]+vc; opex=(sum(lab.values())-lab["R&D"])+vo
        data.append({"month":ml[:2],"lab":{k:round(v,2) for k,v in lab.items()},"vd":{k:round(v,2) for k,v in vd.items()},"cogs":round(cogs,2),"opex":round(opex,2),"totalExp":round(cogs+opex,2),"revenue":0.0,"cashIn":0.0})
    for c in contracts:
        v=to_usd(c["val"], c.get("currency","USD"))
        if w: v=v*c["chance"] if c["chance"] is not None else 0
        sd=date.fromisoformat(c["sd"])
        if c["monthly"]:
            si=max(0,c["sm"]-1 if sd.year==FY else 0); rem=12-si
            if rem<=0: continue
            for i in range(si,12): data[i]["revenue"]+=v/rem
        else:
            if sd.year==FY:
                idx=c["sm"]-1
                if 0<=idx<12: data[idx]["revenue"]+=v
            elif sd.year<FY: data[0]["revenue"]+=v
    for c in contracts:
        cur=c.get("currency","USD")
        # Payment splits take priority
        splits = json.loads(c.get("payment_splits","[]")) if c.get("payment_splits") else []
        if splits:
            for sp in splits:
                try:
                    sd2=date.fromisoformat(sp["date"])
                    if sd2.year==FY:
                        amt=to_usd(sp["amount"], cur)
                        if w and c["chance"] is not None: amt=amt*c["chance"]
                        elif w and c["chance"] is None: amt=0
                        data[sd2.month-1]["cashIn"]+=amt
                except: pass
            continue
        if c["ap"] and c["ap"]>0:
            idx=parse_pm(shift_pm(c["pm"],delay))
            if idx is not None: data[idx]["cashIn"]+=to_usd(c["ap"],cur); continue
        v=to_usd(c["val"], cur)
        if w: v=v*c["chance"] if c["chance"] is not None else 0
        sd=date.fromisoformat(c["sd"])
        if c["monthly"]:
            si=max(0,c["sm"]-1 if sd.year==FY else 0); rem=12-si
            if rem<=0: continue
            for i in range(si,12):
                pd=date(FY,i+1,15)+timedelta(days=c["dso"]+delay)
                if pd.year==FY: data[pd.month-1]["cashIn"]+=v/rem
        else:
            idx=parse_pm(shift_pm(c["pm"],delay))
            if idx is not None: data[idx]["cashIn"]+=v
    cum=0
    for d in data:
        d["revenue"]=round(d["revenue"],2); d["cashIn"]=round(d["cashIn"],2)
        d["grossProfit"]=round(d["revenue"]-d["cogs"],2)
        d["grossMargin"]=round(d["grossProfit"]/d["revenue"]*100,1) if d["revenue"]>0 else 0
        d["netIncome"]=round(d["revenue"]-d["totalExp"],2)
        d["cashOut"]=d["totalExp"]; d["netCashflow"]=round(d["cashIn"]-d["cashOut"],2)
        cum+=d["netCashflow"]; d["cumCash"]=round(cum,2)
        d["burnRate"]=round(d["cashOut"]-d["cashIn"],2) if d["cashOut"]>d["cashIn"] else 0
        d["runway"]=round(cum/d["burnRate"],1) if d["burnRate"]>0 else None
    return data

# ══════════════════════════════════════════
# API: Data
# ══════════════════════════════════════════
@app.get("/api/data")
def get_data(weighted:bool=True, delay:int=0, ghosts:int=0, salary:float=15000):
    s=compute(delay,ghosts,salary,weighted)
    contracts=load_contracts(); employees=load_employees(); expenses=load_expenses()
    cs=[{"id":c["id"],"client":c["client"],"country":c["country"],"industry":c["industry"],
         "value":c["val"],"chance":c["chance"],"weighted":round(c["val"]*(c["chance"] or 0),2),
         "dso":c["dso"],"pm":c["pm"],"monthly":bool(c["monthly"]),"signingDate":c["sd"],
         "currency":c.get("currency","USD"),
         "stage":c["stage"],"stageUpdatedAt":c["stage_updated_at"],
         "salespersonId":c["salesperson_id"],"salespersonName":c.get("salesperson_name",""),
         "notes":json.loads(c["notes"]) if c["notes"] else [],
         "contactName":c.get("contact_name",""),"contactPhone":c.get("contact_phone",""),
         "contactEmail":c.get("contact_email",""),"contactLinkedin":c.get("contact_linkedin",""),
         "paymentSplits":json.loads(c.get("payment_splits","[]")) if c.get("payment_splits") else [],
         "createdAt":c["created_at"],"updatedAt":c["updated_at"]} for c in contracts]
    es=[{"id":e["id"],"name":e["name"],"dept":e["dept"],"gross":e["gross"],
         "positionPct":e.get("position_pct",100),"bonus":e.get("bonus",0),
         "currency":e.get("currency","ILS"),
         "laborCost":round(to_usd((e["gross"]+e.get("bonus",0))*ECF*(e.get("position_pct",100)/100.0), e.get("currency","ILS")),2),
         "hireDate":e["hire_date"],"termDate":e["term_date"]} for e in employees]
    xs=[{"id":x["id"],"dept":x["dept"],"vendor":x["vendor"],"subCat":x["sub_cat"],
         "isCogs":bool(x["is_cogs"]),"currency":x.get("currency","ILS"),
         "amount":round(to_usd(sum(x["amounts"].values())/max(len(x["amounts"]),1), x.get("currency","ILS")),2),
         "amountOriginal":round(sum(x["amounts"].values())/max(len(x["amounts"]),1),2),
         "vendorContact":x.get("vendor_contact",""),"vendorEmail":x.get("vendor_email",""),
         "vendorPhone":x.get("vendor_phone",""),"serviceDesc":x.get("service_desc",""),
         "frequency":x.get("frequency","monthly")} for x in expenses]
    sp=load_salespeople()
    rate=get_exchange_rate()
    return {"summary":s,"contracts":cs,"employees":es,"expenses":xs,
            "salespeople":[{"id":p["id"],"name":p["display_name"]} for p in sp],
            "stages":STAGES,"exchangeRate":rate}

@app.get("/api/sales-analytics")
def sales_analytics(weighted:bool=True):
    contracts=load_contracts()
    by_type={}; by_country={}; total_signed=0; total_pipeline=0
    for c in contracts:
        v=c["val"]
        if weighted: v=v*c["chance"] if c["chance"] is not None else 0
        ind=c["industry"] or "Other"; co=c["country"] or "Unknown"
        is_signed = c["stage"] == "Signed"

        by_type.setdefault(ind,{"signed":0,"pipeline":0,"signedCount":0,"pipelineCount":0})
        by_country.setdefault(co,{"signed":0,"pipeline":0,"signedCount":0,"pipelineCount":0})

        if is_signed:
            by_type[ind]["signed"]+=v; by_type[ind]["signedCount"]+=1
            by_country[co]["signed"]+=v; by_country[co]["signedCount"]+=1
            total_signed+=v
        else:
            by_type[ind]["pipeline"]+=v; by_type[ind]["pipelineCount"]+=1
            by_country[co]["pipeline"]+=v; by_country[co]["pipelineCount"]+=1
            total_pipeline+=v

    total = total_signed + total_pipeline
    for k in by_type:
        d=by_type[k]; d["total"]=round(d["signed"]+d["pipeline"],2)
        d["signed"]=round(d["signed"],2); d["pipeline"]=round(d["pipeline"],2)
        d["pct"]=round(d["total"]/total*100,1) if total>0 else 0
        d["count"]=d["signedCount"]+d["pipelineCount"]
    for k in by_country:
        d=by_country[k]; d["total"]=round(d["signed"]+d["pipeline"],2)
        d["signed"]=round(d["signed"],2); d["pipeline"]=round(d["pipeline"],2)
        d["pct"]=round(d["total"]/total*100,1) if total>0 else 0
        d["count"]=d["signedCount"]+d["pipelineCount"]

    # Top = by signed only (real revenue)
    top_type=max(by_type,key=lambda k:by_type[k]["signed"]) if by_type else None
    top_country=max(by_country,key=lambda k:by_country[k]["signed"]) if by_country else None
    stages_dist={s:0 for s in STAGES}
    for c in contracts: stages_dist[c["stage"]]=stages_dist.get(c["stage"],0)+1
    return {
        "totalSigned":round(total_signed,2),"totalPipeline":round(total_pipeline,2),
        "total":round(total,2),
        "byType":by_type,
        "byCountry":dict(sorted(by_country.items(),key=lambda x:-x[1]["total"])[:10]),
        "topType":top_type,"topCountry":top_country,"dealCount":len(contracts),
        "weighted":weighted,"stageDistribution":stages_dist
    }

# ══════════════════════════════════════════
# API: CRUD (auth required for writes)
# ══════════════════════════════════════════
class ContractIn(BaseModel):
    client:str; country:str=""; industry:str="Enterprise"; value:float
    signingDate:str; dso:int=60; monthly:bool=False; chance:Optional[float]=None
    salespersonId:Optional[str]=None; currency:str="USD"
    contactName:str=""; contactPhone:str=""; contactEmail:str=""; contactLinkedin:str=""

@app.post("/api/contracts")
def add_contract(b:ContractIn, user=Depends(get_current_user)):
    cid=str(uuid4())[:8]; sd=date.fromisoformat(b.signingDate)
    pd=sd+timedelta(days=b.dso); pm=f"{pd.month:02d}-{pd.year}"
    now=datetime.now().isoformat()
    sp_id = b.salespersonId or (user["sub"] if user["role"] in ("sales","sales_manager") else None)
    with get_db() as db:
        db.execute("INSERT INTO contracts (id,client,country,industry,yr,sm,sd,val,dso,pm,monthly,chance,currency,stage,stage_updated_at,salesperson_id,notes,contact_name,contact_phone,contact_email,contact_linkedin,created_at,updated_at) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                   (cid,b.client,b.country,b.industry,sd.year,sd.month,b.signingDate,b.value,b.dso,pm,int(b.monthly),b.chance,b.currency,"Initial Contact",now,sp_id,"[]",b.contactName,b.contactPhone,b.contactEmail,b.contactLinkedin,now,now))
    return {"ok":True,"id":cid,"paymentMonth":pm}

class StageUpdate(BaseModel):
    stage: str

@app.put("/api/contracts/{cid}/stage")
def update_stage(cid:str, b:StageUpdate, user=Depends(get_current_user)):
    if b.stage not in STAGES: raise HTTPException(400, "Invalid stage")
    with get_db() as db:
        c = db.execute("SELECT stage, salesperson_id FROM contracts WHERE id=?", (cid,)).fetchone()
        if not c: raise HTTPException(404)
        # Sales can only edit their own
        if user["role"] == "sales" and c["salesperson_id"] != user["sub"]:
            raise HTTPException(403, "Can only edit your own deals")
        old_idx = STAGES.index(c["stage"]) if c["stage"] in STAGES else 0
        new_idx = STAGES.index(b.stage)
        if new_idx < old_idx: raise HTTPException(400, "Cannot move stage backwards")
        now = datetime.now().isoformat()
        log_audit("contract", cid, "stage", c["stage"], b.stage, user["sub"])
        db.execute("UPDATE contracts SET stage=?, stage_updated_at=?, updated_at=? WHERE id=?", (b.stage, now, now, cid))
    return {"ok": True}

class NoteIn(BaseModel):
    text: str

@app.post("/api/contracts/{cid}/notes")
def add_note(cid:str, b:NoteIn, user=Depends(get_current_user)):
    now = datetime.now().isoformat()
    with get_db() as db:
        c = db.execute("SELECT notes, salesperson_id FROM contracts WHERE id=?", (cid,)).fetchone()
        if not c: raise HTTPException(404)
        if user["role"] == "sales" and c["salesperson_id"] != user["sub"]:
            raise HTTPException(403, "Can only add notes to your own deals")
        notes = json.loads(c["notes"]) if c["notes"] else []
        notes.append({"text": b.text, "by": user.get("name", user["sub"]), "at": now})
        db.execute("UPDATE contracts SET notes=?, updated_at=? WHERE id=?", (json.dumps(notes), now, cid))
    return {"ok": True}

class SplitsUpdate(BaseModel):
    splits: list  # [{amount: float, date: "YYYY-MM-DD"}, ...]

@app.put("/api/contracts/{cid}/splits")
def update_splits(cid:str, b:SplitsUpdate, user=Depends(get_current_user)):
    now = datetime.now().isoformat()
    with get_db() as db:
        c = db.execute("SELECT salesperson_id FROM contracts WHERE id=?", (cid,)).fetchone()
        if not c: raise HTTPException(404)
        if user["role"] == "sales" and c["salesperson_id"] != user["sub"]:
            raise HTTPException(403)
        db.execute("UPDATE contracts SET payment_splits=?, updated_at=? WHERE id=?",
                   (json.dumps(b.splits), now, cid))
    return {"ok": True}

class ContractUpdate(BaseModel):
    client:Optional[str]=None; country:Optional[str]=None; industry:Optional[str]=None
    value:Optional[float]=None; dso:Optional[int]=None; chance:Optional[float]=None
    monthly:Optional[bool]=None; salespersonId:Optional[str]=None
    contactName:Optional[str]=None; contactPhone:Optional[str]=None
    contactEmail:Optional[str]=None; contactLinkedin:Optional[str]=None

@app.put("/api/contracts/{cid}")
def upd_contract(cid:str, b:ContractUpdate, user=Depends(get_current_user)):
    now = datetime.now().isoformat()
    fields=[]; vals=[]
    if b.client is not None: fields.append("client=?"); vals.append(b.client)
    if b.country is not None: fields.append("country=?"); vals.append(b.country)
    if b.industry is not None: fields.append("industry=?"); vals.append(b.industry)
    if b.value is not None: fields.append("val=?"); vals.append(b.value)
    if b.dso is not None: fields.append("dso=?"); vals.append(b.dso)
    if b.chance is not None: fields.append("chance=?"); vals.append(b.chance)
    if b.monthly is not None: fields.append("monthly=?"); vals.append(int(b.monthly))
    if b.salespersonId is not None: fields.append("salesperson_id=?"); vals.append(b.salespersonId)
    if b.contactName is not None: fields.append("contact_name=?"); vals.append(b.contactName)
    if b.contactPhone is not None: fields.append("contact_phone=?"); vals.append(b.contactPhone)
    if b.contactEmail is not None: fields.append("contact_email=?"); vals.append(b.contactEmail)
    if b.contactLinkedin is not None: fields.append("contact_linkedin=?"); vals.append(b.contactLinkedin)
    if not fields: return {"ok":True}
    fields.append("updated_at=?"); vals.append(now)
    vals.append(cid)
    with get_db() as db:
        # Sales can only edit own
        if user["role"] == "sales":
            c = db.execute("SELECT salesperson_id FROM contracts WHERE id=?", (cid,)).fetchone()
            if c and c["salesperson_id"] != user["sub"]: raise HTTPException(403)
        db.execute(f"UPDATE contracts SET {','.join(fields)} WHERE id=?", vals)
        if b.dso is not None:
            row = db.execute("SELECT sd,dso FROM contracts WHERE id=?", (cid,)).fetchone()
            if row:
                sd=date.fromisoformat(row["sd"]); pd=sd+timedelta(days=row["dso"])
                db.execute("UPDATE contracts SET pm=? WHERE id=?", (f"{pd.month:02d}-{pd.year}", cid))
    return {"ok":True}

@app.delete("/api/contracts/{cid}")
def del_contract(cid:str, user=Depends(require_admin)):
    with get_db() as db: db.execute("DELETE FROM contracts WHERE id=?", (cid,))
    return {"ok":True}

class EmployeeIn(BaseModel):
    name:str; department:str="R&D"; gross:float; hireDate:str; termDate:Optional[str]=None

@app.post("/api/employees")
def add_employee(b:EmployeeIn, user=Depends(require_admin)):
    eid=str(uuid4())[:8]
    with get_db() as db:
        db.execute("INSERT INTO employees (id,name,dept,gross,hire_date,term_date) VALUES (?,?,?,?,?,?)",
                   (eid,b.name,b.department,b.gross,b.hireDate,b.termDate))
    return {"ok":True,"id":eid,"laborCost":round(b.gross*ECF,2)}

class EmployeeUpdate(BaseModel):
    name:Optional[str]=None; department:Optional[str]=None
    gross:Optional[float]=None; positionPct:Optional[float]=None
    bonus:Optional[float]=None; currency:Optional[str]=None; termDate:Optional[str]=None

@app.put("/api/employees/{eid}")
def upd_employee(eid:str, b:EmployeeUpdate, user=Depends(require_admin)):
    fields=[]; vals=[]
    if b.name is not None: fields.append("name=?"); vals.append(b.name)
    if b.department is not None: fields.append("dept=?"); vals.append(b.department)
    if b.gross is not None: fields.append("gross=?"); vals.append(b.gross)
    if b.positionPct is not None: fields.append("position_pct=?"); vals.append(b.positionPct)
    if b.bonus is not None: fields.append("bonus=?"); vals.append(b.bonus)
    if b.currency is not None: fields.append("currency=?"); vals.append(b.currency)
    if b.termDate is not None: fields.append("term_date=?"); vals.append(b.termDate if b.termDate else None)
    if not fields: return {"ok":True}
    vals.append(eid)
    with get_db() as db:
        db.execute(f"UPDATE employees SET {','.join(fields)} WHERE id=?", vals)
    return {"ok":True}

@app.delete("/api/employees/{eid}")
def del_employee(eid:str, user=Depends(require_admin)):
    with get_db() as db: db.execute("DELETE FROM employees WHERE id=?", (eid,))
    return {"ok":True}

class ExpenseIn(BaseModel):
    vendor:str; department:str="G&A"; subCategory:str=""; monthlyAmount:float=0; isCogs:bool=False
    vendorContact:str=""; vendorEmail:str=""; vendorPhone:str=""; serviceDesc:str=""
    frequency:str="monthly"

FREQ_MULTIPLIERS = {"monthly":1,"bimonthly":0.5,"quarterly":1/3,"semi_annual":1/6,"annual":1/12}

@app.post("/api/expenses")
def add_expense(b:ExpenseIn, user=Depends(require_admin)):
    xid=str(uuid4())[:8]
    mult=FREQ_MULTIPLIERS.get(b.frequency, 1)
    amounts={m: round(b.monthlyAmount * mult, 2) for m in ML}
    with get_db() as db:
        db.execute("INSERT INTO expenses (id,dept,vendor,sub_cat,is_cogs,amounts,vendor_contact,vendor_email,vendor_phone,service_desc,frequency) VALUES (?,?,?,?,?,?,?,?,?,?,?)",
                   (xid,b.department,b.vendor,b.subCategory,int(b.isCogs),json.dumps(amounts),b.vendorContact,b.vendorEmail,b.vendorPhone,b.serviceDesc,b.frequency))
    return {"ok":True,"id":xid}

class ExpenseUpdate(BaseModel):
    vendor:Optional[str]=None; department:Optional[str]=None; subCategory:Optional[str]=None
    monthlyAmount:Optional[float]=None; isCogs:Optional[bool]=None
    vendorContact:Optional[str]=None; vendorEmail:Optional[str]=None
    vendorPhone:Optional[str]=None; serviceDesc:Optional[str]=None
    frequency:Optional[str]=None; currency:Optional[str]=None

@app.put("/api/expenses/{xid}")
def upd_expense(xid:str, b:ExpenseUpdate, user=Depends(require_admin)):
    fields=[]; vals=[]
    if b.vendor is not None: fields.append("vendor=?"); vals.append(b.vendor)
    if b.department is not None: fields.append("dept=?"); vals.append(b.department)
    if b.subCategory is not None: fields.append("sub_cat=?"); vals.append(b.subCategory)
    if b.isCogs is not None: fields.append("is_cogs=?"); vals.append(int(b.isCogs))
    if b.vendorContact is not None: fields.append("vendor_contact=?"); vals.append(b.vendorContact)
    if b.vendorEmail is not None: fields.append("vendor_email=?"); vals.append(b.vendorEmail)
    if b.vendorPhone is not None: fields.append("vendor_phone=?"); vals.append(b.vendorPhone)
    if b.serviceDesc is not None: fields.append("service_desc=?"); vals.append(b.serviceDesc)
    if b.frequency is not None: fields.append("frequency=?"); vals.append(b.frequency)
    if b.currency is not None: fields.append("currency=?"); vals.append(b.currency)
    if b.monthlyAmount is not None or b.frequency is not None:
        freq = b.frequency
        amt = b.monthlyAmount
        if freq is None or amt is None:
            with get_db() as db:
                row = db.execute("SELECT amounts, frequency FROM expenses WHERE id=?", (xid,)).fetchone()
                if row:
                    if freq is None: freq = row["frequency"]
                    if amt is None:
                        old_amounts = json.loads(row["amounts"])
                        avg = sum(old_amounts.values()) / max(len(old_amounts), 1)
                        old_mult = FREQ_MULTIPLIERS.get(row["frequency"], 1)
                        amt = avg / old_mult if old_mult else avg
        mult = FREQ_MULTIPLIERS.get(freq or "monthly", 1)
        amounts = {m: round((amt or 0) * mult, 2) for m in ML}
        fields.append("amounts=?"); vals.append(json.dumps(amounts))
    if not fields: return {"ok":True}
    vals.append(xid)
    with get_db() as db:
        db.execute(f"UPDATE expenses SET {','.join(fields)} WHERE id=?", vals)
    return {"ok":True}

@app.delete("/api/expenses/{xid}")
def del_expense(xid:str, user=Depends(require_admin)):
    with get_db() as db: db.execute("DELETE FROM expenses WHERE id=?", (xid,))
    return {"ok":True}

@app.get("/api/audit/{entity_id}")
def get_audit(entity_id:str, user=Depends(get_current_user)):
    with get_db() as db:
        rows = db.execute("SELECT * FROM audit_log WHERE entity_id=? ORDER BY changed_at DESC LIMIT 50", (entity_id,)).fetchall()
    return [dict(r) for r in rows]

class RateUpdate(BaseModel):
    rate: float

@app.get("/api/exchange-rate")
def api_get_rate():
    rate = get_exchange_rate()
    with get_db() as db:
        rows = db.execute("SELECT month, rate, locked FROM monthly_rates ORDER BY month").fetchall()
    monthly = {r["month"]: {"rate": r["rate"], "locked": bool(r["locked"])} for r in rows}
    now = datetime.now()
    current_month = f"{now.month:02d}-{now.year}"
    return {"rate": rate, "currentMonth": current_month, "monthlyRates": monthly}

@app.put("/api/exchange-rate")
def api_set_rate(b: RateUpdate, user=Depends(require_admin)):
    set_exchange_rate(b.rate)
    # Also set for current and future unlocked months
    now = datetime.now()
    current_month = f"{now.month:02d}-{now.year}"
    with get_db() as db:
        for m in ML:
            if m >= current_month:
                db.execute("INSERT OR REPLACE INTO monthly_rates (month, rate, locked) VALUES (?,?,0)", (m, b.rate))
    return {"ok": True, "rate": b.rate}

class MonthRateLock(BaseModel):
    month: str; rate: float

@app.put("/api/exchange-rate/lock")
def lock_month_rate(b: MonthRateLock, user=Depends(require_admin)):
    with get_db() as db:
        db.execute("INSERT OR REPLACE INTO monthly_rates (month, rate, locked) VALUES (?,?,1)", (b.month, b.rate))
    return {"ok": True}

# ══════════════════════════════════════════
# Serve
# ══════════════════════════════════════════
@app.get("/", response_class=HTMLResponse)
def serve():
    return (Path(__file__).parent / "index.html").read_text(encoding="utf-8")

@app.on_event("startup")
def startup():
    init_db()
    if not is_seeded():
        print("  \U0001f331 Seeding..."); seed_db()
        print(f"  \u2705 Done")
    else:
        print(f"  \U0001f4be DB loaded")
    lock_past_months()
    now = datetime.now()
    print(f"  \U0001f4b1 Rate: $1 = \u20aa{get_exchange_rate():.2f} (locked for months before {now.month:02d}-{now.year})")
    print(f"\n  Users: admin/admin123 (management), eduardo/sales123, elad/sales123, tiki/sales123 (sales)\n")

if __name__ == "__main__":
    import uvicorn
    print("\n  \u26a1 FinStack v6 — Auth + CRM")
    print("  " + "\u2500" * 35)
    print("  http://localhost:8000\n")
    uvicorn.run(app, host="127.0.0.1", port=8000)
