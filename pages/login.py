import streamlit as st
import time

def show_login_page(db_manager, auth_manager):
    """Show login form for existing users."""
    
    with st.form("login_form"):
        st.markdown("### Login to Your Account")
        
        email = st.text_input("Email", placeholder="john@example.com")
        password = st.text_input("Password", type="password", placeholder="••••••••")
        
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
                            st.success("Login successful!")
                            time.sleep(1)
                            st.rerun()
                        else:
                            st.error("Your subscription has expired. Please contact support.")
                    else:
                        st.error(message)
    
    # Password reset option
    st.markdown("---")
    
    if st.button("Forgot Password?"):
        st.info("Password reset functionality coming soon. Please contact support.")
    
    # Information section
    st.markdown("""
    <div class='card' style='margin-top: 2rem; text-align: center;'>
        <h3>New to CareerVertex?</h3>
        <p>Create an account to start matching your CV with job opportunities!</p>
        <p><strong>Only £25/month</strong> for unlimited CV analyses</p>
    </div>
    """, unsafe_allow_html=True)
