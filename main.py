from tkinter import filedialog,messagebox,simpledialog
import subprocess
import os
from UE4Parse.Assets.Objects.FGuid import FGuid
from UE4Parse.Provider import DefaultFileProvider, MappingProvider
from UE4Parse.Versions import EUEVersion, VersionContainer
from UE4Parse.Encryption import FAESKey
from UE4Parse.Assets.Exports.Sound import UAkMediaAssetData
from UE4Parse.Assets.PackageReader import LegacyPackageReader
from UE4Parse.Readers.FAssetReader import FAssetReader
import logging
import pickledb
import re
from pathlib import Path,WindowsPath
import shutil
import threading
import time
import winsound

db = pickledb.load('save.db', False)
appName = "MK12AudioModder"
aesHexKey = "0x6FAABA4F4EF8A6AC188A517ACEF38F1422484E3B1F3F4CF3DACB27A6CBCCD076"

with open("media.txt", 'r') as file:
    lines = file.readlines()

mediaPaths = [line.strip() for line in lines]

def cloneAndMoveFile(source_path,destination_path):
    if not os.path.exists(os.path.dirname(destination_path)):
        os.makedirs(os.path.dirname(destination_path))
    shutil.copy(source_path, destination_path)
    shutil.move(destination_path, destination_path)
    #print(f"File cloned and moved successfully to: {destination_path}")

def moveFile(source_path, destination_path):
    if not os.path.exists(os.path.dirname(destination_path)):
        os.makedirs(os.path.dirname(destination_path))
    shutil.move(source_path, destination_path)
    #print(f"File moved successfully to: {destination_path}")

def parseVgmstreamOutput(output):
    sample_rate = None
    bitrate = None

    for line in output.split('\n'):
        if line.startswith("sample rate:"):
            sample_rate_match = re.search(r'sample rate: (\d+)', line)
            if sample_rate_match:
                sample_rate = int(sample_rate_match.group(1))
        elif line.startswith("bitrate:"):
            bitrate_match = re.search(r'bitrate: (\d+) kbps', line)
            if bitrate_match:
                bitrate = int(bitrate_match.group(1))

    return sample_rate, bitrate

def process(project):
	print("Choose MK12/Content/Paks directory")
	paksPath = filedialog.askdirectory(
		title="Choose MK12/Content/Paks directory",
		initialdir=db.get("paks")
	)
	db.set("paks",paksPath)
	print("Choose WwiseConsole.exe")
	wwisePath = filedialog.askopenfilename(
		title="Choose WwiseConsole.exe",
		initialdir=db.get("wwise") and os.path.dirname(db.get("wwise")) or None,
		initialfile=db.get("wwise")
	)
	db.set("wwise",wwisePath)
	db.dump()

	print("started wwise command waapi")

	#logging.getLogger("UE4Parse").setLevel(logging.INFO)  # set logging level

	aeskeys = {
		FGuid(0,0,0,0): FAESKey(aesHexKey),
	}

	print("Reading paks...")

	import gc; gc.disable() # temporarily disabling garbage collector gives a huge performance boost

	provider = DefaultFileProvider(paksPath, VersionContainer(EUEVersion.GAME_UE4_BASE))
	provider.initialize()
	provider.submit_keys(aeskeys)  # mount files

	gc.enable()

	print("Successfully loaded paks!")

	nameWAVtoIdWAV = {}
	nameWAVtoSampleBitRate = {}
	#bundleFunctions = []
	packagePaths = {}
	modPakPath = project+"/"+os.path.basename(project)
	dirItems = os.listdir(project)

	def processWem(wemId):
		for path in mediaPaths:
			packagePath = path+"/"+wemId
			package = provider.files.get(packagePath)
			print("package:",package)
			if package != None:
				wem = project+"/"+wemId+".wem"
				buffer = package.get_data()
				with open(wem, 'wb') as f:
					f.write(buffer.base_stream.getvalue())
				wavPath = project+"/"+Path(bnkPath).stem+".wav"
				result = subprocess.run(["vgmstream/vgmstream-cli",wem,"-o",wavPath],capture_output=True,text=True)
				if result.returncode == 0:
					#print(result.stdout)
					nameWAVtoSampleBitRate[wavPath] = parseVgmstreamOutput(result.stdout)
					#print("BOIIII:",nameWAVtoSampleBitRate[wavPath])
				nameWAVtoIdWAV[wavPath] = project+"/wwise/convert/input/"+wemId+".wav"
				os.remove(wem)
				packagePaths[wemId] = packagePath
				# def bundle():
				# 	newWem = project+"/"+wemId+".wem"
				# 	if not os.path.exists(newWem):
				# 		return wemId+".wem is not found"
				# 	moveFile(newWem,modPath+"/"+packagePath+".wem")
				# bundleFunctions.append(bundle)
				break

	for bnk in dirItems:
		bnkPath = project+"/"+bnk
		if Path(bnkPath).suffix != ".bnk":
			continue
		print("PROCESSING",bnk)
		wemId = None
		subprocess.run(["wwiser.exe","-g",bnkPath,"-go",project],stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
		txtpPath = project+"/"+Path(bnk).stem+".txtp"
		with open(txtpPath,"r") as file:
			content = file.read()
			match = re.search(r'Source (\d+)', content)
			if match:
				wemId = match.group(1)
				print("Source number:", wemId)
			else:
				print("Source number not found.")
		os.remove(txtpPath)
		processWem(wemId)

	#simpledialog.askstring(appName,"When you are finished editing the sound, enter the mod project name and press OK.")
	#messagebox.showinfo(appName,"When you are finished modifying audio files, press OK")
	modList = []
	mods = {}
	for nameWav,idWav in nameWAVtoIdWAV.items():
		modName = Path(nameWav).stem
		modList.append(modName)
		mods[modName] = nameWav

	while True:
		print("Modding Menu")
		work = select(modList+["Compile into .pak","Use my .wem","Cancel"],cursor="🢧", cursor_style="cyan")
		if work == "Compile into .pak":
			break
		elif work == "Use my .wem":
			dirItems = os.listdir(project)
			for wem in dirItems:
				if Path(wem).suffix != ".wem":
					continue
				wemId = Path(wem).stem
				processWem(wemId)
		elif work == "Cancel":
			return
		else:
			print("Choose audio to replace",work)
			alt = filedialog.askopenfilename(
				title="Choose audio to replace "+work,
				initialdir=db.get("recent") and os.path.dirname(db.get("recent")) or project
			)
			db.set("recent",alt)
			db.dump()
			shutil.copyfile(alt,mods[work])
			print("Successfully to replace",work)

	wproj = project+"/"+"wwise"
	shutil.copytree("wwise",wproj)
	shutil.copytree("convert",wproj+"/convert")

	wwiseImports = []
	for nameWav,idWav in nameWAVtoIdWAV.items():
		samplerate,bitrate = nameWAVtoSampleBitRate[nameWav]
		#print("HEYYYYYY:",["ffmpeg","-i",nameWav,"-b:a",str(bitrate)+"k","-ar",str(samplerate),idWav])
		subprocess.run(["ffmpeg","-y","-i",nameWav,"-b:a",str(bitrate)+"k","-ar",str(samplerate),idWav],stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
		# wwiseImports.append({
		# 	"audioFile":os.path.join(*idWav.split('/')),
		# 	"objectPath":"\\Actor-Mixer Hierarchy\\Default Work Unit\\<Sound SFX>"+Path(idWav).stem
		# })
		os.remove(nameWav) # delete original before do ffmpeg wav

	#print(wwiseImports)

	cwd = os.getcwd()
	convertPath = os.path.abspath(wproj+"/convert")
	os.chdir(convertPath)
	subprocess.run([convertPath+"/convert.bat",wwisePath])
	os.chdir(cwd)

	wemItems = os.listdir(wproj+"/convert/output/Windows")
	for newWem in wemItems:
		if Path(newWem).suffix != ".wem":
			continue
		path = wproj+"/convert/output/Windows/"+newWem
		wemId = Path(newWem).stem
		print(path,modPakPath+"/"+packagePaths[wemId]+".wem")
		moveFile(path,modPakPath+"/"+packagePaths[wemId]+".wem")

	shutil.rmtree(wproj)
	print("Finished processing with wwise")

	# messagebox.showinfo(appName,"Convert the file given in <number>.wav format to <number>.wem using wwise. When all conversion is complete, press OK.")
	# for bundle in bundleFunctions:
	# 	err = bundle()
	# 	if err != None:
	# 		messagebox.showerror(appName,"Error: "+err)
	# 		return
	subprocess.run([os.path.abspath("unrealpak/UnrealPak-With-Compression.bat"),os.path.abspath(modPakPath)])
	shutil.rmtree(modPakPath)
	os.remove("unrealpak/filelist.txt")
	print(".pak build complete")

	result = messagebox.askquestion(appName,"Successfully compiled the mod into a pak. Do you want to move the mod to the Pakchunk99 folder and apply it to the game right away? Otherwise the paks are stored in the Project folder")
	if result == "yes":
		pak = os.path.basename(project)+".pak"
		moveFile(project+"/"+pak,paksPath+"/Pakchunk99/"+pak)
		messagebox.showinfo(appName,"Successfully moved"+pak+" into Pakchunk99")

class Audio(WindowsPath):
	def __init__(self,path):
		self.sampleRate = 0
		self.bitRate = 0
		self.packagePath = ""
		self.sourceName = ""
		self.sourceId = ""

class Project:
	def __init__(self,name:str,paksPath):
		self.path = Path("Projects/"+name)
		self.paksPath = paksPath
		self.ue4Paks = None
		self.audios = {}
	def toWavFromBnk(self,bnk:Path)->Audio:
		source,name = self.getSourceFromBnk(bnk)
		wem = self.toWemFromSource(source)
		wem.sourceName = name
		wav = self.registerFromWem(wem)
		return wav
	def toWavFromBnks(self,bnks:[Path])->Audio:
		wav = None
		def process(bnk):
			global wav
			source,name = self.getSourceFromBnk(bnk)
			wem = self.toWemFromSource(source)
			wem.sourceName = name
			wav = self.registerFromWem(wem)
		threads = []
		for bnk in bnks:
			thread = threading.Thread(target=process, args=(bnk,))
			thread.start()
			threads.append(thread)

		# Wait for all threads to finish
		for thread in threads:
			thread.join()
			print("one thing done")
		return wav
	def registerFromWem(self,wem:Audio)->Audio:
		source = wem.stem
		wav = wem.with_suffix(".wav")
		result = subprocess.run(["vgmstream/vgmstream-cli",wem,"-o",wav],capture_output=True,text=True)
		audio = Audio(wav)
		audio.sourceName = wem.sourceName
		if result.returncode == 0:
			sample,bit = parseVgmstreamOutput(result.stdout)
			audio.sampleRate = sample
			audio.bitRate = bit
		if wem.packagePath == "":
			wem.packagePath = self.getAudioPackageFromSource(source)
		os.remove(wem)
		#print("SOURCE NAME:",audio.sourceName)
		#if audio.sourceName == "":
			#name = simpledialog.askstring(appName,"Audio Name")
			#audio.sourceName = name
		audio.sourceId = source
		self.audios[source] = audio
		return audio
	def registerFromWems(self, wems: Audio) -> Audio:
		audio = None
		def process_audio(wem):
			global audio
			source = wem.stem
			wav = wem.with_suffix(".wav")
			result = subprocess.run(["vgmstream/vgmstream-cli", str(wem), "-o", str(wav)], capture_output=True, text=True)
			audio = Audio(wav)
			audio.sourceName = wem.sourceName
			if result.returncode == 0:
				sample, bit = parseVgmstreamOutput(result.stdout)
				print(sample)
				audio.sampleRate = sample
				audio.bitRate = bit
			if wem.packagePath == "":
				wem.packagePath = self.getAudioPackageFromSource(source)
			os.remove(wem)
			audio.sourceId = source
			self.audios[source] = audio

		# Create a thread for each audio processing task
		threads = []
		for wem in wems:
			thread = threading.Thread(target=process_audio, args=(wem,))
			thread.start()
			threads.append(thread)

		# Wait for all threads to finish
		for thread in threads:
			thread.join()
			print("one thing done")

		return audio
	def toWemFromSource(self,source:str)->Audio:
		packagePath,package = self.getAudioPackageFromSource(source)
		if package != None:
			wem = self.path.joinpath(Path(source)).with_suffix(".wem")
			buffer = package.get_data()
			with open(wem, 'wb') as f:
				f.write(buffer.base_stream.getvalue())
			audio = Audio(wem)
			audio.packagePath = packagePath
			return audio
	def getAudioPackageFromSource(self,source:str):
		for path in mediaPaths:
			packagePath = path+"/"+source
			package = self.ue4Paks.files.get(packagePath)
			if package != None:
				return packagePath,package
	def getSourceFromBnk(self,bnk:Path):
		if bnk.suffix != ".bnk":
			return
		wemSource = None
		subprocess.run(["wwiser.exe","-g",bnk,"-go",self.path],stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
		#txtp = bnk.with_suffix(".txtp") #project+"/"+Path(bnk).stem+".txtp"
		items = list(os.listdir(self.path))
		txtp = None
		for item in items:
			item = Path(item)
			if item.suffix != ".txtp":
				continue
			item = self.path.joinpath(item)
			if item.stem.startswith(bnk.stem):
				txtp = item
				break
		if txtp != None:
			with open(txtp,"r") as file:
				content = file.read()
				match = re.search(r'Source (\d+)', content)
				if match:
					wemSource = match.group(1)
					#print("Source number:", wemSource)
				else:
					print("Source number not found.")
			os.remove(txtp)
		return wemSource,bnk.stem

# class Audio:
# 	def __init__(self,sourceNamedPath:Path,name:str,source:str):
# 		self.path = sourceNamedPath
# 		self.name = name
# 		self.source = source
# 		self.sampleRate = 0
# 		self.bitRate = 0
# 	def toNamed(self):
# 		namedPath = self.path.parent.joinpath(Path(self.name)).with_suffix(self.path.suffix)
# 		shutil.move(self.path,namedPath)
# 		self.path = namedPath
# 	def toSourceNamed(self):
# 		sourceNamedPath = self.path.parent.joinpath(Path(self.source)).with_suffix(self.path.suffix)
# 		shutil.move(self.path,sourceNamedPath)
# 		self.path = sourceNamedPath

# def processWem(project,provider,bnkPath,wemId):
# 	for path in mediaPaths:
# 		packagePath = path+"/"+wemId
# 		package = provider.files.get(packagePath)
# 		print("package:",package)
# 		if package != None:
# 			wem = project+"/"+wemId+".wem"
# 			buffer = package.get_data()
# 			with open(wem, 'wb') as f:
# 				f.write(buffer.base_stream.getvalue())
# 			wavPath = project+"/"+Path(bnkPath).stem+".wav"
# 			result = subprocess.run(["vgmstream/vgmstream-cli",wem,"-o",wavPath],capture_output=True,text=True)
# 			if result.returncode == 0:
# 				#print(result.stdout)
# 				nameWAVtoSampleBitRate[wavPath] = parseVgmstreamOutput(result.stdout)
# 				#print("BOIIII:",nameWAVtoSampleBitRate[wavPath])
# 			nameWAVtoIdWAV[wavPath] = project+"/wwise/convert/input/"+wemId+".wav"
# 			os.remove(wem)
# 			packagePaths[wemId] = packagePath
# 			# def bundle():
# 			# 	newWem = project+"/"+wemId+".wem"
# 			# 	if not os.path.exists(newWem):
# 			# 		return wemId+".wem is not found"
# 			# 	moveFile(newWem,modPath+"/"+packagePath+".wem")
# 			# bundleFunctions.append(bundle)
# 			break

# def processBnk(project,provider,bnk):
# 	bnkPath = project+"/"+bnk
# 	if Path(bnkPath).suffix != ".bnk":
# 		return
# 	print("PROCESSING",bnk)
# 	wemId = None
# 	subprocess.run(["wwiser.exe","-g",bnkPath,"-go",project])
# 	txtpPath = project+"/"+Path(bnk).stem+".txtp"
# 	with open(txtpPath,"r") as file:
# 		content = file.read()
# 		match = re.search(r'Source (\d+)', content)
# 		if match:
# 			wemId = match.group(1)
# 			print("Source number:", wemId)
# 		else:
# 			print("Source number not found.")
# 	os.remove(txtpPath)
# 	processWem(wemId)

# GUI ----------------------------------------------------------------------------------------------------------

from turbosnake import *
import turbosnake.ttk as element
import tkinter as tk
from ttkthemes import ThemedTk
import tkinterDnD
from tkinter import ttk

portal = tkinterDnD.Tk()
portal.title(appName+" - Drag and drop handler")
portal.geometry("400x400")
portal.resizable(False,False)

stringvar = tk.StringVar()
stringvar.set('Drop here or drag from here!')

dndShared = {}
def drop(event):
	# This function is called, when stuff is dropped into a widget
	stringvar.set(event.data)
	add = dndShared["add"]
	if add != None:
		add(event.data)

# def drag_command(event):
#     # This function is called at the start of the drag,
#     # it returns the drag type, the content type, and the actual content
#     return (tkinterDnD.COPY, "DND_Text", "Some nice dropped text!")


label_2 = ttk.Label(portal, ondrop=drop,
                    textvar=stringvar, padding=50, relief="solid")
label_2.pack(fill="both", expand=True, padx=10, pady=10)

portal.withdraw()

projectsDirectory = Path("Projects")

@element.style
def styleProjectScrollingFrame(s):
	s["width"]=50

@element.style
def styleProjectButton(s):
	s["width"]=50
	s["anchor"]="w"

@element.style
def styleProjectButtonSelected(s):
	s["width"]=50
	s["background"] = "#005fb8"
	s["foreground"] = "#005fb8"
	s["anchor"]="w"

@element.style
def styleRed(s):
	s["background"] = "red"
	s["foreground"] = "red"

@element.style
def styleToolButtonSelected(s):
	s["width"]=15
	s["background"] = "#005fb8"
	s["foreground"] = "#005fb8"

@element.style
def styleToolButton(s):
	s["width"]=9

@element.style
def styleModdingScrollingFrame(s):
	s["width"]=80

@element.style
def styleModdingButton(s):
	s["width"]=80
	s["height"]=30
	s["anchor"]="w"

currentProject = None
provider = None

@functional_component
def App():
	global currentProject
	global provider
	global dndShared
	path,setPath = use_state("projects")
	reload,setReload = use_state(False)
	selection,setSelection = use_state()
	paksPath,setPaksPath = use_state("" if db.get("paks") == "" else db.get("paks"))
	wwisePath,setWwisePath = use_state("" if db.get("wwise") == "" else db.get("wwise"))
	warningVisible,setWarningVisible = use_state(False)
	tool,setTool = use_state("previewer")

	if tool == "adder":
		portal.deiconify()
	else:
		portal.withdraw()

	def doReload():
		setReload(not reload)

	if path == "projects":
		items = os.listdir(projectsDirectory)
		folder_names = [item for item in items if projectsDirectory.joinpath(item).is_dir()]
		isSelected = False
		if selection != None:
			isSelected = True

		def doOpen():
			global currentProject
			global provider
			if paksPath == "" or wwisePath == "":
				setWarningVisible(True)
				return
			currentProject = Project(selection,paksPath)
			if provider != None:
				currentProject.ue4Paks = provider
				setPath("loading_wav")
			else:
				setPath("loading_ue4paks")

		def doCreateNew():
			name = simpledialog.askstring(appName,"New project name")
			if name:
				os.makedirs("Projects/"+name, exist_ok=True)
				doReload()

		def doDelete():
			result = messagebox.askquestion(appName,"Are you sure you want to delete it?")
			if result == "yes":
				shutil.rmtree("Projects/"+selection)
				doReload()

		def createSelectHandler(folder):
			def onSelect():
				s = None
				if folder != selection:
					s = folder
				setSelection(s)
			return onSelect

		def createSelectStyleHandler(selected):
			if selected:
				return styleProjectButtonSelected
			else:
				return styleProjectButton

		def doChoosePaks():
			paksPath = filedialog.askdirectory(
				title="Choose MK12/Content/Paks directory",
				initialdir=db.get("paks")
			)
			db.set("paks",paksPath)
			db.dump()
			setPaksPath(paksPath)

		def doChooseWwiseConsole():
			wwisePath = filedialog.askopenfilename(
				title="Choose WwiseConsole.exe",
				initialdir=os.path.dirname(db.get("wwise")) if db.get("wwise")!=None else None,
				initialfile=db.get("wwise")
			)
			db.set("wwise",wwisePath)
			db.dump()
			setWwisePath(wwisePath)

		element.tk_label(text="MK12/Content/Paks")
		with element.tk_packed_frame(default_side="left"):
			element.tk_button(text=paksPath ,on_click=doChoosePaks)
		if warningVisible and paksPath == "":
			element.tk_button(text="This is required!",style=styleRed)
		element.tk_label(text="WwiseConsole")
		with element.tk_packed_frame(default_side="left"):
			element.tk_button(text=wwisePath,on_click=doChooseWwiseConsole)
		if warningVisible and wwisePath == "":
			element.tk_button(text="This is required!",style=styleRed)
		element.tk_label(text="Projects")
		with element.tk_scrollable_frame(px=5,py=5,style=styleProjectScrollingFrame,fill="x"):
			for folder in folder_names:
				element.tk_button(text=folder,style=createSelectStyleHandler(folder==selection),on_click=createSelectHandler(folder))
		with element.tk_packed_frame(default_side="left",px=5,py=5):
			element.tk_button(text="Reload List",on_click=doReload)
			element.tk_button(text="New...",on_click=doCreateNew)
			element.tk_button(text="Delete Selection",on_click=doDelete,disabled=not isSelected)
			element.tk_button(text="Open Selection",on_click=doOpen,disabled=not isSelected)
	elif path == "loading_ue4paks":
		element.tk_label(text="Reading Paks please wait...")
		def loadUE4Paks():
			global provider
			aeskeys = {
				FGuid(0,0,0,0): FAESKey(aesHexKey),
			}

			print("Reading paks...")

			import gc; gc.disable() # temporarily disabling garbage collector gives a huge performance boost

			provider = DefaultFileProvider(currentProject.paksPath, VersionContainer(EUEVersion.GAME_UE4_BASE))
			provider.initialize()
			provider.submit_keys(aeskeys)  # mount files
			currentProject.ue4Paks = provider

			gc.enable()

			print("Successfully loaded paks!")
		operation = threading.Thread(target=loadUE4Paks,daemon=True)
		operation.start()
		def nextLoading():
			operation.join()
			setPath("loading_wav")
		nextOperation = threading.Thread(target=nextLoading,daemon=True)
		nextOperation.start()
	elif path == "loading_wav":
		element.tk_label(text="Generating .wav please wait...")
		items = list(os.listdir(currentProject.path))
		def process():
			wems = []
			bnks = []
			for item in items:
				item = currentProject.path.joinpath(item)
				if item.suffix == ".wem":
					#currentProject.registerFromWem(Audio(item))
					wems.append(Audio(item))
				elif item.suffix == ".bnk":
					#currentProject.toWavFromBnk(item)
					bnks.append(item)
			currentProject.registerFromWems(wems)
			currentProject.toWavFromBnks(bnks)
			time.sleep(1)
		operation = threading.Thread(target=process,daemon=True)
		operation.start()
		def beginModding():
			operation.join()
			setPath("modding")
		nextOperation = threading.Thread(target=beginModding,daemon=True)
		nextOperation.start()
	elif path == "modding":
		def doBack():
			del currentProject
			currentProject = None
			setTool("previewer")
			setPath("projects")
		def add(path):
			path = Path(path)
			shutil.copyfile(path,currentProject.path.joinpath(path.name))
			path = currentProject.path.joinpath(path.name)
			if path.suffix == ".wem":
				currentProject.registerFromWem(Audio(path))
			elif path.suffix == ".bnk":
				currentProject.toWavFromBnk(path)
			doReload()
		dndShared["add"] = add
		def insertFromComputer():
			items = filedialog.askopenfilenames(
				title="Choose wwise .bnk",
				initialdir=os.path.dirname(db.get("recent")) if db.get("recent")!=None else None,
				initialfile=db.get("recent")
			)
			db.set("recent",path)
			db.dump()
			threads = []
			for item in items:
				thread = threading.Thread(target=add,args=(item,))
				thread.start()
				threads.append(thread)
			for thread in threads:
				thread.join()
				print("one thing done")

		toolFunctions = {}
		def previewer(audio:Audio):
			sound = str(currentProject.path.joinpath(audio.sourceId).with_suffix(".wav"))
			winsound.PlaySound(sound,winsound.SND_ASYNC)
		toolFunctions["previewer"] = previewer
		def remover(audio:Audio,dontReload):
			os.remove(currentProject.path.joinpath(audio.sourceId).with_suffix(".wav"))
			os.remove(currentProject.path.joinpath(audio.sourceName).with_suffix(".bnk"))
			del currentProject.audios[audio.sourceId]
			if not dontReload:
				doReload()
		toolFunctions["remover"] = remover

		def removeAll():
			for _,audio in currentProject.audios.items():
				thread = threading.Thread(target=remover,args=(audio,False,),daemon=True)
				thread.start()

		with element.tk_packed_frame(default_side="left",px=5,py=5):
			element.tk_button(text="Back",on_click=doBack)
			element.tk_button(text="Insert From Computer",on_click=insertFromComputer)
			element.tk_button(text="Remove All",on_click=removeAll)
			element.tk_label(text="Tools:")
			element.tk_button(text="Adder",on_click=lambda:setTool("adder"),style=styleToolButton if tool!="adder" else styleToolButtonSelected)
			element.tk_button(text="Remover",on_click=lambda:setTool("remover"),style=styleToolButton if tool!="remover" else styleToolButtonSelected)
			element.tk_button(text="Previewer",on_click=lambda:setTool("previewer"),style=styleToolButton if tool!="previewer" else styleToolButtonSelected)
			element.tk_button(text="Replacer",on_click=lambda:setTool("replacer"),style=styleToolButton if tool!="replacer" else styleToolButtonSelected)
			element.tk_button(text="Auto Replacer",on_click=lambda:setTool("auto_replacer"),style=styleToolButton if tool!="auto_replacer" else styleToolButtonSelected)
		element.tk_label(text="Audio Packages")
		def createToolFunctionHandler(audio):
			def init():
				f = toolFunctions[tool]
				if f != None:
					f(audio)
			return init
		with element.tk_scrollable_frame(px=5,py=5,style=styleModdingScrollingFrame,width=100):
			for _,audio in currentProject.audios.items():
				#print(audio)
				pass#element.tk_button(text=audio.sourceName,style=styleModdingButton,on_click=createToolFunctionHandler(audio))
		with element.tk_packed_frame(default_side="left",px=5,py=5):
			element.tk_button(text="Build")
			element.tk_button(text="Apply To Pakchunk99")
	# if len(folder_names) > 0:
	# 	print("Choose a project to process")
	# 	project = select(folder_names,cursor="🢧", cursor_style="cyan")
	# 	process("Projects/"+project)
	# else:
	# 	messagebox.showinfo(appName,"The Projects directory is empty. Create a new project by adding a folder and then put the .bnk you want into it")

root = ThemedTk(theme="radiance")

askingClose = False
def onClosing():
	global askingClose
	if askingClose == True:
		return
	askingClose = True
	if messagebox.askokcancel("Quit", "Do you want to quit?"):
		portal.destroy()
		root.destroy()
	else:
		askingClose = False

root.protocol("WM_DELETE_WINDOW", onClosing)

if __name__ == "__main__":
	with element.tk_app(root,min_width=500,min_height=300,title=appName):
		App()
	portal.mainloop()
