import socket 
from time import time, sleep
from datetime import datetime
from utils.coloringPrint import printError, printHeader, printInfo, printWarning
from utils.constants import Constants as cnst
# from psychopy import event


# function for the arduino platform and the execution of the commands
def arduino(startPresentation, _shutdownEvent, command_buffer, _isReading, _streaming, emergency_arduino, emergency_buffer):
	data = 0
	# wait until the presentation starts
	while not startPresentation.is_set():
		startPresentation.wait(1)
		# -------------------------- START PRESENTATION --------------------------------------------
		# ------------------------------------------------------------------------------------------
	if startPresentation.is_set():
		# address = ("139.91.190.207", 80)# ("192.168.1.3", 80)#    #server's address
		address = (cnst.arduino_address, cnst.arduino_port)
		client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)    # set up the socket
	
		try:
			client_socket.settimeout(5)    # wait 1s for the response
			client_socket.connect(address)  # connect to arduino
				
			# command_buffer.cancel_join_thread()
			emergency_buffer.cancel_join_thread()
	
		   
			while startPresentation.is_set():
				# if not command_buffer.empty():
	
					# data = command_buffer.get_nowait() # get the command and translate into move
					# print("SIZE command", command_buffer.qsize())
	
				if not emergency_arduino.is_set():
					print("EGG commands")
					if data == 0:
						move = "s" # stop
						# print("stop")
					elif data == 4:
						move = "f"  # forward
						# print("forward")
					elif data == 2:
						move = "r"  # right
						# print("right")
					elif data == 3:
						move = "b"  # back
						# print("back")
					elif data == 1:
						move = "l"  # left
						# print("left")
					
					else:
						move = "s"  # stop
				else:
					printWarning("KEYBOARD commands")
					move = emergency_buffer.get() # get the command and translate into move

				printHeader("MOVE" + move)    
				client_socket.sendto(move.encode(),address) #send move to arduino/server
						
				sleep(0.05) # delay before the next command
						
					
			move = "s"
			printInfo("Arduino")
			client_socket.sendto(move.encode(),address) # send move to arduino/server
	
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
					
				