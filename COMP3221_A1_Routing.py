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
	def __init__(self, port_no, q):
		threading.Thread.__init__(self)
		self._stop = threading.Event()
		self.port_no = port_no
		self.q = q
	
	def stop(self):
		self._stop.set()
	
	def stopped(self):
		return self._stop.is_set()

	def run(self):
		print("ListeningThread started")
		# Create a socket
		# Ensure that the socket properly connects to the system
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
				break

			# Check if the data being received is from the controller
			if data['type'] == 'command':
				print(" Received Command from controller, ", data['command'])
			else:
				# print("Received: ", data, end="")
				# print(" arriving at ", self.port_no)

				# Put the data into the queue for routing thread
				self.q.put(data['routing_data'])

			# Send the data back to the client
			conn.close()


class SendingThread(threading.Thread):
	def __init__(self, neighbours, node_id , routing_table):
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
		print("SendingThread started")
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
			time.sleep(10)

			# Ensure that the socket properly connects to the system
			for data in self.neighbours.values():
				retry_count = 0
				# print("Trying " + data[1] + " from " + self.node_id)
				try: 
					while retry_count < MAX_RETRIES:
						# Create a socket and connect
						s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
						s.connect(('localhost', int(data[1])))
						# print("Connected to: " + data[1] + " from " + self.node_id)
						
						# put routing tablen into list
						routing_list = [(key, value['distance'], value['path']) for key, value in self.routing_table.items()]

						# Sort the list by putting sending node at start
						routing_list.sort(key=lambda x: (x[0] != self.node_id, x[0]))

						routing_json = {
							'port': self.node_id,
							'type': 'routing_table',
							'routing_data': routing_list
						}
						# Convert the list to json
						routing_json = json.dumps(routing_json)

						# Send the routiong table data
						s.sendall(routing_json.encode("utf-8"))

							
						s.close()
						break
							
				except:
					print("Error: Connection refused to " + data[1] + " from " + self.node_id + " retrying...")
					retry_count += 1
					time.sleep(0.5)
			

class RoutingTable(threading.Thread):
	def __init__(self, neighbours, q, node_id, routing_table):
		threading.Thread.__init__(self)
		self._stop = threading.Event()
		self.neighbours = neighbours
		self.routing_table = {}
		self.q = q
		self.node_id = node_id
		self.routing_table = routing_table
	
	def stop(self):
		self._stop.set()

	def stopped(self):
		return self._stop.is_set()
	
	def run(self):
		print("RoutingTable started")

		while (1):
			if self.stopped():
				print(self.name + " is stopping")
				return
			
			# Wait for soemthing to be put in the queue
			if self.q.empty():
				pass
			else:
				data = self.q.get()
				self.calculate(data, self.routing_table)

	def calculate(self, data, routing_table):
		
		# first handle sending node which is the first entry in the list
		# set cost from sending node to correct cost instead of 0 from sedner's routing table

		sender = data[0]
		sending_node = sender[0]
		for node in data[1:]:
			if node[0] == self.node_id:
				sending_cost = float(node[1])
				break
		if routing_table[sending_node]['distance'] > sending_cost:
			routing_table[sending_node]['path'] = sending_node
			routing_table[sending_node]['distance'] = sending_cost
		data = data[1:]

		# put sending nodes neighbours into the routing table
		for neighbour in data:
			if neighbour[0] == self.node_id:
				continue
			if neighbour[1] == float('inf'):
				continue
			node = neighbour[0]
			cost = float(neighbour[1]) + float(sending_cost)
			cost = round(cost, 2)
			if routing_table[node]['distance'] > float(cost):
				routing_table[node]['distance'] = float(cost)
				path = sending_node + neighbour[2]
				routing_table[node]['path'] = path
				
				# print statements
				print("I am Node " + self.node_id)
				for destination, data in self.routing_table.items():
					if self.node_id == destination:
						continue
					
					least_cost_path = self.node_id + data['path']
					link_cost = data['distance']
					
					# Print the formatted output
					print(f"Least cost path from {self.node_id} to {destination}: {least_cost_path}, link cost: {link_cost}.")
				


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
	routing_table = {
		'A': {'distance': float('inf'), 'path': ""},
		'B': {'distance': float('inf'), 'path': ""},
		'C': {'distance': float('inf'), 'path': ""},
		'D': {'distance': float('inf'), 'path': ""},
		'E': {'distance': float('inf'), 'path': ""},
		'F': {'distance': float('inf'), 'path': ""},
		'G': {'distance': float('inf'), 'path': ""},
		'H': {'distance': float('inf'), 'path': ""},
		'I': {'distance': float('inf'), 'path': ""},
		'J': {'distance': float('inf'), 'path': ""}
	}
	routing_table[node_id]['distance'] = float(0)
	# input neighbours into the routing table
	for neighbour in neighbours:
		routing_table[neighbour]['distance'] = float(neighbours[neighbour][0])
		routing_table[neighbour]['path'] = neighbour

	# inital routing table
	print("Initial Routing Table " + node_id)
	print(routing_table)
		
	# create queue for thread communication
	q = Queue()
	
	router = RoutingTable(neighbours , q, node_id , routing_table)
	router.start()
	
	listener = ListeningThread(int(port_no), q)
	listener.start()

	sender = SendingThread(neighbours, node_id, routing_table)
	sender.start()


	try:
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