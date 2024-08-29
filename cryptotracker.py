import requests
import matplotlib.pyplot as plt


def get_wallet_transactions(wallet_address):
    url = f'https://blockchain.info/rawaddr/{wallet_address}?format=json'
    response = requests.get(url)
    return response.json()

import networkx as nx

def create_wallet_graph(wallet_data):
    G = nx.DiGraph()

    # Incoming transactions
    for tx in wallet_data['txs']:
        for input_tx in tx['inputs']:
            if 'prev_out' in input_tx and 'addr' in input_tx['prev_out']:
                source = input_tx['prev_out']['addr']
                G.add_node(source)
                G.add_edge(source, wallet_data['address'], weight=input_tx['prev_out']['value'])

        # Outgoing transactions
        for output in tx['out']:
            if 'addr' in output:
                target = output['addr']
                G.add_node(target)
                G.add_edge(wallet_data['address'], target, weight=output['value'])

    return G

from sklearn.cluster import DBSCAN
import numpy as np

def analyze_wallet_graph(G):
    node_positions = nx.spring_layout(G)
    positions = np.array([node_positions[node] for node in G.nodes()])

    # Apply DBSCAN for anomaly detection
    clustering = DBSCAN(eps=0.1, min_samples=2).fit(positions)
    labels = clustering.labels_

    # Highlight clusters or anomalies
    plt.figure(figsize=(10, 10))
    nx.draw(G, pos=node_positions, node_color=labels, with_labels=True, cmap=plt.cm.rainbow, node_size=700)
    plt.show()

def calculate_risk_score(G, wallet_address):
    # Example: Centrality-based risk score
    centrality = nx.degree_centrality(G)
    score = centrality.get(wallet_address, 0) * 100

    # Example: Increase score if connected to flagged wallets
    flagged_wallets = ['known_criminal_wallet_1', 'known_criminal_wallet_2']
    connections = [n for n in G.neighbors(wallet_address) if n in flagged_wallets]
    if connections:
        score += len(connections) * 10

    return score


if __name__ == "__main__":
    wallet_address = "bc1qw9c743p7jynaya7mvjx58u9tj4qeg44s8utqxd"
    wallet_data = get_wallet_transactions(wallet_address)

    # Create the transaction graph
    G = create_wallet_graph(wallet_data)

    # Analyze the transaction graph
    analyze_wallet_graph(G)

    # Calculate and print the risk score
    risk_score = calculate_risk_score(G, wallet_address)
    print(f"Risk Score for {wallet_address}: {risk_score}")
