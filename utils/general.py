import logging
import multiprocessing
import queue
import traceback
from multiprocessing.managers import BaseProxy
from queue import Queue
from utils import Constants as cnst
import time


def emptyQueue(q):
	"""
	It empties the given Queue.

	:param [],manager.Queue, queue.Queue. multiprocessing.Queue q:
	:return: None
	"""
	logger = logging.getLogger(cnst.loggerName)
	try:
		if isinstance(q, list):
			for buf in q:
				if isinstance(buf, BaseProxy) or isinstance(q, Queue):
					logger.info('Manager Queue from list emptying') if not buf.empty() else None
					while not buf.empty():
						buf.get()
				elif isinstance(buf, multiprocessing.queues.Queue):
					logger.info('Multiprocessing queue from list emptying') if not buf.empty() else None
					while not buf.empty():
						buf.get()
		elif isinstance(q, Queue) or isinstance(q, BaseProxy):
			logger.info('Manager Queue emptying') if not q.empty() else None
			while not q.empty():
				q.get_nowait()
		elif isinstance(q, multiprocessing.queues.Queue):
			logger.info('Multiprocessing queue emptying') if not q.empty() else None
			while not q.empty():
				q.get_nowait()
	except queue.Empty:
		logger.error(msg='', exc_info=True)
		traceback.print_exc()
	except AttributeError as error:
		logger.error(error)


class TimerError(Exception):
	"""A custom exception used to report errors in use of Timer class"""

class Timer:
	def __init__(self):
		self._start_time = None
	
	def getTime(self):
		return self._start_time
	
	def start(self):
		"""Start a new timer"""
		if self._start_time is not None:
			raise TimerError(f"Timer is running. Use .stop() to stop it")

		self._start_time = time.perf_counter()

	def checkpoint(self):
		if self._start_time is None:
			raise TimerError(f"Timer is not running. Use .start() to start it")
		checkpointTime = time.perf_counter() - self._start_time
		return "{:.5f}".format(checkpointTime)
	
	def stop(self):
		"""Stop the timer, and report the elapsed time"""
		if self._start_time is None:
			raise TimerError(f"Timer is not running. Use .start() to start it")

		elapsed_time = time.perf_counter() - self._start_time
		self._start_time = None
		print(f"Elapsed time: {elapsed_time:0.4f} seconds")