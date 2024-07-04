import os
import binascii
from hashlib import sha256

class Wallet:
    def __init__(self):
        self.private_key = self.generate_private_key()
        self.public_key = self.generate_public_key(self.private_key)

    @staticmethod
    def generate_private_key():
        return binascii.hexlify(os.urandom(32)).decode('ascii')

    @staticmethod
    def generate_public_key(private_key):
        return sha256(private_key.encode('ascii')).hexdigest()

    def get_address(self):
        return self.public_key

    def sign_transaction(self, transaction):
        transaction_data = f"{transaction['sender']}{transaction['recipient']}{transaction['amount']}"
        signature = sha256((transaction_data + self.private_key).encode('ascii')).hexdigest()
        return signature

if __name__ == '__main__':
    wallet = Wallet()
    print("Address:", wallet.get_address())
    print("Private Key:", wallet.private_key)
