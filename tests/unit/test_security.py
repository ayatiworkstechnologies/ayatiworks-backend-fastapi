"""
Tests for authentication service.
"""

import pytest
from app.core.security import (
    hash_password,
    verify_password,
    validate_password_strength,
    create_access_token,
    decode_token,
    generate_otp,
    generate_random_password
)


class TestPasswordHashing:
    """Tests for password hashing functions."""
    
    def test_hash_password(self):
        """Test password hashing."""
        password = "TestPassword123!"
        hashed = hash_password(password)
        
        assert hashed != password
        assert len(hashed) > 50  # bcrypt hashes are long
    
    def test_verify_password_correct(self):
        """Test correct password verification."""
        password = "TestPassword123!"
        hashed = hash_password(password)
        
        assert verify_password(password, hashed) is True
    
    def test_verify_password_incorrect(self):
        """Test incorrect password verification."""
        password = "TestPassword123!"
        hashed = hash_password(password)
        
        assert verify_password("WrongPassword", hashed) is False


class TestPasswordStrength:
    """Tests for password strength validation."""
    
    def test_password_too_short(self):
        """Test password length validation."""
        valid, message = validate_password_strength("Short1!")
        assert valid is False
        assert "8 characters" in message
    
    def test_password_no_uppercase(self):
        """Test uppercase requirement."""
        valid, message = validate_password_strength("password123!")
        assert valid is False
        assert "uppercase" in message
    
    def test_password_no_lowercase(self):
        """Test lowercase requirement."""
        valid, message = validate_password_strength("PASSWORD123!")
        assert valid is False
        assert "lowercase" in message
    
    def test_password_no_digit(self):
        """Test digit requirement."""
        valid, message = validate_password_strength("Password!!")
        assert valid is False
        assert "digit" in message
    
    def test_password_no_special(self):
        """Test special character requirement."""
        valid, message = validate_password_strength("Password123")
        assert valid is False
        assert "special" in message
    
    def test_password_valid(self):
        """Test valid password."""
        valid, message = validate_password_strength("StrongP@ss123")
        assert valid is True


class TestJWT:
    """Tests for JWT token functions."""
    
    def test_create_access_token(self):
        """Test access token creation."""
        data = {"sub": "1", "email": "test@example.com"}
        token = create_access_token(data)
        
        assert token is not None
        assert len(token) > 50
    
    def test_decode_token(self):
        """Test token decoding."""
        data = {"sub": "1", "email": "test@example.com"}
        token = create_access_token(data)
        
        decoded = decode_token(token)
        
        assert decoded is not None
        assert decoded["sub"] == "1"
        assert decoded["email"] == "test@example.com"
        assert decoded["type"] == "access"
    
    def test_decode_invalid_token(self):
        """Test decoding invalid token."""
        decoded = decode_token("invalid.token.here")
        assert decoded is None


class TestOTP:
    """Tests for OTP generation."""
    
    def test_generate_otp_default_length(self):
        """Test OTP generation with default length."""
        otp = generate_otp()
        
        assert otp.isdigit()
        # Default length from settings (6)
    
    def test_generate_otp_custom_length(self):
        """Test OTP generation with custom length."""
        otp = generate_otp(8)
        
        assert len(otp) == 8
        assert otp.isdigit()


class TestRandomPassword:
    """Tests for random password generation."""
    
    def test_generate_random_password(self):
        """Test random password generation."""
        password = generate_random_password()
        
        assert len(password) == 12
        
        # Verify it meets strength requirements
        valid, _ = validate_password_strength(password)
        assert valid is True
    
    def test_generate_random_password_custom_length(self):
        """Test random password with custom length."""
        password = generate_random_password(16)
        
        assert len(password) == 16
