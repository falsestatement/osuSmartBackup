import tkinter as tk
import os
import re
import requests
import json
import pickle
import time
import threading
import random
import multiprocessing as mp
from multiprocessing.pool import ThreadPool as tp
from tkinter import filedialog, messagebox
from tkinter.ttk import Progressbar


class MainGUI:
    def __init__(self) -> None:
        self.root = tk.Tk()

        self.root.geometry("800x600")
        self.root.title("osu! Smart Backup")

        self.titleLabel = tk.Label(
            self.root, text="osu! Smart Backup", font=('Arial', 16))
        self.titleLabel.pack(pady=20)

        self.fileFrame = tk.Frame(self.root)

        self.osuDir = os.getenv("LOCALAPPDATA") + '\osu!'
        self.curDirLabel = tk.Label(self.fileFrame, text=self.osuDir)
        self.curDirLabel.pack()

        self.osuDirButton = tk.Button(
            self.fileFrame, text="Select Your osu! Directory", command=self.selectOsuDir)
        self.osuDirButton.pack()

        self.backupDir = os.getcwd()
        self.backupFile = self.backupDir + '\osuSongs.bak'
        self.backupDirLabel = tk.Label(self.fileFrame, text=self.backupFile)
        self.backupDirLabel.pack(pady=5)

        self.backupDirButton = tk.Button(
            self.fileFrame, text="Select Your Backup Directory", command=self.selectBackupDir)
        self.backupDirButton.pack()

        tk.Button(self.fileFrame, text='View currently backed up songs',
                  command=self.viewBackups).pack()
        self.backupStatusField = tk.Text(self.fileFrame, height=15, width=50)
        self.backupStatusField.pack()

        self.fileFrame.pack(pady=20)

        self.progressBar = Progressbar(
            self.root, orient='horizontal', length=400, mode='determinate')
        self.progressBar.pack()

        self.genBackupButton = tk.Button(
            self.root, text='Generate Backup File', command=self.generateBackup)
        self.genBackupButton.pack()

        self.downloadButton = tk.Button(
            self.root, text='Download from backup', command=self.handleDownload)
        self.downloadButton.pack()

        self.root.mainloop()

    def selectOsuDir(self) -> None:
        self.osuDir = filedialog.askdirectory()
        self.curDirLabel.config(text=self.osuDir)

    def selectBackupDir(self) -> None:
        self.backupDir = filedialog.askdirectory()
        self.backupFile = self.backupDir + '/osuSongs.bak'
        self.backupDirLabel.config(text=self.backupFile)

    def viewBackups(self) -> None:
        if not os.path.isfile(self.backupFile):
            messagebox.showerror(
                title='No backup found', message=f'No backup file found at {self.backupFile}')
            return
        with open(self.backupFile, 'rb') as infile:
            self.beatmapStatus = pickle.load(infile)

        self.backupStatusField.insert(
            '1.0', chars=json.dumps(self.beatmapStatus, indent=2))

    def generateBackup(self) -> None:
        if not os.path.exists(self.osuDir + '/Songs'):
            print('Songs folder not found, possibly incorrect osu! directory')
            return

        if not os.path.isfile(self.backupFile):
            backupAlert = messagebox.askyesno(
                title='No backup file detected', message='No backup file found at the backup location, create a new file?')
            if not backupAlert:
                return
            with open(self.backupFile, 'wb') as outfile:
                pickle.dump({}, outfile)

        songScan = os.scandir(self.osuDir + '/Songs')

        with open(self.backupFile, 'rb') as infile:
            self.beatmapStatus = pickle.load(infile)
        print(json.dumps(self.beatmapStatus, indent=2))

        for song in songScan:
            if not song.is_dir():
                continue

            beatmapId = re.match(r'^\d+', song.name)

            if beatmapId and beatmapId[0] in self.beatmapStatus or song.name in self.beatmapStatus:
                continue

            if not beatmapId:
                print('FAILED: ' + song.name)
                self.beatmapStatus[song.name] = {
                    'status': 'no_id'}
                continue
            beatmapId = beatmapId[0]
            print('New beatmap entry added')
            self.beatmapStatus[str(beatmapId)] = {
                'status': 'needs_data'}

        self.updateBeatmapStatus()

        numUnprocessedBeatmaps = len(
            [b for b in self.beatmapStatus if self.beatmapStatus[b]['status'] == 'needs_data'])

        def fetchBeatmap():
            self.progressBar['value'] = 0
            self.root.update_idletasks()
            for beatmap in self.beatmapStatus:
                if not self.beatmapStatus[beatmap]['status'] == 'needs_data':
                    continue

                print(f'Fetching data for {beatmap}')
                self.getBeatmap(beatmap)
                self.progressBar['value'] = (
                    self.progressBar['value'] + (1 / numUnprocessedBeatmaps) * 100)
                self.root.update_idletasks()

        threading.Thread(target=fetchBeatmap).start()

    def updateBeatmapStatus(self):
        with open(self.backupFile, 'wb') as outfile:
            pickle.dump(self.beatmapStatus, outfile)

    def getBeatmap(self, beatmapId) -> dict:
        beatmapURL = f'https://api.chimu.moe/v1/map/{beatmapId}'
        for _ in range(5):
            try:
                res = requests.get(url=beatmapURL).json()
                self.beatmapStatus[beatmapId]['downloadURL'] = f"https://api.chimu.moe{res['DownloadPath']}"
                self.beatmapStatus[beatmapId]['status'] = 'download_ready'
                self.updateBeatmapStatus()
                break
            except requests.exceptions.Timeout:
                pass
            except requests.exceptions.RequestException as e:
                print(f'Error retrieving beatmap information on {beatmapId}')
                return
            except KeyError:
                print(f'Parent Set ID not found for {beatmapId}')
                return
        else:
            raise SystemExit('Repeated Timeouts...')

    def handleDownload(self):
        downloadURLs = set()

        if not os.path.isfile(self.backupFile):
            messagebox.showerror(
                title='No backup found', message=f'No backup file found at {self.backupFile}')
            return

        with open(self.backupFile, 'rb') as infile:
            self.beatmapStatus = pickle.load(infile)

        for beatmap in self.beatmapStatus:
            if self.beatmapStatus[beatmap].get('downloadURL') == None:
                continue
            downloadURLs.add(self.beatmapStatus[beatmap]['downloadURL'])

        self.downloadWindow = tk.Toplevel(self.root)
        self.downloadWindow.title('Downloading...')
        self.downloadWindow.geometry('500x500')
        self.downloadWindow.protocol('WM_DELETE_WINDOW', lambda: None)
        tk.Label(self.downloadWindow,
                 text='Downloading Beatmaps', font=('Arial', 16))

        # self.downloadWithProgress(20125)

        def startParallelDownload():
            self.downloadButton['state'] = 'disabled'
            for result in tp(mp.cpu_count()).imap_unordered(self.downloadBeatmapSet, downloadURLs):
                print(result)
            self.downloadWindow.destroy()
            self.downloadButton.update()
            self.downloadButton['state'] = 'normal'

        threading.Thread(target=startParallelDownload).start()

    def dummyDownload(self, beatmapSets):
        if random.randint(1, 6) == 1:
            return 'error occurred lol'

        tempbar = Progressbar(self.downloadWindow, length=250,
                              mode='determinate', orient='horizontal')
        tempbar.pack()

        for i, _ in enumerate(range(100)):
            time.sleep(random.randint(1, 10) * 0.01)
            tempbar['value'] = i + 1
            self.downloadWindow.update_idletasks()
        tempbar.pack_forget()

        self.downloadButton.update()

        return beatmapSets

    def downloadWithProgress(self, beatmapSetId):
        downloadProgress = Progressbar(
            self.root, length=450, mode='determinate', orient='horizontal')
        downloadProgress.pack()
        self.downloadButton['state'] = 'disabled'

        with requests.get(f'https://storage.ripple.moe/d/{beatmapSetId}', stream=True) as r:
            with open(os.path.join(self.backupDir, f'{beatmapSetId}.osz'), 'wb') as downloadfile:
                totalSize = int(r.headers.get('Content-Length'))
                for i, data in enumerate(r.iter_content(chunk_size=1024)):
                    downloadfile.write(data)
                    downloadProgress['value'] = i * 1024 / totalSize * 100
                    self.root.update_idletasks()

        downloadProgress.pack_forget()
        self.downloadButton.update()
        self.downloadButton['state'] = 'normal'

    def downloadBeatmapSet(self, beatmapSetId):
        downloadFrame = tk.Frame(self.downloadWindow)
        downloadFrame.pack(pady=10)

        downloadLabel = tk.Label(downloadFrame, text=f'{beatmapSetId}:')
        downloadLabel.grid(row=0, column=0)

        downloadProgress = Progressbar(
            downloadFrame, length=350, orient='horizontal', mode='determinate')
        downloadProgress.grid(row=0, column=1)

        for i, _ in enumerate(range(100)):
            time.sleep(random.randint(1, 10) * 0.01)
            downloadProgress['value'] = i + 1
            self.downloadWindow.update_idletasks()
        downloadFrame.pack_forget()

        return {beatmapSetId: 'success'}


if __name__ == "__main__":
    MainGUI()
