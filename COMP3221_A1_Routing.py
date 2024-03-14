import networkx as nx
import socket
import threading
import sys
import time
import json

MAX_RETRIES = 5

class ListeningThread(threading.Thread):
	def __init__(self, port_no, processing_time):
		threading.Thread.__init__(self)
		self.processing_time = processing_time
		self._stop = threading.Event()
		self.port_no = port_no
	
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
			print("Error: Maximum retries reached")
			return


		while True:
			if self.stopped():
				print(self.name + " is stopping")
				s.close()
				return
			try:
				time.sleep(self.processing_time)
			except:
				print("Already interrupted")
			# Accept the incoming connection
			conn, addr = s.accept()
			print("Connection from: ", addr)

			# Receive the data
			data = conn.recv(1024)
			if not data:
				break
			print("Received: ", data.decode("utf-8"))

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
				print(self.name + " is stopping")
				return

			# Wait the Mandatory 10 seconds before sending a message
			time.sleep(10)
			for neighbour in self.neighbours:

				s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
				# Ensure that the socket properly connects to the system
				retry_count = 0
				while retry_count < MAX_RETRIES:
					try: 
						s.connect(('localhost', int(self.neighbours[neighbour][1])))
						break
					except:
						print("Error: Connection Failed")
						retry_count += 1
						time.sleep(1)
				else:
					print("Error: Maximum retries reached")
					return
				
					# Create a socket
				time.sleep(1)
				# Send the data
				s.sendall(b'Sending from ' + self.node_id.encode("utf-8"))
				s.close()


class RoutingTable(threading.Thread):
	def __init__(self, neighbours):
		threading.Thread.__init__(self)
		self._stop = threading.Event()
		self.neighbours = neighbours
		self.routing_table = {}
		self.processing_time = 1
	
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
			

def main():
	# Check if the input is valid
	file_data = []
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
	
	
	listener = ListeningThread(int(port_no), 1)
	listener.start()

	sender = SendingThread(neighbours, node_id)
	sender.start()

	router = RoutingTable(neighbours)
	router.start()

	try:
		while(1):
			pass
	except KeyboardInterrupt:
		print("Interrupted")
		sender.stop()
		listener.stop()
		router.stop()
		print('here')
		return

# def parse_config_file(file_data):




if __name__ == "__main__":
	main()