"""
Consist of 3 method
	* connectTraining
	* startTrainingApp
	* startTraining

used only for the training and in order to run it needs the unity target executable.

"""
import socket
import subprocess
import sys, os
from multiprocessing import Process

sys.path.append('..')
from utils.constants import Constants as cnst


def connectTraining(trainingClassBuffer):
	"""
	Responsible
		* to create a socket communication with the target executable.
		* to receive the training class byte from the open connection.
		* to put the receiving byte into trainingClassBuffer parameter.

	:param trainingClassBuffer: {Queue(maxsize=1)} - Buffer used to 'give' the training class to :meth:`source.boardEventHandler.BoardEventHandler.startStreaming`

	"""
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
	trainingClassBuffer.put_nowait(bytes_received)

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
	"""
	Simple method, that only executes the unity target executable given in :data:`utils.constants.Constants.unityExePath`

	:param boardApiCallEvents: Events used in :py:class:`source.boardEventHandler.BoardEventHandler`

	"""
	with open(os.devnull, 'wb') as devnull:
		subprocess.check_call([cnst.unityExePath], stdout=devnull, stderr=subprocess.STDOUT)
	boardApiCallEvents["stopStreaming"].set()


def startTraining(startTrainingEvent, boardApiCallEvents, _shutdownEvent, trainingClassBuffer):
	"""
	Method runs via trainingProcess in :py:mod:`source.UIManager`

	:param startTrainingEvent: {Event} - Event which this process will be waiting for, before starting the connectTraining, startTrainingApp processes. This Event is set only by the :py:meth:`source.pyGUI.GUI.trainingButtonClick`
	:param boardApiCallEvents:  Events used in :py:class:`source.boardEventHandler.BoardEventHandler`
	:param _shutdownEvent:  {Event} - Event used to know when to let every running process terminate
	:param trainingClassBuffer: {Queue} -  Buffer will be used to 'give' the training class to :meth:`source.boardEventHandler.BoardEventHandler.startStreaming`, via :meth:`source.training.connectTraining`
	"""
	while not _shutdownEvent.is_set():
		startTrainingEvent.wait(1)
		if startTrainingEvent.is_set():
			boardApiCallEvents["startStreaming"].set()
			socketProcess = Process(target=connectTraining, args=(trainingClassBuffer,))
			applicationProcess = Process(target=startTrainingApp, args=(boardApiCallEvents,))
			if not socketProcess.is_alive():
				socketProcess.start()
			if not applicationProcess.is_alive():
				applicationProcess.start()
			socketProcess.join()
			applicationProcess.join()
			startTrainingEvent.clear()
