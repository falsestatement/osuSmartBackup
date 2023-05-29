import tkinter as tk
import os
import re
import requests
import json
import pickle
import time
import threading
import random
import shutil
import ctypes
import sys
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
                self.saveUnreachable(os.path.join(
                    self.osuDir.replace('/', '\\'), 'Songs', song.name))
                continue
            beatmapId = beatmapId[0]
            print('New beatmap entry added')
            self.beatmapStatus[str(beatmapId)] = {
                'status': 'needs_data', 'filePath': os.path.join(self.osuDir.replace('/', '\\'), 'Songs', song.name)}

        self.updateBeatmapStatus()

        def fetchBeatmapData():
            unprocessedBeatmaps = [
                b for b in self.beatmapStatus if self.beatmapStatus[b]['status'] == 'needs_data']
            self.progressBar['value'] = 0
            self.root.update_idletasks()

            def processBeatmap(beatmapId):
                print(f'Fetching data for {beatmapId}')
                self.getBeatmap(beatmapId)
                return beatmapId

            for progress, _ in enumerate(tp(mp.cpu_count()).imap_unordered(processBeatmap, unprocessedBeatmaps), 1):
                self.progressBar['value'] = progress * \
                    100 / len(unprocessedBeatmaps)
                self.root.update_idletasks()

        threading.Thread(target=fetchBeatmapData).start()

    def updateBeatmapStatus(self):
        with open(self.backupFile, 'wb') as outfile:
            pickle.dump(self.beatmapStatus, outfile)

    def saveUnreachable(self, filePath):
        fileName = re.search(
            r'[^\\]+$', filePath)[0]
        backupPath = os.path.join(self.backupDir.replace(
            '/', '\\'), 'Nonmirrored_Backup')
        backupFile = os.path.join(backupPath, fileName)

        if not os.path.exists(backupPath):
            os.mkdir(backupPath)
        try:
            shutil.copytree(
                filePath, backupFile)
        except OSError as e:
            print(e)

    def getBeatmap(self, beatmapId) -> dict:
        beatmapURL = f'https://api.chimu.moe/v1/map/{beatmapId}'
        beatmapSetURL = f'https://api.chimu.moe/v1/set/{beatmapId}'

        for _ in range(5):
            try:
                res = requests.get(url=beatmapURL).json()
                if res.get('DownloadPath') == None:
                    res = requests.get(url=beatmapSetURL).json()[
                        'ChildrenBeatmaps'][0]

                self.beatmapStatus[beatmapId][
                    'downloadURL'] = f"https://api.chimu.moe{res['DownloadPath']}"
                self.beatmapStatus[beatmapId]['status'] = 'download_ready'
                self.updateBeatmapStatus()
                return
            except requests.exceptions.Timeout:
                continue
            except requests.exceptions.RequestException as e:
                print(f'Error retrieving beatmap information on {beatmapId}')
                self.saveUnreachable(self.beatmapStatus[beatmapId]['filePath'])
                return
            except KeyError:
                print(f'Parent Set ID not found for {beatmapId}')
                self.saveUnreachable(self.beatmapStatus[beatmapId]['filePath'])
                return
        else:
            self.saveUnreachable(self.beatmapStatus[beatmapId]['filePath'])
            print('Unreachable, retried 5 times')

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

        totalProgressFrame = tk.Frame(self.downloadWindow)
        totalProgressFrame.pack(pady=5)
        tk.Label(totalProgressFrame, text='Total Progress').grid(
            row=0, column=0)
        totalProgressBar = Progressbar(
            totalProgressFrame, length=300, orient='horizontal', mode='determinate')
        totalProgressBar.grid(row=0, column=1, padx=5)

        # self.downloadWithProgress(20125)

        def startParallelDownload():
            self.downloadButton['state'] = 'disabled'
            if not os.path.exists(self.backupDir + '/Beatmap_Downloads'):
                os.mkdir(self.backupDir + '/Beatmap_Downloads')

            for totalProgress, result in enumerate(tp(mp.cpu_count()).imap_unordered(self.downloadBeatmapSet, downloadURLs), 1):
                totalProgressBar['value'] = totalProgress * \
                    100 / len(downloadURLs)
                totalProgressFrame.update_idletasks()
                print(result)
            self.downloadWindow.destroy()
            self.downloadButton.update()
            self.downloadButton['state'] = 'normal'

        threading.Thread(target=startParallelDownload).start()

    def downloadBeatmapSet(self, downloadUrl):
        fileName = re.search(r"[^/]+$", downloadUrl)[0]
        
        downloadFrame = tk.Frame(self.downloadWindow)
        downloadFrame.pack(pady=5)

        downloadLabel = tk.Label(downloadFrame, text=f'{downloadUrl}:')
        downloadLabel.grid(row=0, column=0)

        downloadProgress = Progressbar(
            downloadFrame, length=350, orient='horizontal', mode='determinate')
        downloadProgress.grid(row=0, column=1)

        try:
            with requests.get(downloadUrl, stream=True) as r:
                with open(os.path.join(self.backupDir, f'Beatmap_Downloads/{fileName}.osz'), 'wb') as downloadfile:
                    totalSize = int(r.headers.get('Content-Length'))
                    for i, data in enumerate(r.iter_content(chunk_size=1024)):
                        downloadfile.write(data)
                        downloadProgress['value'] = i * 1024 / totalSize * 100
                        downloadFrame.update_idletasks()
        except Exception as e:
            print(e)
            return {downloadUrl: 'failed to download'}

        downloadFrame.pack_forget()

        return {downloadUrl: 'success'}


if __name__ == "__main__":
    def is_admin():
        try:
            return ctypes.windll.shell32.IsUserAnAdmin()
        except:
            return False

    if is_admin():
        MainGUI()
    else:
        # Re-run the program with admin rights
        ctypes.windll.shell32.ShellExecuteW(
            None, "runas", sys.executable, " ".join(sys.argv), None, 1)
