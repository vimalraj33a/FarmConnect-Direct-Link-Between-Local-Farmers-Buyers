import streamlit as st
from PIL import Image
import sqlite3
import os
import io
import pandas as pd
import bcrypt
from datetime import datetime

# -----------------------------------------------------------
# PAGE CONFIG
# -----------------------------------------------------------
st.set_page_config(page_title="FarmConnect", layout="wide")

# -----------------------------------------------------------
# CUSTOM CSS (GREEN–WHITE THEME + BACKGROUND + CARDS)
# -----------------------------------------------------------
page_bg_img = f"""
<style>

:root {{
    --skyblue: #00aaff;
}}

.stApp {{
    background: url("https://images.unsplash.com/photo-1501004318641-b39e6451bec6")
    no-repeat center center fixed;
    background-size: cover;
    color: var(--skyblue) !important;
}}

.stApp * {{
    color: var(--skyblue) !important;
}}

.stApp::before {{
    content: "";
    position: fixed;
    top: 0;
    left: 0;
    height: 100%;
    width: 100%;
    background: rgba(255,255,255,0.70);
    z-index: -1;
}}

.product-card {{
    background: rgba(255,255,255,0.90);
    padding: 15px;
    border-radius: 12px;
    margin-bottom: 20px;
    border-left: 6px solid #2e7d32;
    box-shadow: 0px 3px 8px rgba(0,0,0,0.12);
    color: var(--skyblue) !important;
}}

.stButton > button {{
    border-radius: 8px;
    background-color: #2e7d32 !important;
    color: white !important;
    font-weight: bold;
    padding: 8px 18px;
}}

.stButton > button:hover {{
    background-color: #1b5e20 !important;
    color: white !important;
}}

[data-testid="stSidebar"] {{
    background-color: #e8f5e9 !important;
    color: var(--skyblue) !important;
}}

</style>
"""
st.markdown(page_bg_img, unsafe_allow_html=True)



# -----------------------------------------------------------
# PATHS
# -----------------------------------------------------------
DB_PATH = "farmconnect.db"
UPLOAD_DIR = "uploads"

os.makedirs(UPLOAD_DIR, exist_ok=True)

# -----------------------------------------------------------
# DATABASE SETUP
# -----------------------------------------------------------
def get_connection():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_connection()
    cur = conn.cursor()

    # Users
    cur.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE,
        password_hash BLOB,
        role TEXT,
        created_at TEXT
    )
    """)

    # Products
    cur.execute("""
    CREATE TABLE IF NOT EXISTS products (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        farmer_id INTEGER,
        title TEXT,
        description TEXT,
        price REAL,
        quantity INTEGER,
        image_path TEXT,
        created_at TEXT,
        FOREIGN KEY(farmer_id) REFERENCES users(id)
    )
    """)

    conn.commit()
    conn.close()

init_db()

# -----------------------------------------------------------
# PASSWORD HELPERS
# -----------------------------------------------------------
def hash_password(p):
    return bcrypt.hashpw(p.encode(), bcrypt.gensalt())

def verify_password(p, hashed):
    return bcrypt.checkpw(p.encode(), hashed)

# -----------------------------------------------------------
# USER AUTH
# -----------------------------------------------------------
def register_user(username, password, role):
    conn = get_connection()
    cur = conn.cursor()

    try:
        h = hash_password(password)
        cur.execute(
            "INSERT INTO users (username, password_hash, role, created_at) VALUES (?,?,?,?)",
            (username, h, role, datetime.utcnow().isoformat())
        )
        conn.commit()
        return True, "Registration successful"
    except sqlite3.IntegrityError:
        return False, "Username already exists"
    finally:
        conn.close()

def login_user(username, password):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM users WHERE username = ?", (username,))
    r = cur.fetchone()
    conn.close()

    if not r:
        return False, "User not found"

    if verify_password(password, r["password_hash"]):
        return True, dict(id=r["id"], username=r["username"], role=r["role"])
    return False, "Wrong password"

# -----------------------------------------------------------
# PRODUCT HELPERS
# -----------------------------------------------------------
def add_product(fid, title, desc, price, qty, img_bytes, filename):
    # Save image
    timestamp = datetime.utcnow().strftime("%Y%m%d%H%M%S")
    img_name = f"{timestamp}_{filename}"
    path = os.path.join(UPLOAD_DIR, img_name)

    with open(path, "wb") as f:
        f.write(img_bytes)

    # DB insert
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO products (farmer_id, title, description, price, quantity, image_path, created_at)
        VALUES (?,?,?,?,?,?,?)
    """, (fid, title, desc, price, qty, path, datetime.utcnow().isoformat()))
    conn.commit()
    conn.close()

def get_products(search=None, min_price=None, max_price=None):
    conn = get_connection()
    cur = conn.cursor()

    q = """
        SELECT p.*, u.username AS farmer_name
        FROM products p
        JOIN users u ON p.farmer_id = u.id
        WHERE 1=1
    """
    params = []

    if search:
        q += " AND (p.title LIKE ? OR p.description LIKE ?)"
        s = f"%{search}%"
        params += [s, s]

    if min_price:
        q += " AND p.price >= ?"
        params.append(min_price)

    if max_price:
        q += " AND p.price <= ?"
        params.append(max_price)

    cur.execute(q, params)
    rows = cur.fetchall()
    conn.close()
    return rows

def get_products_by_farmer(farmer_id):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM products WHERE farmer_id=?", (farmer_id,))
    rows = cur.fetchall()
    conn.close()
    return rows

# -----------------------------------------------------------
# SESSION STATE
# -----------------------------------------------------------
if "user" not in st.session_state:
    st.session_state.user = None

if "cart" not in st.session_state:
    st.session_state.cart = {}

# -----------------------------------------------------------
# SIDEBAR (LOGIN / REGISTER)
# -----------------------------------------------------------
st.sidebar.title("🌿 FarmConnect")

if st.session_state.user:
    st.sidebar.success(f"Logged in as: {st.session_state.user['username']}")
    st.sidebar.info(f"Role: {st.session_state.user['role']}")

    if st.sidebar.button("Logout"):
        st.session_state.user = None
        st.session_state.cart = {}

else:
    mode = st.sidebar.selectbox("Select", ["Login", "Register"])

    with st.sidebar.form("auth"):
        u = st.text_input("Username")
        p = st.text_input("Password", type="password")
        role = None

        if mode == "Register":
            role = st.selectbox("Role", ["farmer", "buyer"])

        submit = st.form_submit_button("Submit")

        if submit:
            if mode == "Register":
                ok, msg = register_user(u, p, role)
                st.sidebar.info(msg)
            else:
                ok, user = login_user(u, p)
                if ok:
                    st.session_state.user = user
                else:
                    st.sidebar.error(user)

# -----------------------------------------------------------
# MAIN PAGES
# -----------------------------------------------------------
st.title("🌾 FarmConnect — Local Farmers, Direct Buyers")

tabs = st.tabs(["🌍 Marketplace", "👨‍🌾 Farmer Dashboard", "🛒 My Cart"])

# -----------------------------------------------------------
# 1. MARKETPLACE
# -----------------------------------------------------------
with tabs[0]:
    st.header("🌍 Marketplace")

    col1, col2 = st.columns([3, 1])
    search = col2.text_input("Search")
    min_p = col2.number_input("Min Price", min_value=0.0)
    max_p = col2.number_input("Max Price", min_value=0.0)

    products = get_products(search, min_p, max_p)

    if not products:
        st.info("No products found.")
    else:
        for p in products:
            p = dict(p)

            st.markdown('<div class="product-card">', unsafe_allow_html=True)
            with st.container():

                colA, colB, colC = st.columns([1, 3, 1])

                # Image
                try:
                    img = Image.open(p["image_path"])
                    colA.image(img, use_column_width=True)
                except:
                    colA.write("No image")

                colB.markdown(f"### {p['title']}")
                colB.write(p["description"])
                colB.write(f"**Farmer:** {p['farmer_name']}  ")
                colB.write(f"**Price:** ₹{p['price']}  |  Stock: {p['quantity']}")

                qty = colC.number_input("Qty", min_value=0, max_value=p["quantity"], key=f"q{p['id']}")

                if st.session_state.user and st.session_state.user["role"] == "buyer":
                    if colC.button("Add to cart", key=f"add{p['id']}"):
                        if qty > 0:
                            st.session_state.cart[str(p["id"])] = qty
                            st.success("Added to cart")
                        else:
                            st.warning("Select quantity")

            st.markdown('</div>', unsafe_allow_html=True)

# -----------------------------------------------------------
# 2. FARMER DASHBOARD
# -----------------------------------------------------------
with tabs[1]:
    if not st.session_state.user or st.session_state.user["role"] != "farmer":
        st.warning("Login as a farmer to access this section.")
    else:
        st.header("👨‍🌾 Farmer Dashboard")

        st.subheader("Add New Product")
        with st.form("add_product", clear_on_submit=True):
            title = st.text_input("Title")
            desc = st.text_area("Description")
            price = st.number_input("Price", min_value=0.0)
            qty = st.number_input("Quantity", min_value=0)
            img_file = st.file_uploader("Upload Image", type=["jpg", "jpeg", "png"])
            submit_p = st.form_submit_button("Add Product")

            if submit_p:
                if img_file:
                    add_product(
                        st.session_state.user["id"],
                        title, desc, price, qty,
                        img_file.getvalue(), img_file.name
                    )
                    st.success("Product added successfully!")
                else:
                    st.error("Upload an image")

        st.subheader("Your Products")
        items = get_products_by_farmer(st.session_state.user["id"])

        for r in items:
            r = dict(r)
            st.markdown('<div class="product-card">', unsafe_allow_html=True)

            try:
                img = Image.open(r["image_path"])
                st.image(img, width=200)
            except:
                st.write("No image")

            st.write(f"### {r['title']}")
            st.write(r["description"])
            st.write(f"Price: ₹{r['price']}  |  Qty: {r['quantity']}")

            if st.button("Delete", key=f"del{r['id']}"):
                conn = get_connection()
                conn.execute("DELETE FROM products WHERE id=?", (r["id"],))
                conn.commit()
                conn.close()
                st.experimental_rerun()

            st.markdown('</div>', unsafe_allow_html=True)

# -----------------------------------------------------------
# 3. CART
# -----------------------------------------------------------
with tabs[2]:
    st.header("🛒 My Cart")

    if not st.session_state.user or st.session_state.user["role"] != "buyer":
        st.warning("Login as a buyer to use cart.")
    else:
        if not st.session_state.cart:
            st.info("Your cart is empty")
        else:
            conn = get_connection()
            cur = conn.cursor()

            total = 0
            rows = []

            for pid, qty in st.session_state.cart.items():
                cur.execute("SELECT * FROM products WHERE id=?", (pid,))
                r = cur.fetchone()
                if r:
                    r = dict(r)
                    subtotal = r["price"] * qty
                    rows.append((r["title"], qty, r["price"], subtotal))
                    total += subtotal

            st.table(pd.DataFrame(rows, columns=["Product", "Qty", "Price", "Subtotal"]))
            st.write(f"### Total: ₹{total}")

            if st.button("Checkout"):
                st.success("Order placed successfully!")
                st.session_state.cart = {}

# -----------------------------------------------------------
# END
# -----------------------------------------------------------
