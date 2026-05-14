"""
streamlit_app.py — Delivery Service Management System
======================================================
"""

import sys
import streamlit as st

st.set_page_config(
    page_title="Final Project — Delivery Management System",
    page_icon="",
    layout="wide",
    initial_sidebar_state="expanded",
)

import mysql.connector
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import bcrypt
import datetime
import csv
import io
import time
import random

# ══════════════════════════════════════════════════════════
# CONFIG
# ══════════════════════════════════════════════════════════
# pool_name + pool_size là bắt buộc cho MySQLConnectionPool.
# pool_size=5 phù hợp khi chạy local; tăng khi deploy nhiều user đồng thời.
DB_CONFIG = {
    "host":               "localhost",
    "port":               3306,
    "user":               "app_service",
    "password":           "AppService_Pass@2024",
    "database":           "delivery_db",
    "charset":            "utf8mb4",
    "pool_name":          "delivery_pool",
    "pool_size":          5,
    "pool_reset_session": True,
}

ROLE_PERMS = {
    "delivery_manager": {"customers","orders","vehicles","deliveries",
                         "expenses","reports","issues","audit_log"},
    "dispatcher":       {"customers","orders","vehicles","deliveries","issues"},
    "accountant":       {"expenses","reports"},
}

SLOT_LABELS = {
    "morning":   "Sang (7-12h)",
    "afternoon": "Chieu (12-17h)",
    "evening":   "Toi (17-21h)",
    "anytime":   "Bat ky luc nao",
}

# ══════════════════════════════════════════════════════════
# CSS
# ══════════════════════════════════════════════════════════
st.markdown("""
<style>
:root {
    --bg-base: #080D14;
    --bg-surface: #0E1521;
    --bg-card: #121D2E;
    --bg-raised: #18253A;
    --bg-hover: #1E2F47;
    --bg-active: #1A3550;
    --border: #1E2D45;
    --border-light: #243550;
    --text-1: #E8EFF8;
    --text-2: #8899B2;
    --text-3: #4E6278;
    --accent: #0EA5E9;
    --accent-dark: #0284C7;
    --teal: #14B8A6;
    --teal-dim: #0D9488;
    --indigo: #6366F1;
    --status-pending: #F59E0B;
    --status-assigned: #0EA5E9;
    --status-transit: #6366F1;
    --status-delivered: #10B981;
    --status-failed: #EF4444;
    --status-returned: #F97316;
    --radius: 6px;
    --radius-lg: 10px;
    --shadow: 0 2px 16px rgba(0,0,0,.45);
    --shadow-lg: 0 8px 40px rgba(0,0,0,.6);
    --font-ui: Inter, "Segoe UI", system-ui, -apple-system, BlinkMacSystemFont, sans-serif;
    --font-mono: "JetBrains Mono", "SFMono-Regular", ui-monospace, monospace;
    --transition: .18s cubic-bezier(.4,0,.2,1);
}

/* App baseline */
html { font-size: 14px; }
body, [data-testid="stAppViewContainer"] {
    background: var(--bg-base);
    color: var(--text-1);
    font-family: var(--font-ui);
}
#MainMenu, footer, header, .stDeployButton { visibility: hidden !important; }

[data-testid="stAppViewContainer"] {
    background:
        radial-gradient(circle at top right, rgba(14,165,233,.06), transparent 22%),
        radial-gradient(circle at 18% 16%, rgba(20,184,166,.05), transparent 18%),
        var(--bg-base);
}
[data-testid="stHeader"] { background: transparent; }
.block-container {
    padding-top: 1.2rem !important;
    padding-bottom: 2rem !important;
    max-width: 1500px;
}
[data-testid="stSidebar"] {
    background: var(--bg-surface);
    border-right: 1px solid var(--border);
}
[data-testid="stSidebar"] > div:first-child {
    background: var(--bg-surface);
}
[data-testid="stSidebar"] [data-testid="stVerticalBlockBorderWrapper"] {
    border-color: var(--border) !important;
}
[data-testid="stSidebar"] button,
[data-testid="stSidebar"] .stButton > button {
    justify-content: flex-start;
    text-align: left;
    width: 100%;
}

/* Typography */
h1, h2, h3, h4, h5, h6, p, div, span, label, button, input, textarea, select {
    font-family: var(--font-ui);
}
h1, h2, h3 { letter-spacing: -.02em; }
code, pre, kbd, samp, .tlog, .gps-info {
    font-family: var(--font-mono) !important;
}

/* Login / hero */
[data-testid="column"] [data-testid="stVerticalBlock"] > div:has(input) {
    max-width: 420px;
}
[data-testid="stTextInput"] input,
[data-testid="stTextArea"] textarea,
[data-testid="stNumberInput"] input,
[data-testid="stDateInput"] input,
[data-testid="stSelectbox"] > div,
[data-testid="stMultiSelect"] > div {
    background: var(--bg-surface) !important;
    color: var(--text-1) !important;
    border-color: var(--border-light) !important;
    border-radius: var(--radius) !important;
}
[data-testid="stTextInput"] input:focus,
[data-testid="stTextArea"] textarea:focus,
[data-testid="stNumberInput"] input:focus {
    border-color: var(--accent) !important;
    box-shadow: 0 0 0 1px rgba(14,165,233,.18) !important;
}

/* Buttons */
.stButton > button,
.stDownloadButton > button,
.stFormSubmitButton > button {
    background: var(--bg-raised);
    color: var(--text-1);
    border: 1px solid var(--border);
    border-radius: var(--radius) !important;
    transition: transform var(--transition), background var(--transition), border-color var(--transition), color var(--transition);
    box-shadow: none !important;
}
.stButton > button:hover,
.stDownloadButton > button:hover,
.stFormSubmitButton > button:hover {
    background: var(--bg-hover);
    border-color: var(--border-light);
    transform: translateY(-1px);
}
.stButton > button[kind="primary"],
.stFormSubmitButton > button[kind="primary"] {
    background: var(--accent) !important;
    color: #fff !important;
    border-color: var(--accent) !important;
}
.stButton > button[kind="primary"]:hover,
.stFormSubmitButton > button[kind="primary"]:hover {
    background: var(--accent-dark) !important;
    border-color: var(--accent-dark) !important;
}

/* Sidebar brand */
[data-testid="stSidebar"] [data-testid="stMarkdownContainer"] p,
[data-testid="stSidebar"] [data-testid="stMarkdownContainer"] div {
    color: var(--text-2);
}
[data-testid="stSidebar"] hr { border-color: var(--border); }

/* Metrics / KPI */
div[data-testid="metric-container"] {
    background: var(--bg-card);
    border: 1px solid var(--border);
    border-radius: var(--radius-lg);
    padding: 16px 14px;
    box-shadow: var(--shadow);
    position: relative;
    overflow: hidden;
}
div[data-testid="metric-container"]::before {
    content: "";
    position: absolute;
    top: 0; left: 0; right: 0; height: 2px;
    background: var(--accent);
}
div[data-testid="stMetricValue"] {
    white-space: normal !important;
    word-break: break-word !important;
    font-size: 1.5rem !important;
    line-height: 1.2 !important;
    font-family: var(--font-mono) !important;
}
div[data-testid="stMetricLabel"] {
    color: var(--text-2) !important;
    font-size: 12px !important;
}

/* Containers */
[data-testid="stExpander"] {
    background: var(--bg-card);
    border: 1px solid var(--border);
    border-radius: var(--radius-lg);
    overflow: hidden;
}
[data-testid="stExpander"] details {
    background: var(--bg-card);
}
[data-testid="stExpander"] summary {
    color: var(--text-1);
    font-weight: 600;
}
[data-testid="stTabs"] button {
    color: var(--text-2) !important;
    background: transparent !important;
}
[data-testid="stTabs"] button[aria-selected="true"] {
    color: var(--accent) !important;
    border-bottom-color: var(--accent) !important;
}

/* Dataframes */
[data-testid="stDataFrame"], [data-testid="stArrowVegaLiteChart"] {
    border: 1px solid var(--border);
    border-radius: var(--radius-lg);
    overflow: hidden;
    box-shadow: var(--shadow);
}

/* Notices */
.notify-box {
    background: var(--bg-card);
    border: 1px solid var(--border);
    border-radius: var(--radius-lg);
    padding: 16px;
    margin: 10px 0;
    font-family: var(--font-mono);
    font-size: 12px;
    line-height: 1.7;
    box-shadow: var(--shadow);
}
.tlog {
    background: #161923;
    border-left: 3px solid var(--status-pending);
    padding: 8px 12px;
    color: var(--status-pending);
    border-radius: 0 6px 6px 0;
    margin: 8px 0;
    font-size: 11px;
}
.gps-info {
    background: var(--bg-surface);
    border: 1px solid var(--border);
    border-radius: var(--radius);
    padding: 12px;
    font-size: 12px;
    color: var(--text-2);
}

/* Topbar shell */
.app-topbar {
    display: flex;
    align-items: center;
    gap: 16px;
    margin-bottom: 18px;
    padding: 14px 18px;
    background: rgba(14,21,33,.82);
    border: 1px solid var(--border);
    border-radius: var(--radius-lg);
    box-shadow: var(--shadow);
    backdrop-filter: blur(10px);
}
.app-topbar .title {
    font-size: 15px;
    font-weight: 700;
    letter-spacing: -.02em;
    color: var(--text-1);
    line-height: 1.1;
}
.app-topbar .sub {
    font-size: 12px;
    color: var(--text-2);
    margin-top: 2px;
}
.app-topbar .search {
    flex: 1;
    max-width: 360px;
    position: relative;
}
.app-topbar .search input {
    width: 100%;
    padding: 9px 14px 9px 38px;
    border-radius: var(--radius);
    background: var(--bg-raised);
    border: 1px solid var(--border);
    color: var(--text-1);
    outline: none;
}
.app-topbar .search input::placeholder { color: var(--text-3); }
.app-topbar .search::before {
    content: "🔎";
    position: absolute;
    left: 12px; top: 50%; transform: translateY(-50%);
    font-size: 12px; opacity: .75;
}
.app-topbar .meta {
    margin-left: auto;
    display: flex; align-items: center; gap: 10px;
}
.app-pill {
    padding: 7px 10px;
    border-radius: 999px;
    border: 1px solid var(--border);
    background: var(--bg-card);
    color: var(--text-2);
    font-size: 12px;
    font-family: var(--font-mono);
}
.app-avatar {
    width: 34px; height: 34px; border-radius: 999px;
    display: grid; place-items: center;
    color: #fff; font-weight: 700;
    background: linear-gradient(135deg, var(--indigo), var(--accent));
}

/* Responsive */
@media (max-width: 1200px) {
    .app-topbar { flex-wrap: wrap; }
    .app-topbar .search { order: 3; flex-basis: 100%; max-width: none; }
}
/* Timeline CSS */
.timeline {
    border-left: 2px solid var(--border-light);
    margin-left: 20px;
    padding-left: 20px;
    position: relative;
}
.timeline-item {
    margin-bottom: 20px;
    position: relative;
}
.timeline-item::before {
    content: "";
    background: var(--bg-card);
    border: 2px solid var(--accent);
    border-radius: 50%;
    position: absolute;
    left: -31px;
    top: 5px;
    width: 16px;
    height: 16px;
}
.timeline-date {
    font-size: 11px;
    color: var(--text-2);
    font-family: var(--font-mono);
}
.timeline-content {
    background: var(--bg-raised);
    padding: 10px;
    border-radius: var(--radius);
    border: 1px solid var(--border);
    font-size: 13px;
}
.status-badge {
    padding: 2px 6px;
    border-radius: 4px;
    font-size: 10px;
    font-weight: bold;
    text-transform: uppercase;
}
</style>
""", unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════
# DB HELPERS & ERROR HANDLING
# ══════════════════════════════════════════════════════════
from mysql.connector import pooling
import mysql.connector
import time
from logger import db_logger, app_logger, audit_logger, LOG_DIR

@st.cache_resource
def get_connection_pool():
    db_logger.info("Khởi tạo MySQL Connection Pool...")
    return pooling.MySQLConnectionPool(**DB_CONFIG)

def get_conn():
    pool = get_connection_pool()
    return pool.get_connection()

# ── Decorator bắt lỗi và ghi Log trung tâm ──
def db_action_logger(func):
    def wrapper(*args, **kwargs):
        start_time = time.time()
        # Lấy câu SQL ra để ghi log (nếu là call_sp thì lấy tên proc)
        action_name = args[0] if args else func.__name__
        
        try:
            result = func(*args, **kwargs)
            duration = (time.time() - start_time) * 1000
            db_logger.info(f"SUCCESS | {func.__name__} | {duration:.2f}ms | Query: {str(action_name)[:80]}...")
            return result
        except mysql.connector.Error as e:
            # Lỗi thuộc về MySQL (sai query, mất kết nối...)
            db_logger.error(f"DB ERROR | {func.__name__} | Code: {e.errno} - {e.msg} | Query: {str(action_name)[:150]}", exc_info=True)
            st.error("Hệ thống đang gặp sự cố truy xuất dữ liệu. Vui lòng thử lại sau.")
            return pd.DataFrame() if func.__name__ == 'run_query' else (False if func.__name__ == 'run_exec' else (False, None, ""))
        except Exception as e:
            # Các lỗi logic khác của Python
            app_logger.error(f"APP ERROR | {func.__name__} | {str(e)} | Query: {str(action_name)[:150]}", exc_info=True)
            st.error("Đã xảy ra lỗi hệ thống không mong muốn.")
            return pd.DataFrame() if func.__name__ == 'run_query' else (False if func.__name__ == 'run_exec' else (False, None, ""))
    return wrapper

# ── AuthManager singleton — giữ trạng thái lockout xuyên rerun ──
from auth import AuthManager

@st.cache_resource
def get_auth_manager():
    """
    Tạo 1 instance AuthManager dùng chung cho toàn bộ session Streamlit.
    @st.cache_resource đảm bảo _fail_count và _lockout không bị reset
    sau mỗi lần Streamlit rerun (mỗi lần user click button).
    """
    # AuthManager dùng connect() trực tiếp, tự lọc bỏ pool keys
    return AuthManager(DB_CONFIG)


@db_action_logger
def run_query(sql: str, params=None) -> pd.DataFrame:
    conn = get_conn()
    try:
        conn.rollback() # Ép tải dữ liệu mới nhất (Fix lỗi bóng ma)
        df = pd.read_sql(sql, conn, params=params)
        return df
    finally:
        if 'conn' in locals() and conn.is_connected():
            conn.close()

@db_action_logger
def run_exec(sql: str, params=None) -> bool:
    conn = get_conn()
    try:
        cur = conn.cursor()
        cur.execute(sql, params or ())
        conn.commit()
        return True
    finally:
        if 'cur' in locals(): cur.close()
        if 'conn' in locals() and conn.is_connected(): conn.close()

@db_action_logger
def call_sp(proc: str, in_args: list, out_count: int = 0):
    conn = get_conn()
    try:
        cur = conn.cursor()
        if out_count == 0:
            cur.execute(f"CALL {proc}({','.join(['%s']*len(in_args))})", in_args)
            conn.commit()
            try:
                while cur.nextset(): pass
            except Exception: pass
            return True, None, ""

        out_vars = [f"@out{i}" for i in range(out_count)]
        all_ph   = ",".join(["%s"] * len(in_args) + out_vars)
        cur.execute(f"CALL {proc}({all_ph})", in_args)
        conn.commit()
        
        try:
            while cur.nextset(): pass
        except Exception: pass
        
        cur.execute("SELECT " + ", ".join(out_vars))
        row = cur.fetchone()
        return True, row, ""
    finally:
        if 'cur' in locals(): cur.close()
        if 'conn' in locals() and conn.is_connected(): conn.close()
def render_delivery_timeline(delivery_id: int):
    # 1. Lấy thông tin chuyến giao & tài xế
    d_info = run_query("""
        SELECT d.DriverName, d.DriverPhone, d.Status, d.ScheduledDate, v.LicensePlate
        FROM Deliveries d JOIN Vehicles v ON d.VehicleID = v.VehicleID
        WHERE d.DeliveryID = %s""", (delivery_id,))
    
    if d_info.empty:
        st.warning("Không tìm thấy thông tin hành trình cho DeliveryID này.")
        return

    d = d_info.iloc[0]
    
    # 2. Lấy các nỗ lực giao hàng (Attempts)
    attempts = run_query("""
        SELECT AttemptNumber, AttemptTime, FailureReason, Notes 
        FROM DeliveryAttempts WHERE DeliveryID = %s ORDER BY AttemptTime ASC""", (delivery_id,))
    
    # 3. Lấy lịch sử đổi lịch (Rescheduled)
    reschedules = run_query("""
        SELECT CreatedAt, OldScheduledDate, NewScheduledDate, Reason, Notes
        FROM DeliveryRescheduled WHERE OriginalDeliveryID = %s ORDER BY CreatedAt ASC""", (delivery_id,))

    st.markdown(f"#### Hành trình chuyến giao #{delivery_id}")
    st.caption(f"Tài xế: **{d['DriverName']}** ({d['DriverPhone']}) | Xe: **{d['LicensePlate']}**")
    
    timeline_html = '<div class="timeline">'
    
    # Sự kiện bắt đầu: Phân công
    timeline_html += f"""
    <div class="timeline-item">
        <div class="timeline-date">{d['ScheduledDate']}</div>
        <div class="timeline-content">
            <span class="status-badge" style="background:#0ea5e9">PHÂN CÔNG</span><br>
            Khởi tạo chuyến giao, dự kiến ngày <b>{d['ScheduledDate']}</b>
        </div>
    </div>"""

    # Duyệt qua các lần thất bại/đổi lịch
    for _, row in attempts.iterrows():
        timeline_html += f"""
        <div class="timeline-item">
            <div class="timeline-date">{row['AttemptTime']}</div>
            <div class="timeline-content">
                <span class="status-badge" style="background:#ef4444">THẤT BẠI LẦN {row['AttemptNumber']}</span><br>
                Lý do: <b>{row['FailureReason']}</b>. {row['Notes'] or ''}
            </div>
        </div>"""

    for _, row in reschedules.iterrows():
        timeline_html += f"""
        <div class="timeline-item">
            <div class="timeline-date">{row['CreatedAt']}</div>
            <div class="timeline-content">
                <span class="status-badge" style="background:#f59e0b">ĐỔI LỊCH</span><br>
                Dời từ <b>{row['OldScheduledDate']}</b> sang <b>{row['NewScheduledDate']}</b>. 
                Lý do: {row['Reason']}
            </div>
        </div>"""

    # Sự kiện cuối: Trạng thái hiện tại
    status_color = "#10b981" if d['Status'] == 'completed' else "#6366f1"
    timeline_html += f"""
    <div class="timeline-item">
        <div class="timeline-date">Hiện trạng</div>
        <div class="timeline-content" style="border-left: 4px solid {status_color}">
            <span class="status-badge" style="background:{status_color}">{d['Status'].upper()}</span><br>
            Trạng thái hiện tại của chuyến giao hàng.
        </div>
    </div>"""
    
    timeline_html += '</div>'
    st.markdown(timeline_html, unsafe_allow_html=True)
# ══════════════════════════════════════════════════════════
# AUTH
# ══════════════════════════════════════════════════════════
def do_login(username: str, password: str):
    """
    Delegate sang AuthManager (auth.py) để có đầy đủ:
      - bcrypt verify
      - đếm số lần sai
      - khoá tài khoản sau MAX_ATTEMPTS lần sai (15 phút)
      - audit log: LOGIN_OK / LOGIN_FAIL / ACCOUNT_LOCKED / LOGIN_BLOCKED

    Returns:
        (user_dict, "")    nếu thành công
        (None, error_msg)  nếu thất bại — error_msg đã localize (vd: 'Còn 3 lần thử')
    """
    auth = get_auth_manager()
    session, err = auth.login(username, password)
    if session:
        return {
            "Username": session.username,
            "FullName": session.full_name,
            "Role":     session.role,
            "UserID":   session.user_id,
            "Email":    session.email,
        }, ""
    return None, err


def can(section: str) -> bool:
    return section in ROLE_PERMS.get(st.session_state.get("role", ""), set())


def require_auth():
    if "user" not in st.session_state:
        show_login_page()
        st.stop()


# ══════════════════════════════════════════════════════════
# NOTIFICATION helper
# ══════════════════════════════════════════════════════════
def show_notify(icon: str, title: str, body: str, kind: str = "info"):
    colors = {"success":"#10b981","warning":"#f59e0b",
               "error":"#ef4444","info":"#00d4aa"}
    c = colors.get(kind, "#00d4aa")
    st.markdown(f"""
<div class="notify-box" style="border-color:{c}">
<b style="color:{c}">{icon} {title}</b><br><br>
{body.replace(chr(10), "<br>")}
<br><small style="color:#64748b">
★ Thong bao gia lap SMS/Email. Thuc te: SMTP / Twilio API.</small>
</div>""", unsafe_allow_html=True)


def make_notify_body(event: str, data: dict) -> tuple:
    oid  = data.get("order_id","")
    name = data.get("customer_name","Quy khach")
    templates = {
        "assigned": (
            "", f"Don #{oid} — Tim tai xe",
            f"Kinh gui {name},\nDon hang #{oid} da duoc phan cong.\n"
            f"Tai xe: {data.get('driver','N/A')} | Ngay giao: {data.get('date','')}\n"
            f"Trang thai: Tim tai xe -> Dang di giao."
        ),
        "rescheduled": (
            "", f"Len lich lai don #{oid}",
            f"Kinh gui {name},\nDon #{oid} chua giao duoc do: {data.get('reason','')}\n"
            f"He thong da len lich lai: {data.get('new_time','')}\n"
            f"Gio giao: {SLOT_LABELS.get(data.get('slot','anytime'),'Bat ky')}"
        ),
        "delivered": (
            "", f"Don #{oid} giao thanh cong!",
            f"Kinh gui {name},\nDon hang #{oid} da duoc giao thanh cong!\n"
            f"Thoi gian: {data.get('time', datetime.datetime.now().strftime('%d/%m/%Y %H:%M'))}"
        ),
        "escalated": (
            "", f"Don #{oid} can xu ly",
            f"Kinh gui {name},\nDon #{oid} gap su co: {data.get('reason','')}\n"
            f"Bo phan CSKH se lien he trong 24h."
        ),
    }
    return templates.get(event, ("","Thong bao",str(data)))


# ══════════════════════════════════════════════════════════
# LOGIN PAGE
# ══════════════════════════════════════════════════════════
def show_login_page():
    _, mid, _ = st.columns([1,1.2,1])
    with mid:
        st.markdown("""
<div style="text-align:center;margin-bottom:24px">
  <div style="font-size:52px"></div>
  <h2 style="color:#00d4aa;font-weight:700;letter-spacing:2px;margin:4px 0">
    FINAL PROJECT</h2>
  <p style="color:#64748b;margin:0">Delivery Management System — DSEB66B · NEU</p>
</div>""", unsafe_allow_html=True)

        username = st.text_input("Tên đăng nhập", placeholder="admin",
                                  key="login_username")
        password = st.text_input("Mật khẩu", type="password",
                                  placeholder="••••••••", key="login_password")

        if st.button(" ĐĂNG NHẬP", use_container_width=True, type="primary"):
            if not username or not password:
                st.error("Vui lòng nhập đầy đủ.")
            else:
                with st.spinner("Đang xác thực..."):
                    user, err = do_login(username.strip(), password)
                if user:
                    st.session_state.update({
                        "user":      user["Username"],
                        "full_name": user["FullName"],
                        "role":      user["Role"],
                        "uid":       int(user["UserID"]),
                        "page":      "dashboard",
                    })
                    st.rerun()
                else:
                    # err có thể là:
                    #   - "Sai tên đăng nhập hoặc mật khẩu."
                    #   - "Sai mật khẩu. Còn N lần thử."
                    #   - "Tài khoản bị khóa 15 phút do nhập sai nhiều lần."
                    #   - "Tài khoản tạm khóa. Thử lại sau N phút."
                    st.error(err or "Đăng nhập thất bại.")

        st.markdown("""
<div style="background:#161923;border:1px solid #2a3050;border-radius:8px;
padding:12px;margin-top:14px;font-family:monospace;font-size:11px;color:#64748b">
<b style="color:#94a3b8">Tài khoản mặc định:</b><br>
admin &nbsp;&nbsp;&nbsp;&nbsp;/ Admin@123 &nbsp;→ Quản lý<br>
dispatcher1 / Dispatch@1 → Điều phối<br>
accountant1 / Account@1 → Kế toán
</div>""", unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════
# SIDEBAR
# ══════════════════════════════════════════════════════════
def show_sidebar():
    with st.sidebar:
        st.markdown(f"""
<div style="text-align:center;padding:10px 0 14px;
     border-bottom:1px solid #2a3050;margin-bottom:10px">
  <div style="font-size:28px"></div>
  <div style="color:#00d4aa;font-weight:700;font-size:13px;
       letter-spacing:1.5px">DELIVERY MS</div>
  <div style="color:#64748b;font-size:10px">DSEB66B NEU</div>
</div>
<div style="background:#1e2336;border-radius:8px;padding:10px 12px;
     margin-bottom:10px;border:1px solid #2a3050">
  <div style="font-weight:600;font-size:13px">
    {st.session_state.get("full_name","")}</div>
  <div style="color:#00d4aa;font-size:11px;font-family:monospace">
    {st.session_state.get("role","")}</div>
</div>""", unsafe_allow_html=True)

        pages = [
            ("","Dashboard",         "dashboard",  True),
            ("","Khách hàng",        "customers",  can("customers")),
            ("","Đơn hàng",          "orders",     can("orders")),
            ("","Giao hàng",         "deliveries", can("deliveries")),
            ("","Phương tiện",       "vehicles",   can("vehicles")),
            ("","Chi phí",           "expenses",   can("expenses")),
            ("","Báo cáo",           "reports",    can("reports")),
            ("","Vấn đề đơn hàng",  "issues",     can("issues")),
            ("","Audit Log",         "audit_log",  can("audit_log")),
        ]

        current = st.session_state.get("page","dashboard")
        for icon, label, key, visible in pages:
            if not visible:
                continue
            btn_type = "primary" if current == key else "secondary"
            if st.button(f"{icon} {label}", key=f"nav_{key}",
                         use_container_width=True, type=btn_type):
                st.session_state["page"] = key
                st.rerun()

        st.markdown("---")
        if st.button("⏻ Đăng xuất", use_container_width=True):
            _username = st.session_state.get("user", "unknown")
            _role     = st.session_state.get("role", "unknown")
            audit_logger.info(f"LOGOUT | user={_username} | role={_role}")
            for k in list(st.session_state.keys()):
                del st.session_state[k]
            st.rerun()

        st.markdown(
            f"<div style='text-align:center;color:#2a3050;font-size:10px'>"
            f"{datetime.datetime.now().strftime('%d/%m/%Y %H:%M')}</div>",
            unsafe_allow_html=True
        )


# ══════════════════════════════════════════════════════════
# DASHBOARD
# ══════════════════════════════════════════════════════════
def page_dashboard():
    st.header("Dashboard")

    total   = run_query("SELECT COUNT(*) AS n FROM Orders").iloc[0]["n"]
    pending = run_query("SELECT COUNT(*) AS n FROM Orders WHERE Status='pending'").iloc[0]["n"]
    today   = run_query("SELECT COUNT(*) AS n FROM Deliveries WHERE ScheduledDate=CURDATE()").iloc[0]["n"]
    fails   = run_query("SELECT COUNT(*) AS n FROM DeliveryAttempts").iloc[0]["n"]
    at_risk = run_query("SELECT COUNT(*) AS n FROM vw_at_risk_deliveries").iloc[0]["n"]

    if "dash_view" not in st.session_state:
        st.session_state["dash_view"] = "all"

    CARDS = [
        ("all",     "", "Tổng đơn",       total,   "#00d4aa"),
        ("pending", "", "Chờ xử lý",      pending, "#f59e0b"),
        ("today",   "", "Giao hôm nay",   today,   "#10b981"),
        ("fail",    "", "Lần thất bại",   fails,   "#ef4444"),
        ("risk",    "","Đơn rủi ro cao", at_risk, "#7c3aed"),
    ]

    cols = st.columns(5)
    for col, (key, icon, label, value, color) in zip(cols, CARDS):
        active = st.session_state["dash_view"] == key
        border = color if active else "#2a3050"
        bg     = (f"rgba({int(color[1:3],16)},{int(color[3:5],16)},"
                  f"{int(color[5:7],16)},0.10)") if active else "#1e2336"
        with col:
            st.markdown(f"""
<div style="background:{bg};border:2px solid {border};border-radius:12px;
     padding:16px 12px;text-align:center">
  <div style="font-size:24px">{icon}</div>
  <div style="font-size:26px;font-weight:700;color:{color};
       font-family:monospace;line-height:1.1">{value}</div>
  <div style="font-size:10px;color:#94a3b8;margin-top:4px;
       text-transform:uppercase;letter-spacing:.5px">{label}</div>
</div>""", unsafe_allow_html=True)
            if st.button(f"__{label}__", key=f"card_{key}",
                         use_container_width=True, help=f"Xem {label}"):
                st.session_state["dash_view"] = key
                st.rerun()

    st.divider()

    view = st.session_state["dash_view"]

    if view == "all":
        st.markdown("##### Tất cả đơn hàng gần đây")
        df = run_query("""
            SELECT o.OrderID, c.CustomerName, o.RecipientName,
                   o.Status, FORMAT(o.DeclaredValueVND,0) AS GiaTri,
                   DATE(o.OrderDate) AS NgayDat
            FROM Orders o JOIN Customers c ON o.CustomerID=c.CustomerID
            ORDER BY o.OrderDate DESC LIMIT 30""")
        st.dataframe(df, use_container_width=True, hide_index=True)

    elif view == "pending":
        st.markdown("##### Đơn chờ xử lý (vw_outstanding_orders)")
        # Dùng View vw_outstanding_orders — hide JOIN complexity,
        # auto compute HoursRemaining từ DeadlineDate
        df2 = run_query("""
            SELECT OrderID, CustomerName, RecipientName,
                   DeliveryAddress, DeadlineDate, HoursRemaining,
                   IsFragile, IsHighValue, Status
            FROM   vw_outstanding_orders
            WHERE  Status = 'pending'
            ORDER  BY DeadlineDate ASC
            LIMIT  30""")
        if df2.empty:
            st.success("Không có đơn chờ xử lý!")
        else:
            st.dataframe(df2, use_container_width=True, hide_index=True)

    elif view == "today":
        st.markdown("##### Chuyến giao hôm nay")
        df3 = run_query("""
            SELECT d.DeliveryID, o.OrderID, c.CustomerName,
                   o.RecipientName, d.Status,
                   d.ScheduledDate, d.DriverName
            FROM Deliveries d
            JOIN Orders    o ON d.OrderID=o.OrderID
            JOIN Customers c ON o.CustomerID=c.CustomerID
            WHERE d.ScheduledDate=CURDATE()
            ORDER BY d.DeliveryID DESC""")
        if df3.empty:
            st.info("Không có chuyến giao nào hôm nay.")
        else:
            st.dataframe(df3, use_container_width=True, hide_index=True)

    elif view == "fail":
        st.markdown("##### Tổng hợp giao thất bại (vw_failed_attempts_summary)")
        # Dùng View vw_failed_attempts_summary —
        # gom nhóm theo DeliveryID, thay vì list từng attempt
        df_summary = run_query("""
            SELECT DeliveryID, OrderID, RecipientName, RecipientPhone,
                   DeliveryAddress, TotalAttempts, LastAttemptNumber,
                   LastAttemptTime, LastFailureReason, NextScheduled
            FROM   vw_failed_attempts_summary
            ORDER  BY LastAttemptTime DESC
            LIMIT  20""")
        if df_summary.empty:
            st.success("Không có chuyến giao nào thất bại!")
        else:
            st.dataframe(df_summary, use_container_width=True, hide_index=True)

            # Bổ sung danh sách raw attempts mới nhất để tra cứu chi tiết
            with st.expander("Chi tiết từng lần thất bại (DeliveryAttempts)"):
                df4 = run_query("""
                    SELECT da.DeliveryID, da.AttemptNumber, da.AttemptTime,
                           da.FailureReason, da.ContactAttempted,
                           da.NextAttemptScheduled
                    FROM DeliveryAttempts da
                    ORDER BY da.AttemptTime DESC LIMIT 30""")
                st.dataframe(df4, use_container_width=True, hide_index=True)

    elif view == "risk":
        st.markdown("##### Đơn hàng rủi ro cao")
        st.caption("Đơn có ≥2 lần thất bại, sắp hết deadline, hoặc dễ vỡ + giá trị cao.")
        df_risk = run_query("SELECT * FROM vw_at_risk_deliveries LIMIT 20")
        if df_risk.empty:
            st.success("Không có đơn hàng rủi ro cao!")
        else:
            st.dataframe(df_risk, use_container_width=True, hide_index=True)


# ══════════════════════════════════════════════════════════
# ISSUES — [F2] + [F3] PATCHED
# ══════════════════════════════════════════════════════════
def page_issues():
    st.header("Vấn đề đơn hàng")

    # ── [F3] Load data vào session_state, không reload trang sau khi resolve ──
    # Chi reload khi bam nut "Lam moi" hoac lan dau vao trang
    if "issues_data" not in st.session_state:
        st.session_state["issues_data"] = None

    col_refresh, col_info = st.columns([1, 4])
    with col_refresh:
        if st.button("Làm mới dữ liệu", use_container_width=True):
            st.session_state["issues_data"] = None   # force reload

    # Fetch data once, store in session_state
    if st.session_state["issues_data"] is None:
        st.session_state["issues_data"] = run_query("""
            SELECT oi.IssueID, oi.OrderID, c.CustomerName,
                   oi.IssueType, oi.Severity, oi.ReportedBy,
                   oi.Description, oi.Resolution, oi.ResolutionNotes,
                   DATE(oi.ReportedAt)  AS NgayBaoCao,
                   DATE(oi.ResolvedAt)  AS NgayGiaiQuyet
            FROM OrderIssues oi
            JOIN Orders    o ON oi.OrderID   = o.OrderID
            JOIN Customers c ON o.CustomerID = c.CustomerID
            ORDER BY
                FIELD(oi.Severity,'critical','high','medium','low'),
                oi.ReportedAt DESC""")

    df = st.session_state["issues_data"]

    # ── Dùng placeholder cục bộ thay vì rerun toàn trang ──
    pending_ph  = st.empty()
    resolved_ph = st.empty()

    def _render_tables(dataframe):
        """Render pending và resolved tables vào 2 placeholders."""
        df_pending  = dataframe[dataframe["Resolution"] == "pending"]
        df_resolved = dataframe[dataframe["Resolution"] != "pending"]

        with pending_ph.container():
            st.subheader("Các vấn đề CHƯA XỬ LÝ")
            if not df_pending.empty:
                st.error(f"⚠️ Có {len(df_pending)} vấn đề đang chờ giải quyết!")
                st.dataframe(
                    df_pending.drop(columns=["ResolutionNotes","NgayGiaiQuyet"],
                                    errors="ignore"),
                    use_container_width=True, hide_index=True)
            else:
                st.success("Không có sự cố nào tồn đọng.")

        with resolved_ph.container():
            st.subheader("Lịch sử ĐÃ XỬ LÝ")
            if not df_resolved.empty:
                st.dataframe(df_resolved,
                             use_container_width=True, hide_index=True)
            else:
                st.info("Chưa có lịch sử giải quyết sự cố.")

    _render_tables(df)

    st.divider()

    # ── Form giải quyết — gọi sp_resolve_issue (ACID transaction) ──
    st.subheader("Giải quyết vấn đề")
    st.caption("Hệ thống dùng Stored Procedure sp_resolve_issue — "
               "đảm bảo tính ACID (Atomicity/Consistency).")

    msg_ph = st.empty()   # placeholder cho thông báo, tránh rerun

    with st.form("resolve_form"):
        iid = st.number_input("IssueID cần xử lý", min_value=1, step=1)
        res_map = {
            "resend":         "Gửi lại hàng mới",
            "refund":         "Hoàn tiền toàn phần",
            "partial_refund": "Hoàn tiền một phần",
            "reinspect":      "Kiểm tra lại",
            "dismissed":      "Bác bỏ khiếu nại",
        }
        resolution = st.selectbox("Hình thức xử lý", list(res_map.keys()),
                                   format_func=lambda x: res_map[x])
        r_notes = st.text_input("Ghi chú xử lý")
        sub = st.form_submit_button("✅ Xác nhận xử lý", use_container_width=True)

    if sub:
        # Gọi SP 
        ok, res, err = call_sp(
            "sp_resolve_issue",
            [int(iid), resolution, r_notes or None],
            out_count=2
        )

        if ok and res and res[0] == "OK":
            msg_ph.success(f"{res[1]}")

            # Cập nhật session_state cục bộ, KHÔNG st.rerun()
            updated_df = run_query("""
                SELECT oi.IssueID, oi.OrderID, c.CustomerName,
                       oi.IssueType, oi.Severity, oi.ReportedBy,
                       oi.Description, oi.Resolution, oi.ResolutionNotes,
                       DATE(oi.ReportedAt)  AS NgayBaoCao,
                       DATE(oi.ResolvedAt)  AS NgayGiaiQuyet
                FROM OrderIssues oi
                JOIN Orders    o ON oi.OrderID   = o.OrderID
                JOIN Customers c ON o.CustomerID = c.CustomerID
                ORDER BY
                    FIELD(oi.Severity,'critical','high','medium','low'),
                    oi.ReportedAt DESC""")
            st.session_state["issues_data"] = updated_df
            # Re-render chỉ 2 bảng, không load lại toàn trang
            _render_tables(updated_df)

        elif ok and res:
            msg_ph.error(f"❌ SP trả về lỗi: {res[1]}")
        else:
            # Fallback: nếu SP chưa tồn tại, dùng UPDATE trực tiếp
            fb_ok = run_exec(
                """UPDATE OrderIssues
                   SET Resolution=%s, ResolutionNotes=%s, ResolvedAt=NOW()
                   WHERE IssueID=%s""",
                (resolution, r_notes or None, int(iid))
            )
            if fb_ok:
                msg_ph.success(f"Đã xử lý Issue #{int(iid)} (fallback mode).")
                # Cập nhật cục bộ không rerun
                updated_df = run_query("""
                    SELECT oi.IssueID, oi.OrderID, c.CustomerName,
                           oi.IssueType, oi.Severity, oi.ReportedBy,
                           oi.Description, oi.Resolution, oi.ResolutionNotes,
                           DATE(oi.ReportedAt) AS NgayBaoCao,
                           DATE(oi.ResolvedAt) AS NgayGiaiQuyet
                    FROM OrderIssues oi
                    JOIN Orders    o ON oi.OrderID=o.OrderID
                    JOIN Customers c ON o.CustomerID=c.CustomerID
                    ORDER BY FIELD(oi.Severity,'critical','high','medium','low'),
                             oi.ReportedAt DESC""")
                st.session_state["issues_data"] = updated_df
                _render_tables(updated_df)
            else:
                msg_ph.error(f"Lỗi: {err}")


# ══════════════════════════════════════════════════════════
# CUSTOMERS
# ══════════════════════════════════════════════════════════
def page_customers():
    st.header("Quản lý khách hàng")

    t1, t2, t3, t4, t5 = st.tabs([
        "Danh sách", "Thêm / Sửa / Xóa",
        "Chi tiết khách hàng", "Customer Intelligence",
        "Tuỳ chọn giao hàng (Preferences)"
    ])

    with t1:
        kw = st.text_input("Tìm theo tên / SĐT")
        sql_base = """
            SELECT c.CustomerID, c.CustomerName, c.PhoneNumber, c.Email,
                   c.District, c.City,
                   fn_customer_success_rate(c.CustomerID) AS SuccessRate,
                   fn_customer_risk_level(c.CustomerID)   AS RiskLevel
            FROM Customers c"""
        if kw:
            df = run_query(sql_base + " WHERE c.CustomerName LIKE %s OR c.PhoneNumber LIKE %s ORDER BY c.CustomerName",
                           (f"%{kw}%", f"%{kw}%"))
        else:
            df = run_query(sql_base + " ORDER BY c.CustomerName")

        if not df.empty:
            st.dataframe(df, use_container_width=True, hide_index=True)
            low = (df["RiskLevel"] == "low").sum()
            med = (df["RiskLevel"] == "medium").sum()
            hi  = (df["RiskLevel"].isin(["high","critical"])).sum()
            st.caption(f"Tổng: {len(df)} khách hàng  |  🟢 Low: {low}  |  🟡 Medium: {med}  |  🔴 High/Critical: {hi}")
        else:
            st.info("Không tìm thấy khách hàng nào.")

    if "cust_form_key" not in st.session_state:
        st.session_state["cust_form_key"] = 0

    with t2:
        edit_data = st.session_state.get("edit_cust", {})
        action    = "Cập nhật" if edit_data else "Thêm mới"

        if edit_data:
            st.info(f"Đang sửa: ID={edit_data.get('CustomerID')} — {edit_data.get('CustomerName','')}")

        with st.form(f"cust_form_{st.session_state['cust_form_key']}"):
            col1, col2 = st.columns(2)
            with col1:
                name     = st.text_input("Tên *",      value=edit_data.get("CustomerName",""))
                phone    = st.text_input("SĐT *",      value=edit_data.get("PhoneNumber",""))
                email    = st.text_input("Email",      value=edit_data.get("Email","") or "")
                ward     = st.text_input("Phường/Xã",  value=edit_data.get("Ward","") or "")
            with col2:
                addr     = st.text_input("Địa chỉ *",  value=edit_data.get("Address",""))
                district = st.text_input("Quận/Huyện", value=edit_data.get("District","") or "")
                city     = st.text_input("Thành phố",  value=edit_data.get("City","") or "")
            sub = st.form_submit_button(f"{action}", use_container_width=True)

        if sub:
            if not name or not phone or not addr:
                st.error("Điền đầy đủ trường bắt buộc (*)")
            elif edit_data:
                ok = run_exec(
                    """UPDATE Customers
                       SET CustomerName=%s, PhoneNumber=%s, Email=%s, Address=%s,
                           Ward=%s, District=%s, City=%s
                       WHERE CustomerID=%s""",
                    (name, phone, email or None, addr,
                     ward or None, district or None, city or None,
                     edit_data["CustomerID"])
                )
                if ok:
                    st.success(f"Đã cập nhật khách hàng ID={edit_data['CustomerID']}!")
                    st.session_state.pop("edit_cust", None)
                    st.session_state["cust_form_key"] += 1
                    st.rerun()
            else:
                try:
                    conn_ins = get_conn(); cur_ins = conn_ins.cursor()
                    cur_ins.execute(
                        """INSERT INTO Customers
                           (CustomerName, PhoneNumber, Email, Address, Ward, District, City)
                           VALUES (%s,%s,%s,%s,%s,%s,%s)""",
                        (name, phone, email or None, addr,
                         ward or None, district or None, city or None)
                    )
                    conn_ins.commit()
                    new_cid = cur_ins.lastrowid
                    cur_ins.close(); conn_ins.close()
                    st.session_state["cust_form_key"] += 1
                    st.session_state["new_customer_id"]    = new_cid
                    st.session_state["new_customer_name"]  = name
                    st.session_state["new_customer_phone"] = phone
                    st.session_state["new_customer_addr"]  = addr
                    st.rerun()
                except Exception as e:
                    st.error(f"Lỗi: {e}")

        if "new_customer_id" in st.session_state:
            new_cid   = st.session_state["new_customer_id"]
            new_name  = st.session_state.get("new_customer_name","")
            new_phone = st.session_state.get("new_customer_phone","")
            new_addr  = st.session_state.get("new_customer_addr","")

            st.success(f"Đã thêm khách hàng **{new_name}** (CustomerID = **{new_cid}**)")
            cats = run_query("SELECT CategoryID, CategoryName FROM OrderCategories")

            with st.form("quick_order_form"):
                qc1, qc2 = st.columns(2)
                with qc1:
                    cat_map   = {r.CategoryName: r.CategoryID for r in cats.itertuples()} if not cats.empty else {}
                    cat_sel   = st.selectbox("Danh mục *", list(cat_map.keys())) if cat_map else None
                    rec_name  = st.text_input("Người nhận *", value=new_name)
                    rec_phone = st.text_input("SĐT người nhận *", value=new_phone)
                    q_deadline = st.date_input("Deadline *",
                                               value=datetime.date.today() + datetime.timedelta(days=2))
                with qc2:
                    qaddr = st.text_input("Địa chỉ giao *", value=new_addr)
                    qval  = st.number_input("Giá trị hàng (VND)", min_value=0, step=10000)
                    qwt   = st.number_input("Trọng lượng (kg)", min_value=0.0, step=0.1)
                    qfrag = st.checkbox("Hàng dễ vỡ ")

                c_skip, c_save = st.columns([2,1])
                with c_save:
                    q_sub  = st.form_submit_button("💾 Thêm đơn hàng", use_container_width=True)
                with c_skip:
                    q_skip = st.form_submit_button("⏭ Bỏ qua", use_container_width=True)

            if q_sub:
                if not rec_name or not rec_phone or not qaddr:
                    st.error("Điền đầy đủ trường bắt buộc")
                else:
                    try:
                        # Deadline must be after today
                        deadline_dt = datetime.datetime.combine(
                            q_deadline, datetime.time(23, 59, 59))
                        conn_o = get_conn(); cur_o = conn_o.cursor()
                        cur_o.execute(
                            """INSERT INTO Orders
                               (CustomerID,CategoryID,RecipientName,RecipientPhone,
                                DeliveryAddress,DeclaredValueVND,WeightKg,
                                IsFragile,Status,DeadlineDate)
                               VALUES (%s,%s,%s,%s,%s,%s,%s,%s,'pending',%s)""",
                            (new_cid, cat_map[cat_sel], rec_name, rec_phone,
                             qaddr, int(qval), float(qwt),
                             1 if qfrag else 0, deadline_dt)
                        )
                        conn_o.commit()
                        new_oid = cur_o.lastrowid
                        cur_o.close(); conn_o.close()
                        st.success(f"Đã tạo đơn hàng! (OrderID = **{new_oid}**)")
                        time.sleep(2)
                        for k in ["new_customer_id","new_customer_name",
                                  "new_customer_phone","new_customer_addr"]:
                            st.session_state.pop(k, None)
                        st.rerun()
                    except Exception as e:
                        st.error(f"Lỗi thêm đơn: {e}")

            if q_skip:
                for k in ["new_customer_id","new_customer_name",
                          "new_customer_phone","new_customer_addr"]:
                    st.session_state.pop(k, None)
                st.rerun()

        st.divider()

        st.markdown("**Load khách hàng để sửa**")
        col_a, col_b = st.columns([2,1])
        with col_a:
            cid_edit = st.number_input("Nhập CustomerID cần sửa", min_value=1, step=1, key="edit_cid")
        with col_b:
            st.markdown("<br>", unsafe_allow_html=True)
            if st.button("Load để sửa", use_container_width=True):
                df_e = run_query("SELECT * FROM Customers WHERE CustomerID=%s", (cid_edit,))
                if not df_e.empty:
                    st.session_state["edit_cust"] = df_e.iloc[0].to_dict()
                    st.rerun()
                else:
                    st.error(f"Không tìm thấy CustomerID={cid_edit}")

        st.divider()
        st.markdown("**Xóa khách hàng**")
        st.warning("Chỉ xóa được khách hàng chưa có đơn hàng.")
        col_d1, col_d2 = st.columns([2,1])
        with col_d1:
            cid_del = st.number_input("CustomerID cần xóa", min_value=1, step=1, key="del_cid")
        with col_d2:
            st.markdown("<br>", unsafe_allow_html=True)
            del_btn = st.button("🗑 Xóa", key="del_cust_btn", type="primary", use_container_width=True)

        if del_btn:
            df_check = run_query("SELECT COUNT(*) AS cnt FROM Orders WHERE CustomerID=%s", (cid_del,))
            order_count = int(df_check.iloc[0]["cnt"]) if not df_check.empty else 0
            if order_count > 0:
                st.error(f"Không thể xóa! Khách hàng này có {order_count} đơn hàng.")
            else:
                df_exists = run_query("SELECT CustomerName FROM Customers WHERE CustomerID=%s", (cid_del,))
                if df_exists.empty:
                    st.error(f"Không tìm thấy CustomerID={cid_del}")
                else:
                    cust_name = df_exists.iloc[0]["CustomerName"]
                    if run_exec("DELETE FROM Customers WHERE CustomerID=%s", (cid_del,)):
                        st.success(f"Đã xóa '{cust_name}' (ID={cid_del}).")
                        time.sleep(1.5)
                        st.rerun()

    with t3:
        st.subheader("Toàn bộ đơn hàng của một khách hàng")
        col_inp, col_btn = st.columns([3,1])
        with col_inp:
            cid_input = st.number_input("Nhập CustomerID", min_value=1, step=1, key="cid_det")
        with col_btn:
            st.markdown("<br>", unsafe_allow_html=True)
            if st.button("Xem chi tiết", key="btn_det", use_container_width=True):
                df_c = run_query(
                    """SELECT c.*,
                              fn_customer_success_rate(c.CustomerID) AS SuccessRate,
                              fn_customer_risk_level(c.CustomerID)   AS RiskLevel
                       FROM Customers c WHERE c.CustomerID=%s""",
                    (cid_input,))
                if df_c.empty:
                    st.error("Không tìm thấy khách hàng.")
                    st.session_state.pop("detail_cid", None)
                else:
                    st.session_state["detail_cid"] = cid_input

        detail_cid = st.session_state.get("detail_cid")
        if detail_cid:
            df_c = run_query(
                """SELECT c.*,
                          fn_customer_success_rate(c.CustomerID) AS SuccessRate,
                          fn_customer_risk_level(c.CustomerID)   AS RiskLevel
                   FROM Customers c WHERE c.CustomerID=%s""",
                (detail_cid,))
            if not df_c.empty:
                cust = df_c.iloc[0]
                risk_label = {"low":"An toàn 🟢","medium":"Cần theo dõi 🟡",
                              "high":"Rủi ro cao 🔴","critical":"Khẩn cấp 🟣"}.get(
                               cust["RiskLevel"], cust["RiskLevel"])
                c1,c2,c3,c4 = st.columns([1.8,1,1,1])
                c1.metric("Khách hàng",         cust["CustomerName"])
                c2.metric("SĐT",                cust["PhoneNumber"])
                c3.metric("Tỉ lệ giao thành công", f"{cust['SuccessRate']}%")
                c4.metric("Mức độ rủi ro",      risk_label)

                df_orders = run_query("""
                    SELECT o.OrderID, DATE(o.OrderDate) AS NgayDat,
                           o.Status AS TrangThaiDon, oc.CategoryName,
                           FORMAT(o.DeclaredValueVND,0) AS GiaTri,
                           o.IsFragile, o.IsHighValue,
                           d.DeliveryID, d.DriverName,
                           d.Status AS TrangThaiGiao, d.ScheduledDate,
                           COUNT(da.AttemptID) AS LanThatBai,
                           COUNT(oi.IssueID)   AS SoVanDe
                    FROM Orders o
                    JOIN OrderCategories oc ON o.CategoryID=oc.CategoryID
                    LEFT JOIN Deliveries       d  ON o.OrderID    = d.OrderID
                    LEFT JOIN DeliveryAttempts da ON d.DeliveryID = da.DeliveryID
                    LEFT JOIN OrderIssues      oi ON o.OrderID    = oi.OrderID
                    WHERE o.CustomerID=%s
                    GROUP BY o.OrderID,o.OrderDate,o.Status,oc.CategoryName,
                             o.DeclaredValueVND,o.IsFragile,o.IsHighValue,
                             d.DeliveryID,d.DriverName,d.Status,d.ScheduledDate
                    ORDER BY o.OrderDate DESC""", (detail_cid,))

                if not df_orders.empty:
                    st.dataframe(df_orders, use_container_width=True, hide_index=True)
                    sc = df_orders["TrangThaiDon"].value_counts().reset_index()
                    sc.columns = ["Status","Count"]
                    fig = px.pie(sc, values="Count", names="Status", hole=0.55,
                                 title=f"Phân bổ trạng thái — {cust['CustomerName']}")
                    fig.update_layout(paper_bgcolor="rgba(0,0,0,0)", font_color="#c8d3f5")
                    st.plotly_chart(fig, use_container_width=True)
                else:
                    st.info("Khách hàng này chưa có đơn hàng nào.")

    with t4:
        st.subheader("Customer Risk & Performance Analysis")
        
        df_cust_risk = run_query("""
            SELECT 
                c.CustomerID,
                c.CustomerName,
                COUNT(DISTINCT o.OrderID) AS TotalOrders,
                SUM(o.Status='delivered') AS DeliveredOrders,
                SUM(o.Status='failed') AS FailedOrders,
                COUNT(DISTINCT da.AttemptID) AS TotalAttempts,
                ROUND(COALESCE(SUM(o.DeclaredValueVND),0)/1e6, 2) AS TotalValueM,
                fn_customer_risk_level(c.CustomerID) AS RiskLevel,
                fn_customer_success_rate(c.CustomerID) AS SuccessRate
            FROM Customers c
            LEFT JOIN Orders o ON c.CustomerID = o.CustomerID
            LEFT JOIN Deliveries d ON o.OrderID = d.OrderID
            LEFT JOIN DeliveryAttempts da ON d.DeliveryID = da.DeliveryID
            GROUP BY c.CustomerID, c.CustomerName
            HAVING TotalOrders > 0
            ORDER BY RiskLevel DESC, FailedOrders DESC
        """)
        
        if not df_cust_risk.empty:
            col_pie, col_metric = st.columns([2, 2])
            
            with col_pie:
                risk_counts = df_cust_risk['RiskLevel'].value_counts()
                try:
                    fig_risk = px.pie(
                        names=risk_counts.index,
                        values=risk_counts.values,
                        title="Customer Risk Distribution",
                        color_discrete_map={
                            "critical": "#ef4444",
                            "high": "#f97316", 
                            "medium": "#f59e0b",
                            "low": "#10b981"
                        }
                    )
                    fig_risk.update_layout(
                        paper_bgcolor="rgba(0,0,0,0)",
                        font_color="#c8d3f5"
                    )
                    st.plotly_chart(fig_risk, use_container_width=True)
                except Exception as e:
                    st.warning(f"Risk chart: {e}")
            
            with col_metric:
                total_custs = len(df_cust_risk)
                avg_success = df_cust_risk['SuccessRate'].mean()
                high_risk_count = len(df_cust_risk[df_cust_risk['RiskLevel'].isin(['high', 'critical'])])
                
                st.metric("Total Customers (with orders)", f"{total_custs:,}")
                st.metric("Avg Success Rate", f"{avg_success:.1f}%")
                st.metric("⚠️ High/Critical Risk", f"{high_risk_count}")
            
            st.divider()
            st.subheader("Customer Performance Matrix")
            st.caption("Bubble size = Total Order Value (Triệu VND) | Color = Risk Level")
            try:
                fig_scatter = px.scatter(
                    df_cust_risk,
                    x='TotalOrders',
                    y='SuccessRate',
                    size='TotalValueM',
                    color='RiskLevel',
                    hover_name='CustomerName',
                    hover_data={'TotalOrders': True, 'SuccessRate': ':.1f', 'RiskLevel': True},
                    title="Performance Matrix: Order Frequency vs Success Rate",
                    color_discrete_map={
                        "critical": "#ef4444",
                        "high": "#f97316",
                        "medium": "#f59e0b",
                        "low": "#10b981"
                    },
                    size_max=50
                )
                fig_scatter.update_layout(
                    paper_bgcolor="rgba(0,0,0,0)",
                    plot_bgcolor="rgba(0,0,0,0)",
                    font_color="#c8d3f5",
                    xaxis_title="Total Orders",
                    yaxis_title="Success Rate (%)"
                )
                st.plotly_chart(fig_scatter, use_container_width=True)
            except Exception as e:
                st.warning(f"Performance chart: {e}")
            
            st.divider()
            st.subheader("⚠️ Customers Needing Attention (High/Critical Risk)")
            high_risk_custs = df_cust_risk[df_cust_risk['RiskLevel'].isin(['high', 'critical'])].sort_values('FailedOrders', ascending=False)
            
            if not high_risk_custs.empty:
                st.dataframe(high_risk_custs[['CustomerName', 'TotalOrders', 'DeliveredOrders', 'FailedOrders', 'TotalAttempts', 'TotalValueM', 'RiskLevel', 'SuccessRate']], 
                           use_container_width=True, hide_index=True)
            else:
                st.success("✅ Không có khách hàng nào ở mức risk cao/khẩn cấp!")
            
            st.divider()
            st.subheader("📊 Toàn bộ Customer Summary")
            st.dataframe(df_cust_risk.sort_values('RiskLevel'), use_container_width=True, hide_index=True)
        else:
            st.info("Chưa có dữ liệu khách hàng có đơn hàng. Hãy tạo dữ liệu mẫu và cấu trúc order/delivery để phân tích.")

    # ── TAB 5: CustomerPreferences — giờ giao ưa thích, blackout window ──
    # Bảng CustomerPreferences nuôi sp_smart_reschedule (chọn khung giờ retry)
    with t5:
        st.subheader("Tuỳ chọn giao hàng theo khách hàng (CustomerPreferences)")
        st.caption("Khi sp_smart_reschedule lên lịch lại đơn thất bại, "
                   "nó đọc PreferredTimeSlot từ bảng này để đặt giờ giao kế tiếp.")

        # Danh sách preferences hiện có
        df_pref = run_query("""
            SELECT cp.PreferenceID, cp.CustomerID, c.CustomerName,
                   cp.PreferredTimeSlot, cp.BlackoutStart, cp.BlackoutEnd,
                   cp.ContactMethod, cp.MaxDailyAttempts,
                   cp.SpecialNotes, cp.UpdatedAt
            FROM   CustomerPreferences cp
            JOIN   Customers c ON cp.CustomerID = c.CustomerID
            ORDER  BY cp.UpdatedAt DESC
            LIMIT  100""")
        if not df_pref.empty:
            st.dataframe(df_pref, use_container_width=True, hide_index=True)
        else:
            st.info("Chưa có preference nào.")

        st.divider()

        # Form thêm mới / cập nhật preference
        st.markdown("**Thêm / Cập nhật preference cho 1 khách hàng**")
        st.caption("Bảng có UNIQUE(CustomerID): nếu CustomerID đã tồn tại → UPSERT (cập nhật).")

        custs_for_pref = run_query(
            "SELECT CustomerID, CustomerName, PhoneNumber FROM Customers ORDER BY CustomerName")

        if "pref_form_key" not in st.session_state:
            st.session_state["pref_form_key"] = 0

        pref_sub = False
        sel_cust = None

        with st.form(f"pref_form_{st.session_state['pref_form_key']}"):
            if custs_for_pref.empty:
                st.warning("Chưa có khách hàng nào — thêm khách hàng trước.")
                st.form_submit_button("Lưu", disabled=True)
            else:
                pref_cust_map = {
                    f"#{r.CustomerID} - {r.CustomerName} ({r.PhoneNumber})": r.CustomerID
                    for r in custs_for_pref.itertuples()
                }
                pc1, pc2 = st.columns(2)
                with pc1:
                    sel_cust = st.selectbox("Khách hàng *", list(pref_cust_map.keys()))
                    pref_slot = st.selectbox(
                        "Khung giờ ưa thích *",
                        ["anytime", "morning", "afternoon", "evening"],
                        format_func=lambda x: SLOT_LABELS.get(x, x)
                    )
                    pref_contact = st.selectbox(
                        "Phương thức liên hệ *",
                        ["any", "call", "sms", "email"]
                    )
                    pref_max_att = st.number_input(
                        "Số lần thử tối đa/ngày",
                        min_value=1, max_value=5, value=3, step=1
                    )
                with pc2:
                    pref_bs = st.time_input(
                        "Không làm phiền từ (BlackoutStart)",
                        value=None
                    )
                    pref_be = st.time_input(
                        "Đến (BlackoutEnd)",
                        value=None
                    )
                    pref_notes = st.text_area(
                        "Ghi chú đặc biệt",
                        height=100,
                        placeholder="VD: Chỉ giao khi có người nhà, gọi 30p trước..."
                    )

                pref_sub = st.form_submit_button(
                    "Lưu preference (UPSERT)",
                    type="primary",
                    use_container_width=True
                )

        if pref_sub and sel_cust is not None and not custs_for_pref.empty:
            try:
                conn_p = get_conn()
                cur_p  = conn_p.cursor()
                # UPSERT: nếu CustomerID đã có row → update
                cur_p.execute(
                    """INSERT INTO CustomerPreferences
                       (CustomerID, PreferredTimeSlot, BlackoutStart, BlackoutEnd,
                        ContactMethod, MaxDailyAttempts, SpecialNotes)
                       VALUES (%s,%s,%s,%s,%s,%s,%s)
                       ON DUPLICATE KEY UPDATE
                           PreferredTimeSlot = VALUES(PreferredTimeSlot),
                           BlackoutStart     = VALUES(BlackoutStart),
                           BlackoutEnd       = VALUES(BlackoutEnd),
                           ContactMethod     = VALUES(ContactMethod),
                           MaxDailyAttempts  = VALUES(MaxDailyAttempts),
                           SpecialNotes      = VALUES(SpecialNotes)""",
                    (pref_cust_map[sel_cust],
                     pref_slot,
                     pref_bs.strftime("%H:%M:%S") if pref_bs else None,
                     pref_be.strftime("%H:%M:%S") if pref_be else None,
                     pref_contact,
                     int(pref_max_att),
                     pref_notes or None)
                )
                conn_p.commit()
                cur_p.close()
                conn_p.close()
                st.session_state["pref_form_key"] += 1
                st.success(f"Đã lưu preference cho CustomerID = {pref_cust_map[sel_cust]}")
                time.sleep(1.5)
                st.rerun()
            except Exception as e:
                st.error(f"Lỗi lưu preference: {e}")

        st.divider()

        # Xoá preference (CASCADE đã có khi xoá Customers; tại đây chỉ xoá pref)
        st.markdown("**Xoá preference**")
        cd1, cd2 = st.columns([2, 1])
        with cd1:
            del_pref_cid = st.number_input(
                "CustomerID có preference cần xoá",
                min_value=1, step=1, key="del_pref_cid"
            )
        with cd2:
            st.markdown("<br>", unsafe_allow_html=True)
            if st.button("Xoá preference", type="secondary", use_container_width=True):
                if run_exec(
                    "DELETE FROM CustomerPreferences WHERE CustomerID=%s",
                    (del_pref_cid,)
                ):
                    st.success(f"Đã xoá preference của CustomerID = {del_pref_cid}")
                    time.sleep(1.5)
                    st.rerun()


# ══════════════════════════════════════════════════════════
# ORDERS
# ══════════════════════════════════════════════════════════
def page_orders():
    st.header("Quản lý đơn hàng")

    sf = st.selectbox("Lọc trạng thái",
                      ["Tất cả","pending","assigned","in_transit",
                       "delivered","failed","returned"])
    base = """SELECT o.OrderID, c.CustomerName, o.RecipientName, o.RecipientPhone,
                     oc.CategoryName, o.Status,
                     FORMAT(o.DeclaredValueVND,0) AS GiaTri,
                     o.IsFragile, o.IsHighValue, DATE(o.DeadlineDate) AS Deadline
              FROM Orders o
              JOIN Customers c ON o.CustomerID=c.CustomerID
              JOIN OrderCategories oc ON o.CategoryID=oc.CategoryID"""
    if sf == "Tất cả":
        df = run_query(base + " ORDER BY o.OrderDate DESC LIMIT 200")
    else:
        df = run_query(base + " WHERE o.Status=%s ORDER BY o.OrderDate DESC LIMIT 200", (sf,))
    st.dataframe(df, use_container_width=True, hide_index=True)

    t1, t2, t3 = st.tabs(["Thêm đơn hàng","Hoá đơn","Xóa đơn hàng"])

    if "order_form_key" not in st.session_state:
        st.session_state["order_form_key"] = 0

    with t1:
        if "order_flash_msg" in st.session_state:
            msg_ph2 = st.empty()
            msg_ph2.success(st.session_state.pop("order_flash_msg"))
            time.sleep(2)
            msg_ph2.empty()

        custs = run_query("SELECT CustomerID,CustomerName FROM Customers ORDER BY CustomerName")
        cats  = run_query("SELECT CategoryID,CategoryName FROM OrderCategories")

        with st.form(f"order_form_{st.session_state['order_form_key']}"):
            c1, c2 = st.columns(2)
            with c1:
                if custs.empty:
                    st.warning("Chưa có khách hàng.")
                    st.form_submit_button("Thêm", disabled=True)
                    return
                cust_map = {f"{r.CustomerName} (#{r.CustomerID})": r.CustomerID
                            for r in custs.itertuples()}
                cust_sel  = st.selectbox("Khách hàng *", list(cust_map.keys()))
                cat_map   = {r.CategoryName: r.CategoryID for r in cats.itertuples()}
                cat_sel   = st.selectbox("Danh mục *", list(cat_map.keys()))
                rec_name  = st.text_input("Người nhận *")
                rec_phone = st.text_input("SĐT người nhận *")
            with c2:
                addr     = st.text_input("Địa chỉ giao *")
                val      = st.number_input("Giá trị (VND)", min_value=0, step=10000)
                wt       = st.number_input("Trọng lượng (kg)", min_value=0.0, step=0.1)
                fragile  = st.checkbox("Hàng dễ vỡ")
                deadline = st.date_input("Deadline *",
                                         value=datetime.date.today() + datetime.timedelta(days=2))
                notes    = st.text_input("Ghi chú")
            sub = st.form_submit_button("Thêm đơn hàng", use_container_width=True)

        if sub:
            if not rec_name or not rec_phone or not addr:
                st.error("Điền đầy đủ trường bắt buộc (*)")
            else:
                #Đảm bảo deadline > hôm nay
                deadline_dt = datetime.datetime.combine(
                    deadline, datetime.time(23, 59, 59))
                ok = run_exec(
                    """INSERT INTO Orders
                       (CustomerID,CategoryID,RecipientName,RecipientPhone,
                        DeliveryAddress,DeclaredValueVND,WeightKg,
                        IsFragile,Status,SpecialInstructions,DeadlineDate)
                       VALUES (%s,%s,%s,%s,%s,%s,%s,%s,'pending',%s,%s)""",
                    (cust_map[cust_sel], cat_map[cat_sel], rec_name, rec_phone,
                     addr, int(val), float(wt), 1 if fragile else 0,
                     notes or None, deadline_dt)
                )
                if ok:
                    st.session_state["order_form_key"] += 1
                    st.session_state["order_flash_msg"] = "✅ Đã thêm đơn hàng thành công!"
                    st.rerun()

    with t2:
        oid = st.number_input("OrderID", min_value=1, step=1, key="oid_inv")
        if st.button("Xem hoá đơn"):
            df_o = run_query(
                """SELECT o.*,c.CustomerName,c.PhoneNumber AS CPhone,
                          oc.CategoryName,oc.SurchargeRate
                   FROM Orders o JOIN Customers c ON o.CustomerID=c.CustomerID
                   JOIN OrderCategories oc ON o.CategoryID=oc.CategoryID
                   WHERE o.OrderID=%s""", (oid,))
            if df_o.empty:
                st.error("Không tìm thấy đơn hàng.")
            else:
                o        = df_o.iloc[0]
                df_e     = run_query(
                    """SELECT COALESCE(SUM(e.Amount),0) AS t
                       FROM Deliveries d JOIN Expenses e ON d.DeliveryID=e.DeliveryID
                       WHERE d.OrderID=%s""", (oid,))
                declared = float(o["DeclaredValueVND"] or 0)
                surpct   = float(o["SurchargeRate"]    or 0)
                suramt   = declared * surpct / 100
                texp     = float(df_e.iloc[0]["t"] if not df_e.empty else 0)
                total    = suramt + texp

                st.markdown(f"""
```
══════════════════════════════════════════════════
     HOÁ ĐƠN GIAO HÀNG — DELIVERY SERVICE MS
══════════════════════════════════════════════════
Số HD      : INV-{oid:05d}
Ngày xuất  : {datetime.date.today():%d/%m/%Y}
──────────────────────────────────────────────────
KHÁCH HÀNG : {o['CustomerName']}  SĐT: {o['CPhone']}
NGƯỜI NHẬN : {o['RecipientName']} SĐT: {o['RecipientPhone']}
ĐỊA CHỈ    : {(o['DeliveryAddress'] or '')[:55]}
──────────────────────────────────────────────────
Mã đơn     : #{oid}   Danh mục : {o['CategoryName']}
Trạng thái : {o['Status']}
Dễ vỡ      : {'Có ⚠️' if o['IsFragile'] else 'Không'}
GT cao      : {'Có 💎' if o['IsHighValue'] else 'Không'}
──────────────────────────────────────────────────
Giá trị hàng    : {declared:>15,.0f} VND
Phụ phí ({surpct:.0f}%)    : {suramt:>15,.0f} VND
Chi phí VC      : {texp:>15,.0f} VND
                  ───────────────────
TỔNG CỘNG       : {total:>15,.0f} VND
══════════════════════════════════════════════════
```""")
                si = io.StringIO()
                csv.writer(si).writerows([
                    ["Trường","Giá trị"],
                    ["Số HD", f"INV-{oid:05d}"],
                    ["Khách hàng", o["CustomerName"]],
                    ["Người nhận", o["RecipientName"]],
                    ["Tổng cộng",  f"{total:,.0f} VND"],
                ])
                st.download_button("⬇Tải CSV", si.getvalue(),
                                   f"invoice_{oid}.csv", "text/csv")

    with t3:
        st.markdown("**Xóa đơn hàng**")
        st.warning("Chỉ xóa được đơn chưa có chuyến giao.")
        col_del1, col_del2 = st.columns([2,1])
        with col_del1:
            oid_del = st.number_input("Nhập OrderID cần xóa", min_value=1, step=1, key="del_oid")
        with col_del2:
            st.markdown("<br>", unsafe_allow_html=True)
            del_btn = st.button("🗑 Xóa đơn", key="del_order_btn",
                                type="primary", use_container_width=True)

        if del_btn:
            df_check_deliv = run_query(
                "SELECT COUNT(*) AS cnt FROM Deliveries WHERE OrderID=%s", (oid_del,))
            deliv_count = int(df_check_deliv.iloc[0]["cnt"]) if not df_check_deliv.empty else 0
            if deliv_count > 0:
                st.error(f"Đơn #{oid_del} đã có {deliv_count} chuyến giao — xóa chuyến trước.")
            else:
                df_exists = run_query("SELECT OrderID FROM Orders WHERE OrderID=%s", (oid_del,))
                if df_exists.empty:
                    st.error(f"Không tìm thấy đơn hàng #{oid_del}.")
                elif run_exec("DELETE FROM Orders WHERE OrderID=%s", (oid_del,)):
                    st.success(f"Đã xóa đơn hàng #{oid_del}!")
                    time.sleep(1.5)
                    st.rerun()


# ══════════════════════════════════════════════════════════
# DELIVERIES
# ══════════════════════════════════════════════════════════
def page_deliveries():
    st.header("Giao hàng")

    # Toggle giữa bảng full vs view vw_current_schedule (chỉ active)
    only_active = st.toggle(
        "Chỉ hiển thị chuyến đang/sắp giao (vw_current_schedule)",
        value=False,
        help="Bật để dùng View vw_current_schedule — chỉ status 'scheduled' hoặc 'in_progress'"
    )

    if only_active:
        df = run_query("""
            SELECT DeliveryID, OrderID, DriverName, DriverPhone,
                   ScheduledDate, DeliveryStatus AS Status,
                   LicensePlate, VehicleType,
                   RecipientName, IsFragile, IsHighValue, CategoryName
            FROM   vw_current_schedule
            LIMIT  200""")
    else:
        df = run_query("""
            SELECT d.DeliveryID, o.OrderID, d.DriverName, d.DriverPhone,
                   d.ScheduledDate, d.Status, v.LicensePlate, v.VehicleType,
                   o.RecipientName, o.IsFragile, o.IsHighValue
            FROM Deliveries d JOIN Orders   o ON d.OrderID   = o.OrderID
            JOIN Vehicles   v ON d.VehicleID = v.VehicleID
            ORDER BY d.ScheduledDate DESC LIMIT 200""")
    st.dataframe(df, use_container_width=True, hide_index=True)

    t1, t2, t3, t4, t5 = st.tabs([
        "Phân công tự động","Phân công thủ công",
        "Cập nhật trạng thái","Theo dõi đơn hàng","Đánh giá"
    ])

    with t1:
        st.subheader("Phân công tự động")
        df_pending = run_query("""
            SELECT o.OrderID, c.CustomerName, o.RecipientName,
                   o.DeliveryAddress, DATE(o.DeadlineDate) AS Deadline
            FROM Orders o JOIN Customers c ON o.CustomerID=c.CustomerID
            WHERE o.Status='pending' ORDER BY o.DeadlineDate ASC""")

        if not df_pending.empty:
            st.markdown("**Danh sách đơn hàng đang chờ phân công tài xế:**")
            st.dataframe(df_pending, use_container_width=True, hide_index=True)
            if st.button("Phân công ngay", type="primary", use_container_width=True):
                # Dùng vw_available_vehicles để lấy xe rảnh (hide JOIN-and-filter)
                v_row = run_query(
                    "SELECT VehicleID FROM vw_available_vehicles LIMIT 1")
                if v_row.empty:
                    st.error("Không còn xe rảnh.")
                else:
                    oid_a = int(df_pending.iloc[0]["OrderID"])
                    vid_a = int(v_row.iloc[0]["VehicleID"])
                    sched = datetime.date.today().strftime("%Y-%m-%d")
                    ok, res, err = call_sp("sp_assign_delivery",
                        [oid_a, vid_a, "Tài xế tự động", "N/A", sched], out_count=2)
                    sp_ok = ok and res and res[0] is not None and int(res[0]) > 0
                    if sp_ok:
                        st.success(f"Phân công tự động thành công cho Đơn #{oid_a}! DeliveryID={res[0]}")
                        time.sleep(1)
                        st.rerun()
                    else:
                        sp_err_msg = (res[1] if res and len(res) > 1 and res[1] else None) or err or "Lỗi không xác định."
                        st.error(sp_err_msg)
        else:
            st.success("Không có đơn hàng nào đang chờ phân công.")

    with t2:
        pending = run_query("""SELECT o.OrderID,c.CustomerName,o.RecipientName
                               FROM Orders o
                               JOIN Customers c ON o.CustomerID=c.CustomerID
                               WHERE o.Status='pending'""")
        # Dùng vw_available_vehicles — chỉ liệt kê xe đang available
        # và đã sẵn các cột MaxValueVND, CanCarryFragile để dispatcher đối chiếu
        avail_v = run_query("""
            SELECT VehicleID, VehicleType, LicensePlate,
                   MaxWeightKg, MaxValueVND, CanCarryFragile
            FROM   vw_available_vehicles""")

        with st.form("assign_form"):
            if pending.empty:
                st.warning("Không có đơn pending."); o_sel = None
            else:
                o_map = {f"#{r.OrderID} - {r.CustomerName} → {r.RecipientName}": r.OrderID
                         for r in pending.itertuples()}
                o_sel = o_map[st.selectbox("Đơn hàng (pending) *", list(o_map))]
            if avail_v.empty:
                st.warning("Không có xe available."); v_sel = None
            else:
                v_map = {f"{r.LicensePlate} ({r.VehicleType})": r.VehicleID
                         for r in avail_v.itertuples()}
                v_sel = v_map[st.selectbox("Xe *", list(v_map))]
            c1, c2 = st.columns(2)
            with c1:
                drv_name  = st.text_input("Tên tài xế *")
                drv_phone = st.text_input("SĐT tài xế")
            with c2:
                sched_d = st.date_input("Ngày giao *", value=datetime.date.today())
            sub = st.form_submit_button("Phân công", use_container_width=True)

        if sub and o_sel and v_sel and drv_name:
            ok, res, err = call_sp("sp_assign_delivery",
                [o_sel, v_sel, drv_name, drv_phone or None, str(sched_d)],
                out_count=2)
            sp_ok2 = ok and res and res[0] is not None and int(res[0]) > 0
            if sp_ok2:
                st.success(f"Đã tạo DeliveryID={res[0]}")
                icon, title, body = make_notify_body("assigned", {
                    "order_id": o_sel, "driver": drv_name, "date": str(sched_d)})
                show_notify(icon, title, body, "success")
                time.sleep(1)
                st.rerun()
            else:
                sp_err_msg2 = (res[1] if res and len(res) > 1 and res[1] else None) or err or "Lỗi SP."
                st.error(sp_err_msg2)

    if "fail_form_key" not in st.session_state:
        st.session_state["fail_form_key"] = 0

    with t3:
        if "t3_flash" in st.session_state:
            kind, msg = st.session_state.pop("t3_flash")
            if kind == "success":
                st.success(msg)
            elif kind == "warning":
                st.warning(msg)
            elif kind == "error":
                st.error(msg)
            else:
                st.info(msg)
        if "t3_notify" in st.session_state:
            icon, title, body, nkind = st.session_state.pop("t3_notify")
            show_notify(icon, title, body, nkind)
        t3_msg_ph = st.empty()
        did_upd = st.number_input("DeliveryID cần cập nhật", min_value=1, step=1, key="did_upd")
        c1, c2  = st.columns(2)

        with c1:
            st.markdown("**Hoàn thành**")
            if st.button("Đánh dấu HOÀN THÀNH", use_container_width=True, type="primary"):
                info = run_query(
                    """SELECT o.OrderID, o.RecipientName
                       FROM Deliveries d JOIN Orders o ON d.OrderID=o.OrderID
                       WHERE d.DeliveryID=%s""", (did_upd,))
                ok = run_exec(
                    """UPDATE Deliveries
                       SET Status='completed', ActualDeliveryTime=NOW()
                       WHERE DeliveryID=%s""", (did_upd,))
                if ok and not info.empty:
                    row = info.iloc[0]
                    icon, title, body = make_notify_body("delivered", {
                        "order_id": row["OrderID"],
                        "customer_name": row["RecipientName"],
                        "time": datetime.datetime.now().strftime("%d/%m/%Y %H:%M")})
                    st.session_state["t3_flash"] = ("success", f"Chuyến giao #{did_upd} đã HOÀN THÀNH.")
                    st.session_state["t3_notify"] = (icon, title, body, "success")
                    st.rerun()
                else:
                    st.session_state["t3_flash"] = ("error", f"Không tìm thấy DeliveryID={did_upd}.")
                    st.rerun()

        with c2:
            st.markdown("**Xử lý thất bại thông minh**")
            with st.form(f"smart_fail_form_{st.session_state['fail_form_key']}"):
                reasons = {
                    "no_answer":          "Không bắt máy",
                    "not_home":           "Vắng nhà",
                    "refused":            "Từ chối nhận",
                    "damaged_on_arrival": "Hàng bị hỏng",
                    "wrong_address":      "Sai địa chỉ",
                    "other":              "Lý do khác",
                }
                reason = st.selectbox("Lý do", list(reasons.keys()),
                                      format_func=lambda x: reasons[x])
                notes  = st.text_area("Ghi chú", height=80)
                fail_sub = st.form_submit_button(
                    "Xử lý (sp_smart_reschedule)",
                    type="secondary", use_container_width=True)

            if fail_sub:
                ok, res, err = call_sp("sp_smart_reschedule",
                    [did_upd, reason, notes or None], out_count=2)
                if ok and res and res[0] not in (None, "ERROR"):
                    status_out = res[0]
                    msg_out    = res[1] or ""
                    st.session_state["fail_form_key"] += 1
                    if status_out == "RESCHEDULED":
                        st.session_state["t3_flash"] = ("success", f"Lên lịch lại: {msg_out}")
                    elif status_out in ("ESCALATED", "RETURNED"):
                        st.session_state["t3_flash"] = ("warning", f"{status_out}: {msg_out}")
                    else:
                        st.session_state["t3_flash"] = ("info", msg_out)
                    st.rerun()
                else:
                    sp_err = (res[1] if res and len(res) > 1 and res[1] else None) or err or "Lỗi SP."
                    st.session_state["t3_flash"] = ("error", sp_err)
                    st.rerun()

    with t4:
        st.subheader("Truy vết hành trình đơn hàng")
        c1, c2 = st.columns([1, 2])
        with c1:
            did_track = st.number_input("Nhập DeliveryID để truy vết", min_value=1, step=1, key="track_did")
            btn_track = st.button("🔍 Truy vết ngay", use_container_width=True)
        
        if btn_track or did_track:
            with st.container():
                render_delivery_timeline(did_track)
                
        st.divider()
        st.subheader("Mô phỏng GPS (Thời gian thực)")
        did_gps = st.number_input("DeliveryID (GPS)", min_value=1, step=1, key="gps_did")
        if st.button("Bắt đầu Theo dõi GPS"):
            # THÊM d.Status VÀO CÂU TRUY VẤN
            info_gps = run_query(
                """SELECT d.DriverName, v.LicensePlate,
                          o.RecipientName, o.DeliveryAddress, d.Status
                   FROM Deliveries d
                   JOIN Vehicles v ON d.VehicleID=v.VehicleID
                   JOIN Orders   o ON d.OrderID  =o.OrderID
                   WHERE d.DeliveryID=%s""", (did_gps,))

            if not info_gps.empty:
                r = info_gps.iloc[0]
                st.markdown(f"""
<div class="gps-info">
<b>Tài xế:</b> {r['DriverName']} &nbsp;|&nbsp; <b>Biển số:</b> {r['LicensePlate']}<br>
<b>Người nhận:</b> {r['RecipientName']}<br>
<b>Địa chỉ:</b> {(r['DeliveryAddress'] or '')[:60]}
</div>""", unsafe_allow_html=True)

                # KIỂM TRA TRẠNG THÁI TRƯỚC KHI VẼ BẢN ĐỒ
                current_status = r['Status']
                
                if current_status == 'scheduled':
                    st.info("Xe chưa xuất phát khỏi kho. Tín hiệu GPS chưa được kích hoạt.")
                elif current_status == 'completed':
                    st.success("Chuyến giao đã hoàn thành.")
                elif current_status in ('failed', 'returned'):
                    st.error("Chuyến giao đã thất bại hoặc hoàn về. Không có tín hiệu GPS.")
                else:
                    # Chỉ chạy mô phỏng khi Status là 'in_progress'
                    status_ph  = st.empty()
                    prog_ph    = st.progress(0)
                    col_eta, col_traffic, col_coord = st.columns(3)
                    eta_ph     = col_eta.empty()
                    traffic_ph = col_traffic.empty()
                    coord_ph   = col_coord.empty()
                    chart_ph   = st.empty()

                    STEPS = 18
                    lats = [21.02]; lngs = [105.850]

                    for step in range(1, STEPS + 1):
                        t_frac = step / STEPS
                        lat = 21.02 + t_frac * 0.025 + random.uniform(-0.003, 0.003)
                        lng = 105.85 + t_frac * 0.012 + random.uniform(-0.003, 0.003)
                        lats.append(lat); lngs.append(lng)
                        pct = int(t_frac * 100)

                        h = datetime.datetime.now().hour
                        if (7 <= h <= 9) or (17 <= h <= 19):
                            traffic = "🔴 Tắc đường"; delay = 2.5
                        elif random.random() < 0.18:
                            traffic = "🟡 Chậm vừa"; delay = 1.5
                        else:
                            traffic = "🟢 Bình thường"; delay = 1.0
                        eta = max(0, int((1 - t_frac) * 28 * delay))

                        status_txt = ("✅ Đã giao hàng thành công!" if step == STEPS
                                      else "🔵 Đang trên đường giao hàng...")
                        status_ph.markdown(f"**{status_txt}**")
                        prog_ph.progress(pct)
                        eta_ph.metric("ETA", f"~{eta} phút")
                        traffic_ph.metric("Giao thông", traffic)
                        coord_ph.metric("Toạ độ", f"{lat:.4f}, {lng:.4f}")

                        fig_m = go.Figure()
                        fig_m.add_trace(go.Scatter(x=lngs, y=lats, mode="lines+markers",
                            line=dict(color="#00d4aa", width=2),
                            marker=dict(size=6, color="#00d4aa"), showlegend=False))
                        fig_m.add_trace(go.Scatter(x=[105.850], y=[21.02], mode="markers",
                            marker=dict(size=12, color="#10b981"), name="Kho"))
                        fig_m.add_trace(go.Scatter(x=[105.862], y=[21.045], mode="markers",
                            marker=dict(size=12, color="#ef4444"), name="Khách hàng"))
                        fig_m.add_trace(go.Scatter(x=[lng], y=[lat], mode="markers",
                            marker=dict(size=16, color="#f59e0b", symbol="arrow-up"),
                            name="Xe hiện tại"))
                        fig_m.update_layout(height=400, margin=dict(l=0,r=0,t=20,b=0),
                            paper_bgcolor="#161923", plot_bgcolor="#1e2336",
                            font_color="#c8d3f5")
                        chart_ph.plotly_chart(fig_m, use_container_width=True)
                        time.sleep(1.2)
            else:
                st.error("Không tìm thấy DeliveryID.")
    with t5:
        st.subheader("Đánh giá chuyến giao")
        did_r = st.number_input("DeliveryID", min_value=1, step=1, key="did_rate")
        c1, c2, c3 = st.columns(3)
        with c1: q1 = st.slider("Tình trạng hàng", 1, 5, 5)
        with c2: q2 = st.slider("Dịch vụ tài xế",  1, 5, 5)
        with c3: q3 = st.slider("Thời gian giao",   1, 5, 5)
        avg_r = round((q1+q2+q3)/3, 2)
        st.metric("Điểm trung bình", f"{avg_r}/5.0")
        comment = st.text_input("Nhận xét (tuỳ chọn)")
        if st.button("Gửi đánh giá", type="primary"):
            ok = run_exec(
                """INSERT INTO DeliveryRatings
                   (DeliveryID,OrderCondition,DriverService,DeliveryTime,Comment)
                   VALUES (%s,%s,%s,%s,%s)
                   ON DUPLICATE KEY UPDATE
                       OrderCondition=VALUES(OrderCondition),
                       DriverService=VALUES(DriverService),
                       DeliveryTime=VALUES(DeliveryTime),
                       Comment=VALUES(Comment)""",
                (did_r, q1, q2, q3, comment or None))
            if ok:
                st.success(f"Cảm ơn! Điểm TB = {avg_r}/5.0")


# ══════════════════════════════════════════════════════════
# VEHICLES
# ══════════════════════════════════════════════════════════
def page_vehicles():
    st.header("Phương tiện")
    sf = st.selectbox("Lọc", ["Tất cả","available","in_use","maintenance"])
    if sf == "Tất cả":
        df = run_query("SELECT * FROM Vehicles ORDER BY VehicleType")
    else:
        df = run_query("SELECT * FROM Vehicles WHERE Availability=%s ORDER BY VehicleType", (sf,))
    st.dataframe(df, use_container_width=True, hide_index=True)

    with st.expander("Thêm xe"):
        with st.form("veh_form"):
            c1, c2 = st.columns(2)
            with c1:
                vtype   = st.selectbox("Loại xe *",
                    ["motorbike","van","truck","refrigerated_truck"])
                plate   = st.text_input("Biển số *")
                avail   = st.selectbox("Trạng thái",
                    ["available","in_use","maintenance"])
            with c2:
                max_wt  = st.number_input("Tải tối đa (kg)", 0.0, step=0.5)
                max_val = st.number_input("GT tối đa (VND)", 0, step=100000)
                fragile = st.checkbox("Chở hàng dễ vỡ", value=True)
            sub = st.form_submit_button("Thêm xe", use_container_width=True)
        if sub and plate:
            ok = run_exec(
                """INSERT INTO Vehicles
                   (VehicleType,LicensePlate,Availability,
                    MaxWeightKg,MaxValueVND,CanCarryFragile)
                   VALUES (%s,%s,%s,%s,%s,%s)""",
                (vtype, plate, avail, float(max_wt),
                 int(max_val), 1 if fragile else 0))
            if ok:
                st.success("Đã thêm xe!")
                st.rerun()


# ══════════════════════════════════════════════════════════
# EXPENSES
# ══════════════════════════════════════════════════════════
def page_expenses():
    st.header("Chi phí")
    df = run_query("""
        SELECT e.ExpenseID, e.DeliveryID, o.RecipientName,
               e.ExpenseType, FORMAT(e.Amount,0) AS SoTien,
               e.Description, e.ExpenseDate
        FROM Expenses e JOIN Deliveries d ON e.DeliveryID=d.DeliveryID
        JOIN Orders o ON d.OrderID=o.OrderID
        ORDER BY e.ExpenseDate DESC LIMIT 200""")
    st.dataframe(df, use_container_width=True, hide_index=True)

    # ── Tra cứu chi phí 1 chuyến giao (gọi sp_get_delivery_cost) ──
    with st.expander("Tra cứu chi phí của 1 chuyến giao (sp_get_delivery_cost)"):
        st.caption("Stored Procedure sp_get_delivery_cost trả về (TotalAmount, Breakdown)")
        c_inp, c_btn = st.columns([2, 1])
        with c_inp:
            did_cost = st.number_input(
                "DeliveryID", min_value=1, step=1, key="cost_did"
            )
        with c_btn:
            st.markdown("<br>", unsafe_allow_html=True)
            btn_cost = st.button("Tính tổng chi phí", use_container_width=True)

        if btn_cost:
            ok, res, err = call_sp(
                "sp_get_delivery_cost",
                [int(did_cost)],
                out_count=2
            )
            if ok and res:
                total_amount = float(res[0] or 0)
                breakdown    = res[1] or "(chua co chi phi)"
                mc1, mc2 = st.columns([1, 2])
                mc1.metric("Tổng chi phí", f"{total_amount:,.0f} VND")
                mc2.markdown(f"**Chi tiết:** {breakdown}")
            else:
                st.error(err or "Không tính được chi phí.")

    with st.expander("Thêm chi phí"):
        delivs = run_query("""
            SELECT d.DeliveryID, o.RecipientName, d.ScheduledDate
            FROM Deliveries d JOIN Orders o ON d.OrderID=o.OrderID
            ORDER BY d.ScheduledDate DESC LIMIT 100""")
        with st.form("exp_form"):
            if delivs.empty:
                st.warning("Chưa có chuyến giao."); return
            d_map = {f"#{r.DeliveryID} - {r.RecipientName} ({r.ScheduledDate})": r.DeliveryID
                     for r in delivs.itertuples()}
            d_sel   = d_map[st.selectbox("Chuyến giao *", list(d_map))]
            c1, c2  = st.columns(2)
            with c1:
                etype  = st.selectbox("Loại chi phí *",
                    ["fuel","toll","handling","insurance","failed_attempt","other"])
                amount = st.number_input("Số tiền (VND) *", 0.0, step=1000.0)
            with c2:
                desc  = st.text_input("Mô tả")
                edate = st.date_input("Ngày", value=datetime.date.today())
            sub = st.form_submit_button("Lưu", use_container_width=True)
        if sub:
            ok = run_exec(
                """INSERT INTO Expenses
                   (DeliveryID,ExpenseType,Amount,Description,ExpenseDate)
                   VALUES (%s,%s,%s,%s,%s)""",
                (d_sel, etype, float(amount), desc or None, str(edate)))
            if ok:
                st.success("Đã thêm!")
                st.rerun()


# ══════════════════════════════════════════════════════════
# REPORTS
# ══════════════════════════════════════════════════════════
def page_reports():
    st.header("Báo cáo & Thống kê")

    avg_r    = run_query("SELECT fn_avg_delivery_cost() AS v")
    avg_cost = float(avg_r.iloc[0]["v"]) if not avg_r.empty else 0
    done     = run_query("SELECT COUNT(*) AS n FROM Deliveries WHERE Status='completed'").iloc[0]["n"]
    issues   = run_query("SELECT COUNT(*) AS n FROM OrderIssues WHERE Resolution='pending'").iloc[0]["n"]

    c1, c2, c3 = st.columns(3)
    c1.metric("Chi phí TB (fn_avg_delivery_cost)", f"{avg_cost:,.0f} VND")
    c2.metric("Chuyến hoàn thành",                 done)
    c3.metric("Vấn đề đang mở",                   issues)

    t1, t2, t3, t4 = st.tabs([
        "Đơn theo trạng thái","Chi phí theo loại",
        "Hiệu suất phương tiện","Xuất báo cáo"
    ])

    with t1:
        df1 = run_query("""
            SELECT Status, COUNT(*) AS SoLuong,
                   FORMAT(SUM(DeclaredValueVND),0) AS TongGiaTri
            FROM Orders GROUP BY Status""")
        if not df1.empty:
            fig1 = px.bar(df1, x="Status", y="SoLuong",
                          color="SoLuong", color_continuous_scale="teal",
                          text="SoLuong",
                          title="Phân bổ đơn hàng theo trạng thái")
            fig1.update_traces(textposition="outside")
            fig1.update_layout(paper_bgcolor="rgba(0,0,0,0)",
                               plot_bgcolor="rgba(0,0,0,0)",
                               font_color="#c8d3f5", showlegend=False)
            st.plotly_chart(fig1, use_container_width=True)
            st.dataframe(df1, use_container_width=True, hide_index=True)

    with t2:
        df2 = run_query("""
            SELECT ExpenseType, COUNT(*) AS SoLan,
                   SUM(Amount) AS Tong, AVG(Amount) AS TrungBinh
            FROM Expenses GROUP BY ExpenseType ORDER BY Tong DESC""")
        if not df2.empty:
            fig2 = px.pie(df2, values="Tong", names="ExpenseType",
                          hole=0.55, title="Chi phí theo loại",
                          color_discrete_sequence=px.colors.qualitative.Safe)
            fig2.update_layout(paper_bgcolor="rgba(0,0,0,0)", font_color="#c8d3f5")
            st.plotly_chart(fig2, use_container_width=True)
            st.dataframe(df2, use_container_width=True, hide_index=True)

    with t3:
        df3 = run_query("""
            SELECT v.LicensePlate, v.VehicleType, v.Availability,
                   fn_deliveries_per_vehicle(v.VehicleID) AS TongChuyen
            FROM Vehicles v ORDER BY TongChuyen DESC""")
        if not df3.empty:
            fig3 = px.bar(df3, x="LicensePlate", y="TongChuyen",
                          color="VehicleType",
                          title="Số chuyến theo phương tiện (fn_deliveries_per_vehicle)")
            fig3.update_layout(paper_bgcolor="rgba(0,0,0,0)",
                               plot_bgcolor="rgba(0,0,0,0)", font_color="#c8d3f5")
            st.plotly_chart(fig3, use_container_width=True)
            st.dataframe(df3, use_container_width=True, hide_index=True)

        df_cost = run_query("""
            SELECT OrderID, RecipientName, OrderStatus,
                   TotalExpenseVND, ExpenseCount
            FROM vw_cost_per_order ORDER BY TotalExpenseVND DESC LIMIT 10""")
        st.subheader("Top 10 chi phí cao nhất (vw_cost_per_order)")
        st.dataframe(df_cost, use_container_width=True, hide_index=True)

        df_rate = run_query("""
            SELECT ROUND(AVG(OrderCondition),2) AS HangHoa,
                   ROUND(AVG(DriverService),2)  AS TaiXe,
                   ROUND(AVG(DeliveryTime),2)   AS ThoiGian,
                   ROUND(AVG(AverageScore),2)   AS TrungBinh,
                   COUNT(*)                     AS SoLuot
            FROM DeliveryRatings""")
        if not df_rate.empty and df_rate.iloc[0]["SoLuot"] > 0:
            st.subheader("Thống kê đánh giá")
            r = df_rate.iloc[0]
            rc1,rc2,rc3,rc4 = st.columns(4)
            rc1.metric("Hàng hoá",  f"{r['HangHoa']}/5")
            rc2.metric("Tài xế",    f"{r['TaiXe']}/5")
            rc3.metric("Thời gian",  f"{r['ThoiGian']}/5")
            rc4.metric("Trung bình", f"{r['TrungBinh']}/5.0")

    with t4:
        EXPORTS = {
            "Đơn hàng":     ("Don_hang.csv",
                """SELECT o.OrderID,c.CustomerName,o.RecipientName,o.RecipientPhone,
                          oc.CategoryName,o.Status,o.DeclaredValueVND,
                          o.WeightKg,o.IsFragile,o.IsHighValue,
                          o.OrderDate,o.DeadlineDate
                   FROM Orders o JOIN Customers c ON o.CustomerID=c.CustomerID
                   JOIN OrderCategories oc ON o.CategoryID=oc.CategoryID
                   ORDER BY o.OrderDate DESC"""),
            "Giao hàng":    ("Giao_hang.csv",
                """SELECT d.DeliveryID,d.DriverName,d.DriverPhone,d.ScheduledDate,
                          d.Status,v.LicensePlate,o.RecipientName,o.DeliveryAddress
                   FROM Deliveries d JOIN Orders o ON d.OrderID=o.OrderID
                   JOIN Vehicles v ON d.VehicleID=v.VehicleID
                   ORDER BY d.ScheduledDate DESC"""),
            "Chi phí":      ("Chi_phi.csv",
                "SELECT * FROM Expenses ORDER BY ExpenseDate DESC"),
            "Thất bại":     ("Giao_that_bai.csv",
                "SELECT * FROM DeliveryAttempts ORDER BY AttemptTime DESC"),
            "CP theo đơn":  ("Chi_phi_don.csv",
                "SELECT * FROM vw_cost_per_order ORDER BY TotalExpenseVND DESC"),
            "Hiệu suất xe": ("Hieu_suat_xe.csv",
                """SELECT v.LicensePlate,v.VehicleType,v.Availability,
                          fn_deliveries_per_vehicle(v.VehicleID) AS TongChuyen
                   FROM Vehicles v ORDER BY TongChuyen DESC"""),
            "Vấn đề":       ("Van_de.csv",
                "SELECT * FROM OrderIssues ORDER BY Severity DESC, ReportedAt DESC"),
            "Đánh giá":     ("Danh_gia.csv",
                "SELECT * FROM DeliveryRatings ORDER BY RatedAt DESC"),
        }

        cols = st.columns(4)
        for i, (label, (fname, sql_e)) in enumerate(EXPORTS.items()):
            df_e = run_query(sql_e)
            with cols[i % 4]:
                if not df_e.empty:
                    si = io.StringIO()
                    df_e.to_csv(si, index=False, encoding="utf-8-sig")
                    st.download_button(f"⬇️ {label}", si.getvalue(), fname,
                                       "text/csv", use_container_width=True,
                                       key=f"dl_{i}")
                else:
                    st.button(f"⬇️ {label} (trống)", disabled=True,
                              use_container_width=True, key=f"dl_empty_{i}")


# ══════════════════════════════════════════════════════════
# AUDIT LOG VIEWER  (delivery_manager only)
# ══════════════════════════════════════════════════════════
def page_audit_log():
    import os
    import re

    st.header("Audit Log — Nhật ký hoạt động hệ thống")
    st.caption("Chỉ Quản lý (delivery_manager) mới có thể xem trang này.")

    # ── Đường dẫn file log ──────────────────────────────────
    audit_file = os.path.join(LOG_DIR, "audit.log")

    # ── Đọc và parse log ────────────────────────────────────
    LOG_PATTERN = re.compile(
        r"^(?P<timestamp>\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})"
        r"\s+\|\s+(?P<level>\w+)\s+"
        r"\|\s+(?P<logger>[^\|]+)\s+"
        r"\|\s+(?P<location>[^\|]+)\s+"
        r"\|\s+(?P<message>.+)$"
    )

    rows = []
    if os.path.exists(audit_file):
        try:
            with open(audit_file, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.rstrip()
                    if not line:
                        continue
                    m = LOG_PATTERN.match(line)
                    if m:
                        rows.append({
                            "Thời gian":  m.group("timestamp"),
                            "Mức":        m.group("level"),
                            "Message":    m.group("message"),
                        })
                    else:
                        # dòng không parse được → giữ nguyên
                        rows.append({
                            "Thời gian": "",
                            "Mức":       "RAW",
                            "Message":   line,
                        })
        except Exception as e:
            st.error(f"Không thể đọc file audit log: {e}")
            return
    else:
        st.warning(
            f"Chưa có file audit log tại `{audit_file}`. "
            "File sẽ được tạo tự động sau lần đăng nhập đầu tiên."
        )
        return

    if not rows:
        st.info("File audit log trống.")
        return

    df_log = pd.DataFrame(rows[::-1])  # mới nhất lên đầu

    # ── Bộ lọc ──────────────────────────────────────────────
    col1, col2, col3 = st.columns([2, 2, 1])
    with col1:
        level_opts = ["Tất cả"] + sorted(df_log["Mức"].unique().tolist())
        sel_level  = st.selectbox("Lọc theo mức", level_opts, key="al_level")
    with col2:
        kw = st.text_input("Tìm kiếm trong message", placeholder="VD: LOGIN_FAIL, admin ...", key="al_kw")
    with col3:
        limit = st.number_input("Số dòng hiển thị", min_value=20, max_value=2000,
                                 value=200, step=50, key="al_limit")

    df_view = df_log.copy()
    if sel_level != "Tất cả":
        df_view = df_view[df_view["Mức"] == sel_level]
    if kw.strip():
        df_view = df_view[df_view["Message"].str.contains(kw.strip(), case=False, na=False)]
    df_view = df_view.head(int(limit))

    # ── Màu theo mức ────────────────────────────────────────
    def _color_level(val):
        c = {
            "INFO":    "color:#10b981",
            "WARNING": "color:#f59e0b",
            "ERROR":   "color:#ef4444",
            "CRITICAL":"color:#ef4444;font-weight:700",
            "DEBUG":   "color:#6366f1",
        }.get(val, "color:#8899b2")
        return c

    # ── Thống kê nhanh ──────────────────────────────────────
    with st.expander("Thống kê tổng quan", expanded=False):
        summary = df_log["Mức"].value_counts().reset_index()
        summary.columns = ["Mức", "Số lượng"]
        sc1, sc2 = st.columns([1, 2])
        with sc1:
            st.dataframe(summary, use_container_width=True, hide_index=True)
        with sc2:
            if not summary.empty:
                fig_s = px.bar(
                    summary, x="Mức", y="Số lượng",
                    color="Mức",
                    color_discrete_map={
                        "INFO":"#10b981","WARNING":"#f59e0b",
                        "ERROR":"#ef4444","DEBUG":"#6366f1","RAW":"#8899b2",
                    },
                    title="Phân bố sự kiện audit"
                )
                fig_s.update_layout(
                    paper_bgcolor="rgba(0,0,0,0)",
                    plot_bgcolor="rgba(0,0,0,0)",
                    font_color="#c8d3f5", showlegend=False
                )
                st.plotly_chart(fig_s, use_container_width=True)

    # ── Bảng log ────────────────────────────────────────────
    st.markdown(f"**{len(df_view):,} dòng** (trong tổng {len(df_log):,} bản ghi)")

    # Render bảng với màu inline HTML
    rows_html = ""
    for _, r in df_view.iterrows():
        style = _color_level(r["Mức"])
        level_badge_color = {
            "INFO":    "#10b981", "WARNING": "#f59e0b",
            "ERROR":   "#ef4444", "CRITICAL":"#ef4444",
            "DEBUG":   "#6366f1", "RAW":     "#8899b2",
        }.get(r["Mức"], "#8899b2")
        rows_html += (
            f'<tr>'
            f'<td style="color:#8899b2;font-family:monospace;font-size:11px;'
            f'white-space:nowrap;padding:4px 8px">{r["Thời gian"]}</td>'
            f'<td style="padding:4px 8px">'
            f'<span style="background:{level_badge_color}22;color:{level_badge_color};'
            f'padding:2px 7px;border-radius:4px;font-size:10px;'
            f'font-weight:700;font-family:monospace">{r["Mức"]}</span></td>'
            f'<td style="font-family:monospace;font-size:11px;'
            f'padding:4px 8px;color:#c8d3f5">{r["Message"]}</td>'
            f'</tr>'
        )

    table_html = f"""
<div style="overflow-x:auto;border:1px solid #1E2D45;border-radius:8px;
     background:#0E1521;max-height:520px;overflow-y:auto">
  <table style="width:100%;border-collapse:collapse">
    <thead>
      <tr style="background:#121D2E;border-bottom:1px solid #1E2D45;
           position:sticky;top:0">
        <th style="text-align:left;padding:8px;color:#8899b2;
             font-size:11px;font-weight:600;white-space:nowrap">THỜI GIAN</th>
        <th style="text-align:left;padding:8px;color:#8899b2;
             font-size:11px;font-weight:600">MỨC</th>
        <th style="text-align:left;padding:8px;color:#8899b2;
             font-size:11px;font-weight:600">MESSAGE</th>
      </tr>
    </thead>
    <tbody>
      {rows_html}
    </tbody>
  </table>
</div>"""
    st.markdown(table_html, unsafe_allow_html=True)

    # ── Download toàn bộ audit log ──────────────────────────
    st.markdown("&nbsp;")
    try:
        with open(audit_file, "r", encoding="utf-8") as f:
            raw_content = f.read()
        st.download_button(
            "⬇️ Tải xuống audit.log (toàn bộ)",
            data=raw_content,
            file_name=f"audit_{datetime.datetime.now().strftime('%Y%m%d_%H%M')}.log",
            mime="text/plain",
            use_container_width=False,
            key="dl_audit_log",
        )
    except Exception:
        pass


# ══════════════════════════════════════════════════════════
# MAIN ROUTER
# ══════════════════════════════════════════════════════════
def main():
    if "user" not in st.session_state:
        show_login_page()
        return

    show_sidebar()

    page   = st.session_state.get("page","dashboard")
    routes = {
        "dashboard":  page_dashboard,
        "customers":  page_customers,
        "orders":     page_orders,
        "deliveries": page_deliveries,
        "vehicles":   page_vehicles,
        "expenses":   page_expenses,
        "reports":    page_reports,
        "issues":     page_issues,
        "audit_log":  page_audit_log,
    }
    routes.get(page, page_dashboard)()


if __name__ == "__main__":
    main()