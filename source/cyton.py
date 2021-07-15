"""
Core OpenBCI object for handling connections and samples from the board.

EXAMPLE USE:

def handle_sample(sample):
  print(sample.channel_data)

board = OpenBCIBoard()
board.print_register_settings()
board.start_streaming(handle_sample)

NOTE: If daisy modules is enabled, the callback will occur every two samples, hence "packet_id"
 will only contain even numbers. As a side effect, the sampling rate will be divided by 2.

FIXME: at the moment we can just force daisy mode, do not check that the module is detected.
TODO: enable impedance

"""

from __future__ import print_function
import os
import serial
import struct
import numpy as np
import time
import timeit
import atexit
import logging
import threading
import glob
import sys

from utils import filters
from utils.coloringPrint import *

sys.path.append('..')
from utils.constants import Constants as cnts

scale_fac_uVolts_per_count = cnts.ADS1299_VREF / \
                             float((pow(2, 23) - 1)) / cnts.ADS1299_GAIN_24 * 1000000.
scale_fac_accel_G_per_count = 0.002 / \
                              (pow(2, 4))  # assume set to +/4G, so 2 mG
'''
#Commands for in SDK http://docs.openbci.com/software/01-Open BCI_SDK:

command_stop = "s";
command_startText = "x";
command_startBinary = "b";
command_startBinary_wAux = "n";
command_startBinary_4chan = "v";
command_deactivate_channel = {"1", "2", "3", "4", "5", "6", "7", "8"};
command_activate_channel = {"q", "w", "e", "r", "t", "y", "u", "i"};
command_activate_leadoffP_channel = {"!", "@", "#", "$", "%", "^", "&", "*"};  //shift + 1-8
command_deactivate_leadoffP_channel = {"Q", "W", "E", "R", "T", "Y", "U", "I"};   //letters (plus shift) right below 1-8
command_activate_leadoffN_channel = {"A", "S", "D", "F", "G", "H", "J", "K"}; //letters (plus shift) below the letters below 1-8
command_deactivate_leadoffN_channel = {"Z", "X", "C", "V", "B", "N", "M", "<"};   //letters (plus shift) below the letters below the letters below 1-8
command_biasAuto = "`";
command_biasFixed = "~";
'''


class OpenBCICyton(object):
	"""
	Handle a connection to an OpenBCI board.

	Args:
	  :port: The port to connect to.
	  :baud: The baud of the serial connection.
	  :filter_data: {Boolean} enable or disable filtering data between the given frequencies
	  :scaled_output: {Boolean} enable or disable scaling reading data with the given scaling factor
	  :daisy: {Boolean}  Enable or disable daisy module and 16 chans readings
	  :aux, impedance: unused, for compatibility with ganglion API
	  :log: {Boolean}
	  :timeout: the timeout for the serial connection to board receiver

	"""

	def __init__(self, port=None, baud=115200, filter_data=True, scaled_output=True,
	             daisy=False, aux=False, impedance=False, log=True, timeout=None,
	             lowerBoundFrequency=None, higherBoundFrequency=100, enabledChannels=None, windowSize=None):
		self.baudrate = baud
		self.timeout = timeout
		self.log = log  # print_incoming_text needs log
		self.streaming = False
		# if not port:
		#     port = self.find_port()
		self.port = port
		self.filtering_data = filter_data
		self.scaling_output = scaled_output
		self.daisy = daisy
		self.aux = aux
		self.lowerBoundFrequency = lowerBoundFrequency
		self.higherBoundFrequency = higherBoundFrequency
		self.windowSize = windowSize
		if enabledChannels is None:
			enabledChannels = []
		self.enabledChannels = enabledChannels

		self.streaming = False

		# number of channels per sample *from the board*
		if self.daisy:
			self.board_type = cnts.BOARD_DAISY
			self.number_of_channels = cnts.NUMBER_OF_CHANNELS_DAISY
			self.last_odd_sample = OpenBCISample(-1, [], [])  # used for daisy
			self.sample_rate = cnts.SAMPLE_RATE_125
		else:
			self.board_type = cnts.BOARD_CYTON
			self.number_of_channels = cnts.NUMBER_OF_CHANNELS_CYTON
			self.sample_rate = cnts.SAMPLE_RATE_250

		# number of AUX channels per sample *from the board*
		self.aux_channels_per_sample = cnts.RAW_PACKET_ACCEL_NUMBER_AXIS
		self.imp_channels_per_sample = 0  # impedance check not supported at the moment

		# TODO: if not needed delete them
		self.read_state = 0
		self.log_packet_count = 0
		self.attempt_reconnect = False
		self.last_reconnect = 0
		self.reconnect_freq = 5
		self.packets_dropped = 0

		# Disconnects from board when terminated
		atexit.register(self.disconnect)

	# SET BOARD VARIABLES FUNCTIONS
	def setLowerBoundFrequency(self, freq):
		self.lowerBoundFrequency = freq

	def setHigherBoundFrequency(self, freq):
		self.higherBoundFrequency = freq

	def setWindowSize(self, size):
		self.windowSize = size

	def setEnabledChannels(self, channelsList):
		"""
			Enable channels
			- values must be in the range of the board type available channels
					daisy = 1-16
					cyton = 1-8

			:param channelsList {list} List of the channels want to enable.
				EX. ch = [5,6,7,8] enables the channels 5-8 and disables 1-4


		"""
		self.enabledChannels = []
		for channel in channelsList:
			if 0 < channel < self.number_of_channels:
				self.set_channel(channel, 1)
				self.number_of_channels.append(channel)
			#           TODO: remove that after check
			else:
				print("Not available channel")

	def setFilteringData(self, enable):
		self.filtering_data = enable

	def setScaledOutput(self, enable):
		self.scaling_output = enable

	def setImpedance(self, flag):
		""" Enable/disable impedance measure. Not implemented at the moment on Cyton. """
		return

	# GET BOARD VARIABLES FUNCTIONS

	def getBoardType(self):
		""" Returns the version of the board """
		return self.board_type

	def getLowerBoundFrequency(self):
		return self.lowerBoundFrequency

	def getHigherBoundFrequency(self):
		return self.higherBoundFrequency

	def getWindowSize(self):
		return self.windowSize

	def getEnabledChannels(self):
		return self.enabledChannels

	def isFilteringData(self):
		return self.filtering_data

	def isScalingOutput(self):
		return self.scaling_output

	def getSampleRate(self):
		return self.sample_rate

	def getAvailableNbChannels(self):
		return self.number_of_channels

	def getAvailableNbAUXChannels(self):
		return self.aux_channels_per_sample

	def getAvailableNbImpChannels(self):
		return self.imp_channels_per_sample

	# SERIAL PORT FUNCTIONS
	def ser_write(self, b):
		"""Access serial port object for write"""
		self.ser.write(b)

	def ser_read(self):
		"""Access serial port object for read"""
		return self.ser.read()

	def ser_inWaiting(self):
		"""Access serial port object for inWaiting"""
		return self.ser.inWaiting()

	# API CALLS
	def connect(self):
		if not self.port:
			printInfo("Searching for connection port...")
			self.port = self.find_port()

		printInfo("Connecting to V3 at port %s" % self.port)
		if self.port == "loop://":
			# For testing purposes
			self.ser = serial.serial_for_url(self.port, baudrate=self.baudrate, timeout=self.timeout)
		else:
			self.ser = serial.Serial(port=self.port, baudrate=self.baudrate, timeout=self.timeout)

		printSuccess("Serial established...")

		time.sleep(2)
		# Initialize 32-bit board, doesn't affect 8bit board
		self.ser.write(cnts.softReset)

		# wait for device to be ready
		time.sleep(1)
		if self.port != "loop://":
			self.print_incoming_text()

	def disconnect(self):
		if self.streaming:
			self.stopStreaming()
		if self.ser.isOpen():
			print("Closing Serial...")
			self.ser.close()
			logging.warning('serial closed')

	def stream_one_sample(self):
		"""
				This method read one sample per calling and return it to parent method

		"""
		if not self.streaming:
			self.ser.write(cnts.startStreamingData)
			self.streaming = True

		# Initialize check connection
		# TODO: check_connection creates a lot of threads and crashes system
		#   check what's it doing and replace functionality
		# self.check_connection()

		# read current sample
		sample = self._read_sample()
		# if a daisy module is attached, wait to concatenate two samples
		# (main board + daisy) before passing it to callback
		if self.board_type == cnts.BOARD_DAISY:
			# odd sample: daisy sample, save for later
			if ~sample.id % 2:
				self.last_odd_sample = sample
			# even sample: concatenate and send if last sample was the fist part,
			#  otherwise drop the packet
			elif sample.id - 1 == self.last_odd_sample.id:
				# the aux data will be the average between the two samples, as the channel
				#  samples themselves have been averaged by the board
				avg_aux_data = list(
					(np.array(sample.aux_data) + np.array(self.last_odd_sample.aux_data)) / 2)
				whole_sample = OpenBCISample(sample.id,
				                             sample.channel_data +
				                             self.last_odd_sample.channel_data,
				                             avg_aux_data)
				return whole_sample
		else:
			return sample

	def start_streaming(self, callback, lapse=-1):
		"""
		Start handling streaming data from the board. Call a provided callback
		for every single sample that is processed (every two samples with daisy module).

		Args:
		  callback: A callback function, or a list of functions, that will receive a single
		   argument of the OpenBCISample object captured.
		"""
		try:
			if not self.streaming:
				self.ser.write(cnts.startStreamingData)
				self.streaming = True

			start_time = timeit.default_timer()

			# Enclose callback function in a list if it comes alone
			if not isinstance(callback, list):
				callback = [callback]

			# Initialize check connection
			self.check_connection()

			while self.streaming:

				# read current sample
				sample = self._read_sample()
				# if a daisy module is attached, wait to concatenate two samples
				# (main board + daisy) before passing it to callback
				if self.board_type == cnts.BOARD_DAISY:
					# odd sample: daisy sample, save for later
					if ~sample.id % 2:
						self.last_odd_sample = sample
					# even sample: concatenate and send if last sample was the fist part,
					#  otherwise drop the packet
					elif sample.id - 1 == self.last_odd_sample.id:
						# the aux data will be the average between the two samples, as the channel
						#  samples themselves have been averaged by the board
						avg_aux_data = list(
							(np.array(sample.aux_data) + np.array(self.last_odd_sample.aux_data)) / 2)
						whole_sample = OpenBCISample(sample.id,
						                             sample.channel_data +
						                             self.last_odd_sample.channel_data,
						                             avg_aux_data)
						for call in callback:
							call(whole_sample)
				else:
					for call in callback:
						call(sample)

				if 0 < lapse < (timeit.default_timer() - start_time):
					self.stopStreaming()
				if self.log:
					self.log_packet_count = self.log_packet_count + 1
		except Exception as e:
			exc_type, exc_obj, exc_tb = sys.exc_info()
			fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
			print(exc_type, fname, exc_tb.tb_lineno)
			printError("There was a problem on starting streaming in: " + fname.__str__() +
			           ' line: ' + exc_tb.tb_lineno.__str__() + "\nError Message: " + repr(e))

	def stopStreaming(self):
		print("Stopping streaming...\nWait for buffer to flush...")
		self.streaming = False
		self.ser.write(cnts.stopStreamingData)
		if self.log:
			logging.warning('sent <s>: stopped streaming')

	# SETTINGS AND HELPERS

	def _read_sample(self, max_bytes_to_skip=3000):
		"""
		  PARSER:
		  Parses incoming data packet into OpenBCISample.
		  Incoming Packet Structure:
		  Start Byte(1)|Sample ID(1)|Channel Data(24)|Aux Data(6)|End Byte(1)
		  0xA0|0-255|8, 3-byte signed ints|3 2-byte signed ints|0xC0

		"""

		def read(n):
			"""
				Read bytes from the open serial
				:param n: {int} - The number of bytes to be read
			"""
			bb = self.ser.read(n)
			if not bb:
				self.warn('Device appears to be stalled. Quitting...')
				sys.exit()
			else:
				return bb

		for rep in range(max_bytes_to_skip):

			packet = []
			b = read(1)
			# reading until start byte found
			while struct.unpack('B', b)[0] != cnts.RAW_BYTE_START:
				rep += 1
				# print("Error: " + cnts.ERROR_INVALID_BYTE_START)
				b = read(1)

			if rep != 0:
				self.warn(
					'S>kipped %d bytes before start found' % (rep))
				rep = 0

			packet.append(struct.unpack('B', b)[0])
			rest_packetInBytes = read(cnts.RAW_PACKET_SIZE - 1)
			btSize = (cnts.RAW_PACKET_SIZE - 1).__str__() + 'B'
			packet += (struct.unpack(btSize, rest_packetInBytes))
			packet_id = packet[cnts.RAW_PACKET_POSITION_SAMPLE_NUMBER]
			packet_channel_data = self.get_channel_data_array(packet)
			packet_aux_data = self.get_aux_data_array(packet)
			packet_stop_byte = packet[cnts.RAW_PACKET_POSITION_STOP_BYTE]
			if self.filtering_data:
				packet_channel_data = self.filterChannel(packet_channel_data)
			if is_stop_byte(packet_stop_byte):
				sample = OpenBCISample(packet_id, packet_channel_data, packet_aux_data)
				self.packets_dropped = 0
				return sample
			else:
				self.packets_dropped = self.packets_dropped + 1
				print("Error: " + cnts.ERROR_INVALID_BYTE_STOP)

	def _read_serial_binary(self, max_bytes_to_skip=3000):
		def read(n):
			"""
				Read bytes from the open serial
				:param n: {int} - The number of bytes to be read
			"""
			bb = self.ser.read(n)
			if not bb:
				self.warn('Device appears to be stalled. Quitting...')
				sys.exit()
			else:
				return bb

		for rep in range(max_bytes_to_skip):

			# ---------Start Byte & ID---------
			if self.read_state == 0:

				b = read(1)

				if struct.unpack('B', b)[0] == cnts.RAW_BYTE_START:
					if rep != 0:
						self.warn(
							'S>kipped %d bytes before start found' % (rep))
						rep = 0
					# packet id goes from 0-255
					packet_id = struct.unpack('B', read(1))[0]
					log_bytes_in = str(packet_id)

					self.read_state = 1

			# ---------Channel Data---------
			elif self.read_state == 1:
				channel_data = []
				for c in range(self.number_of_channels):

					# 3 byte ints
					literal_read = read(3)

					unpacked = struct.unpack('3B', literal_read)
					log_bytes_in = log_bytes_in + '|' + str(literal_read)

					# 3byte int in 2s compliment
					if unpacked[0] > 127:
						pre_fix = bytes(bytearray.fromhex('FF'))
					else:
						pre_fix = bytes(bytearray.fromhex('00'))

					literal_read = pre_fix + literal_read

					# unpack little endian(>) signed integer(i)
					# (makes unpacking platform independent)
					myInt = struct.unpack('>i', literal_read)[0]

					if self.scaling_output:
						channel_data.append(myInt * scale_fac_uVolts_per_count)
					else:
						channel_data.append(myInt)

				self.read_state = 2

			# ---------Accelerometer Data---------
			elif self.read_state == 2:
				aux_data = []
				for a in range(self.aux_channels_per_sample):

					# short = h
					acc = struct.unpack('>h', read(2))[0]
					log_bytes_in = log_bytes_in + '|' + str(acc)

					if self.scaling_output:
						aux_data.append(acc * scale_fac_accel_G_per_count)
					else:
						aux_data.append(acc)

				self.read_state = 3
			# ---------End Byte---------
			elif self.read_state == 3:
				val = struct.unpack('B', read(1))[0]
				log_bytes_in = log_bytes_in + '|' + str(val)
				self.read_state = 0  # read next packet
				if val == cnts.RAW_BYTE_STOP:
					sample = OpenBCISample(packet_id, channel_data, aux_data)
					self.packets_dropped = 0
					return sample
				else:
					self.warn("ID:<%d> <Unexpected END_BYTE found <%s> instead of <%s>"
					          % (packet_id, val, cnts.RAW_BYTE_STOP))
					logging.debug(log_bytes_in)
					self.packets_dropped = self.packets_dropped + 1

	def warn(self, text):
		if self.log:
			# log how many packets where sent successfully in between warnings
			if self.log_packet_count:
				logging.info('Data packets received:' +
				             str(self.log_packet_count))
				self.log_packet_count = 0
			logging.warning(text)
		print("Warning: %s" % text)

	def print_incoming_text(self):
		"""

		When starting the connection, print all the debug data until
		we get to a line with the end sequence '$$$'.

		"""
		line = ''
		# Wait for device to send data
		time.sleep(1)

		if self.ser.inWaiting():
			line = ''
			tmpRead = ''
			# Look for end sequence $$$
			while '$$$' not in line:
				# we're supposed to get UTF8 text, but the board might behave otherwise
				tmpRead = self.ser.read().decode('utf-8', errors='replace')
				line += tmpRead
			print(line)
		else:
			self.warn("No Message")

	def openbci_id(self, ser):
		"""
		When automatically detecting port, parse the serial return for the "OpenBCI" ID.
		"""
		line = ''
		# Wait for device to send data
		time.sleep(2)

		if ser.inWaiting():
			line = ''
			tmpRead = ''
			# Look for end sequence $$$
			while '$$$' not in line:
				# we're supposed to get UTF8 text, but the board might behave otherwise
				tmpRead = ser.read().decode('utf-8', errors='replace')
				line += tmpRead
			if "OpenBCI" in line:
				return True
		return False

	def print_register_settings(self):
		self.ser.write(cnts.queryRegisterSettings)
		time.sleep(0.5)
		self.print_incoming_text()

	# DEBUGGING: Prints individual incoming bytes
	def print_bytes_in(self):
		if not self.streaming:
			self.ser.write(cnts.startStreamingData)
			self.streaming = True
		while self.streaming:
			print(struct.unpack('B', self.ser.read())[0])

	def print_packets_in(self):
		# TODO: CHECK IF NEEDED, IF NOT DELETE!
		"""
		Incoming Packet Structure:
		  Start Byte(1)|Sample ID(1)|Channel Data(24)|Aux Data(6)|End Byte(1)
		  0xA0|0-255|8, 3-byte signed ints|3 2-byte signed ints|0xC0
		"""
		while self.streaming:
			b = struct.unpack('B', self.ser.read())[0]

			if b == cnts.RAW_BYTE_START:
				self.attempt_reconnect = False
				if skipped_str:
					logging.debug('SKIPPED\n' + skipped_str + '\nSKIPPED')
					skipped_str = ''

				packet_str = "%03d" % b + '|'
				b = struct.unpack('B', self.ser.read())[0]
				packet_str = packet_str + "%03d" % b + '|'

				# data channels
				for i in range(24 - 1):
					b = struct.unpack('B', self.ser.read())[0]
					packet_str = packet_str + '.' + "%03d" % b

				b = struct.unpack('B', self.ser.read())[0]
				packet_str = packet_str + '.' + "%03d" % b + '|'

				# aux channels
				for i in range(6 - 1):
					b = struct.unpack('B', self.ser.read())[0]
					packet_str = packet_str + '.' + "%03d" % b

				b = struct.unpack('B', self.ser.read())[0]
				packet_str = packet_str + '.' + "%03d" % b + '|'

				# end byte
				b = struct.unpack('B', self.ser.read())[0]

				# Valid Packet
				if b == cnts.RAW_BYTE_STOP:
					packet_str = packet_str + '.' + "%03d" % b + '|VAL'
					print(packet_str)
				# logging.debug(packet_str)

				# Invalid Packet
				else:
					packet_str = packet_str + '.' + "%03d" % b + '|INV'
					# Reset
					self.attempt_reconnect = True

			else:
				print(b)
				if b == cnts.RAW_BYTE_STOP:
					skipped_str = skipped_str + '|END|'
				else:
					skipped_str = skipped_str + "%03d" % b + '.'

			if self.attempt_reconnect and \
					(timeit.default_timer() - self.last_reconnect) > self.reconnect_freq:
				self.last_reconnect = timeit.default_timer()
				self.warn('Reconnecting')
				self.reconnect()

	def check_connection(self, interval=2, max_packets_to_skip=10):
		# stop checking when we're no longer streaming
		if not self.streaming:
			return
		# check number of dropped packages and establish connection problem if too large
		if self.packets_dropped > max_packets_to_skip:
			# if error, attempt to reconnect
			self.reconnect()
		# check again again in 2 seconds
		threading.Timer(interval, self.check_connection).start()

	def reconnect(self):
		self.packets_dropped = 0
		self.warn('Reconnecting')
		self.stopStreaming()
		time.sleep(0.5)
		self.ser.write(cnts.softReset)
		time.sleep(0.5)
		self.ser.write(cnts.startStreamingData)
		time.sleep(0.5)
		self.streaming = True

	# self.attempt_reconnect = False

	def test_signal(self, signal):
		""" Enable / disable test signal

			signal = 0 :  Connecting all pins to ground
			signal = 1 :  Connecting all pins to Vcc
			signal = 2 :  Connecting pins to low frequency 1x amp signal
			signal = 3 :  Connecting pins to high frequency 1x amp signal
			signal = 4 :  Connecting pins to low frequency 2x amp signal
			signal = 5 :  Connecting pins to high frequency 2x amp signal
		"""
		if signal == 0:
			self.ser.write(cnts.connectToInternalGND)
			self.warn("Connecting all pins to ground")
		elif signal == 1:
			self.ser.write(cnts.connectToDCSignal)
			self.warn("Connecting all pins to Vcc")
		elif signal == 2:
			self.ser.write(cnts.connectingPinsToLowFrequency1xAmpSignal)
			self.warn("Connecting pins to low frequency 1x amp signal")
		elif signal == 3:
			self.ser.write(cnts.connectingPinsToHighFrequency1xAmpSignal)
			self.warn("Connecting pins to high frequency 1x amp signal")
		elif signal == 4:
			self.ser.write(cnts.connectingPinsToLowFrequency2xAmpSignal)
			self.warn("Connecting pins to low frequency 2x amp signal")
		elif signal == 5:
			self.ser.write(cnts.connectingPinsToHighFrequency2xAmpSignal)
			self.warn("Connecting pins to high frequency 2x amp signal")
		else:
			self.warn("%s is not a known test signal. Valid signals go from 0-5" % signal)

	def set_channel(self, channel, toggle_position):
		""" Enable / disable channels """
		# Commands to set toggle to on position
		if toggle_position == 1:
			if channel == 1:
				self.ser.write(cnts.channel_1_on)
			if channel == 2:
				self.ser.write(cnts.channel_2_on)
			if channel == 3:
				self.ser.write(cnts.channel_3_on)
			if channel == 4:
				self.ser.write(cnts.channel_4_on)
			if channel == 5:
				self.ser.write(cnts.channel_5_on)
			if channel == 6:
				self.ser.write(cnts.channel_6_on)
			if channel == 7:
				self.ser.write(cnts.channel_7_on)
			if channel == 8:
				self.ser.write(cnts.channel_8_on)
			if channel == 9 and self.daisy:
				self.ser.write(cnts.channel_9_on)
			if channel == 10 and self.daisy:
				self.ser.write(cnts.channel_10_on)
			if channel == 11 and self.daisy:
				self.ser.write(cnts.channel_11_on)
			if channel == 12 and self.daisy:
				self.ser.write(cnts.channel_12_on)
			if channel == 13 and self.daisy:
				self.ser.write(cnts.channel_13_on)
			if channel == 14 and self.daisy:
				self.ser.write(cnts.channel_14_on)
			if channel == 15 and self.daisy:
				self.ser.write(cnts.channel_15_on)
			if channel == 16 and self.daisy:
				self.ser.write(cnts.channel_16_on)
		# Commands to set toggle to off position
		elif toggle_position == 0:
			if channel == 1:
				self.ser.write(cnts.channel_1_off)
			if channel == 2:
				self.ser.write(cnts.channel_2_off)
			if channel == 3:
				self.ser.write(cnts.channel_3_off)
			if channel == 4:
				self.ser.write(cnts.channel_4_off)
			if channel == 5:
				self.ser.write(cnts.channel_5_off)
			if channel == 6:
				self.ser.write(cnts.channel_6_off)
			if channel == 7:
				self.ser.write(cnts.channel_7_off)
			if channel == 8:
				self.ser.write(cnts.channel_8_off)
			if channel == 9 and self.daisy:
				self.ser.write(cnts.channel_9_off)
			if channel == 10 and self.daisy:
				self.ser.write(cnts.channel_10_off)
			if channel == 11 and self.daisy:
				self.ser.write(cnts.channel_11_off)
			if channel == 12 and self.daisy:
				self.ser.write(cnts.channel_12_off)
			if channel == 13 and self.daisy:
				self.ser.write(cnts.channel_13_off)
			if channel == 14 and self.daisy:
				self.ser.write(cnts.channel_14_off)
			if channel == 15 and self.daisy:
				self.ser.write(cnts.channel_15_off)
			if channel == 16 and self.daisy:
				self.ser.write(cnts.channel_16_off)

	def find_port(self):
		# Finds the serial port names
		if sys.platform.startswith('win'):
			ports = ['COM%s' % (i + 1) for i in range(256)]
		elif sys.platform.startswith('linux') or sys.platform.startswith('cygwin'):
			ports = glob.glob('/dev/ttyUSB*')
		elif sys.platform.startswith('darwin'):
			ports = glob.glob('/dev/tty.usbserial*')
		else:
			raise EnvironmentError('Error finding ports on your operating system')
		openbci_port = ''
		for port in ports:
			try:
				s = serial.Serial(port=port, baudrate=self.baudrate, timeout=self.timeout)
				s.write(cnts.softReset)
				openbci_serial = self.openbci_id(s)
				s.close()
				if openbci_serial:
					openbci_port = port
			except (OSError, serial.SerialException):
				pass
		if openbci_port == '':
			raise OSError('Cannot find OpenBCI port')
		else:
			return openbci_port

	def get_channel_data_array(self, readPacket):
		"""
		OpenBCI Incoming Packet Positions
		  Start Byte(1)|Sample ID(1)|Channel Data(24)|Aux Data(6)|End Byte(1)
				0xA0|0-255|8, 3-byte signed ints|3 2-byte signed ints|0xC0
		:param readPacket: packet has been read from the board
		:return: List with the channel data only
		"""
		channel_data = []
		# Get the channels' data one by one from the packet
		for i in range(self.number_of_channels):
			# calculate the first and the last byte of the current channel
			currentChannel_firstByte = (i * 3) + cnts.RAW_PACKET_POSITION_CHANNEL_DATA_START
			currentChannel_lastByte = (i * 3) + cnts.RAW_PACKET_POSITION_CHANNEL_DATA_START + 3
			currentChannel = readPacket[currentChannel_firstByte:currentChannel_lastByte]
			# convert the 24-bit signed integer format data into a more standard 32-bit signed integer
			dt = interpret_24_bit_as_int_32(bytes(currentChannel))
			# append current channel data to the list, scaled or not depend on the board settings
			# TODO: put scale factor in constants or sth like that
			channel_data.append(
				scale_fac_uVolts_per_count * dt if self.scaling_output else dt
			)
		return channel_data

	def get_aux_data_array(self, readPacket):
		"""
		OpenBCI Incoming Packet Positions
		  Start Byte(1)|Sample ID(1)|Channel Data(24)|Aux Data(6)|End Byte(1)
				0xA0|0-255|8, 3-byte signed ints|3 2-byte signed ints|0xC0
		:param readPacket: packet has been read from the board
		:return: List with the channel data only
		"""
		channel_data = []
		# Get the accelerometer' data one by one from the packet
		for i in range(self.aux_channels_per_sample):
			# calculate the first and the last byte of the current aux
			currentAux_firstByte = (i * 2) + cnts.RAW_PACKET_POSITION_TIME_SYNC_AUX_START
			currentAux_lastByte = (i * 2) + cnts.RAW_PACKET_POSITION_TIME_SYNC_AUX_START + 2
			currentAux = readPacket[currentAux_firstByte:currentAux_lastByte]
			# convert the 16-bit signed integer format data into a more standard 32-bit signed integer
			dt = interpret_16_bit_as_int_32(bytes(currentAux))
			# append current aux data to the list, scaled or not depend on the board settings
			# TODO: put scale factor in constants or sth like that
			channel_data.append(
				scale_fac_accel_G_per_count * dt if self.scaling_output else dt
			)
		return channel_data

	def filterChannel(self, channel_data):
		filteredData = []
		for i in range(len(channel_data)):
			filteredData.append(
				filters.bandpass([channel_data[i]], self.lowerBoundFrequency, self.higherBoundFrequency,
				                 self.sample_rate).item(0))
		return filteredData


def is_stop_byte(byte):
	"""
	Used to check and see if a byte adheres to the stop byte structure
		of 0xCx where x is the set of numbers from 0-F in hex of 0-15 in decimal.
	:param byte: {int} - The number to test
	:return: {boolean} - True if `byte` follows the correct form
	"""
	return (byte & 0xF0) == cnts.RAW_BYTE_STOP


def interpret_16_bit_as_int_32(two_byte_buffer):
	return struct.unpack('>h', two_byte_buffer)[0]


def interpret_24_bit_as_int_32(three_byte_buffer):
	# 3 byte ints
	unpacked = struct.unpack('3B', three_byte_buffer)

	# 3byte int in 2s compliment
	if unpacked[0] > 127:
		pre_fix = bytes(bytearray.fromhex('FF'))
	else:
		pre_fix = bytes(bytearray.fromhex('00'))

	three_byte_buffer = pre_fix + three_byte_buffer

	# unpack little endian(>) signed integer(i) (makes unpacking platform independent)
	return struct.unpack('>i', three_byte_buffer)[0]


class OpenBCISample(object):
	"""Object encapulsating a single sample from the OpenBCI board.
	NB: dummy imp for plugin compatiblity
	"""

	def __init__(self, packet_id, channel_data, aux_data):
		self.id = packet_id
		self.channel_data = channel_data
		self.aux_data = aux_data
		self.imp_data = []
