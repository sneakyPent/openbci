from multiprocessing import Process


class DataManager(object):
    """
        Used to share data from one queue to every other queue contained in the given processesQueuesList

        Args:
            data: queue type data will be shared
            processesArgsList: A list of dictionaries with queues the data will get into and their locks
            _share: Event used to wait when there is no data to share
            _newDataAvailable: Event used to inform ,for new data, every other process that is using at least one of
                                the queues contained in processesQueuesList
        """

    def __init__(self, data, processesArgsList, _share, _newDataAvailable):
        self.data = data
        self.processesArgsList = processesArgsList
        self.share = _share
        self.newDataAvailable = _newDataAvailable

    def disableNewDataAvailable(self):
        while True:
            NonEmpty = any(proc.queue.qsize() > 0 for proc in self.processesArgsList)
            if not NonEmpty:
                self.newDataAvailable.clear()
                self.share.wait()

    def shareData(self):
        p = Process(target=self.disableNewDataAvailable)
        p.start()
        try:
            while True:
                self.share.wait()
                while not self.data.empty():
                    dt = self.data.get()
                    for procArgs in self.processesArgsList:
                        procArgs.lock.acquire()
                        try:
                            procArgs.queue.put(dt)
                        finally:
                            procArgs.lock.release()
                    self.newDataAvailable.set()
                self.share.clear()
        except KeyboardInterrupt:
            p.terminate()
