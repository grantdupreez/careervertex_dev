import streamlit as st
import stripe
import uuid
from datetime import datetime, timedelta
from psycopg2.extras import Json
import time
import traceback

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

def create_checkout_session(db_manager, user_id, email):
    """Create a simple Stripe checkout session that opens in a new tab."""
    try:
        if not init_stripe():
            return None, "Stripe not configured"
        
        # Validate inputs
        if not user_id or not email:
            return None, "Missing user information"
        
        # Check for required secrets
        if "STRIPE_PRICE_ID" not in st.secrets:
            return None, "STRIPE_PRICE_ID not configured"
        
        # Create session record in database
        session_id = str(uuid.uuid4())
        
        db_result = db_manager.execute_query(
            """
            INSERT INTO payment_sessions 
            (session_id, user_id, stripe_session_id, session_data, expires_at, status)
            VALUES (%s, %s, %s, %s, %s, %s)
            """,
            (
                session_id,
                user_id,
                'pending_creation',
                Json({
                    "user_email": email,
                    "created_at": datetime.now().isoformat()
                }),
                datetime.now() + timedelta(hours=24),
                'pending'
            ),
            fetch=False,
            commit=True
        )
        
        if db_result is None:
            return None, "Failed to create payment session record"
        
        # Create Stripe checkout session with simple success/cancel URLs
        price_id = st.secrets["STRIPE_PRICE_ID"]
        
        # Use simple static URLs for success/cancel
        success_url = "https://careervertex.com/payment-success"
        cancel_url = "https://careervertex.com/payment-cancelled"
        
        print(f"Creating checkout for user {user_id}, email {email}")
        
        checkout_session = stripe.checkout.Session.create(
            payment_method_types=['card'],
            line_items=[{
                'price': price_id,
                'quantity': 1,
            }],
            mode='subscription',
            success_url=success_url,
            cancel_url=cancel_url,
            customer_email=email,
            client_reference_id=str(user_id),
            metadata={
                "user_id": str(user_id),
                "session_id": session_id
            }
        )
        
        print(f"Checkout session created: {checkout_session.id}")
        
        # Update session with Stripe ID
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
                session_id
            ),
            fetch=False,
            commit=True
        )
        
        return checkout_session.url, session_id
        
    except stripe.error.InvalidRequestError as e:
        error_msg = f"Invalid request: {str(e)}"
        print(f"Stripe InvalidRequestError: {error_msg}")
        if "No such price" in str(e):
            return None, "Invalid price configuration. Please contact support."
        return None, str(e)
    except stripe.error.AuthenticationError as e:
        print(f"Stripe AuthenticationError: {str(e)}")
        return None, "Authentication failed. Please contact support."
    except Exception as e:
        print(f"Unexpected error creating checkout session: {str(e)}")
        traceback.print_exc()
        return None, "An unexpected error occurred."

def check_payment_status(db_manager, user_id):
    """Check if user has an active subscription or recent payment."""
    try:
        # First check if user already has active subscription
        user_result = db_manager.execute_query(
            """
            SELECT subscription_status, subscription_end
            FROM users
            WHERE user_id = %s
            """,
            (user_id,)
        )
        
        if user_result:
            user = user_result[0]
            if user['subscription_status'] == 'active' and user['subscription_end']:
                if user['subscription_end'] > datetime.now():
                    return 'active', None
        
        # Check for pending payment sessions
        pending_sessions = db_manager.execute_query(
            """
            SELECT session_id, stripe_session_id, created_at
            FROM payment_sessions
            WHERE user_id = %s 
            AND status = 'pending'
            AND created_at > NOW() - INTERVAL '24 hours'
            ORDER BY created_at DESC
            """,
            (user_id,)
        )
        
        if pending_sessions:
            return 'pending', pending_sessions[0]
        
        return 'none', None
        
    except Exception as e:
        print(f"Error checking payment status: {str(e)}")
        return 'error', None

def verify_and_process_payment(db_manager, user_id, stripe_session_id=None):
    """Verify payment with Stripe and update subscription if paid."""
    try:
        if not init_stripe():
            return False, "Stripe not configured"
        
        # If no specific session provided, get all pending sessions for user
        if stripe_session_id:
            sessions_to_check = [{'stripe_session_id': stripe_session_id}]
        else:
            sessions_to_check = db_manager.execute_query(
                """
                SELECT stripe_session_id 
                FROM payment_sessions 
                WHERE user_id = %s 
                AND status = 'pending'
                AND created_at > NOW() - INTERVAL '24 hours'
                ORDER BY created_at DESC
                """,
                (user_id,)
            )
        
        if not sessions_to_check:
            return False, "No pending payment sessions found"
        
        # Check each session with Stripe
        for session in sessions_to_check:
            try:
                stripe_session = stripe.checkout.Session.retrieve(
                    session['stripe_session_id'],
                    expand=['subscription', 'customer']
                )
                
                if stripe_session.payment_status == 'paid':
                    # Payment successful! Process it
                    return process_successful_payment(
                        db_manager, 
                        user_id, 
                        stripe_session
                    )
                    
            except stripe.error.InvalidRequestError:
                # Session not found or invalid, skip it
                continue
            except Exception as e:
                print(f"Error checking session {session['stripe_session_id']}: {str(e)}")
                continue
        
        return False, "No completed payments found. Please complete your payment and try again."
        
    except Exception as e:
        print(f"Error verifying payment: {str(e)}")
        traceback.print_exc()
        return False, f"Error verifying payment: {str(e)}"

def process_successful_payment(db_manager, user_id, stripe_session):
    """Process a successful payment from Stripe."""
    try:
        # Get subscription details
        subscription = stripe_session.subscription
        if isinstance(subscription, str):
            subscription = stripe.Subscription.retrieve(subscription)
        
        if not subscription:
            return False, "No subscription found in payment session"
        
        # Calculate subscription period
        subscription_start = datetime.fromtimestamp(subscription.current_period_start)
        subscription_end = datetime.fromtimestamp(subscription.current_period_end)
        
        print(f"Processing payment for user {user_id}: {subscription_start} to {subscription_end}")
        
        # Update user subscription
        update_result = db_manager.execute_query(
            """
            UPDATE users 
            SET subscription_status = 'active',
                subscription_start = %s,
                subscription_end = %s,
                stripe_customer_id = %s,
                stripe_subscription_id = %s
            WHERE user_id = %s
            """,
            (
                subscription_start,
                subscription_end,
                stripe_session.customer,
                subscription.id,
                user_id
            ),
            fetch=False,
            commit=True
        )
        
        if update_result is None:
            return False, "Failed to update subscription"
        
        # Update payment session status
        db_manager.execute_query(
            """
            UPDATE payment_sessions 
            SET status = 'completed', 
                completed_at = NOW()
            WHERE stripe_session_id = %s
            """,
            (stripe_session.id,),
            fetch=False,
            commit=True
        )
        
        # Record payment
        payment_id = str(uuid.uuid4())
        amount = float(stripe_session.amount_total or 0) / 100
        currency = (stripe_session.currency or 'gbp').upper()
        
        db_manager.execute_query(
            """
            INSERT INTO payments (
                payment_id, user_id, amount, currency, 
                payment_method, stripe_payment_id, status, payment_date
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """,
            (
                payment_id, user_id, amount, currency,
                'card', stripe_session.payment_intent or stripe_session.id, 
                'completed', datetime.now()
            ),
            fetch=False,
            commit=True
        )
        
        print(f"Payment processed successfully for user {user_id}")
        return True, "Payment verified! Your subscription is now active."
        
    except Exception as e:
        print(f"Error processing payment: {str(e)}")
        traceback.print_exc()
        return False, f"Error processing payment: {str(e)}"

def cancel_subscription(user_id, db_manager):
    """Cancel a user's subscription."""
    try:
        if not init_stripe():
            return False, "Stripe initialization failed"
        
        # Get user's subscription ID
        user_data = db_manager.execute_query(
            "SELECT stripe_subscription_id FROM users WHERE user_id = %s",
            (user_id,)
        )
        
        if not user_data or not user_data[0]['stripe_subscription_id']:
            return False, "No active subscription found"
        
        subscription_id = user_data[0]['stripe_subscription_id']
        
        # Cancel at period end
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

# UI Components

def show_subscription_ui(db_manager, user_data):
    """Show subscription UI with new tab checkout."""
    
    # Check current status
    status, session_data = check_payment_status(db_manager, user_data['user_id'])
    
    if status == 'active':
        return True  # Already subscribed
    
    elif status == 'pending' and session_data:
        # Show pending payment UI
        st.info("⏳ You have a payment in progress...")
        
        time_since = datetime.now() - session_data['created_at'].replace(tzinfo=None)
        minutes_ago = int(time_since.total_seconds() / 60)
        
        st.write(f"Payment session started {minutes_ago} minutes ago")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            if st.button("✅ I've Completed Payment", type="primary"):
                with st.spinner("Verifying payment with Stripe..."):
                    success, message = verify_and_process_payment(
                        db_manager, 
                        user_data['user_id'],
                        session_data['stripe_session_id']
                    )
                    
                    if success:
                        st.success(message)
                        st.balloons()
                        time.sleep(2)
                        st.rerun()
                    else:
                        st.error(message)
        
        with col2:
            if st.button("🔄 Check Payment Status"):
                with st.spinner("Checking..."):
                    success, message = verify_and_process_payment(
                        db_manager, 
                        user_data['user_id'],
                        session_data['stripe_session_id']
                    )
                    
                    if success:
                        st.success(message)
                        time.sleep(2)
                        st.rerun()
                    else:
                        st.info(message)
        
        with col3:
            if st.button("❌ Cancel & Start Over"):
                # Cancel pending session
                db_manager.execute_query(
                    "UPDATE payment_sessions SET status = 'cancelled' WHERE session_id = %s",
                    (session_data['session_id'],),
                    fetch=False,
                    commit=True
                )
                st.rerun()
        
        return False
    
    else:
        # Show subscription options
        st.markdown("### 🚀 Subscribe to CareerVertex Pro")
        
        col1, col2 = st.columns([2, 1])
        
        with col1:
            st.markdown("#### What's included:")
            st.markdown("""
            ✅ **Unlimited CV analyses** - Analyse as many jobs as you want  
            ✅ **Store multiple CVs** - Keep different versions for different roles  
            ✅ **Custom cover letters** - AI-generated for each application  
            ✅ **Interview prep tips** - Tailored to each job  
            ✅ **Keyword optimization** - Never miss important keywords  
            ✅ **Priority support** - Get help when you need it
            """)
        
        with col2:
            st.markdown("#### Pricing")
            st.markdown("### £25/month")
            st.markdown("Cancel anytime")
            st.markdown("Secure payment via Stripe")
        
        st.markdown("---")
        
        # Center the subscribe button
        col1, col2, col3 = st.columns([1, 2, 1])
        
        with col2:
            if st.button("Subscribe Now - £25/month", type="primary", use_container_width=True):
                with st.spinner("Creating secure checkout session..."):
                    checkout_url, session_id = create_checkout_session(
                        db_manager,
                        user_data['user_id'],
                        user_data['email']
                    )
                    
                    if checkout_url:
                        st.success("✅ Checkout session created!")
                        
                        # Instructions
                        st.markdown("""
                        <div style="text-align: center; padding: 20px; background: #f0f2f5; border-radius: 10px; margin: 20px 0;">
                            <h3>Complete Your Payment</h3>
                            <p>Click the button below to open Stripe checkout in a new tab:</p>
                        </div>
                        """, unsafe_allow_html=True)
                        
                        # Payment button
                        st.markdown(f"""
                        <div style="text-align: center; margin: 20px 0;">
                            <a href="{checkout_url}" target="_blank" style="
                                background: linear-gradient(135deg, #B8860B 0%, #D4AF37 100%);
                                color: #0D1117;
                                padding: 15px 40px;
                                text-decoration: none;
                                border-radius: 5px;
                                font-weight: bold;
                                font-size: 18px;
                                display: inline-block;
                                box-shadow: 0 5px 15px rgba(184, 134, 11, 0.3);
                                transition: all 0.3s ease;
                            ">🔒 Complete Payment in Stripe</a>
                        </div>
                        """, unsafe_allow_html=True)
                        
                        # Instructions after payment
                        st.info("📌 **Important:** After completing payment, return to this tab and click the button below:")
                        
                        if st.button("✅ I've Completed Payment", type="primary", use_container_width=True):
                            st.rerun()
                        
                    else:
                        st.error("Failed to create checkout session. Please try again.")
        
        # Support section
        with st.expander("Need help?"):
            st.markdown("""
            **Having issues with payment?**
            
            1. Make sure pop-ups are enabled for Stripe
            2. Try a different browser if payment page doesn't load
            3. Contact support at support@careervertex.com
            
            **Common issues:**
            - Card declined: Check with your bank
            - Page not loading: Disable ad blockers
            - Session expired: Click 'Subscribe Now' again
            """)
            
            if st.button("Verify Past Payment"):
                with st.spinner("Checking for any completed payments..."):
                    success, message = verify_and_process_payment(
                        db_manager, 
                        user_data['user_id']
                    )
                    
                    if success:
                        st.success(message)
                        time.sleep(2)
                        st.rerun()
                    else:
                        st.info(message)
        
        return False

# Legacy support functions (for backwards compatibility)
def handle_payment_return(db_manager, auth_manager):
    """Legacy function - no longer needed but kept for compatibility."""
    return False

def create_stripe_checkout_session(user_id, email):
    """Legacy function - redirects to new implementation."""
    print("WARNING: Using legacy create_stripe_checkout_session")
    return None

def handle_successful_payment(session_id, db_manager):
    """Legacy function - redirects to new implementation."""
    print("WARNING: Using legacy handle_successful_payment")
    return False
