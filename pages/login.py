import streamlit as st
import time
from core.payment import create_checkout_session

def show_subscription_needed(db_manager):
    """Show subscription page for users who need to subscribe."""
    user_id = st.session_state.get('temp_user_id')
    email = st.session_state.get('temp_email')
    
    if not user_id or not email:
        del st.session_state['needs_subscription']
        st.rerun()
        return
    
    # Get user details
    user = db_manager.get_user_by_id(user_id)
    if not user:
        del st.session_state['needs_subscription']
        st.rerun()
        return
    
    # Check if this is a new user or expired subscription
    is_new_user = user.get('subscription_status') is None or user.get('subscription_status') == 'inactive'
    
    st.markdown(f"""
        <div style='text-align: center; margin-bottom: 2rem;'>
            <h2 style='color: #0A1F3D;'>
                {'Welcome to CareerVertex!' if is_new_user else 'Renew Your Subscription'}
            </h2>
            <p style='color: #666; font-size: 1.1rem;'>
                {'Complete your subscription to start using CareerVertex' if is_new_user else 'Your subscription has expired. Renew to continue using CareerVertex.'}
            </p>
        </div>
    """, unsafe_allow_html=True)
    
    # Show pricing
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
                    <ul style='list-style: none; padding: 0;'>
                        <li style='padding: 0.5rem 0; color: #555;'><span style='color: #10B981;'>✓</span> Unlimited CV analyses</li>
                        <li style='padding: 0.5rem 0; color: #555;'><span style='color: #10B981;'>✓</span> AI-powered optimization</li>
                        <li style='padding: 0.5rem 0; color: #555;'><span style='color: #10B981;'>✓</span> Cover letter generation</li>
                        <li style='padding: 0.5rem 0; color: #555;'><span style='color: #10B981;'>✓</span> Interview preparation</li>
                    </ul>
                </div>
            </div>
        """, unsafe_allow_html=True)
        
        # Subscribe button
        st.markdown("<div style='margin-top: 2rem;'>", unsafe_allow_html=True)
        
        if st.button("🔒 Subscribe Now", type="primary", use_container_width=True):
            with st.spinner("Creating secure payment session..."):
                checkout_url = create_checkout_session(db_manager, user_id, email)
                
                if checkout_url:
                    st.markdown(f"""
                        <div style='text-align: center; padding: 2rem; background: #F0FDF4; 
                                    border-radius: 8px; border: 1px solid #10B981; margin-top: 1rem;'>
                            <h3 style='color: #10B981; margin-bottom: 1rem;'>✅ Redirecting to Stripe...</h3>
                            <p style='color: #555;'>You'll be redirected to Stripe's secure payment page.</p>
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
                    st.error("Failed to create payment session. Please try again.")
        
        # Back to login button
        if st.button("← Back to Login", use_container_width=True):
            del st.session_state['needs_subscription']
            if 'temp_user_id' in st.session_state:
                del st.session_state['temp_user_id']
            if 'temp_email' in st.session_state:
                del st.session_state['temp_email']
            st.rerun()
        
        st.markdown("</div>", unsafe_allow_html=True)


def show_login_page(db_manager, auth_manager):
    """Show login form for existing users."""
    
    # Check if we need to show subscription page
    if st.session_state.get('needs_subscription'):
        show_subscription_needed(db_manager)
        return
    
    # Login form with index.html styling
    st.markdown("""
        <div style='background: white; border-radius: 8px; padding: 2rem; 
                    box-shadow: 0 10px 30px rgba(0,0,0,0.03); border: 1px solid #E1E5EA;'>
            <h3 style='color: #0A1F3D; text-align: center; margin-bottom: 2rem;'>Login to Your Account</h3>
        </div>
    """, unsafe_allow_html=True)
    
    with st.form("login_form"):
        email = st.text_input("Email Address", placeholder="john@example.com")
        password = st.text_input("Password", type="password", placeholder="••••••••")
        
        col1, col2 = st.columns(2)
        with col1:
            remember_me = st.checkbox("Remember me")
        with col2:
            st.markdown("""
                <div style='text-align: right; padding-top: 0.5rem;'>
                    <a href='#' style='color: #1E5A94; text-decoration: none; font-size: 0.9rem;'>
                        Forgot password?
                    </a>
                </div>
            """, unsafe_allow_html=True)
        
        submitted = st.form_submit_button("Login", type="primary", use_container_width=True)
        
        if submitted:
            if not email or not password:
                st.error("Please enter both email and password")
            else:
                with st.spinner("Logging in..."):
                    user, message = auth_manager.login_user(email, password)
                    
                    if user:
                        # Check if user has ever had a subscription
                        has_subscription = user.get('subscription_status') is not None and user.get('subscription_status') != 'inactive'
                        
                        if has_subscription and auth_manager.check_subscription(user['user_id']):
                            # Active subscriber - log them in
                            st.session_state.user_id = user['user_id']
                            st.session_state.user_data = user
                            st.success("✅ Login successful!")
                            time.sleep(1)
                            st.rerun()
                        else:
                            # User needs subscription (either new or expired)
                            st.session_state.temp_user_id = user['user_id']
                            st.session_state.temp_email = user['email']
                            st.session_state.needs_subscription = True
                    else:
                        st.error(message)
    
    # Information section with styling
    st.markdown("""
        <div style='text-align: center; margin-top: 3rem; padding: 2rem; 
                    background: linear-gradient(135deg, rgba(184,134,11,0.05) 0%, rgba(212,175,55,0.05) 100%);
                    border-radius: 8px; border: 1px solid rgba(184,134,11,0.2);'>
            <h3 style='color: #0A1F3D; margin-bottom: 1rem;'>New to CareerVertex?</h3>
            <p style='color: #555; margin-bottom: 1.5rem;'>
                Create an account to start matching your CV with job opportunities!
            </p>
            <div style='font-size: 2rem; color: #B8860B; font-weight: 700; margin-bottom: 0.5rem;'>
                £25<span style='font-size: 1rem; font-weight: 400;'>/month</span>
            </div>
            <p style='color: #666; font-size: 0.9rem;'>Unlimited CV analyses • Cancel anytime</p>
        </div>
    """, unsafe_allow_html=True)
    
    # Trust indicators
    st.markdown("""
        <div style='display: flex; justify-content: center; gap: 3rem; margin-top: 2rem; color: #666;'>
            <div style='text-align: center;'>
                <div style='font-size: 2rem; color: #0A1F3D;'>🔒</div>
                <small>Secure Login</small>
            </div>
            <div style='text-align: center;'>
                <div style='font-size: 2rem; color: #0A1F3D;'>🚀</div>
                <small>Instant Access</small>
            </div>
            <div style='text-align: center;'>
                <div style='font-size: 2rem; color: #0A1F3D;'>💎</div>
                <small>Premium Features</small>
            </div>
        </div>
    """, unsafe_allow_html=True)
