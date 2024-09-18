import streamlit as st
import os
from Send_email import send_email_with_attachment
from Functions import *
import pandas as pd  

st.set_page_config(page_title="Taxation-AI", layout="wide")


def main():
    st.header("TAXATION - AI")

    # Initialize session state for showing the intro
    if "intro_shown" not in st.session_state:
        st.session_state.intro_shown = False
    if "processing_complete" not in st.session_state:
        st.session_state.processing_complete = False

    with st.sidebar:
        st.title("Invoices - Income")
        income_pdf_docs = st.file_uploader("Upload your Income Invoice PDF Files",
                                           accept_multiple_files=True, key="pdf_uploader")

        st.title("Invoices - Expense")
        expenses_pdf_docs = st.file_uploader("Upload your Expense Invoice PDF Files",
                                             accept_multiple_files=True, key="pdf_uploader1")

        if st.button("Submit & Process", key="process_button"):
            if expenses_pdf_docs and income_pdf_docs:
                with st.spinner("Calculating... 🔄"):
                    total_income, income_data = get_details(income_pdf_docs)
                    total_expenses, expenses_data = get_details(expenses_pdf_docs)

                    # Store results in session state
                    st.session_state.total_income = total_income
                    st.session_state.income_data = income_data
                    st.session_state.total_expenses = total_expenses
                    st.session_state.expenses_data = expenses_data
                    st.session_state.intro_shown = False  # Hide intro
                    st.session_state.processing_complete = True  # Mark processing as complete
                st.success("Processing Complete")
            else:
                st.error("Please upload at least one PDF file.")

    # Display results after processing is complete
    if st.session_state.processing_complete:
        st.subheader("Financial Summary")
        with st.spinner("Calculating... 🔄"):
            # Retrieve financial data from session state
            total_income = st.session_state.total_income
            income_data = st.session_state.income_data
            total_expenses = st.session_state.total_expenses
            expenses_data = st.session_state.expenses_data

            net_income = total_income - total_expenses
            tax, tax_percentage = get_tax_bracket(net_income)

            # Display financial metrics
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
                "After-Tax Income(Profit)": [net_income - (net_income * tax)]
            }

            summary_df = pd.DataFrame(financial_summary)

            # Format the "Total_Amount" column with $ sign in each DataFrame
            income_data = add_dollar_sign(income_data)
            expenses_data = add_dollar_sign(expenses_data)
            summary_df = add_dollar_sign_to_all_numeric(summary_df)

            # Convert DataFrames to CSV
            income_csv = convert_df_to_csv(income_data)
            expenses_csv = convert_df_to_csv(expenses_data)
            summary_csv = convert_df_to_csv(summary_df)

            # Zip the files
            zip_buffer = zip_files({
                "Income_data.csv": income_csv,
                "Expenses_data.csv": expenses_csv,
                "Financial_summary.csv": summary_csv
            })

            # Download button for ZIP file
            st.download_button(
                label="Download All Files as ZIP",
                data=zip_buffer,
                file_name="financial_data.zip",
                mime="application/zip"
            )

            # Input field for email
            receiver_email = st.text_input("Enter your email address to receive the ZIP file")

            # Add send button
            if receiver_email and st.button("Send Email"):
                with st.spinner("Sending Email..🔄"):
                    send_email_with_attachment(receiver_email, zip_buffer)
                    st.success("Email sent successfully!")

    # Show intro only if no processing is done yet
    if not st.session_state.processing_complete:
        st.markdown("""
        ## Get instant Tax insights from your Invoices

        ### How It Works

        Follow these simple steps to get Tax insights:

        1. **Upload Your Invoices**: The system accepts multiple Invoice PDF files at once, analyzing the content to provide comprehensive insights.

        2. **Download/Email Results**: After processing the documents, you can download or email the analyzed Invoice insights.
        """)


if __name__ == "__main__":
    main()
