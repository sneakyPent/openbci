from multiprocessing import Process, Event


class DataManager(object):
	"""
		Used to _share data from one queue to every other queue contained in the given processesQueuesList

		Args:
			data: queue type data will be shared
			processesArgsList: A list of dictionaries with queues and their locks for the other processes the data will be shared

	"""

	def __init__(self, data, processesArgsList):
		self.data = data
		self.processesArgsList = processesArgsList

		# share event will be set only by the process will be put data into primary 'data' queue
		self.share = Event()
		# newDataAvailable event will be used by the other processes to wait for new data and it set by DataManager only
		self.newDataAvailable = Event()

	def disableNewDataAvailable(self):
		try:
			while True:
				NonEmpty = any(proc.queue.qsize() > 0 for proc in self.processesArgsList)
				if not NonEmpty:
					self.newDataAvailable.clear()
					self.share.wait()
		except Exception:
			pass

	def getDataManagerEvents(self):
		return {
			"share": self.share,
			"newDataAvailable": self.newDataAvailable,
		}

	def shareData(self):
		print("shareData: waiting")
		print("shareData size: " + self.data.qsize().__str__())
		p = Process(target=self.disableNewDataAvailable)
		p.start()
		try:
			while True:
				self.share.wait()
				while not self.data.empty():
					dt = self.data.get()
					print("_share Data func:" + dt.__str__())
					for procArgs in self.processesArgsList:
						procArgs.lock.acquire()
						# if any queue for any reason get full release lock and continue to next one
						if procArgs.queue.full():
							procArgs.lock.release()
							continue
						try:
							procArgs.queue.put(dt)
						finally:
							procArgs.lock.release()
					self.newDataAvailable.set()
				self.share.clear()
		except KeyboardInterrupt:
			p.terminate()
