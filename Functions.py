from PyPDF2 import PdfReader
import openai
import pandas as pd
import streamlit as st
from io import BytesIO
import zipfile

api_key = st.secrets["OPENAI_API_KEY"]

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
        print("LLM_output",llm_output)
        parsed_data = parse_extracted_data(llm_output)
        parsed_data['File Name'] = pdf.name
        extracted_data.append(parsed_data)
    table = pd.DataFrame(extracted_data)
    df = table
    df['Total_Amount'] = df["Total_Amount"].apply(extract_cost)
    total = df['Total_Amount'].sum()
    return total, df, table

def add_dollar_sign(df):
    if "Total_Amount" in df.columns:
        df["Total_Amount"] = df["Total_Amount"].apply(lambda x: f"${x:,.2f}")
    return df



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
