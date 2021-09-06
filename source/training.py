import socket
import subprocess
import sys, os
from multiprocessing import Process

sys.path.append('..')
from utils.constants import Constants as cnst


def connectTraining(trainingClassBuffer):
	# create socket
	s = socket.socket()
	socket.setdefaulttimeout(None)
	print('socket created ')

	# IP and PORT connection
	port = 8080
	# s.bind(('139.91.190.32', port)) #local host
	s.bind(('127.0.0.1', port))  # local host
	s.listen(30)  # listening for connection for 30 sec?
	print('socket listensing ... ')

	# try:
	c, addr = s.accept()  # when port connected
	print("\ngot connection from ", addr)

	# 1st communication with Quest
	bytes_received = c.recv(1024)  # received bytes
	print(bytes_received.decode("utf-8"))

	# Send "True" string to start the Quest app
	nn_output = "True"
	arr2 = bytes(nn_output, 'utf-8')
	c.sendall(arr2)  # sending back

	# Quest sends the arrow number
	bytes_received = c.recv(1).decode("utf-8")  # received bytes
	print(bytes_received)

	if bytes_received != "E" and bytes_received != "":

		# q_label.put(int(bytes_received))
		bytes_received_old = bytes_received

		while True:  # bytes_received != "E": # "E" means end of the action

			bytes_received = c.recv(1).decode("utf-8")  # received bytes

			if bytes_received == "E" or bytes_received == "":
				break
			else:
				if bytes_received != bytes_received_old:
					# print(bytes_received)
					trainingClassBuffer.put_nowait(bytes_received)
					bytes_received_old = bytes_received

	c.shutdown(socket.SHUT_RDWR)
	c.close()


def startTrainingApp(boardApiCallEvents):
	with open(os.devnull, 'wb') as devnull:
		subprocess.check_call([cnst.unityExePath], stdout=devnull, stderr=subprocess.STDOUT)
	boardApiCallEvents.stopStreaming.set()


def startTraining(startTrainingEvent, boardApiCallEvents, _shutdownEvent, trainingClassBuffer):
	while not _shutdownEvent.is_set():
		startTrainingEvent.wait(1)
		if startTrainingEvent.is_set():
			boardApiCallEvents.startStreaming.set()
			socketProcess = Process(target=connectTraining, args=(trainingClassBuffer,))
			applicationProcess = Process(target=startTrainingApp, args=(boardApiCallEvents,))
			if not socketProcess.is_alive():
				socketProcess.start()
			if not applicationProcess.is_alive():
				applicationProcess.start()
			socketProcess.join()
			applicationProcess.join()
			startTrainingEvent.clear()
