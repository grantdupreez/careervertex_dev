import streamlit as st
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import requests
import json

class EmailSender:
    """Handle email sending with multiple provider support."""
    
    def __init__(self):
        self.provider = st.secrets.get("EMAIL_PROVIDER", "console")
        self.from_email = st.secrets.get("FROM_EMAIL", "noreply@careervertex.com")
        self.from_name = st.secrets.get("FROM_NAME", "CareerVertex")
    
    def send(self, to_email, subject, html_body):
        """Send email using configured provider."""
        if self.provider == "sendgrid":
            return self._send_via_sendgrid(to_email, subject, html_body)
        elif self.provider == "smtp":
            return self._send_via_smtp(to_email, subject, html_body)
        elif self.provider == "aws_ses":
            return self._send_via_aws_ses(to_email, subject, html_body)
        else:
            # Console output for development
            return self._send_via_console(to_email, subject, html_body)
    
    def _send_via_sendgrid(self, to_email, subject, html_body):
        """Send email using SendGrid API."""
        try:
            url = "https://api.sendgrid.com/v3/mail/send"
            headers = {
                "Authorization": f"Bearer {st.secrets['SENDGRID_API_KEY']}",
                "Content-Type": "application/json"
            }
            
            data = {
                "personalizations": [{
                    "to": [{"email": to_email}]
                }],
                "from": {
                    "email": self.from_email,
                    "name": self.from_name
                },
                "subject": subject,
                "content": [{
                    "type": "text/html",
                    "value": html_body
                }]
            }
            
            response = requests.post(url, headers=headers, json=data)
            return response.status_code == 202
            
        except Exception as e:
            print(f"SendGrid error: {e}")
            return False
    
    def _send_via_smtp(self, to_email, subject, html_body):
        """Send email using SMTP."""
        try:
            msg = MIMEMultipart('alternative')
            msg['Subject'] = subject
            msg['From'] = f"{self.from_name} <{self.from_email}>"
            msg['To'] = to_email
            
            html_part = MIMEText(html_body, 'html')
            msg.attach(html_part)
            
            server = smtplib.SMTP(st.secrets['SMTP_HOST'], st.secrets['SMTP_PORT'])
            
            if st.secrets.get('SMTP_USE_TLS', True):
                server.starttls()
            
            server.login(st.secrets['SMTP_USERNAME'], st.secrets['SMTP_PASSWORD'])
            server.send_message(msg)
            server.quit()
            
            return True
            
        except Exception as e:
            print(f"SMTP error: {e}")
            return False
    
    def _send_via_aws_ses(self, to_email, subject, html_body):
        """Send email using AWS SES."""
        try:
            import boto3
            
            client = boto3.client(
                'ses',
                region_name=st.secrets['AWS_REGION'],
                aws_access_key_id=st.secrets['AWS_ACCESS_KEY_ID'],
                aws_secret_access_key=st.secrets['AWS_SECRET_ACCESS_KEY']
            )
            
            response = client.send_email(
                Source=f"{self.from_name} <{self.from_email}>",
                Destination={'ToAddresses': [to_email]},
                Message={
                    'Subject': {'Data': subject},
                    'Body': {'Html': {'Data': html_body}}
                }
            )
            
            return True
            
        except Exception as e:
            print(f"AWS SES error: {e}")
            return False
    
    def _send_via_console(self, to_email, subject, html_body):
        """Output email to console for development."""
        print(f"\n{'='*60}")
        print(f"EMAIL DEBUG OUTPUT")
        print(f"{'='*60}")
        print(f"To: {to_email}")
        print(f"From: {self.from_name} <{self.from_email}>")
        print(f"Subject: {subject}")
        print(f"{'='*60}")
        print("HTML Body Preview:")
        # Extract text content for console display
        import re
        text_body = re.sub('<[^<]+?>', '', html_body)
        print(text_body[:500] + "..." if len(text_body) > 500 else text_body)
        print(f"{'='*60}\n")
        
        return True


# Email template functions
def send_login_email(email, full_name, token):
    """Send login email with secure token link."""
    app_url = st.secrets.get("APP_URL", "http://localhost:8501")
    login_url = f"{app_url}?token={token}"
    
    subject = "Welcome to CareerVertex - Your Login Link"
    
    html_body = f"""
    <html>
    <head>
        <style>
            body {{ font-family: Arial, sans-serif; background-color: #f8f9fa; margin: 0; padding: 0; }}
            .container {{ max-width: 600px; margin: 0 auto; background-color: white; }}
            .header {{ background: linear-gradient(135deg, #0A1F3D 0%, #1E5A94 100%); color: white; padding: 30px; text-align: center; }}
            .content {{ padding: 30px; }}
            .button {{ display: inline-block; background: linear-gradient(135deg, #B8860B 0%, #D4AF37 100%); color: #0D1117; padding: 15px 30px; text-decoration: none; border-radius: 5px; font-weight: bold; margin: 20px 0; }}
            .footer {{ background-color: #f8f9fa; padding: 20px; text-align: center; font-size: 12px; color: #666; }}
            ul {{ padding-left: 20px; }}
            li {{ margin: 10px 0; }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>Welcome to CareerVertex!</h1>
            </div>
            
            <div class="content">
                <p>Hi {full_name},</p>
                
                <p>Thank you for subscribing to CareerVertex Pro. Your payment has been processed successfully.</p>
                
                <p>Click the secure link below to access your account:</p>
                
                <div style="text-align: center;">
                    <a href="{login_url}" class="button">Access Your Account</a>
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
            </div>
            
            <div class="footer">
                <p>If you didn't create this account, please ignore this email.</p>
                <p>© 2024 CareerVertex. All rights reserved.</p>
            </div>
        </div>
    </body>
    </html>
    """
    
    # Send email
    sender = EmailSender()
    success = sender.send(email, subject, html_body)
    
    if success:
        print(f"Login email sent to {email}")
    else:
        print(f"Failed to send login email to {email}")
        # Still show the login URL in console as backup
        print(f"Login URL: {login_url}")
    
    return success


def send_payment_confirmation_email(email, full_name):
    """Send payment confirmation email."""
    subject = "Payment Confirmed - CareerVertex Pro"
    
    html_body = f"""
    <html>
    <head>
        <style>
            body {{ font-family: Arial, sans-serif; background-color: #f8f9fa; margin: 0; padding: 0; }}
            .container {{ max-width: 600px; margin: 0 auto; background-color: white; }}
            .header {{ background: linear-gradient(135deg, #0A1F3D 0%, #1E5A94 100%); color: white; padding: 30px; text-align: center; }}
            .content {{ padding: 30px; }}
            .footer {{ background-color: #f8f9fa; padding: 20px; text-align: center; font-size: 12px; color: #666; }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>Payment Confirmed</h1>
            </div>
            
            <div class="content">
                <p>Hi {full_name},</p>
                
                <p>Your payment for CareerVertex Pro has been successfully processed.</p>
                
                <p><strong>Subscription Details:</strong></p>
                <ul>
                    <li>Plan: CareerVertex Pro</li>
                    <li>Amount: £25.00 per month</li>
                    <li>Status: Active</li>
                </ul>
                
                <p>You will receive a separate email with your login link shortly.</p>
                
                <p>Thank you for choosing CareerVertex!</p>
                
                <p>Best regards,<br>The CareerVertex Team</p>
            </div>
            
            <div class="footer">
                <p>© 2024 CareerVertex. All rights reserved.</p>
            </div>
        </div>
    </body>
    </html>
    """
    
    sender = EmailSender()
    return sender.send(email, subject, html_body)
