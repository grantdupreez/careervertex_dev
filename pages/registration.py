import streamlit as st
from core.payment import create_checkout_session
from utils.email import send_login_email
import time

def show_registration_page(db_manager, auth_manager):
    """Show registration form and handle the registration process."""
    
    # Registration form
    with st.form("registration_form"):
        st.markdown("### Create Your Account")
        
        full_name = st.text_input("Full Name", placeholder="John Doe")
        email = st.text_input("Email", placeholder="john@example.com")
        password = st.text_input("Password", type="password", placeholder="••••••••")
        confirm_password = st.text_input("Confirm Password", type="password", placeholder="••••••••")
        
        terms = st.checkbox("I agree to the Terms of Service and Privacy Policy")
        
        submitted = st.form_submit_button("Register", type="primary", use_container_width=True)
        
        if submitted:
            # Validate inputs
            if not all([full_name, email, password, confirm_password]):
                st.error("Please fill in all fields")
            elif password != confirm_password:
                st.error("Passwords do not match")
            elif len(password) < 8:
                st.error("Password must be at least 8 characters long")
            elif not terms:
                st.error("Please accept the terms and conditions")
            else:
                # Register user
                with st.spinner("Creating your account..."):
                    user_id, message = auth_manager.register_user(email, password, full_name)
                    
                    if user_id:
                        # Store user_id for payment flow
                        st.session_state.temp_user_id = user_id
                        st.session_state.temp_email = email
                        st.session_state.registration_complete = True
                        st.success("Account created successfully!")
                        time.sleep(1)
                        st.rerun()
                    else:
                        st.error(message)
    
    # Show payment step if registration complete
    if st.session_state.get('registration_complete'):
        show_payment_step(db_manager)


def show_payment_step(db_manager):
    """Show payment step after registration."""
    st.markdown("---")
    st.markdown("### Step 2: Subscribe to CareerVertex")
    
    # Pricing display
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.markdown("""
        <div class='card'>
            <h4>CareerVertex Pro - £25/month</h4>
            <ul style='list-style: none; padding-left: 0;'>
                <li>✅ Unlimited CV analyses</li>
                <li>✅ Store multiple CVs</li>
                <li>✅ AI-powered job matching</li>
                <li>✅ Custom cover letters</li>
                <li>✅ Interview preparation tips</li>
                <li>✅ Keyword optimization</li>
            </ul>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        st.markdown("""
        <div class='card' style='text-align: center;'>
            <h2 class='gold-gradient'>£25</h2>
            <p>per month</p>
            <p style='font-size: 0.9em; color: #666;'>Cancel anytime</p>
        </div>
        """, unsafe_allow_html=True)
    
    # Payment button
    if st.button("Proceed to Payment", type="primary", use_container_width=True):
        user_id = st.session_state.get('temp_user_id')
        email = st.session_state.get('temp_email')
        
        if user_id and email:
            with st.spinner("Creating secure payment session..."):
                checkout_url = create_checkout_session(db_manager, user_id, email)
                
                if checkout_url:
                    st.session_state.payment_initiated = True
                    st.markdown(f"""
                    <div style='text-align: center; padding: 2rem;'>
                        <h3>Complete Your Payment</h3>
                        <p>Click the button below to complete your payment securely with Stripe:</p>
                        <a href="{checkout_url}" target="_blank" style="
                            background: linear-gradient(135deg, #B8860B 0%, #D4AF37 100%);
                            color: #0D1117;
                            padding: 1rem 2rem;
                            text-decoration: none;
                            border-radius: 5px;
                            font-weight: bold;
                            display: inline-block;
                            margin: 1rem 0;
                        ">🔒 Complete Payment</a>
                    </div>
                    """, unsafe_allow_html=True)
                    
                    # Show next step
                    st.info("After completing payment, check your email for the login link.")
                else:
                    st.error("Failed to create payment session. Please try again.")


def show_email_sent_confirmation(email):
    """Show confirmation that login email was sent."""
    st.markdown(f"""
    <div class='card' style='text-align: center; padding: 3rem;'>
        <h2>✅ Registration Complete!</h2>
        <p style='font-size: 1.2em;'>We've sent a login link to:</p>
        <p style='font-size: 1.3em; font-weight: bold;'>{email}</p>
        <p>Please check your email and click the secure login link to access your account.</p>
        <p style='color: #666; margin-top: 2rem;'>Didn't receive the email? Check your spam folder or contact support.</p>
    </div>
    """, unsafe_allow_html=True)
