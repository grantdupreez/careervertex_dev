import streamlit as st
import stripe
from datetime import datetime, timedelta
from utils.email import send_login_email

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
        
        # Save payment record
        db_manager.save_payment(user_id, session.id, 25.00, 'pending')
        
        return session.url
        
    except Exception as e:
        print(f"Checkout session error: {e}")
        return None

def verify_payment(db_manager, auth_manager, session_id):
    """Verify payment and activate subscription."""
    if not init_stripe():
        return False
    
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
                
                # Generate login token and send email
                token = auth_manager.generate_login_token(user_id)
                if token:
                    user = db_manager.get_user_by_id(user_id)
                    if user:
                        send_login_email(user['email'], user['full_name'], token)
                
                return True
        
        return False
        
    except Exception as e:
        print(f"Payment verification error: {e}")
        return False

def handle_payment_webhook(db_manager, auth_manager):
    """Handle Stripe webhook for payment confirmation."""
    # This would be implemented if using webhooks
    # For now, we'll use the success URL approach
    pass
