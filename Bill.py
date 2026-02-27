import streamlit as st
import pandas as pd
import sqlite3
from datetime import datetime
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import inch
from io import BytesIO

st.set_page_config(layout="wide")
st.title("Professional Billing System")

# ==============================
# SESSION INITIALIZATION
# ==============================
if "invoice_items" not in st.session_state:
    st.session_state["invoice_items"] = []

if "invoice_no" not in st.session_state:
    st.session_state["invoice_no"] = None

# ==============================
# DATABASE SETUP
# ==============================
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

    c.execute("SELECT COUNT(*) FROM invoices")
    serial = c.fetchone()[0] + 1
    conn.close()

    return f"INV/{fy}/{serial:04d}"

if st.session_state["invoice_no"] is None:
    st.session_state["invoice_no"] = generate_invoice_number()

# ==============================
# CUSTOMER DETAILS
# ==============================
st.subheader("Customer Details")

col1, col2 = st.columns(2)

with col1:
    customer_name = st.text_input("Customer Name")
    phone = st.text_input("Phone")

with col2:
    address = st.text_area("Address")
    invoice_date = st.date_input("Invoice Date", datetime.today())

# ==============================
# ADD ITEM
# ==============================
st.subheader("Add Item")

with st.form("add_item_form", clear_on_submit=True):

    col1, col2, col3 = st.columns([3,1,1])

    product = col1.text_input("Product Name")
    qty = col2.number_input("Quantity", min_value=1, step=1)
    rate = col3.number_input("Rate", min_value=0.0)

    submitted = st.form_submit_button("Add Item")

    if submitted:
        if product.strip() == "":
            st.warning("Enter product name")
        else:
            st.session_state["invoice_items"].append({
                "Product": product,
                "Quantity": qty,
                "Rate": rate,
                "Total": qty * rate
            })

# ==============================
# DISPLAY ITEMS
# ==============================
items = st.session_state.get("invoice_items", [])

if len(items) > 0:

    st.subheader("Current Items")

    for i, item in enumerate(items):

        col1, col2, col3, col4, col5 = st.columns([3,1,1,1,1])

        col1.write(item["Product"])
        col2.write(item["Quantity"])
        col3.write(f"₹ {item['Rate']:.2f}")
        col4.write(f"₹ {item['Total']:.2f}")

        if col5.button("❌", key=f"delete_{i}"):
            st.session_state["invoice_items"].pop(i)
            st.rerun()

    df = pd.DataFrame(items)

    subtotal = df["Total"].sum()
    cgst = subtotal * 0.09
    sgst = subtotal * 0.09
    total = subtotal + cgst + sgst

    st.markdown("---")
    st.write(f"Subtotal: ₹ {subtotal:.2f}")
    st.write(f"CGST (9%): ₹ {cgst:.2f}")
    st.write(f"SGST (9%): ₹ {sgst:.2f}")
    st.write(f"Final Total: ₹ {total:.2f}")

    # ==========================
    # SAVE INVOICE
    # ==========================
    if st.button("Save Invoice"):

        if not customer_name.strip():
            st.error("Customer name required")
        else:
            conn = get_connection()
            c = conn.cursor()

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
            conn.close()

            st.success("Invoice Saved Successfully")

    # ==========================
    # GENERATE PDF (MEMORY SAFE)
    # ==========================
    if st.button("Generate PDF"):

        buffer = BytesIO()
        doc = SimpleDocTemplate(buffer)
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
                f"₹ {item['Rate']:.2f}",
                f"₹ {item['Total']:.2f}"
            ])

        table_data.append(["", "", "Subtotal", f"₹ {subtotal:.2f}"])
        table_data.append(["", "", "CGST (9%)", f"₹ {cgst:.2f}"])
        table_data.append(["", "", "SGST (9%)", f"₹ {sgst:.2f}"])
        table_data.append(["", "", "Total", f"₹ {total:.2f}"])

        table = Table(table_data)
        table.setStyle(TableStyle([
            ("BACKGROUND", (0,0), (-1,0), colors.lightgrey),
            ("GRID", (0,0), (-1,-1), 0.5, colors.grey),
            ("ALIGN", (1,1), (-1,-1), "RIGHT"),
        ]))

        elements.append(table)
        doc.build(elements)
        buffer.seek(0)

        st.download_button(
            label="Download Invoice PDF",
            data=buffer,
            file_name=f"{st.session_state['invoice_no']}.pdf",
            mime="application/pdf"
        )

# ==============================
# CLEAR INVOICE
# ==============================
if st.button("Clear Invoice"):
    st.session_state["invoice_items"] = []
    st.session_state["invoice_no"] = generate_invoice_number()
    st.rerun()

# ==============================
# INVOICE HISTORY + VIEW
# ==============================
# ==============================
# INVOICE HISTORY + VIEW + DELETE
# ==============================
st.markdown("---")
st.subheader("Invoice History")

conn = get_connection()
history = pd.read_sql_query("SELECT * FROM invoices ORDER BY id DESC", conn)
conn.close()

if not history.empty:

    for index, row in history.iterrows():

        col1, col2, col3, col4, col5, col6 = st.columns([2,2,2,2,1,1])

        col1.write(row["invoice_no"])
        col2.write(row["customer_name"])
        col3.write(row["date"])
        col4.write(f"₹ {row['total']:.2f}")

        # ================= VIEW BUTTON =================
        if col5.button("View", key=f"view_{row['invoice_no']}"):

            conn = get_connection()
            items = pd.read_sql_query(
                "SELECT * FROM invoice_items WHERE invoice_no=?",
                conn,
                params=(row["invoice_no"],)
            )
            conn.close()

            st.subheader(f"Invoice Preview - {row['invoice_no']}")
            st.dataframe(items)

            buffer = BytesIO()
            doc = SimpleDocTemplate(buffer)
            elements = []
            styles = getSampleStyleSheet()

            elements.append(Paragraph(f"Invoice No: {row['invoice_no']}", styles["Heading2"]))
            elements.append(Paragraph(f"Customer: {row['customer_name']}", styles["Normal"]))
            elements.append(Paragraph(f"Date: {row['date']}", styles["Normal"]))
            elements.append(Spacer(1, 0.3 * inch))

            table_data = [["Product", "Qty", "Rate", "Total"]]

            for _, item in items.iterrows():
                table_data.append([
                    item["product"],
                    item["quantity"],
                    f"₹ {item['rate']:.2f}",
                    f"₹ {item['total']:.2f}"
                ])

            table_data.append(["", "", "Grand Total", f"₹ {row['total']:.2f}"])

            table = Table(table_data)
            table.setStyle(TableStyle([
                ("BACKGROUND", (0,0), (-1,0), colors.lightgrey),
                ("GRID", (0,0), (-1,-1), 0.5, colors.grey),
                ("ALIGN", (1,1), (-1,-1), "RIGHT"),
            ]))

            elements.append(table)
            doc.build(elements)
            buffer.seek(0)

            st.download_button(
                label="Download This Invoice",
                data=buffer,
                file_name=f"{row['invoice_no']}.pdf",
                mime="application/pdf"
            )

        # ================= DELETE BUTTON =================
        if col6.button("Delete", key=f"delete_invoice_{row['invoice_no']}"):

            conn = get_connection()
            c = conn.cursor()

            # Delete child records first
            c.execute("DELETE FROM invoice_items WHERE invoice_no=?", (row["invoice_no"],))

            # Delete parent record
            c.execute("DELETE FROM invoices WHERE invoice_no=?", (row["invoice_no"],))

            conn.commit()
            conn.close()

            st.success("Invoice Deleted Successfully")
            st.rerun()

else:
    st.info("No invoices found")


