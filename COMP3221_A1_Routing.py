import networkx as nx
import socket
import threading
import sys
import time

class ListeningThread(threading.Thread):
	def __init__(self, node_id, port_no):
		threading.Thread.__init__(self)
		self.node_id = node_id
		self.port_no = port_no
	
	def stop(self):
		self._stop.set()
	
	def stopped(self):
		return self._stop.is_set()

	def run(self):
		# Create a socket
		s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
		s.bind(('localhost', self.port_no))
		s.listen(9)

		while True:
			if self.stopped():
				print(self.name + " is stopping")
				s.close()
				return
			try:
				time.sleep(self.processing_time)
			except:
				print("Alreay interrupted")
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

def main():
	# Check if the input is valid
	if not valid_input_check():
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
		with open(config_file, "r") as f:
			lines = f.readlines()
	except FileNotFoundError:
		print("Error: File not found")
		return False

	return True

if __name__ == "__main__":
	main()