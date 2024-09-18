import streamlit as st
from PyPDF2 import PdfReader
import os
from dotenv import load_dotenv
import openai
import pandas as pd
from io import BytesIO
import zipfile
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
from email.mime.text import MIMEText

api_key = st.secrets["OPENAI_API_KEY"]
email_address = st.secrets["EMAIL_ADDRESS"]
email_password = st.secrets["EMAIL_PASSWORD"]

st.set_page_config(page_title="Docurative AI", layout="wide")


def extract_text_from_pdf(pdf):
    pdf_reader = PdfReader(pdf)
    text = ""
    for page in pdf_reader.pages:
        text += page.extract_text()
    return text


def extract_keywords_from_invoice(invoice_text):
    messages = [
        {"role": "system", "content": "You are an expert at extracting key information from invoices."},
        {"role": "user",
         "content": f"Extract the following information from the invoice:\n- Invoice Number\n- Vendor Name\n- Total Amount\n- Invoice Date\n\nInvoice content:\n{invoice_text}"}
    ]

    response = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        api_key=api_key,
        messages=messages,
        max_tokens=500
    )

    return response['choices'][0]['message']['content']


def parse_extracted_data(llm_output):
    data = {}
    for line in llm_output.split('\n'):
        if ':' in line:
            key, value = line.split(':', 1)
            clean_key = key.strip().replace('-', '').strip().replace(' ', '_')
            clean_value = value.strip()
            data[clean_key] = clean_value
    return data


def convert_df_to_csv(df):
    output = BytesIO()
    df.to_csv(output, index=False)
    output.seek(0)
    return output


def extract_cost(df):
    return float(df.replace('$', '').replace(',', ''))


def get_details(pdf_docs):
    extracted_data = []
    for pdf in pdf_docs:
        pdf_text = extract_text_from_pdf(pdf)
        llm_output = extract_keywords_from_invoice(pdf_text)
        parsed_data = parse_extracted_data(llm_output)
        parsed_data['File Name'] = pdf.name
        extracted_data.append(parsed_data)
    df = pd.DataFrame(extracted_data)
    df['Total_Amount'] = df["Total_Amount"].apply(extract_cost)
    total = df['Total_Amount'].sum()
    return total, df


def get_tax_bracket(net_income):
    tax = 0
    tax_percentage = 0
    if 0 < net_income < 100000:
        tax = .21
        tax_percentage = "21%"
    elif 100000 < net_income < 200000:
        tax = .34
        tax_percentage = "34%"
    return tax, tax_percentage


def zip_files(file_data_dict):
    """Create an in-memory zip file containing the provided CSV files."""
    zip_buffer = BytesIO()
    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zf:
        for filename, filedata in file_data_dict.items():
            zf.writestr(filename, filedata.getvalue())
    zip_buffer.seek(0)
    return zip_buffer


def send_email_with_attachment(receiver_email, zip_buffer):
    """Send an email with the attached ZIP file."""
    # Create the email content
    msg = MIMEMultipart()
    msg['From'] = email_address
    msg['To'] = receiver_email
    msg['Subject'] = 'Your Financial Data - Zip Attachment'

    body = "Please find attached the zip file containing your financial data."
    msg.attach(MIMEText(body, 'plain'))

    # Attach the zip file
    part = MIMEBase('application', 'octet-stream')
    part.set_payload(zip_buffer.read())
    encoders.encode_base64(part)
    part.add_header('Content-Disposition', f'attachment; filename=financial_data.zip')
    msg.attach(part)

    # Send the email
    try:
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(email_address, email_password)
        text = msg.as_string()
        server.sendmail(email_address, receiver_email, text)
        server.quit()
        st.success(f"Email sent successfully to {receiver_email}")
    except Exception as e:
        st.error(f"Failed to send email: {str(e)}")


def main():
    st.header("TAXATION - AI")

    if "intro_shown" not in st.session_state:
        st.session_state.intro_shown = False

    with st.sidebar:
        st.title("Invoices - Income")
        income_pdf_docs = st.file_uploader("Upload your Income Invoice PDF Files",
                                             accept_multiple_files=True, key="pdf_uploader")

        st.title("Invoices - Expense")
        expenses_pdf_docs = st.file_uploader("Upload your Expense Invoice PDF Files",
                                           accept_multiple_files=True, key="pdf_uploader1")

        # Input field for email
        # receiver_email = st.text_input("Enter your email address to receive the ZIP file")

        if st.button("Submit & Process", key="process_button"):
            if expenses_pdf_docs and income_pdf_docs:
                with st.spinner("Processing..."):
                    total_expenses, expenses_data = get_details(expenses_pdf_docs)
                    total_income, income_data = get_details(income_pdf_docs)

                    # Store results in session state
                    st.session_state.total_expenses = total_expenses
                    st.session_state.expenses_data = expenses_data
                    st.session_state.total_income = total_income
                    st.session_state.income_data = income_data

                st.success("Processing Complete")
                st.session_state.intro_shown = True  # Set to True after processing
            else:
                st.error("Please upload at least one PDF file.")

    if not st.session_state.intro_shown:
        st.markdown("""
        ## Get instant Tax insights from your Invoices



        ### How It Works

        Follow these simple steps to get Tax insights:

        1. **Upload Your Invoices**: The system accepts multiple Invoice PDF files at once, analyzing the content to provide comprehensive insights.

        2. **Also download/email**: After processing the documents, you can download or send email of the analyzed Invoice insights.
        """)

    # Display results if they exist in session state
    if "total_expenses" in st.session_state and "total_income" in st.session_state:
        st.subheader("Financial Summary")
        with st.spinner("Calculating... 🔄"):
            total_expenses = st.session_state.total_expenses
            total_income = st.session_state.total_income
            expenses_data = st.session_state.expenses_data
            income_data = st.session_state.income_data

            net_income = total_income - total_expenses
            tax, tax_percentage = get_tax_bracket(net_income)

            col1, col2 = st.columns(2)
            with col1:
                st.metric(label="Gross Income", value=f"${total_income}")
            with col2:
                st.metric(label="Total Expenses", value=f"${total_expenses}")

            col3, col4 = st.columns(2)
            with col3:
                st.metric(label="Net Income", value=f"${net_income}")
            with col4:
                st.metric(label="Tax Percentage", value=f"{tax_percentage}")

            col5, col6 = st.columns(2)
            with col5:
                tax_owed = net_income * tax
                st.metric(label="Tax Owed", value=f"${tax_owed}")

            with col6:
                after_tax_income = float(net_income) - float(tax_owed)
                st.metric(label="After-Tax Income(Profit)", value=f"${after_tax_income}")

            # Prepare the data for the CSV file
            financial_summary = {
                "Total Income": [total_income],
                "Total Expenses": [total_expenses],
                "Net Income": [net_income],
                "Tax Owed": [tax_owed],
                "After-Tax Income(Profit)": [after_tax_income]
            }

            summary_df = pd.DataFrame(financial_summary)

            # Convert DataFrames to CSV
            income_csv = convert_df_to_csv(income_data)
            expenses_csv = convert_df_to_csv(expenses_data)
            summary_csv = convert_df_to_csv(summary_df)

            # Zip the files
            zip_buffer = zip_files({
                "income_data.csv": income_csv,
                "expenses_data.csv": expenses_csv,
                "financial_summary.csv": summary_csv
            })

            # Download button for ZIP file
            st.download_button(
                label="Download All Files as ZIP",
                data=zip_buffer,
                file_name="financial_data.zip",
                mime="application/zip"
            )
            # Input field for email
            receiver_email = st.chat_input("Enter your email address to receive the ZIP file")
            # Email functionality
            if receiver_email:
                send_email_with_attachment(receiver_email, zip_buffer)


if __name__ == "__main__":
    main()
