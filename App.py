import streamlit as st
import os
from Send_email import send_email_with_attachment
from Functions import *




st.set_page_config(page_title="Taxation-AI", layout="wide")


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
