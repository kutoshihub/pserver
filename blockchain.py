import hashlib
import json
import os
from time import time
from flask import Flask, jsonify, request, send_from_directory
from wallet import Wallet
import requests

class Blockchain:
    def __init__(self):
        self.chain = []
        self.current_transactions = []
        self.balances = {}
        self.nodes = set()

        # Load data
        self.load_data()

        # Create the genesis block if the chain is empty
        if not self.chain:
            self.new_block(previous_hash='1', proof=100)

    def register_node(self, address):
        parsed_url = requests.utils.urlparse(address)
        self.nodes.add(parsed_url.netloc)

    def new_block(self, proof, previous_hash=None):
        block = {
            'index': len(self.chain) + 1,
            'timestamp': time(),
            'transactions': self.current_transactions,
            'proof': proof,
            'previous_hash': previous_hash or self.hash(self.chain[-1]),
        }
        self.current_transactions = []
        self.chain.append(block)
        self.save_data()
        self.broadcast_block(block)
        return block

    def new_transaction(self, sender, recipient, amount):
        self.current_transactions.append({
            'sender': sender,
            'recipient': recipient,
            'amount': amount
        })
        if sender != "0":  # Mining reward transactions
            self.balances[sender] -= amount
        self.balances[recipient] = self.balances.get(recipient, 0) + amount
        self.save_data()
        self.broadcast_transaction(sender, recipient, amount)
        return self.last_block['index'] + 1

    def broadcast_transaction(self, sender, recipient, amount):
        for node in self.nodes:
            url = f'http://{node}/transactions/new'
            try:
                requests.post(url, json={
                    'sender': sender,
                    'recipient': recipient,
                    'amount': amount
                })
            except requests.exceptions.RequestException as e:
                print(f"Error broadcasting transaction to {node}: {e}")

    def broadcast_block(self, block):
        for node in self.nodes:
            url = f'http://{node}/block/new'
            try:
                requests.post(url, json=block)
            except requests.exceptions.RequestException as e:
                print(f"Error broadcasting block to {node}: {e}")

    def save_data(self):
        with open('chain.json', 'w') as f:
            json.dump(self.chain, f)
        with open('balances.json', 'w') as f:
            json.dump(self.balances, f)

    def load_data(self):
        if os.path.exists('chain.json'):
            with open('chain.json', 'r') as f:
                self.chain = json.load(f)
        if os.path.exists('balances.json'):
            with open('balances.json', 'r') as f:
                self.balances = json.load(f)

    @staticmethod
    def hash(block):
        block_string = json.dumps(block, sort_keys=True).encode()
        return hashlib.sha256(block_string).hexdigest()

    @property
    def last_block(self):
        return self.chain[-1]

    def proof_of_work(self, last_proof):
        proof = 0
        while self.valid_proof(last_proof, proof) is False:
            proof += 1
        return proof

    @staticmethod
    def valid_proof(last_proof, proof):
        guess = f'{last_proof}{proof}'.encode()
        guess_hash = hashlib.sha256(guess).hexdigest()
        return guess_hash[:4] == "0000"

app = Flask(__name__)
blockchain = Blockchain()
users = {}

@app.route('/mine', methods=['POST'])
def mine():
    values = request.get_json()
    required = ['miner_address']
    if not all(k in values for k in required):
        return 'Missing values', 400

    miner_address = values['miner_address']
    last_block = blockchain.last_block
    last_proof = last_block['proof']
    proof = blockchain.proof_of_work(last_proof)
    blockchain.new_transaction(sender="0", recipient=miner_address, amount=1000)  # Mining reward
    block = blockchain.new_block(proof)
    response = {
        'message': "New Block Forged",
        'index': block['index'],
        'transactions': block['transactions'],
        'proof': block['proof'],
        'previous_hash': block['previous_hash'],
    }
    return jsonify(response), 200

@app.route('/transactions/new', methods=['POST'])
def new_transaction():
    values = request.get_json()
    required = ['sender', 'recipient', 'amount']
    if not all(k in values for k in required):
        return 'Missing values', 400

    amount = int(values['amount'])

    sender = users.get('current_user')
    if not sender:
        return 'User not logged in', 400

    if blockchain.balances.get(sender, 0) < amount:
        return 'Insufficient funds', 400

    index = blockchain.new_transaction(sender, values['recipient'], amount)

    response = {'message': f'Transaction will be added to Block {index}'}
    return jsonify(response), 201

@app.route('/block/new', methods=['POST'])
def new_block():
    values = request.get_json()
    required = ['index', 'timestamp', 'transactions', 'proof', 'previous_hash']
    if not all(k in values for k in required):
        return 'Missing values', 400

    # Add logic to validate and add the new block to the chain if valid
    blockchain.chain.append(values)
    blockchain.save_data()

    response = {'message': 'New block added to the chain'}
    return jsonify(response), 201

@app.route('/chain', methods=['GET'])
def full_chain():
    response = {
        'chain': blockchain.chain,
        'length': len(blockchain.chain),
    }
    return jsonify(response), 200

@app.route('/wallet/new', methods=['GET'])
def new_wallet():
    wallet = Wallet()
    response = {
        'address': wallet.get_address(),
        'private_key': wallet.private_key
    }
    return jsonify(response), 200

@app.route('/balance/<address>', methods=['GET'])
def get_balance(address):
    balance = blockchain.balances.get(address, 0)
    response = {'balance': balance}
    return jsonify(response), 200

@app.route('/login', methods=['POST'])
def login():
    values = request.get_json()
    required = ['private_key']
    if not all(k in values for k in required):
        return 'Missing values', 400

    wallet = Wallet()
    wallet.private_key = values['private_key']
    wallet.public_key = wallet.generate_public_key(wallet.private_key)

    users['current_user'] = wallet.get_address()

    response = {
        'address': wallet.get_address(),
        'private_key': wallet.private_key
    }
    return jsonify(response), 200

@app.route('/nodes/register', methods=['POST'])
def register_nodes():
    values = request.get_json()
    nodes = values.get('nodes')
    if nodes is None:
        return "Error: Please supply a valid list of nodes", 400

    for node in nodes:
        blockchain.register_node(node)

    response = {
        'message': 'New nodes have been added',
        'total_nodes': list(blockchain.nodes),
    }
    return jsonify(response), 201

@app.route('/', defaults={'path': ''})
@app.route('/<path:path>')
def serve(path):
    if path != "" and os.path.exists("frontend/" + path):
        return send_from_directory('frontend', path)
    else:
        return send_from_directory('frontend', 'index.html')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
