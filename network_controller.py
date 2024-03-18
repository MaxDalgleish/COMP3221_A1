import socket
import json

def main():
	
	# Create a sending only socket
	s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

	print("Enter a port a command from the list")
	command = input("1 : disable_node\n2 : enable_node\n3: change_cost")
	command = command.split(" ")
	port, node_command = command[0], command[1]
	print(port)
	address = ('localhost', int(port))
	# Send data
	data = {
		'port': port,
		'type': 'command',
		'command': node_command,
	}

	message = json.dumps(data).encode()
	s.connect(address)
	s.sendall(message)
	# Close the socket
	s.close()

if __name__ == "__main__":
	main()