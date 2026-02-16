import { useState, useEffect, createContext, useContext } from "react";
import { LineChart, Line, BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Cell, Legend } from "recharts";

const TX = {
  fr: {
    title:"AX5 UrbanIA",subtitle:"Sécurité prédictive urbaine",
    tabs:{overview:"Vue d'ensemble",couche1:"C1 CNESST",couche2:"C2 SAAQ",zones:"Zones MTL",simulator:"Simulateur"},
    sourcesActive:"sources actives",
    lesionsConst:"Lésions Construction",zoneWorkSAAQ:"Zone travaux SAAQ",urbanRisk:"Risque urbain",
    tmsConst:"TMS Construction",pedMTL:"Piétons MTL",cycMTL:"Cyclistes MTL",
    y7:"7 ans CNESST",y3:"3 ans (2020-22)",urbanComp:"à composante urbaine",
    rise79:"+79% en 7 ans",inWZ:"en zone travaux",
    trendTitle:"Lésions Construction — Tendance 7 ans",accByRegion:"Accidents zone travaux par région",
    sourcesTitle:"Sources de données — 9 sources, 3 couches",
    onSite:"SUR le chantier",inTransit:"EN TRANSIT",around:"AUTOUR",
    c1Title:"CNESST — Lésions professionnelles Construction",c1Sub:"54 403 lésions | 2016-2022 | SCIAN 23",
    tot7y:"Total 7 ans",growth:"Croissance",tms:"TMS",urbanRL:"Risque urbain",
    scian:"Construction SCIAN 23",g1622:"2016 → 2022",tmsR:"26.0% — hausse +79%",uComp:"51.6% composante urbaine",
    genreTitle:"Genres d'accident — Score risque",scoreGenre:"Score risque par genre",
    annTrends:"Tendances annuelles — Construction",
    lesTotal:"Lésions totales",machine:"Machine",psycho:"Psychologiques",
    hitObj:"Frappé par objet",bodyR:"Réaction du corps",exEff:"Effort excessif",
    fallLow:"Chute niv. inf.",fallSame:"Chute même niv.",caught:"Coincé/écrasé",
    c2Title:"SAAQ — Accidents en zone de travaux routiers",c2Sub:"8 173 accidents | 2020-2022",
    totWZ:"Total zone travaux",peds:"Piétons",cycs:"Cyclistes",
    fatal:"Mortels/graves",heavy:"Véh. lourds",
    ofTot:"du total SAAQ",inclMTL:"dont {n} à MTL",wzPct:"zone travaux",involved:"impliqués",
    byRegion:"Répartition par région",hourDist:"Distribution horaire — Heures de pointe",
    peakH:"71.5% des accidents entre 8h et 20h — heures d'activité chantiers",
    mtlTitle:"Montréal — 2 995 accidents zone travaux (36.6%)",
    pedML:"Piétons MTL",cycML:"Cyclistes MTL",fatML:"Mortels MTL",qcSh:"Part du Québec",
    acc:"Accidents",
    zonesTitle:"Zones urbaines Montréal — Score risque composite",pilot:"Pilote MTL",
    actSites:"Chantiers actifs",pedDay:"Flux piétons/jour",hitlReq:"HITL requis",
    yes:"OUI",no:"Non",
    sevN:"Normal",sevA:"Attention",sevH:"Élevé",sevC:"Critique",
    simTitle:"Simulateur de score — What-If",
    modF:"Facteurs de modulation",simRes:"Résultat du score simulé",
    weather:"Météo",coact:"Coactivité",
    wFine:"Beau temps",wRain:"Pluie",wIce:"Verglas/tempête",
    cIso:"Chantier isolé",c23:"2-3 chantiers adjacents",c4p:"4+ chantiers (critique)",
    formula:"FORMULE",hitlW:"⚠️ HITL OBLIGATOIRE — Validation humaine requise (Charte AgenticX5)",
    profAlert:"Profils alertés",
    allP:"TOUS (9/9)",orangeP:"Piéton, Cycliste, PMR, Coordonnateur",yellowP:"Piéton, Cycliste, Coordonnateur",greenP:"Coordonnateur uniquement",
    foot1:"GenAISafety / Preventera — AX5 UrbanIA v2.0",foot2:"Primauté de la vie | HITL obligatoire | Charte AgenticX5",
    sCIFS:"Entraves CIFS",sPed:"Comptages piétons",sBike:"Comptages vélos",sBT:"Capteurs Bluetooth",
    sAGIR:"Permis AGIR",sMet:"Météo Canada",sBixi:"Stations Bixi",sCN:"CNESST Lésions",sSQ:"SAAQ Zone travaux",
  },
  en: {
    title:"AX5 UrbanIA",subtitle:"Predictive urban safety",
    tabs:{overview:"Overview",couche1:"L1 CNESST",couche2:"L2 SAAQ",zones:"MTL Zones",simulator:"Simulator"},
    sourcesActive:"active sources",
    lesionsConst:"Construction Injuries",zoneWorkSAAQ:"SAAQ Work Zones",urbanRisk:"Urban Risk",
    tmsConst:"MSD Construction",pedMTL:"Pedestrians MTL",cycMTL:"Cyclists MTL",
    y7:"7 yrs CNESST",y3:"3 yrs (2020-22)",urbanComp:"urban component",
    rise79:"+79% over 7 yrs",inWZ:"in work zones",
    trendTitle:"Construction Injuries — 7-Year Trend",accByRegion:"Work zone accidents by region",
    sourcesTitle:"Data sources — 9 sources, 3 layers",
    onSite:"ON the site",inTransit:"IN TRANSIT",around:"AROUND",
    c1Title:"CNESST — Construction Occupational Injuries",c1Sub:"54,403 injuries | 2016-2022 | NAICS 23",
    tot7y:"Total 7 yrs",growth:"Growth",tms:"MSD",urbanRL:"Urban risk",
    scian:"Construction NAICS 23",g1622:"2016 → 2022",tmsR:"26.0% — up +79%",uComp:"51.6% urban component",
    genreTitle:"Accident types — Risk score",scoreGenre:"Urban risk score by type",
    annTrends:"Annual trends — Construction",
    lesTotal:"Total injuries",machine:"Machinery",psycho:"Psychological",
    hitObj:"Struck by object",bodyR:"Body reaction",exEff:"Excessive effort",
    fallLow:"Fall to lower level",fallSame:"Fall same level",caught:"Caught/crushed",
    c2Title:"SAAQ — Road Work Zone Accidents",c2Sub:"8,173 accidents | 2020-2022",
    totWZ:"Total work zone",peds:"Pedestrians",cycs:"Cyclists",
    fatal:"Fatal/serious",heavy:"Heavy vehicles",
    ofTot:"of total SAAQ",inclMTL:"incl. {n} in MTL",wzPct:"work zone",involved:"involved",
    byRegion:"Distribution by region",hourDist:"Hourly distribution — Peak hours",
    peakH:"71.5% of accidents between 8am-8pm — site activity hours",
    mtlTitle:"Montreal — 2,995 work zone accidents (36.6%)",
    pedML:"Pedestrians MTL",cycML:"Cyclists MTL",fatML:"Fatal MTL",qcSh:"Share of Quebec",
    acc:"Accidents",
    zonesTitle:"Montreal urban zones — Composite risk score",pilot:"MTL Pilot",
    actSites:"Active sites",pedDay:"Ped. flux/day",hitlReq:"HITL required",
    yes:"YES",no:"No",
    sevN:"Normal",sevA:"Caution",sevH:"High",sevC:"Critical",
    simTitle:"Score simulator — What-If",
    modF:"Modulation factors",simRes:"Simulated score result",
    weather:"Weather",coact:"Coactivity",
    wFine:"Clear",wRain:"Rain",wIce:"Ice/storm",
    cIso:"Isolated site",c23:"2-3 adjacent sites",c4p:"4+ sites (critical)",
    formula:"FORMULA",hitlW:"⚠️ HITL REQUIRED — Human validation mandatory (AgenticX5 Charter)",
    profAlert:"Profiles alerted",
    allP:"ALL (9/9)",orangeP:"Pedestrian, Cyclist, PMR, Coordinator",yellowP:"Pedestrian, Cyclist, Coordinator",greenP:"Coordinator only",
    foot1:"GenAISafety / Preventera — AX5 UrbanIA v2.0",foot2:"Life primacy | HITL mandatory | AgenticX5 Charter",
    sCIFS:"CIFS Obstructions",sPed:"Pedestrian counts",sBike:"Bike counts",sBT:"Bluetooth sensors",
    sAGIR:"AGIR Permits",sMet:"Weather Canada",sBixi:"Bixi Stations",sCN:"CNESST Injuries",sSQ:"SAAQ Work zones",
  },
};
const LCtx=createContext("fr");const useT=()=>TX[useContext(LCtx)];

const CNESST_Y=[{year:"2016",lesions:6207,tms:1446,machine:322,psy:32},{year:"2017",lesions:6592,tms:1682,machine:342,psy:26},{year:"2018",lesions:7443,tms:1761,machine:326,psy:38},{year:"2019",lesions:8234,tms:2073,machine:368,psy:52},{year:"2020",lesions:7599,tms:2056,machine:490,psy:48},{year:"2021",lesions:8826,tms:2553,machine:501,psy:52},{year:"2022",lesions:9502,tms:2583,machine:517,psy:57}];
const SAAQ_WZ=[{region:"Montréal",accidents:2995,pietons:108,cyclistes:91},{region:"Montérégie",accidents:1259,pietons:22,cyclistes:10},{region:"Cap.-Nat.",accidents:1193,pietons:19,cyclistes:8},{region:"Ch.-App.",accidents:382,pietons:8,cyclistes:3},{region:"Laval",accidents:358,pietons:12,cyclistes:4},{region:"Laurentides",accidents:352,pietons:6,cyclistes:2}];
const SAAQ_H=[{hour:"00-04h",count:481,pct:5.9},{hour:"04-08h",count:826,pct:10.1},{hour:"08-12h",count:1882,pct:23.0},{hour:"12-16h",count:2296,pct:28.1},{hour:"16-20h",count:1664,pct:20.4},{hour:"20-24h",count:999,pct:12.2}];
const ZONES=[{id:"VM-01",name:"Ville-Marie Centre",score:78,sev:"orange",ch:12,flux:4200},{id:"PM-01",name:"Plateau Mont-Royal",score:62,sev:"yellow",ch:8,flux:3100},{id:"RO-01",name:"Rosemont",score:45,sev:"yellow",ch:5,flux:1800},{id:"CD-01",name:"Côte-des-Neiges",score:71,sev:"orange",ch:9,flux:2900},{id:"SW-01",name:{fr:"Sud-Ouest",en:"Southwest"},score:38,sev:"green",ch:3,flux:1200},{id:"ME-01",name:"Mercier-Est",score:29,sev:"green",ch:2,flux:800}];

const K={bg:"#0a0a12",card:"#12121e",brd:"#2a2a3e",purple:"#9333ea",teal:"#14b8a6",red:"#ef4444",orange:"#f97316",yellow:"#f59e0b",green:"#10b981",text:"#e8e8f0",gray:"#8888a0",dim:"#4a4a6a",dark:"#1a1a2e"};

const Card=({title,children,tag,style={}})=>(<div style={{background:K.card,border:`1px solid ${K.brd}`,borderRadius:12,padding:20,...style}}>{(title||tag)&&<div style={{display:"flex",justifyContent:"space-between",alignItems:"center",marginBottom:14}}>{title&&<div style={{fontSize:13,fontWeight:700,color:K.text}}>{title}</div>}{tag}</div>}{children}</div>);
const Met=({label,value,sub,color=K.text,trend})=>(<div style={{textAlign:"center"}}><div style={{fontSize:11,color:K.gray,textTransform:"uppercase",letterSpacing:1,marginBottom:4}}>{label}</div><div style={{fontSize:28,fontWeight:900,color,fontFamily:"monospace"}}>{value}</div>{sub&&<div style={{fontSize:11,color:trend==="up"?K.red:trend==="down"?K.green:K.gray,marginTop:2}}>{sub}</div>}</div>);
const SevB=({severity})=>{const t=useT();const c={green:K.green,yellow:K.yellow,orange:K.orange,red:K.red};const l={green:t.sevN,yellow:t.sevA,orange:t.sevH,red:t.sevC};return(<span style={{display:"inline-flex",alignItems:"center",gap:4,padding:"2px 8px",borderRadius:100,fontSize:10,fontWeight:700,textTransform:"uppercase",background:`${c[severity]}20`,color:c[severity]}}><span style={{width:6,height:6,borderRadius:"50%",background:c[severity]}}/>{l[severity]}</span>);};
const CTag=({n})=>{const c={1:{bg:"#3b82f620",cl:"#3b82f6"},2:{bg:"#f59e0b20",cl:"#f59e0b"},3:{bg:"#9333ea20",cl:"#9333ea"}};return<span style={{fontSize:9,padding:"1px 6px",borderRadius:4,background:c[n].bg,color:c[n].cl,fontWeight:700}}>C{n}</span>;};
const CTip=({active,payload,label})=>{if(!active||!payload?.length)return null;return(<div style={{background:K.dark,border:`1px solid ${K.brd}`,borderRadius:8,padding:"8px 12px",fontSize:12}}><div style={{fontWeight:700,marginBottom:4}}>{label}</div>{payload.map((p,i)=><div key={i} style={{color:p.color}}>{p.name}: {p.value?.toLocaleString()}</div>)}</div>);};

const useGenres=()=>{const t=useT();return[{name:t.hitObj,value:7847,score:9,color:K.red},{name:t.bodyR,value:8384,score:2,color:"#64748b"},{name:t.exEff,value:8069,score:2,color:"#64748b"},{name:t.fallLow,value:5815,score:7,color:K.yellow},{name:t.fallSame,value:4528,score:4,color:"#94a3b8"},{name:t.caught,value:3022,score:6,color:K.orange}];};
const useSrc=()=>{const t=useT();return[{id:1,name:t.sCIFS,co:3,st:"planned",ic:"🚧"},{id:2,name:t.sPed,co:3,st:"planned",ic:"👤"},{id:3,name:t.sBike,co:3,st:"planned",ic:"🚲"},{id:4,name:t.sBT,co:3,st:"planned",ic:"📡"},{id:5,name:t.sAGIR,co:3,st:"planned",ic:"📋"},{id:6,name:t.sMet,co:3,st:"planned",ic:"🌤"},{id:7,name:t.sBixi,co:3,st:"planned",ic:"🚴"},{id:8,name:t.sCN,co:1,st:"active",ic:"🏗",rec:"54 403"},{id:9,name:t.sSQ,co:2,st:"active",ic:"🚛",rec:"8 173"}];};

const TabOV=()=>{const t=useT();const src=useSrc();return(<><div style={{display:"grid",gridTemplateColumns:"repeat(6,1fr)",gap:16,marginBottom:24}}><Card><Met label={t.lesionsConst} value="54 403" sub={t.y7}/></Card><Card><Met label={t.zoneWorkSAAQ} value="8 173" sub={t.y3}/></Card><Card><Met label={t.urbanRisk} value="51.6%" sub={t.urbanComp} color={K.red}/></Card><Card><Met label={t.tmsConst} value="26.0%" sub={t.rise79} color={K.yellow} trend="up"/></Card><Card><Met label={t.pedMTL} value="108" sub={t.inWZ} color={K.red}/></Card><Card><Met label={t.cycMTL} value="91" sub={t.inWZ} color={K.orange}/></Card></div>
  <div style={{display:"grid",gridTemplateColumns:"1fr 1fr",gap:16,marginBottom:24}}>
    <Card title={t.trendTitle} tag={<CTag n={1}/>}><ResponsiveContainer width="100%" height={220}><LineChart data={CNESST_Y}><XAxis dataKey="year" stroke={K.dim} fontSize={11}/><YAxis stroke={K.dim} fontSize={11}/><Tooltip content={<CTip/>}/><Line type="monotone" dataKey="lesions" stroke={K.purple} strokeWidth={2.5} dot={{fill:K.purple,r:4}} name={t.lesTotal}/><Line type="monotone" dataKey="tms" stroke={K.yellow} strokeWidth={2} dot={{fill:K.yellow,r:3}} name={t.tms}/></LineChart></ResponsiveContainer></Card>
    <Card title={t.accByRegion} tag={<CTag n={2}/>}><ResponsiveContainer width="100%" height={220}><BarChart data={SAAQ_WZ} layout="vertical"><XAxis type="number" stroke={K.dim} fontSize={11}/><YAxis type="category" dataKey="region" stroke={K.dim} fontSize={10} width={80}/><Tooltip content={<CTip/>}/><Bar dataKey="accidents" fill={K.teal} radius={[0,4,4,0]} name={t.acc}/><Bar dataKey="pietons" fill={K.red} radius={[0,4,4,0]} name={t.peds}/></BarChart></ResponsiveContainer></Card>
  </div>
  <Card title={t.sourcesTitle}><div style={{display:"grid",gridTemplateColumns:"repeat(3,1fr)",gap:12}}>{[1,2,3].map(co=>(<div key={co}><div style={{fontSize:11,fontWeight:700,color:K.gray,marginBottom:8,display:"flex",alignItems:"center",gap:6}}><CTag n={co}/>{co===1?t.onSite:co===2?t.inTransit:t.around}</div>{src.filter(s=>s.co===co).map(s=>(<div key={s.id} style={{display:"flex",alignItems:"center",justifyContent:"space-between",padding:"6px 10px",borderRadius:6,marginBottom:4,background:s.st==="active"?"#10b98110":K.dark,border:`1px solid ${s.st==="active"?"#10b98130":K.brd}`}}><div style={{display:"flex",alignItems:"center",gap:8,fontSize:12}}><span>{s.ic}</span><span>{s.name}</span></div><div style={{display:"flex",alignItems:"center",gap:6}}>{s.rec&&<span style={{fontSize:10,color:K.teal,fontFamily:"monospace"}}>{s.rec}</span>}<span style={{width:6,height:6,borderRadius:"50%",background:s.st==="active"?K.green:K.dim}}/></div></div>))}</div>))}</div></Card></>);};

const TabC1=()=>{const t=useT();const g=useGenres();return(<><div style={{marginBottom:16,display:"flex",alignItems:"center",gap:8}}><CTag n={1}/><span style={{fontSize:18,fontWeight:800}}>{t.c1Title}</span><span style={{fontSize:12,color:K.gray}}>{t.c1Sub}</span></div>
  <div style={{display:"grid",gridTemplateColumns:"repeat(4,1fr)",gap:16,marginBottom:24}}><Card><Met label={t.tot7y} value="54 403" sub={t.scian} color={K.purple}/></Card><Card><Met label={t.growth} value="+53.1%" sub={t.g1622} color={K.red} trend="up"/></Card><Card><Met label={t.tms} value="14 154" sub={t.tmsR} color={K.yellow} trend="up"/></Card><Card><Met label={t.urbanRL} value="28 093" sub={t.uComp} color={K.red}/></Card></div>
  <div style={{display:"grid",gridTemplateColumns:"2fr 1fr",gap:16,marginBottom:24}}>
    <Card title={t.genreTitle}><ResponsiveContainer width="100%" height={260}><BarChart data={g} layout="vertical"><XAxis type="number" stroke={K.dim} fontSize={11}/><YAxis type="category" dataKey="name" stroke={K.dim} fontSize={10} width={120}/><Tooltip content={<CTip/>}/><Bar dataKey="value" name={t.lesTotal} radius={[0,4,4,0]}>{g.map((d,i)=><Cell key={i} fill={d.color}/>)}</Bar></BarChart></ResponsiveContainer></Card>
    <Card title={t.scoreGenre}>{[...g].sort((a,b)=>b.score-a.score).map((x,i)=>(<div key={i} style={{display:"flex",alignItems:"center",gap:8,marginBottom:8}}><div style={{flex:1,fontSize:11,color:K.gray}}>{x.name}</div><div style={{width:80,height:6,borderRadius:3,background:K.dark,overflow:"hidden"}}><div style={{width:`${x.score*10}%`,height:"100%",borderRadius:3,background:x.score>=7?K.red:x.score>=5?K.yellow:"#64748b"}}/></div><div style={{fontSize:12,fontWeight:700,fontFamily:"monospace",width:24,textAlign:"right",color:x.score>=7?K.red:x.score>=5?K.yellow:"#64748b"}}>{x.score}</div></div>))}</Card>
  </div>
  <Card title={t.annTrends}><ResponsiveContainer width="100%" height={240}><LineChart data={CNESST_Y}><XAxis dataKey="year" stroke={K.dim} fontSize={11}/><YAxis stroke={K.dim} fontSize={11}/><Tooltip content={<CTip/>}/><Line type="monotone" dataKey="lesions" stroke={K.purple} strokeWidth={2.5} dot={{r:4}} name={t.lesTotal}/><Line type="monotone" dataKey="tms" stroke={K.yellow} strokeWidth={2} dot={{r:3}} name={t.tms}/><Line type="monotone" dataKey="machine" stroke={K.red} strokeWidth={1.5} dot={{r:3}} name={t.machine}/><Line type="monotone" dataKey="psy" stroke={K.teal} strokeWidth={1.5} dot={{r:3}} name={t.psycho}/><Legend wrapperStyle={{fontSize:11}}/></LineChart></ResponsiveContainer></Card></>);};

const TabC2=()=>{const t=useT();return(<><div style={{marginBottom:16,display:"flex",alignItems:"center",gap:8}}><CTag n={2}/><span style={{fontSize:18,fontWeight:800}}>{t.c2Title}</span><span style={{fontSize:12,color:K.gray}}>{t.c2Sub}</span></div>
  <div style={{display:"grid",gridTemplateColumns:"repeat(5,1fr)",gap:16,marginBottom:24}}><Card><Met label={t.totWZ} value="8 173" sub={"2.7% "+t.ofTot} color={K.teal}/></Card><Card><Met label={t.peds} value="190" sub={t.inclMTL.replace("{n}","108")} color={K.red}/></Card><Card><Met label={t.cycs} value="119" sub={t.inclMTL.replace("{n}","91")} color={K.orange}/></Card><Card><Met label={t.fatal} value="105" sub={"1.3% "+t.wzPct} color={K.red}/></Card><Card><Met label={t.heavy} value="2 250" sub={"27.5% "+t.involved} color={K.yellow}/></Card></div>
  <div style={{display:"grid",gridTemplateColumns:"1fr 1fr",gap:16,marginBottom:24}}>
    <Card title={t.byRegion}><ResponsiveContainer width="100%" height={260}><BarChart data={SAAQ_WZ}><XAxis dataKey="region" stroke={K.dim} fontSize={10}/><YAxis stroke={K.dim} fontSize={11}/><Tooltip content={<CTip/>}/><Bar dataKey="accidents" fill={K.teal} radius={[4,4,0,0]} name={t.acc}/><Bar dataKey="pietons" fill={K.red} radius={[4,4,0,0]} name={t.peds}/><Bar dataKey="cyclistes" fill={K.orange} radius={[4,4,0,0]} name={t.cycs}/></BarChart></ResponsiveContainer></Card>
    <Card title={t.hourDist}><ResponsiveContainer width="100%" height={260}><BarChart data={SAAQ_H}><XAxis dataKey="hour" stroke={K.dim} fontSize={10}/><YAxis stroke={K.dim} fontSize={11}/><Tooltip content={<CTip/>}/><Bar dataKey="count" name={t.acc} radius={[4,4,0,0]}>{SAAQ_H.map((d,i)=><Cell key={i} fill={d.pct>20?K.red:d.pct>15?K.yellow:"#64748b"}/>)}</Bar></BarChart></ResponsiveContainer><div style={{fontSize:11,color:K.yellow,marginTop:8,fontWeight:600}}>{t.peakH}</div></Card>
  </div>
  <Card title={t.mtlTitle} style={{border:`1px solid ${K.orange}30`}}><div style={{display:"grid",gridTemplateColumns:"repeat(4,1fr)",gap:24,padding:"8px 0"}}><Met label={t.pedML} value="108" color={K.red}/><Met label={t.cycML} value="91" color={K.orange}/><Met label={t.fatML} value="24" color={K.red}/><Met label={t.qcSh} value="36.6%" color={K.teal}/></div></Card></>);};

const TabZn=()=>{const t=useT();const lang=useContext(LCtx);return(<><div style={{marginBottom:16,display:"flex",alignItems:"center",gap:8}}><CTag n={3}/><span style={{fontSize:18,fontWeight:800}}>{t.zonesTitle}</span><span style={{fontSize:12,color:K.gray}}>{t.pilot}</span></div>
  <div style={{display:"grid",gridTemplateColumns:"repeat(3,1fr)",gap:16}}>{ZONES.map(z=>{const nm=typeof z.name==="object"?z.name[lang]:z.name;return(<Card key={z.id} style={{border:`1px solid ${z.sev==="orange"?K.orange+"30":z.sev==="red"?K.red+"30":K.brd}`}}>
    <div style={{display:"flex",justifyContent:"space-between",alignItems:"flex-start",marginBottom:12}}><div><div style={{fontSize:14,fontWeight:700}}>{nm}</div><div style={{fontSize:11,color:K.gray}}>{z.id}</div></div><SevB severity={z.sev}/></div>
    <div style={{display:"flex",alignItems:"center",gap:16,marginBottom:12}}>
      <div style={{position:"relative",width:64,height:64}}><svg viewBox="0 0 36 36" style={{width:64,height:64,transform:"rotate(-90deg)"}}><circle cx="18" cy="18" r="15.5" fill="none" stroke={K.dark} strokeWidth="3"/><circle cx="18" cy="18" r="15.5" fill="none" stroke={z.sev==="red"?K.red:z.sev==="orange"?K.orange:z.sev==="yellow"?K.yellow:K.green} strokeWidth="3" strokeDasharray={`${z.score} ${100-z.score}`} strokeLinecap="round"/></svg><div style={{position:"absolute",top:"50%",left:"50%",transform:"translate(-50%,-50%)",fontSize:16,fontWeight:900,fontFamily:"monospace"}}>{z.score}</div></div>
      <div style={{flex:1}}><div style={{display:"flex",justifyContent:"space-between",fontSize:11,color:K.gray,marginBottom:4}}><span>{t.actSites}</span><span style={{color:K.text,fontWeight:600}}>{z.ch}</span></div><div style={{display:"flex",justifyContent:"space-between",fontSize:11,color:K.gray,marginBottom:4}}><span>{t.pedDay}</span><span style={{color:K.text,fontWeight:600}}>{z.flux.toLocaleString()}</span></div><div style={{display:"flex",justifyContent:"space-between",fontSize:11,color:K.gray}}><span>{t.hitlReq}</span><span style={{color:(z.sev==="orange"||z.sev==="red")?K.red:K.green,fontWeight:600}}>{(z.sev==="orange"||z.sev==="red")?t.yes:t.no}</span></div></div>
    </div>
    <div style={{display:"flex",gap:2,height:4,borderRadius:2,overflow:"hidden"}}><div style={{width:"35%",background:"#3b82f6"}}/><div style={{width:"25%",background:K.yellow}}/><div style={{width:"40%",background:K.purple}}/></div>
    <div style={{display:"flex",justifyContent:"space-between",marginTop:4,fontSize:9,color:K.gray}}><span>C1 35%</span><span>C2 25%</span><span>C3 40%</span></div>
  </Card>);})}</div></>);};

const TabSim=()=>{const t=useT();const[sW,setW]=useState(1.0);const[sC,setC]=useState(1.0);const sc=Math.min(100,Math.round(72*sW*sC));const sv=sc>=85?"red":sc>=65?"orange":sc>=40?"yellow":"green";
return(<><div style={{marginBottom:16,fontSize:18,fontWeight:800}}>{t.simTitle}</div><div style={{display:"grid",gridTemplateColumns:"1fr 1fr",gap:24}}>
  <Card title={t.modF}>
    <div style={{marginBottom:20}}><div style={{display:"flex",justifyContent:"space-between",fontSize:12,marginBottom:6}}><span>{t.weather} (×{sW.toFixed(1)})</span><span style={{color:sW>1.1?K.yellow:K.gray}}>{sW<=1.0?t.wFine:sW<=1.2?t.wRain:t.wIce}</span></div><input type="range" min="1.0" max="1.5" step="0.1" value={sW} onChange={e=>setW(parseFloat(e.target.value))} style={{width:"100%",accentColor:K.purple}}/></div>
    <div style={{marginBottom:20}}><div style={{display:"flex",justifyContent:"space-between",fontSize:12,marginBottom:6}}><span>{t.coact} (×{sC.toFixed(1)})</span><span style={{color:sC>1.2?K.red:K.gray}}>{sC<=1.0?t.cIso:sC<=1.3?t.c23:t.c4p}</span></div><input type="range" min="1.0" max="1.5" step="0.1" value={sC} onChange={e=>setC(parseFloat(e.target.value))} style={{width:"100%",accentColor:K.teal}}/></div>
    <div style={{padding:16,background:K.dark,borderRadius:8,marginTop:16}}><div style={{fontSize:11,color:K.gray,marginBottom:8}}>{t.formula}</div><div style={{fontSize:13,fontFamily:"monospace",color:K.text}}>Score = (C1×0.35 + C2×0.25 + C3×0.40) × {t.weather} × {t.coact}</div><div style={{fontSize:12,fontFamily:"monospace",color:K.purple,marginTop:4}}>= 72 × {sW.toFixed(1)} × {sC.toFixed(1)} = <strong>{sc}</strong></div></div>
  </Card>
  <Card title={t.simRes}><div style={{textAlign:"center",padding:"20px 0"}}>
    <div style={{position:"relative",width:160,height:160,margin:"0 auto"}}><svg viewBox="0 0 36 36" style={{width:160,height:160,transform:"rotate(-90deg)"}}><circle cx="18" cy="18" r="15.5" fill="none" stroke={K.dark} strokeWidth="2.5"/><circle cx="18" cy="18" r="15.5" fill="none" stroke={sv==="red"?K.red:sv==="orange"?K.orange:sv==="yellow"?K.yellow:K.green} strokeWidth="2.5" strokeDasharray={`${sc} ${100-sc}`} strokeLinecap="round" style={{transition:"stroke-dasharray .5s"}}/></svg><div style={{position:"absolute",top:"50%",left:"50%",transform:"translate(-50%,-50%)",fontSize:40,fontWeight:900,fontFamily:"monospace"}}>{sc}</div></div>
    <div style={{marginTop:16}}><SevB severity={sv}/></div>
    {(sv==="orange"||sv==="red")&&<div style={{marginTop:16,padding:"10px 16px",borderRadius:8,background:`${K.red}15`,border:`1px solid ${K.red}30`,fontSize:12,color:K.red,fontWeight:600}}>{t.hitlW}</div>}
    <div style={{marginTop:16,fontSize:11,color:K.gray}}>{t.profAlert}: {sv==="red"?t.allP:sv==="orange"?t.orangeP:sv==="yellow"?t.yellowP:t.greenP}</div>
  </div></Card>
</div></>);};

const TABS=[{id:"overview",C:TabOV},{id:"couche1",C:TabC1},{id:"couche2",C:TabC2},{id:"zones",C:TabZn},{id:"simulator",C:TabSim}];

export default function UrbanIADashboard(){
  const[lang,setLang]=useState("fr");const[tab,setTab]=useState("overview");const[now,setNow]=useState(new Date());
  const t=TX[lang];useEffect(()=>{const iv=setInterval(()=>setNow(new Date()),60000);return()=>clearInterval(iv);},[]);
  const TC=TABS.find(x=>x.id===tab)?.C||TabOV;
  return(<LCtx.Provider value={lang}><div style={{minHeight:"100vh",background:K.bg,color:K.text,fontFamily:"'Segoe UI',system-ui,sans-serif"}}>
    <style>{`@keyframes pulse{0%,100%{opacity:1}50%{opacity:.4}}`}</style>
    <div style={{borderBottom:`1px solid ${K.brd}`,padding:"12px 24px",display:"flex",justifyContent:"space-between",alignItems:"center"}}>
      <div style={{display:"flex",alignItems:"center",gap:12}}><div style={{width:32,height:32,borderRadius:8,background:`linear-gradient(135deg,${K.purple},${K.teal})`,display:"flex",alignItems:"center",justifyContent:"center",fontSize:16,fontWeight:900}}>U</div><div><div style={{fontSize:15,fontWeight:800,letterSpacing:-.5}}>{t.title}</div><div style={{fontSize:10,color:K.gray}}>{t.subtitle}</div></div></div>
      <div style={{display:"flex",alignItems:"center",gap:16,fontSize:12,color:K.gray}}>
        <span style={{display:"flex",alignItems:"center",gap:4}}><span style={{width:6,height:6,borderRadius:"50%",background:K.green,animation:"pulse 2s infinite"}}/>2/9 {t.sourcesActive}</span>
        <span>{now.toLocaleDateString(lang==="fr"?"fr-CA":"en-CA")} {now.toLocaleTimeString(lang==="fr"?"fr-CA":"en-CA",{hour:"2-digit",minute:"2-digit"})}</span>
        <div style={{display:"flex",borderRadius:6,overflow:"hidden",border:`1px solid ${K.dim}`}}>{["fr","en"].map(l=>(<button key={l} onClick={()=>setLang(l)} style={{padding:"3px 10px",background:lang===l?K.purple:"transparent",color:lang===l?K.text:K.gray,border:"none",fontSize:10,fontWeight:700,cursor:"pointer"}}>{l.toUpperCase()}</button>))}</div>
      </div>
    </div>
    <div style={{display:"flex",gap:2,padding:"0 24px",borderBottom:`1px solid ${K.dark}`,background:"#0d0d18"}}>{TABS.map(tb=>(<button key={tb.id} onClick={()=>setTab(tb.id)} style={{padding:"10px 16px",fontSize:12,fontWeight:tab===tb.id?700:400,color:tab===tb.id?K.text:K.gray,background:"none",border:"none",borderBottom:tab===tb.id?`2px solid ${K.purple}`:"2px solid transparent",cursor:"pointer"}}>{t.tabs[tb.id]}</button>))}</div>
    <div style={{padding:24,maxWidth:1400,margin:"0 auto"}}><TC/></div>
    <div style={{borderTop:`1px solid ${K.dark}`,padding:"12px 24px",display:"flex",justifyContent:"space-between",fontSize:11,color:K.dim}}><span>{t.foot1}</span><span>{t.foot2}</span></div>
  </div></LCtx.Provider>);
}
