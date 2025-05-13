import streamlit as st
import hmac

def check_password():
    """Returns `True` if the user had a correct password."""

    def login_form():
        """Form with widgets to collect user information"""
        with st.form("Credentials"):
            st.text_input("Username", key="username")
            st.text_input("Password", type="password", key="password")
            st.form_submit_button("Log in", on_click=password_entered)

    def password_entered():
        """Checks whether a password entered by the user is correct."""
        # Ensure secrets and passwords structure exists before accessing
        if "passwords" in st.secrets and st.session_state["username"] in st.secrets["passwords"]:
            stored_password = st.secrets.passwords[st.session_state["username"]]
            # Ensure stored_password is a string or bytes for hmac.compare_digest
            if isinstance(stored_password, (str, bytes)):
                 if hmac.compare_digest(
                    st.session_state["password"],
                    str(stored_password) # Ensure it's compared as string if needed
                 ):
                    st.session_state["password_correct"] = True
                    del st.session_state["password"]  # Don't store the username or password.
                    del st.session_state["username"]
                    return # Exit function on success
            else:
                 st.error(f"Password configuration error for user {st.session_state['username']}.")

        # If checks failed or structure doesn't exist
        st.session_state["password_correct"] = False


    # Return True if the username + password is validated.
    if st.session_state.get("password_correct", False):
        return True

    # Show inputs for username + password.
    login_form()
    if "password_correct" in st.session_state and not st.session_state["password_correct"]:
        st.error("😕 User not known or password incorrect")
    return False
