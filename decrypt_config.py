import os
import io
import yaml
import getpass
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.scrypt import Scrypt

KEY_FILE = "vault.key"
VAULT_FILE = "config.vault"

def unwrap_key(passphrase):
    with open(KEY_FILE, "rb") as f:
        data = f.read()
    salt, nonce, encrypted_key = data[:16], data[16:28], data[28:]
    kdf = Scrypt(salt=salt, length=32, n=2**14, r=8, p=1)
    kek = kdf.derive(passphrase.encode())
    try:
        return AESGCM(kek).decrypt(nonce, encrypted_key, None)
    except Exception:
        print("Wrong passphrase, or vault.key is corrupted.")
        exit(1)

def load_config(passphrase=None):
    """Returns the decrypted config as a Python dict. Never writes
    plain-text config to disk."""
    if passphrase is None:
        passphrase = os.environ.get("VAULT_PASSPHRASE") or None
    if passphrase is None:
        passphrase = getpass.getpass("Enter your vault passphrase: ")

    raw_key = unwrap_key(passphrase)

    with open(VAULT_FILE, "rb") as f:
        data = f.read()
    nonce, ciphertext = data[:12], data[12:]

    try:
        plaintext = AESGCM(raw_key).decrypt(nonce, ciphertext, None)
    except Exception:
        print("Decryption failed — wrong passphrase or corrupted config.vault.")
        exit(1)

    return yaml.safe_load(io.BytesIO(plaintext))

if __name__ == "__main__":
    # Quick manual test: decrypts and shows account labels only
    # (never prints passwords/TOTP secrets to the screen)
    if not os.path.exists(VAULT_FILE):
        print(f"{VAULT_FILE} not found. Run encrypt_config.py first.")
        exit(1)

    config = load_config()
    print(f"\nDecryption successful. {len(config['accounts'])} accounts found:")
    for acc in config["accounts"]:
        print(f"  - {acc['label']} ({acc['series']}, {acc['itr_status']}, {acc['broker']})")