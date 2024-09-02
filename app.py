from flask import Flask, render_template, jsonify, request, redirect, url_for
import networkx as nx
import requests

app = Flask(__name__)

# Function to fetch transaction details using the provided API
def fetch_transaction(transaction_id):
    url = f"https://blockchain.info/rawtx/{transaction_id}"
    response = requests.get(url)
    return response.json() if response.status_code == 200 else None

# Function to fetch transaction history for a given wallet address
def fetch_wallet_transactions(wallet_address, after_timestamp=None):
    url = f"https://api.blockchain.info/haskoin-store/btc/address/{wallet_address}/transactions?limit=20&offset=0"
    response = requests.get(url)
    transactions = response.json() if response.status_code == 200 else []
    
    if after_timestamp:
        transactions = [tx for tx in transactions if tx.get('block', {}).get('mempool', 0) > after_timestamp]
    
    return transactions

def parse_transaction_data(transaction_data):
    transactions = []
    # Extract transaction time and address details based on actual response structure
    for inp in transaction_data.get('inputs', []):
        from_address = inp.get('prev_out', {}).get('addr', 'unknown')
        for out in transaction_data.get('out', []):
            to_address = out.get('addr', 'unknown')
            amount = out.get('value', 0) / 1e8  # Convert Satoshi to BTC
            transactions.append({
                'from_wallet': from_address,
                'to_wallet': to_address,
                'amount': amount,
                'time': transaction_data.get('time')
            })
    
    print("Parsed transactions:", transactions)  # Print for debugging
    return transactions


# Function to create a graph from transactions
def create_graph_from_transactions(transactions):
    G = nx.DiGraph()
    for tx in transactions:
        G.add_edge(tx['from_wallet'], tx['to_wallet'], amount=tx['amount'])
    return G

# Endpoint to fetch and return transaction graph data as JSON
@app.route('/transaction/<txid>', methods=['GET'])
def transaction_graph(txid):
    transaction_data = fetch_transaction(txid)
    if transaction_data:
        transactions = parse_transaction_data(transaction_data)
        G = create_graph_from_transactions(transactions)
        
        # Convert graph to a format suitable for D3.js or Plotly.js
        graph_data = {
            'nodes': [{'id': node} for node in G.nodes],
            'links': [{'source': u, 'target': v, 'value': data['amount']} for u, v, data in G.edges(data=True)]
        }
        
        return jsonify(graph_data)
    return jsonify({'error': 'Transaction not found'}), 404

# Endpoint to render the graph info page
@app.route('/info/<txid>', methods=['GET'])
def info(txid):
    return render_template('info.html', transaction_id=txid)

# Home route with input box
@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        transaction_id = request.form['transaction_id']
        return redirect(url_for('info', txid=transaction_id))
    return render_template('index.html')

# Endpoint to fetch wallet transactions made after a specific timestamp
@app.route('/wallet/<wallet_id>', methods=['GET'])
def wallet_transactions(wallet_id):
    # Fetch all transactions for the wallet
    transactions = fetch_wallet_transactions(wallet_id)
    
    detailed_transactions = []
    
    # Fetch detailed data for each transaction
    for tx in transactions:
        tx_details = fetch_transaction(tx['txid'])
        if tx_details:
            detailed_transactions.extend(parse_transaction_data(tx_details))
    
    # Create graph from the detailed transactions
    G = create_graph_from_transactions(detailed_transactions)
    
    # Convert graph to a format suitable for D3.js or Plotly.js
    graph_data = {
        'nodes': [{'id': node} for node in G.nodes],
        'links': [{'source': u, 'target': v, 'value': data['amount']} for u, v, data in G.edges(data=True)]
    }
    
    return jsonify(graph_data)


if __name__ == '__main__':
    app.run(debug=True)
