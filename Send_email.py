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
