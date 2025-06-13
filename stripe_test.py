import streamlit as st
import stripe

st.title("Stripe Configuration Test")

# Check secrets
st.write("Checking secrets...")
has_key = "STRIPE_SECRET_KEY" in st.secrets
has_price = "STRIPE_PRICE_ID" in st.secrets
has_url = "APP_URL" in st.secrets

st.write(f"✓ STRIPE_SECRET_KEY: {'Found' if has_key else 'Missing'}")
st.write(f"✓ STRIPE_PRICE_ID: {'Found' if has_price else 'Missing'}")
st.write(f"✓ APP_URL: {'Found' if has_url else 'Missing'}")

if has_key:
    key_prefix = st.secrets["STRIPE_SECRET_KEY"][:14]
    st.write(f"Key starts with: {key_prefix}")
    
if has_price:
    st.write(f"Price ID: {st.secrets['STRIPE_PRICE_ID']}")
    
if has_url:
    st.write(f"App URL: {st.secrets['APP_URL']}")

# Test Stripe connection
if st.button("Test Stripe Connection"):
    try:
        stripe.api_key = st.secrets["STRIPE_SECRET_KEY"]
        # Try to retrieve the price
        price = stripe.Price.retrieve(st.secrets["STRIPE_PRICE_ID"])
        st.success(f"✓ Price found: {price.unit_amount/100} {price.currency.upper()} / {price.recurring.interval}")
    except Exception as e:
        st.error(f"Error: {str(e)}")
