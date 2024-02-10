# requirements:
# - pickledb
# - winsound
# - turbosnake
# - ttkthemes
# - tkinterDnD
# use dotnet instead of pyUE4Parse

from tkinter import filedialog,messagebox,simpledialog
import subprocess
import os
import pickledb
from pathlib import Path,WindowsPath
import shutil
import threading
import time
import winsound

db = pickledb.load('save.db', False)
appName = "MK12AudioModder"
aesHexKey = "0x6FAABA4F4EF8A6AC188A517ACEF38F1422484E3B1F3F4CF3DACB27A6CBCCD076"

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
