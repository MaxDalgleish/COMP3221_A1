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
				#print("Connection from: ", addr)
			except socket.timeout:
				continue

			# Receive the data
			data = json.loads(conn.recv(1024).decode())
			if not data:
				break

			# Check if the data being received is from the controller
			if data['type'] == 'command':
				print(" Received Command from controller, ", data['command'])
			else:
				print("Received: ", data, end="")
				print(" arriving at ", self.port_no)

				self.q.put(data)

			# Send the data back to the client
			conn.close()


class SendingThread(threading.Thread):
	def __init__(self, neighbours, node_id):
		threading.Thread.__init__(self)
		self._stop = threading.Event()
		self.neighbours = neighbours
		self.node_id = node_id
	
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
			
			for neighbour in self.neighbours.values():
				retry_count = 0
				print("Trying " + neighbour[1] + " from " + self.node_id)
				sending_data = {
					'port': self.node_id,
					'type': 'routing'
				}
				while (retry_count < MAX_RETRIES):
					try:
						# Create a socket and connect
						s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
						s.connect(('localhost', int(neighbour[1])))
						print("Connected to: " + neighbour[1] + " from " + self.node_id)

						
						# Send the data
						s.sendall(json.dumps(sending_data).encode())

						# close the connection
						s.close()
						break
							
					except:
						print("Error: Connection refused to " + neighbour[1] + " from " + self.node_id + " retrying...")
						retry_count += 1
						time.sleep(0.5)
			

class RoutingTable(threading.Thread):
	def __init__(self, neighbours, q, node_id):
		threading.Thread.__init__(self)
		self._stop = threading.Event()
		self.neighbours = neighbours
		self.routing_table = {}
		self.q = q
		self.node_id = node_id
	
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
				self.calculate(data)

	def calculate(self, data):
		print(self.node_id + " Calculating: " + str(data))



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

	neighbours = {}
	file_data = []
	for line in open(config_file, "r"):
		file_data.append(line.strip())
	
	for line in file_data[1:]:
		line = line.split()
		neighbours[line[0]] = [line[1], line[2]]
	
	# Parse the configuration file
		
	# create queue for thread communication
	q = Queue()
	
	router = RoutingTable(neighbours , q, node_id)
	router.start()
	
	listener = ListeningThread(int(port_no), q)
	listener.start()

	sender = SendingThread(neighbours, node_id)
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