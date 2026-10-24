"""Multimodal Construction Intelligence Platform (Skill Wallet Capstone Project 1)."""
import json
import re
import urllib.parse

import streamlit as st
from PIL import Image

st.set_page_config(page_title="Construction Intelligence Platform", page_icon="🏗️", layout="wide")

# ----------------------------------------------------------------- styling
st.markdown("""
<style>
.hero{padding:1.2rem 1.5rem;border-radius:14px;background:linear-gradient(120deg,#F59E0B,#EA580C);color:#fff;margin-bottom:1rem}
.hero h1{margin:0;font-size:1.8rem}.hero p{margin:.2rem 0 0;opacity:.9}
.card{background:#1E293B;border:1px solid #334155;border-radius:12px;padding:1rem;text-align:center}
.card .v{font-size:1.7rem;font-weight:700;color:#F59E0B}.card .l{font-size:.8rem;color:#94A3B8}
.pill{display:inline-block;padding:.2rem .7rem;border-radius:999px;font-weight:600;font-size:.8rem}
.Low,.PASS,.Compliant{background:#065F46;color:#A7F3D0}
.Medium,.Warning,.Monitor{background:#92400E;color:#FDE68A}
.High,.FAIL,.NonCompliant,.Urgent{background:#9A3412;color:#FED7AA}
.Critical,.Immediate{background:#991B1B;color:#FECACA}
</style>""", unsafe_allow_html=True)

st.markdown('<div class="hero"><h1>🏗️ Multimodal Construction Intelligence Platform</h1>'
            '<p>PPE safety audit • Crack diagnostics • Cost & valuation • Weather-aware site advisory</p></div>',
            unsafe_allow_html=True)

# ----------------------------------------------------------------- helpers
def card(label, value):
    return f'<div class="card"><div class="v">{value}</div><div class="l">{label}</div></div>'

def pill(text):
    cls = re.sub(r"[^A-Za-z]", "", str(text))
    return f'<span class="pill {cls}">{text}</span>'

def inr(v):
    """Format rupees into Lakhs / Crores."""
    if v >= 1e7:
        return f"₹{v/1e7:,.2f} Cr"
    return f"₹{v/1e5:,.2f} L"

def parse_json(text):
    text = re.sub(r"^```(?:json)?|```$", "", text.strip(), flags=re.M).strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        m = re.search(r"\{.*\}", text, re.S)
        if m:
            return json.loads(m.group(0))
        raise

def get_client():
    key = st.session_state.get("api_key", "").strip()
    if not key:
        return None
    from google import genai
    return genai.Client(api_key=key)

def gemini_vision(prompt, image):
    """Returns (dict, error). Falls back to None when no key."""
    client = get_client()
    if client is None:
        return None, None
    try:
        from google.genai import types
        resp = client.models.generate_content(
            model=st.session_state.model, contents=[prompt, image],
            config=types.GenerateContentConfig(response_mime_type="application/json", temperature=0.2))
        return parse_json(resp.text), None
    except Exception as e:  # noqa
        return None, str(e)

def gemini_chat(history, system):
    client = get_client()
    if client is None:
        return None
    from google.genai import types
    contents = [types.Content(role="user" if m["role"] == "user" else "model",
                              parts=[types.Part(text=m["content"])]) for m in history]
    resp = client.models.generate_content(
        model=st.session_state.model, contents=contents,
        config=types.GenerateContentConfig(system_instruction=system, temperature=0.4))
    return resp.text

# ----------------------------------------------------------------- prompts
PPE_PROMPT = """You are a certified construction safety auditor (OSHA 1926 and IS 456 / NBC India aware).
Analyze this construction site photo. Return ONLY JSON:
{"safety_score":0-100,"overall_status":"Compliant|Warning|NonCompliant",
"ppe_detection":{"helmet":{"detected":bool,"note":""},"high_vis_vest":{"detected":bool,"note":""},
"steel_toe_boots":{"detected":bool,"note":""},"safety_harness":{"detected":bool,"note":""}},
"workers_count":int,
"hazards":[{"hazard":"","severity":"Low|Medium|High|Critical","remedy":""}],
"summary":""}"""

CRACK_PROMPT = """You are a structural engineer. Analyze this concrete/wall surface image. Return ONLY JSON:
{"defect_type":"Hairline|Settlement|Structural Shear|Thermal Expansion|Spalling",
"estimated_width_mm":float,"severity_score":1-10,"urgency":"Monitor|Urgent|Immediate",
"root_causes":["..."],"recommended_repairs":["e.g. epoxy injection, structural re-grouting"],
"monitoring_advice":"","summary":""}"""

DEMO_PPE = {"safety_score": 62, "overall_status": "Warning", "workers_count": 3,
    "ppe_detection": {"helmet": {"detected": True, "note": "2 of 3 workers wearing helmets"},
                      "high_vis_vest": {"detected": True, "note": "Vests present on all workers"},
                      "steel_toe_boots": {"detected": False, "note": "Sneakers/sandals observed"},
                      "safety_harness": {"detected": False, "note": "No harness at elevated edge"}},
    "hazards": [{"hazard": "Unprotected edge at height", "severity": "Critical", "remedy": "Install guardrails and mandate full-body harness with anchor points."},
                {"hazard": "Loose rebar and debris on walkway", "severity": "Medium", "remedy": "Daily housekeeping; cap exposed rebar ends."},
                {"hazard": "Missing helmet on one worker", "severity": "High", "remedy": "Enforce no-helmet-no-entry at site gate."}],
    "summary": "DEMO MODE: sample output. Add a Gemini API key for real image analysis."}
DEMO_CRACK = {"defect_type": "Structural Shear", "estimated_width_mm": 2.4, "severity_score": 7,
    "urgency": "Urgent", "root_causes": ["Excess shear load near support", "Inadequate stirrup spacing", "Differential settlement"],
    "recommended_repairs": ["Epoxy injection for cracks >0.3 mm", "Structural re-grouting", "Jacketing / FRP wrapping of the member"],
    "monitoring_advice": "Install crack gauges; re-inspect every 2 weeks.",
    "summary": "DEMO MODE: sample output. Add a Gemini API key for real image analysis."}

# ----------------------------------------------------------------- sidebar
with st.sidebar:
    st.header("⚙️ Configuration")
    st.session_state.api_key = st.text_input("Google Gemini API Key", type="password",
                                             value=st.session_state.get("api_key", ""),
                                             help="Leave blank for Demo Mode. Key is kept in session only.")
    st.session_state.model = st.text_input("Model", value=st.session_state.get("model", "gemini-2.5-flash"))
    st.success("🟢 Live AI mode") if st.session_state.api_key.strip() else st.warning("🟡 Demo mode (no key)")
    st.markdown("---")
    st.subheader("🧭 Architecture")
    st.markdown("""
1. **Streamlit UI** (4 tabs)
2. **Prompt layer** → strict JSON contracts
3. **Gemini multimodal** vision/chat
4. **Rule engine** for cost & valuation
5. **Pollinations** concept renders

*Zero database, stateless, 1-click deploy.*""")
    st.caption("Epics 1–6 • Skill Wallet Capstone")

# ----------------------------------------------------------------- tabs
t1, t2, t3, t4 = st.tabs(["🦺 Safety & PPE", "🧱 Crack Diagnostics", "💰 Planning & Valuation", "🌦️ Site Assistant"])

def analyze_tab(prompt, demo, key):
    up = st.file_uploader("Upload image (JPG/PNG)", type=["jpg", "jpeg", "png"], key=key)
    if not up:
        return None
    try:
        img = Image.open(up).convert("RGB")
    except Exception:
        st.error("Could not read that image. Please upload a valid JPG/PNG.")
        return None
    c1, c2 = st.columns([1, 1.4])
    c1.image(img, use_container_width=True)
    if c2.button("🔍 Analyze", key=key + "_btn", type="primary"):
        with st.spinner("Analyzing..."):
            data, err = gemini_vision(prompt, img)
        if err:
            st.error(f"AI call failed: {err}. Showing demo output instead.")
        st.session_state[key + "_res"] = data or demo
    return st.session_state.get(key + "_res")

with t1:
    st.subheader("Site Safety & PPE Audit")
    r = analyze_tab(PPE_PROMPT, DEMO_PPE, "ppe")
    if r:
        try:
            a, b, c = st.columns(3)
            a.markdown(card("Safety Score", f'{r["safety_score"]}/100'), unsafe_allow_html=True)
            b.markdown(card("Workers Detected", r.get("workers_count", "—")), unsafe_allow_html=True)
            c.markdown(card("Status", pill(r["overall_status"])), unsafe_allow_html=True)
            st.progress(min(max(int(r["safety_score"]), 0), 100) / 100)
            st.markdown("#### PPE Checklist")
            cols = st.columns(4)
            for col, (k, v) in zip(cols, r["ppe_detection"].items()):
                col.markdown(f"**{k.replace('_', ' ').title()}**  \n{'✅' if v['detected'] else '❌'} {v.get('note', '')}")
            st.markdown("#### Hazards")
            for h in r.get("hazards", []):
                st.markdown(f'{pill(h["severity"])} **{h["hazard"]}** — {h["remedy"]}', unsafe_allow_html=True)
            st.info(r.get("summary", ""))
            st.download_button("⬇️ Download JSON report", json.dumps(r, indent=2), "ppe_report.json", "application/json")
        except (KeyError, TypeError):
            st.error("Unexpected AI response format. Try again.")
            st.json(r)

with t2:
    st.subheader("Crack Diagnostics & Structural Integrity")
    r = analyze_tab(CRACK_PROMPT, DEMO_CRACK, "crack")
    if r:
        try:
            a, b, c, d = st.columns(4)
            a.markdown(card("Defect Type", r["defect_type"]), unsafe_allow_html=True)
            b.markdown(card("Width (mm)", r["estimated_width_mm"]), unsafe_allow_html=True)
            c.markdown(card("Severity", f'{r["severity_score"]}/10'), unsafe_allow_html=True)
            d.markdown(card("Urgency", pill(r["urgency"])), unsafe_allow_html=True)
            l, rr = st.columns(2)
            l.markdown("#### Root Causes")
            for x in r["root_causes"]:
                l.markdown(f"- {x}")
            rr.markdown("#### Recommended Repairs")
            for x in r["recommended_repairs"]:
                rr.markdown(f"- {x}")
            st.warning(r.get("monitoring_advice", ""))
            st.info(r.get("summary", ""))
            st.download_button("⬇️ Download JSON report", json.dumps(r, indent=2), "crack_report.json", "application/json")
        except (KeyError, TypeError):
            st.error("Unexpected AI response format. Try again.")
            st.json(r)

with t3:
    st.subheader("Project Planning & Real Estate Valuation (INR)")
    COST = {"Residential (RCC Frame)": 1800, "Commercial Building": 2500, "Industrial Shed (PEB)": 1600,
            "Villa / Premium": 3200, "Basement + Parking": 2200}
    TIER = {"Tier 1 (Mumbai, Delhi, Bengaluru)": (1.25, 12000), "Tier 2 (Bhopal, Indore, Jaipur)": (1.0, 5500),
            "Tier 3 (Smaller cities)": (0.85, 3000)}
    c1, c2 = st.columns(2)
    stype = c1.selectbox("Structure type", list(COST))
    tier = c2.selectbox("Location tier", list(TIER))
    sqft = c1.number_input("Built-up area (sq ft)", 200, 500000, 2000, 100)
    pct = c2.slider("Completion %", 0, 100, 40)
    mult, market = TIER[tier]
    budget = sqft * COST[stype] * mult
    capex = budget * pct / 100
    # market value: land+building at market rate, discounted for unfinished build
    value = sqft * market * (0.35 + 0.65 * pct / 100)
    steel_t = sqft * 4.0 / 1000      # ~4 kg/sqft
    cement_bags = sqft * 0.4          # ~0.4 bag/sqft
    a, b, c, d = st.columns(4)
    a.markdown(card("Total Budget", inr(budget)), unsafe_allow_html=True)
    b.markdown(card("CapEx Incurred", inr(capex)), unsafe_allow_html=True)
    c.markdown(card("Market Valuation", inr(value)), unsafe_allow_html=True)
    d.markdown(card("Steel / Cement", f"{steel_t:.1f} t / {cement_bags:,.0f} bags"), unsafe_allow_html=True)
    st.markdown("#### Milestone Progress")
    st.progress(pct / 100)
    ms = [(0, "Foundation"), (25, "Plinth & Columns"), (50, "Slab & Structure"), (75, "Masonry & MEP"), (100, "Finishing")]
    st.caption(" → ".join(("✅ " if pct >= p else "⬜ ") + n for p, n in ms))
    st.caption("Estimates are indicative rules of thumb, not a quotation.")
    st.markdown("#### 🎨 Conceptual 3D Rendering")
    style = st.text_input("Describe the building", f"modern {stype.split('(')[0].strip().lower()}, {tier.split(' ')[0]} India, golden hour")
    if st.button("Generate render"):
        p = f"architectural 3D rendering, {style}, photorealistic, {int(sqft)} sq ft, Indian architecture"
        st.image(f"https://image.pollinations.ai/prompt/{urllib.parse.quote(p)}?width=1024&height=640&nologo=true",
                 caption="Generated via Pollinations AI", use_container_width=True)

with t4:
    st.subheader("Daily Site Assistant & Weather Advisory")
    ALERTS = {
        "Normal": ("success", ["Standard toolbox talk at shift start.", "Routine inspection of scaffolds and lifting gear."]),
        "High Wind": ("error", ["Suspend crane and hoist operations above ~36 km/h wind.", "Secure loose sheets, formwork and scaffold cladding.",
                                "Halt work at height; evacuate edges and tower cranes."]),
        "Heavy Rain": ("error", ["Electrical hazard: de-energize temporary panels; check earthing/RCCB.", "Cover fresh concrete; stop pours.",
                                 "Pump out excavations; check slope stability and slippery access."]),
        "Extreme Heat": ("warning", ["Concrete curing protocol: pour early/evening, use chilled water, wet-cure 7+ days.",
                                     "Mandatory hydration/rest breaks; watch for heat stress.", "Limit steel handling in direct sun."]),
    }
    w = st.selectbox("Today's weather", list(ALERTS))
    kind, items = ALERTS[w]
    getattr(st, kind)("**" + w + " Protocol**\n\n" + "\n".join(f"- {i}" for i in items))
    st.markdown("#### 💬 Engineering Assistant")
    SYSTEM = (f"You are a senior Indian construction engineer. Answer concisely, cite IS codes (IS 456, IS 800, NBC 2016) "
              f"where relevant, and prioritise safety. Current site weather: {w}.")
    if "chat" not in st.session_state:
        st.session_state.chat = [{"role": "assistant", "content": "Hi! Ask me about mix design, curing, rebar, safety or scheduling."}]
    for m in st.session_state.chat:
        st.chat_message(m["role"]).write(m["content"])
    if q := st.chat_input("Ask a construction question..."):
        st.session_state.chat.append({"role": "user", "content": q})
        st.chat_message("user").write(q)
        try:
            ans = gemini_chat(st.session_state.chat, SYSTEM)
            if ans is None:
                ans = ("*(Demo mode)* Add a Gemini API key in the sidebar for live answers. "
                       "Rule of thumb: cure concrete at least 7 days (OPC) per IS 456.")
        except Exception as e:  # noqa
            ans = f"Sorry, the AI call failed: {e}"
        st.session_state.chat.append({"role": "assistant", "content": ans})
        st.chat_message("assistant").write(ans)
    if st.button("Clear chat"):
        del st.session_state["chat"]
        st.rerun()
