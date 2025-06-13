import streamlit as st
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

def send_login_email(email, full_name, token):
    """Send login email with secure token link."""
    # For production, use a proper email service like SendGrid or AWS SES
    # This is a placeholder implementation
    
    app_url = st.secrets.get("APP_URL", "http://localhost:8501")
    login_url = f"{app_url}?token={token}"
    
    subject = "Welcome to CareerVertex - Your Login Link"
    
    html_body = f"""
    <html>
    <body style="font-family: Arial, sans-serif; background-color: #f8f9fa; padding: 20px;">
        <div style="max-width: 600px; margin: 0 auto; background-color: white; padding: 30px; border-radius: 10px; box-shadow: 0 5px 15px rgba(0,0,0,0.1);">
            <h1 style="color: #0A1F3D; text-align: center;">Welcome to CareerVertex!</h1>
            
            <p>Hi {full_name},</p>
            
            <p>Thank you for subscribing to CareerVertex Pro. Your payment has been processed successfully.</p>
            
            <p>Click the secure link below to access your account:</p>
            
            <div style="text-align: center; margin: 30px 0;">
                <a href="{login_url}" style="background: linear-gradient(135deg, #B8860B 0%, #D4AF37 100%); color: #0D1117; padding: 15px 30px; text-decoration: none; border-radius: 5px; font-weight: bold; display: inline-block;">
                    Access Your Account
                </a>
            </div>
            
            <p><strong>Important:</strong> This link expires in 24 hours for security reasons.</p>
            
            <p>With CareerVertex Pro, you can now:</p>
            <ul>
                <li>Upload and analyze unlimited CVs</li>
                <li>Match your CV against any job description</li>
                <li>Get AI-powered improvement suggestions</li>
                <li>Generate custom cover letters</li>
                <li>Prepare for interviews with tailored tips</li>
            </ul>
            
            <p>If you have any questions, please don't hesitate to contact our support team.</p>
            
            <p>Best regards,<br>The CareerVertex Team</p>
            
            <hr style="margin: 30px 0; border: none; border-top: 1px solid #ddd;">
            
            <p style="font-size: 12px; color: #666; text-align: center;">
                If you didn't create this account, please ignore this email.
            </p>
        </div>
    </body>
    </html>
    """
    
    # In production, implement actual email sending here
    # For now, display the login URL in the console
    print(f"Login URL for {email}: {login_url}")
    
    # Return True to indicate email was "sent"
    return True

def send_password_reset_email(email, reset_token):
    """Send password reset email."""
    # Similar implementation to login email
    pass
