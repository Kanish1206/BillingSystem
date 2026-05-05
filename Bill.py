 import streamlit as st

import pandas as pd

import sqlite3

from datetime import datetime

from jinja2 import Environment, FileSystemLoader


st.set_page_config(layout="wide", page_title="Tirupati Petroleum Billing", page_icon="⛽")

st.title("⛽ Tirupati Petroleum - Billing System")


# ==============================

# SESSION INITIALIZATION & RATES

# ==============================

if "invoice_items" not in st.session_state:

    st.session_state["invoice_items"] = []


if "invoice_no" not in st.session_state:

    st.session_state["invoice_no"] = None


# Default rates (can be updated in sidebar)

if "petrol_rate" not in st.session_state:

    st.session_state["petrol_rate"] = 106.00

if "diesel_rate" not in st.session_state:

    st.session_state["diesel_rate"] = 94.00


# ==============================

# SIDEBAR: MANAGE FUEL RATES

# ==============================

st.sidebar.header("📈 Today's Fuel Rates")

st.sidebar.markdown("Update the rates below. They will automatically apply to new billing items.")


new_petrol = st.sidebar.number_input("Petrol Rate (₹/L)", value=st.session_state["petrol_rate"], format="%.2f", step=0.10)

new_diesel = st.sidebar.number_input("Diesel Rate (₹/L)", value=st.session_state["diesel_rate"], format="%.2f", step=0.10)


if st.sidebar.button("Update Rates"):

    st.session_state["petrol_rate"] = new_petrol

    st.session_state["diesel_rate"] = new_diesel

    st.sidebar.success("Rates successfully updated!")


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

# CUSTOMER DETAILS

# ==============================

st.subheader("📝 Customer & Vehicle Details")


col1, col2 = st.columns(2)


with col1:

    customer_name = st.text_input("Customer Name", placeholder="e.g. Rahul Sharma or 'Cash'")

    phone = st.text_input("Phone Number")


with col2:

    vehicle_no = st.text_input("Vehicle Number", placeholder="e.g. MH 12 AB 1234")

    invoice_date = st.date_input("Invoice Date", datetime.today())


# ==============================

# ADD ITEM

# ==============================

st.markdown("---")

st.subheader("⛽ Add Fuel / Products")


col1, col2, col3, col4 = st.columns([2, 1.5, 1.5, 1])


product = col1.selectbox("Product", ["Petrol", "Diesel", "Engine Oil", "Coolant", "Other"])


if product == "Petrol":

    auto_rate = st.session_state["petrol_rate"]

elif product == "Diesel":

    auto_rate = st.session_state["diesel_rate"]

else:

    auto_rate = 0.0


qty = col2.number_input("Volume/Qty (Liters/Nos)", min_value=0.01, value=1.00, step=0.50, format="%.2f")

rate = col3.number_input("Rate (₹)", value=float(auto_rate), min_value=0.0, format="%.2f")


if col4.button("➕ Add to Bill", use_container_width=True):

    st.session_state["invoice_items"].append({

        "Product": product,

        "Quantity": qty,

        "Rate": rate,

        "Total": qty * rate

    })

    st.rerun()


# ==============================

# DISPLAY ITEMS & BILLING

# ==============================

items = st.session_state.get("invoice_items", [])


if len(items) > 0:


    st.markdown("### 🛒 Current Bill Items")


    for i, item in enumerate(items):

        c1, c2, c3, c4, c5 = st.columns([3, 1.5, 1.5, 1.5, 1])

        c1.write(f"**{item['Product']}**")

        c2.write(f"{item['Quantity']:.2f} L/U")

        c3.write(f"₹ {item['Rate']:.2f}")

        c4.write(f"**₹ {item['Total']:.2f}**")

        

        if c5.button("❌", key=f"delete_{i}"):

            st.session_state["invoice_items"].pop(i)

            st.rerun()


    df = pd.DataFrame(items)

    subtotal = df["Total"].sum()

    

    cgst = subtotal * 0.09

    sgst = subtotal * 0.09

    total = subtotal + cgst + sgst


    st.markdown("---")

    st.write(f"**Subtotal:** ₹ {subtotal:.2f}")

    st.write(f"**CGST (9%):** ₹ {cgst:.2f}")

    st.write(f"**SGST (9%):** ₹ {sgst:.2f}")

    st.subheader(f"Grand Total: ₹ {total:.2f}")


    # ==========================

    # SAVE INVOICE

    # ==========================

    col_save, col_clear = st.columns(2)

    

    with col_save:

        if st.button("💾 Save Invoice", use_container_width=True):

            if not customer_name.strip():

                customer_name = "Cash Customer"

                

            conn = get_connection()

            c = conn.cursor()


            try:

                c.execute("""

                INSERT INTO invoices

                (invoice_no, customer_name, phone, vehicle_no, date, subtotal, cgst, sgst, total)

                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)

                """, (

                    st.session_state["invoice_no"], customer_name, phone, vehicle_no,

                    str(invoice_date), subtotal, cgst, sgst, total

                ))


                for item in items:

                    c.execute("""

                    INSERT INTO invoice_items

                    (invoice_no, product, quantity, rate, total)

                    VALUES (?, ?, ?, ?, ?)

                    """, (

                        st.session_state["invoice_no"], item["Product"],

                        item["Quantity"], item["Rate"], item["Total"]

                    ))


                conn.commit()

                st.success(f"Invoice {st.session_state['invoice_no']} Saved Successfully!")

                

                st.session_state["invoice_items"] = []

                st.session_state["invoice_no"] = generate_invoice_number()

                st.rerun()

                

            except sqlite3.IntegrityError:

                st.error("This invoice has already been saved.")

            finally:

                conn.close()


    with col_clear:

        if st.button("🗑️ Clear Current Bill", use_container_width=True):

            st.session_state["invoice_items"] = []

            st.rerun()


# ==============================

# INVOICE HISTORY + VIEW

# ==============================

st.markdown("---")

st.subheader("🗂️ Invoice History")


conn = get_connection()

history = pd.read_sql_query("SELECT * FROM invoices ORDER BY id DESC LIMIT 50", conn)

conn.close()


if not history.empty:


    for index, row in history.iterrows():


        col1, col2, col3, col4, col5, col6 = st.columns([1.5, 2, 1.5, 1.5, 1.5, 1])


        col1.write(f"**{row['invoice_no']}**")

        col2.write(row["customer_name"])

        col3.write(row["vehicle_no"] if row["vehicle_no"] else "-")

        col4.write(f"**₹ {row['total']:.2f}**")


        # ================= VIEW & DOWNLOAD HTML =================

        if col5.button("Download HTML", key=f"view_{row['invoice_no']}"):


            conn = get_connection()

            items_df = pd.read_sql_query(

                "SELECT * FROM invoice_items WHERE invoice_no=?",

                conn, params=(row["invoice_no"],)

            )

            conn.close()


            # 1. Setup Jinja2 to read from the current folder

            env = Environment(loader=FileSystemLoader('.'))

            template = env.get_template('invoice_template.html')


            # 2. Convert dataframe items to a list of dictionaries for HTML

            items_list = items_df.to_dict('records')


            # 3. Render the HTML string by passing Python variables into the template

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


            # 4. Create a download button for the HTML file

            st.download_button(

                label="⬇️ Save Invoice",

                data=html_content,

                file_name=f"Tirupati_Invoice_{row['invoice_no'].replace('/', '_')}.html",

                mime="text/html",

                key=f"dl_{row['invoice_no']}"

            )


        # ================= DELETE BUTTON =================

        if col6.button("Delete", key=f"delete_invoice_{row['invoice_no']}"):

            conn = get_connection()

            c = conn.cursor()

            c.execute("DELETE FROM invoice_items WHERE invoice_no=?", (row["invoice_no"],))

            c.execute("DELETE FROM invoices WHERE invoice_no=?", (row["invoice_no"],))

            conn.commit()

            conn.close()

            st.rerun()

else:

    st.info("No invoices found. Start billing to see history here.") 
