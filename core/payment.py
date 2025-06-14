import streamlit as st
import stripe
from datetime import datetime, timedelta

def init_stripe():
    """Initialize Stripe with API key."""
    try:
        stripe.api_key = st.secrets["STRIPE_SECRET_KEY"]
        return True
    except:
        return False

def create_checkout_session(db_manager, user_id, email):
    """Create Stripe checkout session."""
    if not init_stripe():
        return None
    
    try:
        # Create checkout session
        session = stripe.checkout.Session.create(
            payment_method_types=['card'],
            line_items=[{
                'price': st.secrets["STRIPE_PRICE_ID"],
                'quantity': 1,
            }],
            mode='subscription',
            success_url=st.secrets["APP_URL"] + "?payment=success&session_id={CHECKOUT_SESSION_ID}",
            cancel_url=st.secrets["APP_URL"] + "?payment=cancelled",
            customer_email=email,
            client_reference_id=str(user_id),
            metadata={
                'user_id': str(user_id)
            }
        )
        
        # Save payment record as pending
        db_manager.save_payment(user_id, session.id, 25.00, 'pending')
        
        return session.url
        
    except Exception as e:
        print(f"Checkout session error: {e}")
        return None

def verify_payment_and_login(db_manager, auth_manager, session_id):
    """Verify payment and automatically log the user in."""
    if not init_stripe():
        return False, None
    
    try:
        # Retrieve session from Stripe
        session = stripe.checkout.Session.retrieve(session_id, expand=['subscription'])
        
        if session.payment_status == 'paid':
            user_id = session.metadata.get('user_id')
            
            if user_id:
                # Update subscription status
                subscription_end = datetime.now() + timedelta(days=30)
                db_manager.update_user_subscription(
                    user_id,
                    'active',
                    subscription_end,
                    session.customer
                )
                
                # Update payment record
                db_manager.execute(
                    "UPDATE payments SET status = %s WHERE stripe_session_id = %s",
                    ('completed', session_id),
                    fetch=False
                )
                
                # Get user data for auto-login
                user_data = db_manager.get_user_by_id(user_id)
                
                return True, user_data
        
        return False, None
        
    except Exception as e:
        print(f"Payment verification error: {e}")
        return False, None

def handle_stripe_webhook(request_body, signature_header, db_manager):
    """Handle Stripe webhook events for real-time payment updates."""
    if not init_stripe():
        return False
    
    try:
        # Verify webhook signature
        webhook_secret = st.secrets.get("STRIPE_WEBHOOK_SECRET")
        if not webhook_secret:
            print("Warning: No webhook secret configured")
            return False
        
        event = stripe.Webhook.construct_event(
            request_body, signature_header, webhook_secret
        )
        
        # Handle the event
        if event['type'] == 'checkout.session.completed':
            session = event['data']['object']
            
            # Update user subscription
            user_id = session['metadata'].get('user_id')
            if user_id:
                subscription_end = datetime.now() + timedelta(days=30)
                db_manager.update_user_subscription(
                    user_id,
                    'active',
                    subscription_end,
                    session['customer']
                )
                
                # Update payment status
                db_manager.execute(
                    "UPDATE payments SET status = %s WHERE stripe_session_id = %s",
                    ('completed', session['id']),
                    fetch=False
                )
                
                print(f"Subscription activated for user {user_id}")
                
        elif event['type'] == 'customer.subscription.deleted':
            subscription = event['data']['object']
            
            # Find user by stripe customer ID and deactivate
            result = db_manager.execute(
                "SELECT user_id FROM users WHERE stripe_customer_id = %s",
                (subscription['customer'],)
            )
            
            if result:
                user_id = result[0]['user_id']
                db_manager.execute(
                    "UPDATE users SET subscription_status = %s WHERE user_id = %s",
                    ('inactive', user_id),
                    fetch=False
                )
                print(f"Subscription cancelled for user {user_id}")
        
        return True
        
    except stripe.error.SignatureVerificationError as e:
        print(f"Webhook signature verification failed: {e}")
        return False
    except Exception as e:
        print(f"Webhook processing error: {e}")
        return False

def check_and_update_subscription_status(db_manager, user_id):
    """Check if subscription is still valid and update if expired."""
    user = db_manager.get_user_by_id(user_id)
    
    if user and user['subscription_status'] == 'active':
        if user['subscription_end'] and user['subscription_end'] < datetime.now():
            # Subscription has expired
            db_manager.execute(
                "UPDATE users SET subscription_status = %s WHERE user_id = %s",
                ('expired', user_id),
                fetch=False
            )
            return False
        return True
    
    return False
