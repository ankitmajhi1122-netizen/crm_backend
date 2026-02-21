import hashlib

def get_password_hash_input(password: str) -> str:
    if not password:
        return ""
    # DEBUG: Log the input length
    print(f"DEBUG: get_password_hash_input input length: {len(password)}")
    result = hashlib.sha256(password.encode('utf-8')).hexdigest()
    print(f"DEBUG: get_password_hash_input output length: {len(result)}")
    return result
