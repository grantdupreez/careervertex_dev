"""
Stripe Webhook Handler for Streamlit

This file should be deployed as a separate endpoint to handle Stripe webhooks.
For local development, you can use ngrok to expose your local server.

Usage:
1. Run this file with: python webhook_handler.py
2. Use ngrok to expose port 8000: ngrok http 8000
3. Add the ngrok URL + /stripe/webhook to Stripe webhook settings
"""

from flask import Flask, request, jsonify
import stripe
import os
from datetime import datetime, timedelta
import psycopg2
from psycopg2.extras import DictCursor
import json

app = Flask(__name__)

# Load configuration from environment or config file
STRIPE_SECRET_KEY = os.getenv('STRIPE_SECRET_KEY')
STRIPE_WEBHOOK_SECRET = os.getenv('STRIPE_WEBHOOK_SECRET')
DB_CONFIG = {
    'dbname': os.getenv('DB_NAME'),
    'user': os.getenv('DB_USER'),
    'password': os.getenv('DB_PASSWORD'),
    'host': os.getenv('DB_HOST'),
    'port': os.getenv('DB_PORT'),
    'sslmode': 'require'
}

stripe.api_key = STRIPE_SECRET_KEY

def get_db_connection():
    """Get database connection."""
    return psycopg2.connect(**DB_CONFIG)

def update_user_subscription(user_id, status, end_date, customer_id):
    """Update user subscription in database."""
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                UPDATE users 
                SET subscription_status = %s, 
                    subscription_end = %s,
                    stripe_customer_id = %s,
                    subscription_start = CASE 
                        WHEN subscription_start IS NULL THEN NOW() 
                        ELSE subscription_start 
                    END
                WHERE user_id = %s
            """, (status, end_date, customer_id, user_id))
            conn.commit()
    finally:
        conn.close()

def update_payment_status(session_id, status):
    """Update payment status in database."""
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                UPDATE payments 
                SET status = %s 
                WHERE stripe_session_id = %s
            """, (status, session_id))
            conn.commit()
    finally:
        conn.close()

@app.route('/stripe/webhook', methods=['POST'])
def stripe_webhook():
    """Handle Stripe webhook events."""
    payload = request.get_data(as_text=True)
    sig_header = request.headers.get('Stripe-Signature')
    
    try:
        # Verify webhook signature
        event = stripe.Webhook.construct_event(
            payload, sig_header, STRIPE_WEBHOOK_SECRET
        )
    except ValueError:
        # Invalid payload
        return jsonify({'error': 'Invalid payload'}), 400
    except stripe.error.SignatureVerificationError:
        # Invalid signature
        return jsonify({'error': 'Invalid signature'}), 400
    
    # Handle the event
    if event['type'] == 'checkout.session.completed':
        session = event['data']['object']
        
        # Extract user_id from metadata or client_reference_id
        user_id = session.get('metadata', {}).get('user_id') or session.get('client_reference_id')
        
        if user_id:
            # Update subscription status
            subscription_end = datetime.now() + timedelta(days=30)
            update_user_subscription(
                user_id,
                'active',
                subscription_end,
                session['customer']
            )
            
            # Update payment status
            update_payment_status(session['id'], 'completed')
            
            print(f"✅ Subscription activated for user {user_id}")
        else:
            print(f"⚠️ No user_id found in session {session['id']}")
    
    elif event['type'] == 'customer.subscription.updated':
        subscription = event['data']['object']
        
        # Find user by customer ID
        conn = get_db_connection()
        try:
            with conn.cursor(cursor_factory=DictCursor) as cur:
                cur.execute(
                    "SELECT user_id FROM users WHERE stripe_customer_id = %s",
                    (subscription['customer'],)
                )
                result = cur.fetchone()
                
                if result:
                    user_id = result['user_id']
                    
                    # Update subscription based on status
                    if subscription['status'] == 'active':
                        end_date = datetime.fromtimestamp(subscription['current_period_end'])
                        update_user_subscription(user_id, 'active', end_date, subscription['customer'])
                    elif subscription['status'] in ['canceled', 'unpaid']:
                        update_user_subscription(user_id, 'inactive', None, subscription['customer'])
                    
                    print(f"✅ Subscription updated for user {user_id}: {subscription['status']}")
        finally:
            conn.close()
    
    elif event['type'] == 'customer.subscription.deleted':
        subscription = event['data']['object']
        
        # Find user and deactivate subscription
        conn = get_db_connection()
        try:
            with conn.cursor(cursor_factory=DictCursor) as cur:
                cur.execute(
                    "SELECT user_id FROM users WHERE stripe_customer_id = %s",
                    (subscription['customer'],)
                )
                result = cur.fetchone()
                
                if result:
                    user_id = result['user_id']
                    update_user_subscription(user_id, 'inactive', None, subscription['customer'])
                    print(f"✅ Subscription cancelled for user {user_id}")
        finally:
            conn.close()
    
    elif event['type'] == 'invoice.payment_failed':
        invoice = event['data']['object']
        
        # Find user and mark subscription as at risk
        conn = get_db_connection()
        try:
            with conn.cursor(cursor_factory=DictCursor) as cur:
                cur.execute(
                    "SELECT user_id FROM users WHERE stripe_customer_id = %s",
                    (invoice['customer'],)
                )
                result = cur.fetchone()
                
                if result:
                    user_id = result['user_id']
                    # You might want to send an email notification here
                    print(f"⚠️ Payment failed for user {user_id}")
        finally:
            conn.close()
    
    # Return success response
    return jsonify({'status': 'success'}), 200

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint."""
    return jsonify({'status': 'healthy', 'service': 'careervertex-webhooks'}), 200

if __name__ == '__main__':
    # Run the webhook server
    port = int(os.getenv('PORT', 8000))
    app.run(host='0.0.0.0', port=port)
