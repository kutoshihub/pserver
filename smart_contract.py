import json
from blockchain import Blockchain

class SmartContract:
    def __init__(self, blockchain):
        self.blockchain = blockchain

    def execute_contract(self, sender, recipient, amount, contract_code):
        exec(contract_code)
        # Example contract_code: "if amount > 10: recipient = sender"

        self.blockchain.new_transaction(sender, recipient, amount)
        return self.blockchain.last_block['index'] + 1

blockchain = Blockchain()
contract = SmartContract(blockchain)

contract_code = """
if amount > 10:
    recipient = sender
"""
index = contract.execute_contract("Alice", "Bob", 15, contract_code)
print(f"Contract executed in Block {index}")
