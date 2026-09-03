import getpass
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.scrypt import Scrypt

KEY_FILE = "vault.key"
VAULT_FILE = "config.vault"
OUTPUT_FILE = "config.yaml"

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

if __name__ == "__main__":
    passphrase = getpass.getpass("Enter your vault passphrase: ")
    raw_key = unwrap_key(passphrase)

    with open(VAULT_FILE, "rb") as f:
        data = f.read()
    nonce, ciphertext = data[:12], data[12:]

    try:
        plaintext = AESGCM(raw_key).decrypt(nonce, ciphertext, None)
    except Exception:
        print("Decryption failed -- wrong passphrase or corrupted config.vault.")
        exit(1)

    with open(OUTPUT_FILE, "wb") as f:
        f.write(plaintext)

    print(f"\nDecrypted -> {OUTPUT_FILE}")
    print("Edit this file to add the 'name' field to each account, then run")
    print("encrypt_config.py again to save your changes back to config.vault.")
    print("IMPORTANT: delete config.yaml again once you're done editing.")