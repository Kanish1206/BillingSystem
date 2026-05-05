import streamlit as st
import pandas as pd
import sqlite3
from datetime import datetime
from jinja2 import Environment, FileSystemLoader

# ==============================
# PAGE CONFIGURATION
# ==============================
st.set_page_config(layout="wide", page_title="Tirupati Petroleum", page_icon="⛽")

# ==============================
# CUSTOM CSS & ANIMATIONS
# ==============================
st.markdown("""
    <style>
        /* Smooth Fade-In Animation for the main container */
        .block-container {
            animation: fadeIn 0.8s ease-in-out;
        }
        @keyframes fadeIn {
            0% { opacity: 0; transform: translateY(10px); }
            100% { opacity: 1; transform: translateY(0); }
        }
        
        /* Modern Gradient Title */
        .main-title {
            background: -webkit-linear-gradient(45deg, #FF4B2B, #FF416C);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            font-size: 3rem !important;
            font-weight: 800;
            margin-bottom: 0px;
        }
        
        /* Button Hover Effects */
        div.stButton > button {
            transition: all 0.3s ease;
            border-radius: 8px;
            font-weight: 600;
        }
        div.stButton > button:hover {
            transform: translateY(-2px);
            box-shadow: 0 4px 12px rgba(0,0,0,0.15);
        }
        
        /* Delete Button specific styling */
        button[kind="secondary"]:hover {
            border-color: #ff4b4b;
            color: #ff4b4b;
        }
    </style>
""", unsafe_allow_html=True)

st.markdown('<h1 class="main-title">⛽ Tirupati Petroleum Billing</h1>', unsafe_allow_html=True)
st.markdown("---")

# ==============================
# SESSION INITIALIZATION & RATES
# ==============================
if "invoice_items" not in st.session_state:
    st.session_state["invoice_items"] = []
if "invoice_no" not in st.session_state:
    st.session_state["invoice_no"] = None
if "petrol_rate" not in st.session_state:
    st.session_state["petrol_rate"] = 106.00
if "diesel_rate" not in st.session_state:
    st.session_state["diesel_rate"] = 94.00
if "viewing_invoice" not in st.session_state:
    st.session_state["viewing_invoice"] = None

# ==============================
# SIDEBAR: MANAGE FUEL RATES
# ==============================
with st.sidebar:
    st.image("https://cdn-icons-png.flaticon.com/512/3063/3063822.png", width=80) # Generic pump icon
    st.header("📈 Today's Rates")
    st.markdown("Rates apply automatically to new bills.")
    
    with st.container(border=True):
        new_petrol = st.number_input("Petrol (₹/L)", value=st.session_state["petrol_rate"], format="%.2f", step=0.10)
        new_diesel = st.number_input("Diesel (₹/L)", value=st.session_state["diesel_rate"], format="%.2f", step=0.10)

        if st.button("Update Rates", use_container_width=True):
            st.session_state["petrol_rate"] = new_petrol
            st.session_state["diesel_rate"] = new_diesel
            st.success("Rates updated!")

# ==============================
# DATABASE SETUP
# ==============================
DB_FILE = "fuel_database.db"

def get_connection():
    return sqlite3.connect(DB_FILE, check_same_thread=False)

def init_db():
    conn = get_connection()
    c = conn.cursor()
    c.execute("""
    CREATE TABLE IF NOT EXISTS invoices (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        invoice_no TEXT UNIQUE,
        customer_name TEXT,
        phone TEXT,
        vehicle_no TEXT,
        date TEXT,
        subtotal REAL,
        cgst REAL,
        sgst REAL,
        total REAL
    )
    """)
    c.execute("""
    CREATE TABLE IF NOT EXISTS invoice_items (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        invoice_no TEXT,
        product TEXT,
        quantity REAL,
        rate REAL,
        total REAL
    )
    """)
    conn.commit()
    conn.close()

init_db()

# ==============================
# GENERATE INVOICE NUMBER
# ==============================
def generate_invoice_number():
    conn = get_connection()
    c = conn.cursor()
    today = datetime.today()
    year = today.year
    if today.month < 4:
        fy = f"{year-1}-{str(year)[-2:]}"
    else:
        fy = f"{year}-{str(year+1)[-2:]}"

    c.execute("SELECT MAX(id) FROM invoices")
    result = c.fetchone()[0]
    serial = (result if result else 0) + 1
    conn.close()
    return f"INV/{fy}/{serial:04d}"

if st.session_state["invoice_no"] is None:
    st.session_state["invoice_no"] = generate_invoice_number()

# ==============================
# MAIN DASHBOARD: BILLING ENTRY
# ==============================
col_main, col_summary = st.columns([2.5, 1.5], gap="large")

with col_main:
    # --- CUSTOMER DETAILS CARD ---
    with st.container(border=True):
        st.subheader("📝 Customer & Vehicle Details")
        c1, c2 = st.columns(2)
        with c1:
            customer_name = st.text_input("Customer Name", placeholder="e.g. Rahul Sharma or 'Cash'")
            phone = st.text_input("Phone Number", placeholder="10-digit number")
        with c2:
            vehicle_no = st.text_input("Vehicle Number", placeholder="e.g. MH 12 AB 1234")
            invoice_date = st.date_input("Invoice Date", datetime.today())

    # --- ADD PRODUCTS CARD ---
    with st.container(border=True):
        st.subheader("⛽ Add Fuel / Products")
        p1, p2, p3, p4 = st.columns([2, 1.5, 1.5, 1])
        
        product = p1.selectbox("Product", ["Petrol", "Diesel", "Engine Oil", "Coolant", "Other"])
        
        if product == "Petrol":
            auto_rate = st.session_state["petrol_rate"]
        elif product == "Diesel":
            auto_rate = st.session_state["diesel_rate"]
        else:
            auto_rate = 0.0

        qty = p2.number_input("Volume/Qty", min_value=0.01, value=1.00, step=0.50, format="%.2f")
        rate = p3.number_input("Rate (₹)", value=float(auto_rate), min_value=0.0, format="%.2f")

        p4.markdown("<br>", unsafe_allow_html=True) # Alignment fix
        if p4.button("➕ Add", use_container_width=True, type="primary"):
            st.session_state["invoice_items"].append({
                "Product": product,
                "Quantity": qty,
                "Rate": rate,
                "Total": qty * rate
            })
            st.rerun()

with col_summary:
    # --- BILL SUMMARY CARD ---
    with st.container(border=True):
        st.subheader("🛒 Current Bill Summary")
        items = st.session_state.get("invoice_items", [])
        
        if len(items) == 0:
            st.info("No items added yet.")
        else:
            for i, item in enumerate(items):
                i1, i2, i3 = st.columns([3, 2, 1])
                i1.write(f"**{item['Product']}** ({item['Quantity']:.1f}L)")
                i2.write(f"₹{item['Total']:.2f}")
                if i3.button("❌", key=f"del_{i}", help="Remove item"):
                    st.session_state["invoice_items"].pop(i)
                    st.rerun()
            
            st.markdown("---")
            df = pd.DataFrame(items)
            subtotal = df["Total"].sum()
            cgst = subtotal * 0.09
            sgst = subtotal * 0.09
            total = subtotal + cgst + sgst
            
            st.write(f"**Subtotal:** ₹ {subtotal:.2f}")
            st.write(f"**CGST (9%):** ₹ {cgst:.2f}")
            st.write(f"**SGST (9%):** ₹ {sgst:.2f}")
            st.markdown(f"### 🧾 Total: ₹ {total:.2f}")

            s1, s2 = st.columns(2)
            with s1:
                if st.button("💾 Save Bill", use_container_width=True, type="primary"):
                    if not customer_name.strip(): customer_name = "Cash Customer"
                    conn = get_connection()
                    c = conn.cursor()
                    try:
                        c.execute("""
                        INSERT INTO invoices (invoice_no, customer_name, phone, vehicle_no, date, subtotal, cgst, sgst, total)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """, (st.session_state["invoice_no"], customer_name, phone, vehicle_no, str(invoice_date), subtotal, cgst, sgst, total))
                        
                        for item in items:
                            c.execute("""
                            INSERT INTO invoice_items (invoice_no, product, quantity, rate, total)
                            VALUES (?, ?, ?, ?, ?)
                            """, (st.session_state["invoice_no"], item["Product"], item["Quantity"], item["Rate"], item["Total"]))
                        
                        conn.commit()
                        st.toast(f"Invoice {st.session_state['invoice_no']} Saved!", icon="✅")
                        st.session_state["invoice_items"] = []
                        st.session_state["invoice_no"] = generate_invoice_number()
                        st.rerun()
                    except sqlite3.IntegrityError:
                        st.error("This invoice has already been saved.")
                    finally:
                        conn.close()
            with s2:
                if st.button("🗑️ Clear", use_container_width=True):
                    st.session_state["invoice_items"] = []
                    st.rerun()

# ==============================
# INVOICE HISTORY & VIEW
# ==============================
st.markdown("---")
st.subheader("🗂️ Invoice History & Records")

conn = get_connection()
history = pd.read_sql_query("SELECT * FROM invoices ORDER BY id DESC LIMIT 50", conn)
conn.close()

if not history.empty:
    # --- TABLE HEADER ---
    h1, h2, h3, h4, h5 = st.columns([2, 2, 2, 2, 1])
    h1.markdown("**Invoice No.**")
    h2.markdown("**Customer Name**")
    h3.markdown("**Date**")
    h4.markdown("**Total Amount**")
    h5.markdown("**Action**")
    st.markdown("---")

    for index, row in history.iterrows():
        # --- ROW DATA ---
        c1, c2, c3, c4, c5 = st.columns([2, 2, 2, 2, 1])
        c1.write(f"🧾 {row['invoice_no']}")
        c2.write(f"👤 {row['customer_name']}")
        c3.write(f"📅 {row['date']}")
        c4.write(f"💰 ₹ {row['total']:.2f}")
        
        # View Button Logic (Toggles the view state)
        button_label = "⬇️ Close" if st.session_state["viewing_invoice"] == row["invoice_no"] else "👁️ View"
        if c5.button(button_label, key=f"view_btn_{row['invoice_no']}", use_container_width=True):
            if st.session_state["viewing_invoice"] == row["invoice_no"]:
                st.session_state["viewing_invoice"] = None # Close if already viewing
            else:
                st.session_state["viewing_invoice"] = row["invoice_no"] # Open this specific invoice
            st.rerun()

        # --- EXPANDED DETAILS (Only shows if "View" is clicked) ---
        if st.session_state["viewing_invoice"] == row['invoice_no']:
            with st.container(border=True):
                # Fetch items for this specific invoice
                conn = get_connection()
                items_df = pd.read_sql_query("SELECT product as Product, quantity as Quantity, rate as Rate, total as Total FROM invoice_items WHERE invoice_no=?", conn, params=(row["invoice_no"],))
                conn.close()

                v_col1, v_col2 = st.columns([2, 1])
                
                with v_col1:
                    st.markdown("**Invoice Items:**")
                    st.dataframe(items_df, use_container_width=True, hide_index=True)
                
                with v_col2:
                    st.markdown("**Invoice Details:**")
                    st.write(f"**Vehicle No:** {row['vehicle_no'] if row['vehicle_no'] else 'N/A'}")
                    st.write(f"**Phone:** {row['phone'] if row['phone'] else 'N/A'}")
                    st.write(f"**Subtotal:** ₹{row['subtotal']:.2f}")
                    st.write(f"**Taxes (18%):** ₹{row['cgst'] + row['sgst']:.2f}")
                    st.markdown(f"#### **Grand Total: ₹{row['total']:.2f}**")
                    
                    # Setup Jinja2 Template Download
                    env = Environment(loader=FileSystemLoader('.'))
                    try:
                        template = env.get_template('invoice_template.html')
                        items_list = items_df.to_dict('records')
                        html_content = template.render(
                            invoice_no=row['invoice_no'],
                            customer_name=row['customer_name'] if row['customer_name'] else "Cash Customer",
                            vehicle_no=row['vehicle_no'] if row['vehicle_no'] else "N/A",
                            date=row['date'],
                            items=items_list,
                            subtotal=row['subtotal'],
                            cgst=row['cgst'],
                            sgst=row['sgst'],
                            total_amt=row['total']
                        )
                        
                        st.download_button(
                            label="⬇️ Download HTML Invoice",
                            data=html_content,
                            file_name=f"Tirupati_Invoice_{row['invoice_no'].replace('/', '_')}.html",
                            mime="text/html",
                            key=f"dl_{row['invoice_no']}",
                            use_container_width=True,
                            type="primary"
                        )
                    except Exception as e:
                        st.warning(f"Template error: Ensure 'invoice_template.html' exists in the directory.")

                    if st.button("🗑️ Delete Invoice", key=f"del_inv_{row['invoice_no']}", use_container_width=True):
                        conn = get_connection()
                        c = conn.cursor()
                        c.execute("DELETE FROM invoice_items WHERE invoice_no=?", (row["invoice_no"],))
                        c.execute("DELETE FROM invoices WHERE invoice_no=?", (row["invoice_no"],))
                        conn.commit()
                        conn.close()
                        
                        st.session_state["viewing_invoice"] = None # Reset view state after deleting
                        st.toast(f"Deleted {row['invoice_no']}", icon="🗑️")
                        st.rerun()
            st.markdown("---") # Visual separator beneath expanded view
else:
    st.info("No invoices found. Start billing to see your history here.")
