import { useState, createContext, useContext } from "react";

const TX = {
  fr: {
    brand: "AgenticX5", tagline: "Sécurité prédictive urbaine par IA agentique",
    by: "GenAISafety / Preventera",
    pilotBadge: "Pilote Montréal",
    chainTitle: "Chaîne complète du cycle de vie chantier",
    cs: { title: "ConstrucSync Municipal", sub: "Planification EN AMONT", desc: "Orchestrateur pré-permis qui optimise le séquencement des chantiers, simule les impacts et coordonne les parties prenantes AVANT l'autorisation.", agents: "4 agents", data: "API Montréal live", badge: "AVANT", cta: "Ouvrir ConstrucSync →",
      features: ["PermitOptimizer — scoring prédictif 5 composantes", "TerritoryPlanner — 19 arrondissements, 10 corridors stratégiques", "ImpactSimulator — 3 scénarios what-if", "StakeholderSync — 8 parties prenantes, timeline J-7 à J+14"] },
    ua: { title: "UrbanIA", sub: "Surveillance PENDANT", desc: "Orchestrateur 3 couches qui croise 9 sources de données pour prédire les incidents, protéger les usagers vulnérables et guider la coordination terrain.", agents: "6 agents", data: "9 sources temps réel", badge: "PENDANT", cta: "Ouvrir UrbanIA →",
      features: ["CNESSTLesionsRAG — 54 403 lésions SUR le chantier", "SAAQWorkZone — 8 173 accidents EN TRANSIT", "UrbanFlow — 7 sources MTL AUTOUR", "SafetyGraph — croisement 3 couches, score composite"] },
    kpi: [["10", "Agents IA"], ["9", "Sources données"], ["19", "Arrondissements"], ["54 403", "Lésions analysées"]],
    principles: "Principes fondateurs",
    princ: [["Primauté de la vie", "Chaque décision priorise la sécurité des travailleurs et usagers vulnérables"], ["HITL obligatoire", "Aucun agent ne prend de décision sans validation humaine (≥ orange)"], ["Données ouvertes", "Calibré sur données publiques CNESST, SAAQ, Montréal"], ["Charte AgenticX5", "Conformité C-25, transparence algorithmique, auditabilité"]],
    arch: "Architecture",
    footer: "Licence ouverte · github.com/Preventera/UrbanIA",
  },
  en: {
    brand: "AgenticX5", tagline: "Predictive urban safety through agentic AI",
    by: "GenAISafety / Preventera",
    pilotBadge: "Montreal Pilot",
    chainTitle: "Complete construction site lifecycle chain",
    cs: { title: "ConstrucSync Municipal", sub: "UPSTREAM planning", desc: "Pre-permit orchestrator that optimizes construction sequencing, simulates impacts and coordinates stakeholders BEFORE authorization.", agents: "4 agents", data: "Montreal API live", badge: "BEFORE", cta: "Open ConstrucSync →",
      features: ["PermitOptimizer — 5-component predictive scoring", "TerritoryPlanner — 19 boroughs, 10 strategic corridors", "ImpactSimulator — 3 what-if scenarios", "StakeholderSync — 8 stakeholders, J-7 to J+14 timeline"] },
    ua: { title: "UrbanIA", sub: "DURING surveillance", desc: "3-layer orchestrator crossing 9 data sources to predict incidents, protect vulnerable users and guide field coordination.", agents: "6 agents", data: "9 real-time sources", badge: "DURING", cta: "Open UrbanIA →",
      features: ["CNESSTLesionsRAG — 54,403 injuries ON the site", "SAAQWorkZone — 8,173 accidents IN TRANSIT", "UrbanFlow — 7 MTL sources AROUND", "SafetyGraph — 3-layer crossover, composite score"] },
    kpi: [["10", "AI Agents"], ["9", "Data Sources"], ["19", "Boroughs"], ["54,403", "Injuries Analyzed"]],
    principles: "Core Principles",
    princ: [["Life Primacy", "Every decision prioritizes worker and vulnerable user safety"], ["HITL Mandatory", "No agent decides without human validation (≥ orange)"], ["Open Data", "Calibrated on public CNESST, SAAQ, Montreal data"], ["AgenticX5 Charter", "C-25 compliance, algorithmic transparency, auditability"]],
    arch: "Architecture",
    footer: "Open license · github.com/Preventera/UrbanIA",
  },
};
const LCtx = createContext("fr");

const P = { bg: "#07070F", card: "#0F0F1A", navy: "#181830", purple: "#9333EA", teal: "#14B8A6", red: "#EF4444", orange: "#F97316", yellow: "#F59E0B", green: "#10B981", white: "#FFF", gray: "#7878A0", text: "#E2E2F0", dim: "#50506A", blue: "#3B82F6" };

const ModuleCard = ({ module, color, icon, onClick }) => {
  const [hover, setHover] = useState(false);
  return (
    <div onMouseEnter={() => setHover(true)} onMouseLeave={() => setHover(false)} onClick={onClick}
      style={{ flex: 1, background: hover ? `${color}08` : P.card, border: `1px solid ${hover ? color + "40" : P.navy}`, borderRadius: 16, padding: 24, cursor: "pointer", transition: "all 0.3s", transform: hover ? "translateY(-2px)" : "none" }}>
      <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 12 }}>
        <div style={{ width: 40, height: 40, borderRadius: 10, background: `linear-gradient(135deg, ${color}, ${color}80)`, display: "flex", alignItems: "center", justifyContent: "center", fontSize: 18, fontWeight: 900, color: P.white }}>{icon}</div>
        <div>
          <div style={{ fontSize: 18, fontWeight: 800, color: P.text }}>{module.title}</div>
          <div style={{ fontSize: 11, color }}>{module.sub}</div>
        </div>
        <span style={{ marginLeft: "auto", padding: "2px 10px", borderRadius: 20, fontSize: 10, fontWeight: 700, background: `${color}15`, color, border: `1px solid ${color}30` }}>{module.badge}</span>
      </div>
      <div style={{ fontSize: 13, color: P.gray, lineHeight: 1.5, marginBottom: 16 }}>{module.desc}</div>
      <div style={{ display: "flex", gap: 12, marginBottom: 16 }}>
        <span style={{ padding: "3px 10px", background: P.navy, borderRadius: 6, fontSize: 11, color: P.text }}>{module.agents}</span>
        <span style={{ padding: "3px 10px", background: P.navy, borderRadius: 6, fontSize: 11, color: P.text }}>{module.data}</span>
      </div>
      {module.features.map((f, i) => (
        <div key={i} style={{ display: "flex", gap: 6, marginBottom: 5 }}>
          <span style={{ color, fontSize: 10, marginTop: 2 }}>▸</span>
          <span style={{ fontSize: 11, color: P.gray }}>{f}</span>
        </div>
      ))}
      <div style={{ marginTop: 16, padding: "8px 0", textAlign: "center", borderRadius: 8, background: hover ? color : `${color}15`, color: hover ? P.white : color, fontSize: 13, fontWeight: 700, transition: "all 0.3s" }}>{module.cta}</div>
    </div>
  );
};

export default function AX5Landing() {
  const [lang, setLang] = useState("fr");
  const [active, setActive] = useState(null);
  const t = TX[lang];

  if (active) {
    return (
      <div style={{ minHeight: "100vh", background: P.bg, color: P.text, fontFamily: "'Segoe UI', sans-serif" }}>
        <div style={{ padding: "8px 20px", background: P.card, borderBottom: `1px solid ${P.navy}`, display: "flex", alignItems: "center", gap: 12 }}>
          <button onClick={() => setActive(null)} style={{ background: P.navy, border: "none", borderRadius: 6, color: P.gray, padding: "4px 12px", cursor: "pointer", fontSize: 12 }}>← {lang === "fr" ? "Accueil" : "Home"}</button>
          <span style={{ fontSize: 13, color: P.gray }}>{active === "cs" ? t.cs.title : t.ua.title}</span>
          <div style={{ marginLeft: "auto", display: "flex", borderRadius: 6, overflow: "hidden", border: `1px solid ${P.dim}` }}>
            {["fr", "en"].map(l => (<button key={l} onClick={() => setLang(l)} style={{ padding: "3px 10px", background: lang === l ? P.purple : "transparent", color: lang === l ? P.white : P.gray, border: "none", fontSize: 10, fontWeight: 700, cursor: "pointer" }}>{l.toUpperCase()}</button>))}
          </div>
        </div>
        <div style={{ padding: 40, textAlign: "center", color: P.gray }}>
          <div style={{ fontSize: 48, marginBottom: 12 }}>{active === "cs" ? "🏗️" : "🛡️"}</div>
          <div style={{ fontSize: 16, marginBottom: 6 }}>{active === "cs" ? t.cs.title : t.ua.title}</div>
          <div style={{ fontSize: 12 }}>{lang === "fr" ? "Ouvre le fichier JSX correspondant dans Claude.ai pour la démo interactive complète" : "Open the corresponding JSX file in Claude.ai for the full interactive demo"}</div>
          <div style={{ marginTop: 12, padding: "6px 16px", display: "inline-block", background: P.navy, borderRadius: 8, fontSize: 11, color: P.text, fontFamily: "monospace" }}>
            dashboards/AX5-{active === "cs" ? "ConstrucSync" : "UrbanIA"}-Dashboard-Live.jsx
          </div>
        </div>
      </div>
    );
  }

  return (
    <LCtx.Provider value={lang}>
      <div style={{ minHeight: "100vh", background: P.bg, color: P.text, fontFamily: "'Segoe UI', -apple-system, sans-serif" }}>
        {/* HERO */}
        <div style={{ textAlign: "center", padding: "48px 24px 32px" }}>
          <div style={{ display: "inline-flex", alignItems: "center", gap: 12, marginBottom: 16 }}>
            <div style={{ width: 48, height: 48, borderRadius: 12, background: `linear-gradient(135deg, ${P.purple}, ${P.teal})`, display: "flex", alignItems: "center", justifyContent: "center", fontSize: 22, fontWeight: 900, color: P.white }}>X5</div>
            <div style={{ textAlign: "left" }}>
              <div style={{ fontSize: 28, fontWeight: 900, letterSpacing: -1 }}>{t.brand}</div>
              <div style={{ fontSize: 11, color: P.gray }}>{t.by}</div>
            </div>
          </div>
          <div style={{ fontSize: 18, color: P.gray, maxWidth: 600, margin: "0 auto 16px", lineHeight: 1.5 }}>{t.tagline}</div>
          <div style={{ display: "inline-flex", gap: 8 }}>
            <span style={{ padding: "3px 12px", borderRadius: 20, fontSize: 10, fontWeight: 700, background: `${P.green}15`, color: P.green, border: `1px solid ${P.green}30` }}>{t.pilotBadge}</span>
            <span style={{ padding: "3px 12px", borderRadius: 20, fontSize: 10, fontWeight: 700, background: `${P.orange}15`, color: P.orange, border: `1px solid ${P.orange}30` }}>HITL</span>
            <span style={{ padding: "3px 12px", borderRadius: 20, fontSize: 10, fontWeight: 700, background: `${P.teal}15`, color: P.teal, border: `1px solid ${P.teal}30` }}>AgenticX5</span>
            <div style={{ display: "flex", borderRadius: 20, overflow: "hidden", border: `1px solid ${P.dim}` }}>
              {["fr", "en"].map(l => (<button key={l} onClick={() => setLang(l)} style={{ padding: "3px 12px", background: lang === l ? P.purple : "transparent", color: lang === l ? P.white : P.gray, border: "none", fontSize: 10, fontWeight: 700, cursor: "pointer" }}>{l.toUpperCase()}</button>))}
            </div>
          </div>
        </div>

        {/* KPIs */}
        <div style={{ display: "flex", justifyContent: "center", gap: 24, marginBottom: 32 }}>
          {t.kpi.map(([v, l], i) => (
            <div key={i} style={{ textAlign: "center", padding: "8px 20px", background: P.card, borderRadius: 10, border: `1px solid ${P.navy}`, minWidth: 100 }}>
              <div style={{ fontSize: 24, fontWeight: 900, color: [P.purple, P.teal, P.blue, P.orange][i], fontFamily: "monospace" }}>{v}</div>
              <div style={{ fontSize: 10, color: P.gray, marginTop: 2 }}>{l}</div>
            </div>
          ))}
        </div>

        {/* CHAIN */}
        <div style={{ textAlign: "center", marginBottom: 12 }}>
          <span style={{ fontSize: 12, color: P.dim, textTransform: "uppercase", letterSpacing: 2 }}>{t.chainTitle}</span>
        </div>
        <div style={{ display: "flex", alignItems: "center", justifyContent: "center", gap: 8, marginBottom: 24, padding: "0 24px" }}>
          <div style={{ flex: "0 0 auto", textAlign: "center", padding: "6px 14px", background: `${P.purple}15`, borderRadius: 8, border: `1px solid ${P.purple}30` }}>
            <div style={{ fontSize: 11, fontWeight: 700, color: P.purple }}>📋 {lang === "fr" ? "Demande permis" : "Permit request"}</div>
          </div>
          <div style={{ fontSize: 20, color: P.dim }}>→</div>
          <div style={{ flex: "0 0 auto", textAlign: "center", padding: "6px 14px", background: `${P.teal}15`, borderRadius: 8, border: `1px solid ${P.teal}30` }}>
            <div style={{ fontSize: 11, fontWeight: 700, color: P.teal }}>🏗️ ConstrucSync</div>
            <div style={{ fontSize: 9, color: P.dim }}>{t.cs.badge}</div>
          </div>
          <div style={{ fontSize: 20, color: P.dim }}>→</div>
          <div style={{ flex: "0 0 auto", textAlign: "center", padding: "6px 14px", background: `${P.orange}15`, borderRadius: 8, border: `1px solid ${P.orange}30` }}>
            <div style={{ fontSize: 11, fontWeight: 700, color: P.orange }}>✅ {lang === "fr" ? "Autorisation" : "Authorization"}</div>
          </div>
          <div style={{ fontSize: 20, color: P.dim }}>→</div>
          <div style={{ flex: "0 0 auto", textAlign: "center", padding: "6px 14px", background: `${P.blue}15`, borderRadius: 8, border: `1px solid ${P.blue}30` }}>
            <div style={{ fontSize: 11, fontWeight: 700, color: P.blue }}>🛡️ UrbanIA</div>
            <div style={{ fontSize: 9, color: P.dim }}>{t.ua.badge}</div>
          </div>
          <div style={{ fontSize: 20, color: P.dim }}>→</div>
          <div style={{ flex: "0 0 auto", textAlign: "center", padding: "6px 14px", background: `${P.green}15`, borderRadius: 8, border: `1px solid ${P.green}30` }}>
            <div style={{ fontSize: 11, fontWeight: 700, color: P.green }}>🔔 {lang === "fr" ? "Alertes terrain" : "Field alerts"}</div>
          </div>
        </div>

        {/* MODULES */}
        <div style={{ display: "flex", gap: 20, padding: "0 24px", marginBottom: 32 }}>
          <ModuleCard module={t.cs} color={P.teal} icon="CS" onClick={() => setActive("cs")} />
          <ModuleCard module={t.ua} color={P.purple} icon="U" onClick={() => setActive("ua")} />
        </div>

        {/* PRINCIPLES */}
        <div style={{ padding: "0 24px", marginBottom: 32 }}>
          <div style={{ textAlign: "center", fontSize: 12, color: P.dim, textTransform: "uppercase", letterSpacing: 2, marginBottom: 12 }}>{t.principles}</div>
          <div style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: 12 }}>
            {t.princ.map(([title, desc], i) => (
              <div key={i} style={{ padding: "14px 16px", background: P.card, borderRadius: 10, border: `1px solid ${P.navy}`, borderTop: `2px solid ${[P.red, P.orange, P.teal, P.purple][i]}` }}>
                <div style={{ fontSize: 13, fontWeight: 700, color: P.text, marginBottom: 4 }}>{title}</div>
                <div style={{ fontSize: 11, color: P.gray, lineHeight: 1.4 }}>{desc}</div>
              </div>
            ))}
          </div>
        </div>

        {/* FOOTER */}
        <div style={{ padding: "12px 24px", borderTop: `1px solid ${P.navy}`, textAlign: "center", fontSize: 10, color: P.dim }}>
          {t.footer}
        </div>
      </div>
    </LCtx.Provider>
  );
}
