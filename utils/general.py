import multiprocessing
import queue
import traceback
from multiprocessing.managers import BaseProxy
from queue import Queue
from utils import printError


def emptyQueue(q):
	"""
	It empties the given Queue.

	:param [],manager.Queue, queue.Queue. multiprocessing.Queue q:
	:return: None
	"""
	try:
		if isinstance(q, list):
			for buf in q:
				if isinstance(buf, BaseProxy) or isinstance(q, Queue):
					print('Manager Queue from list emptying') if not buf.empty() else None
					while not buf.empty():
						buf.get()
				elif isinstance(buf, multiprocessing.queues.Queue):
					printError('multi queue')
					print('Multiprocessing queue from list emptying') if not buf.empty() else None
					while not buf.empty():
						buf.get()
		elif isinstance(q, Queue) or isinstance(q, BaseProxy):
			print('Manager Queue emptying') if not q.empty() else None
			while not q.empty():
				q.get_nowait()
		elif isinstance(q, multiprocessing.queues.Queue):
			print('Multiprocessing queue emptying') if not q.empty() else None
			while not q.empty():
				q.get_nowait()
	except queue.Empty:
		traceback.print_exc()
	except AttributeError as error:
		pass
	# print(error)
