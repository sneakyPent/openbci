from multiprocessing import Process


class BoardEventHandler:
 	def __init__(self, board, boardApiCallEvents, boardSettings):
		self.board = board
		self.boardApiCallEvents = boardApiCallEvents
		self.boardSettings = boardSettings

	def connect(self):
		ev = self.boardApiCallEvents.connect
		while True:
			ev.wait()
			self.board.connect()
			ev.clear()

	def disconnect(self):
		ev = self.boardApiCallEvents.disconnect
		while True:
			ev.wait()
			print("disconnect")
			self.board.disconnect()
			ev.clear()

	def startStreaming(self):
		ev = self.boardApiCallEvents.startStreaming
		while True:
			ev.wait()
			print("startStreaming")
			ev.clear()

	def stopStreaming(self):
		ev = self.boardApiCallEvents.stopStreaming
		while True:
			ev.wait()
			print("stopStreaming")
			ev.clear()

    def newBoardSettingsAvailable(self):
        ev = self.boardApiCallEvents.newBoardSettingsAvailable
        while True:
            ev.wait()
            print("newBoardSettingsAvailable")
            ev.clear()

    def start(self):
        print("Starting eventHandler")
        connectProcess = Process(target=self.connect)
        disconnectProcess = Process(target=self.disconnect)
        startStreamingProcess = Process(target=self.startStreaming)
        stopStreamingProcess = Process(target=self.stopStreaming)
        newBoardSettingsAvailableProcess = Process(target=self.newBoardSettingsAvailable)

        connectProcess.start()
        disconnectProcess.start()
        startStreamingProcess.start()
        stopStreamingProcess.start()
        newBoardSettingsAvailableProcess.start()

        connectProcess.join()
        disconnectProcess.join()
        startStreamingProcess.join()
        stopStreamingProcess.join()
        newBoardSettingsAvailableProcess.join()
