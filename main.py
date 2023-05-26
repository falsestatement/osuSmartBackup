import tkinter as tk
import os
from tkinter import filedialog

class MainGUI:
    def __init__(self) -> None:
        self.root = tk.Tk()

        self.root.geometry("800x500")
        self.root.title("osu! Smart Backup")

        self.titleLabel = tk.Label(self.root, text="osu! Smart Backup", font=('Arial', 16))
        self.titleLabel.pack(pady=20)

        self.osuDir = os.getenv("LOCALAPPDATA") + '\osu!'
        self.curDirLabel = tk.Label(self.root, text=self.osuDir)
        self.curDirLabel.pack()

        self.osuDirButton = tk.Button(self.root, text="Select Your osu! Directory", command=self.selectOsuDir)
        self.osuDirButton.pack()

        self.genBackupButton = tk.Button(self.root, text='Generate Backup File', command=self.generateBackup)
        self.genBackupButton.pack()

        self.root.mainloop()

    def selectOsuDir(self) -> None:
        self.osuDir = filedialog.askdirectory()
        self.curDirLabel.config(text=self.osuDir)

    def generateBackup(self):
        songScan = os.scandir(self.osuDir + '/Songs')
        for song in songScan:
            if song.is_dir():
                print(song.name)

MainGUI()