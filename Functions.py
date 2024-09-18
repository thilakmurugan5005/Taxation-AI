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
         "content": f"The Vendor Name is not Thilak Company. Please find the other name which is the vendor name. Extract the following information from the invoice:\n- Invoice Number\n- Vendor Name\n- Invoice Date\n- Total Amount\n- Tax Amount\n- Vendor Address\n- Description\n\n{invoice_text}"}
    ]

    response = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        api_key=api_key,
        messages=messages,
        max_tokens=500
    )

    # Extract only the required information
    llm_output = response['choices'][0]['message']['content']

    # Filter only the lines with the required fields
    required_fields = ['Invoice Number', 'Vendor Name', 'Invoice Date','Total Amount','Tax Amount','Vendor Address','Description']
    filtered_output = "\n".join(
        [line for line in llm_output.split('\n') if any(field in line for field in required_fields)])

    return filtered_output


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
        print("LLM-Output",llm_output)
        parsed_data = parse_extracted_data(llm_output)
        parsed_data['File Name'] = pdf.name
        extracted_data.append(parsed_data)
    df = pd.DataFrame(extracted_data)
    df['Total_Amount'] = df["Total_Amount"].apply(extract_cost)
    total = df['Total_Amount'].sum()
    return total, df

# Define a separate function to format the amount
def format_amount(value):
    try:
        # Convert the value to a float first, then format it with a $ sign
        return "${:,.2f}".format(float(value))
    except ValueError:
        # If conversion to float fails, return the value as it is (for non-numeric cases)
        return value

# Function to format "Total_Amount" column without using lambda
def add_dollar_sign(df):
    if "Total_Amount" in df.columns:
        # Apply the custom function to each element in the Total_Amount column
        df["Total_Amount"] = df["Total_Amount"].map(format_amount)
    return df

# Function to format all numeric columns as monetary values
def add_dollar_sign_to_all_numeric(df):
    # Apply the custom function to each numeric column in the DataFrame
    for col in df.select_dtypes(include=["float", "int"]).columns:
        df[col] = df[col].map(format_amount)
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
