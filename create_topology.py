import os
import networkx as nx
import matplotlib.pyplot as plt

# Path to the directory containing config files
config_dir = 'Config_Files/'

# Create an empty graph
G = nx.Graph()
G.add_node("A")
G.add_node("B")
G.add_node("C")
G.add_node("D")
G.add_node("E")
G.add_node("F")
G.add_node("G")
G.add_node("H")
G.add_node("I")
G.add_node("J")

# Iterate over all files in the config directory
for filename in os.listdir(config_dir):
	file_path = os.path.join(config_dir, filename)
	
	# Read the config file and extract the necessary information
	with open(file_path, 'r') as file:
		# Parse the file and extract the necessary information
		# Assuming the file contains information about nodes and their weights
		# Modify the code below according to the structure of your config files
		
		# Add the node to the graph with the weight as an attribute
		
		# Connect the node to other nodes in the graph
		for i, line in enumerate(file):
			if i == 0:
				continue
			node, edge_weight, port = line.strip().split(' ')
			first_char = filename[0]
			G.add_edge(node, first_char, weight=float(edge_weight))

# Display the network topology
# Set the layout algorithm to avoid crossing over lines
pos = nx.spring_layout(G)

# Draw the network topology with edge labels
nx.draw(G, pos, with_labels=True)
edge_labels = nx.get_edge_attributes(G, 'weight')
nx.draw_networkx_edge_labels(G, pos, edge_labels=edge_labels)

# Show the plot
plt.show()