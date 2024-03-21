import socket
import threading
import sys
import time
import json
import signal
import select

MAX_RETRIES = 2
Node_up = True
should_terminate = threading.Event()


class ListeningThread(threading.Thread):
	def __init__(self, port_no, routing_table, config_file, node_id):
		threading.Thread.__init__(self)
		self._stop = should_terminate
		self.port_no = port_no
		self.routing_table = routing_table
		self.config_file = config_file
		self.node_id = node_id
		self.last_state = Node_up
		# self.q = q
	
	
	def stopped(self):
		return self._stop.is_set()

	def run(self):
		# Create a socket
		# Ensure that the socket properly connects to the system
		global Node_up
		retry_count = 0
		while retry_count < MAX_RETRIES:
			try: 
				s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
				s.bind(('localhost', self.port_no))
				s.listen(9)
				break
			except:
				print("Error: Port already in use")
				retry_count += 1
				time.sleep(1)
		else:
			print("Error: Maximum retries reached listen")
			return

		s.settimeout(1)
		while True:
			if self.stopped():
				print(self.name + " is stopping listen")
				s.close()
				return
			# Checking if the Node should be Receiving messages
			if Node_up != self.last_state:
				#Turned On
				if Node_up:
					s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
					s.bind(('localhost', self.port_no))
					s.listen(9)
				else:
					s.close()
				self.last_state = Node_up
				continue

			if not Node_up:
				continue


			# Accept the incoming connection
			try:
				conn, addr = s.accept()
				# print("Connection from: ", addr)
			except socket.timeout:
				continue

			# Receive the data
			data = json.loads(conn.recv(1024).decode())
			if not data:
				print("Error: No data received listen")
				continue

			# Check if the data being received is from the controller

			# Checking each nodes routing data that is incoming
			routing_data = data['routing_data']
			for node in routing_data:
				# If the data is this nodes data, skip
				if node == self.port_no:
					continue
				# If the data doesn't exist in our table, add all
				if node not in self.routing_table:
					self.routing_table[node] = routing_data[node]
				# if the data already exists, compare the version numbers
				if node in self.routing_table:
					for key in routing_data[node]:
						if key in self.routing_table[node]:
							# Checking if the version number is greater
							if self.routing_table[node][key][1] < routing_data[node][key][1]:
								# Replacing the data and updating the config file if the node changes the link cost
								self.routing_table[node][key] = routing_data[node][key]
								self.routing_table[key][node] = [routing_data[node][key][0], routing_data[node][key][1]]
								if self.routing_table[node][key][0] != float("inf"):
									if self.node_id == key:
										update_config_files(self.config_file, node, routing_data[node][key][0])
									elif self.node_id == node:
										update_config_files(self.config_file, key, routing_data[node][key][0])
						else:
							self.routing_table[node][key] = routing_data[node][key]

			# Send the data back to the client
			conn.close()


class SendingThread(threading.Thread):
	def __init__(self, neighbours, node_id, routing_table):
		threading.Thread.__init__(self)
		self._stop = should_terminate
		self.neighbours = neighbours
		self.node_id = node_id
		self.routing_table = routing_table
	
	
	def stopped(self):
		return self._stop.is_set()

	def run(self):
		global Node_up
		while (1):
			# Threading stopping should be before the intialization of the socket
			# Otherwise socket connects to a non-existing port
			if self.stopped():
				print(self.name + " is stopping sending")
				return
			
			time.sleep(10)

			# Check if the Node is currently up
			if not Node_up:
				continue

			# Wait the Mandatory 10 seconds before sending a message

			# Ensure that the socket properly connects to the system
			for key, values in self.neighbours.items():
				
				try: 
					# Create a socket and connect
					s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
					s.connect(('localhost', int(values[1])))
					for keys in self.routing_table[self.node_id]:
						if keys == key and self.routing_table[self.node_id][key][0] == float("inf"):
							# {'A': [length, version_numer]}
							self.routing_table[self.node_id][key][1] += 1
							self.routing_table[self.node_id][key][0] = values[0]
					

					routing_json = {
						'port': self.node_id,
						'type': 'routing_table',
						'routing_data': self.routing_table
					}
					# Convert the list to json
					routing_json = json.dumps(routing_json)

					# Send the routiong table data
					s.sendall(routing_json.encode("utf-8"))

					s.close()
							
				except:
					print("Error: Connection refused to " + values[1] + " from " + self.node_id + " retrying...")
					# If the connection is refused, set the link cost to infinity
					# and increase the version number by one
					for keys in self.routing_table[self.node_id]:
						if keys == key and self.routing_table[self.node_id][key][0] != float("inf"):
							self.routing_table[self.node_id][key][0] = float("inf")
							self.routing_table[self.node_id][key][1] += 1
					
					# set the link cost to infinity if can not reach node
					
			

class RoutingTable(threading.Thread):
	def __init__(self, neighbours, node_id, routing_table):
		threading.Thread.__init__(self)
		self._stop = should_terminate
		self.neighbours = neighbours
		self.routing_table = {}
		self.node_id = node_id
		self.routing_table = routing_table
	

	def stopped(self):
		return self._stop.is_set()
	
	def run(self):

		while (1):
			if self.stopped():
				print(self.name + " is stopping")
				return
			# Check if the Node is currently up
			if not Node_up:
				# Wait 10 seconds before checking again
				time.sleep(10)
				continue
		
			self.calculate(self.routing_table, self.node_id)
			time.sleep(3)



	def calculate(self, routing_table, node_id):
		# ROUTINGTABLE = {'A': {'B': [length, version_number]}}
		visited = []
		visited.append(node_id)
		dijkstras = {}
		active_nodes = dict(routing_table[node_id])
		for key in active_nodes.keys():
			active_nodes[key] = [float(active_nodes[key][0]), node_id]

		# Comparing the distance at each node
			
		smallest_node_distance = min(active_nodes.items(), key=lambda x: x[1][0])

		# {'A': [length, predecessor]}
		dijkstras[smallest_node_distance[0]] = [smallest_node_distance[1][0], smallest_node_distance[1][1]]
		visited.append(smallest_node_distance[0])
		# While not every node has been visited
		while len(visited) != len(routing_table):
			for key, value in routing_table[smallest_node_distance[0]].items():
				if key in active_nodes:
					# If cost is higher than new cost, replace it
					if float(active_nodes[key][0]) > (float(value[0]) + float(smallest_node_distance[1][0])):
						active_nodes[key] = [(float(value[0]) + float(smallest_node_distance[1][0])), smallest_node_distance[0]]
				else:
					active_nodes[key] = [float(value[0]) + float(smallest_node_distance[1][0]), smallest_node_distance[0]]
			# Sort by nodes that haven't already been visited
			filtered_items = {k: v for k, v in active_nodes.items() if k not in visited}
			smallest_node_distance = min(filtered_items.items(), key=lambda x: float(x[1][0]))
			dijkstras[smallest_node_distance[0]] = [smallest_node_distance[1][0], smallest_node_distance[1][1]]
			visited.append(smallest_node_distance[0])
		# Order the dictionary in alphabetical order by keys
		sorted_dict = {key: dijkstras[key] for key in sorted(dijkstras.keys())}
		self.print_routes(sorted_dict)

	def print_routes(self, dijkstras):
		print("I am Node " + self.node_id)
		for key, value in dijkstras.items():

			# If the link cost is infinity, skip
			if float(value[0]) == float("inf"):
				continue
			result = self.find_path(dijkstras, self.node_id, key)
			print("Least cost path from " + self.node_id + " to " + key + ": " + result + ", link cost: " + str(round(float(value[0]), 3)))

	
	def find_path(self, data, start_node, end_node):
		path = [end_node]  # Start with the end node
		current_node = end_node

		# Traverse backwards from the end node to the start node
		while current_node != start_node:
			# Get the predecessor of the current node
			current_node = data[current_node][1]
			path.append(current_node)  # Add the predecessor to the path

		# Reverse the path to get the correct order
		path.reverse()
		return ''.join(path)

class ReadingThread(threading.Thread):
	def __init__(self, node_id, routing_table, neighbours):
		threading.Thread.__init__(self)
		self._stop = should_terminate
		self.node_id = node_id
		self.routing_table = routing_table
		self.neighbours = neighbours
	

	def stopped(self):
		return self._stop.is_set()
		
	def run(self):
		global Node_up
		print("Enter a command from the list")
		print("1: disable_node\n2: enable_node\n3: change_cost\n")
		while(1):
			if self.stopped():
				print(self.name + " is stopping sending")
				return
			# read input from command line
			command, _, _ = select.select([sys.stdin], [], [], 1)
			if command:	
				command = sys.stdin.readline().strip()
			else:
				continue

			command = command.split(" ")

			if command[0] == "1":

				Node_up = False
				print(self.node_id + " is down")
			elif command[0] == "2":
				Node_up = True
				print(self.node_id + " is up")
			elif command[0] == "3":
				# Change the cost of the link
				neighbour_node = command[1]
				new_cost = command[2]
				# {'A': [length, version_number]}
				if neighbour_node in self.routing_table[self.node_id]:
					self.routing_table[self.node_id][neighbour_node][0] = new_cost
					self.routing_table[self.node_id][neighbour_node][1] += 1
					#{A: [length, port], B: [length, port]}
					self.neighbours[neighbour_node][0] = new_cost
					print("Link cost from " + self.node_id + " to " + neighbour_node + " changed to " + new_cost)
				else:
					print("Error: Neighbour not found")


def valid_input_check():
	# Read the command line arguments <Node-ID> <Port-NO> <Node-ConfigFile>
	args = sys.argv[1:]
	if (len(args) != 3):
		print("Usage: python COMP3221_A1_Routing.py <Node-ID> <Port-NO> <Node-ConfigFile>")
		return False

	node_id, port_no, config_file = args[0], args[1], args[2]

	# Ensure Node-ID is a english letter
	if not node_id.isalpha() or not node_id.isupper() or len(node_id) != 1:
		print("Error: Node-ID must be a single capital letter of the English alphabet")
		return False
	
	# Ensure Port-NO 
	try:
		port_no = int(port_no)
		if port_no < 6000:
			raise ValueError("Error: Port-NO must be greater than or equal to 6000")
	except ValueError as e: 
		print(str(e))
		return False
	

	# Read the configuration file
	try:
		open(config_file, "r")
	except FileNotFoundError:
		print("Error: File not found")
		return False

	return True

def update_config_files(config_file, node_id, new_distance):
	with open(config_file, "r") as file:
		lines = file.readlines()
		
	with open(config_file, "w") as file:
		for line in lines:
			if line.startswith(node_id):
				line = line.split()
				line[1] = new_distance
				file.write(" ".join(line) + "\n")
			else:
				file.write(line)

def signal_handler(sig, frame):
	print('You pressed Ctrl+C!')
	should_terminate.set()
			

def main():
	signal.signal(signal.SIGINT, signal_handler)
	# Check if the input is valid
	if not valid_input_check():
		return
	node_id, port_no, config_file = sys.argv[1], sys.argv[2], sys.argv[3]

	# Parse the configuration file
	neighbours = {}
	file_data = []
	for line in open(config_file, "r"):
		file_data.append(line.strip())
	
	for line in file_data[1:]:
		line = line.split()
		neighbours[line[0]] = [line[1], line[2]]
		
	# Setup routing table
	# {'A': {'B': [length, version_number]}}
	temp = {}
	for neighbour in neighbours:
		temp[neighbour] = [neighbours[neighbour][0], 1]
	routing_table = {node_id: temp}

	listener = ListeningThread(int(port_no), routing_table, config_file, node_id)
	listener.start()

	sender = SendingThread(neighbours, node_id, routing_table)
	sender.start()

	reader = ReadingThread(node_id, routing_table, neighbours)
	reader.start()

	time.sleep(15)


	router = RoutingTable(neighbours , node_id, routing_table)
	router.start()
	while(should_terminate.is_set() == False):
		pass
	return



if __name__ == "__main__":
	main()