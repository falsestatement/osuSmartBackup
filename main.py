import tkinter as tk
import os, re, requests, json
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

        self.outputDir = os.getcwd() + '\osuSmartBackup'
        self.outputDirLabel = tk.Label(self.root, text=self.outputDir)
        self.outputDirLabel.pack(pady=5)

        self.outputDirButton = tk.Button(self.root, text="Select Your Output Directory", command=self.selectOutputDir)
        self.outputDirButton.pack()

        self.genBackupButton = tk.Button(self.root, text='Generate Backup File', command=self.generateBackup)
        self.genBackupButton.pack()

        self.root.mainloop()

    def selectOsuDir(self) -> None:
        self.osuDir = filedialog.askdirectory()
        self.curDirLabel.config(text=self.osuDir)

    def selectOutputDir(self) -> None:
        self.outputDir = filedialog.askdirectory()
        self.outputDirLabel.config(text=self.outputDir + '/osuSmartBackup')

    def generateBackup(self) -> None:
        if not os.path.exists(self.osuDir + '/Songs'):
            print('Songs folder not found, possibly incorrect osu! directory')
            return

        songScan = os.scandir(self.osuDir + '/Songs')

        self.beatmapSetList = set()
        
        self.beatmapStatus = dict()
        
        for song in songScan:
            if not song.is_dir(): continue
            
            beatmapId = re.match(r'^\d+', song.name)
            if not beatmapId:
                print('FAILED: ' + song.name)
                self.beatmapStatus[song.name] = {'backedup': False, 'parentSetId': ''}
                continue
            beatmapId = beatmapId[0]
            self.beatmapStatus[str(beatmapId)] = {'backedup': False, 'parentSetId': ''}
        
        print(json.dumps(self.beatmapStatus, indent=2))
        # res = self.getBeatmap(beatmapId)
        # if res:
        #     print(res)
        # else:
        #    print(f'No mirror on {beatmapId}')

    def getBeatmap(self, beatmapId) -> dict:
        beatmapURL = f'https://storage.ripple.moe/api/b/{beatmapId}'
        for _ in range(5):
            try: 
                res = requests.get(url = beatmapURL).json()
                break
            except requests.exceptions.Timeout:
                pass
            except requests.exceptions.RequestException as e:
                raise SystemExit(e)

        return res

MainGUI()