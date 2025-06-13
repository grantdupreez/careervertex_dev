import streamlit as st
import stripe
import uuid
import traceback
from datetime import datetime, timedelta
from psycopg2.extras import Json
import time

def init_stripe():
    """Initialize Stripe with API key."""
    try:
        if "STRIPE_SECRET_KEY" not in st.secrets:
            print("ERROR: STRIPE_SECRET_KEY not found in secrets")
            return False
            
        stripe.api_key = st.secrets["STRIPE_SECRET_KEY"]
        print("Stripe initialized successfully")
        return True
    except Exception as e:
        print(f"ERROR: Failed to initialize Stripe: {str(e)}")
        return False

def create_checkout_session_with_metadata(db_manager, user_id, email):
    """Create a Stripe checkout session with enhanced metadata for better recovery."""
    try:
        if not init_stripe():
            return None, "Stripe configuration missing"
        
        # Validate inputs
        if not user_id or not email:
            return None, "Missing user_id or email"
        
        # Check for required secrets
        if "STRIPE_PRICE_ID" not in st.secrets:
            return None, "STRIPE_PRICE_ID not configured"
        if "APP_URL" not in st.secrets:
            return None, "APP_URL not configured"
            
        # Create a unique session token
        session_token = str(uuid.uuid4())
        
        # Store session info in database BEFORE creating Stripe session
        db_result = db_manager.execute_query(
            """
            INSERT INTO payment_sessions 
            (session_id, user_id, stripe_session_id, session_data, expires_at, status)
            VALUES (%s, %s, %s, %s, %s, %s)
            """,
            (
                session_token,
                user_id,
                'pending_creation',  # Temporary value
                Json({
                    "user_email": email,
                    "created_at": datetime.now().isoformat(),
                    "user_id": str(user_id)
                }),
                datetime.now() + timedelta(hours=1),
                'pending'
            ),
            fetch=False,
            commit=True
        )
        
        if db_result is None:
            return None, "Failed to create payment session in database"
        
        # Create Stripe checkout session
        price_id = st.secrets["STRIPE_PRICE_ID"]
        app_url = st.secrets["APP_URL"].rstrip('/')
        
        print(f"Creating checkout for user {user_id}, email {email}")
        print(f"Success URL: {app_url}?payment_success=true&session_id={{CHECKOUT_SESSION_ID}}&token={session_token}")
        
        checkout_session = stripe.checkout.Session.create(
            customer_email=email,
            payment_method_types=["card"],
            line_items=[{
                "price": price_id,
                "quantity": 1,
            }],
            mode="subscription",
            success_url=f"{app_url}?payment_success=true&session_id={{CHECKOUT_SESSION_ID}}&token={session_token}",
            cancel_url=f"{app_url}?payment_canceled=true",
            client_reference_id=str(user_id),
            metadata={
                "user_id": str(user_id),
                "session_token": session_token,
                "user_email": email
            }
        )
        
        print(f"Checkout session created: {checkout_session.id}")
        
        # Update the session with the actual Stripe session ID
        update_result = db_manager.execute_query(
            """
            UPDATE payment_sessions 
            SET stripe_session_id = %s,
                session_data = session_data || %s
            WHERE session_id = %s
            """,
            (
                checkout_session.id,
                Json({"stripe_url": checkout_session.url}),
                session_token
            ),
            fetch=False,
            commit=True
        )
        
        if update_result is None:
            print("WARNING: Failed to update payment session with Stripe ID")
        
        return checkout_session, None
        
    except stripe.error.InvalidRequestError as e:
        error_msg = f"Invalid request: {str(e)}"
        print(f"Stripe InvalidRequestError: {error_msg}")
        if "No such price" in str(e):
            return None, "Invalid price configuration. Please contact support."
        return None, str(e)
    except stripe.error.AuthenticationError as e:
        print(f"Stripe AuthenticationError: {str(e)}")
        return None, "Authentication failed. Please contact support."
    except stripe.error.StripeError as e:
        print(f"Stripe API error: {str(e)}")
        return None, "Payment processing error. Please try again."
    except Exception as e:
        print(f"Unexpected error creating checkout session: {str(e)}")
        traceback.print_exc()
        return None, "An unexpected error occurred. Please try again."

def process_successful_payment_improved(session_id, token, db_manager):
    """Process payment with better error handling and recovery."""
    try:
        if not init_stripe():
            return False, "Stripe initialization failed", None
        
        print(f"Processing payment for session: {session_id}, token: {token}")
        
        # First, try to find the session using our token
        session_info = None
        if token:
            session_info = db_manager.execute_query(
                """
                SELECT ps.*, u.email, u.full_name 
                FROM payment_sessions ps
                JOIN users u ON ps.user_id = u.user_id
                WHERE ps.session_id = %s
                """,
                (token,)
            )
            if session_info:
                print(f"Found session via token for user: {session_info[0]['user_id']}")
        
        # If no token or session not found, try with Stripe session ID
        if not session_info:
            session_info = db_manager.execute_query(
                """
                SELECT ps.*, u.email, u.full_name 
                FROM payment_sessions ps
                JOIN users u ON ps.user_id = u.user_id
                WHERE ps.stripe_session_id = %s
                """,
                (session_id,)
            )
            if session_info:
                print(f"Found session via Stripe ID for user: {session_info[0]['user_id']}")
        
        # Get Stripe session details
        checkout_session = stripe.checkout.Session.retrieve(
            session_id,
            expand=['customer', 'subscription']
        )
        
        print(f"Checkout session status: {checkout_session.payment_status}")
        
        # Determine user_id from multiple sources
        user_id = None
        user_email = None
        user_name = None
        
        # Priority 1: Our database session
        if session_info:
            user_id = session_info[0]['user_id']
            user_email = session_info[0]['email']
            user_name = session_info[0].get('full_name')
        
        # Priority 2: Stripe metadata
        if not user_id and checkout_session.metadata:
            user_id = checkout_session.metadata.get('user_id')
            user_email = checkout_session.metadata.get('user_email')
        
        # Priority 3: Client reference ID
        if not user_id:
            user_id = checkout_session.client_reference_id
        
        # Priority 4: Email lookup
        if not user_id and checkout_session.customer_details and checkout_session.customer_details.email:
            email_lookup = db_manager.execute_query(
                "SELECT user_id, email, full_name FROM users WHERE email = %s",
                (checkout_session.customer_details.email,)
            )
            if email_lookup:
                user_id = email_lookup[0]['user_id']
                user_email = email_lookup[0]['email']
                user_name = email_lookup[0].get('full_name')
        
        if not user_id:
            print("ERROR: Could not determine user for this payment")
            return False, "Could not determine user for this payment", None
        
        print(f"Processing payment for user_id: {user_id}")
        
        # Process the subscription
        if checkout_session.payment_status != 'paid':
            return False, "Payment not completed", {'user_id': user_id, 'email': user_email}
        
        subscription = checkout_session.subscription
        if isinstance(subscription, str):
            subscription = stripe.Subscription.retrieve(subscription)
        
        if not subscription:
            return False, "No subscription found", {'user_id': user_id, 'email': user_email}
        
        # Update user subscription
        subscription_start = datetime.fromtimestamp(subscription.current_period_start)
        subscription_end = datetime.fromtimestamp(subscription.current_period_end)
        
        print(f"Updating subscription for user {user_id}: {subscription_start} to {subscription_end}")
        
        update_result = db_manager.execute_query(
            """
            UPDATE users 
            SET subscription_status = 'active',
                subscription_start = %s,
                subscription_end = %s,
                stripe_customer_id = %s,
                stripe_subscription_id = %s
            WHERE user_id = %s
            RETURNING email, full_name
            """,
            (
                subscription_start,
                subscription_end,
                checkout_session.customer,
                subscription.id,
                user_id
            ),
            fetch=False,
            commit=True
        )
        
        if not update_result:
            print(f"ERROR: Failed to update subscription for user {user_id}")
            return False, "Failed to update subscription", {'user_id': user_id, 'email': user_email}
        
        # Update payment session
        if token or session_info:
            db_manager.execute_query(
                """
                UPDATE payment_sessions 
                SET status = 'completed', completed_at = NOW()
                WHERE session_id = %s OR stripe_session_id = %s
                """,
                (token, session_id),
                fetch=False,
                commit=True
            )
        
        # Record payment
        payment_id = str(uuid.uuid4())
        amount = float(subscription.items.data[0].price.unit_amount) / 100
        currency = subscription.items.data[0].price.currency.upper()
        
        db_manager.execute_query(
            """
            INSERT INTO payments (
                payment_id, user_id, amount, currency, 
                payment_method, stripe_payment_id, status, payment_date
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """,
            (
                payment_id, user_id, amount, currency,
                "card", checkout_session.payment_intent or session_id, "completed",
                datetime.now()
            ),
            fetch=False,
            commit=True
        )
        
        # Return success with user info for auto-login
        user_info = {
            'user_id': user_id,
            'email': user_email or (update_result[0]['email'] if update_result else None),
            'full_name': user_name or (update_result[0].get('full_name') if update_result else None)
        }
        
        print(f"Payment processed successfully for user {user_id}")
        return True, "Subscription activated successfully!", user_info
        
    except Exception as e:
        print(f"ERROR in process_successful_payment_improved: {str(e)}")
        traceback.print_exc()
        return False, f"Error processing payment: {str(e)}", None

def show_checkout_ui(checkout_session):
    """Display a clean, single checkout UI without duplicates."""
    st.success("✅ Checkout session created successfully!")
    
    # Single, prominent button
    st.markdown("""
    <style>
    .checkout-container {
        text-align: center;
        padding: 2rem;
        background: linear-gradient(135deg, #f5f5f5 0%, #e8e8e8 100%);
        border-radius: 10px;
        margin: 2rem 0;
    }
    .checkout-button {
        background: linear-gradient(135deg, #B8860B 0%, #D4AF37 100%);
        color: #0D1117;
        padding: 1rem 3rem;
        text-decoration: none;
        border-radius: 5px;
        font-weight: bold;
        font-size: 1.2rem;
        display: inline-block;
        box-shadow: 0 5px 15px rgba(184, 134, 11, 0.3);
        transition: all 0.3s ease;
    }
    .checkout-button:hover {
        transform: translateY(-2px);
        box-shadow: 0 7px 20px rgba(184, 134, 11, 0.4);
    }
    </style>
    """, unsafe_allow_html=True)
    
    st.markdown(f"""
    <div class="checkout-container">
        <h3>Ready to complete your subscription?</h3>
        <p>Click the button below to proceed to Stripe's secure checkout</p>
        <a href="{checkout_session.url}" target="_self" class="checkout-button">
            Complete Payment →
        </a>
        <p style="margin-top: 1rem; color: #666; font-size: 0.9rem;">
            You'll be redirected back here after payment
        </p>
    </div>
    """, unsafe_allow_html=True)
    
    # Optional: Show session details in an expander for debugging
    with st.expander("Payment Details", expanded=False):
        st.write(f"**Session ID:** `{checkout_session.id}`")
        st.write(f"**Amount:** £25.00 / month")
        st.write("**What happens next:**")
        st.write("1. Complete payment on Stripe")
        st.write("2. You'll be redirected back here")
        st.write("3. Your subscription will be activated automatically")

def handle_payment_return(db_manager, auth_manager):
    """Handle the return from Stripe payment."""
    query_params = st.query_params
    
    if "payment_success" in query_params and "session_id" in query_params:
        session_id = query_params["session_id"]
        token = query_params.get("token", None)
        
        # Clear URL params early to prevent reprocessing
        st.query_params.clear()
        
        st.title("Processing Your Payment")
        
        # Show processing UI
        with st.spinner("🔄 Activating your subscription..."):
            # Add a small delay for better UX
            time.sleep(1)
            
            success, message, user_info = process_successful_payment_improved(
                session_id, token, db_manager
            )
        
        if success and user_info:
            st.success("✅ " + message)
            st.balloons()
            
            # Auto-login the user if they're not logged in
            if 'user_id' not in st.session_state and user_info.get('user_id'):
                st.session_state['user_id'] = user_info['user_id']
                st.session_state['user_email'] = user_info.get('email', '')
                st.session_state['user_name'] = user_info.get('full_name') or user_info.get('email', '')
                
                # Get full user data
                user_data = auth_manager.get_user_data(user_info['user_id'])
                if user_data:
                    st.session_state['user_data'] = user_data
                
                st.info("You've been automatically logged in!")
                time.sleep(2)
                st.rerun()
            else:
                # User is already logged in, just refresh
                st.info("Your subscription is now active!")
                time.sleep(2)
                st.rerun()
        else:
            # Payment processing failed
            st.error("❌ " + message)
            
            if user_info and user_info.get('user_id'):
                # We know who the user is, help them
                st.info("We've identified your account. Let's try to resolve this:")
                
                col1, col2 = st.columns(2)
                with col1:
                    if st.button("🔄 Retry Activation"):
                        # Retry the activation
                        with st.spinner("Retrying..."):
                            success, message, _ = process_successful_payment_improved(
                                session_id, token, db_manager
                            )
                        if success:
                            st.success("✅ Subscription activated!")
                            time.sleep(2)
                            st.rerun()
                        else:
                            st.error("Still having issues. Please contact support.")
                
                with col2:
                    if st.button("📧 Contact Support"):
                        st.info("Please email support@careervertex.com with the following information:")
                        st.code(f"Session ID: {session_id}\nUser Email: {user_info.get('email', 'Unknown')}")
            else:
                # Can't identify user
                st.warning("Please save this information for support:")
                st.code(f"Session ID: {session_id}")
                st.info("Contact support@careervertex.com with this Session ID to resolve the issue.")
        
        return True
    
    elif "payment_canceled" in query_params:
        st.warning("Payment was canceled. You can try again whenever you're ready.")
        st.query_params.clear()
        return True
    
    return False

# Cleanup function for expired sessions
def cleanup_expired_sessions(db_manager):
    """Remove expired payment sessions"""
    try:
        db_manager.execute_query(
            """
            DELETE FROM payment_sessions 
            WHERE expires_at < NOW() 
            OR (status = 'completed' AND completed_at < NOW() - INTERVAL '7 days')
            """,
            fetch=False,
            commit=True
        )
    except Exception as e:
        print(f"Error cleaning up sessions: {str(e)}")

# Legacy functions for backward compatibility
def create_stripe_checkout_session(user_id, email):
    """Legacy function - redirects to new implementation"""
    print("WARNING: Using legacy create_stripe_checkout_session")
    # This requires access to db_manager, which isn't passed here
    # Return None to force use of new function
    return None

def handle_successful_payment(session_id, db_manager):
    """Legacy function - redirects to new implementation"""
    print("WARNING: Using legacy handle_successful_payment")
    success, message, user_info = process_successful_payment_improved(session_id, None, db_manager)
    return success

def cancel_subscription(user_id, db_manager):
    """Cancel a user's subscription."""
    try:
        if not init_stripe():
            return False, "Stripe initialization failed"
        
        # Get user's subscription ID from database
        user_data = db_manager.execute_query(
            "SELECT stripe_subscription_id FROM users WHERE user_id = %s",
            (user_id,)
        )
        
        if not user_data or not user_data[0]['stripe_subscription_id']:
            return False, "No active subscription found"
        
        subscription_id = user_data[0]['stripe_subscription_id']
        
        # Cancel the subscription at period end
        subscription = stripe.Subscription.modify(
            subscription_id,
            cancel_at_period_end=True
        )
        
        print(f"Subscription {subscription_id} set to cancel at period end")
        
        # Update database
        db_manager.execute_query(
            """
            UPDATE users 
            SET subscription_status = 'cancelling'
            WHERE user_id = %s
            """,
            (user_id,),
            fetch=False,
            commit=True
        )
        
        return True, "Subscription will be cancelled at the end of the current billing period"
        
    except Exception as e:
        print(f"Error cancelling subscription: {str(e)}")
        return False, str(e)

def reactivate_subscription(user_id, db_manager):
    """Reactivate a cancelled subscription."""
    try:
        if not init_stripe():
            return False, "Stripe initialization failed"
        
        # Get user's subscription ID from database
        user_data = db_manager.execute_query(
            "SELECT stripe_subscription_id FROM users WHERE user_id = %s",
            (user_id,)
        )
        
        if not user_data or not user_data[0]['stripe_subscription_id']:
            return False, "No subscription found"
        
        subscription_id = user_data[0]['stripe_subscription_id']
        
        # Reactivate the subscription
        subscription = stripe.Subscription.modify(
            subscription_id,
            cancel_at_period_end=False
        )
        
        print(f"Subscription {subscription_id} reactivated")
        
        # Update database
        db_manager.execute_query(
            """
            UPDATE users 
            SET subscription_status = 'active'
            WHERE user_id = %s
            """,
            (user_id,),
            fetch=False,
            commit=True
        )
        
        return True, "Subscription reactivated successfully"
        
    except Exception as e:
        print(f"Error reactivating subscription: {str(e)}")
        return False, str(e)
