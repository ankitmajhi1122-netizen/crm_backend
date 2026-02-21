import hashlib
import bcrypt

def get_password_hash_input(password: str) -> str:
    """
    Standardize password input.
    We hash with SHA256 first to bypass the 72-byte limit of bcrypt.
    Returns a hex string (64 chars).
    """
    if not password:
        return ""
    return hashlib.sha256(password.encode('utf-8')).hexdigest()

def hash_password(password: str) -> str:
    """
    Hashes a password using direct bcrypt calls to avoid passlib issues.
    """
    pw_input = get_password_hash_input(password)
    # bcrypt expects bytes
    pw_bytes = pw_input.encode('utf-8')
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(pw_bytes, salt)
    return hashed.decode('utf-8')

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verifies a password against a hash using direct bcrypt calls.
    """
    try:
        pw_input = get_password_hash_input(plain_password)
        return bcrypt.checkpw(pw_input.encode('utf-8'), hashed_password.encode('utf-8'))
    except Exception as e:
        print(f"ERROR: Password verification failed: {e}")
        return False
