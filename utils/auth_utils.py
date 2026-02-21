import hashlib

def get_password_hash_input(password: str) -> str:
    """
    Standardize password input for bcrypt.
    We hash with SHA256 first to bypass the 72-byte limit of bcrypt.
    Returns a hex string (64 chars) which is well within 72 bytes.
    """
    if not password:
        return ""
    return hashlib.sha256(password.encode('utf-8')).hexdigest()
