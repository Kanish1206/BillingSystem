import streamlit as st
import pandas as pd
import sqlite3
from datetime import datetime
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib import colors
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib import styles
from reportlab.lib.units import inch
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfbase import pdfmetrics
import os

st.set_page_config(layout="wide")
st.title("Professional Billing System")

# =========================
# DATABASE SETUP
# =========================
conn = sqlite3.connect("database.db", check_same_thread=False)
c = conn.cursor()

c.execute("""
CREATE TABLE IF NOT EXISTS invoices (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    invoice_no TEXT,
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

# =========================
# INVOICE NUMBER
# =========================
def generate_invoice_number():
    today = datetime.today()
    year = today.year
    if today.month < 4:
        fy = f"{year-1}-{str(year)[-2:]}"
    else:
        fy = f"{year}-{str(year+1)[-2:]}"
    
    c.execute("SELECT COUNT(*) FROM invoices")
    serial = c.fetchone()[0] + 1
    
    return f"INV/{fy}/{serial:04d}"

if "items" not in st.session_state:
    st.session_state.items = []

if "invoice_no" not in st.session_state:
    st.session_state.invoice_no = generate_invoice_number()

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
        st.session_state.items.append({
            "Product": product,
            "Quantity": qty,
            "Rate": rate,
            "Total": qty * rate
        })

# =========================
# DISPLAY ITEMS
# =========================
if st.session_state.items:

    df = pd.DataFrame(st.session_state.items)
    subtotal = df["Total"].sum()
    cgst = subtotal * 0.09
    sgst = subtotal * 0.09
    total = subtotal + cgst + sgst

    st.dataframe(df)

    st.write(f"Subtotal: ₹ {subtotal:.2f}")
    st.write(f"CGST: ₹ {cgst:.2f}")
    st.write(f"SGST: ₹ {sgst:.2f}")
    st.write(f"Final Total: ₹ {total:.2f}")

    # =========================
    # SAVE INVOICE
    # =========================
    if st.button("Save Invoice"):

        if not customer_name.strip():
            st.error("Customer Name Required")
        else:
            c.execute("""
            INSERT INTO invoices 
            (invoice_no, customer_name, phone, address, date, subtotal, cgst, sgst, total)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                st.session_state.invoice_no,
                customer_name,
                phone,
                address,
                str(invoice_date),
                subtotal,
                cgst,
                sgst,
                total
            ))

            for item in st.session_state.items:
                c.execute("""
                INSERT INTO invoice_items
                (invoice_no, product, quantity, rate, total)
                VALUES (?, ?, ?, ?, ?)
                """, (
                    st.session_state.invoice_no,
                    item["Product"],
                    item["Quantity"],
                    item["Rate"],
                    item["Total"]
                ))

            conn.commit()
            st.success("Invoice Saved Successfully")

    # =========================
    # GENERATE PDF
    # =========================
    if st.button("Generate PDF"):

        file_name = f"{st.session_state.invoice_no}.pdf"
        doc = SimpleDocTemplate(file_name)
        elements = []

        style = styles.getSampleStyleSheet()
        elements.append(Paragraph(f"Invoice No: {st.session_state.invoice_no}", style["Heading2"]))
        elements.append(Paragraph(f"Customer: {customer_name}", style["Normal"]))
        elements.append(Paragraph(f"Phone: {phone}", style["Normal"]))
        elements.append(Paragraph(f"Date: {invoice_date}", style["Normal"]))
        elements.append(Spacer(1, 0.3 * inch))

        table_data = [["Product", "Qty", "Rate", "Total"]]

        for item in st.session_state.items:
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

    if st.button("Clear"):
        st.session_state.items = []
        st.session_state.invoice_no = generate_invoice_number()
        st.rerun()

# =========================
# INVOICE HISTORY
# =========================
st.markdown("---")
st.subheader("Invoice History")

c.execute("SELECT * FROM invoices ORDER BY id DESC")
rows = c.fetchall()

if rows:
    history_df = pd.DataFrame(rows, columns=[
        "ID", "Invoice No", "Customer", "Phone",
        "Address", "Date", "Subtotal", "CGST",
        "SGST", "Total"
    ])
    st.dataframe(history_df)
