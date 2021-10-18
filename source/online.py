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
import json
from time import sleep
import serial
from utils.coloringPrint import printError, printInfo, printWarning
from utils.constants import Constants as cnst, getSessionFilename
from utils.filters import *
from classification.train_processing_cca_3 import calculate_cca_correlations

forward = '{"c":"xy","x":0,"y":45}\r\n'
back = '{"c":"xy","x":0,"y":-45}\r\n'
right = '{"c":"xy","x":40,"y":0}\r\n'
left = '{"c":"xy","x":-40,"y":0}\r\n'
stop = '{"c":"xy","x":0,"y":0}\r\n'
connection_serial = '{"c":"input","d":"usb"}\r\n'
info_usb = '"input":"usb"'
info_wifi = '"input":"wifi"'
connection_wifi = '{"c":"input","d":"wifi"}\r\n'
info = '{"c":"info"}\r\n'
x = '{"c":"ping"}\r\n'
speed = '{"c":"speed_s", "d":"-"}\r\n'
power_off = '{"c":"power_off"}\r\n'


class Error(Exception):
	"""Base class for other exceptions"""
	pass


class SocketConnectionError(Error):
	"""Raised when the input value is too large"""
	pass


def socketConnect(board, boardApiCallEvents, socketConnection, startOnlineEvent, _shutdownEvent):
	"""
	* Responsible

		* to create a socket communication with the target executable.
		* to receive the training class byte from the open connection.
		* to put the receiving byte into trainingClassBuffer parameter.
		* to set the socketConnection event, only if socket connection established. When set,  the :py:meth:`source.training.startTrainingApp` process and the :py:meth:`source.boardEventHandler.BoardEventHandler.startStreaming` can be start.

	* When the connection could not be established then wait for 10 sec and then retrying.

	:param OpenBCICyton board: Represents the OpenBCICyton class
	:param [Event] boardApiCallEvents:
	:param Event socketConnection:
	:param Event startOnlineEvent:
	:param Event _shutdownEvent:

	"""
	while not _shutdownEvent.is_set():
		startOnlineEvent.wait(1)
		if startOnlineEvent.is_set():
			if not board.isConnected():
				printError('Could not start straining without connected Board.')
				startOnlineEvent.clear()
				continue
			# create socket
			s = socket.socket()
			socket.setdefaulttimeout(None)
			printInfo('socket created')
			# IP and PORT connection
			port = 8080
			while not socketConnection.is_set():
				try:
					# s.bind(('139.91.190.32', port)) #local host
					s.bind(('127.0.0.1', port))  # local host
					s.listen(30)  # listening for connection for 30 sec?
					printInfo('Socket listening ... ')
					# try:
					socketConnection.set()
					c, addr = s.accept()  # when port connected
					printWarning('Got connection from ' + addr.__str__())

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
						raise SocketConnectionError

					if bytes_received != "E" and bytes_received != "":

						# q_label.put(int(bytes_received))
						bytes_received_old = bytes_received
						while True:  # bytes_received != "E": # "E" means end of the action
							bytes_received = c.recv(1).decode("utf-8")  # received bytes
							c.sendall('2'.encode())
							if bytes_received == "E" or bytes_received == "":
								boardApiCallEvents["stopStreaming"].set()
								socketConnection.clear()
								break
							else:
								if bytes_received != bytes_received_old:
									try:
										if int(bytes_received) == cnst.onlineUnitySentByte:
											boardApiCallEvents["startStreaming"].set()
									except:
										raise SocketConnectionError
									bytes_received_old = bytes_received
					c.shutdown(socket.SHUT_RDWR)
					c.close()
					break
				except socket.error as error:
					print(error.__str__() + '. Wait for 10 seconds before trying again')
					time.sleep(10)
					pass
				except SocketConnectionError:
					printError('SocketConnection problem')
					c.shutdown(socket.SHUT_RDWR)
					socketConnection.clear()
					c.close()
			socketConnection.clear()
			startOnlineEvent.clear()


def startTargetApp(_shutdownEvent, socketConnection):
	"""
	Simple method, that only executes the unity target executable given in :data:`utils.constants.Constants.unityExePath`

	"""
	print(os.getpid())
	while not _shutdownEvent.is_set():
		socketConnection.wait(1)
		if socketConnection.is_set():
			with open(os.devnull, 'wb') as devnull:
				subprocess.check_call([cnst.onlineUnityExePath], stdout=devnull, stderr=subprocess.STDOUT)


def onlineProcessing(board, _shutdownEvent, windowedDataBuffer, predictBuffer, socketConnection):
	while not _shutdownEvent.is_set():
		socketConnection.wait(1)
		if socketConnection.is_set():
			filename = cnst.classifierFilename
			clf = joblib.load(filename)
			chan_ind = board.getEnabledChannels()
			frames_ch = cnst.frames_ch
			lowcut = board.getLowerBoundFrequency()
			highcut = board.getHigherBoundFrequency()
			harmonics_num = cnst.harmonics_num
			fs = board.getSampleRate()
			while not windowedDataBuffer.empty() and socketConnection.is_set():
				segment_full = np.array(windowedDataBuffer.get())

				# I sum the frames along axis 1 (i.e. I sum all the elements of each row)
				frames_np = np.sum(np.array(frames_ch), 1)
				# I divide the screen refresh rate by the frames_np for each stimulus frequency
				stimulus_freqs = np.divide(np.full(frames_np.shape[0], 60.), frames_np)

				stimulus_freqs = 2 * stimulus_freqs  # checkerboard invokes double of the stimuli freqs!!!!!!!!!!!!

				segment = segment_full[:, np.asarray(chan_ind)]
				# choose channels (last column = label, it doesn't apply in online mode)

				segment_filt = butter_bandpass_filter(segment, lowcut, highcut, fs, order=10)  # filter the data
				r_segment = calculate_cca_correlations(segment_filt, fs, frames_ch,
				                                       harmonics_num)  # calculate cca correlations
				command_predicted = clf.predict(r_segment)  # predict
				# print("Processing", command_buffer.qsize())

				predictBuffer.put(command_predicted)


def managePredict(_shutdownEvent, predictBuffer, socketConnection):
	target3_ = False
	while not _shutdownEvent.is_set():
		socketConnection.wait(1)
		if socketConnection.is_set():
			command = '{"c":"xy","x":0,"y":0}\r\n'
			fileName = getSessionFilename(online=True)
			try:
				# why using cancel join thread ???????????
				predictBuffer.cancel_join_thread()
				myfile = open(fileName, 'w')
				# define the number of targets to send the right commands
				if target3_:
					mode = 5
				else:
					mode = 6

				cmd_old = 0
				while not _shutdownEvent.is_set() and socketConnection.is_set():
					if not predictBuffer.empty():
						data = predictBuffer.get_nowait()  # get the command and translate into move
						# sut the "stop" between commands
						if not cmd_old == 0 and data == 0:
							temp = data
							data = cmd_old
							cmd_old = temp
						else:
							cmd_old = data

						if data == 0:

							if command == '{"c":"xy","x":0,"y":45}\r\n':  # if previous_command == forward
								print("I reduce once my speed")
								temp_command = '{"c":"xy","x":0,"y":20}\r\n'  # reduce the speed
								myfile.write("I reduce once my speed" + '\n')
								command = temp_command

							elif command == '{"c":"xy","x":0,"y":20}\r\n':
								print("I reduce twice my speed")
								temp_command = '{"c":"xy","x":0,"y":10}\r\n'  # reduce the speed
								myfile.write("I reduce twice my speed" + '\n')
								command = temp_command
							else:
								print("Stop: " + stop)
								myfile.write("Stop: " + stop)
								command = stop

							sleep(0.08)  # delay before the next command
						elif data == 1:
							# ......if interface is a square.........
							print("Left: " + left)
							myfile.write("Left: " + left)
							# print("left")
							command = left
						elif data == 2:
							if mode == 6:
								# ......if interface is a cross or a square.........
								print("Right: " + right)
								myfile.write("Right: " + right)
								# print("right")
								command = right
							else:
								print("Forward: " + forward)
								myfile.write("Forward: " + forward)
								# print("back")
								command = forward
						elif data == 3:
							if mode == 6:
								# ......if interface is a square.........
								print("Back: " + back)
								myfile.write("Back: " + back)
								# print("back")
								command = back
							else:
								print("Left: " + left)
								myfile.write("Left: " + left)
								# print("left")
								command = left
						elif data == 4:
							if mode == 6:
								#  ...... if interface is a square ......
								print("Forward: " + forward)
								myfile.write("Forward: " + forward)
								command = forward
							else:
								print("Right: " + right)
								myfile.write("Right: " + right)
								command = right
						else:
							print("Stop: " + stop)
							myfile.write("Stop: " + stop)
							command = stop

							sleep(0.08)  # delay before the next command

				print("Stop: " + stop)
				myfile.write("Stop: " + stop)
				while not predictBuffer.empty():
					predictBuffer.get_nowait()
				print("End wheel")
				myfile.write("End wheel")
				myfile.close()
			except serial.SerialException:
				print("Problem connecting to serial device.")
				while not predictBuffer.empty():
					predictBuffer.get_nowait()
				myfile.close()
			while not predictBuffer.qsize() == 0:
				dt = predictBuffer.get()[0]
				print(int(dt).__str__())


def wheel_serial(_shutdownEvent, socketConnection, command_buffer, usb_port_, emergency_arduino,
                 target3_=False):
	# wait = 0
	# while socketConnection.is_set():
	# 	wait = 1
	while not _shutdownEvent.is_set():
		socketConnection.wait(1)
		if socketConnection.is_set():
			debugMode = 0
			command = '{"c":"xy","x":0,"y":0}\r\n'
			fileName = getSessionFilename(online=True)
			try:
				ser = serial.Serial(port=usb_port_, baudrate=115200, parity=serial.PARITY_NONE,
				                    stopbits=serial.STOPBITS_ONE,
				                    bytesize=serial.EIGHTBITS)
				command_buffer.cancel_join_thread()
				ser.write(connection_serial.encode())  # connect to port
				ser.readline().decode()

				ser.write(info.encode())
				info_list = ser.readline().decode().split(",", 6)
				myfile = open(fileName, 'w')
				print(info_list)

				# define the number of targets to send the right commands
				if target3_:
					mode = 5
				else:
					mode = 6

				cmd_old = 0
				while not _shutdownEvent.is_set() and socketConnection.is_set():
					if not command_buffer.empty():
						data = command_buffer.get_nowait()  # get the command and translate into move

						if ser.isOpen():
							# if not emergency_arduino.is_set():
							if True:
								if not cmd_old == 0 and data == 0:  # sut the "stop" between commands
									temp = data
									data = cmd_old
									cmd_old = temp
								else:
									cmd_old = data

								if data == 0:

									if command == '{"c":"xy","x":0,"y":45}\r\n':  # if previous_command == forward
										print("I reduce once my speed")
										temp_command = '{"c":"xy","x":0,"y":20}\r\n'  # reduce the speed
										if debugMode == 1:
											myfile.write("I reduce once my speed" + '\n')
										elif debugMode == 0:
											ser.write(temp_command.encode())  # stop
										command = temp_command

									elif command == '{"c":"xy","x":0,"y":20}\r\n':
										print("I reduce twice my speed")
										temp_command = '{"c":"xy","x":0,"y":10}\r\n'  # reduce the speed
										if debugMode == 1:
											myfile.write("I reduce twice my speed" + '\n')
										elif debugMode == 0:
											ser.write(temp_command.encode())  # stop
										command = temp_command
									else:
										if debugMode == 1:
											print("Stop: " + stop)
											myfile.write("Stop: " + stop)
										elif debugMode == 0:
											ser.write(stop.encode())  # stop
										command = stop

									sleep(0.08)  # delay before the next command
								elif data == 1:
									# ......if interface is a square.........
									if debugMode == 1:
										print("Left: " + left)
										myfile.write("Left: " + left)
									elif debugMode == 0:
										ser.write(left.encode())  # left
									# print("left")
									command = left
								elif data == 2:
									if mode == 6:
										# ......if interface is a cross or a square.........
										if debugMode == 1:
											print("Right: " + right)
											myfile.write("Right: " + right)
										elif debugMode == 0:
											ser.write(right.encode())  # right
										# print("right")
										command = right
									else:
										if debugMode == 1:
											print("Forward: " + forward)
											myfile.write("Forward: " + forward)
										elif debugMode == 0:
											ser.write(forward.encode())  # back
										# print("back")
										command = forward
								elif data == 3:
									if mode == 6:
										# ......if interface is a square.........
										if debugMode == 1:
											print("Back: " + back)
											myfile.write("Back: " + back)
										elif debugMode == 0:
											ser.write(back.encode())  # back
										# print("back")
										command = back
									else:
										if debugMode == 1:
											print("Left: " + left)
											myfile.write("Left: " + left)
										elif debugMode == 0:
											ser.write(left.encode())  # left
										# print("left")
										command = left
								elif data == 4:
									if mode == 6:
										#  ...... if interface is a square ......
										if debugMode == 1:
											print("Forward: " + forward)
											myfile.write("Forward: " + forward)
										elif debugMode == 0:
											ser.write(forward.encode())  # forward
										command = forward
									else:
										if debugMode == 1:
											print("Right: " + right)
											myfile.write("Right: " + right)
										elif debugMode == 0:
											ser.write(right.encode())  # right
										command = right
								else:
									if debugMode == 1:
										print("Stop: " + stop)
										myfile.write("Stop: " + stop)
									elif debugMode == 0:
										ser.write(stop.encode())  # stop
									command = stop

									sleep(0.08)  # delay before the next command
					# else:
					#     print("keyboard")
					#     if not emergency_buffer.empty():
					#         data = emergency_buffer.get()
					#         if data == 55:
					#             ser.write(stop.encode())
					#             command = '{"c":"xy","x":0,"y":0}\r\n'

					#         elif data == 1:
					#             ser.write(forward.encode())
					#             command = '{"c":"xy","x":0,"y":45}\r\n'

					#         elif data == 2:
					#             ser.write(right.encode())
					#             command = '{"c":"xy","x":40,"y":0}\r\n'

					#         elif data == 3:
					#             ser.write(back.encode())
					#             command = '{"c":"xy","x":0,"y":-45}\r\n'

					#         elif data == 4:
					#             ser.write(left.encode())
					#             command = '{"c":"xy","x":-40,"y":0}\r\n'

					#         sleep(0.08)
					#     else:
					#         ser.write(command.encode())
					#         sleep(0.08)
					#         ser.write(info.encode())
					#         info_list = ser.readline().decode().split(",",6)

					else:
						if debugMode == 1:
							# myfile.write("command: " + command + '\n')
							pass
						elif debugMode == 0:
							ser.write(command.encode())
						sleep(0.08)
				if debugMode == 1:
					print("Stop: " + stop)
					myfile.write("Stop: " + stop)
				elif debugMode == 0:
					ser.write(stop.encode())
				while not command_buffer.empty():
					command_buffer.get_nowait()

				print("End wheel")
				myfile.close()
			except serial.SerialException:
				print("Problem connecting to serial device.")
				while not command_buffer.empty():
					command_buffer.get_nowait()
				myfile.close()


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
	:param Queue windowedDataBuffer: Buffer will be used to 'give' the training class to :meth:`source.boardEventHandler.BoardEventHandler.startStreaming`, via :meth:`source.training.connectTraining`
	"""
	procList = []
	socketConnection = Event()
	socketConnection.clear()
	predictBuffer = Queue(maxsize=100)

	# Create the process needed
	socketProcess = Process(target=socketConnect,
	                        args=(board, boardApiCallEvents, socketConnection, startOnlineEvent, _shutdownEvent,))
	applicationProcess = Process(target=startTargetApp, args=(_shutdownEvent, socketConnection,))
	onlineProcessingProcess = Process(target=onlineProcessing,
	                                  args=(board, _shutdownEvent, windowedDataBuffer,
	                                        predictBuffer, socketConnection,))
	managePredictProcess = Process(target=managePredict,
	                               args=(_shutdownEvent, predictBuffer, socketConnection,))
	wheelProcess = Process(target=wheel_serial,
	                       args=(_shutdownEvent, socketConnection, predictBuffer, 'COM4', None, None))

	procList.append(socketProcess)
	procList.append(applicationProcess)
	procList.append(onlineProcessingProcess)
	procList.append(managePredictProcess)
	# procList.append(wheelProcess)

	for proc in procList:
		proc.start()

	# join processes
	for proc in procList:
		proc.join()
