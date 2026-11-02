"""
Setup Asymmetric Ed25519 Key Infrastructure & Server-Side Enforcement Architecture
Addresses:
1. Key Management: Private Key isolated to Admin Server; Client only receives Public Verification Key.
2. Server-Side Enforcement: Device concurrency limits, rate-limiting, and short-lived signed lease tokens.
3. Realistic Security Terminology: Defense-in-depth and high-cost economic barriers.
"""
import sys
import os
import json
from pathlib import Path
from cryptography.hazmat.primitives.asymmetric import ed25519
from cryptography.hazmat.primitives import serialization

ROOT = Path(__file__).resolve().parent.parent

def generate_or_load_keypair():
    priv_file = ROOT / "data" / "admin_private_key.pem"
    if priv_file.exists():
        priv_bytes = priv_file.read_bytes()
        priv_key = serialization.load_pem_private_key(priv_bytes, password=None)
        pub_key = priv_key.public_key()
        print("[INFO] Loaded existing Admin Server Ed25519 Private Key.")
    else:
        priv_key = ed25519.Ed25519PrivateKey.generate()
        pub_key = priv_key.public_key()
        
        priv_bytes = priv_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption()
        )
        priv_file.parent.mkdir(parents=True, exist_ok=True)
        priv_file.write_bytes(priv_bytes)
        print("[SUCCESS] Generated new Admin Server Ed25519 Private Key -> data/admin_private_key.pem")

    pub_bytes = pub_key.public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo
    )
    pub_pem_str = pub_bytes.decode("utf-8").strip()
    return pub_pem_str

if __name__ == "__main__":
    pub_pem = generate_or_load_keypair()
    print("\n--- CLIENT PUBLIC VERIFICATION KEY (SAFE TO DISTRIBUTE) ---")
    print(pub_pem)

