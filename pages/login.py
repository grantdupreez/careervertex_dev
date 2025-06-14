import streamlit as st
import time

def show_login_page(db_manager, auth_manager):
    """Show login form for existing users."""
    
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
                        # Check subscription status
                        if auth_manager.check_subscription(user['user_id']):
                            st.session_state.user_id = user['user_id']
                            st.session_state.user_data = user
                            st.success("✅ Login successful!")
                            time.sleep(1)
                            st.rerun()
                        else:
                            # User exists but subscription expired
                            st.error("Your subscription has expired.")
                            
                            # Show resubscribe option
                            st.markdown("""
                                <div style='background: #FEF3C7; border: 1px solid #F59E0B; 
                                            border-radius: 5px; padding: 1rem; margin-top: 1rem;'>
                                    <p style='color: #92400E; margin: 0;'>
                                        <strong>Subscription Required</strong><br/>
                                        Your subscription has expired. Please resubscribe to continue using CareerVertex.
                                    </p>
                                </div>
                            """, unsafe_allow_html=True)
                            
                            if st.button("Resubscribe Now", key="resubscribe"):
                                # Create new checkout session for existing user
                                from core.payment import create_checkout_session
                                checkout_url = create_checkout_session(db_manager, user['user_id'], user['email'])
                                
                                if checkout_url:
                                    st.markdown(f"""
                                        <div style='text-align: center; padding: 2rem;'>
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
                                            }}, 1000);
                                        </script>
                                    """, unsafe_allow_html=True)
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
