import sys
from PyQt5.QtGui import QFont
from PyQt5.QtWidgets import *
from checkComboBox import *

sys.path.append('..')
from utils.constants import Constants as cnst

colors = 'rgbycmwr'


class GUI(QMainWindow):
	def __init__(self, dataDict, newDataAvailableEvent, board, boardApiCallEvents, boardCytonSettings, _shutdownEvent,
	             writeDataEvent):
		super().__init__()

		self.dataDict = dataDict
		self.newDataAvailableEvent = newDataAvailableEvent
		self.board = board
		self.boardApiCallEvents = boardApiCallEvents
		self.shutdownEvent = _shutdownEvent
		self.writeDataEvent = writeDataEvent
		self.boardCytonSettings = boardCytonSettings
		self.graphData = []

		# QMainWindow settings
		self.setWindowTitle("My GUI for Cyton Board")
		self.font = QFont('sanserif', 13)

		# create main widget will be used as CentralWidget in QMainWindow
		mainWidget = QWidget(parent=self)

		# add a menu bar
		self.menubar = self.menuBar()
		# add horizontal layout for the settings of the cyton board
		self.mainLayout = QGridLayout(mainWidget)
		self.boardSettingLayout = QHBoxLayout()
		self.mainLayout.addLayout(self.boardSettingLayout, 0, 0)
		# add a layout for the graphs
		self.graphLayout = QVBoxLayout()
		self.mainLayout.addLayout(self.graphLayout, 1, 0, 2, 5)

		# enable not stretching layouts on the vertical axis
		self.mainLayout.setRowStretch(self.mainLayout.rowCount(), 1)

		# init settings bar and menu bar
		self.initBoardSettingsBar()
		self.initMenuBar()

		# send board settings with current init choices
		self.freqComboClick(self.freqComboChoices.currentText())
		self.windowComboClick(self.timeWindowComboChoices.currentText())
		self.filteringDataFunction(self.filterDataCheckbox.checkState())
		self.scalingDataFunction(self.scalingDataCheckbox.checkState())
		# set central widget
		self.setCentralWidget(mainWidget)

	def initMenuBar(self):
		self.menubar.setFont(self.font)
		# Menu Bar options
		startStreamAction = QAction('&Start streaming', self)
		stopStreamAction = QAction('Sto&p streaming', self)
		connectAction = QAction('&Connect', self)
		disconnectAction = QAction('&Disconnect', self)
		quitting = QAction('&QUIT', self)

		graphs = self.menubar.addMenu('&Add Graphs')
		timeSeriesPlotAction = QAction('Time series', self)
		fftPlotAction = QAction('FFT', self)
		linearPlotAction = QAction('Linear', self)
		graphs.addActions([timeSeriesPlotAction, fftPlotAction, linearPlotAction])
		self.menubar.addActions(
			[startStreamAction, stopStreamAction, connectAction, disconnectAction, quitting])
		"""
				-MENU BAR ACTIONS FOR EACH OPTION 

		Adding every action in thread so as the GUI not freezing,
		when waiting each process to finished. In order to do this 
		we create a worker object, pass the function as argument,
		and then add the worker object to QThreadPool of GUI-QMainWindow
		object. Lastly pass this action in connect as lambda expression

		"""

		startStreamAction.triggered.connect(self.startStreaming)
		stopStreamAction.triggered.connect(self.stopStreaming)
		connectAction.triggered.connect(self.connectBoard)
		disconnectAction.triggered.connect(self.disconnectBoard)
		quitting.triggered.connect(self.quitGUI)

		# timeSeriesPlotAction.triggered.connect(self.addTimeSeriesPlot)
		# fftPlotAction.triggered.connect(self.addFFTPlot)
		# linearPlotAction.triggered.connect(self.addLinearPlot)

		self.resize(1500, 800)

	def initBoardSettingsBar(self):
		boardSettingsSpacing = 30
		# create a combo menu for the frequencies bands
		freqCombo = QHBoxLayout()
		freqComboTitle = QLabel('Band pass frequencies:')
		self.freqComboChoices = QComboBox()
		freqComboTitle.setFont(self.font)
		self.freqComboChoices.setFont(self.font)
		self.freqComboChoices.setToolTip('Select the Frequencies where data will be filtered.')
		self.freqComboChoices.addItems(cnst.bandPassFreqList)
		freqCombo.addWidget(freqComboTitle)
		freqCombo.addWidget(self.freqComboChoices)
		self.freqComboChoices.activated[str].connect(self.freqComboClick)

		# add frequency combo to boardSettingLayout
		self.boardSettingLayout.addLayout(freqCombo)
		self.boardSettingLayout.addSpacing(boardSettingsSpacing)

		# create a combo menu for the timeWindow choices
		timeWindowCombo = QHBoxLayout()
		timeWindowComboTitle = QLabel('Window size:')
		self.timeWindowComboChoices = QComboBox()
		timeWindowComboTitle.setFont(self.font)
		self.timeWindowComboChoices.setFont(self.font)
		self.timeWindowComboChoices.setEditable(True)
		self.timeWindowComboChoices.addItems(cnst.windowSizeList)
		timeWindowCombo.addWidget(timeWindowComboTitle)
		timeWindowCombo.addWidget(self.timeWindowComboChoices)
		self.timeWindowComboChoices.activated[str].connect(self.windowComboClick)

		# add timeWindow combo to boardSettingLayout
		self.boardSettingLayout.addLayout(timeWindowCombo)
		self.boardSettingLayout.addSpacing(boardSettingsSpacing)

		# add checkbox for enabling filtering Data
		self.filterDataCheckbox = QCheckBox("Filter Data")
		self.filterDataCheckbox.setChecked(True)
		self.filterDataCheckbox.setFont(self.font)
		self.filterDataCheckbox.stateChanged.connect(self.filteringDataFunction)
		self.boardSettingLayout.addWidget(self.filterDataCheckbox)
		self.boardSettingLayout.addSpacing(boardSettingsSpacing)

		# add checkbox for enabling scaling Data
		self.scalingDataCheckbox = QCheckBox("Scaling Data")
		self.scalingDataCheckbox.setChecked(True)
		self.scalingDataCheckbox.setFont(self.font)
		self.scalingDataCheckbox.stateChanged.connect(self.scalingDataFunction)
		self.boardSettingLayout.addWidget(self.scalingDataCheckbox)
		self.boardSettingLayout.addSpacing(boardSettingsSpacing)

		# add a push button to send query for RegisteSettings
		self.infoButton = QPushButton("Board info")
		self.infoButton.setFont(self.font)
		self.infoButton.clicked.connect(self.infoButtonClick)
		self.boardSettingLayout.addWidget(self.infoButton)
		self.boardSettingLayout.addSpacing(boardSettingsSpacing)

		# channelsList = ['channel 1', 'channel 2', 'channel 3', 'channel 4', 'channel 5', 'channel 6', 'channel 7',
		#            'channel 8']
		# channelsCombo = CheckComboBox(placeholderText='Enable Channels')
		# model = channelsCombo.model()
		# for i in range(len(channelsList)):
		#     channelsCombo.addItem(channelsList[i])
		#     model.item(i).setCheckable(True)
		#
		# channelsCombo.setFont(self.font)
		# channelsCombo.activated[str].connect(lambda: channelsComboChange("doklimi"))
		# self.boardSettingLayout.addWidget(channelsCombo)
		# self.boardSettingLayout.addSpacing(boardSettingsSpacing)

		self.boardSettingLayout.addStretch()

	def startStreaming(self):
		self.boardApiCallEvents.startStreaming.set()

	def stopStreaming(self):
		self.writeDataEvent.set()
		self.boardApiCallEvents.stopStreaming.set()

	def connectBoard(self):
		self.boardApiCallEvents.connect.set()

	def disconnectBoard(self):
		self.boardApiCallEvents.disconnect.set()

	def quitGUI(self):
		while self.writeDataEvent.is_set():
			pass
		self.shutdownEvent.set()
		QApplication.instance().quit()

	#  calling functions

	def channelsComboChange(self, choices):
		print("test")
		print(choices)

    def infoButtonClick(self, btn):
        self.board.setHigherBoundFrequency(200)
        print(self.board.getBoardType())
        # changing the text of label after button get clicked

	def freqComboClick(self, freq):
		try:
			lowerBound = int(freq.split("-")[0])
			upperBound = int(freq.split("-")[1])
			self.boardCytonSettings["lowerBand"] = lowerBound
			self.boardCytonSettings["upperBand"] = upperBound
			self.boardApiCallEvents.newBoardSettingsAvailable.set()
		except Exception:
			print("freqComboClick ERROR!")

	def windowComboClick(self, size):
		try:
			self.boardCytonSettings["windowSize"] = int(size)
			self.boardApiCallEvents.newBoardSettingsAvailable.set()
		except Exception:
			print("windowComboClick ERROR!")

	def filteringDataFunction(self, state):
		try:
			if state == Qt.Checked:
				self.boardCytonSettings["filtering_data"] = True
			else:
				self.boardCytonSettings["filtering_data"] = False
			self.boardApiCallEvents.newBoardSettingsAvailable.set()
		except Exception:
			print("filteringDataFunction ERROR!")

	def scalingDataFunction(self, state):
		try:
			if state == Qt.Checked:
				self.boardCytonSettings["scaling_output"] = True
			else:
				self.boardCytonSettings["scaling_output"] = False
			self.boardApiCallEvents.newBoardSettingsAvailable.set()
		except Exception:
			print("scalingDataFunction ERROR!")



def startGUI(dataDict, newDataAvailableEvent, board, boardApiCallEvents, boardCytonSettings, _shutdownEvent,
             writeDataEvent):
	app = QApplication(sys.argv)
	gui = GUI(dataDict, newDataAvailableEvent, board, boardApiCallEvents, boardCytonSettings, _shutdownEvent,
	          writeDataEvent)
	gui.show()
	sys.exit(app.exec_())


if __name__ == "__main__":
	startGUI(None, None, None, None)
