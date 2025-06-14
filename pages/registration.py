import streamlit as st
from core.payment import create_checkout_session
import time
import re

def show_registration_page(db_manager, auth_manager):
    """Show registration form and handle the registration process."""
    
    # Check if we're in the payment flow
    if st.session_state.get('registration_complete'):
        show_payment_step(db_manager)
        return
    
    # Registration form with index.html styling
    st.markdown("""
        <div style='background: white; border-radius: 8px; padding: 2rem; 
                    box-shadow: 0 10px 30px rgba(0,0,0,0.03); border: 1px solid #E1E5EA;'>
            <h3 style='color: #0A1F3D; text-align: center; margin-bottom: 2rem;'>Create Your Account</h3>
        </div>
    """, unsafe_allow_html=True)
    
    with st.form("registration_form"):
        col1, col2 = st.columns(2)
        
        with col1:
            first_name = st.text_input("First Name", placeholder="John")
        with col2:
            last_name = st.text_input("Last Name", placeholder="Doe")
        
        email = st.text_input("Email Address", placeholder="john@example.com")
        
        col1, col2 = st.columns(2)
        with col1:
            password = st.text_input("Password", type="password", placeholder="••••••••")
        with col2:
            confirm_password = st.text_input("Confirm Password", type="password", placeholder="••••••••")
        
        terms = st.checkbox("I agree to the Terms of Service and Privacy Policy")
        
        submitted = st.form_submit_button(
            "Create Account", 
            type="primary", 
            use_container_width=True
        )
        
        if submitted:
            # Validate inputs
            errors = []
            
            if not all([first_name, last_name, email, password, confirm_password]):
                errors.append("Please fill in all fields")
            
            # Email validation
            email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
            if email and not re.match(email_pattern, email):
                errors.append("Please enter a valid email address")
            
            if password != confirm_password:
                errors.append("Passwords do not match")
            elif len(password) < 8:
                errors.append("Password must be at least 8 characters long")
            
            if not terms:
                errors.append("Please accept the terms and conditions")
            
            if errors:
                for error in errors:
                    st.error(error)
            else:
                # Register user
                full_name = f"{first_name} {last_name}"
                
                with st.spinner("Creating your account..."):
                    user_id, message = auth_manager.register_user(email, password, full_name)
                    
                    if user_id:
                        # Store user info for payment flow
                        st.session_state.temp_user_id = user_id
                        st.session_state.temp_email = email
                        st.session_state.temp_name = full_name
                        st.session_state.registration_complete = True
                        st.success("✅ Account created successfully!")
                        time.sleep(1)
                        st.rerun()
                    else:
                        st.error(message)
    
    # Benefits section
    st.markdown("""
        <div style='margin-top: 2rem; text-align: center;'>
            <p style='color: #666;'>Join thousands of professionals using CareerVertex to land their dream jobs</p>
            <div style='display: flex; justify-content: center; gap: 2rem; margin-top: 1rem;'>
                <div>
                    <strong style='color: #0A1F3D; font-size: 1.5rem;'>85%</strong><br/>
                    <span style='color: #666; font-size: 0.9rem;'>Interview Rate</span>
                </div>
                <div>
                    <strong style='color: #0A1F3D; font-size: 1.5rem;'>3x</strong><br/>
                    <span style='color: #666; font-size: 0.9rem;'>More Callbacks</span>
                </div>
                <div>
                    <strong style='color: #0A1F3D; font-size: 1.5rem;'>24/7</strong><br/>
                    <span style='color: #666; font-size: 0.9rem;'>AI Analysis</span>
                </div>
            </div>
        </div>
    """, unsafe_allow_html=True)


def show_payment_step(db_manager):
    """Show payment step after registration."""
    st.markdown("---")
    
    # Payment header
    st.markdown("""
        <div style='text-align: center; margin-bottom: 2rem;'>
            <h2 style='color: #0A1F3D;'>Complete Your Subscription</h2>
            <p style='color: #666;'>Just one more step to unlock unlimited CV analysis</p>
        </div>
    """, unsafe_allow_html=True)
    
    # Pricing card with index.html styling
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        st.markdown("""
            <div style='background: white; border-radius: 8px; overflow: hidden;
                        box-shadow: 0 15px 40px rgba(0,0,0,0.05); border: 1px solid #E1E5EA;'>
                <div style='background: linear-gradient(135deg, #B8860B 0%, #D4AF37 100%); 
                            color: white; padding: 2rem; text-align: center;'>
                    <div style='font-size: 0.9rem; margin-bottom: 0.5rem;'>MONTHLY SUBSCRIPTION</div>
                    <div style='font-size: 3rem; font-weight: 700;'>£25</div>
                    <div style='font-size: 0.9rem; opacity: 0.9;'>per month • Cancel anytime</div>
                </div>
                <div style='padding: 2rem;'>
                    <h4 style='color: #0A1F3D; margin-bottom: 1.5rem; text-align: center;'>
                        Everything you need to land your dream job
                    </h4>
        """, unsafe_allow_html=True)
        
        features = [
            "Unlimited CV analyses",
            "AI-powered keyword optimization",
            "ATS compatibility scoring",
            "Custom cover letter generation",
            "Interview preparation tips",
            "Multiple CV storage & versioning",
            "Industry-specific insights",
            "Priority support"
        ]
        
        for feature in features:
            st.markdown(f"""
                <div style='padding: 0.5rem 0; color: #555;'>
                    <span style='color: #10B981; margin-right: 0.5rem;'>✓</span> {feature}
                </div>
            """, unsafe_allow_html=True)
        
        st.markdown("</div></div>", unsafe_allow_html=True)
        
        # Payment button
        st.markdown("<div style='margin-top: 2rem;'>", unsafe_allow_html=True)
        
        if st.button("🔒 Proceed to Secure Payment", type="primary", use_container_width=True):
            user_id = st.session_state.get('temp_user_id')
            email = st.session_state.get('temp_email')
            
            if user_id and email:
                with st.spinner("Creating secure payment session..."):
                    checkout_url = create_checkout_session(db_manager, user_id, email)
                    
                    if checkout_url:
                        # Show success message and redirect
                        st.markdown(f"""
                            <div style='text-align: center; padding: 2rem; background: #F0FDF4; 
                                        border-radius: 8px; border: 1px solid #10B981;'>
                                <h3 style='color: #10B981; margin-bottom: 1rem;'>✅ Redirecting to Stripe...</h3>
                                <p style='color: #555;'>You'll be redirected to Stripe's secure payment page.</p>
                                <p style='color: #555; margin-bottom: 2rem;'>After payment, you'll be automatically logged in.</p>
                                <a href="{checkout_url}" style="
                                    background: linear-gradient(135deg, #B8860B 0%, #D4AF37 100%);
                                    color: #0D1117;
                                    padding: 1rem 2rem;
                                    text-decoration: none;
                                    border-radius: 5px;
                                    font-weight: bold;
                                    display: inline-block;
                                ">Continue to Payment →</a>
                            </div>
                            <script>
                                setTimeout(function() {{
                                    window.location.href = "{checkout_url}";
                                }}, 1500);
                            </script>
                        """, unsafe_allow_html=True)
                    else:
                        st.error("Failed to create payment session. Please try again or contact support.")
            else:
                st.error("Session expired. Please register again.")
                del st.session_state['registration_complete']
                st.rerun()
        
        st.markdown("</div>", unsafe_allow_html=True)
        
        # Security badges
        st.markdown("""
            <div style='text-align: center; margin-top: 2rem; padding: 1rem;'>
                <div style='display: flex; justify-content: center; align-items: center; gap: 2rem;'>
                    <div style='color: #666;'>
                        <span style='font-size: 1.5rem;'>🔒</span><br/>
                        <small>Secure Payment</small>
                    </div>
                    <div style='color: #666;'>
                        <span style='font-size: 1.5rem;'>💳</span><br/>
                        <small>Powered by Stripe</small>
                    </div>
                    <div style='color: #666;'>
                        <span style='font-size: 1.5rem;'>🛡️</span><br/>
                        <small>SSL Encrypted</small>
                    </div>
                </div>
            </div>
        """, unsafe_allow_html=True)
