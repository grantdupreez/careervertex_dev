import streamlit as st
import stripe
import uuid
import traceback
import secrets
import hashlib
from datetime import datetime, timedelta

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

def create_payment_session(db_manager, user_id, user_email):
    """Create a payment session before redirecting to Stripe"""
    try:
        # Create Stripe checkout session first
        checkout_session = create_stripe_checkout_session(user_id, user_email)
        
        if not checkout_session:
            return None
            
        # Store session in database
        session_id = str(uuid.uuid4())
        expires_at = datetime.now() + timedelta(hours=1)  # 1 hour expiration
        
        session_data = {
            "user_email": user_email,
            "checkout_url": checkout_session.url,
            "stripe_checkout_id": checkout_session.id
        }
        
        db_manager.execute_query(
            """
            INSERT INTO payment_sessions 
            (session_id, user_id, stripe_session_id, session_data, expires_at)
            VALUES (%s, %s, %s, %s, %s)
            """,
            (session_id, user_id, checkout_session.id, Json(session_data), expires_at),
            fetch=False,
            commit=True
        )
        
        return checkout_session
        
    except Exception as e:
        print(f"Error creating payment session: {str(e)}")
        return None

def handle_successful_payment_with_session(session_id, db_manager):
    """Enhanced payment handler that uses stored session data"""
    try:
        if not init_stripe():
            print("ERROR: Stripe initialization failed")
            return False
        
        print(f"Processing payment for Stripe session: {session_id}")
        
        # First, check our database for session info
        session_info = db_manager.execute_query(
            """
            SELECT ps.*, u.email 
            FROM payment_sessions ps
            JOIN users u ON ps.user_id = u.user_id
            WHERE ps.stripe_session_id = %s 
            AND ps.expires_at > NOW()
            AND ps.status = 'pending'
            """,
            (session_id,)
        )
        
        if session_info:
            print(f"Found session info in database for user: {session_info[0]['user_id']}")
            stored_user_id = session_info[0]['user_id']
            stored_email = session_info[0]['email']
        else:
            print("No valid session found in database, trying Stripe metadata")
            stored_user_id = None
            stored_email = None
        
        # Get the checkout session from Stripe
        checkout_session = stripe.checkout.Session.retrieve(
            session_id,
            expand=['customer', 'subscription', 'line_items']
        )
        
        print(f"Checkout session status: {checkout_session.payment_status}")
        
        # Determine user_id with fallback options
        user_id = stored_user_id  # Prefer our stored session
        if not user_id:
            user_id = checkout_session.metadata.get("user_id")
        if not user_id:
            user_id = checkout_session.client_reference_id
            
        if not user_id:
            print("ERROR: No user_id found anywhere")
            # Last resort: try email lookup
            email = stored_email or (checkout_session.customer_details.email if checkout_session.customer_details else None)
            if email:
                user_lookup = db_manager.execute_query(
                    "SELECT user_id FROM users WHERE email = %s",
                    (email,)
                )
                if user_lookup:
                    user_id = user_lookup[0]['user_id']
                    print(f"Found user by email: {user_id}")
        
        if not user_id:
            print("ERROR: Cannot determine user for this payment")
            return False
            
        # Process the subscription as before
        subscription_id = checkout_session.subscription
        if not subscription_id:
            print("ERROR: No subscription in checkout session")
            return False
            
        # Get subscription details
        if isinstance(subscription_id, str):
            subscription = stripe.Subscription.retrieve(subscription_id)
        else:
            subscription = subscription_id
            
        # Update user subscription
        subscription_start = datetime.fromtimestamp(subscription.current_period_start)
        subscription_end = datetime.fromtimestamp(subscription.current_period_end)
        
        update_result = db_manager.execute_query(
            """
            UPDATE users 
            SET subscription_status = %s, 
                subscription_start = %s,
                subscription_end = %s,
                stripe_customer_id = %s,
                stripe_subscription_id = %s
            WHERE user_id = %s
            RETURNING user_id
            """,
            (
                'active',
                subscription_start,
                subscription_end,
                checkout_session.customer,
                subscription.id,
                user_id
            ),
            fetch=True,
            commit=True
        )
        
        if not update_result:
            print("ERROR: Failed to update user subscription")
            return False
            
        # Mark payment session as completed
        if session_info:
            db_manager.execute_query(
                """
                UPDATE payment_sessions 
                SET status = 'completed', completed_at = NOW()
                WHERE stripe_session_id = %s
                """,
                (session_id,),
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
                payment_id,
                user_id,
                amount,
                currency,
                "card",
                checkout_session.payment_intent or checkout_session.id,
                "completed",
                datetime.now()
            ),
            fetch=False,
            commit=True
        )
        
        print(f"SUCCESS: Subscription activated for user {user_id}")
        return True
        
    except Exception as e:
        print(f"ERROR in payment processing: {str(e)}")
        import traceback
        traceback.print_exc()
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

# Updated create_stripe_checkout_session to work with sessions
def create_stripe_checkout_session_secure(db_manager, user_id, email):
    """Create a Stripe checkout session with database session tracking"""
    try:
        if not init_stripe():
            print("ERROR: Stripe initialization failed")
            return None
        
        # Validate inputs
        if not user_id or not email:
            print("ERROR: Missing user_id or email")
            return None
            
        # Create Stripe checkout session
        price_id = st.secrets["STRIPE_PRICE_ID"]
        app_url = st.secrets["APP_URL"].rstrip('/')
        
        checkout_session = stripe.checkout.Session.create(
            customer_email=email,
            payment_method_types=["card"],
            line_items=[{
                "price": price_id,
                "quantity": 1,
            }],
            mode="subscription",
            success_url=f"{app_url}?success=true&session_id={{CHECKOUT_SESSION_ID}}",
            cancel_url=f"{app_url}?canceled=true",
            client_reference_id=str(user_id),
            metadata={"user_id": str(user_id)}
        )
        
        # Store session in database
        session_id = str(uuid.uuid4())
        expires_at = datetime.now() + timedelta(hours=1)
        
        session_data = {
            "user_email": email,
            "checkout_url": checkout_session.url,
            "stripe_checkout_id": checkout_session.id,
            "created_at": datetime.now().isoformat()
        }
        
        result = db_manager.execute_query(
            """
            INSERT INTO payment_sessions 
            (session_id, user_id, stripe_session_id, session_data, expires_at, status)
            VALUES (%s, %s, %s, %s, %s, %s)
            """,
            (session_id, user_id, checkout_session.id, Json(session_data), expires_at, 'pending'),
            fetch=False,
            commit=True
        )
        
        if result is False:
            print("WARNING: Failed to store payment session, but continuing")
        else:
            print(f"Payment session stored: {session_id}")
        
        return checkout_session
        
    except Exception as e:
        print(f"Error creating secure checkout session: {str(e)}")
        import traceback
        traceback.print_exc()
        return None


def create_stripe_checkout_session(user_id, email):
    """Create a Stripe checkout session for subscription."""
    try:
        if not init_stripe():
            print("ERROR: Stripe initialization failed in create_checkout_session")
            st.error("Stripe configuration error. Please contact support.")
            return None
        
        # Validate required secrets
        missing_secrets = []
        if "STRIPE_PRICE_ID" not in st.secrets:
            missing_secrets.append("STRIPE_PRICE_ID")
        if "APP_URL" not in st.secrets:
            missing_secrets.append("APP_URL")
            
        if missing_secrets:
            error_msg = f"Missing required secrets: {', '.join(missing_secrets)}"
            print(f"ERROR: {error_msg}")
            st.error(f"Configuration error: {error_msg}")
            return None
        
        price_id = st.secrets["STRIPE_PRICE_ID"]
        app_url = st.secrets["APP_URL"].rstrip('/')  # Remove trailing slash if present
        
        print(f"Creating checkout for user {user_id}, email {email}")
        print(f"Using price ID: {price_id}")
        print(f"Using API key starting with: {st.secrets['STRIPE_SECRET_KEY'][:14]}...")
        print(f"Success URL: {app_url}?success=true&session_id={{CHECKOUT_SESSION_ID}}")
        print(f"Cancel URL: {app_url}?canceled=true")
        
        checkout_session = stripe.checkout.Session.create(
            customer_email=email,
            payment_method_types=["card"],
            line_items=[
                {
                    "price": price_id,
                    "quantity": 1,
                },
            ],
            mode="subscription",
            success_url=f"{app_url}?success=true&session_id={{CHECKOUT_SESSION_ID}}",
            cancel_url=f"{app_url}?canceled=true",
            client_reference_id=str(user_id),
            metadata={"user_id": str(user_id)}
        )
        
        print(f"Checkout session created successfully: {checkout_session.id}")
        print(f"Checkout URL: {checkout_session.url}")
        
        return checkout_session
        
    except stripe.error.InvalidRequestError as e:
        error_msg = f"Invalid request: {str(e)}"
        print(f"Stripe InvalidRequestError: {error_msg}")
        if "No such price" in str(e):
            st.error("Invalid price configuration. Please contact support.")
            print("ERROR: The price ID does not exist in your Stripe account or is from the wrong mode (test/live)")
        else:
            st.error(f"Invalid request: {str(e)}")
        traceback.print_exc()
        return None
    except stripe.error.AuthenticationError as e:
        print(f"Stripe AuthenticationError: {str(e)}")
        st.error("Authentication failed. Please contact support.")
        print("ERROR: Invalid API key or wrong mode (test/live)")
        traceback.print_exc()
        return None
    except stripe.error.StripeError as e:
        error_msg = f"Stripe error: {str(e)}"
        print(f"Stripe API error: {error_msg}")
        print(f"Error type: {type(e).__name__}")
        if hasattr(e, 'user_message'):
            print(f"User message: {e.user_message}")
            st.error(e.user_message)
        else:
            st.error("Payment processing error. Please try again.")
        traceback.print_exc()
        return None
    except Exception as e:
        error_msg = f"Unexpected error: {str(e)}"
        print(f"Unexpected error creating checkout session: {error_msg}")
        st.error("An unexpected error occurred. Please try again.")
        traceback.print_exc()
        return None

def handle_successful_payment(session_id, db_manager):
    """Process a successful payment."""
    try:
        if not init_stripe():
            print("ERROR: Stripe initialization failed in handle_successful_payment")
            return False
        
        print(f"Processing successful payment for session: {session_id}")
        
        # Get the checkout session with expanded data
        try:
            checkout_session = stripe.checkout.Session.retrieve(
                session_id,
                expand=['customer', 'subscription', 'line_items']
            )
        except stripe.error.StripeError as e:
            print(f"ERROR: Failed to retrieve checkout session: {str(e)}")
            return False
        
        print(f"Checkout session status: {checkout_session.payment_status}")
        print(f"Checkout session data: {checkout_session}")
        
        # Get user_id from metadata or client_reference_id
        user_id = checkout_session.metadata.get("user_id")
        if not user_id:
            user_id = checkout_session.client_reference_id
            print(f"Using client_reference_id as user_id: {user_id}")
        
        if not user_id:
            print("ERROR: No user_id found in checkout session")
            print(f"Metadata: {checkout_session.metadata}")
            print(f"Client reference ID: {checkout_session.client_reference_id}")
            return False
        
        print(f"Processing payment for user_id: {user_id}")
        
        # Verify user exists in database
        user_check = db_manager.execute_query(
            "SELECT user_id, email FROM users WHERE user_id = %s",
            (user_id,)
        )
        
        if not user_check:
            print(f"ERROR: User {user_id} not found in database")
            # Try to find by email as fallback
            if checkout_session.customer_details and checkout_session.customer_details.email:
                email = checkout_session.customer_details.email
                print(f"Trying to find user by email: {email}")
                user_check = db_manager.execute_query(
                    "SELECT user_id, email FROM users WHERE email = %s",
                    (email,)
                )
                if user_check:
                    user_id = user_check[0]['user_id']
                    print(f"Found user by email, user_id: {user_id}")
                else:
                    print(f"ERROR: No user found with email {email}")
                    return False
            else:
                return False
        
        # Get subscription details
        subscription_id = checkout_session.subscription
        if not subscription_id:
            print("ERROR: No subscription ID in checkout session")
            return False
            
        print(f"Subscription ID: {subscription_id}")
        
        # Retrieve full subscription details
        try:
            if isinstance(subscription_id, str):
                subscription = stripe.Subscription.retrieve(subscription_id)
            else:
                subscription = subscription_id
        except stripe.error.StripeError as e:
            print(f"ERROR: Failed to retrieve subscription: {str(e)}")
            return False
            
        print(f"Subscription status: {subscription.status}")
        
        # Calculate subscription dates
        subscription_start = datetime.fromtimestamp(subscription.current_period_start)
        subscription_end = datetime.fromtimestamp(subscription.current_period_end)
        
        print(f"Subscription period: {subscription_start} to {subscription_end}")
        
        # Update user subscription in database with better error handling
        try:
            update_result = db_manager.execute_query(
                """
                UPDATE users 
                SET subscription_status = %s, 
                    subscription_start = %s,
                    subscription_end = %s,
                    stripe_customer_id = %s,
                    stripe_subscription_id = %s
                WHERE user_id = %s
                RETURNING user_id
                """,
                (
                    'active',
                    subscription_start,
                    subscription_end,
                    checkout_session.customer,
                    subscription.id,
                    user_id
                ),
                fetch=True,
                commit=True
            )
            
            if not update_result:
                print(f"ERROR: Failed to update user subscription - no rows returned")
                return False
                
            print(f"User subscription updated successfully for user_id: {update_result[0]['user_id']}")
            
        except Exception as e:
            print(f"ERROR: Database update failed: {str(e)}")
            import traceback
            traceback.print_exc()
            return False
        
        # Record the payment
        try:
            payment_id = str(uuid.uuid4())
            
            # Get the amount from the subscription
            amount = float(subscription.items.data[0].price.unit_amount) / 100
            currency = subscription.items.data[0].price.currency.upper()
            
            payment_result = db_manager.execute_query(
                """
                INSERT INTO payments (
                    payment_id, user_id, amount, currency, 
                    payment_method, stripe_payment_id, status, payment_date
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    payment_id,
                    user_id,
                    amount,
                    currency,
                    "card",
                    checkout_session.payment_intent or checkout_session.id,
                    "completed",
                    datetime.now()
                ),
                fetch=False,
                commit=True
            )
            
            if payment_result is False:
                print("WARNING: Failed to record payment in database")
            else:
                print(f"Payment recorded successfully: {payment_id}")
        
        except Exception as e:
            print(f"WARNING: Failed to record payment: {str(e)}")
            # Don't return False here as subscription was already activated
        
        # Final verification
        verify_result = db_manager.execute_query(
            """
            SELECT subscription_status, subscription_end 
            FROM users 
            WHERE user_id = %s
            """,
            (user_id,)
        )
        
        if verify_result and verify_result[0]['subscription_status'] == 'active':
            print(f"SUCCESS: Subscription verified as active for user {user_id}")
            return True
        else:
            print(f"ERROR: Subscription verification failed for user {user_id}")
            return False
            
    except Exception as e:
        print(f"CRITICAL ERROR in handle_successful_payment: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

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
