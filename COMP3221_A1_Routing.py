import networkx as nx
import socket
import threading
import sys
import time
import json
import signal
from queue import Queue

MAX_RETRIES = 5

class ListeningThread(threading.Thread):
	def __init__(self, port_no, processing_time, q):
		threading.Thread.__init__(self)
		self.processing_time = processing_time
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
			s.settimeout(3)
			# Accept the incoming connection
			try:
				conn, addr = s.accept()
				# print("Connection from: ", addr)
			except socket.timeout:
				# print("Error: Connection Timed Out listen")
				continue

			# Receive the data
			data = conn.recv(1024).decode("utf-8")
			data = json.loads(data)
			if not data:
				print("Error: No data received listen")
				break
			print("Received: ", data)
			print(" arriving at ", self.port_no)

			self.q.put(data)

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

			# Wait the Mandatory 10 seconds before sending a message
			time.sleep(10)

			# Ensure that the socket properly connects to the system
			retry_count = 0
			# while retry_count < MAX_RETRIES:
			
			for data in self.neighbours.values():
				print("Trying " + data[1] + " from " + self.node_id)
				try: 
					# Create a socket and connect
					s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
					s.connect(('localhost', int(data[1])))
					print("Connected to: " + data[1] + " from " + self.node_id)
					
					# put routing tablen into list
					routing_list = [(key, value['distance']) for key, value in self.routing_table.items()]

					# Sort the list by putting sending node at start
					routing_list.sort(key=lambda x: (x[0] != self.node_id, x[0]))

					# Convert the list to json
					routing_json = json.dumps(routing_list)

					# Send the routiong table data
					s.sendall(routing_json.encode("utf-8"))

					# close the connection
					s.close()
						
				except:
					#print("Error: Connection Failed sending")
					retry_count += 1
					time.sleep(1)
				continue
			

class RoutingTable(threading.Thread):
	def __init__(self, neighbours, q, node_id, routing_table):
		threading.Thread.__init__(self)
		self._stop = threading.Event()
		self.neighbours = neighbours
		self.processing_time = 1
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
		print(self.node_id + " Calculating: ")
		print(data)

		# Parse the data
		# put sending node into the routing table
		sender = data[0]
		sending_node = sender[0]
		for node in data:
			if node[0] == self.node_id:
				sending_cost = float(node[1])
		routing_table[sending_node]['distance'] = sending_cost
		data = data[1:]

		# put sending nodes neighbours into the routing table
		for neighbour in data:
			if neighbour[0] == self.node_id:
				continue
			node = neighbour[0]
			cost = float(neighbour[1]) + sending_cost
			if routing_table[node]['distance'] > cost:
				routing_table[node]['distance'] = cost
		print(self.routing_table)


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
			'A': {'distance': float('inf')},
			'B': {'distance': float('inf')},
			'C': {'distance': float('inf')},
			'D': {'distance': float('inf')},
			'E': {'distance': float('inf')},
			'F': {'distance': float('inf')},
			'G': {'distance': float('inf')},
			'H': {'distance': float('inf')},
			'I': {'distance': float('inf')},
			'J': {'distance': float('inf')}
		}
	routing_table[node_id]['distance'] = 0
	# input neighbours into the routing table
	for neighbour in neighbours:
		routing_table[neighbour]['distance'] = neighbours[neighbour][0]
		
	# create queue for thread communication
	q = Queue()
	
	router = RoutingTable(neighbours , q, node_id , routing_table)
	router.start()
	
	listener = ListeningThread(int(port_no), 1, q)
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

# def parse_config_file(file_data):




if __name__ == "__main__":
	main()