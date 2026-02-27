import streamlit as st
import pandas as pd
import sqlite3
from datetime import datetime
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import inch

st.set_page_config(layout="wide")
st.title("Professional Billing System")

# =========================
# SAFE SESSION INIT
# =========================
if "invoice_items" not in st.session_state:
    st.session_state["invoice_items"] = []

if "invoice_no" not in st.session_state:
    st.session_state["invoice_no"] = None

# =========================
# DATABASE
# =========================
DB_FILE = "database.db"

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
        address TEXT,
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
        quantity INTEGER,
        rate REAL,
        total REAL
    )
    """)

    conn.commit()
    conn.close()

init_db()

# =========================
# INVOICE NUMBER
# =========================
def generate_invoice_number():
    conn = get_connection()
    c = conn.cursor()

    today = datetime.today()
    year = today.year
    if today.month < 4:
        fy = f"{year-1}-{str(year)[-2:]}"
    else:
        fy = f"{year}-{str(year+1)[-2:]}"

    c.execute("SELECT COUNT(*) FROM invoices")
    serial = c.fetchone()[0] + 1
    conn.close()

    return f"INV/{fy}/{serial:04d}"

if st.session_state["invoice_no"] is None:
    st.session_state["invoice_no"] = generate_invoice_number()

# =========================
# CUSTOMER DETAILS
# =========================
st.subheader("Customer Details")

col1, col2 = st.columns(2)

with col1:
    customer_name = st.text_input("Customer Name")
    phone = st.text_input("Phone")

with col2:
    address = st.text_area("Address")
    invoice_date = st.date_input("Invoice Date", datetime.today())

# =========================
# ADD ITEM
# =========================
st.subheader("Add Item")

col1, col2, col3 = st.columns(3)

with col1:
    product = st.text_input("Product Name")

with col2:
    qty = st.number_input("Quantity", min_value=1, step=1)

with col3:
    rate = st.number_input("Rate", min_value=0.0)

if st.button("Add Item"):
    if product.strip():
        st.session_state["invoice_items"].append({
            "Product": product,
            "Quantity": qty,
            "Rate": rate,
            "Total": qty * rate
        })

# =========================
# DISPLAY ITEMS
# =========================
items = st.session_state.get("invoice_items", [])

if isinstance(items, list) and len(items) > 0:

    df = pd.DataFrame(items)

    subtotal = df["Total"].sum()
    cgst = subtotal * 0.09
    sgst = subtotal * 0.09
    total = subtotal + cgst + sgst

    st.dataframe(df)

    st.write(f"Subtotal: ₹ {subtotal:.2f}")
    st.write(f"CGST (9%): ₹ {cgst:.2f}")
    st.write(f"SGST (9%): ₹ {sgst:.2f}")
    st.write(f"Final Total: ₹ {total:.2f}")

    # =========================
    # SAVE INVOICE
    # =========================
    if st.button("Save Invoice"):

        if not customer_name.strip():
            st.error("Customer name required")
        else:
            conn = get_connection()
            c = conn.cursor()

            try:
                c.execute("""
                INSERT INTO invoices
                (invoice_no, customer_name, phone, address, date, subtotal, cgst, sgst, total)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    st.session_state["invoice_no"],
                    customer_name,
                    phone,
                    address,
                    str(invoice_date),
                    subtotal,
                    cgst,
                    sgst,
                    total
                ))

                for item in items:
                    c.execute("""
                    INSERT INTO invoice_items
                    (invoice_no, product, quantity, rate, total)
                    VALUES (?, ?, ?, ?, ?)
                    """, (
                        st.session_state["invoice_no"],
                        item["Product"],
                        item["Quantity"],
                        item["Rate"],
                        item["Total"]
                    ))

                conn.commit()
                st.success("Invoice Saved Successfully")

            except Exception as e:
                st.error(f"Database Error: {e}")

            finally:
                conn.close()

    # =========================
    # GENERATE PDF
    # =========================
    if st.button("Generate PDF"):

        file_name = f"{st.session_state['invoice_no']}.pdf"
        doc = SimpleDocTemplate(file_name)
        elements = []

        styles = getSampleStyleSheet()

        elements.append(Paragraph(f"Invoice No: {st.session_state['invoice_no']}", styles["Heading2"]))
        elements.append(Paragraph(f"Customer: {customer_name}", styles["Normal"]))
        elements.append(Paragraph(f"Phone: {phone}", styles["Normal"]))
        elements.append(Paragraph(f"Date: {invoice_date}", styles["Normal"]))
        elements.append(Spacer(1, 0.3 * inch))

        table_data = [["Product", "Qty", "Rate", "Total"]]

        for item in items:
            table_data.append([
                item["Product"],
                item["Quantity"],
                f"{item['Rate']:.2f}",
                f"{item['Total']:.2f}"
            ])

        table_data.append(["", "", "Subtotal", f"{subtotal:.2f}"])
        table_data.append(["", "", "CGST", f"{cgst:.2f}"])
        table_data.append(["", "", "SGST", f"{sgst:.2f}"])
        table_data.append(["", "", "Total", f"{total:.2f}"])

        table = Table(table_data)
        table.setStyle(TableStyle([
            ("BACKGROUND", (0,0), (-1,0), colors.grey),
            ("GRID", (0,0), (-1,-1), 1, colors.black),
            ("ALIGN", (-1,1), (-1,-1), "RIGHT")
        ]))

        elements.append(table)
        doc.build(elements)

        with open(file_name, "rb") as f:
            st.download_button(
                "Download Invoice",
                f,
                file_name=file_name,
                mime="application/pdf"
            )

# =========================
# CLEAR BUTTON
# =========================
if st.button("Clear Invoice"):
    st.session_state["invoice_items"] = []
    st.session_state["invoice_no"] = generate_invoice_number()
    st.rerun()

# =========================
# INVOICE HISTORY
# =========================
st.markdown("---")
st.subheader("Invoice History")

conn = get_connection()
history = pd.read_sql_query("SELECT * FROM invoices ORDER BY id DESC", conn)
conn.close()

if not history.empty:
    st.dataframe(history)
else:
    st.info("No invoices found")
