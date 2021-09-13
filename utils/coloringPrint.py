from utils.constants import Constants as cnst


# TODO: make print error adds error in log file too
def printError(string):
	print(cnst.FAIL + 'ERROR: ' + cnst.ENDC + string)


def printSuccess(string):
	print(cnst.OKGREEN + 'SUCCESS: ' + cnst.ENDC + string)


def printWarning(string):
	print(cnst.WARNING + 'WARNING: ' + cnst.ENDC + string)


def printHeader(string):
	print(cnst.HEADER + string + cnst.ENDC)


def printInfo(string):
	print(cnst.CYAN + 'INFO: ' + cnst.ENDC + string)


def printBold(string):
	print(cnst.BOLD + string + cnst.ENDC)


def printUnderlined(string):
	print(cnst.UNDERLINE + string + cnst.ENDC)
