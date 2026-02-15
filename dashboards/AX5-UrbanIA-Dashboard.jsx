import { useState, useEffect, useCallback } from "react";
import { LineChart, Line, BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, PieChart, Pie, Cell, RadialBarChart, RadialBar, Legend } from "recharts";

// ── DATA ──────────────────────────────────────────────────────
const CNESST_YEARLY = [
  { year: "2016", lesions: 6207, tms: 1446, machine: 322, psy: 32 },
  { year: "2017", lesions: 6592, tms: 1682, machine: 342, psy: 26 },
  { year: "2018", lesions: 7443, tms: 1761, machine: 326, psy: 38 },
  { year: "2019", lesions: 8234, tms: 2073, machine: 368, psy: 52 },
  { year: "2020", lesions: 7599, tms: 2056, machine: 490, psy: 48 },
  { year: "2021", lesions: 8826, tms: 2553, machine: 501, psy: 52 },
  { year: "2022", lesions: 9502, tms: 2583, machine: 517, psy: 57 },
];

const SAAQ_WORKZONE = [
  { region: "Montréal", accidents: 2995, pietons: 108, cyclistes: 91, mortels: 24 },
  { region: "Montérégie", accidents: 1259, pietons: 22, cyclistes: 10, mortels: 18 },
  { region: "Cap.-Nat.", accidents: 1193, pietons: 19, cyclistes: 8, mortels: 15 },
  { region: "Ch.-App.", accidents: 382, pietons: 8, cyclistes: 3, mortels: 9 },
  { region: "Laval", accidents: 358, pietons: 12, cyclistes: 4, mortels: 7 },
  { region: "Laurentides", accidents: 352, pietons: 6, cyclistes: 2, mortels: 8 },
];

const RISK_GENRES = [
  { name: "Frappé par objet", value: 7847, score: 9, color: "#ef4444" },
  { name: "Réaction du corps", value: 8384, score: 2, color: "#64748b" },
  { name: "Effort excessif", value: 8069, score: 2, color: "#64748b" },
  { name: "Chute niv. inf.", value: 5815, score: 7, color: "#f59e0b" },
  { name: "Chute même niv.", value: 4528, score: 4, color: "#94a3b8" },
  { name: "Coincé/écrasé", value: 3022, score: 6, color: "#f97316" },
];

const SAAQ_HOURS = [
  { hour: "00-04h", count: 481, pct: 5.9 },
  { hour: "04-08h", count: 826, pct: 10.1 },
  { hour: "08-12h", count: 1882, pct: 23.0 },
  { hour: "12-16h", count: 2296, pct: 28.1 },
  { hour: "16-20h", count: 1664, pct: 20.4 },
  { hour: "20-24h", count: 999, pct: 12.2 },
];

const SOURCES = [
  { id: 1, name: "Entraves CIFS", couche: 3, status: "planned", icon: "🚧" },
  { id: 2, name: "Comptages piétons", couche: 3, status: "planned", icon: "👤" },
  { id: 3, name: "Comptages vélos", couche: 3, status: "planned", icon: "🚲" },
  { id: 4, name: "Capteurs Bluetooth", couche: 3, status: "planned", icon: "📡" },
  { id: 5, name: "Permis AGIR", couche: 3, status: "planned", icon: "📋" },
  { id: 6, name: "Météo Canada", couche: 3, status: "planned", icon: "🌤" },
  { id: 7, name: "Stations Bixi", couche: 3, status: "planned", icon: "🚴" },
  { id: 8, name: "CNESST Lésions", couche: 1, status: "active", icon: "🏗", records: "54 403" },
  { id: 9, name: "SAAQ Zone travaux", couche: 2, status: "active", icon: "🚛", records: "8 173" },
];

const ZONES_MOCK = [
  { id: "VM-01", name: "Ville-Marie Centre", score: 78, severity: "orange", chantiers: 12, flux: 4200 },
  { id: "PM-01", name: "Plateau Mont-Royal", score: 62, severity: "yellow", chantiers: 8, flux: 3100 },
  { id: "RO-01", name: "Rosemont", score: 45, severity: "yellow", chantiers: 5, flux: 1800 },
  { id: "CD-01", name: "Côte-des-Neiges", score: 71, severity: "orange", chantiers: 9, flux: 2900 },
  { id: "SW-01", name: "Sud-Ouest", score: 38, severity: "green", chantiers: 3, flux: 1200 },
  { id: "ME-01", name: "Mercier-Est", score: 29, severity: "green", chantiers: 2, flux: 800 },
];

// ── COMPONENTS ───────────────────────────────────────────────

const Metric = ({ label, value, sub, color = "#e8e8f0", trend }) => (
  <div style={{ textAlign: "center" }}>
    <div style={{ fontSize: 11, color: "#8888a0", textTransform: "uppercase", letterSpacing: 1, marginBottom: 4 }}>{label}</div>
    <div style={{ fontSize: 28, fontWeight: 900, color, fontFamily: "'JetBrains Mono', monospace" }}>{value}</div>
    {sub && <div style={{ fontSize: 11, color: trend === "up" ? "#ef4444" : trend === "down" ? "#10b981" : "#8888a0", marginTop: 2 }}>{sub}</div>}
  </div>
);

const SeverityBadge = ({ severity }) => {
  const colors = { green: "#10b981", yellow: "#f59e0b", orange: "#f97316", red: "#ef4444" };
  const labels = { green: "Normal", yellow: "Attention", orange: "Élevé", red: "Critique" };
  return (
    <span style={{
      display: "inline-flex", alignItems: "center", gap: 4, padding: "2px 8px",
      borderRadius: 100, fontSize: 10, fontWeight: 700, textTransform: "uppercase",
      background: `${colors[severity]}20`, color: colors[severity], letterSpacing: 0.5
    }}>
      <span style={{ width: 6, height: 6, borderRadius: "50%", background: colors[severity] }} />
      {labels[severity]}
    </span>
  );
};

const CoucheTag = ({ n }) => {
  const c = { 1: { bg: "#3b82f620", color: "#3b82f6", label: "C1 SUR" }, 2: { bg: "#f59e0b20", color: "#f59e0b", label: "C2 TRANSIT" }, 3: { bg: "#9333ea20", color: "#9333ea", label: "C3 AUTOUR" } };
  const s = c[n];
  return <span style={{ fontSize: 9, padding: "1px 6px", borderRadius: 4, background: s.bg, color: s.color, fontWeight: 700, letterSpacing: 0.5 }}>{s.label}</span>;
};

const Card = ({ title, children, tag, style = {} }) => (
  <div style={{
    background: "#12121e", border: "1px solid #2a2a3e", borderRadius: 12, padding: 20,
    ...style
  }}>
    {(title || tag) && (
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 14 }}>
        {title && <div style={{ fontSize: 13, fontWeight: 700, color: "#e8e8f0" }}>{title}</div>}
        {tag}
      </div>
    )}
    {children}
  </div>
);

const CustomTooltip = ({ active, payload, label }) => {
  if (!active || !payload?.length) return null;
  return (
    <div style={{ background: "#1a1a2e", border: "1px solid #2a2a3e", borderRadius: 8, padding: "8px 12px", fontSize: 12 }}>
      <div style={{ fontWeight: 700, marginBottom: 4 }}>{label}</div>
      {payload.map((p, i) => (
        <div key={i} style={{ color: p.color }}>{p.name}: {p.value?.toLocaleString()}</div>
      ))}
    </div>
  );
};

// ── MAIN DASHBOARD ───────────────────────────────────────────

export default function UrbanIADashboard() {
  const [activeTab, setActiveTab] = useState("overview");
  const [now, setNow] = useState(new Date());
  const [simScore, setSimScore] = useState(72);
  const [simWeather, setSimWeather] = useState(1.0);
  const [simCoactivity, setSimCoactivity] = useState(1.0);

  useEffect(() => {
    const t = setInterval(() => setNow(new Date()), 60000);
    return () => clearInterval(t);
  }, []);

  const computeScore = useCallback(() => {
    const base = 72;
    return Math.min(100, Math.round(base * simWeather * simCoactivity));
  }, [simWeather, simCoactivity]);

  useEffect(() => setSimScore(computeScore()), [computeScore]);

  const getSeverity = (s) => s >= 85 ? "red" : s >= 65 ? "orange" : s >= 40 ? "yellow" : "green";

  const tabs = [
    { id: "overview", label: "Vue d'ensemble" },
    { id: "couche1", label: "C1 CNESST" },
    { id: "couche2", label: "C2 SAAQ" },
    { id: "zones", label: "Zones MTL" },
    { id: "simulator", label: "Simulateur" },
  ];

  return (
    <div style={{ minHeight: "100vh", background: "#0a0a12", color: "#e8e8f0", fontFamily: "'Segoe UI', system-ui, sans-serif" }}>
      {/* HEADER */}
      <div style={{ borderBottom: "1px solid #2a2a3e", padding: "12px 24px", display: "flex", justifyContent: "space-between", alignItems: "center" }}>
        <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
          <div style={{ width: 32, height: 32, borderRadius: 8, background: "linear-gradient(135deg, #9333ea, #14b8a6)", display: "flex", alignItems: "center", justifyContent: "center", fontSize: 16, fontWeight: 900 }}>U</div>
          <div>
            <div style={{ fontSize: 15, fontWeight: 800, letterSpacing: -0.5 }}>AX5 UrbanIA</div>
            <div style={{ fontSize: 10, color: "#8888a0" }}>Sécurité prédictive urbaine</div>
          </div>
        </div>
        <div style={{ display: "flex", alignItems: "center", gap: 16, fontSize: 12, color: "#8888a0" }}>
          <span style={{ display: "flex", alignItems: "center", gap: 4 }}>
            <span style={{ width: 6, height: 6, borderRadius: "50%", background: "#10b981", animation: "pulse 2s infinite" }} />
            2/9 sources actives
          </span>
          <span>{now.toLocaleDateString("fr-CA")} {now.toLocaleTimeString("fr-CA", { hour: "2-digit", minute: "2-digit" })}</span>
        </div>
      </div>

      {/* TABS */}
      <div style={{ display: "flex", gap: 2, padding: "0 24px", borderBottom: "1px solid #1a1a2e", background: "#0d0d18" }}>
        {tabs.map(t => (
          <button key={t.id} onClick={() => setActiveTab(t.id)} style={{
            padding: "10px 16px", fontSize: 12, fontWeight: activeTab === t.id ? 700 : 400,
            color: activeTab === t.id ? "#e8e8f0" : "#8888a0", background: "none", border: "none",
            borderBottom: activeTab === t.id ? "2px solid #9333ea" : "2px solid transparent",
            cursor: "pointer", transition: "all 0.2s"
          }}>{t.label}</button>
        ))}
      </div>

      <div style={{ padding: 24, maxWidth: 1400, margin: "0 auto" }}>
        {/* ━━━ OVERVIEW TAB ━━━ */}
        {activeTab === "overview" && (
          <>
            {/* KPI BAR */}
            <div style={{ display: "grid", gridTemplateColumns: "repeat(6, 1fr)", gap: 16, marginBottom: 24 }}>
              <Card><Metric label="Lésions Construction" value="54 403" sub="7 ans CNESST" /></Card>
              <Card><Metric label="Zone travaux SAAQ" value="8 173" sub="3 ans (2020-22)" /></Card>
              <Card><Metric label="Risque urbain" value="51.6%" sub="à composante urbaine" color="#ef4444" /></Card>
              <Card><Metric label="TMS Construction" value="26.0%" sub="+79% en 7 ans" color="#f59e0b" trend="up" /></Card>
              <Card><Metric label="Piétons MTL" value="108" sub="en zone travaux" color="#ef4444" /></Card>
              <Card><Metric label="Cyclistes MTL" value="91" sub="en zone travaux" color="#f97316" /></Card>
            </div>

            {/* TWO CHARTS ROW */}
            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 16, marginBottom: 24 }}>
              <Card title="Lésions Construction — Tendance 7 ans" tag={<CoucheTag n={1} />}>
                <ResponsiveContainer width="100%" height={220}>
                  <LineChart data={CNESST_YEARLY}>
                    <XAxis dataKey="year" stroke="#4a4a6a" fontSize={11} />
                    <YAxis stroke="#4a4a6a" fontSize={11} />
                    <Tooltip content={<CustomTooltip />} />
                    <Line type="monotone" dataKey="lesions" stroke="#9333ea" strokeWidth={2.5} dot={{ fill: "#9333ea", r: 4 }} name="Lésions" />
                    <Line type="monotone" dataKey="tms" stroke="#f59e0b" strokeWidth={2} dot={{ fill: "#f59e0b", r: 3 }} name="TMS" />
                  </LineChart>
                </ResponsiveContainer>
              </Card>

              <Card title="Accidents zone travaux par région" tag={<CoucheTag n={2} />}>
                <ResponsiveContainer width="100%" height={220}>
                  <BarChart data={SAAQ_WORKZONE} layout="vertical">
                    <XAxis type="number" stroke="#4a4a6a" fontSize={11} />
                    <YAxis type="category" dataKey="region" stroke="#4a4a6a" fontSize={10} width={80} />
                    <Tooltip content={<CustomTooltip />} />
                    <Bar dataKey="accidents" fill="#14b8a6" radius={[0, 4, 4, 0]} name="Accidents" />
                    <Bar dataKey="pietons" fill="#ef4444" radius={[0, 4, 4, 0]} name="Piétons" />
                  </BarChart>
                </ResponsiveContainer>
              </Card>
            </div>

            {/* SOURCES STATUS */}
            <Card title="Sources de données — 9 sources, 3 couches">
              <div style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: 12 }}>
                {[1, 2, 3].map(couche => (
                  <div key={couche}>
                    <div style={{ fontSize: 11, fontWeight: 700, color: "#8888a0", marginBottom: 8, display: "flex", alignItems: "center", gap: 6 }}>
                      <CoucheTag n={couche} />
                      {couche === 1 ? "SUR le chantier" : couche === 2 ? "EN TRANSIT" : "AUTOUR"}
                    </div>
                    {SOURCES.filter(s => s.couche === couche).map(s => (
                      <div key={s.id} style={{
                        display: "flex", alignItems: "center", justifyContent: "space-between",
                        padding: "6px 10px", borderRadius: 6, marginBottom: 4,
                        background: s.status === "active" ? "#10b98110" : "#1a1a2e",
                        border: `1px solid ${s.status === "active" ? "#10b98130" : "#2a2a3e"}`
                      }}>
                        <div style={{ display: "flex", alignItems: "center", gap: 8, fontSize: 12 }}>
                          <span>{s.icon}</span>
                          <span>{s.name}</span>
                        </div>
                        <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
                          {s.records && <span style={{ fontSize: 10, color: "#14b8a6", fontFamily: "monospace" }}>{s.records}</span>}
                          <span style={{
                            width: 6, height: 6, borderRadius: "50%",
                            background: s.status === "active" ? "#10b981" : "#4a4a6a"
                          }} />
                        </div>
                      </div>
                    ))}
                  </div>
                ))}
              </div>
            </Card>
          </>
        )}

        {/* ━━━ COUCHE 1 TAB ━━━ */}
        {activeTab === "couche1" && (
          <>
            <div style={{ marginBottom: 16, display: "flex", alignItems: "center", gap: 8 }}>
              <CoucheTag n={1} />
              <span style={{ fontSize: 18, fontWeight: 800 }}>CNESST — Lésions professionnelles Construction</span>
              <span style={{ fontSize: 12, color: "#8888a0" }}>54 403 lésions | 2016-2022 | SCIAN 23</span>
            </div>

            <div style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: 16, marginBottom: 24 }}>
              <Card><Metric label="Total 7 ans" value="54 403" sub="Construction SCIAN 23" color="#9333ea" /></Card>
              <Card><Metric label="Croissance" value="+53.1%" sub="2016 → 2022" color="#ef4444" trend="up" /></Card>
              <Card><Metric label="TMS" value="14 154" sub="26.0% — hausse +79%" color="#f59e0b" trend="up" /></Card>
              <Card><Metric label="Risque urbain" value="28 093" sub="51.6% composante urbaine" color="#ef4444" /></Card>
            </div>

            <div style={{ display: "grid", gridTemplateColumns: "2fr 1fr", gap: 16, marginBottom: 24 }}>
              <Card title="Genres d'accident — Score risque urbain">
                <ResponsiveContainer width="100%" height={260}>
                  <BarChart data={RISK_GENRES} layout="vertical">
                    <XAxis type="number" stroke="#4a4a6a" fontSize={11} />
                    <YAxis type="category" dataKey="name" stroke="#4a4a6a" fontSize={10} width={120} />
                    <Tooltip content={<CustomTooltip />} />
                    <Bar dataKey="value" name="Lésions" radius={[0, 4, 4, 0]}>
                      {RISK_GENRES.map((d, i) => <Cell key={i} fill={d.color} />)}
                    </Bar>
                  </BarChart>
                </ResponsiveContainer>
              </Card>

              <Card title="Score risque urbain par genre">
                {RISK_GENRES.sort((a, b) => b.score - a.score).map((g, i) => (
                  <div key={i} style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 8 }}>
                    <div style={{ flex: 1, fontSize: 11, color: "#8888a0" }}>{g.name}</div>
                    <div style={{ width: 80, height: 6, borderRadius: 3, background: "#1a1a2e", overflow: "hidden" }}>
                      <div style={{ width: `${g.score * 10}%`, height: "100%", borderRadius: 3, background: g.score >= 7 ? "#ef4444" : g.score >= 5 ? "#f59e0b" : "#64748b" }} />
                    </div>
                    <div style={{ fontSize: 12, fontWeight: 700, fontFamily: "monospace", width: 24, textAlign: "right", color: g.score >= 7 ? "#ef4444" : g.score >= 5 ? "#f59e0b" : "#64748b" }}>{g.score}</div>
                  </div>
                ))}
              </Card>
            </div>

            <Card title="Tendances annuelles — Construction">
              <ResponsiveContainer width="100%" height={240}>
                <LineChart data={CNESST_YEARLY}>
                  <XAxis dataKey="year" stroke="#4a4a6a" fontSize={11} />
                  <YAxis stroke="#4a4a6a" fontSize={11} />
                  <Tooltip content={<CustomTooltip />} />
                  <Line type="monotone" dataKey="lesions" stroke="#9333ea" strokeWidth={2.5} dot={{ r: 4 }} name="Lésions totales" />
                  <Line type="monotone" dataKey="tms" stroke="#f59e0b" strokeWidth={2} dot={{ r: 3 }} name="TMS" />
                  <Line type="monotone" dataKey="machine" stroke="#ef4444" strokeWidth={1.5} dot={{ r: 3 }} name="Machine" />
                  <Line type="monotone" dataKey="psy" stroke="#14b8a6" strokeWidth={1.5} dot={{ r: 3 }} name="Psychologiques" />
                  <Legend wrapperStyle={{ fontSize: 11 }} />
                </LineChart>
              </ResponsiveContainer>
            </Card>
          </>
        )}

        {/* ━━━ COUCHE 2 TAB ━━━ */}
        {activeTab === "couche2" && (
          <>
            <div style={{ marginBottom: 16, display: "flex", alignItems: "center", gap: 8 }}>
              <CoucheTag n={2} />
              <span style={{ fontSize: 18, fontWeight: 800 }}>SAAQ — Accidents en zone de travaux routiers</span>
              <span style={{ fontSize: 12, color: "#8888a0" }}>8 173 accidents | 2020-2022</span>
            </div>

            <div style={{ display: "grid", gridTemplateColumns: "repeat(5, 1fr)", gap: 16, marginBottom: 24 }}>
              <Card><Metric label="Total zone travaux" value="8 173" sub="2.7% du total SAAQ" color="#14b8a6" /></Card>
              <Card><Metric label="Piétons" value="190" sub="dont 108 à MTL" color="#ef4444" /></Card>
              <Card><Metric label="Cyclistes" value="119" sub="dont 91 à MTL" color="#f97316" /></Card>
              <Card><Metric label="Mortels/graves" value="105" sub="1.3% zone travaux" color="#ef4444" /></Card>
              <Card><Metric label="Véh. lourds" value="2 250" sub="27.5% impliqués" color="#f59e0b" /></Card>
            </div>

            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 16, marginBottom: 24 }}>
              <Card title="Répartition par région">
                <ResponsiveContainer width="100%" height={260}>
                  <BarChart data={SAAQ_WORKZONE}>
                    <XAxis dataKey="region" stroke="#4a4a6a" fontSize={10} />
                    <YAxis stroke="#4a4a6a" fontSize={11} />
                    <Tooltip content={<CustomTooltip />} />
                    <Bar dataKey="accidents" fill="#14b8a6" radius={[4, 4, 0, 0]} name="Accidents" />
                    <Bar dataKey="pietons" fill="#ef4444" radius={[4, 4, 0, 0]} name="Piétons" />
                    <Bar dataKey="cyclistes" fill="#f97316" radius={[4, 4, 0, 0]} name="Cyclistes" />
                  </BarChart>
                </ResponsiveContainer>
              </Card>

              <Card title="Distribution horaire — Heures de pointe">
                <ResponsiveContainer width="100%" height={260}>
                  <BarChart data={SAAQ_HOURS}>
                    <XAxis dataKey="hour" stroke="#4a4a6a" fontSize={10} />
                    <YAxis stroke="#4a4a6a" fontSize={11} />
                    <Tooltip content={<CustomTooltip />} />
                    <Bar dataKey="count" name="Accidents" radius={[4, 4, 0, 0]}>
                      {SAAQ_HOURS.map((d, i) => (
                        <Cell key={i} fill={d.pct > 20 ? "#ef4444" : d.pct > 15 ? "#f59e0b" : "#64748b"} />
                      ))}
                    </Bar>
                  </BarChart>
                </ResponsiveContainer>
                <div style={{ fontSize: 11, color: "#f59e0b", marginTop: 8, fontWeight: 600 }}>
                  71.5% des accidents entre 8h et 20h — heures d'activité chantiers
                </div>
              </Card>
            </div>

            <Card title="Montréal — 2 995 accidents zone travaux (36.6%)" style={{ border: "1px solid #f5730630" }}>
              <div style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: 24, padding: "8px 0" }}>
                <Metric label="Piétons MTL" value="108" color="#ef4444" />
                <Metric label="Cyclistes MTL" value="91" color="#f97316" />
                <Metric label="Mortels MTL" value="24" color="#ef4444" />
                <Metric label="Part du Québec" value="36.6%" color="#14b8a6" />
              </div>
            </Card>
          </>
        )}

        {/* ━━━ ZONES TAB ━━━ */}
        {activeTab === "zones" && (
          <>
            <div style={{ marginBottom: 16, display: "flex", alignItems: "center", gap: 8 }}>
              <CoucheTag n={3} />
              <span style={{ fontSize: 18, fontWeight: 800 }}>Zones urbaines Montréal — Score risque composite</span>
              <span style={{ fontSize: 12, color: "#8888a0" }}>Pilote MTL</span>
            </div>

            <div style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: 16, marginBottom: 24 }}>
              {ZONES_MOCK.map(z => (
                <Card key={z.id} style={{ border: `1px solid ${z.severity === "orange" ? "#f9731630" : z.severity === "red" ? "#ef444430" : "#2a2a3e"}` }}>
                  <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: 12 }}>
                    <div>
                      <div style={{ fontSize: 14, fontWeight: 700 }}>{z.name}</div>
                      <div style={{ fontSize: 11, color: "#8888a0" }}>{z.id}</div>
                    </div>
                    <SeverityBadge severity={z.severity} />
                  </div>

                  <div style={{ display: "flex", alignItems: "center", gap: 16, marginBottom: 12 }}>
                    <div style={{ position: "relative", width: 64, height: 64 }}>
                      <svg viewBox="0 0 36 36" style={{ width: 64, height: 64, transform: "rotate(-90deg)" }}>
                        <circle cx="18" cy="18" r="15.5" fill="none" stroke="#1a1a2e" strokeWidth="3" />
                        <circle cx="18" cy="18" r="15.5" fill="none"
                          stroke={z.severity === "red" ? "#ef4444" : z.severity === "orange" ? "#f97316" : z.severity === "yellow" ? "#f59e0b" : "#10b981"}
                          strokeWidth="3" strokeDasharray={`${z.score} ${100 - z.score}`} strokeLinecap="round" />
                      </svg>
                      <div style={{ position: "absolute", top: "50%", left: "50%", transform: "translate(-50%, -50%)", fontSize: 16, fontWeight: 900, fontFamily: "monospace" }}>{z.score}</div>
                    </div>
                    <div style={{ flex: 1 }}>
                      <div style={{ display: "flex", justifyContent: "space-between", fontSize: 11, color: "#8888a0", marginBottom: 4 }}>
                        <span>Chantiers actifs</span><span style={{ color: "#e8e8f0", fontWeight: 600 }}>{z.chantiers}</span>
                      </div>
                      <div style={{ display: "flex", justifyContent: "space-between", fontSize: 11, color: "#8888a0", marginBottom: 4 }}>
                        <span>Flux piétons/jour</span><span style={{ color: "#e8e8f0", fontWeight: 600 }}>{z.flux.toLocaleString()}</span>
                      </div>
                      <div style={{ display: "flex", justifyContent: "space-between", fontSize: 11, color: "#8888a0" }}>
                        <span>HITL requis</span>
                        <span style={{ color: z.severity === "orange" || z.severity === "red" ? "#ef4444" : "#10b981", fontWeight: 600 }}>
                          {z.severity === "orange" || z.severity === "red" ? "OUI" : "Non"}
                        </span>
                      </div>
                    </div>
                  </div>

                  {/* Score decomposition bar */}
                  <div style={{ display: "flex", gap: 2, height: 4, borderRadius: 2, overflow: "hidden" }}>
                    <div style={{ width: "35%", background: "#3b82f6", title: "C1 CNESST" }} />
                    <div style={{ width: "25%", background: "#f59e0b", title: "C2 SAAQ" }} />
                    <div style={{ width: "40%", background: "#9333ea", title: "C3 MTL" }} />
                  </div>
                  <div style={{ display: "flex", justifyContent: "space-between", marginTop: 4, fontSize: 9, color: "#8888a0" }}>
                    <span>C1 35%</span><span>C2 25%</span><span>C3 40%</span>
                  </div>
                </Card>
              ))}
            </div>
          </>
        )}

        {/* ━━━ SIMULATOR TAB ━━━ */}
        {activeTab === "simulator" && (
          <>
            <div style={{ marginBottom: 16, fontSize: 18, fontWeight: 800 }}>Simulateur de score — What-If</div>

            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 24 }}>
              <Card title="Facteurs de modulation">
                <div style={{ marginBottom: 20 }}>
                  <div style={{ display: "flex", justifyContent: "space-between", fontSize: 12, marginBottom: 6 }}>
                    <span>Météo (×{simWeather.toFixed(1)})</span>
                    <span style={{ color: simWeather > 1.1 ? "#f59e0b" : "#8888a0" }}>
                      {simWeather <= 1.0 ? "Beau temps" : simWeather <= 1.2 ? "Pluie" : "Verglas/tempête"}
                    </span>
                  </div>
                  <input type="range" min="1.0" max="1.5" step="0.1" value={simWeather}
                    onChange={e => setSimWeather(parseFloat(e.target.value))}
                    style={{ width: "100%", accentColor: "#9333ea" }} />
                </div>

                <div style={{ marginBottom: 20 }}>
                  <div style={{ display: "flex", justifyContent: "space-between", fontSize: 12, marginBottom: 6 }}>
                    <span>Coactivité (×{simCoactivity.toFixed(1)})</span>
                    <span style={{ color: simCoactivity > 1.2 ? "#ef4444" : "#8888a0" }}>
                      {simCoactivity <= 1.0 ? "Chantier isolé" : simCoactivity <= 1.3 ? "2-3 chantiers adjacents" : "4+ chantiers (critique)"}
                    </span>
                  </div>
                  <input type="range" min="1.0" max="1.5" step="0.1" value={simCoactivity}
                    onChange={e => setSimCoactivity(parseFloat(e.target.value))}
                    style={{ width: "100%", accentColor: "#14b8a6" }} />
                </div>

                <div style={{ padding: 16, background: "#1a1a2e", borderRadius: 8, marginTop: 16 }}>
                  <div style={{ fontSize: 11, color: "#8888a0", marginBottom: 8 }}>FORMULE</div>
                  <div style={{ fontSize: 13, fontFamily: "monospace", color: "#e8e8f0" }}>
                    Score = (C1×0.35 + C2×0.25 + C3×0.40) × Météo × Coactivité
                  </div>
                  <div style={{ fontSize: 12, fontFamily: "monospace", color: "#9333ea", marginTop: 4 }}>
                    = 72 × {simWeather.toFixed(1)} × {simCoactivity.toFixed(1)} = <strong>{simScore}</strong>
                  </div>
                </div>
              </Card>

              <Card title="Résultat du score simulé">
                <div style={{ textAlign: "center", padding: "20px 0" }}>
                  <div style={{ position: "relative", width: 160, height: 160, margin: "0 auto" }}>
                    <svg viewBox="0 0 36 36" style={{ width: 160, height: 160, transform: "rotate(-90deg)" }}>
                      <circle cx="18" cy="18" r="15.5" fill="none" stroke="#1a1a2e" strokeWidth="2.5" />
                      <circle cx="18" cy="18" r="15.5" fill="none"
                        stroke={simScore >= 85 ? "#ef4444" : simScore >= 65 ? "#f97316" : simScore >= 40 ? "#f59e0b" : "#10b981"}
                        strokeWidth="2.5" strokeDasharray={`${simScore} ${100 - simScore}`} strokeLinecap="round"
                        style={{ transition: "stroke-dasharray 0.5s" }} />
                    </svg>
                    <div style={{ position: "absolute", top: "50%", left: "50%", transform: "translate(-50%, -50%)" }}>
                      <div style={{ fontSize: 40, fontWeight: 900, fontFamily: "monospace" }}>{simScore}</div>
                    </div>
                  </div>

                  <div style={{ marginTop: 16 }}>
                    <SeverityBadge severity={getSeverity(simScore)} />
                  </div>

                  {(getSeverity(simScore) === "orange" || getSeverity(simScore) === "red") && (
                    <div style={{
                      marginTop: 16, padding: "10px 16px", borderRadius: 8,
                      background: "#ef444415", border: "1px solid #ef444430",
                      fontSize: 12, color: "#ef4444", fontWeight: 600
                    }}>
                      ⚠️ HITL OBLIGATOIRE — Validation humaine requise (Charte AgenticX5)
                    </div>
                  )}

                  <div style={{ marginTop: 16, fontSize: 11, color: "#8888a0" }}>
                    Profils alertés: {getSeverity(simScore) === "red" ? "TOUS (9/9)" :
                      getSeverity(simScore) === "orange" ? "Piéton, Cycliste, PMR, Coordonnateur" :
                      getSeverity(simScore) === "yellow" ? "Piéton, Cycliste, Coordonnateur" : "Coordonnateur uniquement"}
                  </div>
                </div>
              </Card>
            </div>
          </>
        )}
      </div>

      {/* FOOTER */}
      <div style={{ borderTop: "1px solid #1a1a2e", padding: "12px 24px", display: "flex", justifyContent: "space-between", fontSize: 11, color: "#4a4a6a" }}>
        <span>GenAISafety / Preventera — AX5 UrbanIA v0.1.0</span>
        <span>Primauté de la vie | HITL obligatoire | Charte AgenticX5</span>
      </div>

      <style>{`@keyframes pulse { 0%,100% { opacity:1; } 50% { opacity:0.4; } }`}</style>
    </div>
  );
}
