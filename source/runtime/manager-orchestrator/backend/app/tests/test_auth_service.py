from app.services.auth import hash_password, verify_password


def test_password_hash_roundtrip():
    encoded = hash_password('secret123!')
    assert encoded.startswith('pbkdf2_sha256$')
    assert verify_password('secret123!', encoded)
    assert not verify_password('wrong', encoded)
