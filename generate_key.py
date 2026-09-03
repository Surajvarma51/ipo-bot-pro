import os
import secrets
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.scrypt import Scrypt
import getpass

KEY_FILE = "vault.key"

def prompt_passphrase():
    p1 = getpass.getpass("Create a passphrase for your vault: ")
    p2 = getpass.getpass("Confirm passphrase: ")
    if p1 != p2:
        print("Passphrases did not match. Try again.")
        exit(1)
    if len(p1) < 8:
        print("Passphrase should be at least 8 characters.")
        exit(1)
    return p1

def create_protected_key(passphrase):
    salt = os.urandom(16)
    kdf = Scrypt(salt=salt, length=32, n=2**14, r=8, p=1)
    kek = kdf.derive(passphrase.encode())

    raw_key = secrets.token_bytes(32)  # actual AES-256 data key
    nonce = os.urandom(12)
    encrypted_key = AESGCM(kek).encrypt(nonce, raw_key, None)

    with open(KEY_FILE, "wb") as f:
        f.write(salt + nonce + encrypted_key)

    print(f"\nKey created and saved to {KEY_FILE}")
    print("Keep this file safe. Without it AND your passphrase, your data cannot be recovered.")

if __name__ == "__main__":
    if os.path.exists(KEY_FILE):
        print(f"{KEY_FILE} already exists. Delete it first if you want to create a new one.")
        exit(1)
    passphrase = prompt_passphrase()
    create_protected_key(passphrase)