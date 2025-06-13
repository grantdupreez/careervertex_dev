import streamlit as st
import streamlit.components.v1 as components
import stripe
import uuid
from datetime import datetime

st.set_page_config(page_title="Stripe Integration Test", layout="wide")

st.title("🔧 Stripe Integration Test Page")

# Initialize session state
if 'test_user_id' not in st.session_state:
    st.session_state['test_user_id'] = str(uuid.uuid4())
if 'test_email' not in st.session_state:
    st.session_state['test_email'] = "test@example.com"

# Check for redirect first
if 'checkout_url' in st.session_state and st.session_state['checkout_url']:
    checkout_url = st.session_state['checkout_url']
    del st.session_state['checkout_url']
    
    st.warning("⚠️ Automatic redirect to Stripe checkout...")
    st.markdown(f"### [👉 Click here to proceed to Stripe Checkout]({checkout_url})")
    
    # Try multiple redirect methods
    st.markdown("If you're not redirected automatically, click the link above.")
    
    # Method 1: Meta refresh
    st.markdown(
        f'<meta http-equiv="refresh" content="0;URL={checkout_url}">',
        unsafe_allow_html=True
    )
    
    # Method 2: JavaScript redirect with delay
    redirect_script = f"""
    <script>
    setTimeout(function() {{
        window.location.href = "{checkout_url}";
    }}, 100);
    </script>
    """
    st.markdown(redirect_script, unsafe_allow_html=True)
    
    # Method 3: Using components.html with more height
    components.html(
        f"""
        <script>
        window.parent.location.href = "{checkout_url}";
        </script>
        <p>Redirecting to Stripe checkout...</p>
        <p>If you're not redirected, <a href="{checkout_url}" target="_top">click here</a>.</p>
        """,
        height=100
    )
    
    st.stop()

# Check for success/cancel in URL params
query_params = st.query_params
if "success" in query_params:
    st.success("✅ Payment successful! You've returned from Stripe checkout.")
    if "session_id" in query_params:
        st.write(f"Session ID: {query_params['session_id']}")
    st.query_params.clear()
elif "canceled" in query_params:
    st.warning("Payment was cancelled.")
    st.query_params.clear()

# Configuration check section
st.header("1️⃣ Configuration Check")

col1, col2 = st.columns(2)

with col1:
    st.subheader("Secrets Status")
    
    # Check secrets
    has_key = "STRIPE_SECRET_KEY" in st.secrets
    has_price = "STRIPE_PRICE_ID" in st.secrets
    has_url = "APP_URL" in st.secrets
    
    if has_key:
        st.success("✅ STRIPE_SECRET_KEY found")
        key_prefix = st.secrets["STRIPE_SECRET_KEY"][:14]
        if key_prefix.startswith("sk_test_"):
            st.info("🧪 Using TEST mode key")
        elif key_prefix.startswith("sk_live_"):
            st.warning("⚡ Using LIVE mode key")
        else:
            st.error("❌ Invalid key format")
    else:
        st.error("❌ STRIPE_SECRET_KEY missing")
    
    if has_price:
        st.success("✅ STRIPE_PRICE_ID found")
        st.code(st.secrets["STRIPE_PRICE_ID"])
    else:
        st.error("❌ STRIPE_PRICE_ID missing")
    
    if has_url:
        st.success("✅ APP_URL found")
        st.code(st.secrets["APP_URL"])
    else:
        st.error("❌ APP_URL missing")

with col2:
    st.subheader("Connection Test")
    
    if has_key and has_price:
        try:
            stripe.api_key = st.secrets["STRIPE_SECRET_KEY"]
            
            # Test API connection
            st.write("Testing API connection...")
            account = stripe.Account.retrieve()
            st.success(f"✅ Connected to Stripe account: {account.id}")
            
            # Test price retrieval
            st.write("Testing price retrieval...")
            price = stripe.Price.retrieve(st.secrets["STRIPE_PRICE_ID"])
            st.success(f"✅ Price found: {price.unit_amount/100} {price.currency.upper()} / {price.recurring.interval}")
            
            # Display product info if available
            if price.product:
                product = stripe.Product.retrieve(price.product)
                st.info(f"Product: {product.name}")
                
        except stripe.error.AuthenticationError as e:
            st.error(f"❌ Authentication failed: {str(e)}")
            st.warning("Check if your API key is valid and in the correct mode")
        except stripe.error.InvalidRequestError as e:
            st.error(f"❌ Invalid request: {str(e)}")
            if "No such price" in str(e):
                st.warning("Price ID not found. Check if it exists and matches your API key mode (test/live)")
        except Exception as e:
            st.error(f"❌ Error: {str(e)}")
    else:
        st.warning("⚠️ Missing required configuration")

st.markdown("---")

# Test checkout section
st.header("2️⃣ Test Checkout Session")

col1, col2 = st.columns(2)

with col1:
    st.subheader("Test User Details")
    test_email = st.text_input("Test Email", value=st.session_state['test_email'])
    st.session_state['test_email'] = test_email
    
    st.info(f"Test User ID: {st.session_state['test_user_id']}")
    
    if st.button("🔄 Generate New User ID"):
        st.session_state['test_user_id'] = str(uuid.uuid4())
        st.rerun()

with col2:
    st.subheader("Create Checkout Session")
    
    if has_key and has_price and has_url:
        if st.button("🛒 Create Test Checkout Session", type="primary"):
            try:
                stripe.api_key = st.secrets["STRIPE_SECRET_KEY"]
                
                with st.spinner("Creating checkout session..."):
                    # Create checkout session
                    app_url = st.secrets["APP_URL"].rstrip('/')
                    
                    session_params = {
                        "customer_email": test_email,
                        "payment_method_types": ["card"],
                        "line_items": [{
                            "price": st.secrets["STRIPE_PRICE_ID"],
                            "quantity": 1,
                        }],
                        "mode": "subscription",
                        "success_url": f"{app_url}?success=true&session_id={{CHECKOUT_SESSION_ID}}",
                        "cancel_url": f"{app_url}?canceled=true",
                        "client_reference_id": st.session_state['test_user_id'],
                        "metadata": {"user_id": st.session_state['test_user_id']}
                    }
                    
                    st.write("Creating session with parameters:")
                    st.json(session_params)
                    
                    checkout_session = stripe.checkout.Session.create(**session_params)
                    
                    st.success("✅ Checkout session created!")
                    st.write(f"Session ID: {checkout_session.id}")
                    
                    # Method 1: Direct link button (most reliable)
                    st.markdown(f"### [🛒 Go to Stripe Checkout]({checkout_session.url})")
                    st.info("Click the link above to proceed to payment")
                    
                    # Method 2: Alternative button approach
                    col1, col2 = st.columns(2)
                    with col1:
                        st.markdown(f"""
                        <a href="{checkout_session.url}" target="_blank">
                            <button style="
                                background-color: #635BFF;
                                color: white;
                                padding: 10px 20px;
                                border: none;
                                border-radius: 5px;
                                cursor: pointer;
                                font-size: 16px;
                            ">Open Stripe Checkout</button>
                        </a>
                        """, unsafe_allow_html=True)
                    
                    # Show the URL for manual copy if needed
                    with st.expander("Show checkout URL (for manual copy)"):
                        st.code(checkout_session.url)
                    
                    # Optional: Still try automatic redirect
                    if st.checkbox("Try automatic redirect (experimental)"):
                        st.session_state['checkout_url'] = checkout_session.url
                        st.rerun()
                    
            except Exception as e:
                st.error(f"❌ Error creating checkout session: {str(e)}")
                st.code(str(e))
                
                # Provide debugging info
                if "No such price" in str(e):
                    st.warning("**Debugging tips:**")
                    st.write("1. Ensure the price ID exists in your Stripe dashboard")
                    st.write("2. Check that your API key and price ID are from the same mode (both test or both live)")
                    st.write("3. In Stripe dashboard, go to Products and verify the price ID")
    else:
        st.warning("⚠️ Missing required configuration. Check the status above.")

st.markdown("---")

# Test cards section
st.header("3️⃣ Test Credit Cards")
st.info("Use these test cards in Stripe's test mode:")

test_cards = {
    "Successful payment": "4242 4242 4242 4242",
    "Requires authentication": "4000 0025 0000 3155",
    "Declined": "4000 0000 0000 0002",
}

for card_type, number in test_cards.items():
    st.code(f"{card_type}: {number}")

st.write("Use any future date for expiry, any 3 digits for CVC, and any 5 digits for postal code.")

st.markdown("---")

# Debug information
st.header("4️⃣ Debug Information")

if st.checkbox("Show detailed configuration"):
    st.subheader("Current Configuration")
    config_info = {
        "API Key Mode": "TEST" if "sk_test_" in st.secrets.get("STRIPE_SECRET_KEY", "") else "LIVE",
        "Price ID": st.secrets.get("STRIPE_PRICE_ID", "Not set"),
        "App URL": st.secrets.get("APP_URL", "Not set"),
        "Test User ID": st.session_state.get('test_user_id', 'Not set'),
        "Test Email": st.session_state.get('test_email', 'Not set'),
    }
    st.json(config_info)

if st.checkbox("Show session state"):
    st.subheader("Session State")
    st.write(dict(st.session_state))

# Instructions
st.markdown("---")
st.header("📋 How to Use This Test Page")
st.markdown("""
1. **Check Configuration**: Ensure all three secrets are properly configured
2. **Test Connection**: Verify that Stripe can connect and find your price
3. **Create Checkout**: Click the checkout button to test the full flow
4. **Complete Payment**: Use a test card to complete the payment
5. **Return to App**: You should be redirected back with success parameters

**If the redirect doesn't work:**
- Check browser console for JavaScript errors
- Ensure your APP_URL is correct
- Try the manual link provided
""")

st.markdown("---")
st.caption("This is a test page for debugging Stripe integration. Do not use in production.")
