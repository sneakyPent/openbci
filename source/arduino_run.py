import socket
from time import time, sleep
from datetime import datetime
from utils.coloringPrint import printError, printHeader, printInfo, printWarning
from utils.constants import Constants as cnst


# from psychopy import event


# function for the arduino platform and the execution of the commands
def arduino(startPresentation, _shutdownEvent, command_buffer, currentClassBuffer, _streaming, emergency_arduino,
            emergency_buffer):
	commandClass = 0
	# wait until the presentation starts
	while not _shutdownEvent.is_set():
		startPresentation.wait(1)
		# -------------------------- START PRESENTATION --------------------------------------------
		# ------------------------------------------------------------------------------------------
		if startPresentation.is_set() and _streaming.is_set():
			address = (cnst.arduino_address, cnst.arduino_port)
			client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)  # set up the socket

			try:
				client_socket.settimeout(5)  # wait 1s for the response
				client_socket.connect(address)  # connect to arduino

				while startPresentation.is_set():
					if not command_buffer.empty():

						commandClass = command_buffer.get_nowait()  # get the command and translate into move
						# print("SIZE command", command_buffer.qsize())

						if not emergency_arduino.is_set():
							printWarning("EGG commands")
							# if command class found then return based on dictionary else return cnst.onlineStreamingCommands_STOP
							move = cnst.arduino_class4Switcher.get(commandClass, cnst.onlineStreamingCommands_STOP)
							# Create info message 
							msg = 'COMAND CLASS: ' + commandClass.__str__() + ', MOVE: ' + move + ' -> ' \
							      + cnst.arduino_CommandsTranslationForDebug.get(move, 'NOT AVAILABLE COMMAND')
							currentClassBuffer.put_nowait(commandClass)
							printWarning(commandClass.__str__())

						else:
							printWarning("KEYBOARD commands")
							move = emergency_buffer.get()  # get the command and translate into move
							# Create info message 
							msg = 'COMAND CLASS: ' + commandClass.__str__() + ', MOVE: ' + move + ' -> ' \
							      + cnst.arduino_CommandsTranslationForDebug.get(move, 'NOT AVAILABLE COMMAND')

						printInfo(msg)
						client_socket.sendto(move.encode(), address)  # send move to arduino/server
						sleep(0.05)  # delay before the next command

				move = "s"
				printInfo("Arduino")
				client_socket.sendto(move.encode(), address)  # send move to arduino/server
				# currentClassBuffer.put_nowait(commandClass)
				# printWarning(commandClass.__str__())

				# check if the queues are full and empty them
				while not command_buffer.empty():
					command_buffer.get_nowait()

				while not emergency_buffer.empty():
					emergency_buffer.get()

				client_socket.close()
				printInfo("Arduino close")

			except socket.error:
				printError("Error at Arduino connection!")
				# _isReading.clear()
				startPresentation.clear()
				while not command_buffer.empty():
					command_buffer.get_nowait()

				while not emergency_buffer.empty():
					emergency_buffer.get()
