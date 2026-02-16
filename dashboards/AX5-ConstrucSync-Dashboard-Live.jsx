import { useState, useEffect, useMemo, useCallback } from "react";
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Cell, PieChart, Pie } from "recharts";

// ══════════════════════════════════════════════════════════════════════════
// CONFIG API — Données ouvertes Montréal
// ══════════════════════════════════════════════════════════════════════════

const API_BASE = "https://donnees.montreal.ca/api/3/action/datastore_search";
const RESOURCE_PERMITS = "cc41b532-f12d-40fb-9f55-eb58c9a2b12b"; // Entraves et travaux en cours
const RESOURCE_IMPACTS = "a1e18c89-c3b4-4bc2-b8f6-5e4edab1bf3e"; // Impacts des entraves
const CIFS_URL = "https://donnees.montreal.ca/api/3/action/datastore_search?resource_id=cc41b532-f12d-40fb-9f55-eb58c9a2b12b";

const fetchMTL = async (resourceId, limit = 1000, offset = 0) => {
  try {
    const url = `${API_BASE}?resource_id=${resourceId}&limit=${limit}&offset=${offset}`;
    const r = await fetch(url);
    if (!r.ok) throw new Error(`HTTP ${r.status}`);
    const data = await r.json();
    return data?.result?.records || [];
  } catch (e) {
    console.error("Fetch error:", e);
    return null;
  }
};

// ══════════════════════════════════════════════════════════════════════════
// ARRONDISSEMENT MAPPING
// ══════════════════════════════════════════════════════════════════════════

const ARR_MAP = {
  AHU: { name: "Ahuntsic-Cartierville", max: 8 },
  ANJ: { name: "Anjou", max: 4 },
  CDN: { name: "CDN-NDG", max: 10 },
  LAC: { name: "Lachine", max: 5 },
  LAS: { name: "LaSalle", max: 5 },
  PLA: { name: "Plateau-Mont-Royal", max: 10 },
  LSO: { name: "Le Sud-Ouest", max: 8 },
  IBI: { name: "Île-Bizard-SG", max: 3 },
  MHM: { name: "Mercier-Hochelaga", max: 8 },
  MTN: { name: "Montréal-Nord", max: 5 },
  OUT: { name: "Outremont", max: 4 },
  PRF: { name: "Pierrefonds-Roxboro", max: 5 },
  RDP: { name: "RDP-PAT", max: 6 },
  RPP: { name: "Rosemont-PPP", max: 10 },
  VSL: { name: "Saint-Laurent", max: 7 },
  STL: { name: "Saint-Léonard", max: 5 },
  VER: { name: "Verdun", max: 5 },
  VIM: { name: "Ville-Marie", max: 15 },
  VSE: { name: "Villeray-SM-PE", max: 8 },
};

const CORRIDORS = [
  { id: "STC", name: "Sainte-Catherine", type: "piéton", priority: 10, max: 1, keywords: ["sainte-catherine", "ste-catherine"] },
  { id: "REV-SD", name: "REV Saint-Denis", type: "cyclable", priority: 9, max: 1, keywords: ["saint-denis", "st-denis"] },
  { id: "RENE", name: "René-Lévesque", type: "urgence", priority: 10, max: 1, keywords: ["rené-lévesque", "rene-levesque"] },
  { id: "BERRI", name: "Berri / Stn centrale", type: "transport", priority: 10, max: 1, keywords: ["berri"] },
  { id: "CANAL", name: "Canal Lachine", type: "cyclable", priority: 8, max: 1, keywords: ["canal", "lachine"] },
  { id: "ND", name: "Notre-Dame", type: "urgence", priority: 10, max: 1, keywords: ["notre-dame"] },
  { id: "REV-PL", name: "REV Peel", type: "cyclable", priority: 9, max: 1, keywords: ["peel"] },
  { id: "MR", name: "Mont-Royal", type: "piéton", priority: 8, max: 2, keywords: ["mont-royal"] },
  { id: "GUY", name: "Guy-Concordia", type: "transport", priority: 8, max: 1, keywords: ["guy", "concordia"] },
  { id: "MASSON", name: "Masson", type: "piéton", priority: 7, max: 2, keywords: ["masson"] },
];

const TYPE_RISK = { "Aqueduc": 7, "Égout": 7, "Voirie": 6, "Bâtiment": 4, "Télécommunication": 3, "Gaz": 8, "Électricité": 5, "Démolition": 9, "Excavation": 8 };
const EMPRISE_RISK = { fermeture_complete: 10, occupation_partielle: 5, trottoir: 7, piste_cyclable: 6, stationnement: 2 };

const SEASONS = {
  hiver: { label: "Hiver", modifier: 1.3, color: "#60a5fa", months: [12, 1, 2, 3], constraints: ["Gel du sol — excavation limitée", "Déneigement prioritaire", "Verglas — signalisation lumineuse obligatoire"] },
  printemps: { label: "Printemps", modifier: 1.1, color: "#34d399", months: [4, 5], constraints: ["Dégel — structures fragiles", "Nids-de-poule — coordination voirie", "Reprise cyclisme"] },
  ete: { label: "Été", modifier: 1.15, color: "#fbbf24", months: [6, 7, 8], constraints: ["Festivals — coordination culturelle", "Terrasses protégées", "Canicule — pauses travailleurs"] },
  automne: { label: "Automne", modifier: 1.05, color: "#f97316", months: [9, 10, 11], constraints: ["Rentrée scolaire", "Pluies — drainage obligatoire"] },
};

const currentSeason = () => {
  const m = new Date().getMonth() + 1;
  return Object.values(SEASONS).find(s => s.months.includes(m)) || SEASONS.hiver;
};

// ══════════════════════════════════════════════════════════════════════════
// PALETTE & STYLES
// ══════════════════════════════════════════════════════════════════════════

const P = {
  bg: "#07070F", card: "#0F0F1A", navy: "#181830", purple: "#9333EA",
  teal: "#14B8A6", red: "#EF4444", orange: "#F97316", yellow: "#F59E0B",
  green: "#10B981", white: "#FFFFFF", gray: "#7878A0", text: "#E2E2F0",
  blue: "#3B82F6", dim: "#50506A",
};

const Card = ({ title, children, accent, style, right }) => (
  <div style={{ background: P.card, borderRadius: 12, padding: "14px 16px", borderLeft: `3px solid ${accent || P.purple}`, position: "relative", ...style }}>
    {title && (
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 10 }}>
        <span style={{ fontSize: 10, color: P.gray, textTransform: "uppercase", letterSpacing: 1.8, fontFamily: "monospace" }}>{title}</span>
        {right && <span style={{ fontSize: 10, color: P.dim }}>{right}</span>}
      </div>
    )}
    {children}
  </div>
);

const Pill = ({ label, color }) => (
  <span style={{ display: "inline-block", padding: "2px 9px", borderRadius: 20, fontSize: 9, fontWeight: 700, background: `${color}18`, color, letterSpacing: 0.3, border: `1px solid ${color}30` }}>{label}</span>
);

const Metric = ({ label, value, color = P.text, sub, big }) => (
  <div style={{ textAlign: "center" }}>
    <div style={{ fontSize: 9, color: P.gray, textTransform: "uppercase", letterSpacing: 1.2, marginBottom: 2 }}>{label}</div>
    <div style={{ fontSize: big ? 32 : 22, fontWeight: 900, color, fontFamily: "monospace", lineHeight: 1.1 }}>{value}</div>
    {sub && <div style={{ fontSize: 9, color: P.dim, marginTop: 2 }}>{sub}</div>}
  </div>
);

const Gauge = ({ value, max = 100, color, size = 90, label }) => {
  const pct = Math.min(1, value / max);
  const r = (size - 10) / 2;
  const circ = 2 * Math.PI * r;
  return (
    <div style={{ textAlign: "center", position: "relative", width: size, height: size }}>
      <svg width={size} height={size} style={{ transform: "rotate(-90deg)" }}>
        <circle cx={size/2} cy={size/2} r={r} fill="none" stroke={P.navy} strokeWidth="7" />
        <circle cx={size/2} cy={size/2} r={r} fill="none" stroke={color} strokeWidth="7"
          strokeDasharray={`${circ * pct} ${circ * (1 - pct)}`} strokeLinecap="round"
          style={{ transition: "stroke-dasharray 0.6s ease" }} />
      </svg>
      <div style={{ position: "absolute", top: "50%", left: "50%", transform: "translate(-50%, -50%)" }}>
        <div style={{ fontSize: 20, fontWeight: 900, color, fontFamily: "monospace" }}>{value}</div>
        {label && <div style={{ fontSize: 8, color: P.dim }}>{label}</div>}
      </div>
    </div>
  );
};

const LoadingDot = () => (
  <span style={{ display: "inline-block", width: 6, height: 6, borderRadius: "50%", background: P.purple, animation: "pulse 1.2s infinite", marginRight: 4 }} />
);

const SeverityBadge = ({ severity }) => {
  const map = { green: { bg: P.green, label: "VERT" }, yellow: { bg: P.yellow, label: "JAUNE" }, orange: { bg: P.orange, label: "ORANGE" }, red: { bg: P.red, label: "ROUGE" } };
  const s = map[severity] || map.green;
  return <span style={{ padding: "3px 12px", borderRadius: 6, fontSize: 11, fontWeight: 800, background: `${s.bg}20`, color: s.bg, border: `1px solid ${s.bg}40`, letterSpacing: 0.5 }}>{s.label}</span>;
};

// ══════════════════════════════════════════════════════════════════════════
// DATA PROCESSOR
// ══════════════════════════════════════════════════════════════════════════

function processPermits(records) {
  const now = new Date();
  const byArr = {};
  const byCategory = {};
  const byStatus = {};
  const activePermits = [];
  const corridorHits = {};

  CORRIDORS.forEach(c => { corridorHits[c.id] = 0; });

  records.forEach(r => {
    const arr = r.boroughid || "UNKNOWN";
    const end = r.duration_enddate ? new Date(r.duration_enddate) : null;
    const start = r.duration_startdate ? new Date(r.duration_startdate) : null;
    const isActive = end && end >= now && start && start <= now;
    const status = r.currentstatus || "unknown";
    const cat = r.reason_category || "Autre";

    if (!byArr[arr]) byArr[arr] = { active: 0, total: 0, planned: 0 };
    byArr[arr].total++;
    if (isActive) { byArr[arr].active++; activePermits.push(r); }
    else if (start && start > now) byArr[arr].planned++;

    byCategory[cat] = (byCategory[cat] || 0) + 1;
    byStatus[status] = (byStatus[status] || 0) + 1;

    // Corridor detection
    const street = ((r.occupancyname || "") + " " + (r.id || "")).toLowerCase();
    if (isActive) {
      CORRIDORS.forEach(c => {
        if (c.keywords.some(k => street.includes(k))) corridorHits[c.id]++;
      });
    }
  });

  return { byArr, byCategory, byStatus, activePermits, corridorHits, total: records.length };
}

// ══════════════════════════════════════════════════════════════════════════
// TABS
// ══════════════════════════════════════════════════════════════════════════

const TabTerritoire = ({ data, loading }) => {
  if (loading) return <div style={{ textAlign: "center", padding: 60, color: P.gray }}><LoadingDot />Chargement des données Montréal...</div>;
  if (!data) return <div style={{ textAlign: "center", padding: 60, color: P.red }}>Erreur de connexion à donnees.montreal.ca</div>;

  const { byArr, byCategory, corridorHits, activePermits, total } = data;
  const season = currentSeason();

  const arrData = Object.entries(ARR_MAP).map(([code, info]) => {
    const d = byArr[code] || { active: 0, total: 0, planned: 0 };
    const pct = Math.round((d.active / info.max) * 100);
    return { code, ...info, ...d, pct, status: pct >= 90 ? "saturé" : pct >= 70 ? "chargé" : "disponible" };
  }).sort((a, b) => b.pct - a.pct);

  const totalActive = arrData.reduce((s, a) => s + a.active, 0);
  const totalPlanned = arrData.reduce((s, a) => s + a.planned, 0);
  const totalCap = arrData.reduce((s, a) => s + a.max, 0);
  const saturated = arrData.filter(a => a.status === "saturé").length;

  const corridorsEnriched = CORRIDORS.map(c => ({
    ...c, current: corridorHits[c.id] || 0,
    status: (corridorHits[c.id] || 0) >= c.max ? "saturé" : (corridorHits[c.id] || 0) > 0 ? "actif" : "libre",
  }));
  const corSaturated = corridorsEnriched.filter(c => c.status === "saturé").length;

  const catData = Object.entries(byCategory).sort((a, b) => b[1] - a[1]).slice(0, 8).map(([name, count]) => ({ name: name.length > 25 ? name.slice(0, 23) + "…" : name, count }));

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
      {/* KPIs */}
      <div style={{ display: "grid", gridTemplateColumns: "repeat(6, 1fr)", gap: 8 }}>
        <Card accent={P.green}><Metric label="Permis chargés" value={total} color={P.green} sub="donnees.montreal.ca" /></Card>
        <Card accent={P.teal}><Metric label="Chantiers actifs" value={totalActive} color={P.teal} sub="en cours aujourd'hui" /></Card>
        <Card accent={P.blue}><Metric label="Planifiés" value={totalPlanned} color={P.blue} sub="date future" /></Card>
        <Card accent={P.yellow}><Metric label="Capacité MTL" value={totalCap} color={P.yellow} sub="max simultanés" /></Card>
        <Card accent={P.red}><Metric label="Zones saturées" value={saturated} color={saturated > 0 ? P.red : P.green} sub={`sur ${arrData.length}`} /></Card>
        <Card accent={P.orange}><Metric label="Corridors bloqués" value={corSaturated} color={corSaturated > 0 ? P.orange : P.green} sub={`sur ${CORRIDORS.length}`} /></Card>
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12 }}>
        {/* Heatmap */}
        <Card title="Utilisation par arrondissement" accent={P.purple} right="Données en direct">
          <ResponsiveContainer width="100%" height={340}>
            <BarChart data={arrData} layout="vertical" margin={{ left: 0, right: 8 }}>
              <XAxis type="number" domain={[0, 120]} tick={{ fill: P.dim, fontSize: 9 }} axisLine={false} tickLine={false} />
              <YAxis type="category" dataKey="code" tick={{ fill: P.gray, fontSize: 9, fontFamily: "monospace" }} axisLine={false} tickLine={false} width={30} />
              <Tooltip contentStyle={{ background: P.card, border: `1px solid ${P.navy}`, borderRadius: 8, color: P.text, fontSize: 11 }}
                formatter={(v, n, p) => [`${v}% · ${p.payload.active}/${p.payload.max} actifs`, p.payload.name]} />
              <Bar dataKey="pct" radius={[0, 4, 4, 0]} barSize={13}>
                {arrData.map((a, i) => <Cell key={i} fill={a.pct >= 90 ? P.red : a.pct >= 70 ? P.orange : a.pct >= 50 ? P.yellow : P.teal} />)}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </Card>

        <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
          {/* Corridors */}
          <Card title="Corridors stratégiques" accent={P.teal} right={`${corSaturated} saturés`}>
            <div style={{ maxHeight: 180, overflowY: "auto" }}>
              {corridorsEnriched.sort((a, b) => b.priority - a.priority).map(c => {
                const color = c.status === "saturé" ? P.red : c.status === "actif" ? P.yellow : P.green;
                const icon = { piéton: "🚶", cyclable: "🚲", urgence: "🚑", transport: "🚌" }[c.type] || "📍";
                return (
                  <div key={c.id} style={{ display: "flex", alignItems: "center", gap: 8, padding: "5px 0", borderBottom: `1px solid ${P.navy}` }}>
                    <span style={{ fontSize: 14 }}>{icon}</span>
                    <span style={{ flex: 1, fontSize: 12, color: P.text, fontWeight: 600 }}>{c.name}</span>
                    <Pill label={c.type} color={P.teal} />
                    <span style={{ fontSize: 10, color, fontWeight: 700, minWidth: 50, textAlign: "right" }}>
                      {c.current}/{c.max} {c.status === "saturé" ? "⛔" : ""}
                    </span>
                  </div>
                );
              })}
            </div>
          </Card>

          {/* Categories */}
          <Card title="Types de travaux (top 8)" accent={P.blue}>
            <ResponsiveContainer width="100%" height={130}>
              <BarChart data={catData} margin={{ left: 0, right: 4 }}>
                <XAxis dataKey="name" tick={{ fill: P.dim, fontSize: 8 }} axisLine={false} tickLine={false} angle={-20} textAnchor="end" height={40} />
                <YAxis tick={{ fill: P.dim, fontSize: 9 }} axisLine={false} tickLine={false} width={30} />
                <Bar dataKey="count" fill={P.blue} radius={[3, 3, 0, 0]} barSize={16} />
              </BarChart>
            </ResponsiveContainer>
          </Card>
        </div>
      </div>

      {/* Season */}
      <Card title="Contraintes saisonnières actives" accent={season.color}>
        <div style={{ display: "flex", alignItems: "center", gap: 14 }}>
          <div style={{ padding: "6px 14px", background: `${season.color}15`, borderRadius: 8, textAlign: "center", minWidth: 90 }}>
            <div style={{ fontSize: 16, fontWeight: 900, color: season.color }}>{season.label}</div>
            <div style={{ fontSize: 10, color: P.dim }}>×{season.modifier} risque</div>
          </div>
          <div style={{ flex: 1, display: "flex", flexWrap: "wrap", gap: 5 }}>
            {season.constraints.map((c, i) => <span key={i} style={{ padding: "3px 8px", background: P.navy, borderRadius: 5, fontSize: 10, color: P.text }}>{c}</span>)}
          </div>
        </div>
      </Card>
    </div>
  );
};

const TabPermit = ({ data, loading }) => {
  const [form, setForm] = useState({ rue: "Sainte-Catherine Ouest", arr: "VIM", type: "Voirie", emprise: "fermeture_complete", duree: 30, pietons: true, cyclistes: true, transport: true });
  const [result, setResult] = useState(null);

  const evaluate = () => {
    const arrInfo = ARR_MAP[form.arr] || { name: form.arr, max: 8 };
    const arrData = data?.byArr?.[form.arr] || { active: 0 };
    const typeR = TYPE_RISK[form.type] || 5;
    const empR = EMPRISE_RISK[form.emprise] || 5;

    const coactivity = Math.min(100, (arrData.active / arrInfo.max) * 55 + arrData.active * 4);
    const vuln = (form.pietons ? 30 : 0) + (form.cyclistes ? 20 : 0) + (form.transport ? 15 : 0);
    const historical = 35;
    const cascade = Math.min(100, (typeR + empR) * 5 + form.duree * 0.5);
    const saturation = Math.min(100, (arrData.active / arrInfo.max) * 100);
    const seasonMod = currentSeason().modifier;

    const rawScore = coactivity * 0.30 + vuln * 0.25 + historical * 0.20 + cascade * 0.15 + saturation * 0.10;
    const score = Math.round(Math.min(100, rawScore * seasonMod));
    const severity = score >= 75 ? "red" : score >= 55 ? "orange" : score >= 30 ? "yellow" : "green";
    const rec = severity === "red" ? "REPORTER" : severity === "orange" ? "CONDITIONNER" : "APPROUVER";

    const corridor = CORRIDORS.find(c => c.keywords.some(k => form.rue.toLowerCase().includes(k)));

    const conditions = [];
    if (form.pietons) conditions.push("Corridor piéton sécurisé largeur min 1.5m maintenu en tout temps");
    if (form.cyclistes) conditions.push("Déviation cyclable balisée avec signalisation au sol");
    if (form.pietons) conditions.push("Parcours accessible PMR maintenu (pente max 5%, largeur 1.5m)");
    if (form.transport) conditions.push("Notification STM 72h avant début des travaux");
    if (form.emprise === "fermeture_complete") conditions.push("Signalisation avancée 200m en amont");
    if (arrData.active >= arrInfo.max * 0.7) conditions.push("Réunion coordination inter-chantiers hebdomadaire obligatoire");
    if (form.duree > 30) conditions.push("Rapport d'avancement bi-mensuel au Bureau des permis");
    if (corridor) conditions.push(`Corridor stratégique ${corridor.name} — coordination AGIR obligatoire`);

    setResult({ score, severity, rec, coactivity: Math.round(coactivity), vuln, historical, cascade: Math.round(cascade), saturation: Math.round(saturation), conditions, corridor, active: arrData.active, arrInfo, seasonMod });
  };

  return (
    <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12 }}>
      <Card title="Nouvelle demande de permis" accent={P.purple}>
        <div style={{ display: "flex", flexDirection: "column", gap: 9 }}>
          <div>
            <div style={{ fontSize: 10, color: P.gray, marginBottom: 2 }}>Rue</div>
            <input value={form.rue} onChange={e => setForm({ ...form, rue: e.target.value })} style={{ width: "100%", boxSizing: "border-box", padding: "7px 10px", background: P.navy, border: `1px solid ${P.gray}25`, borderRadius: 6, color: P.text, fontSize: 13, outline: "none" }} />
          </div>
          <div>
            <div style={{ fontSize: 10, color: P.gray, marginBottom: 2 }}>Arrondissement (données réelles : {data?.byArr?.[form.arr]?.active || 0} actifs)</div>
            <select value={form.arr} onChange={e => setForm({ ...form, arr: e.target.value })} style={{ width: "100%", padding: "7px 10px", background: P.navy, border: `1px solid ${P.gray}25`, borderRadius: 6, color: P.text, fontSize: 13 }}>
              {Object.entries(ARR_MAP).sort((a,b) => a[1].name.localeCompare(b[1].name)).map(([code, info]) => {
                const d = data?.byArr?.[code] || { active: 0 };
                return <option key={code} value={code}>{info.name} ({d.active}/{info.max} actifs)</option>;
              })}
            </select>
          </div>
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 8 }}>
            <div>
              <div style={{ fontSize: 10, color: P.gray, marginBottom: 2 }}>Type de travaux</div>
              <select value={form.type} onChange={e => setForm({ ...form, type: e.target.value })} style={{ width: "100%", padding: "7px 10px", background: P.navy, border: `1px solid ${P.gray}25`, borderRadius: 6, color: P.text, fontSize: 12 }}>
                {Object.keys(TYPE_RISK).map(t => <option key={t}>{t}</option>)}
              </select>
            </div>
            <div>
              <div style={{ fontSize: 10, color: P.gray, marginBottom: 2 }}>Type d'emprise</div>
              <select value={form.emprise} onChange={e => setForm({ ...form, emprise: e.target.value })} style={{ width: "100%", padding: "7px 10px", background: P.navy, border: `1px solid ${P.gray}25`, borderRadius: 6, color: P.text, fontSize: 12 }}>
                {Object.keys(EMPRISE_RISK).map(t => <option key={t} value={t}>{t.replace(/_/g, " ")}</option>)}
              </select>
            </div>
          </div>
          <div>
            <div style={{ fontSize: 10, color: P.gray, marginBottom: 2 }}>Durée</div>
            <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
              <input type="range" min={5} max={120} value={form.duree} onChange={e => setForm({ ...form, duree: +e.target.value })} style={{ flex: 1, accentColor: P.purple }} />
              <span style={{ fontSize: 14, color: P.teal, fontWeight: 800, fontFamily: "monospace", minWidth: 40, textAlign: "right" }}>{form.duree}j</span>
            </div>
          </div>
          <div style={{ display: "flex", gap: 14, marginTop: 2 }}>
            {[["pietons","🚶 Piétons"], ["cyclistes","🚲 Cyclistes"], ["transport","🚌 Transport"]].map(([k, l]) => (
              <label key={k} style={{ display: "flex", alignItems: "center", gap: 4, fontSize: 12, color: P.text, cursor: "pointer" }}>
                <input type="checkbox" checked={form[k]} onChange={e => setForm({ ...form, [k]: e.target.checked })} style={{ accentColor: P.purple }} />{l}
              </label>
            ))}
          </div>
          <button onClick={evaluate} disabled={loading} style={{ marginTop: 4, padding: "10px 0", background: loading ? P.gray : `linear-gradient(135deg, ${P.purple}, #7c3aed)`, color: P.white, border: "none", borderRadius: 8, fontSize: 14, fontWeight: 700, cursor: loading ? "wait" : "pointer", letterSpacing: 0.5 }}>
            📋 Évaluer le permis
          </button>
        </div>
      </Card>

      <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
        {result ? (
          <>
            <Card title="Score de risque prédictif" accent={result.severity === "red" ? P.red : result.severity === "orange" ? P.orange : P.yellow}>
              <div style={{ display: "flex", alignItems: "center", gap: 16 }}>
                <Gauge value={result.score} color={result.severity === "red" ? P.red : result.severity === "orange" ? P.orange : result.severity === "yellow" ? P.yellow : P.green} size={100} label="/100" />
                <div style={{ flex: 1 }}>
                  <div style={{ display: "flex", gap: 8, alignItems: "center", marginBottom: 6 }}>
                    <SeverityBadge severity={result.severity} />
                    <span style={{ fontSize: 18, fontWeight: 900, color: P.text }}>{result.rec}</span>
                  </div>
                  <div style={{ fontSize: 11, color: P.gray }}>{result.active} chantiers actifs dans {result.arrInfo.name} ({result.active}/{result.arrInfo.max})</div>
                  <div style={{ fontSize: 10, color: P.dim, marginTop: 2 }}>Saison: {currentSeason().label} (×{result.seasonMod})</div>
                  {result.corridor && <div style={{ marginTop: 5, padding: "3px 8px", background: `${P.red}15`, borderRadius: 5, fontSize: 10, color: P.red, display: "inline-block" }}>⚠️ Corridor {result.corridor.name} ({result.corridor.type}) P{result.corridor.priority}</div>}
                </div>
              </div>
              <div style={{ display: "grid", gridTemplateColumns: "repeat(5, 1fr)", gap: 6, marginTop: 12 }}>
                {[
                  { label: "Coactivité", val: result.coactivity, w: 30, color: P.purple },
                  { label: "Vulnérables", val: result.vuln, w: 25, color: P.orange },
                  { label: "Historique", val: result.historical, w: 20, color: P.blue },
                  { label: "Cascade", val: result.cascade, w: 15, color: P.red },
                  { label: "Saturation", val: result.saturation, w: 10, color: P.yellow },
                ].map(c => (
                  <div key={c.label} style={{ textAlign: "center", padding: "5px 0", background: P.navy, borderRadius: 6 }}>
                    <div style={{ fontSize: 8, color: P.dim }}>{c.label} ({c.w}%)</div>
                    <div style={{ fontSize: 16, fontWeight: 800, color: c.color, fontFamily: "monospace" }}>{c.val}</div>
                  </div>
                ))}
              </div>
            </Card>
            <Card title={`Conditions de mitigation (${result.conditions.length})`} accent={P.orange}>
              {result.conditions.map((c, i) => (
                <div key={i} style={{ display: "flex", gap: 6, padding: "4px 0", borderBottom: `1px solid ${P.navy}` }}>
                  <span style={{ color: P.orange, fontSize: 10 }}>▸</span>
                  <span style={{ fontSize: 11, color: P.text }}>{c}</span>
                </div>
              ))}
              <div style={{ marginTop: 8, padding: 6, background: `${P.red}10`, borderRadius: 5, fontSize: 10, color: P.orange, textAlign: "center", fontWeight: 600 }}>
                ⚠️ HITL OBLIGATOIRE — Charte AgenticX5
              </div>
            </Card>
          </>
        ) : (
          <Card style={{ display: "flex", alignItems: "center", justifyContent: "center", minHeight: 280 }}>
            <div style={{ textAlign: "center", color: P.gray }}>
              <div style={{ fontSize: 40, marginBottom: 8 }}>📋</div>
              <div style={{ fontSize: 13 }}>Remplissez le formulaire et cliquez Évaluer</div>
              <div style={{ fontSize: 10, marginTop: 4, color: P.dim }}>Scoring calibré sur {data?.total || "..."} permis réels Montréal</div>
            </div>
          </Card>
        )}
      </div>
    </div>
  );
};

const TabSimulation = ({ data }) => {
  const arrCode = "VIM";
  const arrActive = data?.byArr?.[arrCode]?.active || 8;

  const [p, setP] = useState({ chantiers: arrActive, score: 65, pietons: 3200, cyclistes: 500, type: "Voirie", emprise: "fermeture_complete", duree: 30 });

  const scenarios = useMemo(() => {
    const typeR = TYPE_RISK[p.type] || 6;
    const coact = p.chantiers >= 5 ? 2.0 : p.chantiers >= 3 ? 1.5 : p.chantiers >= 2 ? 1.3 : 1.0;
    const rr = { fermeture_complete: 0.9, trottoir: 0.6, occupation_partielle: 0.3, piste_cyclable: 0.7, stationnement: 0.1 }[p.emprise] || 0.3;

    const baseline = { name: "Sans chantier", score: p.score, pietons: 0, cyclistes: 0, incidents: 0, color: P.dim };
    const wScore = Math.min(100, Math.round(p.score + typeR * coact + (p.pietons * rr + p.cyclistes * rr) / 100));
    const pR = Math.round(p.pietons * rr); const cR = Math.round(p.cyclistes * rr);
    const wInc = +((pR * 0.036 + cR * 0.048) / 1000 * p.duree).toFixed(1);
    const withC = { name: "Avec chantier", score: wScore, pietons: pR, cyclistes: cR, incidents: wInc, color: P.red };

    const fCh = Math.max(0, Math.round(p.chantiers * 0.7));
    const fCoact = fCh >= 5 ? 2.0 : fCh >= 3 ? 1.5 : fCh >= 2 ? 1.3 : 1.0;
    const dScore = Math.min(100, Math.round(p.score * 0.85 + typeR * fCoact + (pR * 0.8 + cR * 0.8) / 120));
    const dInc = +((pR * 0.8 * 0.036 + cR * 0.8 * 0.048) / 1000 * p.duree).toFixed(1);
    const deferred = { name: "Reporté 30j", score: dScore, pietons: Math.round(pR * 0.8), cyclistes: Math.round(cR * 0.8), incidents: dInc, color: P.teal };

    return [baseline, withC, deferred];
  }, [p]);

  const delta = scenarios[1].score - scenarios[0].score;
  const saved = scenarios[1].score - scenarios[2].score;

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
      <Card title="Paramètres — Simulation What-If" accent={P.purple}>
        <div style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: 10 }}>
          {[
            { label: "Score UrbanIA actuel", key: "score", min: 0, max: 100, unit: "/100" },
            { label: `Chantiers actifs zone (réel: ${arrActive})`, key: "chantiers", min: 0, max: 20, unit: "" },
            { label: "Flux piétons/h", key: "pietons", min: 0, max: 8000, unit: "/h" },
            { label: "Flux cyclistes/h", key: "cyclistes", min: 0, max: 2000, unit: "/h" },
          ].map(s => (
            <div key={s.key}>
              <div style={{ fontSize: 9, color: P.gray, marginBottom: 2 }}>{s.label}</div>
              <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
                <input type="range" min={s.min} max={s.max} value={p[s.key]} onChange={e => setP({ ...p, [s.key]: +e.target.value })} style={{ flex: 1, accentColor: P.purple }} />
                <span style={{ fontSize: 12, color: P.teal, fontWeight: 700, minWidth: 36, textAlign: "right", fontFamily: "monospace" }}>{p[s.key]}{s.unit}</span>
              </div>
            </div>
          ))}
        </div>
      </Card>

      <div style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: 12 }}>
        {scenarios.map((s, i) => (
          <Card key={i} accent={s.color} title={s.name}>
            <div style={{ display: "flex", justifyContent: "center", marginBottom: 8 }}>
              <Gauge value={s.score} color={s.color} size={90} label="Score" />
            </div>
            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 6 }}>
              <div style={{ padding: 5, background: P.navy, borderRadius: 5, textAlign: "center" }}>
                <div style={{ fontSize: 8, color: P.dim }}>🚶 Piétons redirigés</div>
                <div style={{ fontSize: 15, fontWeight: 800, color: s.pietons > 0 ? P.orange : P.green, fontFamily: "monospace" }}>{s.pietons.toLocaleString()}</div>
              </div>
              <div style={{ padding: 5, background: P.navy, borderRadius: 5, textAlign: "center" }}>
                <div style={{ fontSize: 8, color: P.dim }}>🚲 Cyclistes redirigés</div>
                <div style={{ fontSize: 15, fontWeight: 800, color: s.cyclistes > 0 ? P.orange : P.green, fontFamily: "monospace" }}>{s.cyclistes.toLocaleString()}</div>
              </div>
            </div>
            <div style={{ marginTop: 6, padding: 5, background: P.navy, borderRadius: 5, textAlign: "center" }}>
              <div style={{ fontSize: 8, color: P.dim }}>Incidents prédits ({p.duree}j)</div>
              <div style={{ fontSize: 17, fontWeight: 900, color: s.incidents > 0.5 ? P.red : P.green, fontFamily: "monospace" }}>{s.incidents}</div>
            </div>
          </Card>
        ))}
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12 }}>
        <Card title="Delta risque" accent={delta > 25 ? P.red : delta > 10 ? P.orange : P.green}>
          <div style={{ display: "flex", alignItems: "center", gap: 14 }}>
            <div style={{ fontSize: 44, fontWeight: 900, color: delta > 25 ? P.red : delta > 10 ? P.orange : P.green, fontFamily: "monospace" }}>+{delta}</div>
            <div>
              <div style={{ fontSize: 13, color: P.text, fontWeight: 700 }}>points de risque</div>
              <div style={{ fontSize: 11, color: P.gray }}>{delta > 25 ? "Impact significatif — reporter" : delta > 10 ? "Impact modéré — conditions" : "Impact faible — approuver"}</div>
            </div>
          </div>
        </Card>
        <Card title="Gain du report 30j" accent={P.teal}>
          <div style={{ display: "flex", alignItems: "center", gap: 14 }}>
            <div style={{ fontSize: 44, fontWeight: 900, color: P.teal, fontFamily: "monospace" }}>-{saved}</div>
            <div>
              <div style={{ fontSize: 13, color: P.text, fontWeight: 700 }}>points économisés</div>
              <div style={{ fontSize: 11, color: P.gray }}>{scenarios[1].pietons - scenarios[2].pietons} piétons épargnés</div>
            </div>
          </div>
        </Card>
      </div>
    </div>
  );
};

const TabCoordination = ({ data }) => {
  const stakeholders = [
    { name: "Bureau des permis", canal: "email", p: 10, icon: "🏛️" },
    { name: "Coordonnateur AGIR", canal: "dashboard", p: 10, icon: "📋" },
    { name: "SPVM", canal: "radio", p: 9, icon: "👮" },
    { name: "SIM (pompiers)", canal: "radio", p: 9, icon: "🚒" },
    { name: "Urgences-santé", canal: "radio", p: 8, icon: "🚑" },
    { name: "STM", canal: "email", p: 8, icon: "🚌" },
    { name: "Résidents zone", canal: "SMS", p: 6, icon: "🏠" },
    { name: "Commerçants", canal: "email", p: 5, icon: "🏪" },
  ];

  const timeline = [
    { day: "J-7", tasks: ["Notification pré-chantier — toutes parties prenantes", "Validation plan signalisation (AGIR)"], st: "done" },
    { day: "J-5", tasks: ["Réunion coordination inter-chantiers", "Notification STM relocalisation arrêts"], st: "done" },
    { day: "J-3", tasks: ["Inspection terrain signalisation", "Vérification corridor piéton PMR"], st: "active" },
    { day: "J-1", tasks: ["Confirmation finale", "Activation NudgeAgent alertes piétons/cyclistes"], st: "pending" },
    { day: "J0", tasks: ["Début des travaux", "Monitoring UrbanIA temps réel activé"], st: "pending" },
    { day: "J+7", tasks: ["Rapport avancement #1", "Vérification conditions mitigation"], st: "pending" },
    { day: "J+14", tasks: ["Rapport bi-mensuel Bureau des permis"], st: "pending" },
  ];

  const channels = [
    { canal: "Dashboard", icon: "📊", who: "Coordonnateur, Ville", color: P.purple },
    { canal: "Email", icon: "📧", who: "Bureau permis, STM", color: P.blue },
    { canal: "SMS", icon: "📱", who: "Résidents, Commerçants", color: P.teal },
    { canal: "Radio", icon: "📻", who: "SPVM, SIM, Urgences", color: P.red },
    { canal: "NudgeAgent", icon: "🔔", who: "9 profils × FR/EN", color: P.yellow },
  ];

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
      <Card title="Parties prenantes — plan type voirie sévérité orange" accent={P.purple}>
        <div style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: 8 }}>
          {stakeholders.map((s, i) => (
            <div key={i} style={{ display: "flex", alignItems: "center", gap: 7, padding: "7px 8px", background: P.navy, borderRadius: 7 }}>
              <span style={{ fontSize: 18 }}>{s.icon}</span>
              <div>
                <div style={{ fontSize: 11, fontWeight: 700, color: P.text }}>{s.name}</div>
                <div style={{ fontSize: 9, color: P.dim }}>{s.canal} · P{s.p}</div>
              </div>
            </div>
          ))}
        </div>
      </Card>

      <Card title="Timeline de coordination" accent={P.teal}>
        <div style={{ paddingLeft: 20, position: "relative" }}>
          <div style={{ position: "absolute", left: 5, top: 0, bottom: 0, width: 2, background: `${P.gray}20` }} />
          {timeline.map((t, i) => {
            const c = t.st === "done" ? P.green : t.st === "active" ? P.yellow : P.dim;
            return (
              <div key={i} style={{ marginBottom: 12, position: "relative" }}>
                <div style={{ position: "absolute", left: -18, top: 2, width: 10, height: 10, borderRadius: "50%", background: c }} />
                <div style={{ display: "flex", alignItems: "flex-start", gap: 10 }}>
                  <span style={{ minWidth: 32, fontSize: 12, fontWeight: 800, color: c, fontFamily: "monospace" }}>{t.day}</span>
                  <div style={{ flex: 1 }}>
                    {t.tasks.map((task, j) => <div key={j} style={{ fontSize: 11, color: t.st === "done" ? P.dim : P.text, textDecoration: t.st === "done" ? "line-through" : "none", marginBottom: 2 }}>{task}</div>)}
                  </div>
                  <Pill label={t.st === "done" ? "terminé" : t.st === "active" ? "en cours" : "à venir"} color={c} />
                </div>
              </div>
            );
          })}
        </div>
      </Card>

      <Card title="Canaux de notification multi-modal" accent={P.orange}>
        <div style={{ display: "grid", gridTemplateColumns: "repeat(5, 1fr)", gap: 8 }}>
          {channels.map(c => (
            <div key={c.canal} style={{ textAlign: "center", padding: "8px 4px", background: P.navy, borderRadius: 7, borderTop: `2px solid ${c.color}` }}>
              <div style={{ fontSize: 22 }}>{c.icon}</div>
              <div style={{ fontSize: 11, fontWeight: 700, color: c.color, marginTop: 3 }}>{c.canal}</div>
              <div style={{ fontSize: 9, color: P.dim, marginTop: 1 }}>{c.who}</div>
            </div>
          ))}
        </div>
      </Card>
    </div>
  );
};

// ══════════════════════════════════════════════════════════════════════════
// MAIN
// ══════════════════════════════════════════════════════════════════════════

const TABS = [
  { id: "territoire", label: "🗺️ Territoire", comp: TabTerritoire },
  { id: "evaluer", label: "📋 Évaluer", comp: TabPermit },
  { id: "simulation", label: "🔮 Simulation", comp: TabSimulation },
  { id: "coordination", label: "🤝 Coordination", comp: TabCoordination },
];

export default function ConstrucSyncLive() {
  const [tab, setTab] = useState("territoire");
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [lastFetch, setLastFetch] = useState(null);

  const loadData = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const records = await fetchMTL(RESOURCE_PERMITS, 1000, 0);
      if (!records) throw new Error("API indisponible");
      // Fetch second page if needed
      let all = records;
      if (records.length === 1000) {
        const page2 = await fetchMTL(RESOURCE_PERMITS, 1000, 1000);
        if (page2) all = [...records, ...page2];
      }
      setData(processPermits(all));
      setLastFetch(new Date());
    } catch (e) {
      setError(e.message);
      // Fallback to demo data
      setData(null);
    }
    setLoading(false);
  }, []);

  useEffect(() => { loadData(); }, [loadData]);

  const Tab = TABS.find(t => t.id === tab)?.comp || TabTerritoire;

  return (
    <div style={{ minHeight: "100vh", background: P.bg, color: P.text, fontFamily: "'Segoe UI', -apple-system, sans-serif" }}>
      <style>{`@keyframes pulse { 0%, 100% { opacity: 1; } 50% { opacity: 0.3; } }`}</style>

      {/* Header */}
      <div style={{ background: P.card, borderBottom: `2px solid ${P.purple}`, padding: "10px 20px", display: "flex", alignItems: "center", justifyContent: "space-between" }}>
        <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
          <div style={{ width: 34, height: 34, background: `linear-gradient(135deg, ${P.purple}, #7c3aed)`, borderRadius: 8, display: "flex", alignItems: "center", justifyContent: "center", fontWeight: 900, fontSize: 13, color: P.white }}>CS</div>
          <div>
            <div style={{ fontSize: 16, fontWeight: 800, letterSpacing: 0.3 }}>ConstrucSync Municipal</div>
            <div style={{ fontSize: 10, color: P.gray }}>Planification chantiers — EN AMONT d'UrbanIA — Données ouvertes Montréal</div>
          </div>
        </div>
        <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
          {data && <span style={{ fontSize: 9, color: P.green }}>● LIVE {data.total} permis</span>}
          {loading && <span style={{ fontSize: 9, color: P.yellow }}><LoadingDot />Chargement...</span>}
          {error && <span style={{ fontSize: 9, color: P.red }}>● {error}</span>}
          <Pill label="HITL" color={P.orange} />
          <Pill label="AgenticX5" color={P.teal} />
          <button onClick={loadData} style={{ background: P.navy, border: `1px solid ${P.gray}30`, borderRadius: 5, color: P.gray, fontSize: 10, padding: "3px 8px", cursor: "pointer" }}>↻ Refresh</button>
        </div>
      </div>

      {/* Tabs */}
      <div style={{ display: "flex", background: P.card, borderBottom: `1px solid ${P.navy}` }}>
        {TABS.map(t => (
          <button key={t.id} onClick={() => setTab(t.id)}
            style={{ flex: 1, padding: "9px 0", background: tab === t.id ? P.navy : "transparent", color: tab === t.id ? P.purple : P.gray, border: "none", borderBottom: tab === t.id ? `2px solid ${P.purple}` : "2px solid transparent", fontSize: 12, fontWeight: 700, cursor: "pointer", transition: "all 0.15s" }}>
            {t.label}
          </button>
        ))}
      </div>

      {/* Content */}
      <div style={{ padding: "14px 16px" }}>
        <Tab data={data} loading={loading} />
      </div>

      {/* Footer */}
      <div style={{ padding: "8px 20px", background: P.card, borderTop: `1px solid ${P.navy}`, display: "flex", justifyContent: "space-between", fontSize: 9, color: P.dim }}>
        <span>GenAISafety / Preventera — AX5 ConstrucSync Municipal v2.0</span>
        <span>Source: donnees.montreal.ca/dataset/info-travaux (licence ouverte)</span>
        <span>{lastFetch ? `Dernière mise à jour: ${lastFetch.toLocaleTimeString("fr-CA")}` : "..."} · github.com/Preventera/UrbanIA</span>
      </div>
    </div>
  );
}
