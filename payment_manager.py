import streamlit as st
import stripe
import uuid
from datetime import datetime
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

def create_stripe_checkout_session(user_id, email):
    """Create a Stripe checkout session for subscription."""
    try:
        if not init_stripe():
            print("ERROR: Stripe initialization failed in create_checkout_session")
            return None
        
        # Validate required secrets
        if "STRIPE_PRICE_ID" not in st.secrets:
            print("ERROR: STRIPE_PRICE_ID not found in secrets")
            return None
            
        if "APP_URL" not in st.secrets:
            print("ERROR: APP_URL not found in secrets")
            return None
        
        price_id = st.secrets["STRIPE_PRICE_ID"]
        app_url = st.secrets["APP_URL"].rstrip('/')  # Remove trailing slash if present
        
        print(f"Creating checkout for user {user_id}, email {email}")
        print(f"Using price ID: {price_id}")
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
        
    except stripe.error.StripeError as e:
        print(f"Stripe API error: {str(e)}")
        print(f"Error type: {type(e).__name__}")
        if hasattr(e, 'user_message'):
            print(f"User message: {e.user_message}")
        traceback.print_exc()
        return None
    except Exception as e:
        print(f"Unexpected error creating checkout session: {str(e)}")
        traceback.print_exc()
        return None

def handle_successful_payment(session_id, db_manager):
    """Process a successful payment."""
    try:
        if not init_stripe():
            print("ERROR: Stripe initialization failed in handle_successful_payment")
            return False
        
        print(f"Processing successful payment for session: {session_id}")
        
        # Get the checkout session
        checkout_session = stripe.checkout.Session.retrieve(
            session_id,
            expand=['customer', 'subscription']
        )
        
        print(f"Checkout session status: {checkout_session.payment_status}")
        
        # Get user_id from metadata
        user_id = checkout_session.metadata.get("user_id")
        if not user_id:
            print("ERROR: No user_id found in checkout session metadata")
            # Try client_reference_id as fallback
            user_id = checkout_session.client_reference_id
            if not user_id:
                print("ERROR: No user_id found in client_reference_id either")
                return False
        
        print(f"Processing payment for user_id: {user_id}")
        
        # Get subscription details
        if hasattr(checkout_session, 'subscription'):
            if isinstance(checkout_session.subscription, str):
                # If it's a string ID, fetch the subscription
                subscription = stripe.Subscription.retrieve(checkout_session.subscription)
            else:
                # If it's already expanded
                subscription = checkout_session.subscription
                
            print(f"Subscription ID: {subscription.id}")
            print(f"Subscription status: {subscription.status}")
            
            # Calculate subscription dates
            subscription_start = datetime.fromtimestamp(subscription.current_period_start)
            subscription_end = datetime.fromtimestamp(subscription.current_period_end)
            
            print(f"Subscription period: {subscription_start} to {subscription_end}")
            
            # Update user subscription in database
            update_result = db_manager.execute_query(
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
                fetch=False,
                commit=True
            )
            
            if not update_result:
                print("ERROR: Failed to update user subscription in database")
                return False
            
            print("User subscription updated successfully")
            
            # Record the payment
            payment_id = str(uuid.uuid4())
            
            # Get the amount from the subscription
            amount = float(subscription.items.data[0].price.unit_amount) / 100  # Convert from pence/cents to pounds/dollars
            currency = subscription.items.data[0].price.currency.upper()
            
            payment_result = db_manager.execute_query(
                """
                INSERT INTO payments (
                    payment_id, user_id, amount, currency, 
                    payment_method, stripe_payment_id, status
                ) VALUES (%s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    payment_id,
                    user_id,
                    amount,
                    currency,
                    "card",
                    checkout_session.payment_intent or checkout_session.id,
                    "completed"
                ),
                fetch=False,
                commit=True
            )
            
            if not payment_result:
                print("WARNING: Failed to record payment in database")
                # Don't return False here as the subscription was already activated
            else:
                print("Payment recorded successfully")
            
            return True
        else:
            print("ERROR: No subscription found in checkout session")
            return False
            
    except stripe.error.StripeError as e:
        print(f"Stripe API error processing payment: {str(e)}")
        traceback.print_exc()
        return False
    except Exception as e:
        print(f"Unexpected error processing payment: {str(e)}")
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
