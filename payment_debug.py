import streamlit as st
import stripe
from db_manager import DatabaseManager
from payment_manager import handle_successful_payment

st.title("Payment Debug Tool")

# Initialize database
db_manager = DatabaseManager()

# Check if there's a session_id in URL
query_params = st.query_params
if "session_id" in query_params:
    st.info(f"Found session_id in URL: {query_params['session_id']}")

# Manual session ID input
st.header("1. Debug Specific Session")
session_id = st.text_input("Enter Stripe Session ID", value=query_params.get("session_id", ""))

if session_id and st.button("Debug This Session"):
    # Initialize Stripe
    if "STRIPE_SECRET_KEY" in st.secrets:
        stripe.api_key = st.secrets["STRIPE_SECRET_KEY"]
        
        try:
            # Retrieve session details
            st.subheader("Session Details")
            session = stripe.checkout.Session.retrieve(
                session_id,
                expand=['customer', 'subscription', 'line_items', 'payment_intent']
            )
            
            # Display key information
            col1, col2 = st.columns(2)
            
            with col1:
                st.write("**Payment Status:**", session.payment_status)
                st.write("**Session Status:**", session.status)
                st.write("**Customer Email:**", session.customer_details.email if session.customer_details else "N/A")
                st.write("**Customer ID:**", session.customer)
            
            with col2:
                st.write("**Subscription ID:**", session.subscription)
                st.write("**Payment Intent:**", session.payment_intent)
                st.write("**Amount:**", f"{session.amount_total/100} {session.currency.upper()}")
            
            # Check metadata
            st.subheader("Metadata")
            st.json(dict(session.metadata))
            
            # Check client reference ID
            st.write("**Client Reference ID:**", session.client_reference_id)
            
            # Try to find user
            st.subheader("User Lookup")
            user_id = session.metadata.get("user_id") or session.client_reference_id
            
            if user_id:
                st.write(f"Looking for user_id: {user_id}")
                
                user_result = db_manager.execute_query(
                    "SELECT * FROM users WHERE user_id = %s",
                    (user_id,)
                )
                
                if user_result:
                    st.success("✅ User found in database")
                    user = user_result[0]
                    st.write(f"- Email: {user['email']}")
                    st.write(f"- Subscription Status: {user['subscription_status']}")
                    st.write(f"- Subscription End: {user['subscription_end']}")
                else:
                    st.error("❌ User NOT found in database")
                    
                    # Try email lookup
                    if session.customer_details and session.customer_details.email:
                        email = session.customer_details.email
                        st.write(f"Trying email lookup: {email}")
                        
                        email_result = db_manager.execute_query(
                            "SELECT * FROM users WHERE email = %s",
                            (email,)
                        )
                        
                        if email_result:
                            st.success(f"✅ User found by email")
                            user = email_result[0]
                            st.write(f"- User ID: {user['user_id']}")
                            st.write(f"- Subscription Status: {user['subscription_status']}")
            
            # Test payment processing
            if st.button("Test Payment Processing"):
                with st.spinner("Processing payment..."):
                    result = handle_successful_payment(session_id, db_manager)
                    
                    if result:
                        st.success("✅ Payment processed successfully!")
                        
                        # Verify update
                        if user_id:
                            updated_user = db_manager.execute_query(
                                "SELECT * FROM users WHERE user_id = %s",
                                (user_id,)
                            )
                            if updated_user:
                                st.write("Updated user data:")
                                st.json(dict(updated_user[0]))
                    else:
                        st.error("❌ Payment processing failed")
                        st.write("Check the console/logs for detailed error messages")
            
        except Exception as e:
            st.error(f"Error retrieving session: {str(e)}")

st.markdown("---")

# Check recent payments
st.header("2. Recent Checkout Sessions")

if st.button("List Recent Sessions"):
    try:
        stripe.api_key = st.secrets["STRIPE_SECRET_KEY"]
        
        # List recent checkout sessions
        sessions = stripe.checkout.Session.list(limit=10)
        
        for session in sessions.data:
            with st.expander(f"Session: {session.id} ({session.status})"):
                col1, col2 = st.columns(2)
                
                with col1:
                    st.write("**Created:**", datetime.fromtimestamp(session.created))
                    st.write("**Status:**", session.status)
                    st.write("**Payment Status:**", session.payment_status)
                
                with col2:
                    st.write("**Customer Email:**", session.customer_details.email if session.customer_details else "N/A")
                    st.write("**Amount:**", f"{session.amount_total/100} {session.currency.upper()}")
                    st.write("**Metadata:**", dict(session.metadata))
                
                if st.button(f"Debug", key=f"debug_{session.id}"):
                    st.session_state['debug_session_id'] = session.id
                    st.rerun()
    
    except Exception as e:
        st.error(f"Error listing sessions: {str(e)}")

# Check user subscriptions
st.markdown("---")
st.header("3. Check User Subscriptions")

user_email = st.text_input("Enter user email to check")

if user_email and st.button("Check User"):
    user_result = db_manager.execute_query(
        "SELECT * FROM users WHERE email = %s",
        (user_email,)
    )
    
    if user_result:
        user = user_result[0]
        st.success("User found!")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.write("**User ID:**", user['user_id'])
            st.write("**Email:**", user['email'])
            st.write("**Created:**", user['created_at'])
        
        with col2:
            st.write("**Subscription Status:**", user['subscription_status'])
            st.write("**Subscription Start:**", user['subscription_start'])
            st.write("**Subscription End:**", user['subscription_end'])
            st.write("**Stripe Customer ID:**", user['stripe_customer_id'])
            st.write("**Stripe Subscription ID:**", user['stripe_subscription_id'])
        
        # Check payments
        payments = db_manager.execute_query(
            "SELECT * FROM payments WHERE user_id = %s ORDER BY payment_date DESC",
            (user['user_id'],)
        )
        
        if payments:
            st.subheader("Payment History")
            for payment in payments:
                st.write(f"- {payment['payment_date']}: {payment['amount']} {payment['currency']} ({payment['status']})")
    else:
        st.error("User not found")

# Database connection test
st.markdown("---")
st.header("4. Database Connection Test")

if st.button("Test Database"):
    try:
        result = db_manager.execute_query("SELECT COUNT(*) as count FROM users")
        if result:
            st.success(f"✅ Database connected. Total users: {result[0]['count']}")
        else:
            st.error("❌ Database query failed")
    except Exception as e:
        st.error(f"❌ Database error: {str(e)}")
