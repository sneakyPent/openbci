import os
import sys
from multiprocessing import Process, Event
from utils.coloringPrint import *


class BoardEventHandler:

	def __init__(self, board, boardSettings, dataManagerEvents, dataBuffer):
		self.board = board
		self.dataManagerEvents = dataManagerEvents
		self.boardSettings = boardSettings
		# The data buffer queue used to put streaming data
		self.dataBuffer = dataBuffer
		self.connected = Event()

		# events used to start and stop the BoardEventHandler functions
		self.connectEvent = Event()
		self.disconnectEvent = Event()
		self.startStreamingEvent = Event()
		self.stopStreamingEvent = Event()
		self.newBoardSettingsAvailableEvent = Event()

	""" 
				Action Functions
	"""

	def connect(self):
		while True:
			self.connectEvent.wait()
			if not self.connected.is_set():
				printInfo("Connecting...")
				try:
					self.board.connect()
					self.connected.set()
				except OSError:
					printError("Could not connect to board. Make sure it is properly connected and enabled")
			else:
				printInfo("Already have a connection!")
			self.connectEvent.clear()

	def disconnect(self):
		while True:
			self.disconnectEvent.wait()
			if self.connected.is_set():
				printInfo("Disconnecting...")
				try:
					self.board.disconnect()
					self.connected.clear()
				except:
					printError("No connection to disconnect from ")
			else:
				printInfo("No connection to disconnect from")
			self.disconnectEvent.clear()

	def startStreaming(self):
		while True:
			self.startStreamingEvent.wait()
			if self.connected.is_set():
				printInfo("Starting streaming...")
				while self.startStreamingEvent.is_set():
					try:
						sample = self.board.stream_one_sample()
						self.dataBuffer.put(sample.channel_data)
						self.dataManagerEvents.share.set()
					except Exception as e:
						self.startStreamingEvent.clear()
						exc_type, exc_obj, exc_tb = sys.exc_info()
						fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
						printError("There was a problem on starting streaming in: " + fname.__str__() +
						           ' line: ' + exc_tb.tb_lineno.__str__() + "\nError Message: " + repr(e))
			else:
				if not self.connected.is_set():
					printInfo("No connection to stop streaming from.")
			self.startStreamingEvent.clear()

	def stopStreaming(self):
		while True:
			self.stopStreamingEvent.wait()
			if self.connected.is_set() and self.startStreamingEvent.is_set():
				printInfo("Stopping streaming...")
				try:
					self.startStreamingEvent.clear()
					self.board.stopStreaming()
				except:
					printError("There is no stream to stop.")
			else:
				if not self.connected.is_set():
					printInfo("No connection to stop streaming from.")
				elif not self.startStreamingEvent.is_set():
					printInfo("No active streaming to stop.")

			self.stopStreamingEvent.clear()

	def newBoardSettingsAvailable(self):
		while True:
			self.newBoardSettingsAvailableEvent.wait()
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
			self.newBoardSettingsAvailableEvent.clear()

	"""     Assistive functions     """

	def getBoardHandlerEvents(self):
		"""
		Returns the events used to start and stop the BoardEventHandler functions in dictionary format

		"""
		return {
			"connect": self.connectEvent,
			"disconnect": self.disconnectEvent,
			"startStreaming": self.startStreamingEvent,
			"stopStreaming": self.stopStreamingEvent,
			"newBoardSettingsAvailable": self.newBoardSettingsAvailableEvent
		}

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
