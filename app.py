import streamlit as st
import pandas as pd
import numpy as np
import re
import plotly.express as px
from openai import OpenAI
from PIL import Image
import os
import duckdb
from sqlalchemy import create_engine
import urllib.parse
import psutil
import pyodbc
import requests
from streamlit_lottie import st_lottie
import time
# import clr  # Lazy-loaded in Power BI section to avoid startup crash
import streamlit.components.v1 as components
import base64 # Added for video encoding
import sqlite3
import hashlib
import socket
import uuid as _uuid_mod
from datetime import datetime, timedelta

st.set_page_config(page_title="AI BI Copilot", layout="wide")

# Cloud detection (True if running on Streamlit Community Cloud)
IS_CLOUD = "STREAMLIT_SERVER_PORT" in os.environ

# ================= AUTH & SUBSCRIPTION SYSTEM =================
AUTH_DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'auth.db')

def _auth_conn():
    conn = sqlite3.connect(AUTH_DB_PATH)
    conn.execute("PRAGMA journal_mode=WAL")
    return conn

def _init_auth_db():
    conn = _auth_conn()
    conn.executescript('''
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
    ''')
    # Column migration
    try:
        conn.execute("ALTER TABLE users ADD COLUMN is_premium INTEGER DEFAULT 0")
    except: pass
    try:
        conn.execute("ALTER TABLE users ADD COLUMN trial_used INTEGER DEFAULT 0")
    except: pass
    try:
        conn.execute("ALTER TABLE users ADD COLUMN username TEXT UNIQUE")
    except: pass
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
        conn.execute("INSERT INTO users (username, email, password_hash, device_id) VALUES (?, ?, ?, ?)",
                     (username.strip(), email.lower().strip(), _hash_pw(password), _get_device_id()))
        conn.commit()
        return True, "Account created successfully! Please login."
    except sqlite3.IntegrityError:
        return False, "An account with this email already exists."
    finally:
        conn.close()

def _login(identifier, password):
    conn = _auth_conn()
    row = conn.execute("SELECT password_hash, device_id, email FROM users WHERE (email = ? OR username = ?)",
                       (identifier.lower().strip(), identifier.strip())).fetchone()
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
        return False, "⛔ This account is locked to another device. Single-device license only — sharing is not allowed."
    if not stored_device:
        conn.execute("UPDATE users SET device_id = ? WHERE email = ?", (this_device, actual_email))
        conn.commit()
    conn.close()
    return True, actual_email

def _check_sub(email):
    conn = _auth_conn()
    row = conn.execute("SELECT subscription_expiry, is_premium, trial_used FROM users WHERE email = ?", (email.lower().strip(),)).fetchone()
    conn.close()
    if not row or not row[0]:
        return False, None, 0, (row[2] if row else 0)
    try:
        expiry = datetime.strptime(row[0], "%Y-%m-%d")
    except:
        return False, None, 0, (row[2] if row else 0)
    is_premium = row[1]
    trial_used = row[2]
    if datetime.now() > expiry:
        return False, expiry, is_premium, trial_used
    return True, expiry, is_premium, trial_used

def _activate_trial(email):
    conn = _auth_conn()
    expiry_date = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")
    conn.execute("UPDATE users SET subscription_expiry = ?, trial_used = 1, is_premium = 0 WHERE email = ?", 
                 (expiry_date, email.lower().strip()))
    conn.commit()
    conn.close()
    return True, "1-Day Free Trial activated!"

def _activate_key(email, key):
    conn = _auth_conn()
    key_row = conn.execute("SELECT days, used_by FROM subscription_keys WHERE key = ?", (key.strip(),)).fetchone()
    if not key_row:
        conn.close()
        return False, "Invalid subscription key."
    if key_row[1]:
        conn.close()
        return False, "This key has already been used."
    days = key_row[0]
    user_row = conn.execute("SELECT subscription_expiry FROM users WHERE email = ?", (email.lower().strip(),)).fetchone()
    base_date = datetime.now()
    if user_row and user_row[0]:
        try:
            existing = datetime.strptime(user_row[0], "%Y-%m-%d")
            if existing > base_date:
                base_date = existing
        except:
            pass
    new_expiry = base_date + timedelta(days=days)
    expiry_str = new_expiry.strftime("%Y-%m-%d")
    conn.execute("UPDATE users SET subscription_expiry = ?, is_premium = 1 WHERE email = ?", (expiry_str, email.lower().strip()))
    conn.execute("UPDATE subscription_keys SET used_by = ?, used_at = ? WHERE key = ?",
                 (email.lower().strip(), datetime.now().strftime("%Y-%m-%d %H:%M:%S"), key.strip()))
    conn.commit()
    conn.close()
    return True, f"✅ Subscription activated until {new_expiry.strftime('%B %d, %Y')}!"

# Initialize auth database
_init_auth_db()

# Session defaults for auth
if 'authenticated' not in st.session_state:
    st.session_state.authenticated = False
if 'user_email' not in st.session_state:
    st.session_state.user_email = None
if 'sub_expiry' not in st.session_state:
    st.session_state.sub_expiry = None


# ================= VIDEO EMBED FUNCTION =================
@st.cache_data(show_spinner=False)
def get_base64_video(file_path):
    try:
        with open(file_path, "rb") as video_file:
            return base64.b64encode(video_file.read()).decode('utf-8')
    except Exception as e:
        return ""

# Read your specific video file (Ensure this is in the same folder as app.py)
video_base64 = get_base64_video("jayz.mp4")


def render_bubble():
    components.html(f"""
<style>
@keyframes bubbleRotate {{
    from {{ transform: rotate(0deg); }}
    to {{ transform: rotate(360deg); }}
}}
#bc {{
    animation: bubbleRotate 8s linear infinite;
    will-change: transform;
}}
</style>
<div style="display:flex; justify-content:center; margin-top:-20px; margin-bottom:10px; pointer-events:none;">
    <video id="bv1" muted playsinline style="display:none;"
           src="data:video/mp4;base64,{video_base64}"></video>
    <video id="bv2" muted playsinline style="display:none;"
           src="data:video/mp4;base64,{video_base64}"></video>
    <canvas id="bc" style="width:160px; height:auto;"></canvas>
</div>
<script>
const v1 = document.getElementById('bv1');
const v2 = document.getElementById('bv2');
const canvas = document.getElementById('bc');
const ctx = canvas.getContext('2d', {{ willReadFrequently: true }});
let ready = false;
let active = v1;
let frameCount = 0;
let cachedFrame = null;

function draw() {{
    requestAnimationFrame(draw);
    if (active.readyState < 2) return;
    if (!ready && active.videoWidth > 0) {{
        // 4K quality: use 4x multiplier for ultra-sharp rendering
        const scale = 4;
        canvas.width = 160 * scale;
        canvas.height = 160 * (active.videoHeight / active.videoWidth) * scale;
        ready = true;
    }}

    const other = (active === v1) ? v2 : v1;
    if (active.duration && active.currentTime >= active.duration - 0.25) {{
        other.currentTime = 0;
        other.play();
        active = other;
    }}

    frameCount++;
    // Only do expensive pixel manipulation every 3rd frame; reuse cached result otherwise
    if (frameCount % 3 === 0 || !cachedFrame) {{
        ctx.drawImage(active, 0, 0, canvas.width, canvas.height);
        const f = ctx.getImageData(0, 0, canvas.width, canvas.height);
        const d = f.data;
        const len = d.length;
        for (let i = 0; i < len; i += 4) {{
            const r = d[i], g = d[i+1], b = d[i+2];
            const mx = r > g ? (r > b ? r : b) : (g > b ? g : b);
            if (mx < 75) {{ 
                d[i+3] = 0; 
            }} else if (mx < 115) {{
                d[i+3] = (mx - 75) * 6.375;
            }}
        }}
        ctx.putImageData(f, 0, 0);
        cachedFrame = f;
    }} else {{
        ctx.putImageData(cachedFrame, 0, 0);
    }}
}}

v1.play().then(() => {{ requestAnimationFrame(draw); }}).catch(() => {{
    v1.addEventListener('canplay', () => {{ v1.play(); requestAnimationFrame(draw); }});
}});
</script>
""", height=200)

# ================= LOGIN / SIGNUP GATE =================
if not st.session_state.authenticated:
    st.markdown('<link href="https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;500;600;700;800&family=Inter:wght@300;400;500;600;700&display=swap" rel="stylesheet">', unsafe_allow_html=True)
    with open('style.css', 'r', encoding='utf-8') as f:
        st.markdown(f'<style>{f.read()}</style>', unsafe_allow_html=True)

    render_bubble()
    st.markdown("""
    <div style="text-align: center; padding: 40px 0 20px 0;">
        <div style="font-family: 'Outfit', sans-serif; font-size: 2.8rem; font-weight: 800;">
            <span style="color: #FF4B91 !important;">AI </span><span>BI Copilot</span>
        </div>
        
    </div>
    """, unsafe_allow_html=True)

    _auth_col1, _auth_col2, _auth_col3 = st.columns([1, 2, 1])
    with _auth_col2:
        auth_mode = st.radio("", ["Login", "Sign Up"], horizontal=True, label_visibility="collapsed")

        if auth_mode == "Login":
            with st.form("login_form"):
                login_id = st.text_input("Username or Email", placeholder="e.g. user123 or you@example.com")
                login_password = st.text_input("Password", type="password", placeholder="Enter your password")
                login_btn = st.form_submit_button("Login", type="primary", use_container_width=True)
                if login_btn:
                    if not login_id or not login_password:
                        st.error("Please fill in all fields.")
                    else:
                        ok, res = _login(login_id, login_password)
                        if ok:
                            st.session_state.authenticated = True
                            st.session_state.user_email = res
                            st.rerun()
                        else:
                            st.error(res)
        else:
            with st.form("signup_form"):
                reg_username = st.text_input("Username", placeholder="e.g. user123")
                reg_email = st.text_input("Email", placeholder="you@example.com")
                reg_password = st.text_input("Password", type="password", placeholder="Min 6 characters")
                reg_confirm = st.text_input("Confirm Password", type="password", placeholder="Re-enter password")
                reg_btn = st.form_submit_button("Create Account", type="primary", use_container_width=True)
                if reg_btn:
                    if not reg_username or not reg_email or not reg_password:
                        st.error("Please fill in all fields.")
                    elif len(reg_password) < 6:
                        st.error("Password must be at least 6 characters.")
                    elif reg_password != reg_confirm:
                        st.error("Passwords do not match.")
                    else:
                        ok, msg = _register(reg_username, reg_email, reg_password)
                        if ok:
                            st.session_state.authenticated = True
                            st.session_state.user_email = reg_email.lower().strip()
                            st.success("Account created successfully! Welcome to your trial session.")
                            time.sleep(1.5)
                            st.rerun()
                        else:
                            st.error(msg)

    st.stop()

# ================= SUBSCRIPTION CHECK =================
_sub_active, _sub_expiry, _is_premium, _trial_used = _check_sub(st.session_state.user_email)
st.session_state.sub_expiry = _sub_expiry

if not _sub_active:
    st.markdown('<link href="https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;500;600;700;800&family=Inter:wght@300;400;500;600;700&display=swap" rel="stylesheet">', unsafe_allow_html=True)
    with open('style.css', 'r', encoding='utf-8') as f:
        st.markdown(f'<style>{f.read()}</style>', unsafe_allow_html=True)

    render_bubble()
    
    _user_email = st.session_state.user_email
    _stripe_email = urllib.parse.quote(_user_email)

    st.markdown(f"""
    <div style="text-align: center; padding: 20px 0 30px 0;">
        <div style="font-family: 'Outfit', sans-serif; font-size: 2.8rem; font-weight: 800;">
            <span style="color: #FF4B91 !important;">AI </span><span>BI Copilot</span>
        </div>
        <div style="margin-top: 10px; padding: 6px 16px; background: rgba(193, 74, 138, 0.1); border-radius: 20px; display: inline-block;">
            <span style="font-family: 'Inter', sans-serif; font-size: 0.85rem; color: #FF4B91; font-weight: 600;">
                \U0001f4cb Subscription Status: INACTIVE
            </span>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # Choice Section: Trial vs Premium
    _c1, _c2 = st.columns(2)
    
    with _c1:
        if not _trial_used:
            st.markdown("""
            <div style="background: rgba(255,255,255,0.03); border: 1px solid rgba(255,255,255,0.1); border-radius: 20px; padding: 25px; height: 180px; text-align: center; display: flex; flex-direction: column; justify-content: center;">
                <h3 style="margin: 0; font-family: 'Outfit', sans-serif; font-size: 1.4rem;">🎁 Free Trial</h3>
                <p style="font-size: 0.85rem; opacity: 0.7; margin: 10px 0;">Get full access for 24 hours to explore all AI insights.</p>
            </div>
            """, unsafe_allow_html=True)
            if st.button("Activate 1-Day Trial", use_container_width=True):
                _activate_trial(_user_email)
                st.success("Trial activated! Welcome aboard.")
                time.sleep(1.5)
                st.rerun()
        else:
            st.markdown("""
            <div style="background: rgba(255,255,255,0.01); border: 1px dashed rgba(255,255,255,0.1); border-radius: 20px; padding: 25px; height: 180px; text-align: center; display: flex; flex-direction: column; justify-content: center; opacity: 0.6;">
                <h3 style="margin: 0; font-family: 'Outfit', sans-serif; font-size: 1.4rem;">🎁 Trial Applied</h3>
                <p style="font-size: 0.85rem; margin: 10px 0;">You have already used your 1-day free trial on this account.</p>
            </div>
            """, unsafe_allow_html=True)

    with _c2:
        st.markdown("""
        <div style="background: rgba(193, 74, 138, 0.05); border: 1px solid #C14A8A; border-radius: 20px; padding: 25px; height: 180px; text-align: center; display: flex; flex-direction: column; justify-content: center;">
            <h3 style="margin: 0; font-family: 'Outfit', sans-serif; color: #C14A8A; font-size: 1.4rem;">💎 Get Premium</h3>
            <p style="font-size: 0.85rem; opacity: 0.8; margin: 10px 0;">Select a plan below to unlock unlimited AI power forever.</p>
        </div>
        """, unsafe_allow_html=True)
        st.markdown(f"<div style='text-align: center; font-size: 0.75rem; opacity: 0.5; margin-top: 8px;'>Keys are sent to: <b>{_user_email}</b></div>", unsafe_allow_html=True)

    st.divider()

    # Plan Cards
    st.markdown('<h3 style="text-align: center; font-family: \'Outfit\', sans-serif; margin-bottom: 25px;">Select Your Plan</h3>', unsafe_allow_html=True)
    _p1, _p2, _p3 = st.columns(3)
    
    with _p1:
        st.markdown(f"""
        <div style="padding: 20px; border: 1px solid rgba(255,255,255,0.1); border-radius: 16px; background: rgba(0,0,0,0.2); text-align: center; min-height: 200px; display: flex; flex-direction: column; justify-content: space-between;">
            <div>
                <div style="font-weight: 700; opacity: 0.7;">Monthly</div>
                <div style="font-size: 1.8rem; font-weight: 800; margin: 10px 0;">$5<span style="font-size: 0.9rem; font-weight: 400;">/mo</span></div>
            </div>
            <a href="https://buy.stripe.com/test_monthly?prefilled_email={_stripe_email}" target="_blank" style="display: block; padding: 10px; background: rgba(255,255,255,0.05); border: 1px solid rgba(255,255,255,0.1); border-radius: 8px; color: white; text-decoration: none; font-weight: bold; font-size: 0.85rem;">Buy Monthly</a>
        </div>
        """, unsafe_allow_html=True)

    with _p2:
        st.markdown(f"""
        <div style="padding: 20px; border: 1px solid #C14A8A; border-radius: 16px; background: rgba(193, 74, 138, 0.08); text-align: center; min-height: 200px; position: relative; display: flex; flex-direction: column; justify-content: space-between;">
            <div style="position: absolute; top: -10px; left: 50%; transform: translateX(-50%); background: #C14A8A; color: white; font-size: 0.65rem; padding: 2px 10px; border-radius: 10px; font-weight: bold;">BEST VALUE</div>
            <div>
                <div style="font-weight: 700; color: #fff;">Quarterly</div>
                <div style="font-size: 1.8rem; font-weight: 800; margin: 10px 0; color: #C14A8A;">$29<span style="font-size: 0.9rem; font-weight: 400; color: #fff;">/qtr</span></div>
            </div>
            <a href="https://buy.stripe.com/test_quarterly?prefilled_email={_stripe_email}" target="_blank" style="display: block; padding: 10px; background: #C14A8A; border-radius: 8px; color: white; text-decoration: none; font-weight: bold; font-size: 0.85rem;">Buy Quarterly</a>
        </div>
        """, unsafe_allow_html=True)

    with _p3:
        st.markdown(f"""
        <div style="padding: 20px; border: 1px solid rgba(255,255,255,0.1); border-radius: 16px; background: rgba(0,0,0,0.2); text-align: center; min-height: 200px; display: flex; flex-direction: column; justify-content: space-between;">
            <div>
                <div style="font-weight: 700; opacity: 0.7;">Yearly</div>
                <div style="font-size: 1.8rem; font-weight: 800; margin: 10px 0;">$59<span style="font-size: 0.9rem; font-weight: 400;">/yr</span></div>
            </div>
            <a href="https://buy.stripe.com/test_yearly?prefilled_email={_stripe_email}" target="_blank" style="display: block; padding: 10px; background: rgba(255,255,255,0.05); border: 1px solid rgba(255,255,255,0.1); border-radius: 8px; color: white; text-decoration: none; font-weight: bold; font-size: 0.85rem;">Buy Yearly</a>
        </div>
        """, unsafe_allow_html=True)

    st.markdown(f"""
    <div style="margin-top: 30px; padding: 20px; border-radius: 16px; background: rgba(255,255,255,0.02); border: 1px solid rgba(255,255,255,0.1); text-align: center;">
        <div style="font-size: 0.9rem; color: rgba(255,255,255,0.7); line-height: 1.6;">
            🚀 <b>Immediate Access:</b> Upon successful purchase, your unique activation key will be sent instantly to:<br>
            <span style="color: #C14A8A; font-weight: 700; font-size: 1.1rem;">{_user_email}</span>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # Final Activation Section (Bottom)
    st.markdown('<div style="margin-top: 60px; text-align: center; opacity: 0.5;">Already have a key?</div>', unsafe_allow_html=True)
    with st.form("sub_form"):
        sub_key = st.text_input("Enter Activation Key", placeholder="XXXX-XXXX-XXXX-XXXX")
        sub_btn = st.form_submit_button("UNLOCKED ACCESS", type="primary", use_container_width=True)
        if sub_btn:
            if not sub_key:
                st.error("Please enter your subscription key.")
            else:
                ok, msg = _activate_key(_user_email, sub_key)
                if ok:
                    st.success(msg)
                    time.sleep(1.5)
                    st.rerun()
                else:
                    st.error(msg)

    if st.button("Logout", use_container_width=True):
        st.session_state.authenticated = False
        st.session_state.user_email = None
        st.rerun()

    st.stop()

client = OpenAI(
    base_url="https://integrate.api.nvidia.com/v1",
    api_key="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"
)

# ================= UI: ELYSIUM AI STYLE — PREMIUM EDITION =================
st.markdown('<link href="https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;500;600;700;800&family=Inter:wght@300;400;500;600;700&display=swap" rel="stylesheet">', unsafe_allow_html=True)

# Mouse Follower Script
components.html("""
<script>
const doc = window.parent.document;
if (!doc.getElementById('ag-cursor-sprinkles')) {
    const container = doc.createElement('div');
    container.id = 'ag-cursor-sprinkles';
    container.style.position = 'fixed';
    container.style.top = '0';
    container.style.left = '0';
    container.style.width = '100vw';
    container.style.height = '100vh';
    container.style.pointerEvents = 'none';
    container.style.zIndex = '9999';
    doc.body.appendChild(container);
    
    // Antigravity style colors (blues, pinks, purples)
    const colors = ['#3b82f6', '#8b5cf6', '#ec4899', '#06b6d4'];
    
    doc.addEventListener('mousemove', (e) => {
        if (Math.random() > 0.85) return; // spawn most of the time for dense real-time feel
        
        const sprinkle = doc.createElement('div');
        sprinkle.style.position = 'absolute';
        sprinkle.style.left = e.clientX + 'px';
        sprinkle.style.top = e.clientY + 'px';
        
        // Random sprinkle shape (dashes)
        sprinkle.style.width = (Math.random() * 3 + 2) + 'px'; 
        sprinkle.style.height = (Math.random() * 8 + 4) + 'px'; 
        sprinkle.style.background = colors[Math.floor(Math.random() * colors.length)];
        sprinkle.style.borderRadius = '5px';
        
        const initAngle = Math.random() * 360;
        sprinkle.style.transform = `translate(-50%, -50%) rotate(${initAngle}deg)`;
        sprinkle.style.transition = 'all 0.7s cubic-bezier(0.25, 0.46, 0.45, 0.94)';
        sprinkle.style.opacity = '1';
        
        container.appendChild(sprinkle);
        
        // Execute the visual scatter burst
        requestAnimationFrame(() => {
            const flyX = e.clientX + (Math.random() - 0.5) * 100;
            const flyY = e.clientY + (Math.random() - 0.5) * 100;
            const finalAngle = initAngle + (Math.random() > 0.5 ? 90 : -90);
            
            sprinkle.style.left = flyX + 'px';
            sprinkle.style.top = flyY + 'px';
            sprinkle.style.opacity = '0';
            sprinkle.style.transform = `translate(-50%, -50%) rotate(${finalAngle}deg) scale(0)`;
        });
        
        setTimeout(() => { sprinkle.remove(); }, 750);
    });
}
</script>
""", height=0, width=0)

# Load external CSS
with open('style.css', 'r', encoding='utf-8') as f:
    st.markdown(f'<style>{f.read()}</style>', unsafe_allow_html=True)


# Native Flow Flex Header (With MP4 Video)
st.markdown('''
<div class="hero-header-section">
    <div class="main-title">
        <span style="color: #FF4B91 !important;">AI </span><span class="title-dark">BI Copilot</span>
    </div>
</div>
''', unsafe_allow_html=True)

render_bubble()

# ================= SIDEBAR: ACCOUNT INFO =================
_sub_active, _sub_expiry, _is_premium, _trial_used = _check_sub(st.session_state.user_email)
_status_label = "💎 Premium Subscriber" if _is_premium else "Free User"
_display_expiry = _sub_expiry.strftime('%b %d, %Y') if _sub_expiry else 'N/A'
st.sidebar.markdown(f"""
<div style="padding: 10px 0 14px 0; border-bottom: 1px solid rgba(255,255,255,0.2); margin-bottom: 12px;">
    <div style="font-size: 0.75rem; opacity: 0.6;">Logged in as</div>
    <div style="font-weight: 700; font-size: 0.9rem; margin-top: 2px;">{st.session_state.user_email}</div>
    <div style="font-size: 0.82rem; margin-top: 6px; font-weight: 600; color: {'#C14A8A' if _is_premium else '#ffffff'};">{_status_label}</div>
    <div style="font-size: 0.72rem; margin-top: 4px; opacity: 0.8;">Subscription until: {_display_expiry}</div>
</div>
""", unsafe_allow_html=True)

if st.sidebar.button("Logout", use_container_width=True):
    st.session_state.authenticated = False
    st.session_state.user_email = None
    st.rerun()

# ================= SIDEBAR UPLOADER & DB CONNECTION =================
st.sidebar.header("Data Source")

if 'data_source_type' not in st.session_state:
    st.session_state.data_source_type = "CSV Upload"

def set_data_source(src):
    if st.session_state.get('data_source_type') != src:
        if 'db_df' in st.session_state:
            del st.session_state['db_df']
    st.session_state.data_source_type = src

st.sidebar.button("CSV", 
                  type="primary" if st.session_state.data_source_type == "CSV Upload" else "secondary",
                  on_click=set_data_source, args=("CSV Upload",),
                  use_container_width=True)

st.sidebar.button("Database", 
                  type="primary" if st.session_state.data_source_type == "Database Connection" else "secondary",
                  on_click=set_data_source, args=("Database Connection",),
                  use_container_width=True)

st.sidebar.button("Power BI", 
                  type="primary" if st.session_state.data_source_type == "Live Power BI" else "secondary",
                  on_click=set_data_source, args=("Live Power BI",),
                  use_container_width=True)

data_source_type = st.session_state.data_source_type
st.sidebar.caption(f"Currently Active: **{data_source_type}**")

uploaded_files = None
db_connection_error = None

if data_source_type == "CSV Upload":
    uploaded_files = st.sidebar.file_uploader("Upload CSV or Excel files", type=['csv', 'xlsx', 'xls'], accept_multiple_files=True)

elif data_source_type == "Database Connection":
    st.sidebar.subheader("Database Credentials")
    db_type = st.sidebar.selectbox("Database Type", ["SQL Server", "MySQL"])
    db_host = st.sidebar.text_input("Host (e.g., localhost)")
    db_port = st.sidebar.text_input("Port (e.g., 1433 or 3306)")
    db_user = st.sidebar.text_input("Username")
    db_pass = st.sidebar.text_input("Password", type="password")
    db_name = st.sidebar.text_input("Database Name")
    db_table = st.sidebar.text_input("Table Name")
    
    if st.sidebar.button("Connect & Load Data", type="primary"):
        if not all([db_host, db_user, db_name, db_table]):
            st.sidebar.error("Please fill in all required fields.")
        else:
            try:
                safe_pass = urllib.parse.quote_plus(db_pass) if db_pass else ""
                credentials = f"{db_user}:{safe_pass}" if safe_pass else f"{db_user}"
                
                if db_type == "MySQL":
                    port = db_port if db_port else "3306"
                    engine = create_engine(f"mysql+pymysql://{credentials}@{db_host}:{port}/{db_name}")
                else:
                    port = db_port if db_port else "1433"
                    # In cloud use FreeTDS (from packages.txt), locally use the official MS driver
                    driver_name = "FreeTDS" if IS_CLOUD else "ODBC+Driver+17+for+SQL+Server"
                    engine = create_engine(f"mssql+pyodbc://{credentials}@{db_host}:{port}/{db_name}?driver={driver_name}")
                
                count_query = f"SELECT COUNT(*) FROM {db_table}"
                total_rows = pd.read_sql(count_query, engine).iloc[0, 0]
                
                loading_container = st.sidebar.empty()
                progress_bar = loading_container.progress(0, text="Connecting to Database... 0%")
                
                query = f"SELECT * FROM {db_table}"
                chunk_size = max(1000, total_rows // 100) if total_rows > 0 else 1000
                chunks = []
                rows_fetched = 0
                
                for chunk in pd.read_sql(query, engine, chunksize=chunk_size):
                    chunks.append(chunk)
                    rows_fetched += len(chunk)
                    pct = min(int((rows_fetched / total_rows) * 100), 100) if total_rows > 0 else 100
                    progress_bar.progress(pct, text=f"Fetching data... {pct}% ({rows_fetched:,}/{total_rows:,} rows)")
                
                db_df = pd.concat(chunks, ignore_index=True) if chunks else pd.DataFrame()
                
                progress_bar.progress(100, text="Database loaded successfully! 100%")
                time.sleep(0.5)
                loading_container.empty()
                
                st.session_state['db_df'] = db_df
                st.session_state['db_engine'] = engine
                st.sidebar.success(f"Successfully loaded {len(db_df):,} rows from {db_table}!")
            except Exception as e:
                db_connection_error = str(e)
                st.sidebar.error(f"Error: {db_connection_error}")

elif data_source_type == "Live Power BI":
    st.sidebar.subheader("Live Power BI Scanner")
    st.sidebar.caption("Scans your computer for an open Power BI file and connects to its hidden data engine.")
    
    if st.sidebar.button("🔍 Scan for Open Power BI", use_container_width=True):
        with st.spinner("Scanning local ports for msmdsrv.exe..."):
            found_port = None
            try:
                for proc in psutil.process_iter(['name', 'pid']):
                    if proc.info['name'] and 'msmdsrv.exe' in proc.info['name'].lower():
                        for conn in proc.connections(kind='tcp'):
                            if conn.status == 'LISTEN':
                                found_port = conn.laddr.port
                                st.session_state['pbi_port'] = found_port
                                break
            except Exception as e:
                st.sidebar.error(f"Scanner error: {e}")
            
            if found_port:
                st.sidebar.markdown(f'<div style="background-color: #d4edda; border: 1px solid #c3e6cb; padding: 15px; border-radius: 18px; color: #155724; font-family: Inter, sans-serif; box-shadow: 0 4px 15px rgba(0,0,0,0.05); margin-bottom: 1rem;">✅ Found Power BI running on Port: {found_port}</div>', unsafe_allow_html=True)
            else:
                st.sidebar.markdown('<div style="background-color: #fff3cd; border: 1px solid #ffeeba; padding: 15px; border-radius: 18px; color: #856404; font-family: Inter, sans-serif; box-shadow: 0 4px 15px rgba(0,0,0,0.05); margin-bottom: 1rem;">⚠️ No active Power BI Desktop file found. Please make sure Power BI Desktop is open on this computer.</div>', unsafe_allow_html=True)

    if 'pbi_port' in st.session_state and st.session_state['pbi_port']:
        pbi_table = st.sidebar.text_input("Exact Table Name inside Power BI:")
        
        if st.sidebar.button("Extract Data", type="primary", use_container_width=True):
            if not pbi_table:
                st.sidebar.warning("Please enter the name of the table you want to extract.")
            else:
                try:
                    port = st.session_state['pbi_port']
                    current_dir = os.path.dirname(os.path.abspath(__file__))
                    dll_path = os.path.join(current_dir, "Microsoft.AnalysisServices.AdomdClient.dll")
                    
                    if not os.path.exists(dll_path):
                        raise Exception("Could not find 'Microsoft.AnalysisServices.AdomdClient.dll' in your app's folder. Please paste it directly next to your app.py file.")
                        
                    import clr  # Lazy import to avoid startup crash
                    clr.AddReference(dll_path)
                    import Microsoft.AnalysisServices.AdomdClient as adomd
                    
                    conn_str = f"Data Source=localhost:{port}"
                    conn = adomd.AdomdConnection(conn_str)
                    conn.Open()
                    
                    loading_container = st.sidebar.empty()
                    progress_bar = loading_container.progress(0, text="Initializing Power BI Connection... 0%")
                    
                    try:
                        count_cmd = conn.CreateCommand()
                        count_cmd.CommandText = f"EVALUATE ROW(\"Count\", COUNTROWS('{pbi_table}'))"
                        count_reader = count_cmd.ExecuteReader()
                        total_rows = 1000
                        if count_reader.Read():
                            total_rows = int(count_reader.GetValue(0))
                        count_reader.Close()
                    except:
                        total_rows = 50000 
                    
                    cmd = conn.CreateCommand()
                    cmd.CommandText = f"EVALUATE '{pbi_table}'"
                    reader = cmd.ExecuteReader()
                    
                    cols = [reader.GetName(i) for i in range(reader.FieldCount)]
                    data = []
                    row_count = 0
                    
                    while reader.Read():
                        data.append([reader.GetValue(i) for i in range(reader.FieldCount)])
                        row_count += 1
                        if row_count % max(100, total_rows // 100) == 0:
                            pct = min(int((row_count / total_rows) * 100), 100) if total_rows > 0 else 50
                            progress_bar.progress(pct, text=f"Extracting data... {pct}% ({row_count:,} rows)")
                            
                    progress_bar.progress(100, text="Extraction complete! Finalizing data format... 100%")
                    time.sleep(0.5)
                    
                    reader.Close()
                    conn.Close()
                    
                    db_df = pd.DataFrame(data, columns=cols)
                    db_df.columns = [col.split('[')[-1].replace(']', '') if '[' in col else col for col in db_df.columns]
                    
                    loading_container.empty()
                    st.session_state['db_df'] = db_df
                    st.sidebar.success(f"Successfully pulled {len(db_df):,} rows from Power BI!")
                except Exception as e:
                    db_connection_error = str(e)
                    st.sidebar.error("Connection failed.")
                    st.sidebar.error(f"Error Details: {db_connection_error}")

# ================= MULTI-TAB ARCHITECTURE =================
data_container = st.container()

with data_container:
    # ================= LOAD DATA WITH GUARANTEED PROGRESS BAR =================
    try:
        if data_source_type in ["Database Connection", "Live Power BI"] and 'db_df' in st.session_state:
            df = st.session_state['db_df'].copy()
            
        elif data_source_type == "CSV Upload" and uploaded_files is not None and len(uploaded_files) > 0:
            
            loading_container = st.empty()
            progress_bar = loading_container.progress(0, text="Initializing File Reader... 0%")
            
            all_dfs = []
            total_files = len(uploaded_files)
            
            for file_idx, uploaded_file in enumerate(uploaded_files):
                file_name = uploaded_file.name
                file_ext = os.path.splitext(file_name)[1].lower()
                base_pct = int((file_idx / total_files) * 100)
                file_pct_range = int(100 / total_files)
                
                progress_bar.progress(min(base_pct, 99), text=f"Reading file {file_idx + 1}/{total_files}: {file_name}... {base_pct}%")
                
                if file_ext in ['.xlsx', '.xls']:
                    uploaded_file.seek(0)
                    file_df = pd.read_excel(uploaded_file, engine='openpyxl' if file_ext == '.xlsx' else 'xlrd')
                    all_dfs.append(file_df)
                    done_pct = min(base_pct + file_pct_range, 100)
                    progress_bar.progress(min(done_pct, 99), text=f"Loaded Excel: {file_name} ({len(file_df):,} rows)... {done_pct}%")
                else:
                    uploaded_file.seek(0)
                    total_lines = sum(1 for _ in uploaded_file) - 1
                    uploaded_file.seek(0)
                    
                    if total_lines > 0:
                        chunk_size = max(100, total_lines // 20)
                        chunks = []
                        rows_read = 0
                        
                        for chunk in pd.read_csv(uploaded_file, encoding="latin1", chunksize=chunk_size):
                            chunks.append(chunk)
                            rows_read += len(chunk)
                            inner_pct = min(int((rows_read / total_lines) * file_pct_range), file_pct_range)
                            progress_bar.progress(min(base_pct + inner_pct, 99), text=f"Reading CSV {file_idx + 1}/{total_files}: {file_name}... {base_pct + inner_pct}% ({rows_read:,}/{total_lines:,} rows)")
                        
                        file_df = pd.concat(chunks, ignore_index=True) if chunks else pd.DataFrame()
                    else:
                        file_df = pd.read_csv(uploaded_file, encoding="latin1")
                    all_dfs.append(file_df)
            
            df = pd.concat(all_dfs, ignore_index=True) if all_dfs else pd.DataFrame()
            
            progress_bar.progress(100, text=f"All {total_files} file(s) loaded successfully! ({len(df):,} total rows) 100%")
            time.sleep(0.5) 
            loading_container.empty() 
            
        else:
            if db_connection_error:
                st.error(f"Connection failed: {db_connection_error}")
            else:
                st.warning("⚠️ No data found. Please upload CSV or Excel files, connect to a database, or connect to Live Power BI in the sidebar to get started.")
            st.stop()
    except Exception as e:
        st.error(f"Error loading data: {e}")
        st.stop()

    # --- TRUE-SYNC DATA PREPARATION BAR ---
    data_prep_container = st.empty()
    
    # Determine the label based on the source
    source_label = "CSV" if data_source_type == "CSV Upload" else "Database" if data_source_type == "Database Connection" else "Power BI"
    
    data_prep_bar = data_prep_container.progress(5, text=f"Processing {source_label} Data: Cleaning column names... 5%")

    # BULLETPROOF COLUMN CLEANING FOR DUCKDB
    df.columns = df.columns.str.lower().str.replace(r'[^a-z0-9_]', '_', regex=True).str.strip('_')

    # ================= NUMERIC DETECTION =================
    data_prep_bar.progress(25, text=f"Processing {source_label} Data: Detecting numeric formats... 25%")
    numeric_cols=[]
    for col in df.columns:
        cleaned=df[col].astype(str).str.replace(r"[₹$,]","",regex=True)
        converted=pd.to_numeric(cleaned,errors="coerce")
        if converted.notna().sum()>0.4*len(df):
            df[col]=converted
            numeric_cols.append(col)

    # ================= DATE DETECTION =================
    data_prep_bar.progress(60, text=f"Processing {source_label} Data: Parsing dates and times (this may take a moment)... 60%")
    date_cols=[]
    for col in df.columns:
        if col in numeric_cols: continue
        try:
            converted = pd.to_datetime(df[col].astype(str), errors='coerce', utc=True)
            if converted.notna().sum() > 0.4 * len(df[col].dropna()) and len(df[col].dropna()) > 0:
                date_cols.append(col)
                df[col] = converted
        except: 
            pass

    data_prep_bar.progress(85, text=f"Processing {source_label} Data: Categorizing metrics... 85%")
    dimension_cols=[c for c in df.columns if c not in numeric_cols and c not in date_cols]

    business_keywords=["sales","revenue","profit","margin","amount","income","quantity","cost","price", "delay", "duration", "charging", "kw"]
    business_metrics=[c for c in numeric_cols if any(k in c for k in business_keywords)]
    if not business_metrics and numeric_cols:
        business_metrics=numeric_cols

    if not numeric_cols:
        st.error("⚠️ No numeric columns detected in this dataset. I need at least one metric to aggregate.")
        st.stop()

    # --- SORT BUSINESS METRICS BY PRIORITY ---
    priority_keywords = ["sales", "revenue", "profit", "margin", "amount", "quantity", "price", "income", "cost"]
    
    def get_priority(col_name):
        lower_col = col_name.lower()
        for i, pk in enumerate(priority_keywords):
            if pk in lower_col:
                return i
        return 999

    business_metrics.sort(key=get_priority)
    main_metric = business_metrics[0] if business_metrics else numeric_cols[0]
    
    data_prep_bar.progress(100, text=f"Processing {source_label} Data: Complete! 100%")
    time.sleep(0.3)
    data_prep_container.empty()

    # ================= TABS =================
    tab_copilot, tab_dashboard = st.tabs(["🧠 AI Copilot & Insights", "📊 Executive Dashboard"])

    def render_kpis():
        # ================= KPI =================
        kpi_cols=st.columns(min(4,max(1, len(business_metrics))))
        for i,col in enumerate(business_metrics[:4]):
            with kpi_cols[i]:
                money_keywords = ['sales', 'price', 'revenue', 'amount', 'profit', 'margin', 'cost']
                is_money = any(keyword in col.lower() for keyword in money_keywords)
                
                display_label = col.replace('_', ' ').strip().title() if len(col) > 4 else col.upper()
                
                if is_money:
                    kpi_value = f"${df[col].sum():,.2f}"
                else:
                    kpi_value = f"{df[col].sum():,.0f}"
                
                st.markdown(f"""
                <div style="padding: 8px 0;">
                    <div style="font-size: 0.85rem; color: rgba(255,255,255,0.6); margin-bottom: 4px;">Total {display_label}</div>
                    <div style="font-size: 1.6rem; font-weight: 700; color: #ffffff; word-break: break-all;">{kpi_value}</div>
                </div>
                """, unsafe_allow_html=True)

        st.markdown("<hr style='margin: 10px 0; border: none; border-top: 1px solid rgba(255,154,158,0.2);'>", unsafe_allow_html=True)

    with tab_dashboard:
        render_kpis()
        
        # Auto-generate Charts (2-col grid for 10 Insights)
        st.subheader("Automated Analytics Dashboard (10 Smart Views)")
        
        def _apply_theme(f):
            if f:
                f.update_layout(plot_bgcolor='#0a0c14', paper_bgcolor='#0a0c14', 
                                font=dict(color='#f0f2f5', family='Inter, sans-serif'), 
                                title_font=dict(size=14, color='#f0f2f5', family='Outfit, sans-serif'), 
                                xaxis=dict(gridcolor='rgba(255,255,255,0.05)', zerolinecolor='rgba(255,255,255,0.08)'), 
                                yaxis=dict(gridcolor='rgba(255,255,255,0.05)', zerolinecolor='rgba(255,255,255,0.08)'), 
                                margin=dict(l=20, r=20, t=50, b=20))
            return f

        dash_c1, dash_c2 = st.columns(2)
        
        # Defining maximally diverse fields to prevent redundant charts
        d1 = dimension_cols[0] if len(dimension_cols) > 0 else None
        d2 = dimension_cols[1] if len(dimension_cols) > 1 else d1
        d3 = dimension_cols[2] if len(dimension_cols) > 2 else d2
        d4 = dimension_cols[3] if len(dimension_cols) > 3 else d1
        m1 = numeric_cols[0] if len(numeric_cols) > 0 else main_metric
        m2 = numeric_cols[1] if len(numeric_cols) > 1 else m1
        m3 = numeric_cols[2] if len(numeric_cols) > 2 else m1
        m4 = numeric_cols[3] if len(numeric_cols) > 3 else m2
        dt = date_cols[0] if len(date_cols) > 0 else None

        with dash_c1:
            # 1. Trend or Top Pie (Uses dt/d1 and m1)
            try:
                if dt:
                    tmp = df.groupby(dt)[m1].sum().reset_index()
                    fig = _apply_theme(px.area(tmp, x=dt, y=m1, title=f"1. Trend of {m1.title()}"))
                elif d1:
                    tmp = df.groupby(d1)[m1].sum().reset_index().nlargest(10, m1)
                    fig = _apply_theme(px.pie(tmp, names=d1, values=m1, hole=0.4, title=f"1. Top {d1.title()} by {m1.title()}"))
                else:
                    fig = _apply_theme(px.line(df, y=m1, title=f"1. Sequence of {m1.title()}"))
                if fig: st.plotly_chart(fig, use_container_width=True)
            except: pass

            # 3. Bottom Performers (Uses d3 and m3)
            try:
                if d3:
                    tmp = df.groupby(d3)[m3].sum().reset_index().nsmallest(10, m3)
                    fig = px.bar(tmp, x=m3, y=d3, orientation='h', title=f"3. Bottom {d3.title()} on {m3.title()}")
                    fig.update_traces(marker_color='#ff4b4b')
                    fig = _apply_theme(fig)
                    st.plotly_chart(fig, use_container_width=True)
            except: pass

            # 5. Box Plot / Variance (Uses d4 and m2)
            try:
                if d4:
                    tmp = df.nlargest(1000, m2)
                    fig = _apply_theme(px.box(tmp, x=d4, y=m2, color=d4, title=f"5. Variance of {m2.title()} over {d4.title()}"))
                    st.plotly_chart(fig, use_container_width=True)
            except: pass

            # 7. Distribution Histogram (Uses m4)
            try:
                fig = _apply_theme(px.histogram(df.sample(min(5000, len(df))), x=m4, nbins=30, title=f"7. Distribution of {m4.title()}"))
                st.plotly_chart(fig, use_container_width=True)
            except: pass

            # 9. Funnel Chart (Uses d2 and m1)
            try:
                if d2:
                    tmp = df.groupby(d2)[m1].sum().reset_index().nlargest(6, m1)
                    fig = _apply_theme(px.funnel(tmp, x=m1, y=d2, title=f"9. {m1.title()} Pipeline across {d2.title()}"))
                    st.plotly_chart(fig, use_container_width=True)
            except: pass

        with dash_c2:
            # 2. Top Performers (Uses d2 and m2)
            try:
                if d2:
                    tmp = df.groupby(d2)[m2].sum().reset_index().nlargest(10, m2)
                    fig = px.bar(tmp, x=d2, y=m2, text_auto='.2s', title=f"2. Top 10 {d2.title()} on {m2.title()}")
                    fig = _apply_theme(fig)
                    st.plotly_chart(fig, use_container_width=True)
            except: pass

            # 4. Correlation / Scatter (Uses m1 and m3)
            try:
                if len(numeric_cols) > 1:
                    fig = px.scatter(df.sample(min(2000, len(df))), x=m1, y=m3, color=d1, title=f"4. Correlation: {m1.title()} vs {m3.title()}")
                    fig = _apply_theme(fig)
                    st.plotly_chart(fig, use_container_width=True)
            except: pass

            # 6. Treemap (Hierarchy) (Uses d1, d3, values=m4)
            try:
                if len(dimension_cols) > 1 and len(df) > 0:
                    tmp = df.groupby([d1, d3])[m4].sum().reset_index()
                    tmp = tmp[tmp[m4] > 0]
                    tmp = tmp.nlargest(20, m4)
                    if len(tmp) > 0:
                        fig = _apply_theme(px.treemap(tmp, path=[d1, d3], values=m4, title=f"6. Hierarchy: {d1.title()} → {d3.title()} on {m4.title()}"))
                        st.plotly_chart(fig, use_container_width=True)
            except: pass

            # 8. Donut Chart (Uses d4 and m2)
            try:
                if d4 and d4 != d1:
                    tmp = df.groupby(d4)[m2].sum().reset_index().nlargest(8, m2)
                    fig = _apply_theme(px.pie(tmp, names=d4, values=m2, hole=0.5, title=f"8. Market Segment: {d4.title()} ({m2.title()})"))
                    st.plotly_chart(fig, use_container_width=True)
                elif len(numeric_cols) > 1:
                    tmp = df.nlargest(100, m2)
                    fig = _apply_theme(px.line(tmp.reset_index(), y=m3, title=f"8. Track of {m3.title()} over top volume"))
                    st.plotly_chart(fig, use_container_width=True)
            except: pass

            # 10. Density Heatmap (Uses d2, d3 and m1)
            try:
                if d2 and d3 and d2 != d3:
                    tmp = df.sample(min(5000, len(df)))
                    fig = _apply_theme(px.density_heatmap(tmp, x=d2, y=d3, z=m1, histfunc="sum", title=f"10. Density: {d2.title()} vs {d3.title()}"))
                    st.plotly_chart(fig, use_container_width=True)
                elif len(numeric_cols) > 1:
                    tmp = df.sample(min(3000, len(df)))
                    fig = _apply_theme(px.density_heatmap(tmp, x=m1, y=m3, title=f"10. Density Heatmap: {m1.title()} vs {m3.title()}"))
                    st.plotly_chart(fig, use_container_width=True)
            except: pass

    with tab_copilot:
        render_kpis()
        # Reduced vertical space
        st.write("<div style='margin-bottom: -15px;'></div>", unsafe_allow_html=True)

        # ================= AUTONOMOUS INSIGHT =================
        if st.button("Run Autonomous Insight Scan", type="primary"):
        
            # Phase 1: Computation (Hidden with a standardized 1-100% sync bar)
            loading_container = st.empty()
            pbar = loading_container.progress(0, text="AI Analysis in progress...")
        
            # Math: Numerics (0% -> 25%)
            num_metrics = df[numeric_cols].agg(['count', 'nunique', 'max', 'min', 'sum'])
            time.sleep(0.5) 
            pbar.progress(25, text="Generated Numerical summaries.")
        
            # Math: Dimensions (25% -> 60%)
            dim_insights = {}
            no_chart_terms = ['ordernumber', 'orderid', 'phone', 'zip', 'zipcode', 'customername', 'customerid']
            money_keywords = ['sales', 'price', 'revenue', 'amount', 'profit', 'margin', 'cost']
            for dim in dimension_cols:
                grp=df.groupby(dim)[main_metric].sum()
                if len(grp)>1:
                    dim_insights[dim] = grp
            time.sleep(0.5)
            pbar.progress(60, text="Analyzed Descriptors & Categoricals.")

            # Math: Dates (60% -> 90%)
            date_insights = {}
            if date_cols:
                grp=df.groupby(df[date_cols[0]].dt.year)[main_metric].sum()
                if len(grp)>1:
                    date_insights[date_cols[0]] = grp
            time.sleep(0.5)
            pbar.progress(90, text="Finalizing Time-Series processing.")

            # Complete! (90% -> 100%)
            time.sleep(0.3)
            pbar.progress(100, text="Scan Complete! Preparing visuals.")
            time.sleep(0.3)
            loading_container.empty()

            # Phase 2: Instant UI Rendering (Math is already done)
            st.subheader("Numerical Insights")
            no_sum_columns = ['ordernumber', 'orderid', 'year', 'month', 'day', 'qtr', 'quarter', 'id', 'code', 'number', 'zip', 'pin', 'phone', 'lat', 'lon', 'latitude', 'longitude', 'index', 'version']
            sum_allow_keywords = ["sales", "revenue", "profit", "margin", "amount", "income", "quantity", "cost", "price", "delay", "duration", "charging", "kw", "unit", "sold", "total"]
            money_keywords = ['sales', 'price', 'revenue', 'amount', 'profit', 'margin', 'cost']

            def _should_skip_sum(col):
                is_no_sum = any(term in col.lower() for term in no_sum_columns)
                is_sum_allowed = any(term in col.lower() for term in sum_allow_keywords)
                return is_no_sum or not is_sum_allowed

            for i in range(0,len(numeric_cols),4):
                cols=st.columns(4)
                for j in range(4):
                    if i+j<len(numeric_cols):
                        col=numeric_cols[i+j]
                    
                        count_val = num_metrics.loc['count', col]
                        unique_val = num_metrics.loc['nunique', col]
                        max_raw = num_metrics.loc['max', col]
                        min_raw = num_metrics.loc['min', col]
                        sum_raw = num_metrics.loc['sum', col]
                        is_money = any(keyword in col.lower() for keyword in money_keywords)
                    
                        with cols[j]:
                            if _should_skip_sum(col):
                                if is_money:
                                    max_val = f"${max_raw:,.2f}"
                                    min_val = f"${min_raw:,.2f}"
                                else:
                                    max_val = f"{max_raw:,.0f}"
                                    min_val = f"{min_raw:,.0f}"
                            
                                st.markdown(f"""
                                <div class="insight-card">
                                <b class="insight-title">{col}</b><br>
                                Count: {count_val:,.0f}<br>
                                Unique: {unique_val:,}<br>
                                Max: {max_val}<br>
                                Min: {min_val}
                                </div>
                                """, unsafe_allow_html=True)
                            else:
                                if is_money:
                                    total_display = f"${sum_raw:,.2f}"
                                    max_display = f"${max_raw:,.2f}"
                                    min_display = f"${min_raw:,.2f}"
                                else:
                                    total_display = f"{sum_raw:,.0f}"
                                    max_display = f"{max_raw:,.0f}"
                                    min_display = f"{min_raw:,.0f}"
                            
                                st.markdown(f"""
                                <div class="insight-card">
                                <b class="insight-title">{col}</b><br>
                                Total: {total_display}<br>
                                Unique: {unique_val:,}<br>
                                Max: {max_display}<br>
                                Min: {min_display}
                                </div>
                                """, unsafe_allow_html=True)

            st.subheader("Descriptive Insights")
            for dim, grp in dim_insights.items():
                money_keywords = ['sales', 'price', 'revenue', 'amount', 'profit', 'margin', 'cost']
                is_money = any(keyword in main_metric.lower() for keyword in money_keywords)
                best_value = grp.max()
                worst_value = grp.min()
            
                if is_money:
                    best_display = f"${best_value:,.2f}"
                    worst_display = f"${worst_value:,.2f}"
                else:
                    best_display = f"{best_value:,.0f}"
                    worst_display = f"{worst_value:,.0f}"
            
                st.markdown(f"""
                <div class="insight-card">
                <b class="insight-title">{dim}</b><br>
                Best: {grp.idxmax()} ({best_display})<br>
                Worst: {grp.idxmin()} ({worst_display})
                </div>
                """, unsafe_allow_html=True)

            if date_insights:
                st.subheader("Date Insights")
                for d, grp in date_insights.items():
                    money_keywords = ['sales', 'price', 'revenue', 'amount', 'profit', 'margin', 'cost']
                    is_money = any(keyword in main_metric.lower() for keyword in money_keywords)
                    best_value = grp.max()
                    worst_value = grp.min()
                
                    if is_money:
                        best_display = f"${best_value:,.2f}"
                        worst_display = f"${worst_value:,.2f}"
                    else:
                        best_display = f"{best_value:,.0f}"
                        worst_display = f"{worst_value:,.0f}"
                
                    st.markdown(f"""
                    <div class="insight-card">
                    <b class="insight-title">{d}</b><br>
                    Best Year: {int(grp.idxmax())} ({best_display})<br>
                    Worst Year: {int(grp.idxmin())} ({worst_display})
                    </div>
                    """, unsafe_allow_html=True)

        # Custom tight divider to save vertical space
        st.markdown("<hr style='margin: 10px 0; border: none; border-top: 1px solid rgba(255,154,158,0.2);'>", unsafe_allow_html=True)    
        # ================= ⭐ SMART BI ENGINE =================

        SYNONYMS={
            "product":"productline",
            "products":"productline",
            "item":"productline",
            "category":"productline",
            "order":"ordernumber",
            "orders":"ordernumber",
            "date":"orderdate",
            "orderdate":"orderdate",
            "country":"country",
            "region":"country",
            "status":"status",
            "address":"addressline1",
            "city":"city",
            "customer":"customername",
            "customername":"customername",
            "contact":"contactfirstname",
            "firstname":"contactfirstname",
            "territory":"territory",
            "month":"month_id",
            "year":"year_id",
            "performing":"sales",
            "performance":"sales"
        }

        MONTH_MAP = {
            'january': 1, 'jan': 1,
            'february': 2, 'feb': 2,
            'march': 3, 'mar': 3,
            'april': 4, 'apr': 4,
            'may': 5,
            'june': 6, 'jun': 6,
            'july': 7, 'jul': 7,
            'august': 8, 'aug': 8,
            'september': 9, 'sep': 9,
            'october': 10, 'oct': 10,
            'november': 11, 'nov': 11,
            'december': 12, 'dec': 12
        }

        AGG_KEYWORDS = {
            'total': 'SUM',
            'sum': 'SUM',
            'average': 'AVG',
            'avg': 'AVG',
            'mean': 'AVG',
            'count': 'COUNT',
            'number of': 'COUNT',
            'how many': 'COUNT',
            'minimum': 'MIN',
            'min': 'MIN',
            'maximum': 'MAX',
            'max': 'MAX',
            'distinct': 'DISTINCT COUNT',
            'unique': 'DISTINCT COUNT'
        }

        SPECIAL_PATTERNS = {
            'shortest': 'LENGTH',
            'longest': 'LENGTH',
            'smallest': 'MIN',
            'largest': 'MAX',
            'earliest': 'MIN',
            'latest': 'MAX',
            'first': 'MIN',
            'last': 'MAX'
        }

        def understand_data_structure():
            data_profile = {
                "table_name": "data",
                "columns": list(df.columns),
                "dimensions": dimension_cols,
                "metrics": numeric_cols,
                "date_fields": date_cols,
                "sample_values": {},
                "column_domains": {},
                "row_count": len(df)
            }
        
            for col in df.columns:
                if col in dimension_cols:
                    unique_vals = df[col].dropna().unique()
                    data_profile["sample_values"][col] = {
                        "unique_count": int(len(unique_vals)),
                        "examples": [str(v) for v in unique_vals[:10]]
                    }
                elif col in numeric_cols:
                    data_profile["column_domains"][col] = {
                        "min": float(df[col].min()) if not pd.isna(df[col].min()) else 0,
                        "max": float(df[col].max()) if not pd.isna(df[col].max()) else 0,
                        "avg": float(df[col].mean()) if not pd.isna(df[col].mean()) else 0,
                        "sum": float(df[col].sum()) if not pd.isna(df[col].sum()) else 0,
                        "nulls": int(df[col].isna().sum())
                    }
                elif col in date_cols:
                    non_null = df[col].dropna()
                    if len(non_null) > 0:
                        data_profile["column_domains"][col] = {
                            "min_date": str(non_null.min()),
                            "max_date": str(non_null.max())
                        }
        
            return data_profile

        def is_powerbi_related(question):
            powerbi_keywords = [
                "data", "analysis", "analyze", "analytics", "dashboard", "report",
                "visualization", "chart", "graph", "plot", "insight", "metric",
                "kpi", "measure", "dimension", "filter", "segment", "trend",
                "comparison", "distribution", "correlation", "pattern", "outlier",
                "sales", "revenue", "profit", "customer", "product", "order",
                "quantity", "price", "cost", "margin", "country", "region",
                "date", "time", "year", "month", "quarter", "total", "average",
                "sum", "count", "minimum", "maximum", "top", "bottom", "best",
                "worst", "highest", "lowest", "performance", "growth", "decline",
                "shortest", "longest", "earliest", "latest", "smallest", "largest",
                "first", "last", "performing"
            ]
        
            question_lower = question.lower()
            for keyword in powerbi_keywords:
                if keyword in question_lower:
                    return True
            for col in df.columns:
                if col in question_lower:
                    return True
            return True

        def resolve_col(text, pool):
            text=text.lower()
            for word,col in SYNONYMS.items():
                if word in text and col in pool:
                    return col
            for c in pool:
                if c in text:
                    return c
            tokens=text.split()
            scores={c:sum(1 for t in tokens if t in c) for c in pool}
            best=max(scores,key=scores.get)
            return best

        def resolve_col_from_phrase(phrase, pool):
            phrase = phrase.lower()
            for word, col in SYNONYMS.items():
                if word == phrase and col in pool:
                    return col
            for col in pool:
                if phrase == col or col in phrase or phrase in col:
                    return col
            words = phrase.split()
            for col in pool:
                col_lower = col.lower()
                for word in words:
                    if word in col_lower:
                        return col
            return None

        def detect_aggregation_from_question(question):
            q = question.lower()
            for keyword, agg_type in AGG_KEYWORDS.items():
                if keyword in q:
                    return agg_type
            return None

        def extract_time_filter(q):
            month = None
            year = None
            for month_name, month_num in MONTH_MAP.items():
                if month_name in q:
                    month = month_num
                    break
            year_match = re.search(r'\b(19|20)\d{2}\b', q)
            if year_match:
                year = year_match.group(0)
            return month, year

        def handle_special_queries(question):
            q = question.lower()
            for pattern, operation in SPECIAL_PATTERNS.items():
                if pattern in q:
                    target_col = None
                    for col in df.columns:
                        if col in q:
                            target_col = col
                            break
                    if not target_col:
                        for word, col in SYNONYMS.items():
                            if word in q and col in df.columns:
                                target_col = col
                                break
                    if target_col:
                        if operation == 'LENGTH':
                            if pattern == 'shortest':
                                df_copy = df.copy()
                                df_copy['name_length'] = df_copy[target_col].astype(str).str.len()
                                result = df_copy.loc[df_copy['name_length'].idxmin(), target_col]
                                return pd.DataFrame({f"shortest_{target_col}": [result]})
                            elif pattern == 'longest':
                                df_copy = df.copy()
                                df_copy['name_length'] = df_copy[target_col].astype(str).str.len()
                                result = df_copy.loc[df_copy['name_length'].idxmax(), target_col]
                                return pd.DataFrame({f"longest_{target_col}": [result]})
                        else:
                            con = duckdb.connect()
                            try:
                                con.register("data", df)
                                if pattern in ['smallest', 'earliest', 'first']:
                                    sql = f"SELECT MIN({target_col}) as {pattern}_{target_col} FROM data"
                                elif pattern in ['largest', 'latest', 'last']:
                                    sql = f"SELECT MAX({target_col}) as {pattern}_{target_col} FROM data"
                                return con.execute(sql).df()
                            finally:
                                con.close()
            return None

        def handle_time_filtered_questions(question, selected_agg):
            q = question.lower()
            month, year = extract_time_filter(q)
            if month and ('sales' in q or 'revenue' in q or 'total' in q):
                date_col = None
                for col in date_cols:
                    if 'date' in col:
                        date_col = col
                        break
                if not date_col and date_cols:
                    date_col = date_cols[0]
            
                if date_col:
                    metric_col = None
                    for col in numeric_cols:
                        if 'sales' in col or 'revenue' in col or 'amount' in col:
                            metric_col = col
                            break
                    if not metric_col and numeric_cols:
                        metric_col = numeric_cols[0]
                
                    where_clauses = [f"EXTRACT(MONTH FROM {date_col}) = {month}"]
                    if year:
                        where_clauses.append(f"EXTRACT(YEAR FROM {date_col}) = {year}")
                    where_sql = " AND ".join(where_clauses)
                
                    con = duckdb.connect()
                    try:
                        con.register("data", df)
                        if 'total' in q or 'sum' in q:
                            sql = f"SELECT SUM({metric_col}) as total_sales FROM data WHERE {where_sql}"
                        elif 'average' in q or 'avg' in q:
                            sql = f"SELECT AVG({metric_col}) as avg_sales FROM data WHERE {where_sql}"
                        elif 'count' in q:
                            sql = f"SELECT COUNT({metric_col}) as order_count FROM data WHERE {where_sql}"
                        elif selected_agg != "None (show raw data)":
                            if selected_agg == "SUM":
                                sql = f"SELECT SUM({metric_col}) as total_sales FROM data WHERE {where_sql}"
                            elif selected_agg == "AVG":
                                sql = f"SELECT AVG({metric_col}) as avg_sales FROM data WHERE {where_sql}"
                            elif selected_agg == "COUNT":
                                sql = f"SELECT COUNT({metric_col}) as order_count FROM data WHERE {where_sql}"
                            elif selected_agg == "MIN":
                                sql = f"SELECT MIN({metric_col}) as min_sales FROM data WHERE {where_sql}"
                            elif selected_agg == "MAX":
                                sql = f"SELECT MAX({metric_col}) as max_sales FROM data WHERE {where_sql}"
                            else:
                                sql = f"SELECT SUM({metric_col}) as total_sales FROM data WHERE {where_sql}"
                        else:
                            sql = f"SELECT SUM({metric_col}) as total_sales FROM data WHERE {where_sql}"
                    
                        result = con.execute(sql).df()
                        return result
                    finally:
                        con.close()
            return None

        # ================= AGGREGATION SELECTOR =================
        if 'agg_option' not in st.session_state:
            st.session_state.agg_option = "None (show raw data)"

        if 'chat_history' not in st.session_state:
            st.session_state.chat_history = []

        # ================= NLQ =================
        st.markdown("<h3 style='margin-top: -85px; margin-bottom: 0px; font-weight: 800; font-family: Outfit, sans-serif;'><span style='color: #FF4B91 !important;'>AI</span> <span style='color: #000000;'>Copilot</span> Insights</h3>", unsafe_allow_html=True)
        with st.form("ask_form", border=False):
            col1, col2 = st.columns([5, 1])
            with col1:
                q = st.text_input("Ask business question", placeholder="Ask your question here...", label_visibility="collapsed")
            with col2:
                ask_pressed = st.form_submit_button("ASK", type="primary", use_container_width=True)

        agg_option = st.selectbox(
            "Select aggregation type (optional override):",
            ["None (show raw data)", "COUNT", "DISTINCT COUNT", "SUM", "AVG", "MIN", "MAX"],
            key="agg_option"
        )

        st.caption("💡 Ask anything about your data in plain English!")

        mem_col1, mem_col2 = st.columns([4, 1])
        with mem_col1:
            if len(st.session_state.chat_history) > 0:
                st.info(f"🧠 Memory active: Remembering context from last {len(st.session_state.chat_history)} queries.")
            else:
                st.caption("🧠 Memory empty. Ask a question to start building context.")
        with mem_col2:
            if st.button("🗑️ Clear Context", use_container_width=True):
                st.session_state.chat_history = []
                st.rerun()

        def _build_schema_context():
            """Build a rich schema context string with sample values and stats for the LLM."""
            data_profile = understand_data_structure()
            schema_lines = []
            for col in df.columns:
                col_type = "Numeric" if col in numeric_cols else "Date" if col in date_cols else "Text/Categorical"
                line = f"- {col} ({col_type})"
                if col in data_profile["sample_values"]:
                    info = data_profile["sample_values"][col]
                    examples = ', '.join(info['examples'][:8])
                    line += f"  [Unique values: {info['unique_count']}. Examples: {examples}]"
                if col in data_profile["column_domains"]:
                    dom = data_profile["column_domains"][col]
                    if 'min_date' in dom:
                        line += f"  [Range: {dom['min_date']} to {dom['max_date']}]"
                    else:
                        line += f"  [Min: {dom['min']:.2f}, Max: {dom['max']:.2f}, Avg: {dom['avg']:.2f}, Sum: {dom['sum']:.2f}]"
                schema_lines.append(line)
            return "\n".join(schema_lines), data_profile

        def _build_llm_prompt(question, agg, schema_str, error_context=None):
            """Build the LLM prompt for SQL generation."""
            history_str = ""
            if st.session_state.chat_history:
                history_str = "\n=== PREVIOUS CONVERSATION HISTORY (Use for follow-up context) ===\n"
                for q_past, sql_past in st.session_state.chat_history[-5:]:
                    history_str += f"Q: \"{q_past}\"\nSQL: {sql_past}\n---\n"
                history_str += "If the new question references 'that', 'those', 'this', 'it', 'same', 'them', 'previous', or implies continuation, modify the most recent Past SQL to fulfill the new request. If it is a completely new topic, write a fresh query.\n"

            error_section = ""
            if error_context:
                error_section = f"""
    === PREVIOUS ATTEMPT FAILED ===
    The SQL you generated previously was:
    {error_context['sql']}

    It failed with this error:
    {error_context['error']}

    Please fix the SQL to avoid this error. Common fixes:
    - Check column names match exactly (case-sensitive)
    - Ensure GROUP BY includes all non-aggregated columns
    - Ensure FROM data is present
    - Do not use columns that don't exist
    - For string comparisons use ILIKE instead of = for flexibility
    ========================
    """

            prompt = f"""You are an elite Data Analyst and DuckDB SQL expert powering an AI BI Copilot application.
    You have a DuckDB table named 'data' with {len(df)} rows and the following schema:

    {schema_str}

    {history_str}
    {error_section}

    User's natural language question: "{question}"
    User's selected aggregation override: "{agg}"

    === INTELLIGENCE RULES ===

    1. SCHEMA FIDELITY: Use ONLY columns from the schema above. Never invent columns. Match column names EXACTLY (they are lowercase with underscores).

    2. QUERY STRUCTURE: ALWAYS include 'FROM data'. NEVER use SELECT *. Always name columns explicitly.

    3. GROUP BY RULE: If your SELECT has ANY aggregate function (COUNT, SUM, AVG, MIN, MAX) alongside a non-aggregated column, you MUST GROUP BY every non-aggregated column. This is non-negotiable.

    4. NATURAL LANGUAGE UNDERSTANDING:
       - "show me X" → SELECT the relevant columns, possibly with aggregation
       - "how many" / "count" / "number of" → use COUNT()
       - "total" / "sum" / "overall" → use SUM()
       - "average" / "avg" / "mean" → use AVG()
       - "top N" → ORDER BY ... DESC LIMIT N
       - "bottom N" / "worst N" / "lowest N" → ORDER BY ... ASC LIMIT N
       - "best" / "highest" / "most" → ORDER BY ... DESC LIMIT 1
       - "worst" / "lowest" / "least" → ORDER BY ... ASC LIMIT 1
       - "by" / "per" / "for each" / "across" → GROUP BY that dimension
       - "between X and Y" → WHERE col BETWEEN X AND Y
       - "greater than" / "more than" / "above" → WHERE col > value
       - "less than" / "below" / "under" → WHERE col < value
       - "trend" / "over time" → GROUP BY date/time column, ORDER BY date
       - "compare" / "comparison" / "vs" → SELECT both items with their metrics
       - "growth" / "change" / "difference" → compute difference or percentage change
       - "distribution" → GROUP BY with COUNT
       - "correlation" → SELECT both numeric columns
       - "percentage" / "share" / "proportion" → compute ratio with window function or subquery

    5. STRING MATCHING: When filtering by text values (e.g., country='USA'), use ILIKE for case-insensitive matching. If the user mentions a value, find the closest match from the sample values shown in the schema.

    6. DATE HANDLING: For date columns, use EXTRACT(YEAR FROM col), EXTRACT(MONTH FROM col), etc. For "monthly trend" use EXTRACT(MONTH FROM date_col). For "yearly" use EXTRACT(YEAR FROM date_col).

    7. AGGREGATION OVERRIDE: If the user selected an aggregation override that is NOT 'None (show raw data)', apply that aggregation to the primary metric column.

    8. ORDERING: Always add meaningful ORDER BY. For aggregated results, order by the aggregate DESC unless the user asks for bottom/worst/lowest.

    9. ALIASES: Give columns readable aliases using AS (e.g., SUM(sales) AS total_sales).

    10. LIMIT: For questions asking to "list" or "show all", limit to 100 rows max. For top/bottom questions, use the specified N.

    11. MULTI-COLUMN QUESTIONS: If the user asks about multiple metrics (e.g., "sales and profit by country"), include ALL requested metrics in the SELECT.

    12. WHEN UNSURE: If the question is ambiguous, prefer the interpretation that gives the most useful business insight. Default metric should be the first numeric column. Default dimension should be the first categorical column.

    13. RETURN ONLY the raw SQL query. No explanations, no markdown, no code fences. Just the SELECT statement.
    """
            return prompt

        def smart_query(question, selected_agg):
            schema_str, data_profile = _build_schema_context()
        
            # Generate SQL from LLM
            def _call_llm_for_sql(prompt_text):
                res = client.chat.completions.create(
                    model="nvidia/nemotron-3-super-120b-a12b",
                    messages=[{"role": "user", "content": prompt_text}],
                    temperature=0.0,
                    top_p=0.95,
                    max_tokens=1024
                )
                sql_query = res.choices[0].message.content.strip()
                # Clean any markdown fences
                sql_query = re.sub(r"^```sql\s*\n?", "", sql_query, flags=re.MULTILINE)
                sql_query = re.sub(r"^```\s*\n?", "", sql_query, flags=re.MULTILINE)
                sql_query = re.sub(r"\n?```$", "", sql_query, flags=re.MULTILINE)
                sql_query = sql_query.strip()
                # Remove any leading explanation text before SELECT
                select_match = re.search(r'(SELECT\s)', sql_query, re.IGNORECASE)
                if select_match and select_match.start() > 0:
                    sql_query = sql_query[select_match.start():]
                return sql_query
        
            # Attempt up to 3 times with self-repair
            max_attempts = 3
            last_error = None
            last_sql = None
        
            for attempt in range(max_attempts):
                try:
                    if attempt == 0:
                        prompt = _build_llm_prompt(question, selected_agg, schema_str)
                    else:
                        prompt = _build_llm_prompt(question, selected_agg, schema_str, 
                                                  error_context={"sql": last_sql, "error": str(last_error)})
                
                    sql = _call_llm_for_sql(prompt)
                    last_sql = sql
                
                    # Validate basic structure
                    if not sql.upper().strip().startswith('SELECT'):
                        raise Exception(f"Generated output is not a valid SQL SELECT statement: {sql[:100]}")
                    if 'FROM' not in sql.upper():
                        raise Exception("Generated SQL is missing FROM clause")
                
                    con = duckdb.connect()
                    try:
                        con.register("data", df)
                        result = con.execute(sql).df()
                    
                        # Store successful SQL in chat history
                        st.session_state.chat_history.append((question, sql))
                        # Keep history manageable
                        if len(st.session_state.chat_history) > 10:
                            st.session_state.chat_history = st.session_state.chat_history[-10:]
                    
                        return result
                    finally:
                        con.close()
                    
                except Exception as e:
                    last_error = e
                    last_sql = sql if 'sql' in dir() else "(no SQL generated)"
                    if attempt < max_attempts - 1:
                        continue
        
            # All attempts failed — raise the last error with context
            raise Exception(f"After {max_attempts} attempts, could not generate a working query.\nLast SQL: {last_sql}\nLast Error: {str(last_error)}")

        if ask_pressed and q:
            if not is_powerbi_related(q):
                st.warning("⚠️ Please ask a question related to data analysis.")
            else:
                try:
                    # Phase 1: Computation + progress bar
                    loading_container = st.empty()
                    pbar = loading_container.progress(5, text="Translating natural language to SQL... 5%")
                
                    # Get result (cached inside smart_query)
                    result = smart_query(q, st.session_state.agg_option)
                    time.sleep(0.5)
                    pbar.progress(50, text="Executing query on DuckDB engine... 50%")
                
                    # ----- Prepare visualisation (still cached) -----
                    fig = None
                    is_metric = False
                    metric_col_name = None
                    metric_val = None

                    if len(result.columns) >= 2 and len(result) > 1:
                        pbar.progress(70, text="Rendering smart visualizations... 70%")
                        col1 = result.columns[0]
                        col2 = result.columns[1]
                        num_rows = len(result)
                        q_lower = q.lower()
                    
                        # Detect column types
                        is_date = False
                        if pd.api.types.is_datetime64_any_dtype(result[col1]):
                            is_date = True
                        elif result[col1].dtype == 'object' or str(result[col1].dtype) == 'string':
                            val = str(result[col1].iloc[0])
                            if re.match(r'^\d{4}-\d{2}-\d{2}', val) or re.match(r'^\d{2}/\d{2}/\d{4}', val):
                                is_date = True
                        is_c1_num = pd.api.types.is_numeric_dtype(result[col1])
                        is_c2_num = pd.api.types.is_numeric_dtype(result[col2])
                    
                        # Check if col1 looks like a time sequence (year, month, quarter)
                        is_time_like = any(t in col1.lower() for t in ['year', 'month', 'quarter', 'qtr', 'week', 'date', 'day', 'period'])
                    
                        # Detect question intent for chart type
                        wants_trend = any(w in q_lower for w in ['trend', 'over time', 'over the', 'monthly', 'yearly', 'quarterly', 'weekly', 'growth', 'decline', 'change over', 'progression', 'timeline', 'history'])
                        wants_compare = any(w in q_lower for w in ['compare', 'comparison', 'vs', 'versus', 'difference between', 'against'])
                        wants_distribution = any(w in q_lower for w in ['distribution', 'spread', 'breakdown', 'share', 'proportion', 'percentage', 'pie', 'composition', 'mix'])
                        wants_ranking = any(w in q_lower for w in ['top', 'bottom', 'best', 'worst', 'highest', 'lowest', 'rank', 'ranking', 'most', 'least', 'leading', 'lagging'])
                        wants_correlation = any(w in q_lower for w in ['correlation', 'relationship', 'scatter', 'plotted against', 'vs'])
                        wants_area = any(w in q_lower for w in ['area', 'cumulative', 'stacked area', 'filled'])
                        wants_hbar = any(w in q_lower for w in ['horizontal', 'hbar'])
                        wants_treemap = any(w in q_lower for w in ['treemap', 'tree map', 'hierarchy', 'hierarchical'])
                        wants_funnel = any(w in q_lower for w in ['funnel', 'pipeline', 'stages', 'conversion'])
                    
                        # Has 3+ columns? Could do grouped bar
                        has_multi_metrics = len(result.columns) >= 3 and sum(pd.api.types.is_numeric_dtype(result[c]) for c in result.columns) >= 2
                    
                        try:
                            # 1. Explicit user intent takes priority
                            if wants_funnel and not is_c1_num and is_c2_num and num_rows <= 10:
                                fig = px.funnel(result, x=col2, y=col1,
                                                title=f"{col2.replace('_', ' ').title()} Funnel by {col1.replace('_', ' ').title()}")
                        
                            elif wants_treemap and not is_c1_num and is_c2_num:
                                fig = px.treemap(result, path=[col1], values=col2,
                                                 title=f"{col2.replace('_', ' ').title()} Treemap by {col1.replace('_', ' ').title()}")
                        
                            elif wants_area and is_c2_num and (is_date or is_time_like):
                                temp_res = result.sort_values(by=col1)
                                fig = px.area(temp_res, x=col1, y=col2,
                                              title=f"{col2.replace('_', ' ').title()} over {col1.replace('_', ' ').title()}")
                        
                            elif wants_distribution and not is_c1_num and is_c2_num and num_rows <= 8:
                                fig = px.pie(result, names=col1, values=col2, hole=0.4,
                                             title=f"Distribution of {col2.replace('_', ' ').title()}")
                                fig.update_traces(textposition='inside', textinfo='percent+label')
                        
                            elif wants_correlation and is_c1_num and is_c2_num:
                                fig = px.scatter(result, x=col1, y=col2,
                                                 title=f"{col2.replace('_', ' ').title()} vs {col1.replace('_', ' ').title()}",
                                                 trendline="ols")
                        
                            elif wants_hbar and not is_c1_num and is_c2_num:
                                fig = px.bar(result, x=col2, y=col1, orientation='h',
                                             title=f"{col2.replace('_', ' ').title()} by {col1.replace('_', ' ').title()}")
                        
                            # 2. Date / time-series → line chart
                            elif (is_date or is_time_like) and is_c2_num:
                                temp_res = result.sort_values(by=col1)
                                if wants_trend or num_rows > 6:
                                    fig = px.line(temp_res, x=col1, y=col2, markers=True,
                                                  title=f"{col2.replace('_', ' ').title()} over {col1.replace('_', ' ').title()}")
                                else:
                                    fig = px.bar(temp_res, x=col1, y=col2,
                                                 title=f"{col2.replace('_', ' ').title()} by {col1.replace('_', ' ').title()}")
                        
                            # 3. Ranking questions → horizontal bar (looks great for top/bottom)
                            elif wants_ranking and not is_c1_num and is_c2_num:
                                sorted_res = result.sort_values(by=col2, ascending=True)
                                fig = px.bar(sorted_res, x=col2, y=col1, orientation='h',
                                             title=f"{col2.replace('_', ' ').title()} by {col1.replace('_', ' ').title()}")
                                fig.update_traces(marker_color='#00e8a2')
                        
                            # 4. Comparison with multiple metrics → grouped bar
                            elif wants_compare and has_multi_metrics:
                                numeric_cols_in_result = [c for c in result.columns if pd.api.types.is_numeric_dtype(result[c])]
                                fig = px.bar(result, x=col1, y=numeric_cols_in_result, barmode='group',
                                             title=f"Comparison by {col1.replace('_', ' ').title()}")
                        
                            # 5. Two numeric columns (not time) → scatter
                            elif is_c1_num and is_c2_num and not is_time_like and 'year' not in col1.lower() and 'month' not in col1.lower():
                                fig = px.scatter(result, x=col1, y=col2,
                                                 title=f"{col2.replace('_', ' ').title()} vs {col1.replace('_', ' ').title()}",
                                                 trendline="ols")
                        
                            # 6. Categorical + numeric: smart pick based on row count
                            elif not is_c1_num and is_c2_num:
                                if num_rows <= 5 and not wants_ranking:
                                    # Small categories → donut for variety
                                    fig = px.pie(result, names=col1, values=col2, hole=0.4,
                                                 title=f"{col2.replace('_', ' ').title()} by {col1.replace('_', ' ').title()}")
                                    fig.update_traces(textposition='inside', textinfo='percent+label')
                                elif num_rows <= 12:
                                    # Medium range → vertical bar
                                    sorted_res = result.sort_values(by=col2, ascending=False)
                                    fig = px.bar(sorted_res, x=col1, y=col2,
                                                 title=f"{col2.replace('_', ' ').title()} by {col1.replace('_', ' ').title()}")
                                else:
                                    # Many categories → horizontal bar for readability
                                    sorted_res = result.sort_values(by=col2, ascending=True)
                                    fig = px.bar(sorted_res, x=col2, y=col1, orientation='h',
                                                 title=f"{col2.replace('_', ' ').title()} by {col1.replace('_', ' ').title()}")
                        
                            # 7. Fallback → bar chart
                            else:
                                fig = px.bar(result, x=col1, y=col2,
                                             title=f"{col2.replace('_', ' ').title()} by {col1.replace('_', ' ').title()}")
                        except Exception:
                            fig = px.bar(result, x=col1, y=col2)
                    
                        # Apply premium theme to ALL chart types
                        if fig:
                            fig.update_layout(
                                plot_bgcolor='#0a0c14',
                                paper_bgcolor='#0a0c14',
                                font=dict(color='#f0f2f5', family='Inter, sans-serif'),
                                title_font=dict(size=16, color='#f0f2f5', family='Outfit, sans-serif'),
                                xaxis=dict(gridcolor='rgba(255,255,255,0.05)', zerolinecolor='rgba(255,255,255,0.08)'),
                                yaxis=dict(gridcolor='rgba(255,255,255,0.05)', zerolinecolor='rgba(255,255,255,0.08)'),
                                margin=dict(l=40, r=40, t=50, b=40),
                                hoverlabel=dict(bgcolor='#141620', font_color='#f0f2f5', bordercolor='rgba(0,232,162,0.3)')
                            )
                            fig.update_traces(marker_color='#00e8a2', selector=dict(type='bar'))
                    elif len(result.columns) == 1 and len(result) == 1:
                        is_metric = True
                        metric_col_name = result.columns[0]
                        metric_val = result.iloc[0, 0]
                
                    pbar.progress(85, text="Synthesizing business insights... 85%")
                
                    # ----- LLM insight (still needed) -----
                    result_sample = result.head(20)
                    prompt = f"""
                    You are a Business Intelligence expert analyzing data.
                    User question: {q}
                    Aggregation selected: {st.session_state.agg_option}
                    Result data (sample of up to 20 rows):
                    {result_sample.to_string(index=False)}
                
                    Provide ONE short, actionable business insight based on this data. 
                    Keep it concise and focused on business value. Do not mention "based on the data".
                    """
                    insight_resp = client.chat.completions.create(
                        model="nvidia/nemotron-3-super-120b-a12b",
                        messages=[{"role": "user", "content": prompt}],
                        temperature=0.7,
                        top_p=0.95,
                        max_tokens=512
                    )
                    final_insight = insight_resp.choices[0].message.content
                
                    # Phase 2: Complete
                    time.sleep(0.3)
                    pbar.progress(100, text="Finalizing response... 100%")
                    time.sleep(0.3)
                    loading_container.empty()
                
                    # ----- Render -----
                    st.dataframe(result)
                
                    if fig:
                        st.plotly_chart(fig, use_container_width=True)
                    elif is_metric:
                        money_keywords = ['sales', 'revenue', 'price', 'amount', 'profit', 'margin', 'cost', 'sum', 'total']
                        is_money = any(kw in metric_col_name.lower() for kw in money_keywords)
                        if is_money and isinstance(metric_val, (int, float)):
                            st.metric("Result", f"${metric_val:,.2f}")
                        elif isinstance(metric_val, (int, float)):
                            st.metric("Result", f"{metric_val:,.2f}")
                        else:
                            st.metric("Result", metric_val)
                
                    st.success("💡 Insight: " + final_insight)
                    st.session_state['export_df'] = result
            
                except Exception as e:
                    st.error(f"Sorry, I couldn't process that question. Error details: {str(e)}")
                    st.info("Try rephrasing your question to be more specific about the columns you want to analyze, or click 'Clear Context' if the AI is confused by a previous question.")

        # ================= EXPORT PIPELINE =================
        if 'export_df' in st.session_state:
            st.divider()
            st.subheader("💾 Export AI Dataset to Power BI")
            st.write("Turn your AI's calculations into a permanent table. You can load this perfectly clean dataset directly into Power BI without writing DAX.")

            c_exp1, c_exp2 = st.columns(2)
            with c_exp1:
                csv_data = st.session_state['export_df'].to_csv(index=False).encode('utf-8')
                st.download_button(
                    label="📥 Download as CSV",
                    data=csv_data,
                    file_name="ai_copilot_export.csv",
                    mime="text/csv",
                    use_container_width=True
                )
            
            with c_exp2:
                if data_source_type == "Database Connection" and 'db_engine' in st.session_state:
                    with st.expander("🗄️ Save as New Table in SQL Server / MySQL"):
                        new_table = st.text_input("Table Name:", value="AI_Summary_Data")
                        if st.button("Write to Database", use_container_width=True):
                            try:
                                with st.spinner("Writing to database..."):
                                    st.session_state['export_df'].to_sql(new_table, con=st.session_state['db_engine'],
                                                                         if_exists='replace', index=False)
                                st.success(f"Successfully created '{new_table}' in your database!")
                            except Exception as e:
                                st.error(f"Database error: {e}")
                else:
                    st.info("Connect to your SQL Server or MySQL database in the sidebar to write tables directly back to your server.")