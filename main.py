import tkinter as tk
import os, re, requests, json, pickle
from tkinter import filedialog, messagebox

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

        self.backupDir = os.getcwd()
        self.backupFile = self.backupDir + '\osuSongs.bak'
        self.backupDirLabel = tk.Label(self.root, text=self.backupFile)
        self.backupDirLabel.pack(pady=5)

        self.backupDirButton = tk.Button(self.root, text="Select Your Output Directory", command=self.selectBackupDir)
        self.backupDirButton.pack()

        self.genBackupButton = tk.Button(self.root, text='Generate Backup File', command=self.generateBackup)
        self.genBackupButton.pack()

        self.root.mainloop()

    def selectOsuDir(self) -> None:
        self.osuDir = filedialog.askdirectory()
        self.curDirLabel.config(text=self.osuDir)

    def selectBackupDir(self) -> None:
        self.backupDir = filedialog.askdirectory()
        self.backupFile = self.backupDir + '/osuSongs.bak'
        self.backupDirLabel.config(text=self.backupFile)

    def generateBackup(self) -> None:
        if not os.path.exists(self.osuDir + '/Songs'):
            print('Songs folder not found, possibly incorrect osu! directory')
            return

        if not os.path.isfile(self.backupFile):
            backupAlert = messagebox.askyesno(title='No backup file detected', message='No backup file found at the backup location, create a new file?')
            if not backupAlert:
                return
            with open(self.backupFile, 'wb') as outfile:
                pickle.dump({}, outfile)

        songScan = os.scandir(self.osuDir + '/Songs')

        with open(self.backupFile, 'rb') as infile:
            self.beatmapStatus = pickle.load(infile)
        
        for song in songScan:
            if not song.is_dir(): continue
            
            beatmapId = re.match(r'^\d+', song.name)
            
            if beatmapId and beatmapId[0] in self.beatmapStatus or song.name in self.beatmapStatus:
                continue
            
            if not beatmapId:
                print('FAILED: ' + song.name)
                self.beatmapStatus[song.name] = {'reachable': False, 'parentSetId': ''}
                continue
            beatmapId = beatmapId[0]
            print('New beatmap entry added')
            self.beatmapStatus[str(beatmapId)] = {'reachable': True, 'parentSetId': ''}
        
        with open(self.backupFile, 'wb') as outfile:
            pickle.dump(self.beatmapStatus, outfile)
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