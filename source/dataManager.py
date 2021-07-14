from multiprocessing import Process


class DataManager(object):
	"""
		Used to _share data from one queue to every other queue contained in the given processesQueuesList

		Args:
			data: queue type data will be shared
			processesArgsList: A list of dictionaries with queues the data will get into and their locks
			dataManagerEvents.share: Event used to wait when there is no data to _share
			dataManagerEvents.newDataAvailable: Event used to inform ,for new data, every other process that is using at least one of
								the queues contained in processesQueuesList
		"""

	def __init__(self, data, processesArgsList, dataManagerEvents):
		self.data = data
		self.processesArgsList = processesArgsList
		self._share = dataManagerEvents.share
		self._newDataAvailable = dataManagerEvents.newDataAvailable

	def disableNewDataAvailable(self):
		try:
			while True:
				NonEmpty = any(proc.queue.qsize() > 0 for proc in self.processesArgsList)
				if not NonEmpty:
					self._newDataAvailable.clear()
					self._share.wait()
		except Exception:
			pass

	def shareData(self):
		print("shareData: waiting")
		print("shareData size: " + self.data.qsize().__str__())
		p = Process(target=self.disableNewDataAvailable)
		p.start()
		try:
			while True:
				self._share.wait()
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
					self._newDataAvailable.set()
				self._share.clear()
		except KeyboardInterrupt:
			p.terminate()
