import streamlit as st
import stripe
import uuid
from datetime import datetime

def init_stripe():
    """Initialize Stripe with API key."""
    if "STRIPE_SECRET_KEY" in st.secrets:
        stripe.api_key = st.secrets["STRIPE_SECRET_KEY"]
        return True
    else:
        print("Warning: STRIPE_SECRET_KEY not found in secrets")
        return False

def create_stripe_checkout_session(user_id, email):
    """Create a Stripe checkout session for subscription."""
    try:
        if not init_stripe():
            return None
            
        checkout_session = stripe.checkout.Session.create(
            customer_email=email,
            payment_method_types=["card"],
            line_items=[
                {
                    "price": st.secrets["STRIPE_PRICE_ID"],
                    "quantity": 1,
                },
            ],
            mode="subscription",
            success_url=st.secrets["APP_URL"] + "?success=true&session_id={CHECKOUT_SESSION_ID}",
            cancel_url=st.secrets["APP_URL"] + "?canceled=true",
            client_reference_id=str(user_id),
            metadata={"user_id": str(user_id)}
        )
        return checkout_session
    except Exception as e:
        print(f"Failed to create checkout session: {str(e)}")
        return None

def handle_successful_payment(session_id, db_manager):
    """Process a successful payment."""
    try:
        if not init_stripe():
            return False
            
        # Get the checkout session
        checkout_session = stripe.checkout.Session.retrieve(session_id)
        
        # Get customer details
        user_id = checkout_session.metadata.get("user_id")
        if not user_id:
            return False
            
        # Get subscription details
        subscription = stripe.Subscription.retrieve(checkout_session.subscription)
        
        # Calculate subscription end date
        subscription_start = datetime.fromtimestamp(subscription.current_period_start)
        subscription_end = datetime.fromtimestamp(subscription.current_period_end)
        
        # Update user subscription in database
        db_manager.execute_query(
            """
            UPDATE users 
            SET subscription_status = %s, 
                subscription_start = %s,
                subscription_end = %s,
                stripe_customer_id = %s,
                stripe_subscription_id = %s
            WHERE user_id = %s
            """,
            (
                'active',
                subscription_start,
                subscription_end,
                checkout_session.customer,
                subscription.id,
                user_id
            ),
            fetch=False
        )
        
        # Record the payment
        payment_id = uuid.uuid4()
        db_manager.execute_query(
            """
            INSERT INTO payments (
                payment_id, user_id, amount, currency, 
                payment_method, stripe_payment_id, status
            ) VALUES (%s, %s, %s, %s, %s, %s, %s)
            """,
            (
                payment_id,
                user_id,
                float(subscription.plan.amount) / 100,  # Convert from pence to pounds
                subscription.plan.currency.upper(),
                "card",
                checkout_session.payment_intent,
                "completed"
            ),
            fetch=False
        )
        
        return True
    except Exception as e:
        print(f"Failed to process successful payment: {str(e)}")
        return False