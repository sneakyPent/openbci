"""
Consist of 3 method
	* connectTraining
	* startTrainingApp
	* startTraining

used only for the training and in order to run it needs the unity target executable.

"""
import queue
import socket
import subprocess
import os
import time
from multiprocessing import Process, Event, Queue

import joblib
from utils.coloringPrint import printError
from utils.constants import Constants as cnst
from utils.filters import *
from classification.train_processing_cca_3 import calculate_cca_correlations


def socketConnect(boardApiCallEvents, socketConnection, stopOnlineStreamingEvent):
	"""
	* Responsible

		* to create a socket communication with the target executable.
		* to receive the training class byte from the open connection.
		* to put the receiving byte into trainingClassBuffer parameter.
		* to set the socketConnection event, only if socket connection established. When set,  the :py:meth:`source.training.startTrainingApp` process and the :py:meth:`source.boardEventHandler.BoardEventHandler.startStreaming` can be start.

	* When the connection could not be established then wait for 10 sec and then retrying.

	:param Queue(maxsize=1) trainingClassBuffer: Buffer used to 'give' the training class to :meth:`source.boardEventHandler.BoardEventHandler.startStreaming`.
	:param Event socketConnection: Used as flag so the main process :py:meth:`source.training.startTraining` can proceed to start the streaming and the training application.

	"""
	# create socket
	s = socket.socket()
	socket.setdefaulttimeout(None)
	print('socket created ')

	# IP and PORT connection
	port = 8080
	while not socketConnection.is_set():
		try:
			# s.bind(('139.91.190.32', port)) #local host
			s.bind(('127.0.0.1', port))  # local host
			s.listen(30)  # listening for connection for 30 sec?
			print('socket listensing ... ')
			# try:
			socketConnection.set()
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
			c.sendall('2'.encode())
			try:
				if int(bytes_received) == cnst.onlineUnitySentByte:
					boardApiCallEvents["startStreaming"].set()
			except:
				c.shutdown(socket.SHUT_RDWR)
				stopOnlineStreamingEvent.set()
				c.close()
				continue

			if bytes_received != "E" and bytes_received != "":

				# q_label.put(int(bytes_received))
				bytes_received_old = bytes_received
				while True:  # bytes_received != "E": # "E" means end of the action

					bytes_received = c.recv(1).decode("utf-8")  # received bytes
					c.sendall('2'.encode())
					if bytes_received == "E" or bytes_received == "":
						boardApiCallEvents["stopStreaming"].set()
						stopOnlineStreamingEvent.set()
						break
					else:
						if bytes_received != bytes_received_old:
							try:
								if int(bytes_received) == cnst.onlineUnitySentByte:
									boardApiCallEvents["startStreaming"].set()
							except:
								c.shutdown(socket.SHUT_RDWR)
								c.close()
								stopOnlineStreamingEvent.set()
								continue
							bytes_received_old = bytes_received
			c.shutdown(socket.SHUT_RDWR)
			c.close()
		except socket.error as error:
			print(error.__str__() + '. Wait for 10 seconds before trying again')
			time.sleep(10)
			pass
	socketConnection.clear()


def startTargetApp():
	"""
	Simple method, that only executes the unity target executable given in :data:`utils.constants.Constants.unityExePath`

	:param boardApiCallEvents: Events used in :py:class:`source.boardEventHandler.BoardEventHandler`

	"""
	with open(os.devnull, 'wb') as devnull:
		subprocess.check_call([cnst.onlineUnityExePath], stdout=devnull, stderr=subprocess.STDOUT)


def onlineProcessing(board, _shutdownEvent, windowedDataBuffer, predictBuffer, stopOnlineStreamingEvent):
	# load the classifier
	filename = cnst.classifierFilename
	clf = joblib.load(filename)
	chan_ind = board.getEnabledChannels()
	frames_ch = cnst.frames_ch
	lowcut = board.getLowerBoundFrequency()
	highcut = board.getHigherBoundFrequency()
	harmonics_num = cnst.harmonics_num
	fs = board.getSampleRate()
		
	while not _shutdownEvent.is_set() and not stopOnlineStreamingEvent.is_set():
		while not windowedDataBuffer.qsize() == 0 and not stopOnlineStreamingEvent.is_set():
			segment_full = np.array(windowedDataBuffer.get())

			frames_np = np.sum(np.array(frames_ch),1)   # I sum the frames along axis 1 (i.e. I sum all the elements of each row)
			stimulus_freqs = np.divide(np.full(frames_np.shape[0],60.) , frames_np)     # I divide the screen refresh rate by the frames_np for each stimulus frequency



			stimulus_freqs = 2*stimulus_freqs   #checkerboard invokes double of the stimuli freqs!!!!!!!!!!!!

			segment = segment_full[:,np.asarray(chan_ind)] # choose channels (last column = label, it doesn't apply in online mode) 


			segment_filt = butter_bandpass_filter(segment, lowcut, highcut, fs, order=10)   # filter the data
			r_segment = calculate_cca_correlations(segment_filt, fs, frames_ch, harmonics_num)  # calculate cca correlations
			command_predicted = clf.predict(r_segment)  # predict
			# print("Processing", command_buffer.qsize())

			predictBuffer.put(command_predicted)


def managePredict(_shutdownEvent, predictBuffer, stopOnlineStreamingEvent):
	while not _shutdownEvent.is_set() and not stopOnlineStreamingEvent.is_set():
		while not predictBuffer.qsize() == 0 and not stopOnlineStreamingEvent.is_set():
			dt = predictBuffer.get()
			print(dt)


def startOnline(board, startOnlineEvent, boardApiCallEvents, _shutdownEvent, windowedDataBuffer):
	"""
	* Method runs via onlineProcess in :py:mod:`source.UIManager`
	* Runs simultaneously with the boardEventHandler process and waits for the startOnlineEvent, which is set only by the boardEventHandler.
	* When the startOnlineEvent is set:

		* Starts the socketConnect process.
		* Starts the startTargetApp process.
		* Starts streaming from existing connection.
	

	:param OpenBCICyton board: Represents the OpenBCICyton class
	:param Event startOnlineEvent: Event which this process will be waiting for, before starting the connectTraining, startTrainingApp processes. This Event is set only by the :py:meth:`source.pyGUI.GUI.trainingButtonClick`
	:param [Event] boardApiCallEvents:  Events used in :py:class:`source.boardEventHandler.BoardEventHandler`
	:param Event _shutdownEvent: Event used to know when to let every running process terminate
	:param Queue trainingClassBuffer: Buffer will be used to 'give' the training class to :meth:`source.boardEventHandler.BoardEventHandler.startStreaming`, via :meth:`source.training.connectTraining`
	"""
	socketConnection = Event()
	stopOnlineStreamingEvent = Event() 
	socketConnection.clear()
	stopOnlineStreamingEvent.clear()
	predictBuffer = Queue(maxsize=100)

	socketProcess = Process(target=socketConnect, args=(boardApiCallEvents, socketConnection, stopOnlineStreamingEvent,))
	applicationProcess = Process(target=startTargetApp)
	onlineProcessingProcess = Process(target=onlineProcessing, args=(board, _shutdownEvent, windowedDataBuffer, predictBuffer, stopOnlineStreamingEvent,))
	managePredictProcess = Process(target=managePredict, args=(_shutdownEvent, predictBuffer, stopOnlineStreamingEvent,))
	while not _shutdownEvent.is_set():
		startOnlineEvent.wait(1)
		if startOnlineEvent.is_set():
			if not board.isConnected():
				printError('Could not start straining without connected Board.')
				startOnlineEvent.clear()
				continue
			if not socketProcess.is_alive():
				socketProcess.start()
			socketConnection.wait(1)
			if socketConnection.is_set():
				if not applicationProcess.is_alive():
					applicationProcess.start()
				if not onlineProcessingProcess.is_alive():
					onlineProcessingProcess.start()
				if not managePredictProcess.is_alive():
					managePredictProcess.start()
				socketProcess.join()
				applicationProcess.join()
				onlineProcessingProcess.join()
				managePredictProcess.join()
				startOnlineEvent.clear()
				socketConnection.clear()
				stopOnlineStreamingEvent.clear()
				# recreating process because eve after Process Termination cannot start a process twice
				socketProcess = Process(target=socketConnect, args=(boardApiCallEvents, socketConnection, stopOnlineStreamingEvent,))
				applicationProcess = Process(target=startTargetApp)
				onlineProcessingProcess = Process(target=onlineProcessing, args=(board, _shutdownEvent, windowedDataBuffer, predictBuffer, stopOnlineStreamingEvent,))
				managePredictProcess = Process(target=managePredict, args=(_shutdownEvent, predictBuffer, stopOnlineStreamingEvent,))