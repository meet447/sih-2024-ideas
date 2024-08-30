import requests
import pandas as pd
import networkx as nx
import matplotlib.pyplot as plt
from collections import Counter
from sklearn.ensemble import IsolationForest
import time

# Function to fetch transaction details using the provided API
def fetch_transaction(transaction_id):
    url = f"https://blockchain.info/rawtx/{transaction_id}"
    response = requests.get(url)
    if response.status_code == 200:
        return response.json()
    else:
        raise Exception("Failed to fetch transaction data")

# Function to fetch transaction history for a given wallet address
def fetch_wallet_transactions(wallet_address, retries=3, delay=5):
    url = f"https://blockchain.info/rawaddr/{wallet_address}"
    
    for attempt in range(retries):
        try:
            response = requests.get(url)
            if response.status_code == 200:
                print("succes @")
                return response.json()
            else:
                print(f"Attempt {attempt + 1}: Failed to fetch data for wallet {wallet_address} (Status code: {response.status_code})")
                time.sleep(delay)
        except requests.exceptions.RequestException as e:
            print(f"Attempt {attempt + 1}: Network error: {e}")
            time.sleep(delay)
    
    print(f"Failed to fetch wallet transaction history for {wallet_address} after {retries} attempts.")
    return None  # Return None if the data couldn't be fetched

# Function to parse transaction data
def parse_transaction_data(transaction_data):
    inputs = transaction_data.get('inputs', [])
    outputs = transaction_data.get('out', [])
    
    transactions = []
    
    for inp in inputs:
        from_address = inp['prev_out'].get('addr', 'unknown')
        for out in outputs:
            to_address = out.get('addr', 'unknown')
            amount = out.get('value', 0) / 1e8  # Convert Satoshi to BTC
            transactions.append({
                'from_wallet': from_address,
                'to_wallet': to_address,
                'amount': amount,
                'time': transaction_data.get('time')
            })
    
    return transactions

# Function to analyze transaction clusters using NetworkX
def analyze_transactions(transactions):
    df = pd.DataFrame(transactions)
    G = nx.from_pandas_edgelist(df, 'from_wallet', 'to_wallet', ['amount'], create_using=nx.DiGraph())
    
    clusters = list(nx.weakly_connected_components(G))
    return G, clusters

# Function to detect anomalies in transactions using AI (Isolation Forest)
def detect_anomalies(transactions):
    df = pd.DataFrame(transactions)
    features = df[['amount']]  # Using 'amount' as the feature for simplicity
    model = IsolationForest(contamination=0.1)
    model.fit(features)
    df['anomaly'] = model.predict(features)
    anomalies = df[df['anomaly'] == -1]
    
    return anomalies

# Function to identify end receivers in a cluster
def identify_end_receivers(G, largest_cluster):
    end_receivers = []
    
    for node in largest_cluster:
        if G.out_degree(node) == 0:  # No outgoing transactions, making it a potential end receiver
            end_receivers.append(node)
    
    return end_receivers

# Function to check common wallets in end receivers' transaction history
def find_common_wallets(end_receivers):
    all_wallets = []

    for receiver in end_receivers:
        wallet_data = fetch_wallet_transactions(receiver)
        for tx in wallet_data.get('txs', []):
            transactions = parse_transaction_data(tx)
            for transaction in transactions:
                all_wallets.append(transaction['from_wallet'])
    
    wallet_counter = Counter(all_wallets)
    common_wallets = [wallet for wallet, count in wallet_counter.items() if count > 1]
    
    return common_wallets

# Function to visualize the transaction network graph
def visualize_graph(G, largest_cluster, end_receivers, anomalies, blacklisted_wallets):
    pos = nx.spring_layout(G)
    plt.figure(figsize=(12, 8))
    
    # Draw all nodes
    nx.draw_networkx_nodes(G, pos, node_color='lightblue', node_size=500)
    
    # Highlight nodes in the largest cluster
    nx.draw_networkx_nodes(G, pos, nodelist=largest_cluster, node_color='orange', node_size=700)
    
    # Highlight end receivers
    nx.draw_networkx_nodes(G, pos, nodelist=end_receivers, node_color='red', node_size=800)
    
    # Highlight blacklisted wallets
    nx.draw_networkx_nodes(G, pos, nodelist=blacklisted_wallets, node_color='black', node_size=900)
    
    # Draw all edges
    nx.draw_networkx_edges(G, pos, width=1.0, alpha=0.5)
    
    # Draw labels
    nx.draw_networkx_labels(G, pos, font_size=12, font_color='black')
    
    # Highlight anomalies with red edges
    anomaly_edges = [(row['from_wallet'], row['to_wallet']) for idx, row in anomalies.iterrows()]
    nx.draw_networkx_edges(G, pos, edgelist=anomaly_edges, edge_color='red', width=2.0)
    
    plt.title("Transaction Network Graph with End Receivers and Blacklisted Wallets")
    plt.show()

# Main function
if __name__ == "__main__":
    transaction_id = "a4c2e1154a90759b3ebe771a1ee469bfc142a79a21dc662ae72cf355d100a6fd"
    transaction_data = fetch_transaction(transaction_id)
    
    transactions = parse_transaction_data(transaction_data)
    G, clusters = analyze_transactions(transactions)
    anomalies = detect_anomalies(transactions)
    
    # Assuming the end receivers are in the largest cluster
    largest_cluster = max(clusters, key=len)
    end_receivers = identify_end_receivers(G, largest_cluster)
    
    # Find common wallets in end receivers' transaction history
    blacklisted_wallets = find_common_wallets(end_receivers)
    
    print(f"End Receivers: {end_receivers}")
    print(f"Blacklisted Wallets: {blacklisted_wallets}")
    
    # Visualize the transaction graph with end receivers and blacklisted wallets
    visualize_graph(G, largest_cluster, end_receivers, anomalies, blacklisted_wallets)
