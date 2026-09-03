import os
import yaml
import getpass
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.scrypt import Scrypt

KEY_FILE = "vault.key"
CONFIG_FILE = "config.yaml"
VAULT_FILE = "config.vault"

REQUIRED_FIELDS = ["label", "name", "series", "itr_status", "broker", "client_id", "password", "totp_secret"]
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

def validate_config():
    try:
        with open(CONFIG_FILE, "r") as f:
            data = yaml.safe_load(f)
    except yaml.YAMLError as e:
        print("config.yaml has a YAML formatting error:")
        if hasattr(e, "problem_mark"):
            mark = e.problem_mark
            print(f"  Line {mark.line + 1}, Column {mark.column + 1}")
        print(f"  {e}")
        exit(1)

    if "accounts" not in data or not isinstance(data["accounts"], list):
        print("config.yaml must have an 'accounts' list.")
        exit(1)

    for i, acc in enumerate(data["accounts"]):
        for field in REQUIRED_FIELDS:
            if field not in acc or not str(acc[field]).strip():
                print(f"Account #{i+1} is missing or has empty field: '{field}'")
                exit(1)

    print(f"Validated: {len(data['accounts'])} accounts, all required fields present.")
    return data

if __name__ == "__main__":
    if not os.path.exists(KEY_FILE):
        print(f"{KEY_FILE} not found. Run generate_key.py first.")
        exit(1)
    if not os.path.exists(CONFIG_FILE):
        print(f"{CONFIG_FILE} not found.")
        exit(1)

    validate_config()

    passphrase = getpass.getpass("Enter your vault passphrase: ")
    raw_key = unwrap_key(passphrase)

    with open(CONFIG_FILE, "rb") as f:
        plaintext = os.fsync and f.read()

    nonce = os.urandom(12)
    ciphertext = AESGCM(raw_key).encrypt(nonce, plaintext, None)

    with open(VAULT_FILE, "wb") as f:
        f.write(nonce + ciphertext)

    print(f"\nEncrypted successfully -> {VAULT_FILE}")
    print("You can now safely delete config.yaml (the plain-text version).")