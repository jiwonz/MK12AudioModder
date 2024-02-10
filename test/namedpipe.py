import win32pipe, win32file
import os.path
import time
import os

def waitForFile(file_path):
	while not os.path.exists(file_path):
		time.sleep(1)

class PipeServer():
	def __init__(self, pipeName):
		self.pipe = win32pipe.CreateNamedPipe(
		r'\\.\pipe\\'+pipeName,
		win32pipe.PIPE_ACCESS_OUTBOUND,
		win32pipe.PIPE_TYPE_MESSAGE | win32pipe.PIPE_READMODE_MESSAGE | win32pipe.PIPE_WAIT,
		1, 65536, 65536,
		0,
		None)

	#Carefull, this blocks until a connection is established
	def connect(self):
		win32pipe.ConnectNamedPipe(self.pipe, None)

	#Message without tailing '\n'
	def write(self, message):
		win32file.WriteFile(self.pipe, message.encode()+b'\n')

	def close(self):
		win32file.CloseHandle(self.pipe)


t = PipeServer("MK12AudioModder")
t.connect()
while True:
	msg = input("tell something: ")
	if msg == "":
		break
	t.write(msg)
	waitForFile("test.done")
	os.remove("test.done")
	print("process success!")

t.close()
