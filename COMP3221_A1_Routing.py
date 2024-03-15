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
				print("Listening on port: ", self.port_no)
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
				print("Connection from: ", addr)
			except socket.timeout:
				print("Error: Connection Timed Out listen")
				continue

			# Receive the data
			data = conn.recv(1024)
			if not data:
				break
			print("Received: ", data.decode("utf-8"))

			self.q.put(data.decode("utf-8"))

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

			# Wait the Mandatory 10 seconds before sending a message
			time.sleep(10)
			for neighbour in self.neighbours:

				s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
				# Ensure that the socket properly connects to the system
				retry_count = 0
				while retry_count < MAX_RETRIES:
					for data in self.neighbours.values():
						print("try: ", data[1])
						try: 
							s.connect(('localhost', int(data[1])))
							print("Connected to: ", data[1])
							# s.connect(('localhost', int(self.neighbours[neighbour][1])))
						except:
							print("Error: Connection Failed sending")
							retry_count += 1
							time.sleep(1)
				else:
					print("Error: Maximum retries reached sending")
					print(self.name + " is stopping sending2")
					return
				
					# Create a socket
				time.sleep(1)
				# Send the data
				s.sendall(b'Sending from ' + self.node_id.encode("utf-8") + b' to ' + neighbour.encode("utf-8") + b' ' + self.neighbours[neighbour][0].encode("utf-8"))
				s.close()


class RoutingTable(threading.Thread):
	def __init__(self, neighbours, q):
		threading.Thread.__init__(self)
		self._stop = threading.Event()
		self.neighbours = neighbours
		self.routing_table = {}
		self.processing_time = 1
		self.q = q
	
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
		print("Calculating")
		print(data)


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
	
	router = RoutingTable(neighbours , q=q)
	router.start()
	
	listener = ListeningThread(int(port_no), 1, q=q)
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

# def parse_config_file(file_data):




if __name__ == "__main__":
	main()