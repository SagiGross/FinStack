import { useState, useMemo } from "react";
import {
  LineChart, Line, BarChart, Bar, AreaChart, Area, XAxis, YAxis,
  CartesianGrid, Tooltip, Legend, ResponsiveContainer, ComposedChart,
  Cell, ReferenceLine, PieChart, Pie,
} from "recharts";
import {
  LayoutDashboard, TrendingUp, Wallet, ChevronLeft,
  ChevronRight, ArrowUpRight, ArrowDownRight, DollarSign, Users,
  FileText, Target, Zap, BarChart3, PieChart as PieIcon,
  SlidersHorizontal, Ghost, Clock, Percent, Building2, Globe,
  Activity, Minus, CreditCard, Briefcase,
} from "lucide-react";

/* ═══════════════════════════════════════════════════════════════════
   FINANCIAL ENGINE — Real data from uploaded Excel
   ═══════════════════════════════════════════════════════════════════ */
const ECF = 1.35;
const FY = 2026;
const ML = Array.from({ length: 12 }, (_, i) => `${String(i + 1).padStart(2, "0")}-${FY}`);

const EMP = [
  { id: "e01", n: "Etti Berger", d: "G&A", g: 16487.46, h: "2024-01-01", t: null },
  { id: "e02", n: "Shai Grumet", d: "R&D", g: 11314.92, h: "2024-01-01", t: null },
  { id: "e03", n: "Arye Laskin", d: "R&D", g: 9051.94, h: "2024-01-01", t: null },
  { id: "e04", n: "Oren Chappo", d: "R&D", g: 11961.49, h: "2024-01-01", t: null },
  { id: "e05", n: "Eduardo Borotchin", d: "S&M", g: 10345.07, h: "2024-01-01", t: null },
  { id: "e06", n: "Nitai Driel", d: "R&D", g: 387.94, h: "2024-01-01", t: null },
  { id: "e07", n: "Elad Lev", d: "S&M", g: 8082.09, h: "2024-01-01", t: null },
  { id: "e08", n: "Tiki Tavero", d: "S&M", g: 6465.67, h: "2024-01-01", t: null },
  { id: "e09", n: "Meirav Zetz", d: "G&A", g: 2020.52, h: "2024-01-01", t: null },
  { id: "e10", n: "Yaniv Barkai", d: "R&D", g: 19431.60, h: "2024-01-01", t: "2026-01-31" },
  { id: "e11", n: "Elad Sheskin", d: "R&D", g: 0, h: "2024-01-01", t: "2025-12-31" },
];

const CON = [
  { id:"c01",cl:"Ministry of Defence",co:"Indonesia",ind:"Government",yr:2026,sm:1,sd:"2026-01-01",v:800000,dso:60,pm:"03-2026",mo:false,ch:0.75,ap:null },
  { id:"c02",cl:"Ministry of Defence",co:"Indonesia",ind:"Government",yr:2026,sm:1,sd:"2026-01-01",v:150000,dso:120,pm:"05-2026",mo:false,ch:0.75,ap:null },
  { id:"c03",cl:"Serbia",co:"Serbia",ind:"Government",yr:2025,sm:10,sd:"2025-10-01",v:90000,dso:240,pm:"05-2026",mo:false,ch:0.5,ap:null },
  { id:"c04",cl:"Practical Cyber Academy",co:"Singapore",ind:"Academy",yr:2026,sm:2,sd:"2026-02-01",v:155000,dso:240,pm:"09-2026",mo:false,ch:0.75,ap:null },
  { id:"c05",cl:"IAI",co:"Israel",ind:"Enterprise",yr:2025,sm:11,sd:"2025-11-01",v:200000,dso:180,pm:"04-2026",mo:false,ch:null,ap:null },
  { id:"c06",cl:"Elta",co:"Israel",ind:"Enterprise",yr:2025,sm:10,sd:"2025-10-01",v:5000,dso:180,pm:"03-2026",mo:false,ch:1.0,ap:3483.87 },
  { id:"c07",cl:"Elta",co:"Israel",ind:"Enterprise",yr:2025,sm:10,sd:"2025-10-01",v:900000,dso:270,pm:"06-2026",mo:false,ch:0.5,ap:null },
  { id:"c08",cl:"Elta",co:"Israel",ind:"Enterprise",yr:2026,sm:2,sd:"2026-02-01",v:480000,dso:120,pm:"06-2026",mo:false,ch:0.25,ap:null },
  { id:"c09",cl:"Elta",co:"Israel",ind:"Enterprise",yr:2026,sm:1,sd:"2026-01-01",v:200000,dso:270,pm:"09-2026",mo:false,ch:0.25,ap:null },
  { id:"c10",cl:"Schools",co:"Israel",ind:"Academy",yr:2025,sm:10,sd:"2025-10-01",v:26000,dso:60,pm:"11-2025",mo:false,ch:0.25,ap:null },
  { id:"c11",cl:"Schools",co:"Israel",ind:"Academy",yr:2025,sm:10,sd:"2025-10-01",v:15000,dso:120,pm:"01-2026",mo:false,ch:1.0,ap:11231.94 },
  { id:"c12",cl:"The Jewish Agency",co:"Israel",ind:"Government",yr:2026,sm:2,sd:"2026-02-01",v:4000,dso:180,pm:"07-2026",mo:false,ch:0.25,ap:null },
  { id:"c13",cl:"Improvate",co:"Israel",ind:"Academy",yr:2026,sm:5,sd:"2026-05-01",v:150000,dso:60,pm:"06-2026",mo:true,ch:1.0,ap:12108.06 },
  { id:"c14",cl:"OST",co:"Japan",ind:"Academy",yr:2026,sm:1,sd:"2026-01-01",v:20000,dso:60,pm:"03-2026",mo:false,ch:null,ap:null },
  { id:"c15",cl:"SPAN",co:"Croatia",ind:"Enterprise",yr:2025,sm:12,sd:"2025-12-01",v:29000,dso:300,pm:"09-2026",mo:false,ch:0.75,ap:null },
  { id:"c16",cl:"Bank of Israel",co:"Israel",ind:"Government",yr:2026,sm:1,sd:"2026-01-01",v:15000,dso:45,pm:"02-2026",mo:false,ch:1.0,ap:null },
  { id:"c17",cl:"Military Academy",co:"Macedonia",ind:"Government",yr:2026,sm:1,sd:"2026-01-01",v:32500,dso:270,pm:"09-2026",mo:false,ch:0.25,ap:null },
  { id:"c18",cl:"DSA",co:"Cyprus",ind:"Government",yr:2025,sm:10,sd:"2025-10-01",v:56000,dso:210,pm:"04-2026",mo:false,ch:0.5,ap:35404.52 },
  { id:"c19",cl:"DSA",co:"Cyprus",ind:"Government",yr:2026,sm:1,sd:"2026-01-01",v:73000,dso:360,pm:"12-2026",mo:false,ch:0.5,ap:null },
  { id:"c20",cl:"DSA",co:"Cyprus",ind:"Government",yr:2026,sm:3,sd:"2026-03-01",v:76000,dso:240,pm:"10-2026",mo:false,ch:0.75,ap:null },
  { id:"c21",cl:"Cyber Services HK",co:"Hong Kong",ind:"Academy",yr:2025,sm:11,sd:"2025-11-01",v:8000,dso:30,pm:"12-2025",mo:false,ch:null,ap:null },
  { id:"c22",cl:"Villa Tech",co:"US",ind:"Enterprise",yr:2026,sm:1,sd:"2026-01-01",v:9000,dso:90,pm:"04-2026",mo:false,ch:null,ap:null },
  { id:"c23",cl:"MAG",co:"Nigeria",ind:"Enterprise",yr:2026,sm:1,sd:"2026-01-01",v:30000,dso:45,pm:"02-2026",mo:false,ch:1.0,ap:22800 },
  { id:"c24",cl:"Future Smart",co:"Greece",ind:"Academy",yr:2025,sm:12,sd:"2025-12-01",v:2500,dso:270,pm:"08-2026",mo:false,ch:1.0,ap:null },
  { id:"c25",cl:"Technion",co:"Israel",ind:"Academy",yr:2026,sm:1,sd:"2026-01-01",v:42000,dso:270,pm:"09-2026",mo:true,ch:1.0,ap:3870.97 },
  { id:"c26",cl:"Villa Tech",co:"US",ind:"Enterprise",yr:2026,sm:1,sd:"2026-01-01",v:9000,dso:180,pm:"06-2026",mo:false,ch:null,ap:null },
  { id:"c27",cl:"Citadel",co:"Israel",ind:"Government",yr:2026,sm:1,sd:"2026-01-01",v:19000,dso:180,pm:"06-2026",mo:false,ch:null,ap:null },
  { id:"c28",cl:"EU Funding",co:"Greece",ind:"Government",yr:2026,sm:1,sd:"2026-01-01",v:300000,dso:270,pm:"09-2026",mo:false,ch:0.25,ap:null },
  { id:"c29",cl:"Black Wall Global",co:"Japan",ind:"Academy",yr:2026,sm:1,sd:"2026-01-01",v:8000,dso:180,pm:"06-2026",mo:false,ch:null,ap:null },
  { id:"c30",cl:"Schools",co:"Israel",ind:"Academy",yr:2026,sm:1,sd:"2026-01-01",v:64000,dso:270,pm:"09-2026",mo:false,ch:null,ap:null },
  { id:"c31",cl:"Abu Dhabi",co:"UAE",ind:"Government",yr:2026,sm:1,sd:"2026-01-01",v:300000,dso:270,pm:"09-2026",mo:false,ch:0.75,ap:null },
  { id:"c32",cl:"????",co:"UAE",ind:"Government",yr:2025,sm:12,sd:"2025-12-01",v:500000,dso:300,pm:"09-2026",mo:false,ch:0.25,ap:null },
  { id:"c33",cl:"????",co:"UAE",ind:"Government",yr:2025,sm:12,sd:"2025-12-01",v:300000,dso:300,pm:"09-2026",mo:false,ch:0.25,ap:null },
  { id:"c34",cl:"Saudi Arabia",co:"Saudi Arabia",ind:"Government",yr:2026,sm:1,sd:"2026-01-01",v:500000,dso:270,pm:"09-2026",mo:false,ch:null,ap:null },
  { id:"c35",cl:"Kenya",co:"Kenya",ind:"Government",yr:2026,sm:2,sd:"2026-02-01",v:500000,dso:120,pm:"06-2026",mo:false,ch:null,ap:null },
  { id:"c36",cl:"Albania",co:"Albania",ind:"Government",yr:2026,sm:3,sd:"2026-03-01",v:300000,dso:180,pm:"08-2026",mo:false,ch:null,ap:null },
  { id:"c37",cl:"Cyber Gain",co:"Israel",ind:"Enterprise",yr:2026,sm:2,sd:"2026-02-01",v:1000,dso:45,pm:"03-2026",mo:false,ch:null,ap:null },
  { id:"c38",cl:"Synergy 7",co:"Israel",ind:"Enterprise",yr:2026,sm:2,sd:"2026-02-01",v:3000,dso:60,pm:"04-2026",mo:false,ch:1.0,ap:null },
  { id:"c39",cl:"Gabon",co:"Gabon",ind:"Government",yr:2026,sm:3,sd:"2026-03-01",v:450000,dso:120,pm:"06-2026",mo:false,ch:0.5,ap:null },
  { id:"c40",cl:"KSV/023",co:"Kosovo",ind:"Government",yr:2026,sm:1,sd:"2026-01-01",v:60000,dso:60,pm:"03-2026",mo:false,ch:1.0,ap:null },
  { id:"c41",cl:"Alliance Bank",co:"Malaysia",ind:"Enterprise",yr:2026,sm:1,sd:"2026-01-01",v:42000,dso:60,pm:"03-2026",mo:false,ch:0.5,ap:null },
  { id:"c42",cl:"Migdal",co:"Israel",ind:"Enterprise",yr:2026,sm:1,sd:"2026-01-01",v:20322.58,dso:45,pm:"02-2026",mo:false,ch:1.0,ap:null },
  { id:"c43",cl:"Cyber Gain",co:"Israel",ind:"Enterprise",yr:2026,sm:1,sd:"2026-01-01",v:1100,dso:90,pm:"04-2026",mo:false,ch:null,ap:null },
  { id:"c44",cl:"Univ. of Botswana",co:"Botswana",ind:"Academy",yr:2026,sm:1,sd:"2026-01-01",v:100000,dso:270,pm:"09-2026",mo:false,ch:0.25,ap:null },
  { id:"c45",cl:"CSIRT",co:"Rwanda",ind:"Government",yr:2026,sm:1,sd:"2026-01-01",v:200000,dso:270,pm:"09-2026",mo:false,ch:0.25,ap:null },
  { id:"c46",cl:"NFSU",co:"India",ind:"Academy",yr:2026,sm:2,sd:"2026-02-01",v:90000,dso:240,pm:"09-2026",mo:false,ch:0.5,ap:null },
  { id:"c47",cl:"Black Wall Global",co:"Japan",ind:"Enterprise",yr:2026,sm:1,sd:"2026-01-01",v:8200,dso:60,pm:"03-2026",mo:false,ch:1.0,ap:null },
  { id:"c48",cl:"Ivory Coast",co:"Ivory Coast",ind:"Government",yr:2026,sm:1,sd:"2026-01-01",v:80000,dso:60,pm:"03-2026",mo:false,ch:0.75,ap:null },
];

const VEX = [
  { d:"R&D",vn:"Tera Sky",cogs:true,a:[2866.24,2500,2500,2500,2500,2500,2500,2500,2500,2500,2500,2500] },
  { d:"G&A",vn:"Atidim",cogs:false,a:[7006.37,6875,6875,6875,6875,6875,6875,6875,6875,6875,6875,6875] },
  { d:"G&A",vn:"Tel Aviv",cogs:false,a:[1433.12,1406.25,1406.25,1406.25,1406.25,1406.25,1406.25,1406.25,1406.25,1406.25,1406.25,1406.25] },
  { d:"G&A",vn:"Ilan",cogs:false,a:[1114.65,1093.75,1093.75,1093.75,1093.75,1093.75,1093.75,1093.75,1093.75,1093.75,1093.75,1093.75] },
  { d:"G&A",vn:"Herzog",cogs:false,a:[1592.36,1562.50,1562.50,1562.50,1562.50,1562.50,1562.50,1562.50,1562.50,1562.50,1562.50,1562.50] },
  { d:"G&A",vn:"Misc.",cogs:false,a:Array(12).fill(300) },
  { d:"R&D",vn:"Cellcom",cogs:true,a:[254.78,257.99,257.99,257.99,257.99,257.99,257.99,257.99,257.99,257.99,257.99,257.99] },
  { d:"G&A",vn:"Misc.",cogs:false,a:Array(12).fill(300) },
  { d:"G&A",vn:"Registrar",cogs:false,a:[445.86,0,0,0,0,0,0,0,0,0,0,0] },
  { d:"Training",vn:"Misc.",cogs:true,a:Array(12).fill(20000) },
  { d:"G&A",vn:"Misc.",cogs:false,a:Array(12).fill(10000) },
  { d:"R&D",vn:"Nir",cogs:true,a:[11146.50,11286.86,11286.86,11286.86,11286.86,11286.86,11286.86,11286.86,11286.86,11286.86,11286.86,11286.86] },
  { d:"G&A",vn:"Altshare",cogs:false,a:[1273.89,0,0,0,0,0,0,0,0,0,0,0] },
  { d:"G&A",vn:"Misc.",cogs:false,a:Array(12).fill(100) },
  { d:"G&A",vn:"Misc.",cogs:false,a:[31.85,32.25,32.25,32.25,32.25,32.25,32.25,32.25,32.25,32.25,32.25,32.25] },
  { d:"S&M",vn:"Misc.",cogs:false,a:Array(12).fill(1500) },
  { d:"G&A",vn:"Misc.",cogs:false,a:Array(12).fill(800) },
  { d:"R&D",vn:"Tzahi",cogs:true,a:[0,5643.43,5643.43,5643.43,5643.43,5643.43,5643.43,5643.43,5643.43,5643.43,5643.43,5643.43] },
];

function parsePM(pm){try{const[m,y]=pm.split("-").map(Number);return y===FY&&m>=1&&m<=12?m-1:null}catch{return null}}
function shiftPM(pm,days){if(!days)return pm;try{const[m,y]=pm.split("-").map(Number);const d=new Date(y,m-1,15);d.setDate(d.getDate()+days);return`${String(d.getMonth()+1).padStart(2,"0")}-${d.getFullYear()}`}catch{return pm}}

function compute(ghosts=[],delay=0,w=true){
  const allE=[...EMP,...ghosts];
  const data=ML.map((ml,mi)=>{
    const[mm,yy]=ml.split("-").map(Number);const md=new Date(yy,mm-1,1);
    const lab={"R&D":0,"S&M":0,"G&A":0,"Training":0};
    allE.forEach(e=>{const h=new Date(e.h);const t=e.t?new Date(e.t):null;if(md>=h&&(!t||md<=t))lab[e.d]+=e.g*ECF});
    const vd={"R&D":0,"S&M":0,"G&A":0,"Training":0};let vc=0,vo=0;
    VEX.forEach(x=>{const a=x.a[mi];vd[x.d]+=a;if(x.cogs)vc+=a;else vo+=a});
    const lc=lab["R&D"],lo=lab["S&M"]+lab["G&A"]+lab["Training"];
    return{month:ml.substring(0,2),lab,vd,cogs:lc+vc,opex:lo+vo,totalExp:lc+vc+lo+vo,revenue:0,cashIn:0};
  });
  CON.forEach(c=>{let val=c.v;if(w){val=c.ch!==null?val*c.ch:0}
    if(c.mo){let si=c.sm-1;if(new Date(c.sd).getFullYear()<FY)si=0;if(si<0)si=0;const rem=12-si;if(rem<=0)return;const mv=val/rem;for(let i=si;i<12;i++)data[i].revenue+=mv}
    else{if(new Date(c.sd).getFullYear()===FY){const idx=c.sm-1;if(idx>=0&&idx<12)data[idx].revenue+=val}else if(new Date(c.sd).getFullYear()<FY)data[0].revenue+=val}});
  CON.forEach(c=>{if(c.ap){const idx=parsePM(shiftPM(c.pm,delay));if(idx!==null)data[idx].cashIn+=c.ap;return}
    let val=c.v;if(w){val=c.ch!==null?val*c.ch:0}
    if(c.mo){let si=c.sm-1;if(new Date(c.sd).getFullYear()<FY)si=0;const rem=12-si;if(rem<=0)return;const mv=val/rem;
      for(let i=si;i<12;i++){const pd=new Date(FY,i,15);pd.setDate(pd.getDate()+c.dso+delay);if(pd.getFullYear()===FY&&pd.getMonth()<12)data[pd.getMonth()].cashIn+=mv}}
    else{const idx=parsePM(shiftPM(c.pm,delay));if(idx!==null)data[idx].cashIn+=val}});
  let cum=0;
  data.forEach(d=>{d.grossProfit=d.revenue-d.cogs;d.grossMargin=d.revenue>0?d.grossProfit/d.revenue*100:0;d.netIncome=d.revenue-d.totalExp;d.cashOut=d.totalExp;d.netCashflow=d.cashIn-d.cashOut;cum+=d.netCashflow;d.cumCash=cum;d.burnRate=d.cashOut>d.cashIn?d.cashOut-d.cashIn:0;d.runway=d.burnRate>0?cum/d.burnRate:null});
  return data;
}

/* ═══════════════════════════════════════════════════════════════════
   DESIGN TOKENS
   ═══════════════════════════════════════════════════════════════════ */
const T = {
  bg:"#0B0F1A",bgCard:"#111827",bgHover:"#1a2236",bgSb:"#0d1117",bgIn:"#1a2236",
  bd:"#1e293b",bdL:"#2a3a52",
  tx:"#e2e8f0",txD:"#94a3b8",txM:"#64748b",
  ac:"#3b82f6",acL:"#60a5fa",acG:"rgba(59,130,246,0.15)",
  gn:"#10b981",gnL:"#34d399",gnG:"rgba(16,185,129,0.12)",
  rd:"#ef4444",rdG:"rgba(239,68,68,0.12)",
  am:"#f59e0b",pu:"#8b5cf6",cy:"#06b6d4",pk:"#ec4899",tl:"#14b8a6",
  r:14,rS:10,
  f:"'Outfit','Satoshi',system-ui,-apple-system,sans-serif",
  fm:"'JetBrains Mono','Fira Code',monospace",
};
const fmt=n=>{if(n==null)return"—";const a=Math.abs(n);if(a>=1e6)return`$${(n/1e6).toFixed(2)}M`;if(a>=1e3)return`$${(n/1e3).toFixed(1)}K`;return`$${n.toFixed(0)}`};
const fmtP=n=>n==null?"—":`${n.toFixed(1)}%`;
const fmtM=n=>n==null?"∞":`${n.toFixed(1)}`;

/* ═══════════════════════════════════════════════════════════════════
   COMPONENTS
   ═══════════════════════════════════════════════════════════════════ */
function GC({children,s={},glow}){return<div style={{background:T.bgCard,border:`1px solid ${T.bd}`,borderRadius:T.r,padding:20,boxShadow:glow||"inset 0 1px 0 0 rgba(255,255,255,0.04)",position:"relative",overflow:"hidden",...s}}>{children}</div>}

function KPI({icon:Ic,label,value,sub,delta,color=T.ac,dl=0}){
  const pos=delta>0;const Ar=delta>0?ArrowUpRight:delta<0?ArrowDownRight:Minus;
  return(
    <div style={{background:T.bgCard,border:`1px solid ${T.bd}`,borderRadius:T.r,padding:"18px 20px",position:"relative",overflow:"hidden",animation:`fsu 0.5s ${dl}ms both cubic-bezier(.4,0,.2,1)`}}>
      <div style={{position:"absolute",top:-20,right:-20,width:80,height:80,borderRadius:"50%",background:color,opacity:0.06}}/>
      <div style={{display:"flex",alignItems:"center",gap:8,marginBottom:10}}>
        <div style={{width:32,height:32,borderRadius:8,background:`${color}18`,display:"flex",alignItems:"center",justifyContent:"center"}}><Ic size={16} color={color} strokeWidth={2.2}/></div>
        <span style={{fontSize:11,fontWeight:600,textTransform:"uppercase",letterSpacing:1,color:T.txM}}>{label}</span>
      </div>
      <div style={{fontSize:28,fontWeight:800,color:T.tx,letterSpacing:-1,fontFamily:T.fm,lineHeight:1}}>{value}</div>
      <div style={{display:"flex",alignItems:"center",justifyContent:"space-between",marginTop:8}}>
        <span style={{fontSize:12,color:T.txD}}>{sub}</span>
        {delta!==undefined&&<div style={{display:"flex",alignItems:"center",gap:3,padding:"2px 8px",borderRadius:20,background:pos?T.gnG:delta<0?T.rdG:"transparent",color:pos?T.gn:delta<0?T.rd:T.txM,fontSize:11,fontWeight:700}}><Ar size={12}/>{Math.abs(delta).toFixed(1)}%</div>}
      </div>
    </div>
  );
}

function CTT({active,payload,label}){
  if(!active||!payload?.length)return null;
  return(
    <div style={{background:"rgba(17,24,39,0.96)",backdropFilter:"blur(16px)",border:`1px solid ${T.bdL}`,borderRadius:12,padding:"12px 16px",boxShadow:"0 4px 24px rgba(0,0,0,0.3)",minWidth:160}}>
      <div style={{fontSize:12,fontWeight:700,color:T.tx,marginBottom:8,letterSpacing:0.5}}>{label}</div>
      {payload.map((p,i)=><div key={i} style={{display:"flex",alignItems:"center",justifyContent:"space-between",gap:16,marginBottom:3}}>
        <div style={{display:"flex",alignItems:"center",gap:6}}><div style={{width:8,height:8,borderRadius:3,background:p.color}}/><span style={{fontSize:11,color:T.txD}}>{p.name}</span></div>
        <span style={{fontSize:12,fontWeight:700,color:T.tx,fontFamily:T.fm}}>{fmt(p.value)}</span>
      </div>)}
    </div>
  );
}

function CP({title,icon:Ic,children,h=280}){return<GC s={{padding:"16px 12px 8px"}}><div style={{display:"flex",alignItems:"center",gap:8,marginBottom:12,paddingLeft:8}}>{Ic&&<Ic size={14} color={T.acL}/>}<span style={{fontSize:13,fontWeight:700,color:T.tx,letterSpacing:0.3}}>{title}</span></div><ResponsiveContainer width="100%" height={h}>{children}</ResponsiveContainer></GC>}

const gs="#1e293b";const at={fontSize:10,fill:T.txM,fontFamily:T.fm};

function RS({label,icon:Ic,value,onChange,min,max,step=1,unit="",color=T.ac}){return(
  <div style={{display:"flex",flexDirection:"column",gap:6}}>
    <div style={{display:"flex",justifyContent:"space-between",alignItems:"center"}}>
      <div style={{display:"flex",alignItems:"center",gap:6}}><Ic size={13} color={color}/><span style={{fontSize:11,fontWeight:700,textTransform:"uppercase",letterSpacing:0.8,color:T.txD}}>{label}</span></div>
      <span style={{fontSize:15,fontWeight:800,color,fontFamily:T.fm}}>{value}{unit}</span>
    </div>
    <input type="range" min={min} max={max} step={step} value={value} onChange={e=>onChange(Number(e.target.value))} style={{width:"100%",accentColor:color,height:4,cursor:"pointer"}}/>
  </div>
)}

/* ═══════════════════════════════════════════════════════════════════
   SIDEBAR
   ═══════════════════════════════════════════════════════════════════ */
function Sidebar({tab,setTab,col,setCol}){
  const items=[{id:"dash",icon:LayoutDashboard,label:"Dashboard"},{id:"costs",icon:Wallet,label:"Expenses"},{id:"pipeline",icon:Target,label:"Pipeline"},{id:"scenario",icon:SlidersHorizontal,label:"What-If"}];
  return(
    <div style={{width:col?64:220,minHeight:"100vh",background:T.bgSb,borderRight:`1px solid ${T.bd}`,display:"flex",flexDirection:"column",transition:"width 0.3s cubic-bezier(.4,0,.2,1)",flexShrink:0,zIndex:10}}>
      <div style={{padding:col?"20px 12px":"20px 20px",borderBottom:`1px solid ${T.bd}`,display:"flex",alignItems:"center",gap:10,justifyContent:col?"center":"flex-start"}}>
        <div style={{width:34,height:34,borderRadius:10,background:`linear-gradient(135deg,${T.ac},${T.pu})`,display:"flex",alignItems:"center",justifyContent:"center",boxShadow:`0 0 20px ${T.acG}`}}><Zap size={18} color="#fff" strokeWidth={2.5}/></div>
        {!col&&<div><div style={{fontSize:16,fontWeight:800,color:T.tx,letterSpacing:-0.5}}>FinStack</div><div style={{fontSize:9,fontWeight:600,color:T.txM,textTransform:"uppercase",letterSpacing:1.5}}>CFO Suite</div></div>}
      </div>
      <div style={{padding:"12px 8px",flex:1,display:"flex",flexDirection:"column",gap:2}}>
        {items.map(it=>{const a=tab===it.id;return(
          <button key={it.id} onClick={()=>setTab(it.id)} style={{display:"flex",alignItems:"center",gap:12,padding:col?"12px 0":"11px 14px",justifyContent:col?"center":"flex-start",borderRadius:T.rS,border:"none",cursor:"pointer",background:a?T.acG:"transparent",color:a?T.acL:T.txD,transition:"all 0.2s",width:"100%",position:"relative"}}>
            {a&&<div style={{position:"absolute",left:0,top:"50%",transform:"translateY(-50%)",width:3,height:20,borderRadius:4,background:T.ac}}/>}
            <it.icon size={18} strokeWidth={a?2.3:1.8}/>{!col&&<span style={{fontSize:13,fontWeight:a?700:500}}>{it.label}</span>}
          </button>
        )})}
      </div>
      <button onClick={()=>setCol(!col)} style={{padding:16,border:"none",cursor:"pointer",background:"transparent",color:T.txM,borderTop:`1px solid ${T.bd}`,display:"flex",alignItems:"center",justifyContent:"center"}}>{col?<ChevronRight size={16}/>:<ChevronLeft size={16}/>}</button>
    </div>
  );
}

/* ═══════════════════════════════════════════════════════════════════
   HEADER
   ═══════════════════════════════════════════════════════════════════ */
function Header({data,w,setW}){
  const l=data[data.length-1];const tr=data.reduce((s,d)=>s+d.revenue,0);
  return(
    <div style={{padding:"12px 24px",borderBottom:`1px solid ${T.bd}`,display:"flex",alignItems:"center",justifyContent:"space-between",background:T.bgSb}}>
      <div style={{display:"flex",gap:28,alignItems:"center"}}>
        {[{l:"Cash",v:fmt(l.cumCash),ic:CreditCard,c:l.cumCash>=0?T.gn:T.rd},{l:"Burn/mo",v:fmt(data.reduce((s,d)=>s+d.totalExp,0)/12),ic:Activity,c:T.am},{l:"Runway",v:l.runway?`${fmtM(l.runway)} mo`:"∞",ic:Clock,c:T.cy},{l:"FY Rev",v:fmt(tr),ic:TrendingUp,c:T.gn}].map((k,i)=>(
          <div key={i} style={{display:"flex",alignItems:"center",gap:8}}>
            <k.ic size={14} color={k.c} strokeWidth={2}/>
            <div><div style={{fontSize:9,fontWeight:600,textTransform:"uppercase",letterSpacing:1.2,color:T.txM}}>{k.l}</div><div style={{fontSize:15,fontWeight:800,color:T.tx,fontFamily:T.fm,letterSpacing:-0.5}}>{k.v}</div></div>
          </div>
        ))}
      </div>
      <button onClick={()=>setW(!w)} style={{display:"flex",alignItems:"center",gap:8,padding:"8px 16px",borderRadius:10,border:`1px solid ${T.bdL}`,background:T.bgIn,cursor:"pointer",color:T.tx,transition:"all 0.2s"}}>
        <div style={{width:36,height:20,borderRadius:10,position:"relative",background:w?T.ac:T.txM,transition:"all 0.25s"}}><div style={{width:16,height:16,borderRadius:8,background:"#fff",position:"absolute",top:2,left:w?18:2,transition:"all 0.25s",boxShadow:"0 1px 4px rgba(0,0,0,0.3)"}}/></div>
        <span style={{fontSize:12,fontWeight:600}}>{w?"Weighted":"Full Pipeline"}</span>
      </button>
    </div>
  );
}

/* ═══════════════════════════════════════════════════════════════════
   TAB: DASHBOARD
   ═══════════════════════════════════════════════════════════════════ */
function DashTab({data}){
  const t=useMemo(()=>({rv:data.reduce((s,d)=>s+d.revenue,0),cg:data.reduce((s,d)=>s+d.cogs,0),op:data.reduce((s,d)=>s+d.opex,0),ni:data.reduce((s,d)=>s+d.netIncome,0),br:data.reduce((s,d)=>s+d.totalExp,0)/12,gm:data.reduce((s,d)=>s+d.grossMargin,0)/12}),[data]);
  const rd=data[0].revenue>0?((data[1].revenue-data[0].revenue)/data[0].revenue*100):0;
  return(
    <div style={{display:"flex",flexDirection:"column",gap:16}}>
      <div style={{display:"grid",gridTemplateColumns:"repeat(6,1fr)",gap:12}}>
        <KPI icon={TrendingUp} label="Annual Revenue" value={fmt(t.rv)} sub="FY 2026" color={T.gn} dl={0}/>
        <KPI icon={BarChart3} label="Gross Margin" value={fmtP(t.gm)} sub={`COGS ${fmt(t.cg)}`} color={T.am} dl={50}/>
        <KPI icon={DollarSign} label="Net Income" value={fmt(t.ni)} sub="After OpEx" color={t.ni>=0?T.gn:T.rd} delta={rd} dl={100}/>
        <KPI icon={Activity} label="Avg Burn" value={fmt(t.br)} sub="Monthly" color={T.pu} dl={150}/>
        <KPI icon={CreditCard} label="End Cash" value={fmt(data[11].cumCash)} sub="Dec 2026" color={T.ac} dl={200}/>
        <KPI icon={Clock} label="Runway" value={data[11].runway?`${fmtM(data[11].runway)} mo`:"∞"} sub="Current rate" color={T.cy} dl={250}/>
      </div>
      <div style={{display:"grid",gridTemplateColumns:"1fr 1fr",gap:14}}>
        <CP title="Monthly P&L" icon={BarChart3}>
          <ComposedChart data={data}>
            <defs><linearGradient id="rg" x1="0" y1="0" x2="0" y2="1"><stop offset="0%" stopColor={T.gn} stopOpacity={0.9}/><stop offset="100%" stopColor={T.gn} stopOpacity={0.6}/></linearGradient></defs>
            <CartesianGrid strokeDasharray="3 3" stroke={gs} vertical={false}/><XAxis dataKey="month" tick={at} axisLine={false} tickLine={false}/><YAxis tick={at} axisLine={false} tickLine={false} tickFormatter={fmt}/><Tooltip content={<CTT/>}/>
            <Bar dataKey="revenue" name="Revenue" fill="url(#rg)" radius={[5,5,0,0]}/><Bar dataKey="cogs" name="COGS" fill={T.am} radius={[5,5,0,0]} opacity={0.75}/><Bar dataKey="opex" name="OpEx" fill={T.pu} radius={[5,5,0,0]} opacity={0.65}/>
            <Line dataKey="netIncome" name="Net Income" stroke={T.cy} strokeWidth={2.5} dot={false} type="monotone"/>
          </ComposedChart>
        </CP>
        <CP title="Cash Position" icon={CreditCard}>
          <ComposedChart data={data}>
            <defs><linearGradient id="cg" x1="0" y1="0" x2="0" y2="1"><stop offset="0%" stopColor={T.ac} stopOpacity={0.25}/><stop offset="100%" stopColor={T.ac} stopOpacity={0.02}/></linearGradient></defs>
            <CartesianGrid strokeDasharray="3 3" stroke={gs} vertical={false}/><XAxis dataKey="month" tick={at} axisLine={false} tickLine={false}/><YAxis tick={at} axisLine={false} tickLine={false} tickFormatter={fmt}/><Tooltip content={<CTT/>}/>
            <Area dataKey="cumCash" name="Cumulative" stroke={T.ac} fill="url(#cg)" strokeWidth={2.5} type="monotone" dot={false}/>
            <Bar dataKey="cashIn" name="Cash In" fill={T.gn} radius={[4,4,0,0]} opacity={0.7}/><Bar dataKey="cashOut" name="Cash Out" fill={T.rd} radius={[4,4,0,0]} opacity={0.5}/>
            <ReferenceLine y={0} stroke={T.txM} strokeDasharray="4 4"/>
          </ComposedChart>
        </CP>
        <CP title="Gross Margin Trend" icon={TrendingUp}>
          <AreaChart data={data}>
            <defs><linearGradient id="gg" x1="0" y1="0" x2="0" y2="1"><stop offset="0%" stopColor={T.am} stopOpacity={0.2}/><stop offset="100%" stopColor={T.am} stopOpacity={0}/></linearGradient></defs>
            <CartesianGrid strokeDasharray="3 3" stroke={gs} vertical={false}/><XAxis dataKey="month" tick={at} axisLine={false} tickLine={false}/><YAxis tick={at} axisLine={false} tickLine={false} tickFormatter={v=>`${v}%`} domain={[-100,100]}/><Tooltip content={<CTT/>}/>
            <Area dataKey="grossMargin" name="Gross Margin %" stroke={T.am} fill="url(#gg)" strokeWidth={2.5} type="monotone" dot={{r:3,fill:T.bgCard,stroke:T.am,strokeWidth:2}}/>
            <ReferenceLine y={50} stroke={T.gn} strokeDasharray="4 4" label={{value:"Target 50%",position:"insideTopRight",fontSize:9,fill:T.gn}}/>
            <ReferenceLine y={0} stroke={T.rd} strokeDasharray="4 4" opacity={0.5}/>
          </AreaChart>
        </CP>
        <CP title="Monthly Net Burn" icon={Activity}>
          <BarChart data={data}>
            <CartesianGrid strokeDasharray="3 3" stroke={gs} vertical={false}/><XAxis dataKey="month" tick={at} axisLine={false} tickLine={false}/><YAxis tick={at} axisLine={false} tickLine={false} tickFormatter={fmt}/><Tooltip content={<CTT/>}/>
            <Bar dataKey="burnRate" name="Net Burn" radius={[5,5,0,0]}>{data.map((d,i)=><Cell key={i} fill={d.burnRate>150000?T.rd:d.burnRate>100000?T.am:T.gn} opacity={0.8}/>)}</Bar>
          </BarChart>
        </CP>
      </div>
    </div>
  );
}

/* ═══════════════════════════════════════════════════════════════════
   TAB: COSTS
   ═══════════════════════════════════════════════════════════════════ */
function CostTab({data}){
  const dd=data.map(d=>({month:d.month,"R&D":d.lab["R&D"]+d.vd["R&D"],"S&M":d.lab["S&M"]+d.vd["S&M"],"G&A":d.lab["G&A"]+d.vd["G&A"],"Training":d.lab["Training"]+d.vd["Training"]}));
  const an={"R&D":0,"S&M":0,"G&A":0,"Training":0};dd.forEach(d=>Object.keys(an).forEach(k=>an[k]+=d[k]));
  const pd=Object.entries(an).map(([name,value])=>({name,value:Math.round(value)}));const PC=[T.ac,T.pk,T.tl,T.am];
  return(
    <div style={{display:"flex",flexDirection:"column",gap:14}}>
      <div style={{display:"grid",gridTemplateColumns:"repeat(4,1fr)",gap:12}}>
        {Object.entries(an).map(([dept,val],i)=><KPI key={dept} icon={[Briefcase,Users,Building2,FileText][i]} label={dept} value={fmt(val)} sub="Annual" color={PC[i]} dl={i*50}/>)}
      </div>
      <div style={{display:"grid",gridTemplateColumns:"2fr 1fr",gap:14}}>
        <CP title="Monthly by Department" icon={BarChart3} h={300}>
          <BarChart data={dd}><CartesianGrid strokeDasharray="3 3" stroke={gs} vertical={false}/><XAxis dataKey="month" tick={at} axisLine={false} tickLine={false}/><YAxis tick={at} axisLine={false} tickLine={false} tickFormatter={fmt}/><Tooltip content={<CTT/>}/><Legend wrapperStyle={{fontSize:11,color:T.txD}}/>
            <Bar dataKey="R&D" stackId="a" fill={T.ac}/><Bar dataKey="S&M" stackId="a" fill={T.pk}/><Bar dataKey="G&A" stackId="a" fill={T.tl}/><Bar dataKey="Training" stackId="a" fill={T.am} radius={[5,5,0,0]}/>
          </BarChart>
        </CP>
        <CP title="Annual Split" icon={PieIcon} h={300}>
          <PieChart><Pie data={pd} dataKey="value" nameKey="name" cx="50%" cy="50%" outerRadius={95} innerRadius={55} paddingAngle={3} strokeWidth={0}>{pd.map((_,i)=><Cell key={i} fill={PC[i]}/>)}</Pie>
            <Tooltip formatter={v=>fmt(v)} contentStyle={{background:T.bgCard,border:`1px solid ${T.bd}`,borderRadius:10,fontSize:12}}/><Legend wrapperStyle={{fontSize:11,color:T.txD}}/>
          </PieChart>
        </CP>
      </div>
      <CP title="Labor vs Vendor" icon={Users} h={240}>
        <BarChart data={data.map(d=>({month:d.month,Labor:Object.values(d.lab).reduce((a,b)=>a+b,0),Vendor:Object.values(d.vd).reduce((a,b)=>a+b,0)}))}><CartesianGrid strokeDasharray="3 3" stroke={gs} vertical={false}/><XAxis dataKey="month" tick={at} axisLine={false} tickLine={false}/><YAxis tick={at} axisLine={false} tickLine={false} tickFormatter={fmt}/><Tooltip content={<CTT/>}/><Legend wrapperStyle={{fontSize:11,color:T.txD}}/>
          <Bar dataKey="Labor" fill={T.ac} radius={[5,5,0,0]} opacity={0.85}/><Bar dataKey="Vendor" fill={T.am} radius={[5,5,0,0]} opacity={0.85}/>
        </BarChart>
      </CP>
    </div>
  );
}

/* ═══════════════════════════════════════════════════════════════════
   TAB: PIPELINE
   ═══════════════════════════════════════════════════════════════════ */
function PipeTab(){
  const[hr,setHr]=useState(null);
  const bI={},bC={};CON.forEach(c=>{const wv=c.ch!==null?c.v*c.ch:0;if(!bI[c.ind])bI[c.ind]={total:0,weighted:0,count:0};bI[c.ind].total+=c.v;bI[c.ind].weighted+=wv;bI[c.ind].count++;if(!bC[c.co])bC[c.co]={total:0,weighted:0,count:0};bC[c.co].total+=c.v;bC[c.co].weighted+=wv;bC[c.co].count++});
  const tP=CON.reduce((s,c)=>s+c.v,0),tW=CON.reduce((s,c)=>s+c.v*(c.ch||0),0);
  const iD=Object.entries(bI).map(([k,v])=>({name:k,...v})).sort((a,b)=>b.weighted-a.weighted);
  const tC=Object.entries(bC).sort((a,b)=>b[1].weighted-a[1].weighted).slice(0,8).map(([k,v])=>({name:k,...v}));
  const ic={Government:T.ac,Enterprise:T.pk,Academy:T.gn};
  return(
    <div style={{display:"flex",flexDirection:"column",gap:14}}>
      <div style={{display:"grid",gridTemplateColumns:"repeat(3,1fr)",gap:12}}>
        <KPI icon={Target} label="Total Pipeline" value={fmt(tP)} sub={`${CON.length} deals`} color={T.ac}/>
        <KPI icon={Zap} label="Expected Value" value={fmt(tW)} sub="Weighted" color={T.gn}/>
        <KPI icon={Percent} label="Conversion" value={fmtP(tW/tP*100)} sub="Weighted/Total" color={T.am}/>
      </div>
      <div style={{display:"grid",gridTemplateColumns:"1fr 1fr",gap:14}}>
        <CP title="By Industry" icon={Building2} h={220}>
          <BarChart data={iD} layout="vertical" margin={{left:10}}><CartesianGrid strokeDasharray="3 3" stroke={gs} horizontal={false}/><XAxis type="number" tick={at} axisLine={false} tickLine={false} tickFormatter={fmt}/><YAxis dataKey="name" type="category" tick={{...at,fontSize:11}} width={75} axisLine={false} tickLine={false}/><Tooltip content={<CTT/>}/>
            <Bar dataKey="total" name="Total" fill={T.ac} opacity={0.25} radius={[0,4,4,0]}/><Bar dataKey="weighted" name="Weighted" fill={T.ac} radius={[0,4,4,0]}/>
          </BarChart>
        </CP>
        <CP title="Top Countries" icon={Globe} h={220}>
          <BarChart data={tC} layout="vertical" margin={{left:10}}><CartesianGrid strokeDasharray="3 3" stroke={gs} horizontal={false}/><XAxis type="number" tick={at} axisLine={false} tickLine={false} tickFormatter={fmt}/><YAxis dataKey="name" type="category" tick={{...at,fontSize:11}} width={75} axisLine={false} tickLine={false}/><Tooltip content={<CTT/>}/>
            <Bar dataKey="weighted" name="Expected" fill={T.gn} radius={[0,5,5,0]}/>
          </BarChart>
        </CP>
      </div>
      <GC s={{padding:0}}>
        <div style={{padding:"16px 20px 12px",borderBottom:`1px solid ${T.bd}`,display:"flex",alignItems:"center",gap:8}}><FileText size={14} color={T.acL}/><span style={{fontSize:13,fontWeight:700,color:T.tx}}>Deal Pipeline</span><span style={{fontSize:11,color:T.txM,marginLeft:"auto"}}>{CON.length} contracts</span></div>
        <div style={{overflowX:"auto"}}>
          <table style={{width:"100%",borderCollapse:"collapse"}}>
            <thead><tr style={{borderBottom:`1px solid ${T.bd}`}}>{["Client","Country","Industry","Value","Chance","Expected","DSO","Pay Mo."].map(h=><th key={h} style={{textAlign:"left",padding:"10px 14px",fontSize:10,fontWeight:700,textTransform:"uppercase",letterSpacing:1,color:T.txM}}>{h}</th>)}</tr></thead>
            <tbody>{CON.map((c,i)=>(
              <tr key={c.id} onMouseEnter={()=>setHr(i)} onMouseLeave={()=>setHr(null)} style={{borderBottom:`1px solid ${T.bd}`,background:hr===i?T.bgHover:"transparent",transition:"background 0.15s"}}>
                <td style={{padding:"10px 14px",fontSize:12,fontWeight:600,color:T.tx}}>{c.cl}</td>
                <td style={{padding:"10px 14px",fontSize:12,color:T.txD}}>{c.co}</td>
                <td style={{padding:"10px 14px"}}><span style={{padding:"3px 10px",borderRadius:20,fontSize:10,fontWeight:700,background:`${ic[c.ind]||T.txM}18`,color:ic[c.ind]||T.txD}}>{c.ind}</span></td>
                <td style={{padding:"10px 14px",fontSize:12,fontWeight:700,color:T.tx,fontFamily:T.fm}}>{fmt(c.v)}</td>
                <td style={{padding:"10px 14px"}}>{c.ch!==null?<div style={{display:"flex",alignItems:"center",gap:6}}><div style={{width:40,height:4,borderRadius:2,background:T.bgIn,overflow:"hidden"}}><div style={{width:`${c.ch*100}%`,height:"100%",borderRadius:2,background:c.ch>=0.75?T.gn:c.ch>=0.5?T.am:T.rd}}/></div><span style={{fontSize:11,fontWeight:700,color:c.ch>=0.75?T.gn:c.ch>=0.5?T.am:T.rd,fontFamily:T.fm}}>{(c.ch*100).toFixed(0)}%</span></div>:<span style={{fontSize:11,color:T.txM}}>—</span>}</td>
                <td style={{padding:"10px 14px",fontSize:12,fontWeight:700,color:T.acL,fontFamily:T.fm}}>{fmt(c.v*(c.ch||0))}</td>
                <td style={{padding:"10px 14px",fontSize:11,color:T.txD,fontFamily:T.fm}}>{c.dso}d</td>
                <td style={{padding:"10px 14px",fontSize:11,color:T.txD,fontFamily:T.fm}}>{c.pm}</td>
              </tr>
            ))}</tbody>
          </table>
        </div>
      </GC>
    </div>
  );
}

/* ═══════════════════════════════════════════════════════════════════
   TAB: SCENARIO
   ═══════════════════════════════════════════════════════════════════ */
function ScenTab({delay,setDelay,ghosts,setGhosts,gS,setGS}){
  const base=useMemo(()=>compute([],0,true),[]);
  const gl=useMemo(()=>Array.from({length:ghosts},(_,i)=>({id:`g${i}`,n:`Ghost ${i+1}`,d:"R&D",g:gS,h:"2026-01-01",t:null})),[ghosts,gS]);
  const sc=useMemo(()=>compute(gl,delay,true),[gl,delay]);
  const cp=ML.map((_,i)=>({month:base[i].month,"Base Burn":base[i].totalExp,"Scenario Burn":sc[i].totalExp,"Base Cash":base[i].cumCash,"Scenario Cash":sc[i].cumCash}));
  const bd=sc.reduce((s,d)=>s+d.totalExp,0)-base.reduce((s,d)=>s+d.totalExp,0);
  const cd=sc[11].cumCash-base[11].cumCash;
  return(
    <div style={{display:"flex",flexDirection:"column",gap:14}}>
      <GC s={{padding:24}} glow={`0 0 40px ${T.acG}`}>
        <div style={{display:"flex",alignItems:"center",gap:8,marginBottom:18}}><SlidersHorizontal size={16} color={T.acL}/><span style={{fontSize:15,fontWeight:800,color:T.tx}}>Scenario Controls</span></div>
        <div style={{display:"grid",gridTemplateColumns:"1fr 1fr 1fr",gap:24}}>
          <RS icon={Clock} label="Sales Delay" value={delay} onChange={setDelay} min={0} max={180} step={15} unit=" days" color={T.am}/>
          <RS icon={Ghost} label="Ghost Hires" value={ghosts} onChange={setGhosts} min={0} max={10} unit="" color={T.pu}/>
          <RS icon={DollarSign} label="Salary Each" value={gS} onChange={setGS} min={5000} max={30000} step={1000} unit="" color={T.cy}/>
        </div>
      </GC>
      <div style={{display:"grid",gridTemplateColumns:"repeat(4,1fr)",gap:12}}>
        <KPI icon={Users} label="New Headcount" value={`+${ghosts}`} sub={`${fmt(gS)} × 1.35`} color={T.pu}/>
        <KPI icon={Activity} label="Extra Burn/mo" value={fmt(ghosts*gS*ECF)} sub="Labor added" color={T.rd}/>
        <KPI icon={Wallet} label="Burn Delta" value={fmt(bd)} sub="vs Base" color={bd>0?T.rd:T.gn}/>
        <KPI icon={CreditCard} label="End Cash" value={fmt(sc[11].cumCash)} sub={`Base: ${fmt(base[11].cumCash)}`} color={T.ac} delta={base[11].cumCash!==0?cd/Math.abs(base[11].cumCash)*100:0}/>
      </div>
      <div style={{display:"grid",gridTemplateColumns:"1fr 1fr",gap:14}}>
        <CP title="Burn Comparison" icon={Activity} h={280}>
          <BarChart data={cp}><CartesianGrid strokeDasharray="3 3" stroke={gs} vertical={false}/><XAxis dataKey="month" tick={at} axisLine={false} tickLine={false}/><YAxis tick={at} axisLine={false} tickLine={false} tickFormatter={fmt}/><Tooltip content={<CTT/>}/><Legend wrapperStyle={{fontSize:11,color:T.txD}}/>
            <Bar dataKey="Base Burn" fill={T.ac} opacity={0.4} radius={[4,4,0,0]}/><Bar dataKey="Scenario Burn" fill={T.rd} opacity={0.8} radius={[4,4,0,0]}/>
          </BarChart>
        </CP>
        <CP title="Cash Trajectory" icon={TrendingUp} h={280}>
          <LineChart data={cp}><CartesianGrid strokeDasharray="3 3" stroke={gs} vertical={false}/><XAxis dataKey="month" tick={at} axisLine={false} tickLine={false}/><YAxis tick={at} axisLine={false} tickLine={false} tickFormatter={fmt}/><Tooltip content={<CTT/>}/><Legend wrapperStyle={{fontSize:11,color:T.txD}}/>
            <Line dataKey="Base Cash" stroke={T.ac} strokeWidth={2.5} dot={false} type="monotone"/><Line dataKey="Scenario Cash" stroke={T.rd} strokeWidth={2.5} strokeDasharray="8 4" dot={false} type="monotone"/>
            <ReferenceLine y={0} stroke={T.txM} strokeDasharray="4 4"/>
          </LineChart>
        </CP>
      </div>
    </div>
  );
}

/* ═══════════════════════════════════════════════════════════════════
   MAIN
   ═══════════════════════════════════════════════════════════════════ */
export default function CFODashboard(){
  const[tab,setTab]=useState("dash");
  const[col,setCol]=useState(false);
  const[w,setW]=useState(true);
  const[delay,setDelay]=useState(0);
  const[ghosts,setGhosts]=useState(0);
  const[gS,setGS]=useState(15000);
  const data=useMemo(()=>compute([],0,w),[w]);
  return(
    <div style={{display:"flex",fontFamily:T.f,background:T.bg,color:T.tx,minHeight:"100vh"}}>
      <style>{`
        @import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;500;600;700;800;900&family=JetBrains+Mono:wght@400;500;600;700;800&display=swap');
        *{box-sizing:border-box;margin:0;padding:0}
        ::-webkit-scrollbar{width:6px;height:6px}::-webkit-scrollbar-track{background:transparent}::-webkit-scrollbar-thumb{background:${T.bdL};border-radius:3px}
        input[type="range"]{-webkit-appearance:none;appearance:none;background:${T.bd};border-radius:4px;outline:none}
        input[type="range"]::-webkit-slider-thumb{-webkit-appearance:none;width:16px;height:16px;border-radius:50%;cursor:pointer;border:2px solid #fff;box-shadow:0 1px 4px rgba(0,0,0,0.4)}
        @keyframes fsu{from{opacity:0;transform:translateY(12px)}to{opacity:1;transform:translateY(0)}}
      `}</style>
      <Sidebar tab={tab} setTab={setTab} col={col} setCol={setCol}/>
      <div style={{flex:1,display:"flex",flexDirection:"column",minWidth:0}}>
        <Header data={data} w={w} setW={setW}/>
        <div style={{flex:1,overflow:"auto",padding:20}}>
          {tab==="dash"&&<DashTab data={data}/>}
          {tab==="costs"&&<CostTab data={data}/>}
          {tab==="pipeline"&&<PipeTab/>}
          {tab==="scenario"&&<ScenTab delay={delay} setDelay={setDelay} ghosts={ghosts} setGhosts={setGhosts} gS={gS} setGS={setGS}/>}
        </div>
      </div>
    </div>
  );
}
