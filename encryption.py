"""Encryption utilities for securing sensitive data."""
import logging
from typing import Optional
from cryptography.fernet import Fernet
import base64
import hashlib

logger = logging.getLogger(__name__)


class EncryptionManager:
    """Manages encryption and decryption of sensitive data."""

    def __init__(self, encryption_key: Optional[str] = None):
        """
        Initialize encryption manager.

        Args:
            encryption_key: Base64-encoded encryption key. If None, encryption is disabled.
        """
        self._enabled = encryption_key is not None and encryption_key.strip() != ""
        self._fernet = None

        if self._enabled:
            try:
                # Ensure the key is properly formatted
                key = encryption_key.strip()

                # If key is not a valid Fernet key, derive one from it
                if not self._is_valid_fernet_key(key):
                    logger.info("Deriving Fernet key from provided encryption key...")
                    key = self._derive_key(key)

                self._fernet = Fernet(key.encode() if isinstance(key, str) else key)
                logger.info("✅ Encryption enabled")
            except Exception as e:
                logger.error(f"❌ Failed to initialize encryption: {e}")
                logger.warning("⚠️  Running without encryption - data will NOT be encrypted!")
                self._enabled = False
        else:
            logger.warning("⚠️  No encryption key provided - data will NOT be encrypted!")

    def _is_valid_fernet_key(self, key: str) -> bool:
        """Check if the key is a valid Fernet key format."""
        try:
            # Fernet keys are 32 bytes, base64 encoded (44 characters with padding)
            if len(key) == 44 and key.endswith('='):
                base64.urlsafe_b64decode(key)
                return True
        except Exception:
            pass
        return False

    def _derive_key(self, password: str) -> str:
        """
        Derive a Fernet key from a password using PBKDF2.

        Args:
            password: The password to derive the key from

        Returns:
            Base64-encoded Fernet key
        """
        # Use PBKDF2 to derive a 32-byte key
        kdf_key = hashlib.pbkdf2_hmac(
            'sha256',
            password.encode(),
            b'whatsapp-monitor-salt',  # Static salt for deterministic key derivation
            100000,
            dklen=32
        )
        # Encode as base64 for Fernet
        return base64.urlsafe_b64encode(kdf_key).decode()

    @property
    def is_enabled(self) -> bool:
        """Check if encryption is enabled."""
        return self._enabled

    def encrypt(self, data: str) -> str:
        """
        Encrypt a string.

        Args:
            data: Plain text to encrypt

        Returns:
            Encrypted text (or original if encryption disabled)
        """
        if not self._enabled or not data:
            return data

        try:
            encrypted = self._fernet.encrypt(data.encode())
            return encrypted.decode()
        except Exception as e:
            logger.error(f"❌ Encryption failed: {e}")
            return data

    def decrypt(self, encrypted_data: str) -> str:
        """
        Decrypt a string.

        Args:
            encrypted_data: Encrypted text to decrypt

        Returns:
            Decrypted plain text (or original if encryption disabled)
        """
        if not self._enabled or not encrypted_data:
            return encrypted_data

        try:
            decrypted = self._fernet.decrypt(encrypted_data.encode())
            return decrypted.decode()
        except Exception as e:
            logger.error(f"❌ Decryption failed: {e}")
            # Return original data if decryption fails (might be unencrypted legacy data)
            return encrypted_data


# Global encryption manager instance
_encryption_manager: Optional[EncryptionManager] = None


def init_encryption(encryption_key: Optional[str] = None) -> EncryptionManager:
    """
    Initialize global encryption manager.

    Args:
        encryption_key: Encryption key (will be derived if not in Fernet format)

    Returns:
        EncryptionManager instance
    """
    global _encryption_manager
    _encryption_manager = EncryptionManager(encryption_key)
    return _encryption_manager


def get_encryption_manager() -> EncryptionManager:
    """Get the global encryption manager instance."""
    if _encryption_manager is None:
        raise RuntimeError("Encryption manager not initialized. Call init_encryption() first.")
    return _encryption_manager


def generate_key() -> str:
    """
    Generate a new Fernet encryption key.

    Returns:
        Base64-encoded encryption key
    """
    return Fernet.generate_key().decode()
