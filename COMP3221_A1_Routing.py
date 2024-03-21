import networkx as nx
import socket
import threading
import sys
import time
import json
import signal
from queue import Queue

MAX_RETRIES = 5
Node_up = True


class ListeningThread(threading.Thread):
	def __init__(self, port_no, routing_table):
		threading.Thread.__init__(self)
		self._stop = threading.Event()
		self.port_no = port_no
		self.routing_table = routing_table
		# self.q = q
	
	def stop(self):
		self._stop.set()
	
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


		while True:
			if self.stopped():
				print(self.name + " is stopping listen")
				s.close()
				return
			# Checking if the Node should be Receiving messages
			if not Node_up:
				continue

			s.settimeout(3)
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
			#if data['type'] == 'command':
				#print(" Received Command from controller, ", data['command_values'])
			#if data['type'] == 'routing_table':
			else:

				# self.q.put(data['routing_data'])
				routing_data = data['routing_data']
				for node in routing_data:
					if node == self.port_no:
						continue
					if node not in self.routing_table:
						self.routing_table[node] = routing_data[node]

			# Send the data back to the client
			conn.close()


class SendingThread(threading.Thread):
	def __init__(self, neighbours, node_id, routing_table):
		threading.Thread.__init__(self)
		self._stop = threading.Event()
		self.neighbours = neighbours
		self.node_id = node_id
		self.routing_table = routing_table
	
	def stop(self):
		self._stop.set()
	
	def stopped(self):
		return self._stop.is_set()

	def run(self):
		global Node_up
		while (1):
			# Threading stopping should be before the intialization of the socket
			# Otherwise socket connects to a non-existing port
			if self.stopped():
				print(self.name + " is stopping sending1")
				return
			
			# Check if the Node is currently up
			if not Node_up:
				continue

			# Wait the Mandatory 10 seconds before sending a message
			time.sleep(3)

			# Ensure that the socket properly connects to the system
			for neighbour in self.neighbours.values():
				retry_count = 0
				# print("Trying " + data[1] + " from " + self.node_id)
				try: 
					while retry_count < MAX_RETRIES:
						# Create a socket and connect
						s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
						s.connect(('localhost', int(neighbour[1])))
						# print("Connected to: " + data[1] + " from " + self.node_id)
						

						routing_json = {
							'port': self.node_id,
							'type': 'routing_table',
							'time': time.time(),
							'routing_data': self.routing_table
						}
						# Convert the list to json
						routing_json = json.dumps(routing_json)

						# Send the routiong table data
						s.sendall(routing_json.encode("utf-8"))

						s.close()
						break
							
				except:
					print("Error: Connection refused to " + neighbour[1] + " from " + self.node_id + " retrying...")
					retry_count += 1
					time.sleep(0.5)
				if retry_count == MAX_RETRIES:
					print("Error: Maximum retries reached sending")
					# set the link cost to infinity
					self.routing_table[self.node_id][neighbour[0]] = float('inf')
			

class RoutingTable(threading.Thread):
	def __init__(self, neighbours, node_id, routing_table):
		threading.Thread.__init__(self)
		self._stop = threading.Event()
		self.neighbours = neighbours
		self.routing_table = {}
		self.node_id = node_id
		self.routing_table = routing_table
	
	def stop(self):
		self._stop.set()

	def stopped(self):
		return self._stop.is_set()
	
	def run(self):

		while (1):
			if self.stopped():
				print(self.name + " is stopping")
				return
			# Check if the Node is currently up
			if not Node_up:
				time.sleep(10)
				continue
		
			self.calculate(self.routing_table, self.node_id)
			time.sleep(3)



	def calculate(self, routing_table, node_id):

		visited = []
		visited.append(node_id)
		dijkstras = {}
		active_nodes = dict(routing_table[node_id])
		for key in active_nodes.keys():
			active_nodes[key] = [active_nodes[key], node_id]
		smallest_node_distance = min(active_nodes.items(), key=lambda x: x[1][0])

		# {'A': [length, predecessor]}
		dijkstras[smallest_node_distance[0]] = [smallest_node_distance[1][0], smallest_node_distance[1][1]]
		visited.append(smallest_node_distance[0])
		while len(visited) != len(routing_table):
			for key, value in routing_table[smallest_node_distance[0]].items():
				if key in active_nodes:
					if float(active_nodes[key][0]) > (float(value) + float(smallest_node_distance[1][0])):
						active_nodes[key] = [(float(value) + float(smallest_node_distance[1][0])), smallest_node_distance[0]]
				else:
					active_nodes[key] = [float(value) + float(smallest_node_distance[1][0]), smallest_node_distance[0]]
			filtered_items = {k: v for k, v in active_nodes.items() if k not in visited}
			smallest_node_distance = min(filtered_items.items(), key=lambda x: float(x[1][0]))
			dijkstras[smallest_node_distance[0]] = [smallest_node_distance[1][0], smallest_node_distance[1][1]]
			visited.append(smallest_node_distance[0])
		sorted_dict = {key: dijkstras[key] for key in sorted(dijkstras.keys())}
		self.print_routes(sorted_dict)

	def print_routes(self, dijkstras):
		print("I am Node " + self.node_id)
		for key, value in dijkstras.items():
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
	def __init__(self, node_id):
		threading.Thread.__init__(self)
		self._stop = threading.Event()
		self.node_id = node_id
	
	def stop(self):
		self._stop.set()

	def stopped(self):
		return self._stop.is_set()
		
	def run(self):

		global Node_up

		while(1):
			if self.stopped():
				print(self.name + " is stopping sending1")
				return
			# read input from command line
			print("Enter a command from the list")
			command = input("1: disable_node\n2: enable_node\n3: change_cost\n")
			command = command.split(" ")
			

			if Node_up and command[0] == "1":
				Node_up = False
				print(self.node_id + " is down")
			elif not Node_up and command[0] == "2":
				Node_up = True
				print(self.node_id + " is up")


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

def signal_handler(sig, frame):
	print('You pressed Ctrl+C!')
	raise KeyboardInterrupt
			

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
	temp = {}
	for neighbour in neighbours:
		temp[neighbour] = neighbours[neighbour][0]
	routing_table = {node_id: temp}

	listener = ListeningThread(int(port_no), routing_table)
	listener.start()

	sender = SendingThread(neighbours, node_id, routing_table)
	sender.start()

	reader = ReadingThread(node_id)
	reader.start()

	try:
		time.sleep(15)
	except KeyboardInterrupt:
		# End the Program
		print("Interrupted")
		listener.stop()
		sender.stop()
		return


	try:
		router = RoutingTable(neighbours , node_id, routing_table)
		router.start()
		while(1):
			pass
	except KeyboardInterrupt:
		# End the Program
		print("Interrupted")
		router.stop()
		listener.stop()
		sender.stop()
		return



if __name__ == "__main__":
	main()