import os
import sys
from multiprocessing import Process
from utils.coloringPrint import *


class BoardEventHandler:

	def __init__(self, board, boardApiCallEvents, boardSettings, dataManagerEvents, dataBuffer):
		self.board = board
		self.boardApiCallEvents = boardApiCallEvents
		self.dataManagerEvents = dataManagerEvents
		self.boardSettings = boardSettings
		self.dataBuffer = dataBuffer

	def connect(self):
		ev = self.boardApiCallEvents.connect
		while True:
			ev.wait()
			printInfo("Connecting...")
			try:
				self.board.connect()
			except OSError:
				printError("Could not connect to board. Make sure it is properly connected and enabled")
			ev.clear()

	def disconnect(self):
		ev = self.boardApiCallEvents.disconnect
		while True:
			ev.wait()
			printInfo("Disconnecting...")
			try:
				self.board.disconnect()
			except:
				printError("No connection to disconnect from ")
			ev.clear()

	def startStreaming(self):

		ev = self.boardApiCallEvents.startStreaming
		while True:
			ev.wait()
			printInfo("Starting streaming...")
			while ev.is_set():
				try:
					sample = self.board.stream_one_sample()
					self.dataBuffer.put(sample.channel_data)
					self.dataManagerEvents.share.set()
				except Exception as e:
					ev.clear()
					exc_type, exc_obj, exc_tb = sys.exc_info()
					fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
					printError("There was a problem on starting streaming in: " + fname.__str__() +
					           ' line: ' + exc_tb.tb_lineno.__str__() + "\nError Message: " + repr(e))

	def stopStreaming(self):
		ev = self.boardApiCallEvents.stopStreaming
		while True:
			ev.wait()
			printInfo("Stopping streaming...")
			try:
				self.boardApiCallEvents.startStreaming.clear()
				self.board.stopStreaming()
			except:
				printError("There is no stream to stop")
			# self.dataManagerEvents.share.clear()
			ev.clear()

	def newBoardSettingsAvailable(self):
		ev = self.boardApiCallEvents.newBoardSettingsAvailable
		while True:
			ev.wait()
			printInfo("New board setting Available...")
			if self.boardSettings["lowerBand"] != self.board.getLowerBoundFrequency():
				self.board.setLowerBoundFrequency(self.boardSettings["lowerBand"])
			if self.boardSettings["upperBand"] != self.board.getHigherBoundFrequency():
				self.board.setHigherBoundFrequency(self.boardSettings["upperBand"])
			if self.boardSettings["windowSize"] != self.board.getWindowSize():
				self.board.setWindowSize(self.boardSettings["windowSize"])
			if self.boardSettings["filtering_data"] != self.board.isFilteringData():
				self.board.setFilteringData(self.boardSettings["filtering_data"])
			if self.boardSettings["scaling_output"] != self.board.isScalingOutput():
				self.board.setScaledOutput(self.boardSettings["scaling_output"])
			ev.clear()

	def start(self):
		procList = []
		try:
			printInfo("Starting eventHandler")
			connectProcess = Process(target=self.connect)
			disconnectProcess = Process(target=self.disconnect)
			startStreamingProcess = Process(target=self.startStreaming)
			stopStreamingProcess = Process(target=self.stopStreaming)
			newBoardSettingsAvailableProcess = Process(target=self.newBoardSettingsAvailable)

			procList.append(connectProcess)
			procList.append(disconnectProcess)
			procList.append(startStreamingProcess)
			procList.append(stopStreamingProcess)
			procList.append(newBoardSettingsAvailableProcess)

			for proc in procList:
				proc.start()

			# join processes
			for proc in procList:
				proc.join()
		except KeyboardInterrupt:
			# terminate processes
			for proc in procList:
				proc.terminate()
