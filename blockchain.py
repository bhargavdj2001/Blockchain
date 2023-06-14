
import hashlib
import json
import requests
from time import time
from textwrap import dedent
from urllib import response
from urllib.parse import urlparse
from uuid import uuid4
from flask import Flask, jsonify, request, render_template 


class Blockchain(object):
    def __init__(self):
        self.chain = []                         # To store Blockchain
        self.current_transactions = []          # To store transactions
        self.nodes = set()

        # Create the genesis block
        self.new_block(previous_hash=1, proof=100)

    def new_block(self, proof, previous_hash=None):
        # Creates a new block and adds it to the chain 
        '''
        (parameter) proof : <int> The proof given by the Proof of Work algorithm
        (parameter) previous_hash : <str> Hash of previous Block
        (return) : <dict> new Block
        '''

        block = {
            'index' : len(self.chain)+1,
            'timestamp' : time(),
            'transactions' : self.current_transactions,
            'proof' : proof,
            'previous_hash' : previous_hash or self.hash(self.chain[-1]),
        }

        # Reset the current list of transactions
        self.current_transactions = []

        self.chain.append(block)
        return block 

    def new_transaction(self, sender, recipient, amount):
        # Adds a new transaction to the list of transactions 
        '''
        Creates a new transaction to go into the next mined block
        (parameter) sender : <str> Address of sender
        (parameter) recipient : <str> Address of recipient
        (parameter) amount : <int> Amount
        (return) : the index of the block that will hold this transaction.
        '''
        self.current_transactions.append({
            'sender' : sender,
            'recipient' : recipient,
            'amount' : amount 
        })

        return self.last_block['index']+1 

    def proof_of_work(self, last_proof):
        '''
        Simple Proof of Work Algorithm:
            - Find a number p' such that hash(pp') contains leading 
                4 zeroes, where p is the previous proof
            (parameter) last_proof : <int>
            (return) <int>
        '''
        proof = 0
        while self.valid_proof(last_proof, proof) is False:
            proof+=1 
        return proof 

    def register_node(self, address):
        '''
        Add a new node to the list of nodes
        (parameter) address : <str> Address of node. Example - 'http://192.168.0.5:5000'
        (return) None
        '''
        parsed_url = urlparse(address)
        self.nodes.add(parsed_url.netloc)

    def valid_chain(self, chain):
        '''
        Determine if a given blockchain is valid
        '''
        last_block = chain[0]
        current_index = 1

        while(current_index<len(chain)):
            block = chain[current_index]
            print(f'{last_block}')
            print(f'{block}')
            print('\n-----------\n')
            # Check that the hash of the block is correct
            if block['previous_hash']!=self.hash(last_block):
                return False 
            
            # Check that the Proof of Work is correct 
            if not self.valid_proof(last_block['proof'], block['proof']):
                return False 
            
            last_block = block 
            current_index+=1
        
        return True 

    def resolve_conflicts(self):
        '''
        This is out Consensus Algorithm, it resolves conflicts by replacing
        our chain with the longest one in the network.
        (return) True is our chain was replaced, False if not
        '''

        neighbors = self.nodes
        new_chain = None 

        # We are only looking for chains longer than ours 
        max_length = len(self.chain)

        # Grab and verify for chains from all the nodes in our network
        for node in neighbors:
            response = requests.get(f'http://{node}/chain')

            if response.status_code==200:
                length = response.json()['length']
                chain = response.json()['chain']

                # Check if the length is longer and the chain is valid
                if length>max_length and self.valid_chain(chain):
                    max_length = length 
                    new_chain = chain 

        # Replace out chain if we discovered a new, valid chain longer than ours
        if new_chain:
            self.chain = new_chain 
            return True
        
        return False 

    @staticmethod
    def valid_proof(last_proof, proof):
        '''
        Validates the Proof: Does hash(last_proof, proof) contain 4 leading zeroes?
        (return) True if correct, False if not. 
        '''
        guess = f'{last_proof}{proof}'.encode()
        guess_hash = hashlib.sha256(guess).hexdigest()
        return guess_hash[:4] == '0000'

    @staticmethod
    def hash(block):
        # Hashes a Block 
        '''
        Creates a SHA-256 hash of a Block 
        (parameter) block : <dict> Block
        (return) : <str>
        '''
        # We must make sure the Dictionary is Ordered, or we will have inconsistent hashes
        block_string = json.dumps(block, sort_keys=True).encode()
        return hashlib.sha256(block_string).hexdigest()

    @property 
    def last_block(self):
        # Returns the last block in the chain 
        return self.chain[-1]


# Instantiate our Node
app = Flask(__name__)

# Generate a globally unique address for this node
node_identifier = str(uuid4()).replace('-', '')

# Instantiate the Blockchain
blockchain = Blockchain()

@app.route('/', methods=['POST', 'GET'])
def index():
    return render_template('index.html')

@app.route('/mine', methods=['GET'])
def mine():
    # We run the proof of work algorithm to get the next proof
    last_block = blockchain.last_block
    last_proof = last_block['proof']
    proof = blockchain.proof_of_work(last_proof)

    # We must receive a reward for finding the proof.
    # The sender is "0" to signify that this node has mined a new coin.
    blockchain.new_transaction(
        sender = "0",
        recipient = node_identifier, 
        amount = 1,
    )

    #Forge the new Block by adding it to the chain
    previous_hash = blockchain.hash(last_block)
    block = blockchain.new_block(proof, previous_hash)    

    return render_template('mine.html', block=block)

@app.route('/transactions/new', methods=['GET', 'POST'])
def new_transaction():
    if request.method=='POST':
        s = request.form['sender']
        r = request.form['recipient']
        a = request.form['amount']
        index = blockchain.new_transaction(sender = s, recipient = r, amount = a)
        return render_template('transaction.html', index = index,t = 2)
    
    else:
        return render_template('transaction.html', t = 1)

@app.route('/chain', methods=['GET'])
def full_chain():
    chain = blockchain.chain 
    length = len(blockchain.chain)
    return render_template('display_chain.html', chain = chain, l = length)

@app.route('/nodes/register', methods=['GET', 'POST'])
def register_nodes():
    if (request.method=='POST'):
        node = request.form['n']
        blockchain.register_node(node)
        return render_template('register_nodes.html', t=2)
    else:
        return render_template('register_nodes.html', t=1)

@app.route('/nodes/resolve', methods=['GET'])
def consensus():
    replaced = blockchain.resolve_conflicts()
    return render_template('verify.html', r = replaced)

if __name__=="__main__":
    app.run(debug=True)
