class SessionStore:
    """
    Temporary in-memory store for keeping device sessions alive during flow testing.
    In a production database, you would map Device Profiles to User records.
    """
    
    # Keeps track of OTP flow
    # Key: email -> Value: {"device_session": {...}, "verification_id": 1234}
    PENDING_SIGNUPS = {}
    
    # Keeps track of verified, logged-in users 
    # Key: auth_token -> Value: device_session
    ACTIVE_USERS = {}
