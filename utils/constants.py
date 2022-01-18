import os
import time
from enum import Enum

from matplotlib import colors as mcolors
import enum

baseColors = dict(mcolors.BASE_COLORS, **mcolors.CSS4_COLORS)

class TargetPlatform(enum.Enum):
    UNITY = 0
    PSYCHOPY = 1

def getSessionFilename(training=False, openbciGUI=False, online=False, classification=False):
	if training:
		return Constants.destinationFolder + 'Training__' + time.strftime("%d-%m-%Y__%H-%M-%S")
	elif openbciGUI:
		return 'openBCI_GUI_Training__' + time.strftime("%d-%m-%Y__%H-%M-%S")
	elif online:
		return 'online' + time.strftime("%d-%m-%Y__%H-%M-%S") + '.txt'
	elif classification:
		return 'Classifier_' + time.strftime("%d-%m-%Y__%H-%M-%S")
	else:
		return Constants.destinationFolder + 'Streaming__' + time.strftime("%d-%m-%Y__%H-%M-%S")


def getDestinationFolderWithDate():
	path = '../streamData/' + time.strftime("%d-%m-%Y") + "/"
	isExist = os.path.exists(path)

	if not isExist:
		# Create a new directory because it does not exist
		os.makedirs(path)
	return path


class ElectrodeType(Enum):
	DRY = 0
	WET = 1


class FftType(Enum):
	brainflowFFT = 0
	pythonFFT = 1


class FilterType(Enum):
	butter_bandpass_filter = 0
	lowpass_highpass = 1
	brainflow_bandpass = 2


class Constants:
	"""The constants!"""

	ADS1299_GAIN_1 = 1.0
	ADS1299_GAIN_2 = 2.0
	ADS1299_GAIN_4 = 4.0
	ADS1299_GAIN_6 = 6.0
	ADS1299_GAIN_8 = 8.0
	ADS1299_GAIN_12 = 12.0
	ADS1299_GAIN_24 = 24.0

	ADS1299_VREF = 4.5  # reference voltage for ADC in ADS1299.  set by its hardware

	BOARD_CYTON = 'cyton'
	BOARD_DAISY = 'daisy'
	BOARD_GANGLION = 'ganglion'
	BOARD_NONE = 'none'

	CYTON_ACCEL_SCALE_FACTOR_GAIN = 0.002 / (pow(2, 4))  # assume set to +/4G, so 2 mG

	""" Errors """
	ERROR_INVALID_BYTE_LENGTH = 'Invalid Packet Byte Length'
	ERROR_INVALID_BYTE_START = 'Invalid Start Byte'
	ERROR_INVALID_BYTE_STOP = 'Invalid Stop Byte'
	ERROR_INVALID_DATA = 'Invalid data - try again'
	ERROR_INVALID_TYPE = 'Invalid type - check comments for input type'
	ERROR_MISSING_REGISTER_SETTING = 'Missing register setting'
	ERROR_MISSING_REQUIRED_PROPERTY = 'Missing property in JSON'
	ERROR_TIME_SYNC_IS_NULL = "'this.sync.curSyncObj' must not be null"
	ERROR_TIME_SYNC_NO_COMMA = 'Missed the time sync sent confirmation. Try sync again'
	ERROR_UNDEFINED_OR_NULL_INPUT = 'Undefined or Null Input'

	""" Possible number of channels """

	NUMBER_OF_CHANNELS_CYTON = 8
	NUMBER_OF_CHANNELS_DAISY = 16
	NUMBER_OF_CHANNELS_GANGLION = 4

	""" Protocols """
	PROTOCOL_BLE = 'ble'
	PROTOCOL_SERIAL = 'serial'
	PROTOCOL_WIFI = 'wifi'

	RAW_BYTE_START = 0xA0
	RAW_BYTE_STOP = 0xC0
	RAW_PACKET_ACCEL_NUMBER_AXIS = 3
	RAW_PACKET_SIZE = 33
	"""
	OpenBCI Raw Packet Positions
	0:[startByte] | 1:[sampleNumber] | 2:[Channel-1.1] | 3:[Channel-1.2] | 4:[Channel-1.3] | 5:[Channel-2.1] | 6:[Channel-2.2] | 7:[Channel-2.3] | 8:[Channel-3.1] | 9:[Channel-3.2] | 10:[Channel-3.3] | 11:[Channel-4.1] | 12:[Channel-4.2] | 13:[Channel-4.3] | 14:[Channel-5.1] | 15:[Channel-5.2] | 16:[Channel-5.3] | 17:[Channel-6.1] | 18:[Channel-6.2] | 19:[Channel-6.3] | 20:[Channel-7.1] | 21:[Channel-7.2] | 22:[Channel-7.3] | 23:[Channel-8.1] | 24:[Channel-8.2] | 25:[Channel-8.3] | 26:[Aux-1.1] | 27:[Aux-1.2] | 28:[Aux-2.1] | 29:[Aux-2.2] | 30:[Aux-3.1] | 31:[Aux-3.2] | 32:StopByte
	"""
	RAW_PACKET_POSITION_START_BYTE = 0
	RAW_PACKET_POSITION_SAMPLE_NUMBER = 1
	RAW_PACKET_POSITION_CHANNEL_DATA_START = 2
	RAW_PACKET_POSITION_CHANNEL_DATA_STOP = 25
	RAW_PACKET_POSITION_START_AUX = 26
	RAW_PACKET_POSITION_TIME_SYNC_AUX_START = 26
	RAW_PACKET_POSITION_TIME_SYNC_AUX_STOP = 28
	RAW_PACKET_POSITION_TIME_SYNC_TIME_START = 28
	RAW_PACKET_POSITION_STOP_AUX = 31
	RAW_PACKET_POSITION_STOP_BYTE = 32
	RAW_PACKET_POSITION_TIME_SYNC_TIME_STOP = 32

	""" Stream packet types """
	RAW_PACKET_TYPE_STANDARD_ACCEL = 0  # 0000
	RAW_PACKET_TYPE_STANDARD_RAW_AUX = 1  # 0001
	RAW_PACKET_TYPE_USER_DEFINED_TYPE = 2  # 0010
	RAW_PACKET_TYPE_ACCEL_TIME_SYNC_SET = 3  # 0011
	RAW_PACKET_TYPE_ACCEL_TIME_SYNCED = 4  # 0100
	RAW_PACKET_TYPE_RAW_AUX_TIME_SYNC_SET = 5  # 0101
	RAW_PACKET_TYPE_RAW_AUX_TIME_SYNCED = 6  # 0110
	RAW_PACKET_TYPE_IMPEDANCE = 7  # 0111

	""" Max sample number """
	SAMPLE_NUMBER_MAX_CYTON = 255
	SAMPLE_NUMBER_MAX_GANGLION = 200

	""" Possible Sample Rates """
	SAMPLE_RATE_1000 = 1000
	SAMPLE_RATE_125 = 125
	SAMPLE_RATE_12800 = 12800
	SAMPLE_RATE_1600 = 1600
	SAMPLE_RATE_16000 = 16000
	SAMPLE_RATE_200 = 200
	SAMPLE_RATE_2000 = 2000
	SAMPLE_RATE_250 = 250
	SAMPLE_RATE_25600 = 25600
	SAMPLE_RATE_3200 = 3200
	SAMPLE_RATE_400 = 400
	SAMPLE_RATE_4000 = 4000
	SAMPLE_RATE_500 = 500
	SAMPLE_RATE_6400 = 6400
	SAMPLE_RATE_800 = 800
	SAMPLE_RATE_8000 = 8000

	""" Cyton board sdk commands """
	# Stream Data Commands
	startStreamingData = b'b'
	stopStreamingData = b's'
	# Miscellaneous Commands
	softReset = b'v'
	queryRegisterSettings = b'?'

	# Test Signal Control Commands
	connectToInternalGND = b'0'
	connectingPinsToLowFrequency1xAmpSignal = b'-'
	connectToDCSignal = b'p'
	connectingPinsToHighFrequency1xAmpSignal = b'='
	connectingPinsToLowFrequency2xAmpSignal = b'['
	connectingPinsToHighFrequency2xAmpSignal = b']'

	# Turn Channels OFF
	channel_1_off = b'1'
	channel_2_off = b'2'
	channel_3_off = b'3'
	channel_4_off = b'4'
	channel_5_off = b'5'
	channel_6_off = b'6'
	channel_7_off = b'7'
	channel_8_off = b'8'
	channel_9_off = b'q'
	channel_10_off = b'w'
	channel_11_off = b'e'
	channel_12_off = b'r'
	channel_13_off = b't'
	channel_14_off = b'y'
	channel_15_off = b'u'
	channel_16_off = b'i'

	# Turn Channels OΝ
	channel_1_on = b'!'
	channel_2_on = b'@'
	channel_3_on = b'#'
	channel_4_on = b'$'
	channel_5_on = b'%'
	channel_6_on = b'^'
	channel_7_on = b'&'
	channel_8_on = b'*'
	channel_9_on = b'Q'
	channel_10_on = b'W'
	channel_11_on = b'E'
	channel_12_on = b'R'
	channel_13_on = b'T'
	channel_14_on = b'Y'
	channel_15_on = b'U'
	channel_16_on = b'I'

	""" Cyton board settings """
	bandPassFreqList = ["1-50", "3-30", "4-40", "5-50"]
	initBandPassFreqList = "4-40"
	windowSizeList = [1, 2, 3, 4, 5]
	initWindowSizeValue = 3
	windowStepSizeList = [0.5, 1, 1.5, 0.99, 0.35]
	initStepSizeValue = 0.5
	synchingSignal = [0, 0, 0, 0, 0, 0, 0, 0]
	initEnabledChannels = [0, 1, 2]
	initUsingElectrodes = ElectrodeType.DRY

	""" printng massages colors"""
	FAIL = '\033[91m'
	OKGREEN = '\033[92m'
	WARNING = '\033[93m'
	HEADER = '\033[95m'
	CYAN = '\033[96m'
	OKCYAN = '\033[96m'
	ENDC = '\033[0m'
	BOLD = '\033[1m'
	UNDERLINE = '\033[4m'

	"""Streaming File names"""

	destinationFolder = getDestinationFolderWithDate()

	""" Queue size """
	maxQueueSize = 2500
	writeDataMaxQueueSize = maxQueueSize * 100  # approximate 15 minutes of streaming

	""" GUI """
	# the order of the channels' color  is the same order as the wires' colors in the equivalent pin
	GUIChannelColors = [baseColors['red'], baseColors['orange'], baseColors['yellow'], baseColors['green'],
	                    baseColors['blue'], baseColors['purple'], baseColors['turquoise'], baseColors['orchid'],
	                    baseColors['gray'], baseColors['saddlebrown'], baseColors['papayawhip']]

	channelsList = ['channel 1', 'channel 2', 'channel 3', 'channel 4',
	                'channel 5', 'channel 6', 'channel 7', 'channel 8']

	""" Unity exe """
	trainingUnityExePath = "C:/Users/Nikolas/Desktop/training/trainingOpenbci.exe"
	# trainingUnityExePath = "/home/zn/Desktop/Diplo/unityScreens/training/trainingOpenbci.exe"
	onlineUnityExePath = "C:/Users/Nikolas/Desktop/online/onlineOpenbci.exe"
	# onlineUnityExePath = "/home/zn/Desktop/Diplo/unityScreens/online/onlineOpenbci.exe"
	onlineUnitySentByte = 8
	unknownClass = 200
	trainingClasses = [0, 1, 2, 3, 4]
	trainingClassesFrequencies = [0, 3, 3.75, 3.33, 4.28]

	""" classification """
	initClassifierFilename = "classifier_LDA.sav"
	classifiersDirectory = '../classifiers/'
	targetDuration = 7  # in seconds
	frames_ch = [[0 for j in range(2)] for i in range(4)]  # The duration (in frames) of the first checkerboard pattern
	frames_ch[0] = [10, 10]  # for frequency=3 Hz
	frames_ch[1] = [8, 8]  # for frequency=3.75 Hz
	frames_ch[2] = [9, 9]  # for frequency=3.33 Hz
	frames_ch[3] = [7, 7]  # for frequency=4.28 Hz
	harmonics_num = 2

	""" online Streaming Commands """
	# 4 target classes
	target4Class_STOP = 0
	target4Class_LEFT = 1
	target4Class_RIGHT = 2
	target4Class_BACK = 3
	target4Class_FORWARD = 4
	# 3 target classes
	target3Class_STOP = 0
	target3Class_FORWARD = 2
	target3Class_LEFT = 3
	target3Class_RIGHT = 1
	# keyBoardCommands
	keyboardKey_QUIT = 'Q'
	keyboardKey_EXIT = 'E'
	keyboardKey_STOP = 'S'
	keyboardKey_FORWARD = 'F'
	keyboardKey_BACK = 'B'
	keyboardKey_RIGHT = 'R'
	keyboardKey_LEFT = 'L'
	keyboardKeyList = [keyboardKey_QUIT, keyboardKey_EXIT, keyboardKey_STOP, keyboardKey_FORWARD, keyboardKey_BACK,
	                   keyboardKey_RIGHT, keyboardKey_LEFT]
	#  Commands
	onlineStreamingCommands_STOP = '{"c":"xy","x":0,"y":0}\r\n'
	onlineStreamingCommands_REDUCE_SPEED_1 = '{"c":"xy","x":0,"y":20}\r\n'
	onlineStreamingCommands_REDUCE_SPEED_2 = '{"c":"xy","x":0,"y":10}\r\n'
	onlineStreamingCommands_LEFT = '{"c":"xy","x":-40,"y":0}\r\n'
	onlineStreamingCommands_RIGHT = '{"c":"xy","x":40,"y":0}\r\n'
	onlineStreamingCommands_BACK = '{"c":"xy","x":0,"y":-45}\r\n'
	onlineStreamingCommands_FORWARD = '{"c":"xy","x":0,"y":45}\r\n'
	#  commands Dictionary
	class4Switcher = {
		target4Class_STOP: onlineStreamingCommands_STOP,
		target4Class_LEFT: onlineStreamingCommands_LEFT,
		target4Class_RIGHT: onlineStreamingCommands_RIGHT,
		target4Class_BACK: onlineStreamingCommands_BACK,
		target4Class_FORWARD: onlineStreamingCommands_FORWARD
	}
	class3Switcher = {
		target3Class_STOP: onlineStreamingCommands_STOP,
		target3Class_LEFT: onlineStreamingCommands_LEFT,
		target3Class_RIGHT: onlineStreamingCommands_RIGHT,
		target3Class_FORWARD: onlineStreamingCommands_FORWARD

	}
	keyBoardCommandsSwitcher = {
		keyboardKey_STOP: onlineStreamingCommands_STOP,
		keyboardKey_FORWARD: onlineStreamingCommands_FORWARD,
		keyboardKey_BACK: onlineStreamingCommands_BACK,
		keyboardKey_RIGHT: onlineStreamingCommands_RIGHT,
		keyboardKey_LEFT: onlineStreamingCommands_LEFT
	}
	commandsTranslationForDebug = {
		onlineStreamingCommands_STOP: 'STOP',
		onlineStreamingCommands_REDUCE_SPEED_1: 'REDUCE_SPEED_1',
		onlineStreamingCommands_REDUCE_SPEED_2: 'REDUCE_SPEED_2',
		onlineStreamingCommands_LEFT: 'LEFT',
		onlineStreamingCommands_RIGHT: 'RIGHT',
		onlineStreamingCommands_BACK: 'BACK',
		onlineStreamingCommands_FORWARD: 'FORWARD'
	}
	wheelchairUsbPort = 'COM4'
	# SENSORS
	sensorUsbPort = 'COM7'
	sensorLimit_FRONT = 70
	sensorLimit_SIDE = 30

	online_connection_serial = '{"c":"input","d":"usb"}\r\n'
	online_info_usb = '"input":"usb"'
	online_info_wifi = '"input":"wifi"'
	online_connection_wifi = '{"c":"input","d":"wifi"}\r\n'
	online_info = '{"c":"info"}\r\n'
	online_x = '{"c":"ping"}\r\n'
	online_speed = '{"c":"speed_s", "d":"-"}\r\n'
	online_power_off = '{"c":"power_off"}\r\n'

	""" Logging """
	padding = ' '
	loggerName = 'cytonLogger'
	logsDirectory = '../logs/'
	logFilename = logsDirectory + 'cytonBoard__' + time.strftime("%d-%m-%Y__%H-%M-%S") + '.log'
	logFileHandlerFormat = "[%(asctime)s] [%(levelname)-8s] (%(filename)s:%(lineno)s) -- %(message)s"
	logStreamHandlerFormat = "[%(levelname)-8s]  %(message)s"
	
	
	mediaPath = '../media/'
	
	""" ARDUINO """
	ip_cam = 'http://192.168.2.145:8080/video'
	# address = ("139.91.190.207", 80)# ("192.168.1.3", 80)#    #server's address
	arduino_address = "192.168.2.146"
	arduino_port = 80
	
	arduino_onlineStreamingCommands_STOP = 's'
	arduino_onlineStreamingCommands_LEFT = 'l'
	arduino_onlineStreamingCommands_RIGHT = 'r'
	arduino_onlineStreamingCommands_BACK = 'b'
	arduino_onlineStreamingCommands_FORWARD = 'f'
	
	arduino_KeyBoardCommandsSwitcher = {
		keyboardKey_STOP: onlineStreamingCommands_STOP,
		keyboardKey_FORWARD: onlineStreamingCommands_FORWARD,
		keyboardKey_BACK: onlineStreamingCommands_BACK,
		keyboardKey_RIGHT: onlineStreamingCommands_RIGHT,
		keyboardKey_LEFT: onlineStreamingCommands_LEFT
	}
	
	arduino_CommandsTranslationForDebug = {
		arduino_onlineStreamingCommands_STOP: 'STOP',
		arduino_onlineStreamingCommands_LEFT: 'LEFT',
		arduino_onlineStreamingCommands_RIGHT: 'RIGHT',
		arduino_onlineStreamingCommands_BACK: 'BACK',
		arduino_onlineStreamingCommands_FORWARD: 'FORWARD'
	}
	
	arduino_class4Switcher = {
		target4Class_STOP: arduino_onlineStreamingCommands_STOP,
		target4Class_LEFT: arduino_onlineStreamingCommands_LEFT,
		target4Class_RIGHT: arduino_onlineStreamingCommands_RIGHT,
		target4Class_BACK: arduino_onlineStreamingCommands_BACK,
		target4Class_FORWARD: arduino_onlineStreamingCommands_FORWARD
	}
	
	_keyboardKey_STOP = "keyboardKey_STOP"
	_keyboardKey_FORWARD = "keyboardKey_FORWARD"
	_keyboardKey_BACK = "keyboardKey_BACK"
	_keyboardKey_RIGHT = "keyboardKey_RIGHT"
	_keyboardKey_LEFT = "keyboardKey_LEFT"
	_keyboardKey_EXIT_PRESENTATION = "keyboardKey_EXIT_PRESENTATION"
	_keyboardKey_RETURN_EEG = "keyboardKey_RETURN_EEG"
	
	emergencyKeyboardCommands = {
		_keyboardKey_EXIT_PRESENTATION: "escape",
		_keyboardKey_STOP: "space" ,
		_keyboardKey_FORWARD: "w" ,
		_keyboardKey_BACK: "s" ,
		_keyboardKey_RIGHT: "d" ,
		_keyboardKey_LEFT: "a" ,
		_keyboardKey_RETURN_EEG: "z"
	}
	
	groundTruthKeyboardCommands = {
		_keyboardKey_STOP: "num_0" ,
		_keyboardKey_FORWARD: "up" ,
		_keyboardKey_BACK: "down" ,
		_keyboardKey_RIGHT: "right" ,
		_keyboardKey_LEFT: "left"
	}
	
	groundTruthKeyboardCommands_class4Switcher = {
		_keyboardKey_STOP: target4Class_STOP,
		_keyboardKey_FORWARD: target4Class_FORWARD,
		_keyboardKey_BACK: target4Class_BACK,
		_keyboardKey_RIGHT: target4Class_RIGHT,
		_keyboardKey_LEFT: target4Class_LEFT
	}
