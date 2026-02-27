import streamlit as st
import pandas as pd
import pdfkit
import os
from datetime import datetime
from jinja2 import Template

st.set_page_config(layout="wide")
st.title("Professional Billing System")

# -----------------------------
# Invoice Number (Financial Year Based)
# -----------------------------
def generate_invoice_number():
    today = datetime.today()
    year = today.year
    if today.month < 4:
        fy = f"{year-1}-{str(year)[-2:]}"
    else:
        fy = f"{year}-{str(year+1)[-2:]}"
    serial = len(st.session_state.items) + 1
    return f"INV/{fy}/{serial:04d}"

if "items" not in st.session_state:
    st.session_state.items = []

if "invoice_no" not in st.session_state:
    st.session_state.invoice_no = generate_invoice_number()

# -----------------------------
# Company Details (Static)
# -----------------------------
company_name = "Your Company Pvt Ltd"
company_address = "Your Company Address"
company_gstin = "22AAAAA0000A1Z5"

# -----------------------------
# Customer Details
# -----------------------------
st.subheader("Customer Details")

col1, col2 = st.columns(2)

with col1:
    customer_name = st.text_input("Customer Name")
    customer_phone = st.text_input("Phone")

with col2:
    customer_address = st.text_area("Address")
    invoice_date = st.date_input("Invoice Date", datetime.today())

# -----------------------------
# Add Product
# -----------------------------
st.subheader("Add Item")

col1, col2, col3 = st.columns(3)

with col1:
    product = st.text_input("Product Name")

with col2:
    qty = st.number_input("Quantity", min_value=1, step=1)

with col3:
    rate = st.number_input("Rate", min_value=0.0)

if st.button("Add Item"):
    if not product.strip():
        st.error("Product name required")
    else:
        st.session_state.items.append({
            "Product": product,
            "Quantity": qty,
            "Rate": rate,
            "Total": qty * rate
        })

# -----------------------------
# Display & Edit Items
# -----------------------------
if st.session_state.items:

    st.subheader("Invoice Items")

    for i, item in enumerate(st.session_state.items):
        col1, col2, col3, col4, col5 = st.columns(5)

        with col1:
            name = st.text_input("Name", item["Product"], key=f"name_{i}")
        with col2:
            q = st.number_input("Qty", value=item["Quantity"], key=f"qty_{i}")
        with col3:
            r = st.number_input("Rate", value=item["Rate"], key=f"rate_{i}")
        with col4:
            if st.button("Update", key=f"update_{i}"):
                st.session_state.items[i] = {
                    "Product": name,
                    "Quantity": q,
                    "Rate": r,
                    "Total": q * r
                }
        with col5:
            if st.button("Delete", key=f"delete_{i}"):
                st.session_state.items.pop(i)
                st.rerun()

    df = pd.DataFrame(st.session_state.items)
    subtotal = df["Total"].sum()

    st.markdown("---")

    gst_percent = 18
    cgst = subtotal * 0.09
    sgst = subtotal * 0.09
    final_total = subtotal + cgst + sgst

    st.write(f"Subtotal: ₹ {subtotal:.2f}")
    st.write(f"CGST (9%): ₹ {cgst:.2f}")
    st.write(f"SGST (9%): ₹ {sgst:.2f}")
    st.write(f"Final Total: ₹ {final_total:.2f}")

    # -----------------------------
    # Generate HTML Invoice
    # -----------------------------
    def generate_html():
        rows = ""
        for item in st.session_state.items:
            rows += f"""
            <tr>
                <td>{item['Product']}</td>
                <td>{item['Quantity']}</td>
                <td>{item['Rate']:.2f}</td>
                <td>{item['Total']:.2f}</td>
            </tr>
            """

        html_template = """
        <html>
        <head>
        <style>
            body { font-family: Arial; }
            .header { display: flex; justify-content: space-between; }
            .logo { width: 120px; }
            table { width: 100%; border-collapse: collapse; margin-top: 20px; }
            th, td { border: 1px solid black; padding: 8px; text-align: center; }
            .total { text-align: right; margin-top: 20px; }
        </style>
        </head>
        <body>

        <div class="header">
            <img src="logo.png" class="logo">
            <div>
                <h2>{{company_name}}</h2>
                <p>{{company_address}}</p>
                <p>GSTIN: {{company_gstin}}</p>
            </div>
        </div>

        <hr>

        <h3>Invoice No: {{invoice_no}}</h3>
        <p>Date: {{invoice_date}}</p>

        <h4>Bill To:</h4>
        <p>{{customer_name}}</p>
        <p>{{customer_phone}}</p>
        <p>{{customer_address}}</p>

        <table>
            <tr>
                <th>Product</th>
                <th>Qty</th>
                <th>Rate</th>
                <th>Total</th>
            </tr>
            {{rows}}
        </table>

        <div class="total">
            <p>Subtotal: {{subtotal}}</p>
            <p>CGST (9%): {{cgst}}</p>
            <p>SGST (9%): {{sgst}}</p>
            <h3>Final Total: {{final_total}}</h3>
        </div>

        </body>
        </html>
        """

        template = Template(html_template)

        return template.render(
            company_name=company_name,
            company_address=company_address,
            company_gstin=company_gstin,
            invoice_no=st.session_state.invoice_no,
            invoice_date=invoice_date,
            customer_name=customer_name,
            customer_phone=customer_phone,
            customer_address=customer_address,
            rows=rows,
            subtotal=f"{subtotal:.2f}",
            cgst=f"{cgst:.2f}",
            sgst=f"{sgst:.2f}",
            final_total=f"{final_total:.2f}"
        )

    # -----------------------------
    # Generate PDF
    # -----------------------------
    if st.button("Generate PDF Invoice"):

        if not customer_name.strip():
            st.error("Customer name required")
        else:
            html_content = generate_html()
            file_name = f"{st.session_state.invoice_no}.pdf"

            pdfkit.from_string(html_content, file_name)

            with open(file_name, "rb") as f:
                st.download_button(
                    "Download Invoice",
                    f,
                    file_name=file_name,
                    mime="application/pdf"
                )

    if st.button("Clear Bill"):
        st.session_state.items = []
        st.session_state.invoice_no = generate_invoice_number()
        st.rerun()