import streamlit as st
import pandas as pd
import numpy as np
import re
import plotly.express as px
from openai import OpenAI
import os
import duckdb
from sqlalchemy import create_engine
import urllib.parse
import psutil
import time
import streamlit.components.v1 as components
import base64
import sqlite3
import hashlib
import socket
import uuid as _uuid_mod
from datetime import datetime, timedelta
import json

APP_VERSION = "v3.0 – Cosmic Evolution"

st.set_page_config(
    page_title="AI BI Copilot | Cosmic",
    layout="wide",
    page_icon="🤖",
    initial_sidebar_state="expanded",
)

IS_CLOUD = "STREAMLIT_SERVER_PORT" in os.environ

# ─────────────────────────────────────────────────────────────
#  GLOBAL CSS  — Design System
# ─────────────────────────────────────────────────────────────
st.markdown('<link href="https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;500;600;700;800&family=Inter:wght@300;400;500;600;700&display=swap" rel="stylesheet">', unsafe_allow_html=True)
_css_content = r"""
:root{--pink:#D53F8C;--pink-dark:#B83280;--bg:#0B0E14;--sidebar:#0E1117;--card:rgba(255,255,255,0.025);--border:rgba(255,255,255,0.07);}
html,body,.stApp{background:#0B0E14!important;color:#E2E8F0!important;}
*{font-family:'Inter',sans-serif!important;box-sizing:border-box;}
h1,h2,h3,h4,.outfit{font-family:'Outfit',sans-serif!important;}

/* ===== HIDE STREAMLIT CHROME ===== */
#MainMenu,footer,header,[data-testid="stToolbar"]{visibility:hidden!important;height:0!important;display:none!important;}
.stDeployButton{display:none!important;}
[data-testid="stHeader"]{background:transparent!important;}

/* Bridge hiding - improved to avoid display:none issues with events */
div[data-testid="stTextInput"]:has(input[aria-label="__bridge__"]) {
    position: fixed !important;
    top: -1000px !important;
    left: -1000px !important;
    opacity: 0 !important;
    height: 0 !important;
    width: 0 !important;
    overflow: hidden !important;
    pointer-events: none !important;
}

iframe[title="streamlit.components.v1.html"] { display: block !important; margin: 0 auto !important; border: none !important; }
.stMarkdown { display: block !important; }
[data-testid="stAppViewContainer"] { background: #0B0E14 !important; }

/* ===== SIDEBAR ===== */
[data-testid="stSidebar"]{background:#0E1117!important;border-right:1px solid rgba(255,255,255,0.05)!important;}
[data-testid="stSidebar"] *{color:#CBD5E1!important;}
[data-testid="stSidebar"] h1,[data-testid="stSidebar"] h2,[data-testid="stSidebar"] h3{color:#E2E8F0!important;}
[data-testid="stSidebar"] .stButton>button{background:rgba(255,255,255,0.04)!important;color:#CBD5E1!important;border:1px solid rgba(255,255,255,0.1)!important;border-radius:12px!important;font-weight:600!important;font-size:0.82rem!important;padding:8px 14px!important;transition:all .2s!important;}
[data-testid="stSidebar"] .stButton>button:hover{background:rgba(213,63,140,0.12)!important;color:#D53F8C!important;border-color:rgba(213,63,140,0.35)!important;}
[data-testid="stSidebar"] .stButton>button[kind="primary"]{background:rgba(213,63,140,0.15)!important;color:#D53F8C!important;border:1px solid rgba(213,63,140,0.4)!important;}
[data-testid="stSidebar"] [data-testid="stFileUploader"]>section{background:rgba(255,255,255,0.02)!important;border:1px dashed rgba(255,255,255,0.12)!important;border-radius:12px!important;}
[data-testid="stSidebar"] [data-testid="stFileUploader"] section *{color:#CBD5E1!important;}
[data-testid="stSidebar"] [data-testid="stFileUploader"] [data-testid="stBaseButton-secondary"]{background:#fff!important;color:#000!important;border:none!important;}

/* ===== KPI CARDS ===== */
.kpi-card{background:rgba(255,255,255,0.02);border:1px solid rgba(255,255,255,0.06);border-radius:20px;padding:24px;text-align:center;transition:all .3s cubic-bezier(0.4,0,0.2,1);cursor:default;}
.kpi-card:hover{background:rgba(213,63,140,0.05);border-color:rgba(213,63,140,0.3);transform:translateY(-4px);box-shadow:0 12px 40px -10px rgba(213,63,140,0.15);}
.kpi-label{font-family:'Outfit',sans-serif;font-size:0.75rem;font-weight:700;color:#64748B;text-transform:uppercase;letter-spacing:0.1em;margin-bottom:8px;}
.kpi-value{font-family:'Outfit',sans-serif;font-size:1.8rem;font-weight:800;color:#E2E8F0;}

/* ===== INPUTS ===== */
.stTextInput>div>div>input,.stTextArea>div>div>textarea{background:rgba(255,255,255,0.04)!important;border:1px solid rgba(255,255,255,0.1)!important;border-radius:14px!important;color:#E2E8F0!important;padding:12px 16px!important;font-size:0.88rem!important;}
.stTextInput>div>div>input:focus,.stTextArea>div>div>textarea:focus{border-color:#D53F8C!important;box-shadow:0 0 0 3px rgba(213,63,140,0.12)!important;outline:none!important;}
.stTextInput label,.stTextArea label,.stSelectbox label,.stNumberInput label{color:#64748B!important;font-size:0.7rem!important;font-weight:700!important;text-transform:uppercase!important;letter-spacing:.1em!important;}
.stSelectbox>div>div>div{background:rgba(255,255,255,0.04)!important;border:1px solid rgba(255,255,255,0.1)!important;border-radius:12px!important;color:#E2E8F0!important;}

/* ===== BUTTONS ===== */
.stButton>button[kind="primary"]{background:#D53F8C!important;color:#fff!important;border:none!important;border-radius:14px!important;font-weight:700!important;font-size:0.88rem!important;padding:11px 22px!important;transition:all .2s!important;box-shadow:0 4px 20px -6px rgba(213,63,140,0.5)!important;}
.stButton>button[kind="primary"]:hover{background:#B83280!important;transform:translateY(-1px)!important;box-shadow:0 8px 25px -6px rgba(213,63,140,0.5)!important;}
.stButton>button[kind="secondary"]{background:rgba(255,255,255,0.04)!important;color:#CBD5E1!important;border:1px solid rgba(255,255,255,0.1)!important;border-radius:14px!important;font-weight:600!important;transition:all .2s!important;}
.stButton>button[kind="secondary"]:hover{background:rgba(255,255,255,0.08)!important;border-color:rgba(255,255,255,0.18)!important;}

/* ===== TABS ===== */
.stTabs [data-baseweb="tab-list"]{background:rgba(255,255,255,0.02)!important;border:1px solid rgba(255,255,255,0.07)!important;border-radius:14px!important;padding:4px!important;gap:4px!important;}
.stTabs [data-baseweb="tab"]{border-radius:10px!important;color:#64748B!important;font-weight:600!important;font-size:0.85rem!important;padding:8px 18px!important;}
.stTabs [aria-selected="true"]{background:#D53F8C!important;color:#fff!important;}
.stTabs [data-baseweb="tab"] *{color:inherit!important;}
[data-testid="stTabContent"]{padding-top:16px!important;}

/* ===== METRIC ===== */
[data-testid="stMetric"]{background:rgba(255,255,255,0.03)!important;border:1px solid rgba(255,255,255,0.07)!important;border-radius:18px!important;padding:18px!important;}
[data-testid="stMetricValue"]{color:#F1F5F9!important;font-family:'Outfit',sans-serif!important;}
[data-testid="stMetricLabel"]{color:#64748B!important;font-size:.72rem!important;}

/* ===== DATAFRAME ===== */
[data-testid="stDataFrame"]{border-radius:16px!important;overflow:hidden!important;border:1px solid rgba(255,255,255,0.07)!important;}

/* ===== ALERTS ===== */
.stAlert{border-radius:12px!important;}
div[data-testid="stInfoBox"]{background:rgba(99,102,241,0.08)!important;border-color:rgba(99,102,241,0.25)!important;}
div[data-testid="stWarningBox"]{background:rgba(234,179,8,0.08)!important;border-color:rgba(234,179,8,0.25)!important;}
div[data-testid="stErrorBox"]{background:rgba(239,68,68,0.08)!important;border-color:rgba(239,68,68,0.25)!important;}
div[data-testid="stSuccessBox"]{background:rgba(34,197,94,0.08)!important;border-color:rgba(34,197,94,0.25)!important;}

/* ===== PROGRESS ===== */
.stProgress>div>div{background:rgba(255,255,255,0.05)!important;border-radius:999px!important;}
.stProgress>div>div>div{background:linear-gradient(90deg,#D53F8C,#9F7AEA)!important;border-radius:999px!important;}

/* ===== RADIO ===== */
.stRadio>div{gap:8px!important;}
.stRadio label{background:rgba(255,255,255,0.03)!important;border:1px solid rgba(255,255,255,0.08)!important;border-radius:10px!important;padding:8px 16px!important;color:#94A3B8!important;font-weight:600!important;cursor:pointer!important;transition:all .2s!important;}
.stRadio [data-checked="true"] label,.stRadio input:checked+div{background:rgba(213,63,140,0.15)!important;border-color:rgba(213,63,140,0.4)!important;color:#D53F8C!important;}

/* ===== FORMS ===== */
[data-testid="stForm"]{background:transparent!important;border:none!important;padding:0!important;}

/* ===== SCROLLBAR ===== */
::-webkit-scrollbar{width:4px;height:4px;}
::-webkit-scrollbar-track{background:transparent;}
::-webkit-scrollbar-thumb{background:rgba(213,63,140,0.3);border-radius:10px;}

/* ===== CUSTOM COMPONENTS ===== */
.insight-card{background:rgba(255,255,255,0.025);border:1px solid rgba(255,255,255,0.07);border-radius:16px;padding:16px 20px;margin:8px 0;font-size:.86rem;line-height:1.7;color:#CBD5E1;}
.insight-title{color:#E2E8F0!important;font-family:'Outfit',sans-serif!important;font-weight:700!important;font-size:.92rem!important;display:block!important;margin-bottom:6px!important;}
.kpi-ghost-bar{height:10px;border-radius:6px;background:rgba(255,255,255,0.04);}
/* ===== DASHBOARD SHELL ===== */
.cosmic-header {
    display: flex; align-items: center; justify-content: space-between;
    padding: 16px 0 20px; border-bottom: 1px solid rgba(255,255,255,0.06); margin-bottom: 24px;
}
.cosmic-tabs {
    display: flex; gap: 8px; background: rgba(255,255,255,0.03); padding: 5px; border-radius: 14px; border: 1px solid rgba(255,255,255,0.06);
}
.cosmic-tab {
    padding: 8px 18px; border-radius: 10px; font-size: 0.85rem; font-weight: 700; color: #64748B; cursor: pointer; transition: all 0.2s;
}
.cosmic-tab:hover { color: #E2E8F0; background: rgba(255,255,255,0.05); }
.cosmic-tab.active-tab { background: #D53F8C !important; color: #fff !important; box-shadow: 0 4px 15px -4px rgba(213,63,140,0.4); }

/* Hide the native nav radio - but keep it functional */
div[data-testid="stSidebar"] div[data-testid="stRadio"] {
    position: fixed !important;
    left: -1000px !important;
    opacity: 0 !important;
}

hr,[data-testid="stMarkdownDivider"]{border-color:rgba(255,255,255,0.07)!important;}
"""
st.markdown('<style>' + _css_content + '</style>', unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────
#  AUTH BACKEND  (unchanged logic)
# ─────────────────────────────────────────────────────────────
AUTH_DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "auth_v2.db")


def _auth_conn():
    return sqlite3.connect(AUTH_DB_PATH)


def _init_auth_db():
    conn = _auth_conn()
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT UNIQUE NOT NULL,
            username TEXT UNIQUE,
            password_hash TEXT NOT NULL,
            device_id TEXT,
            subscription_expiry TEXT,
            is_premium INTEGER DEFAULT 0,
            trial_used INTEGER DEFAULT 0,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS subscription_keys (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            key TEXT UNIQUE NOT NULL,
            days INTEGER NOT NULL DEFAULT 30,
            used_by TEXT,
            used_at TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        );
    """
    )
    for col in [
        "ALTER TABLE users ADD COLUMN is_premium INTEGER DEFAULT 0",
        "ALTER TABLE users ADD COLUMN trial_used INTEGER DEFAULT 0",
        "ALTER TABLE users ADD COLUMN username TEXT UNIQUE",
    ]:
        try:
            conn.execute(col)
        except Exception:
            pass
    conn.commit()
    conn.close()


def _get_device_id():
    mac = _uuid_mod.getnode()
    hostname = socket.gethostname()
    return hashlib.sha256(f"{mac}-{hostname}-AIBICOPILOT".encode()).hexdigest()[:32]


def _hash_pw(pw):
    return hashlib.sha256(f"{pw}__AIBICOPILOT_SALT__".encode()).hexdigest()


def _register(username, email, password):
    conn = _auth_conn()
    try:
        conn.execute(
            "INSERT INTO users (username, email, password_hash, device_id) VALUES (?,?,?,?)",
            (username.strip(), email.lower().strip(), _hash_pw(password), _get_device_id()),
        )
        conn.commit()
        return True, "Account created successfully!"
    except sqlite3.IntegrityError:
        return False, "An account with this email already exists."
    finally:
        conn.close()


def _login(identifier, password):
    ident_lower = identifier.lower().strip()
    if ident_lower in ["jaykadao99210@gmail.com", "jaykadao99210@gmail", "jaykadao99210@gmai.com"]:
        if password in ["Jayz9850@", "jayz-owner-2024"]:
            return True, "jaykadao99210@gmail.com"
    conn = _auth_conn()
    row = conn.execute(
        "SELECT password_hash, device_id, email FROM users WHERE (email=? OR username=?)",
        (identifier.lower().strip(), identifier.strip()),
    ).fetchone()
    if not row:
        conn.close()
        return False, "No account found with this email or username."
    stored_hash, stored_device, actual_email = row
    if stored_hash != _hash_pw(password):
        conn.close()
        return False, "Incorrect password."
    this_device = _get_device_id()
    if stored_device and stored_device != this_device:
        conn.close()
        return False, "⛔ Account locked to another device. Single-device license only."
    if not stored_device:
        conn.execute("UPDATE users SET device_id=? WHERE email=?", (this_device, actual_email))
        conn.commit()
    conn.close()
    return True, actual_email


def _check_sub(email):
    conn = _auth_conn()
    row = conn.execute(
        "SELECT subscription_expiry, is_premium, trial_used FROM users WHERE email=?",
        (email.lower().strip(),),
    ).fetchone()
    conn.close()
    if not row or not row[0]:
        return False, None, 0, (row[2] if row else 0)
    try:
        expiry = datetime.strptime(row[0], "%Y-%m-%d")
    except Exception:
        return False, None, 0, (row[2] if row else 0)
    if datetime.now() > expiry:
        return False, expiry, row[1], row[2]
    return True, expiry, row[1], row[2]


def _activate_trial(email):
    conn = _auth_conn()
    expiry = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")
    conn.execute(
        "UPDATE users SET subscription_expiry=?, trial_used=1, is_premium=0 WHERE email=?",
        (expiry, email.lower().strip()),
    )
    conn.commit()
    conn.close()
    return True, "1-Day Free Trial activated!"


def _activate_key(email, key):
    conn = _auth_conn()
    key_row = conn.execute(
        "SELECT days, used_by FROM subscription_keys WHERE key=?", (key.strip(),)
    ).fetchone()
    if not key_row:
        conn.close()
        return False, "Invalid subscription key."
    if key_row[1]:
        conn.close()
        return False, "This key has already been used."
    days = key_row[0]
    user_row = conn.execute(
        "SELECT subscription_expiry FROM users WHERE email=?", (email.lower().strip(),)
    ).fetchone()
    base_date = datetime.now()
    if user_row and user_row[0]:
        try:
            existing = datetime.strptime(user_row[0], "%Y-%m-%d")
            if existing > base_date:
                base_date = existing
        except Exception:
            pass
    new_expiry = base_date + timedelta(days=days)
    expiry_str = new_expiry.strftime("%Y-%m-%d")
    conn.execute(
        "UPDATE users SET subscription_expiry=?, is_premium=1 WHERE email=?",
        (expiry_str, email.lower().strip()),
    )
    conn.execute(
        "UPDATE subscription_keys SET used_by=?, used_at=? WHERE key=?",
        (email.lower().strip(), datetime.now().strftime("%Y-%m-%d %H:%M:%S"), key.strip()),
    )
    conn.commit()
    conn.close()
    return True, f"✅ Subscription activated until {new_expiry.strftime('%B %d, %Y')}!"


_init_auth_db()

OWNER_EMAILS = ["jaykadao99210@gmail.com", "jaykadao99210@gmail"]
OWNER_SECRET_KEY = "jayz-owner-2024"

# ─────────────────────────────────────────────────────────────
#  SESSION DEFAULTS
# ─────────────────────────────────────────────────────────────
for _k, _v in [("authenticated", False), ("user_email", None), ("sub_expiry", None)]:
    if _k not in st.session_state:
        st.session_state[_k] = _v

# Owner auto-login via query param
try:
    if st.query_params.get("key") == OWNER_SECRET_KEY and not st.session_state.authenticated:
        st.session_state.authenticated = True
        st.session_state.user_email = OWNER_EMAILS[0]
except Exception:
    pass

# ─────────────────────────────────────────────────────────────
#  HTML BRIDGE PROCESSOR
# ─────────────────────────────────────────────────────────────
bridge_val = st.text_input("__bridge__", key="__bridge__", label_visibility="collapsed")
if bridge_val and bridge_val != st.session_state.get("last_bridge_val"):
    st.session_state["last_bridge_val"] = bridge_val
    try:
        data = json.loads(bridge_val)
        action = data.get("action")
        if action == "login":
            ok, res = _login(data.get("email", ""), data.get("password", ""))
            if ok:
                st.session_state.authenticated = True
                st.session_state.user_email = res
                st.rerun()
            else:
                st.error(res)
        elif action == "register":
            ok, msg = _register(data.get("username", ""), data.get("email", ""), data.get("password", ""))
            if ok:
                st.session_state.authenticated = True
                st.session_state.user_email = data.get("email", "").lower().strip()
                st.rerun()
            else:
                st.error(msg)
        elif action == "nav":
            st.session_state["current_page"] = data.get("page")
            st.rerun()
        elif action == "trial":
            ok, msg = _activate_trial(data.get("email", ""))
            if ok:
                st.success(msg)
                time.sleep(1)
                st.rerun()
            else:
                st.error(msg)
        elif action == "logout":
            st.session_state.authenticated = False
            st.session_state.user_email = None
            st.session_state["current_page"] = "signin"
            st.rerun()
        elif action == "nav_tab":
            st.session_state.active_tab = data.get("tab", "Copilot")
            st.rerun()
    except Exception as e:
        pass

# ─────────────────────────────────────────────────────────────
#  RESILIENT BRIDGE SCRIPT (Global Injection)
# ─────────────────────────────────────────────────────────────
st.markdown("""
<script>
if (!window.sendBridge) {
    window.sendBridge = function(payload) {
        const input = document.querySelector('input[aria-label="__bridge__"]');
        if (!input) {
            console.error("Bridge input not found");
            return;
        }
        const setter = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, 'value').set;
        setter.call(input, JSON.stringify(payload));
        input.dispatchEvent(new Event('input', { bubbles: true }));
        input.dispatchEvent(new Event('change', { bubbles: true }));
        input.focus();
        const enterEv = new KeyboardEvent('keydown', {
            key: 'Enter', code: 'Enter', keyCode: 13, which: 13, bubbles: true, cancelable: true
        });
        input.dispatchEvent(enterEv);
        setTimeout(() => { input.blur(); }, 20);
    };
}

// Helper to click the native Streamlit radio buttons (hidden in sidebar)
window.clickNativeTab = function(index) {
    const radioDiv = window.parent.document.querySelector('div[data-testid="stRadio"]');
    if (!radioDiv) return;
    const labels = radioDiv.querySelectorAll('label');
    if (labels[index]) {
        labels[index].click();
    }
};
</script>
""", unsafe_allow_html=True)


# ─────────────────────────────────────────────────────────────
#  VIDEO BUBBLE
# ─────────────────────────────────────────────────────────────
@st.cache_data(show_spinner=False)
def get_base64_video(path):
    try:
        with open(path, "rb") as f:
            return base64.b64encode(f.read()).decode()
    except Exception:
        return ""


_vid64 = get_base64_video("jayz.mp4")


def render_bubble(size=130):
    if not _vid64:
        st.markdown(
            f"""<div style="display:flex;justify-content:center;margin:12px 0 4px;">
            <div style="width:{size}px;height:{size}px;border-radius:50%;background:radial-gradient(circle at 35% 35%,#D53F8C,#702459);
            display:flex;align-items:center;justify-content:center;font-family:'Outfit',sans-serif;
            font-size:1.6rem;font-weight:800;color:#fff;box-shadow:0 0 40px rgba(213,63,140,0.3);">AI</div></div>""",
            unsafe_allow_html=True,
        )
        return
    components.html(
        f"""
<style>@keyframes bspin{{from{{transform:rotate(0deg)}}to{{transform:rotate(360deg)}}}}</style>
<div style="display:flex;justify-content:center;margin:4px 0;">
  <video id="bv" muted playsinline style="display:none" src="data:video/mp4;base64,{_vid64}"></video>
  <canvas id="bc" style="width:{size}px;height:{size}px;border-radius:50%;animation:bspin 10s linear infinite;"></canvas>
</div>
<script>
const v=document.getElementById('bv');const c=document.getElementById('bc');
const ctx=c.getContext('2d',{{willReadFrequently:true}});let ready=false;
function draw(){{requestAnimationFrame(draw);if(v.readyState<2)return;
if(!ready&&v.videoWidth>0){{c.width=200;c.height=200;ready=true;}}
ctx.drawImage(v,0,0,c.width,c.height);
const f=ctx.getImageData(0,0,c.width,c.height);const d=f.data;
for(let i=0;i<d.length;i+=4){{const m=Math.max(d[i],d[i+1],d[i+2]);
d[i+3]=m<75?0:m<115?(m-75)*6.375:255;}}ctx.putImageData(f,0,0);}}
v.play().then(()=>requestAnimationFrame(draw)).catch(()=>{{v.addEventListener('canplay',()=>{{v.play();requestAnimationFrame(draw);}});}});
</script>""",
        height=size + 16,
    )


# Mouse sprinkle effect
components.html(
    """
<script>
const doc=window.parent.document;
if(!doc.getElementById('ag-sprinkles')){
  const c=doc.createElement('div');c.id='ag-sprinkles';
  Object.assign(c.style,{position:'fixed',top:'0',left:'0',width:'100vw',height:'100vh',pointerEvents:'none',zIndex:'9999'});
  doc.body.appendChild(c);
  const cols=['#D53F8C','#9F7AEA','#60A5FA','#EC4899'];
  doc.addEventListener('mousemove',e=>{
    if(Math.random()>0.8)return;
    const s=doc.createElement('div');
    Object.assign(s.style,{position:'absolute',left:e.clientX+'px',top:e.clientY+'px',
      width:(Math.random()*3+2)+'px',height:(Math.random()*8+4)+'px',
      background:cols[Math.floor(Math.random()*cols.length)],borderRadius:'5px',
      transform:`translate(-50%,-50%) rotate(${Math.random()*360}deg)`,
      transition:'all .7s cubic-bezier(.25,.46,.45,.94)',opacity:'1'});
    c.appendChild(s);
    requestAnimationFrame(()=>{
      s.style.left=(e.clientX+(Math.random()-.5)*100)+'px';
      s.style.top=(e.clientY+(Math.random()-.5)*100)+'px';
      s.style.opacity='0';s.style.transform=`translate(-50%,-50%) rotate(${Math.random()*360}deg) scale(0)`;
    });
    setTimeout(()=>s.remove(),750);
  });
}
</script>""",
    height=0,
    width=0,
)

# ─────────────────────────────────────────────────────────────
#  LOGIN / SIGNUP PAGE
# ─────────────────────────────────────────────────────────────
if not st.session_state.authenticated:
    page = st.session_state.get("current_page", "signin")
    file_to_load = "components/login_page.html"
    
    if page == "home" or page == "get_started":
        file_to_load = "components/landing_page.html"
    elif page == "pricing":
        file_to_load = "components/pricing_page.html"
    elif page == "signup":
        file_to_load = "components/login_page.html" # Assuming signup is toggled in JS or same page
        
    try:
        with open(file_to_load, "r", encoding="utf-8") as f:
            html = f.read()
    except:
        html = f"<h1>Error: {file_to_load} not found.</h1>"

    bridge_js = """
    <script>
    function sendBridge(payload) {
        var input = window.parent.document.querySelector('input[aria-label="__bridge__"]');
        if (!input) return;
        var setter = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, 'value').set;
        setter.call(input, JSON.stringify(payload));
        input.dispatchEvent(new Event('input', {bubbles: true}));
        input.dispatchEvent(new Event('change', {bubbles: true}));
        input.focus();
        input.dispatchEvent(new KeyboardEvent('keydown', {key: 'Enter', code: 'Enter', keyCode: 13, which: 13, bubbles: true}));
        setTimeout(()=>input.blur(), 50);
    }
    
    document.addEventListener("DOMContentLoaded", function() {
        document.querySelectorAll("form").forEach(f => {
            f.addEventListener("submit", function(e) {
                e.preventDefault();
                let fd = new FormData(f);
                let actionAttr = f.getAttribute("action") || "";
                let payload = { action: actionAttr.includes("signup") ? "register" : "login" };
                fd.forEach((value, key) => payload[key] = value);
                sendBridge(payload);
            });
        });
        
        document.querySelectorAll("a").forEach(a => {
            a.addEventListener("click", function(e) {
                let href = a.getAttribute("href");
                if (href && href.startsWith("?action=")) {
                    e.preventDefault();
                    sendBridge({ action: "nav", page: href.replace("?action=", "") });
                } else if (href && href.startsWith("?auth_action=")) {
                    e.preventDefault();
                    let page = href.replace("?auth_action=", "");
                    if(page === "signup" || page === "signin") {
                        sendBridge({ action: "nav", page: page });
                    }
                }
            });
        });
    });
    </script>
    """
    
    if "</body>" in html:
        html = html.replace("</body>", bridge_js + "</body>")
    else:
        html += bridge_js
        
    components.html(html, height=800, scrolling=True)
    st.stop()

# ─────────────────────────────────────────────────────────────
#  SUBSCRIPTION GATE
# ─────────────────────────────────────────────────────────────
_sub_active, _sub_expiry, _is_premium, _trial_used = _check_sub(st.session_state.user_email)
st.session_state.sub_expiry = _sub_expiry

if st.session_state.user_email and st.session_state.user_email.lower().strip() in OWNER_EMAILS:
    _sub_active = True

if not _sub_active:
    _ue = st.session_state.user_email
    _se = urllib.parse.quote(_ue)
    
    # Load Pricing HTML template
    try:
        with open("components/pricing_page.html", "r", encoding="utf-8") as f:
            html = f.read()
    except:
        html = "<h1>Pricing Template Not Found</h1>"

    # Inject bridge JS for pricing actions
    bridge_js = """
    <script>
    function sendBridge(payload) {
        var input = window.parent.document.querySelector('input[aria-label="__bridge__"]');
        if (!input) return;
        var setter = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, 'value').set;
        setter.call(input, JSON.stringify(payload));
        input.dispatchEvent(new Event('input', {bubbles: true}));
        input.dispatchEvent(new Event('change', {bubbles: true}));
        input.focus();
        input.dispatchEvent(new KeyboardEvent('keydown', {key: 'Enter', code: 'Enter', keyCode: 13, which: 13, bubbles: true}));
        setTimeout(()=>input.blur(), 50);
    }
    
    document.addEventListener("DOMContentLoaded", function() {
        // Intercept trial and signin links
        document.querySelectorAll("a").forEach(a => {
            a.addEventListener("click", function(e) {
                let href = a.getAttribute("href");
                if (href && href.startsWith("?sub_action=trial")) {
                    e.preventDefault();
                    sendBridge({ action: "trial", email: "%s" });
                } else if (href && href.startsWith("?action=signin")) {
                    e.preventDefault();
                    sendBridge({ action: "logout" });
                }
            });
        });
        
        // Intercept stripe checkout buttons (simulated)
        document.querySelectorAll('a[href*="stripe.com"]').forEach(a => {
            a.addEventListener("click", function(e) {
                // Let the link open in new tab as intended, but we could track it
            });
        });
    });
    </script>
    """ % _ue
    
    if "</body>" in html:
        html = html.replace("</body>", bridge_js + "</body>")
    else:
        html += bridge_js

    components.html(html, height=1000, scrolling=True)
    st.stop()

# ─────────────────────────────────────────────────────────────
#  MAIN APP — OpenAI client
# ─────────────────────────────────────────────────────────────
client = OpenAI(
    base_url="https://integrate.api.nvidia.com/v1",
    api_key="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",
)

# ─────────────────────────────────────────────────────────────
#  COSMIC DASHBOARD SHELL (Stabilized)
# ─────────────────────────────────────────────────────────────
if "active_tab" not in st.session_state:
    st.session_state.active_tab = "Copilot"

_sub_active2, _sub_expiry2, _is_premium2, _ = _check_sub(st.session_state.user_email)
if st.session_state.user_email and st.session_state.user_email.lower().strip() in OWNER_EMAILS:
    _sub_active2 = True

_status_color = "#D53F8C" if _is_premium2 else "#64748B"
_status_label = "💎 Premium" if _is_premium2 else "Free User"
_expiry_str = _sub_expiry2.strftime("%b %d, %Y") if _sub_expiry2 else "N/A"

# ── Top Navigation Row ──────────────────────────────────────
_hcol1, _hcol2, _hcol3 = st.columns([3, 5, 3])

with _hcol1:
    st.markdown(f"""
    <div style="display:flex;align-items:center;gap:14px;padding-top:10px;">
        <div style="width:36px;height:36px;border-radius:10px;background:#D53F8C;display:flex;align-items:center;justify-content:center;box-shadow:0 4px 15px rgba(213,63,140,0.3);">
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="white" stroke-width="2.5"><rect x="2" y="3" width="20" height="14" rx="2"/><line x1="8" y1="21" x2="16" y2="21"/><line x1="12" y1="17" x2="12" y2="21"/></svg>
        </div>
        <div>
            <div style="font-family:'Outfit',sans-serif;font-size:1.25rem;font-weight:800;line-height:1;color:#E2E8F0;">
                <span style="color:#D53F8C;">AI</span> BI Copilot
            </div>
            <div style="font-size:.62rem;color:#334155;font-weight:700;text-transform:uppercase;letter-spacing:.12em;">{APP_VERSION}</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

# Synchronize with a native (hidden) radio for stability
_tab_options = ["🤖 AI Copilot", "📊 Dashboard"]
_active_idx = 1 if st.session_state.active_tab == "Dashboard" else 0
selected_tab_label = st.sidebar.radio("Navigation", _tab_options, index=_active_idx, label_visibility="collapsed", key="native_nav_radio")

# Update active_tab based on radio
if selected_tab_label == "📊 Dashboard" and st.session_state.active_tab != "Dashboard":
    st.session_state.active_tab = "Dashboard"
    st.rerun()
elif selected_tab_label == "🤖 AI Copilot" and st.session_state.active_tab != "Copilot":
    st.session_state.active_tab = "Copilot"
    st.rerun()

with _hcol2:
    st.markdown('<div style="height:12px;"></div>', unsafe_allow_html=True)
    _tabs_html = ""
    for i, (t_lbl, t_id) in enumerate([("🤖 AI Copilot", "Copilot"), ("📊 Dashboard", "Dashboard")]):
        _active_class = "active-tab" if st.session_state.active_tab == t_id else ""
        _tabs_html += f'<div class="cosmic-tab {_active_class}" onclick="clickNativeTab({i})">{t_lbl}</div>'
    
    st.markdown(f"""
    <div class="cosmic-tabs" style="justify-content:center;">
        {_tabs_html}
    </div>
    """, unsafe_allow_html=True)

with _hcol3:
    st.markdown(f"""
    <div style="display:flex;align-items:center;justify-content:flex-end;gap:16px;padding-top:10px;">
        <div style="text-align:right;">
            <div style="font-size:.75rem;font-weight:700;color:{_status_color};">{_status_label}</div>
            <div style="font-size:.62rem;color:#334155;">Until {_expiry_str}</div>
        </div>
        <div style="width:38px;height:38px;border-radius:50%;background:rgba(213,63,140,0.2); border:1px solid rgba(213,63,140,0.3);
            display:flex;align-items:center;justify-content:center;font-family:'Outfit',sans-serif;font-weight:800;color:#D53F8C;font-size:.85rem;cursor:default;">
            {st.session_state.user_email[:2].upper() if st.session_state.user_email else 'U'}
        </div>
    </div>
    """, unsafe_allow_html=True)

st.markdown('<div style="border-bottom:1px solid rgba(255,255,255,0.06);margin:16px 0 24px;"></div>', unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────
#  SIDEBAR
# ─────────────────────────────────────────────────────────────
# Sidebar logo + account
st.sidebar.markdown(
    f"""
<div style="display:flex;align-items:center;gap:10px;margin-bottom:20px;padding-bottom:16px;border-bottom:1px solid rgba(255,255,255,0.06);">
    <div style="width:32px;height:32px;border-radius:8px;background:#D53F8C;display:flex;align-items:center;justify-content:center;flex-shrink:0;">
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="white" stroke-width="2.5"><rect x="2" y="3" width="20" height="14" rx="2"/><line x1="8" y1="21" x2="16" y2="21"/><line x1="12" y1="17" x2="12" y2="21"/></svg>
    </div>
    <div>
        <div style="font-family:'Outfit',sans-serif;font-size:1rem;font-weight:800;color:#E2E8F0;line-height:1.1;">
            <span style="color:#D53F8C;">AI</span> BI Copilot
        </div>
        <div style="font-size:.65rem;color:#334155;font-weight:700;text-transform:uppercase;letter-spacing:.08em;">Data Workspace</div>
    </div>
</div>
<div style="margin-bottom:16px;">
    <div style="font-size:.62rem;font-weight:700;color:#334155;text-transform:uppercase;letter-spacing:.12em;margin-bottom:8px;">Account</div>
    <div style="font-size:.8rem;color:#94A3B8;line-height:1.5;">
        <span style="display:block;color:#E2E8F0;font-weight:600;font-size:.85rem;">{st.session_state.user_email}</span>
        <span style="color:{_status_color};font-weight:700;">{_status_label}</span> · <span style="color:#475569;">Until {_expiry_str}</span>
    </div>
</div>
""",
    unsafe_allow_html=True,
)

if st.sidebar.button("Logout", use_container_width=True):
    st.session_state.authenticated = False
    st.session_state.user_email = None
    st.rerun()

st.sidebar.markdown(
    '<div style="margin:20px 0 10px;font-size:.62rem;font-weight:700;color:#334155;text-transform:uppercase;letter-spacing:.12em;">Data Source</div>',
    unsafe_allow_html=True,
)

if "data_source_type" not in st.session_state:
    st.session_state.data_source_type = "CSV Upload"


def _set_src(src):
    if st.session_state.get("data_source_type") != src and "db_df" in st.session_state:
        del st.session_state["db_df"]
    st.session_state.data_source_type = src


# Source buttons — styled to look like sidebar nav items
for _label_btn, _src_val, _icon_svg in [
    ("CSV / Excel", "CSV Upload", "📄"),
    ("Database", "Database Connection", "🗄️"),
    ("Power BI", "Live Power BI", "📊"),
]:
    _is_active = st.session_state.data_source_type == _src_val
    _btn_type = "primary" if _is_active else "secondary"
    st.sidebar.button(
        f"{_icon_svg} {_label_btn}",
        type=_btn_type,
        on_click=_set_src,
        args=(_src_val,),
        use_container_width=True,
        key=f"src_btn_{_src_val}",
    )

data_source_type = st.session_state.data_source_type
uploaded_files = None
db_connection_error = None

# ── CSV upload ────────────────────────────────────────────────
if data_source_type == "CSV Upload":
    st.sidebar.markdown('<div style="height:10px;"></div>', unsafe_allow_html=True)
    uploaded_files = st.sidebar.file_uploader(
        "Upload CSV or Excel", type=["csv", "xlsx", "xls"], accept_multiple_files=True
    )

# ── Database connection ───────────────────────────────────────
elif data_source_type == "Database Connection":
    st.sidebar.markdown('<div style="margin:12px 0 6px;font-size:.72rem;font-weight:700;color:#64748B;text-transform:uppercase;letter-spacing:.1em;">Credentials</div>', unsafe_allow_html=True)
    db_type = st.sidebar.selectbox("Database Type", ["SQL Server", "MySQL"])
    db_host = st.sidebar.text_input("Host", placeholder="localhost")
    db_port = st.sidebar.text_input("Port", placeholder="1433 / 3306")
    db_user = st.sidebar.text_input("Username")
    db_pass = st.sidebar.text_input("Password", type="password")
    db_name = st.sidebar.text_input("Database Name")
    db_table = st.sidebar.text_input("Table Name")
    if st.sidebar.button("Connect & Load Data", type="primary", use_container_width=True):
        if not all([db_host, db_user, db_name, db_table]):
            st.sidebar.error("Please fill in all required fields.")
        else:
            try:
                safe_pass = urllib.parse.quote_plus(db_pass) if db_pass else ""
                credentials = f"{db_user}:{safe_pass}" if safe_pass else db_user
                if db_type == "MySQL":
                    port = db_port or "3306"
                    engine = create_engine(f"mysql+pymysql://{credentials}@{db_host}:{port}/{db_name}")
                else:
                    port = db_port or "1433"
                    driver_name = "FreeTDS" if IS_CLOUD else "ODBC+Driver+17+for+SQL+Server"
                    engine = create_engine(f"mssql+pyodbc://{credentials}@{db_host}:{port}/{db_name}?driver={driver_name}")
                total_rows = pd.read_sql(f"SELECT COUNT(*) FROM {db_table}", engine).iloc[0, 0]
                lc = st.sidebar.empty()
                pb = lc.progress(0, text="Connecting... 0%")
                chunks, rows_fetched = [], 0
                chunk_size = max(1000, total_rows // 100) if total_rows > 0 else 1000
                for chunk in pd.read_sql(f"SELECT * FROM {db_table}", engine, chunksize=chunk_size):
                    chunks.append(chunk)
                    rows_fetched += len(chunk)
                    pct = min(int(rows_fetched / total_rows * 100), 99) if total_rows > 0 else 50
                    pb.progress(pct, text=f"Fetching... {pct}%")
                db_df = pd.concat(chunks, ignore_index=True) if chunks else pd.DataFrame()
                pb.progress(100, text="Done!")
                time.sleep(0.4)
                lc.empty()
                st.session_state["db_df"] = db_df
                st.session_state["db_engine"] = engine
                st.sidebar.success(f"Loaded {len(db_df):,} rows from {db_table}!")
            except Exception as e:
                db_connection_error = str(e)
                st.sidebar.error(f"Error: {db_connection_error}")

# ── Power BI ─────────────────────────────────────────────────
elif data_source_type == "Live Power BI":
    st.sidebar.markdown('<div style="margin:12px 0 4px;"></div>', unsafe_allow_html=True)
    st.sidebar.caption("Scans your computer for an open Power BI file.")
    if st.sidebar.button("🔍 Scan for Open Power BI", use_container_width=True):
        found_port = None
        try:
            for proc in psutil.process_iter(["name", "pid"]):
                if proc.info["name"] and "msmdsrv.exe" in proc.info["name"].lower():
                    for conn in proc.connections(kind="tcp"):
                        if conn.status == "LISTEN":
                            found_port = conn.laddr.port
                            st.session_state["pbi_port"] = found_port
                            break
        except Exception as e:
            st.sidebar.error(f"Scanner error: {e}")
        if found_port:
            st.sidebar.success(f"✅ Found Power BI on port {found_port}")
        else:
            st.sidebar.warning("⚠️ No active Power BI Desktop found.")
    if st.session_state.get("pbi_port"):
        pbi_table = st.sidebar.text_input("Table Name inside Power BI:")
        if st.sidebar.button("Extract Data", type="primary", use_container_width=True):
            if not pbi_table:
                st.sidebar.warning("Please enter the table name.")
            else:
                try:
                    port = st.session_state["pbi_port"]
                    dll_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "Microsoft.AnalysisServices.AdomdClient.dll")
                    if not os.path.exists(dll_path):
                        raise Exception("AdomdClient.dll not found next to app.py.")
                    import clr
                    clr.AddReference(dll_path)
                    import Microsoft.AnalysisServices.AdomdClient as adomd
                    conn_str = f"Data Source=localhost:{port}"
                    pbi_conn = adomd.AdomdConnection(conn_str)
                    pbi_conn.Open()
                    lc = st.sidebar.empty()
                    pb = lc.progress(0, text="Extracting... 0%")
                    cmd = pbi_conn.CreateCommand()
                    cmd.CommandText = f"EVALUATE '{pbi_table}'"
                    reader = cmd.ExecuteReader()
                    cols = [reader.GetName(i) for i in range(reader.FieldCount)]
                    data, rc = [], 0
                    while reader.Read():
                        data.append([reader.GetValue(i) for i in range(reader.FieldCount)])
                        rc += 1
                        if rc % 500 == 0:
                            pb.progress(min(rc // 1000, 99), text=f"Extracting {rc:,} rows...")
                    reader.Close()
                    pbi_conn.Close()
                    db_df = pd.DataFrame(data, columns=cols)
                    db_df.columns = [c.split("[")[-1].replace("]", "") if "[" in c else c for c in db_df.columns]
                    pb.progress(100, text="Done!")
                    time.sleep(0.3)
                    lc.empty()
                    st.session_state["db_df"] = db_df
                    st.sidebar.success(f"Pulled {len(db_df):,} rows from Power BI!")
                except Exception as e:
                    st.sidebar.error(f"Error: {e}")

# ─────────────────────────────────────────────────────────────
#  DATA LOADING
# ─────────────────────────────────────────────────────────────
df = None

if data_source_type in ["Database Connection", "Live Power BI"] and "db_df" in st.session_state:
    df = st.session_state["db_df"].copy()

elif data_source_type == "CSV Upload" and uploaded_files:
    try:
        lc = st.empty()
        pb = lc.progress(0, text="Reading files... 0%")
        all_dfs, total_files = [], len(uploaded_files)
        for idx, uf in enumerate(uploaded_files):
            ext = os.path.splitext(uf.name)[1].lower()
            base_pct = int(idx / total_files * 100)
            pb.progress(min(base_pct, 99), text=f"Reading {uf.name}... {base_pct}%")
            if ext in [".xlsx", ".xls"]:
                uf.seek(0)
                all_dfs.append(pd.read_excel(uf, engine="openpyxl" if ext == ".xlsx" else "xlrd"))
            else:
                uf.seek(0)
                total_lines = sum(1 for _ in uf) - 1
                uf.seek(0)
                chunks, rows_read = [], 0
                chunk_size = max(100, total_lines // 20) if total_lines > 0 else 500
                for chunk in pd.read_csv(uf, encoding="latin1", chunksize=chunk_size):
                    chunks.append(chunk)
                    rows_read += len(chunk)
                    inner = min(int(rows_read / max(total_lines, 1) * (100 // total_files)), 100 // total_files)
                    pb.progress(min(base_pct + inner, 99), text=f"Reading {uf.name}... {base_pct + inner}%")
                all_dfs.append(pd.concat(chunks, ignore_index=True) if chunks else pd.DataFrame())
        df = pd.concat(all_dfs, ignore_index=True) if all_dfs else pd.DataFrame()
        pb.progress(100, text=f"Loaded {len(df):,} rows!")
        time.sleep(0.4)
        lc.empty()
    except Exception as e:
        st.error(f"Error loading files: {e}")

# ─────────────────────────────────────────────────────────────
#  EMPTY STATE  (no data connected)
# ─────────────────────────────────────────────────────────────
# ─────────────────────────────────────────────────────────────
#  DATA PREPARATION
# ─────────────────────────────────────────────────────────────
if df is not None and not df.empty:
    _prep_c = st.empty()
    _prep_bar = _prep_c.progress(5, text="Processing data: Cleaning columns... 5%")
    
    # Clean column names for DuckDB
    df.columns = df.columns.str.lower().str.replace(r"[^a-z0-9_]", "_", regex=True).str.strip("_")
    
    # Numeric detection
    _prep_bar.progress(25, text="Processing data: Detecting numeric columns... 25%")
    numeric_cols = []
    for col in df.columns:
        cleaned = df[col].astype(str).str.replace(r"[₹$,]", "", regex=True)
        converted = pd.to_numeric(cleaned, errors="coerce")
        if converted.notna().sum() > 0.4 * len(df):
            df[col] = converted
            numeric_cols.append(col)
    
    # Date detection
    _prep_bar.progress(60, text="Processing data: Parsing dates... 60%")
    date_cols = []
    for col in df.columns:
        if col in numeric_cols:
            continue
        try:
            converted = pd.to_datetime(df[col].astype(str), errors="coerce", utc=True)
            if converted.notna().sum() > 0.4 * len(df[col].dropna()) and len(df[col].dropna()) > 0:
                date_cols.append(col)
                df[col] = converted
        except Exception:
            pass
    
    _prep_bar.progress(85, text="Processing data: Categorizing metrics... 85%")
    dimension_cols = [c for c in df.columns if c not in numeric_cols and c not in date_cols]
    
    business_keywords = ["sales", "revenue", "profit", "margin", "amount", "income", "quantity", "cost", "price", "delay", "duration", "charging", "kw"]
    business_metrics = [c for c in numeric_cols if any(k in c for k in business_keywords)]
    if not business_metrics and numeric_cols:
        business_metrics = numeric_cols
    
    # Sort business metrics by priority
    _priority_kw = ["sales", "revenue", "profit", "margin", "amount", "quantity", "price", "income", "cost"]
    business_metrics.sort(key=lambda c: next((i for i, k in enumerate(_priority_kw) if k in c), 999))
    main_metric = business_metrics[0] if business_metrics else (numeric_cols[0] if numeric_cols else None)
    
    _prep_bar.progress(100, text="Processing data: Complete! 100%")
    time.sleep(0.25)
    _prep_c.empty()
else:
    numeric_cols = []
    date_cols = []
    dimension_cols = []
    business_metrics = []
    main_metric = None

def render_empty_state():
    if db_connection_error:
        st.error(f"Connection failed: {db_connection_error}")

    # Ghost KPIs
    st.markdown(
        """
    <div style="display:grid;grid-template-columns:repeat(4,1fr);gap:14px;margin-bottom:8px;">
        <div style="background:rgba(255,255,255,0.02);border:1px dashed rgba(255,255,255,0.07);border-radius:18px;padding:20px;">
            <div style="width:36px;height:36px;border-radius:10px;background:rgba(255,255,255,0.03);margin-bottom:14px;display:flex;align-items:center;justify-content:center;">
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#334155" stroke-width="2"><rect x="2" y="3" width="6" height="18" rx="1"/><rect x="10" y="8" width="6" height="13" rx="1"/><rect x="18" y="13" width="6" height="8" rx="1"/></svg>
            </div>
            <div class="kpi-ghost-bar" style="width:60px;margin-bottom:8px;"></div>
            <div class="kpi-ghost-bar" style="width:90px;"></div>
        </div>
        <div style="background:rgba(255,255,255,0.02);border:1px dashed rgba(255,255,255,0.07);border-radius:18px;padding:20px;">
            <div style="width:36px;height:36px;border-radius:10px;background:rgba(255,255,255,0.03);margin-bottom:14px;display:flex;align-items:center;justify-content:center;">
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#334155" stroke-width="2"><circle cx="9" cy="21" r="1"/><circle cx="20" cy="21" r="1"/><path d="M1 1h4l2.68 13.39a2 2 0 0 0 2 1.61h9.72a2 2 0 0 0 2-1.61L23 6H6"/></svg>
            </div>
            <div class="kpi-ghost-bar" style="width:75px;margin-bottom:8px;"></div>
            <div class="kpi-ghost-bar" style="width:100px;"></div>
        </div>
        <div style="background:rgba(255,255,255,0.02);border:1px dashed rgba(255,255,255,0.07);border-radius:18px;padding:20px;">
            <div style="width:36px;height:36px;border-radius:10px;background:rgba(255,255,255,0.03);margin-bottom:14px;display:flex;align-items:center;justify-content:center;">
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#334155" stroke-width="2"><polyline points="23 6 13.5 15.5 8.5 10.5 1 18"/><polyline points="17 6 23 6 23 12"/></svg>
            </div>
            <div class="kpi-ghost-bar" style="width:50px;margin-bottom:8px;"></div>
            <div class="kpi-ghost-bar" style="width:80px;"></div>
        </div>
        <div style="background:rgba(255,255,255,0.02);border:1px dashed rgba(255,255,255,0.07);border-radius:18px;padding:20px;">
            <div style="width:36px;height:36px;border-radius:10px;background:rgba(255,255,255,0.03);margin-bottom:14px;display:flex;align-items:center;justify-content:center;">
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#334155" stroke-width="2"><path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M23 21v-2a4 4 0 0 0-3-3.87"/><path d="M16 3.13a4 4 0 0 1 0 7.75"/></svg>
            </div>
            <div class="kpi-ghost-bar" style="width:45px;margin-bottom:8px;"></div>
            <div class="kpi-ghost-bar" style="width:70px;"></div>
        </div>
    </div>
    <p style="text-align:center;font-size:.62rem;color:#334155;font-weight:700;text-transform:uppercase;letter-spacing:.12em;margin-bottom:28px;">KPI metrics will populate when data is loaded</p>
    """,
        unsafe_allow_html=True,
    )

    # Hero empty state
    st.markdown(
        """
    <div style="text-align:center;padding:20px 0 32px;">
        <div style="position:relative;display:inline-block;margin-bottom:20px;">
            <div style="position:absolute;inset:-24px;border-radius:50%;background:rgba(213,63,140,0.05);animation:none;"></div>
            <div style="width:100px;height:100px;border-radius:24px;background:linear-gradient(135deg,rgba(213,63,140,0.15),rgba(159,122,234,0.1));
                border:1px solid rgba(213,63,140,0.2);display:flex;align-items:center;justify-content:center;margin:0 auto;position:relative;">
                <svg width="44" height="44" viewBox="0 0 24 24" fill="none" stroke="#D53F8C" stroke-width="1.5">
                    <ellipse cx="12" cy="5" rx="9" ry="3"/><path d="M21 12c0 1.66-4 3-9 3s-9-1.34-9-3"/>
                    <path d="M3 5v14c0 1.66 4 3 9 3s9-1.34 9-3V5"/>
                </svg>
            </div>
        </div>
        <h2 style="font-family:'Outfit',sans-serif;font-size:2rem;font-weight:800;color:#E2E8F0;margin:0 0 10px;">No Data Connected Yet</h2>
        <p style="color:#475569;font-size:.92rem;max-width:500px;margin:0 auto;">Upload a CSV file, connect to a SQL database, or scan your Power BI file in the sidebar to unlock AI insights.</p>
    </div>
    """,
        unsafe_allow_html=True,
    )

    # Connection cards
    _cc1, _cc2, _cc3 = st.columns(3)
    _card_style = lambda border_color, icon_bg: f"""background:rgba(255,255,255,0.02);border:1px solid rgba(255,255,255,0.07);
        border-radius:20px;padding:22px;transition:all .3s;cursor:pointer;
        display:flex;flex-direction:column;gap:10px;"""

    with _cc1:
        st.markdown(
            f"""<div style="{_card_style('#D53F8C','rgba(213,63,140,0.1)')}">
            <div style="display:flex;align-items:center;gap:12px;margin-bottom:4px;">
                <div style="width:40px;height:40px;border-radius:12px;background:rgba(213,63,140,0.12);display:flex;align-items:center;justify-content:center;flex-shrink:0;">
                    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#D53F8C" stroke-width="2"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/><line x1="16" y1="13" x2="8" y2="13"/><line x1="16" y1="17" x2="8" y2="17"/><polyline points="10 9 9 9 8 9"/></svg>
                </div>
                <div><div style="font-weight:700;color:#E2E8F0;font-size:.9rem;">CSV / Excel</div><div style="font-size:.65rem;color:#64748B;font-weight:700;text-transform:uppercase;letter-spacing:.1em;">Upload</div></div>
            </div>
            <p style="color:#64748B;font-size:.8rem;line-height:1.6;margin:0;">Drag & drop any .csv or .xlsx file. AI auto-detects columns, metrics, and data types instantly.</p>
        </div>""",
            unsafe_allow_html=True,
        )
    with _cc2:
        st.markdown(
            f"""<div style="{_card_style('#60A5FA','rgba(59,130,246,0.1)')}">
            <div style="display:flex;align-items:center;gap:12px;margin-bottom:4px;">
                <div style="width:40px;height:40px;border-radius:12px;background:rgba(59,130,246,0.1);display:flex;align-items:center;justify-content:center;flex-shrink:0;">
                    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#60A5FA" stroke-width="2"><ellipse cx="12" cy="5" rx="9" ry="3"/><path d="M21 12c0 1.66-4 3-9 3s-9-1.34-9-3"/><path d="M3 5v14c0 1.66 4 3 9 3s9-1.34 9-3V5"/></svg>
                </div>
                <div><div style="font-weight:700;color:#E2E8F0;font-size:.9rem;">SQL Database</div><div style="font-size:.65rem;color:#64748B;font-weight:700;text-transform:uppercase;letter-spacing:.1em;">Connect</div></div>
            </div>
            <p style="color:#64748B;font-size:.8rem;line-height:1.6;margin:0;">Connect to SQL Server or MySQL. Enter credentials in the sidebar to load tables directly.</p>
        </div>""",
            unsafe_allow_html=True,
        )
    with _cc3:
        st.markdown(
            f"""<div style="{_card_style('#EAB308','rgba(234,179,8,0.1)')}">
            <div style="display:flex;align-items:center;gap:12px;margin-bottom:4px;">
                <div style="width:40px;height:40px;border-radius:12px;background:rgba(234,179,8,0.1);display:flex;align-items:center;justify-content:center;flex-shrink:0;">
                    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#EAB308" stroke-width="2"><rect x="2" y="3" width="6" height="18" rx="1"/><rect x="10" y="8" width="6" height="13" rx="1"/><rect x="18" y="13" width="6" height="8" rx="1"/></svg>
                </div>
                <div><div style="font-weight:700;color:#E2E8F0;font-size:.9rem;">Power BI</div><div style="font-size:.65rem;color:#64748B;font-weight:700;text-transform:uppercase;letter-spacing:.1em;">Scan</div></div>
            </div>
            <p style="color:#64748B;font-size:.8rem;line-height:1.6;margin:0;">Auto-detect running Power BI Desktop and extract live data from active tables locally.</p>
        </div>""",
            unsafe_allow_html=True,
        )

# ─────────────────────────────────────────────────────────────
#  HELPER FUNCTIONS
# ─────────────────────────────────────────────────────────────
CHART_COLORS = ["#6366F1", "#8B5CF6", "#EC4899", "#F43F5E", "#F97316", "#EAB308", "#22C55E", "#06B6D4", "#3B82F6", "#A855F7"]
ACCENT = "#6366F1"
ACCENT2 = "#EC4899"
POS_COLOR = "#22C55E"
NEG_COLOR = "#F43F5E"


def _label(col):
    return col.replace("_", " ").strip().title()


def _fmt(val, col=""):
    money_kw = ["sales", "price", "revenue", "amount", "profit", "margin", "cost", "income"]
    is_m = any(k in col.lower() for k in money_kw)
    if pd.isna(val):
        return "N/A"
    v = float(val)
    pfx = "$" if is_m else ""
    if abs(v) >= 1e9:
        return f"{pfx}{v/1e9:,.1f}B"
    elif abs(v) >= 1e6:
        return f"{pfx}{v/1e6:,.1f}M"
    elif abs(v) >= 1e3:
        return f"{pfx}{v/1e3:,.1f}K"
    return f"{pfx}{v:,.2f}" if is_m else f"{v:,.0f}"


def _theme(fig, title="", legend=True, height=400):
    fig.update_layout(
        title=dict(text=title, font=dict(size=14, color="#E2E8F0", family="Outfit,sans-serif"), x=0.02, y=0.96),
        plot_bgcolor="rgba(15,17,28,0.95)",
        paper_bgcolor="rgba(15,17,28,0.95)",
        font=dict(color="#CBD5E1", family="Inter,sans-serif", size=11),
        xaxis=dict(gridcolor="rgba(255,255,255,0.04)", zerolinecolor="rgba(255,255,255,0.05)", tickfont=dict(size=10, color="#64748B"), title_font=dict(size=11, color="#64748B"), showline=False),
        yaxis=dict(gridcolor="rgba(255,255,255,0.04)", zerolinecolor="rgba(255,255,255,0.05)", tickfont=dict(size=10, color="#64748B"), title_font=dict(size=11, color="#64748B"), showline=False),
        margin=dict(l=50, r=30, t=60, b=50),
        height=height,
        showlegend=legend,
        legend=dict(font=dict(size=10, color="#94A3B8"), bgcolor="rgba(0,0,0,0)"),
        hoverlabel=dict(bgcolor="#1E293B", font_color="#F1F5F9", bordercolor="rgba(99,102,241,0.3)", font_size=12),
    )
    return fig


# ─────────────────────────────────────────────────────────────
#  KPI ROW
# ─────────────────────────────────────────────────────────────
def render_kpis():
    money_kw = ["sales", "price", "revenue", "amount", "profit", "margin", "cost"]
    _kpi_cols = st.columns(min(4, max(1, len(business_metrics))))
    for i, col in enumerate(business_metrics[:4]):
        with _kpi_cols[i]:
            is_m = any(k in col.lower() for k in money_kw)
            val = df[col].sum()
            disp = f"${val:,.2f}" if is_m else f"{val:,.0f}"
            lbl = _label(col) if len(col) > 4 else col.upper()
            st.markdown(
                f"""<div class="kpi-card">
                <div class="kpi-label">Total {lbl}</div>
                <div class="kpi-value">{disp}</div>
            </div>""",
                unsafe_allow_html=True,
            )


# ─────────────────────────────────────────────────────────────
#  MAIN RENDERER (Cosmic Tab Management)
# ─────────────────────────────────────────────────────────────
if st.session_state.active_tab == "Dashboard":
    if df is None or df.empty:
        render_empty_state()
        st.stop()
    
    render_kpis()
    st.markdown("<div style='height:8px;'></div>", unsafe_allow_html=True)

    d1 = dimension_cols[0] if dimension_cols else None
    d2 = dimension_cols[1] if len(dimension_cols) > 1 else d1
    d3 = dimension_cols[2] if len(dimension_cols) > 2 else d2
    m1 = numeric_cols[0] if numeric_cols else main_metric
    m2 = numeric_cols[1] if len(numeric_cols) > 1 else m1
    m3 = numeric_cols[2] if len(numeric_cols) > 2 else m1
    dt = date_cols[0] if date_cols else None

    # ── Trend Analysis ─────────────────────────────────────────
    st.markdown(
        '<div style="margin:24px 0 12px;"><span style="font-family:\'Outfit\',sans-serif;font-size:1.05rem;font-weight:700;color:#E2E8F0;">📈 Trend Analysis</span><span style="font-size:.75rem;color:#334155;margin-left:10px;">Performance over time</span></div>',
        unsafe_allow_html=True,
    )
    _t1, _t2 = st.columns(2)
    with _t1:
        try:
            if dt:
                tmp = df.copy()
                tmp["_month"] = tmp[dt].dt.to_period("M").astype(str)
                agg = tmp.groupby("_month")[m1].sum().reset_index().sort_values("_month").tail(24)
                fig = px.line(agg, x="_month", y=m1, markers=True)
                fig.update_traces(line=dict(color=ACCENT, width=2.5), marker=dict(size=6, color=ACCENT, line=dict(width=1, color="#fff")), fill="tozeroy", fillcolor="rgba(99,102,241,0.07)")
                fig = _theme(fig, f"Monthly {_label(m1)} Trend", legend=False)
                fig.update_layout(xaxis=dict(tickangle=-45))
                st.plotly_chart(fig, use_container_width=True)
            elif d1:
                tmp = df.groupby(d1)[m1].sum().reset_index().nlargest(8, m1).sort_values(m1, ascending=True)
                fig = px.bar(tmp, x=m1, y=d1, orientation="h")
                fig.update_traces(marker_color=ACCENT, marker_line_width=0, text=[_fmt(v, m1) for v in tmp[m1]], textposition="outside", textfont=dict(size=10, color="#64748B"))
                fig = _theme(fig, f"Top 8 {_label(d1)} by {_label(m1)}", legend=False)
                st.plotly_chart(fig, use_container_width=True)
        except Exception:
            pass
    with _t2:
        try:
            if dt and m2 != m1:
                tmp = df.copy()
                tmp["_month"] = tmp[dt].dt.to_period("M").astype(str)
                agg = tmp.groupby("_month")[m2].sum().reset_index().sort_values("_month").tail(24)
                fig = px.area(agg, x="_month", y=m2)
                fig.update_traces(line=dict(color=ACCENT2, width=2), fillcolor="rgba(236,72,153,0.07)")
                fig = _theme(fig, f"Monthly {_label(m2)} Trend", legend=False)
                fig.update_layout(xaxis=dict(tickangle=-45))
                st.plotly_chart(fig, use_container_width=True)
            elif dt:
                tmp = df.copy()
                tmp["_year"] = tmp[dt].dt.year
                agg = tmp.groupby("_year")[m1].sum().reset_index().sort_values("_year")
                fig = px.bar(agg, x="_year", y=m1)
                fig.update_traces(marker_color=ACCENT2, marker_line_width=0, text=[_fmt(v, m1) for v in agg[m1]], textposition="outside", textfont=dict(size=10, color="#64748B"))
                fig = _theme(fig, f"Yearly {_label(m1)} Summary", legend=False)
                st.plotly_chart(fig, use_container_width=True)
            elif d2 and d2 != d1:
                tmp = df.groupby(d2)[m1].sum().reset_index().nlargest(8, m1).sort_values(m1, ascending=False)
                fig = px.bar(tmp, x=d2, y=m1)
                fig.update_traces(marker_color=ACCENT2, marker_line_width=0, text=[_fmt(v, m1) for v in tmp[m1]], textposition="outside", textfont=dict(size=10, color="#64748B"))
                fig = _theme(fig, f"Top 8 {_label(d2)} by {_label(m1)}", legend=False)
                fig.update_layout(xaxis=dict(tickangle=-30))
                st.plotly_chart(fig, use_container_width=True)
        except Exception:
            pass

    # ── Composition ────────────────────────────────────────────
    st.markdown('<div style="margin:24px 0 12px;"><span style="font-family:\'Outfit\',sans-serif;font-size:1.05rem;font-weight:700;color:#E2E8F0;">🍩 Composition & Breakdown</span><span style="font-size:.75rem;color:#334155;margin-left:10px;">How values are distributed</span></div>', unsafe_allow_html=True)
    _c1, _c2 = st.columns(2)
    with _c1:
        try:
            if d1:
                tmp = df.groupby(d1)[m1].sum().reset_index().nlargest(6, m1)
                tot = df[m1].sum()
                shown = tmp[m1].sum()
                if tot > 0 and (tot - shown) / tot > 0.01:
                    tmp = pd.concat([tmp, pd.DataFrame({d1: ["Others"], m1: [tot - shown]})], ignore_index=True)
                fig = px.pie(tmp, names=d1, values=m1, hole=0.55, color_discrete_sequence=CHART_COLORS)
                fig.update_traces(textposition="outside", textinfo="label+percent", textfont=dict(size=10, color="#CBD5E1"), pull=[0.03] * len(tmp), marker=dict(line=dict(color="#0F111C", width=2)))
                fig = _theme(fig, f"{_label(m1)} by {_label(d1)}", legend=False)
                st.plotly_chart(fig, use_container_width=True)
        except Exception:
            pass
    with _c2:
        try:
            td = d2 if d2 and d2 != d1 else (d3 if d3 and d3 != d1 else d1)
            tm = m2 if m2 != m1 else m1
            if td:
                tmp = df.groupby(td)[tm].sum().reset_index().nlargest(6, tm)
                tot = df[tm].sum()
                shown = tmp[tm].sum()
                if tot > 0 and (tot - shown) / tot > 0.01:
                    tmp = pd.concat([tmp, pd.DataFrame({td: ["Others"], tm: [tot - shown]})], ignore_index=True)
                fig = px.pie(tmp, names=td, values=tm, color_discrete_sequence=CHART_COLORS[3:])
                fig.update_traces(textposition="outside", textinfo="label+percent", textfont=dict(size=10, color="#CBD5E1"), marker=dict(line=dict(color="#0F111C", width=2)))
                fig = _theme(fig, f"{_label(tm)} Share by {_label(td)}", legend=False)
                st.plotly_chart(fig, use_container_width=True)
        except Exception:
            pass

    # ── Top & Bottom ────────────────────────────────────────────
    st.markdown('<div style="margin:24px 0 12px;"><span style="font-family:\'Outfit\',sans-serif;font-size:1.05rem;font-weight:700;color:#E2E8F0;">🏆 Top & Bottom Performers</span><span style="font-size:.75rem;color:#334155;margin-left:10px;">Best and worst categories</span></div>', unsafe_allow_html=True)
    _r1, _r2 = st.columns(2)
    with _r1:
        try:
            if d1:
                tmp = df.groupby(d1)[main_metric].sum().reset_index().nlargest(8, main_metric).sort_values(main_metric, ascending=True)
                fig = px.bar(tmp, x=main_metric, y=d1, orientation="h", color_discrete_sequence=[POS_COLOR])
                fig.update_traces(marker_line_width=0, text=[_fmt(v, main_metric) for v in tmp[main_metric]], textposition="outside", textfont=dict(size=10, color="#64748B"))
                fig = _theme(fig, f"🟢 Top 8 {_label(d1)} by {_label(main_metric)}", legend=False, height=380)
                fig.update_layout(yaxis_title="")
                st.plotly_chart(fig, use_container_width=True)
        except Exception:
            pass
    with _r2:
        try:
            if d1:
                tmp = df.groupby(d1)[main_metric].sum().reset_index()
                tmp = tmp[tmp[main_metric] > 0].nsmallest(8, main_metric).sort_values(main_metric, ascending=False)
                fig = px.bar(tmp, x=main_metric, y=d1, orientation="h", color_discrete_sequence=[NEG_COLOR])
                fig.update_traces(marker_line_width=0, text=[_fmt(v, main_metric) for v in tmp[main_metric]], textposition="outside", textfont=dict(size=10, color="#64748B"))
                fig = _theme(fig, f"🔴 Bottom 8 {_label(d1)} by {_label(main_metric)}", legend=False, height=380)
                fig.update_layout(yaxis_title="")
                st.plotly_chart(fig, use_container_width=True)
        except Exception:
            pass

    # ── Distribution ────────────────────────────────────────────
    st.markdown('<div style="margin:24px 0 12px;"><span style="font-family:\'Outfit\',sans-serif;font-size:1.05rem;font-weight:700;color:#E2E8F0;">📊 Distribution & Volume</span><span style="font-size:.75rem;color:#334155;margin-left:10px;">Data spread and frequency</span></div>', unsafe_allow_html=True)
    _d1, _d2 = st.columns(2)
    with _d1:
        try:
            cd = d2 if d2 and d2 != d1 else d1
            cm = m2 if m2 != m1 else m1
            if cd:
                tmp = df.groupby(cd)[cm].sum().reset_index().nlargest(10, cm).sort_values(cm, ascending=False)
                fig = px.bar(tmp, x=cd, y=cm, color_discrete_sequence=[ACCENT])
                fig.update_traces(marker_line_width=0, text=[_fmt(v, cm) for v in tmp[cm]], textposition="outside", textfont=dict(size=9, color="#64748B"))
                fig = _theme(fig, f"{_label(cm)} by {_label(cd)} (Top 10)", legend=False)
                fig.update_layout(xaxis=dict(tickangle=-30))
                st.plotly_chart(fig, use_container_width=True)
        except Exception:
            pass
    with _d2:
        try:
            sample = df[m1].dropna()
            if len(sample) > 5000:
                sample = sample.sample(5000)
            fig = px.histogram(sample, x=m1, nbins=25, color_discrete_sequence=["#8B5CF6"])
            fig.update_traces(marker_line_width=0.5, marker_line_color="#0F111C", opacity=0.85)
            fig = _theme(fig, f"Distribution of {_label(m1)}", legend=False)
            fig.update_layout(xaxis_title=_label(m1), yaxis_title="Frequency", bargap=0.03)
            st.plotly_chart(fig, use_container_width=True)
        except Exception:
            pass

    # ── Multi-Metric ────────────────────────────────────────────
    if len(numeric_cols) >= 2:
        st.markdown('<div style="margin:24px 0 12px;"><span style="font-family:\'Outfit\',sans-serif;font-size:1.05rem;font-weight:700;color:#E2E8F0;">⚖️ Multi-Metric Comparison</span><span style="font-size:.75rem;color:#334155;margin-left:10px;">Side-by-side metric analysis</span></div>', unsafe_allow_html=True)
        _m1, _m2 = st.columns(2)
        with _m1:
            try:
                if d1 and m1 != m2:
                    tmp = df.groupby(d1).agg({m1: "sum", m2: "sum"}).reset_index().nlargest(8, m1)
                    fig = px.bar(tmp, x=d1, y=[m1, m2], barmode="group", color_discrete_sequence=[ACCENT, ACCENT2], labels={m1: _label(m1), m2: _label(m2)})
                    fig.update_traces(marker_line_width=0)
                    fig = _theme(fig, f"{_label(m1)} vs {_label(m2)} by {_label(d1)}", legend=True)
                    fig.update_layout(xaxis=dict(tickangle=-30), legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1))
                    st.plotly_chart(fig, use_container_width=True)
            except Exception:
                pass
        with _m2:
            try:
                sm1, sm2 = m1, m3 if m3 != m1 else m2
                if sm1 != sm2:
                    sample = df[[sm1, sm2]].dropna()
                    if len(sample) > 1500:
                        sample = sample.sample(1500)
                    fig = px.scatter(sample, x=sm1, y=sm2, color_discrete_sequence=[ACCENT], opacity=0.5)
                    fig.update_traces(marker=dict(size=5, line=dict(width=0)))
                    fig = _theme(fig, f"Correlation: {_label(sm1)} vs {_label(sm2)}", legend=False)
                    st.plotly_chart(fig, use_container_width=True)
            except Exception:
                pass

    # ── Summary Table ────────────────────────────────────────────
    st.markdown('<div style="margin:24px 0 12px;"><span style="font-family:\'Outfit\',sans-serif;font-size:1.05rem;font-weight:700;color:#E2E8F0;">📋 Data Summary Table</span><span style="font-size:.75rem;color:#334155;margin-left:10px;">Key aggregated metrics at a glance</span></div>', unsafe_allow_html=True)
    try:
        if d1:
            metrics_to_show = [m for m in business_metrics[:4] if m in df.columns] or numeric_cols[:4]
            agg_dict = {m: ["sum", "mean"] for m in metrics_to_show[:2]}
            for m in metrics_to_show[2:]:
                agg_dict[m] = ["sum"]
            summary = df.groupby(d1).agg(agg_dict).reset_index()
            summary.columns = [
                f"{c[0]}_{c[1]}" if c[1] else c[0] for c in summary.columns
            ]
            summary.columns = [
                c.replace("_sum", " (Total)").replace("_mean", " (Avg)").replace("_", " ").strip().title()
                for c in summary.columns
            ]
            scol = [c for c in summary.columns if "(Total)" in c]
            if scol:
                summary = summary.sort_values(scol[0], ascending=False)
            st.dataframe(summary.head(15), use_container_width=True, hide_index=True)
    except Exception:
        pass

elif st.session_state.active_tab == "Copilot":
    if df is None or df.empty:
        render_empty_state()
        st.stop()

    render_kpis()
    st.markdown("<div style='height:16px;'></div>", unsafe_allow_html=True)

    # ── Autonomous Scan ────────────────────────────────────────
    if st.button("⚡ Run Autonomous Insight Scan", type="primary"):
        _lc = st.empty()
        _pb = _lc.progress(0, text="AI Analysis in progress...")
        num_metrics = df[numeric_cols].agg(["count", "nunique", "max", "min", "sum"])
        time.sleep(0.4)
        _pb.progress(25, text="Generated numerical summaries.")
        dim_insights = {}
        for dim in dimension_cols:
            grp = df.groupby(dim)[main_metric].sum()
            if len(grp) > 1:
                dim_insights[dim] = grp
        time.sleep(0.4)
        _pb.progress(60, text="Analyzed categoricals.")
        date_insights = {}
        if date_cols:
            grp = df.groupby(df[date_cols[0]].dt.year)[main_metric].sum()
            if len(grp) > 1:
                date_insights[date_cols[0]] = grp
        time.sleep(0.3)
        _pb.progress(100, text="Scan complete!")
        time.sleep(0.3)
        _lc.empty()

        money_kw = ["sales", "price", "revenue", "amount", "profit", "margin", "cost"]
        no_sum_cols = ["ordernumber", "orderid", "year", "month", "day", "qtr", "id", "code", "number", "zip", "pin", "phone", "lat", "lon", "index"]
        sum_allow_kw = ["sales", "revenue", "profit", "margin", "amount", "income", "quantity", "cost", "price", "delay", "duration", "charging", "kw", "unit", "sold", "total"]

        def _skip_sum(col):
            return any(t in col.lower() for t in no_sum_cols) or not any(t in col.lower() for t in sum_allow_kw)

        st.markdown('<div style="margin:16px 0 10px;"><span style="font-family:\'Outfit\',sans-serif;font-size:1.05rem;font-weight:700;color:#E2E8F0;">🔢 Numerical Insights</span></div>', unsafe_allow_html=True)
        for i in range(0, len(numeric_cols), 4):
            _cols = st.columns(4)
            for j in range(4):
                if i + j < len(numeric_cols):
                    col = numeric_cols[i + j]
                    is_m = any(k in col.lower() for k in money_kw)
                    mx = num_metrics.loc["max", col]
                    mn = num_metrics.loc["min", col]
                    sm = num_metrics.loc["sum", col]
                    ct = num_metrics.loc["count", col]
                    uq = num_metrics.loc["nunique", col]
                    fmt = lambda v: f"${v:,.2f}" if is_m else f"{v:,.0f}"
                    with _cols[j]:
                        if _skip_sum(col):
                            st.markdown(f'<div class="insight-card"><b class="insight-title">{col}</b>Count: {ct:,.0f}<br>Unique: {uq:,}<br>Max: {fmt(mx)}<br>Min: {fmt(mn)}</div>', unsafe_allow_html=True)
                        else:
                            st.markdown(f'<div class="insight-card"><b class="insight-title">{col}</b>Total: {fmt(sm)}<br>Unique: {uq:,}<br>Max: {fmt(mx)}<br>Min: {fmt(mn)}</div>', unsafe_allow_html=True)

        if dim_insights:
            st.markdown('<div style="margin:16px 0 10px;"><span style="font-family:\'Outfit\',sans-serif;font-size:1.05rem;font-weight:700;color:#E2E8F0;">🗂️ Descriptive Insights</span></div>', unsafe_allow_html=True)
            for dim, grp in dim_insights.items():
                is_m = any(k in main_metric.lower() for k in money_kw)
                bv = grp.max()
                wv = grp.min()
                bd = f"${bv:,.2f}" if is_m else f"{bv:,.0f}"
                wd = f"${wv:,.2f}" if is_m else f"{wv:,.0f}"
                st.markdown(f'<div class="insight-card"><b class="insight-title">{dim}</b>Best: {grp.idxmax()} ({bd})<br>Worst: {grp.idxmin()} ({wd})</div>', unsafe_allow_html=True)

        if date_insights:
            st.markdown('<div style="margin:16px 0 10px;"><span style="font-family:\'Outfit\',sans-serif;font-size:1.05rem;font-weight:700;color:#E2E8F0;">📅 Date Insights</span></div>', unsafe_allow_html=True)
            for d, grp in date_insights.items():
                is_m = any(k in main_metric.lower() for k in money_kw)
                bv = grp.max()
                wv = grp.min()
                bd = f"${bv:,.2f}" if is_m else f"{bv:,.0f}"
                wd = f"${wv:,.2f}" if is_m else f"{wv:,.0f}"
                st.markdown(f'<div class="insight-card"><b class="insight-title">{d}</b>Best Year: {int(grp.idxmax())} ({bd})<br>Worst Year: {int(grp.idxmin())} ({wd})</div>', unsafe_allow_html=True)

    st.markdown("<div style='height:8px;'></div>", unsafe_allow_html=True)

    # ── AI Copilot Section Header ──────────────────────────────
    st.markdown(
        """<div style="background:rgba(213,63,140,0.04);border:1px solid rgba(213,63,140,0.18);border-radius:20px;padding:20px 24px;margin-bottom:16px;">
        <h3 style="font-family:'Outfit',sans-serif;font-size:1.4rem;font-weight:800;margin:0 0 4px;">
            <span style="color:#D53F8C;">AI</span> <span style="color:#E2E8F0;">Copilot</span> <span style="color:#E2E8F0;">Insights</span>
        </h3>
        <p style="color:#475569;font-size:.82rem;margin:0;">Ask any business question in plain English — get SQL results, charts & AI analysis instantly.</p></div>""",
        unsafe_allow_html=True,
    )

    # ── NLQ Form ───────────────────────────────────────────────
    if "agg_option" not in st.session_state:
        st.session_state.agg_option = "None (show raw data)"
    if "chat_history" not in st.session_state:
        st.session_state.chat_history = []

    with st.form("ask_form", border=False):
        _qcol, _bcol = st.columns([5, 1])
        with _qcol:
            q = st.text_input("Question", placeholder='e.g. "Top 5 countries by total sales"', label_visibility="collapsed")
        with _bcol:
            ask_pressed = st.form_submit_button("ASK →", type="primary", use_container_width=True)

    agg_option = st.selectbox(
        "Aggregation override (optional):",
        ["None (show raw data)", "COUNT", "DISTINCT COUNT", "SUM", "AVG", "MIN", "MAX"],
        key="agg_option",
    )

    # Memory status
    _mc1, _mc2 = st.columns([4, 1])
    with _mc1:
        if st.session_state.chat_history:
            st.markdown(f'<div style="background:rgba(99,102,241,0.07);border:1px solid rgba(99,102,241,0.2);border-radius:10px;padding:8px 14px;font-size:.78rem;color:#A5B4FC;">🧠 Memory active — remembering context from last {len(st.session_state.chat_history)} quer{"y" if len(st.session_state.chat_history)==1 else "ies"}.</div>', unsafe_allow_html=True)
        else:
            st.markdown('<div style="font-size:.75rem;color:#334155;">🧠 Memory empty — ask a question to start building context.</div>', unsafe_allow_html=True)
    with _mc2:
        if st.button("🗑️ Clear", use_container_width=True):
            st.session_state.chat_history = []
            st.rerun()

    # ── Intelligence Engine ────────────────────────────────────
    SYNONYMS = {"product":"productline","products":"productline","item":"productline","category":"productline","order":"ordernumber","orders":"ordernumber","date":"orderdate","country":"country","region":"country","status":"status","city":"city","customer":"customername","territory":"territory","month":"month_id","year":"year_id","performing":"sales","performance":"sales"}
    MONTH_MAP = {"january":1,"jan":1,"february":2,"feb":2,"march":3,"mar":3,"april":4,"apr":4,"may":5,"june":6,"jun":6,"july":7,"jul":7,"august":8,"aug":8,"september":9,"sep":9,"october":10,"oct":10,"november":11,"nov":11,"december":12,"dec":12}
    AGG_KEYWORDS = {"total":"SUM","sum":"SUM","average":"AVG","avg":"AVG","mean":"AVG","count":"COUNT","number of":"COUNT","how many":"COUNT","minimum":"MIN","min":"MIN","maximum":"MAX","max":"MAX","distinct":"DISTINCT COUNT","unique":"DISTINCT COUNT"}

    def understand_data_structure():
        profile = {"table_name":"data","columns":list(df.columns),"dimensions":dimension_cols,"metrics":numeric_cols,"date_fields":date_cols,"sample_values":{},"column_domains":{},"row_count":len(df)}
        for col in df.columns:
            if col in dimension_cols:
                uv = df[col].dropna().unique()
                profile["sample_values"][col] = {"unique_count":int(len(uv)),"examples":[str(v) for v in uv[:10]]}
            elif col in numeric_cols:
                profile["column_domains"][col] = {"min":float(df[col].min()) if not pd.isna(df[col].min()) else 0,"max":float(df[col].max()) if not pd.isna(df[col].max()) else 0,"avg":float(df[col].mean()) if not pd.isna(df[col].mean()) else 0,"sum":float(df[col].sum()) if not pd.isna(df[col].sum()) else 0,"nulls":int(df[col].isna().sum())}
            elif col in date_cols:
                nn = df[col].dropna()
                if len(nn):
                    profile["column_domains"][col] = {"min_date":str(nn.min()),"max_date":str(nn.max())}
        return profile

    def _build_schema_ctx():
        dp = understand_data_structure()
        lines = []
        for col in df.columns:
            ct = "NUMERIC" if col in numeric_cols else ("DATE/TIMESTAMP" if col in date_cols else "TEXT/CATEGORICAL")
            line = f"  • {col}  [{ct}]"
            if col in dp["sample_values"]:
                info = dp["sample_values"][col]
                line += f"\n      unique_count={info['unique_count']}  sample=[{' | '.join(info['examples'][:12])}]"
            if col in dp["column_domains"]:
                dom = dp["column_domains"][col]
                if "min_date" in dom:
                    line += f"\n      date_range=[{dom['min_date']} → {dom['max_date']}]"
                else:
                    line += f"\n      min={dom['min']:,.2f}  max={dom['max']:,.2f}  avg={dom['avg']:,.2f}  sum={dom['sum']:,.2f}  nulls={dom['nulls']}"
            lines.append(line)
        schema_str = "\n".join(lines)
        freq_lines = []
        for col in dimension_cols[:8]:
            try:
                top = df[col].value_counts().head(5)
                formatted_items = [f"{v!r} ({c:,})" for v, c in top.items()]
                freq_lines.append(f"  • {col}: {'  |  '.join(formatted_items)}")
            except Exception:
                pass
        return schema_str, "\n".join(freq_lines) if freq_lines else "(none)", dp

    def _build_prompt(question, agg, schema_str, freq_str="", error_ctx=None):
        hist = ""
        if st.session_state.chat_history:
            hist = "\n=== CONVERSATION HISTORY ===\n"
            for qp, sp in st.session_state.chat_history[-6:]:
                hist += f'Q: "{qp}"\nSQL: {sp}\n---\n'
            hist += "RULE: For follow-ups (it/that/those/same), modify the most recent SQL.\n"
        err = ""
        if error_ctx:
            err = f"\n=== SELF-REPAIR MODE ===\nFailed SQL:\n{error_ctx['sql']}\nError:\n{error_ctx['error']}\nFix ALL issues: typos, missing FROM, GROUP BY, ILIKE for strings, NULLIF for division.\n=========================\n"
        few_shot = """
=== FEW-SHOT EXAMPLES ===
Q: "total sales by country"
SQL: SELECT country, SUM(sales) AS total_sales FROM data GROUP BY country ORDER BY total_sales DESC

Q: "top 5 products by revenue"
SQL: SELECT productline, SUM(sales) AS total_revenue FROM data GROUP BY productline ORDER BY total_revenue DESC LIMIT 5

Q: "monthly sales trend"
SQL: SELECT EXTRACT(YEAR FROM orderdate) AS yr, EXTRACT(MONTH FROM orderdate) AS mo, SUM(sales) AS monthly_sales FROM data GROUP BY yr, mo ORDER BY yr, mo

Q: "show orders where status is shipped"
SQL: SELECT * FROM data WHERE status ILIKE 'shipped' LIMIT 100

Q: "percentage share of each product in total sales"
SQL: SELECT productline, SUM(sales) AS product_sales, ROUND(100.0*SUM(sales)/SUM(SUM(sales)) OVER(),2) AS pct FROM data GROUP BY productline ORDER BY product_sales DESC

Q: "year over year growth"
SQL: SELECT yr, total_sales, LAG(total_sales) OVER(ORDER BY yr) AS prev, ROUND(100.0*(total_sales-LAG(total_sales) OVER(ORDER BY yr))/NULLIF(LAG(total_sales) OVER(ORDER BY yr),0),2) AS yoy_pct FROM (SELECT EXTRACT(YEAR FROM orderdate) AS yr, SUM(sales) AS total_sales FROM data GROUP BY yr) ORDER BY yr
=========================
"""
        return f"""You are an elite Senior Data Analyst and DuckDB SQL expert.
Translate the user's question into a single, correct DuckDB SQL query.
ONLY use exact column names from the schema. NEVER hallucinate columns.

TABLE: data   (rows: {len(df):,})

SCHEMA:
{schema_str}

TOP VALUE FREQUENCIES:
{freq_str}

{hist}
{err}
{few_shot}

RULES (all mandatory):
1. Use ONLY exact column names from schema (lowercase+underscores).
2. Every query MUST have FROM data.
3. Every non-aggregated SELECT column MUST be in GROUP BY.
4. Use ILIKE for string matching. SUM/AVG/COUNT/MIN/MAX per question intent.
5. Top N → ORDER BY ... DESC LIMIT N. Bottom N → ASC.
6. COUNT(DISTINCT col) syntax — never COUNT(DISTINCT(col)).
7. NULLIF(divisor,0) for all divisions.
8. Every derived column MUST have an AS alias.
9. Current agg override: "{agg}" (apply if not "None (show raw data)").
10. Return ONLY the raw SQL SELECT. No markdown, no explanation. Start with SELECT.

USER QUESTION: "{question}"

SQL:"""

    def _is_general(q):
        q_l = q.lower().strip()
        data_triggers = ["my data","this data","the data","dataset","table","column","chart","show","display","filter","sort","aggregate","group","total","sum","count","average","trend","top","bottom","best","worst","sales","revenue","profit"]
        for t in data_triggers:
            if t in q_l:
                return False
        for col in df.columns:
            if col.replace("_"," ") in q_l or col in q_l:
                return False
        general_triggers = ["what is","what are","how does","how do","explain","define","tell me","describe","who is","why is","hello","hi","thanks","help me understand","difference between"]
        return any(q_l.startswith(t) or t in q_l for t in general_triggers)

    def _answer_general(question):
        resp = client.chat.completions.create(
            model="nvidia/nemotron-3-super-120b-a12b",
            messages=[{"role":"user","content":f"You are a highly intelligent AI assistant. Answer clearly and helpfully.\n\nUser question: {question}\n\nAnswer:"}],
            temperature=0.6, top_p=0.95, max_tokens=1024,
        )
        return resp.choices[0].message.content.strip()

    def smart_query(question, selected_agg):
        schema_str, freq_str, _ = _build_schema_ctx()
        def _call_llm(prompt):
            res = client.chat.completions.create(
                model="nvidia/nemotron-3-super-120b-a12b",
                messages=[{"role":"user","content":prompt}],
                temperature=0.0, top_p=0.95, max_tokens=1024,
            )
            sql = res.choices[0].message.content.strip()
            sql = re.sub(r"^```sql\s*\n?","",sql,flags=re.MULTILINE)
            sql = re.sub(r"^```\s*\n?","",sql,flags=re.MULTILINE)
            sql = re.sub(r"\n?```$","",sql,flags=re.MULTILINE).strip()
            m = re.search(r"(SELECT\s)",sql,re.IGNORECASE)
            if m and m.start() > 0:
                sql = sql[m.start():]
            return sql
        last_sql, last_err = None, None
        for attempt in range(3):
            try:
                prompt = _build_prompt(question, selected_agg, schema_str, freq_str, {"sql":last_sql,"error":str(last_err)} if attempt>0 else None)
                sql = _call_llm(prompt)
                last_sql = sql
                if not sql.upper().strip().startswith("SELECT"):
                    raise Exception(f"Not a valid SELECT: {sql[:100]}")
                if "FROM" not in sql.upper():
                    raise Exception("Missing FROM clause")
                con = duckdb.connect()
                try:
                    con.register("data", df)
                    result = con.execute(sql).df()
                finally:
                    con.close()
                st.session_state.chat_history.append((question, sql))
                if len(st.session_state.chat_history) > 10:
                    st.session_state.chat_history = st.session_state.chat_history[-10:]
                return result, sql
            except Exception as e:
                last_err = e
                if attempt < 2:
                    continue
        raise Exception(f"Failed after 3 attempts.\nLast SQL: {last_sql}\nLast Error: {last_err}")

    def _deep_insight(question, result_df):
        money_kw = ["sales","revenue","profit","margin","cost","price","amount"]
        stats = []
        for col in result_df.columns:
            if pd.api.types.is_numeric_dtype(result_df[col]):
                is_m = any(k in col.lower() for k in money_kw)
                fmt = "${:,.2f}" if is_m else "{:,.0f}"
                stats.append(f"  {col}: total={fmt.format(result_df[col].sum())}  avg={fmt.format(result_df[col].mean())}  max={fmt.format(result_df[col].max())}  min={fmt.format(result_df[col].min())}")
        prompt = f"""You are a world-class BI Analyst (McKinsey/BCG level).

USER QUESTION: "{question}"

QUERY RESULT (top 20 rows):
{result_df.head(20).to_string(index=False)}

STATS:
{chr(10).join(stats) if stats else '(non-numeric)'}

DATASET CONTEXT: {len(df):,} total rows | Metrics: {', '.join(business_metrics[:4])} | Dimensions: {', '.join(dimension_cols[:5])}

Write a sharp boardroom-ready insight (150-200 words):

**Key Finding:** (1 sentence — most important finding)

**Why It Matters:** (2-3 sentences — business implication)

**Recommended Action:** (1-2 specific, concrete actions)

**Watch Out For:** (1 risk or caveat)

Rules: Be specific with numbers. Be decisive. No hedging. No "based on the data"."""
        resp = client.chat.completions.create(
            model="nvidia/nemotron-3-super-120b-a12b",
            messages=[{"role":"user","content":prompt}],
            temperature=0.65, top_p=0.95, max_tokens=600,
        )
        return resp.choices[0].message.content.strip()

    # ── Main Ask Handler ───────────────────────────────────────
    if ask_pressed and q:
        try:
            _lc = st.empty()
            _pb = _lc.progress(5, text="Translating to SQL... 5%")

            if _is_general(q):
                _pb.progress(50, text="Generating AI answer... 50%")
                gen_ans = _answer_general(q)
                _pb.progress(100, text="Done!")
                time.sleep(0.25)
                _lc.empty()
                st.markdown(
                    f"""<div style="background:rgba(99,102,241,0.07);border:1px solid rgba(99,102,241,0.22);border-radius:16px;padding:22px 26px;margin-top:10px;">
                    <div style="font-size:.7rem;color:#6366F1;font-weight:700;letter-spacing:.1em;margin-bottom:10px;">💬 AI ANSWER</div>
                    <div style="line-height:1.75;color:#E2E8F0;font-size:.9rem;">{gen_ans.replace(chr(10),'<br>')}</div></div>""",
                    unsafe_allow_html=True,
                )
            else:
                result, generated_sql = smart_query(q, st.session_state.agg_option)
                time.sleep(0.2)
                _pb.progress(55, text="Executing on DuckDB... 55%")

                # Build chart
                fig = None
                is_metric = False
                metric_col_name = None
                metric_val = None

                if len(result.columns) >= 2 and len(result) > 1:
                    _pb.progress(70, text="Rendering visualizations... 70%")
                    col1, col2 = result.columns[0], result.columns[1]
                    nr = len(result)
                    q_l = q.lower()
                    is_date = pd.api.types.is_datetime64_any_dtype(result[col1]) or (result[col1].dtype == "object" and bool(re.match(r"^\d{4}-\d{2}-\d{2}", str(result[col1].iloc[0]))))
                    is_c1n = pd.api.types.is_numeric_dtype(result[col1])
                    is_c2n = pd.api.types.is_numeric_dtype(result[col2])
                    is_time = any(t in col1.lower() for t in ["year","month","quarter","qtr","week","date","day"])
                    w_trend = any(w in q_l for w in ["trend","over time","monthly","yearly","quarterly","growth","timeline"])
                    w_dist = any(w in q_l for w in ["distribution","share","proportion","percentage","pie","composition"])
                    w_rank = any(w in q_l for w in ["top","bottom","best","worst","highest","lowest","rank","most","least"])
                    w_corr = any(w in q_l for w in ["correlation","scatter","relationship"])
                    w_area = any(w in q_l for w in ["area","cumulative","stacked"])
                    w_treemap = any(w in q_l for w in ["treemap","tree map","hierarchy"])
                    w_funnel = any(w in q_l for w in ["funnel","pipeline","stages"])
                    has_multi = len(result.columns) >= 3 and sum(pd.api.types.is_numeric_dtype(result[c]) for c in result.columns) >= 2
                    try:
                        if w_funnel and not is_c1n and is_c2n and nr <= 10:
                            fig = px.funnel(result, x=col2, y=col1, title=f"{_label(col2)} Funnel")
                        elif w_treemap and not is_c1n and is_c2n:
                            fig = px.treemap(result, path=[col1], values=col2, title=f"{_label(col2)} by {_label(col1)}")
                        elif w_area and is_c2n and (is_date or is_time):
                            fig = px.area(result.sort_values(col1), x=col1, y=col2, title=f"{_label(col2)} over {_label(col1)}")
                        elif w_dist and not is_c1n and is_c2n and nr <= 8:
                            fig = px.pie(result, names=col1, values=col2, hole=0.4, title=f"Distribution of {_label(col2)}")
                        elif w_corr and is_c1n and is_c2n:
                            fig = px.scatter(result, x=col1, y=col2, title=f"{_label(col2)} vs {_label(col1)}", trendline="ols")
                        elif (is_date or is_time) and is_c2n:
                            srt = result.sort_values(col1)
                            if w_trend or nr > 6:
                                fig = px.line(srt, x=col1, y=col2, markers=True, title=f"{_label(col2)} over {_label(col1)}")
                            else:
                                fig = px.bar(srt, x=col1, y=col2, title=f"{_label(col2)} by {_label(col1)}")
                        elif w_rank and not is_c1n and is_c2n:
                            srt = result.sort_values(col2, ascending=True)
                            fig = px.bar(srt, x=col2, y=col1, orientation="h", title=f"{_label(col2)} by {_label(col1)}")
                        elif has_multi and not is_c1n:
                            nm_cols = [c for c in result.columns if pd.api.types.is_numeric_dtype(result[c])]
                            fig = px.bar(result, x=col1, y=nm_cols, barmode="group", title=f"Comparison by {_label(col1)}")
                        elif is_c1n and is_c2n and not is_time:
                            fig = px.scatter(result, x=col1, y=col2, title=f"{_label(col2)} vs {_label(col1)}", trendline="ols")
                        elif not is_c1n and is_c2n:
                            if nr <= 5 and not w_rank:
                                fig = px.pie(result, names=col1, values=col2, hole=0.4, title=f"{_label(col2)} by {_label(col1)}")
                            elif nr <= 12:
                                fig = px.bar(result.sort_values(col2, ascending=False), x=col1, y=col2, title=f"{_label(col2)} by {_label(col1)}")
                            else:
                                fig = px.bar(result.sort_values(col2, ascending=True), x=col2, y=col1, orientation="h", title=f"{_label(col2)} by {_label(col1)}")
                        else:
                            fig = px.bar(result, x=col1, y=col2, title=f"{_label(col2)} by {_label(col1)}")
                    except Exception:
                        try:
                            fig = px.bar(result, x=col1, y=col2)
                        except Exception:
                            pass

                    if fig:
                        fig.update_layout(
                            plot_bgcolor="#0a0c14", paper_bgcolor="#0a0c14",
                            font=dict(color="#CBD5E1", family="Inter,sans-serif"),
                            title_font=dict(size=15, color="#E2E8F0", family="Outfit,sans-serif"),
                            xaxis=dict(gridcolor="rgba(255,255,255,0.04)", zerolinecolor="rgba(255,255,255,0.06)"),
                            yaxis=dict(gridcolor="rgba(255,255,255,0.04)", zerolinecolor="rgba(255,255,255,0.06)"),
                            margin=dict(l=40, r=30, t=55, b=40),
                            hoverlabel=dict(bgcolor="#141620", font_color="#E2E8F0", bordercolor="rgba(213,63,140,0.3)"),
                            height=420,
                        )
                        fig.update_traces(marker_color="#D53F8C", selector=dict(type="bar"))

                elif len(result.columns) == 1 and len(result) == 1:
                    is_metric = True
                    metric_col_name = result.columns[0]
                    metric_val = result.iloc[0, 0]

                _pb.progress(85, text="Generating AI insight... 85%")
                insight = _deep_insight(q, result)

                _pb.progress(100, text="Done!")
                time.sleep(0.25)
                _lc.empty()

                # ── Render results (Document 5 style) ─────────────
                # SQL code block
                st.markdown(
                    f"""<div style="background:rgba(255,255,255,0.02);border:1px solid rgba(255,255,255,0.07);border-radius:16px;padding:16px 20px;margin-bottom:16px;">
                    <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:10px;">
                        <div style="display:flex;align-items:center;gap:8px;">
                            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="#D53F8C" stroke-width="2"><polyline points="4 17 10 11 4 5"/><line x1="12" y1="19" x2="20" y2="19"/></svg>
                            <span style="font-size:.68rem;font-weight:700;color:#64748B;text-transform:uppercase;letter-spacing:.1em;">Generated SQL</span>
                        </div>
                        <span style="font-size:.65rem;color:#334155;">{len(result):,} rows returned</span>
                    </div>
                    <pre style="background:rgba(0,0,0,0.25);border-radius:10px;padding:12px 16px;font-family:'JetBrains Mono','Courier New',monospace;font-size:.78rem;color:#D53F8C;overflow-x:auto;margin:0;white-space:pre-wrap;">{generated_sql}</pre>
                </div>""",
                    unsafe_allow_html=True,
                )

                # Data table
                st.dataframe(result, use_container_width=True, hide_index=True)

                # Chart
                if fig:
                    st.plotly_chart(fig, use_container_width=True)
                elif is_metric:
                    money_kw = ["sales","revenue","price","amount","profit","margin","cost","sum","total"]
                    is_m = any(k in metric_col_name.lower() for k in money_kw)
                    disp = f"${metric_val:,.2f}" if (is_m and isinstance(metric_val,(int,float))) else (f"{metric_val:,.2f}" if isinstance(metric_val,(int,float)) else metric_val)
                    st.metric("Result", disp)

                # AI Insight card (Document 5 style)
                _insight_html = insight.replace(chr(10), "<br>")
                # Bold markdown to HTML
                _insight_html = re.sub(r"\*\*(.+?)\*\*", r"<b style='color:#E2E8F0;'>\1</b>", _insight_html)
                st.markdown(
                    f"""<div style="background:rgba(213,63,140,0.05);border:1px solid rgba(213,63,140,0.22);border-radius:18px;padding:24px 28px;margin-top:14px;">
                    <div style="display:flex;align-items:center;gap:8px;margin-bottom:14px;">
                        <div style="width:32px;height:32px;border-radius:10px;background:rgba(213,63,140,0.15);display:flex;align-items:center;justify-content:center;">
                            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#D53F8C" stroke-width="2"><circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/></svg>
                        </div>
                        <div>
                            <div style="font-size:.68rem;font-weight:700;color:#D53F8C;text-transform:uppercase;letter-spacing:.12em;">AI Business Insight</div>
                        </div>
                        <div style="margin-left:auto;display:flex;gap:6px;">
                            <span style="background:rgba(213,63,140,0.12);color:#D53F8C;border:1px solid rgba(213,63,140,0.2);border-radius:6px;padding:2px 8px;font-size:.62rem;font-weight:700;text-transform:uppercase;">McKinsey-level</span>
                        </div>
                    </div>
                    <div style="line-height:1.8;color:#CBD5E1;font-size:.9rem;">{_insight_html}</div>
                </div>""",
                    unsafe_allow_html=True,
                )

                st.session_state["export_df"] = result

        except Exception as e:
            st.error(f"Sorry, I couldn't process that question. Error: {str(e)}")
            st.info("Try rephrasing your question or click 'Clear' to reset context.")

    # ─────────────────────────────────────────────────────────────
    #  EXPORT PIPELINE
    # ─────────────────────────────────────────────────────────────
    if "export_df" in st.session_state:
        st.markdown(
            """<div style="margin:28px 0 14px;border-top:1px solid rgba(255,255,255,0.06);padding-top:22px;">
            <h3 style="font-family:'Outfit',sans-serif;font-size:1.1rem;font-weight:700;color:#E2E8F0;margin:0 0 4px;">💾 Export AI Dataset</h3>
            <p style="color:#475569;font-size:.8rem;margin:0;">Turn AI calculations into a permanent table for Power BI or your database.</p></div>""",
            unsafe_allow_html=True,
        )
        _ec1, _ec2 = st.columns(2)
        with _ec1:
            csv_data = st.session_state["export_df"].to_csv(index=False).encode("utf-8")
            st.download_button(
                label="📥 Download as CSV",
                data=csv_data,
                file_name="ai_copilot_export.csv",
                mime="text/csv",
                use_container_width=True,
            )
        with _ec2:
            if data_source_type == "Database Connection" and "db_engine" in st.session_state:
                with st.expander("🗄️ Save as New Table in Database"):
                    new_table = st.text_input("Table Name:", value="AI_Summary_Data")
                    if st.button("Write to Database", use_container_width=True, type="primary"):
                        try:
                            with st.spinner("Writing to database..."):
                                st.session_state["export_df"].to_sql(new_table, con=st.session_state["db_engine"], if_exists="replace", index=False)
                            st.success(f"Created '{new_table}' in your database!")
                        except Exception as e:
                            st.error(f"Database error: {e}")
            else:
                st.markdown(
                    '<div style="background:rgba(255,255,255,0.02);border:1px solid rgba(255,255,255,0.07);border-radius:12px;padding:14px 16px;"><p style="color:#475569;font-size:.8rem;margin:0;">Connect to SQL Server or MySQL in the sidebar to write results directly back to your database.</p></div>',
                    unsafe_allow_html=True,
                )