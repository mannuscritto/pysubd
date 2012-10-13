#!/usr/bin/python
# -*- coding: utf-8 -*-

from PyQt4 import QtCore
import os
import traceback
from opensubs import Site
import utils
from PyQt4.QtCore import QObject, pyqtSlot

communicator = utils.communicator


class SubtitleDownload(QtCore.QThread):

    '''Traverses a directory and all subdirectories and downloads
        the best available subtitles.'''

    queue = {}
    queue['Addic7ed'] = []
    queue['OpenSubtitles'] = {}

    def __init__(self, parent=None):
        QtCore.QThread.__init__(self, parent)

        self.not_found = []
        communicator.no_sub_found.connect(self.append_to_not_found)
        self.logger = utils.logger
        self.sites = {'Addic7ed': Site().create('Addic7ed'),
                      'OpenSubtitles': Site().create('OpenSubtitles')}

    def init(self, videos_pathlist, lang):
        self.videos_pathlist = videos_pathlist
        self.lang = lang
        self.start()

    def stopTask(self):
        self.cancelled = True
        for (site_name, site_instance) in self.sites.iteritems():
                site_instance.stopTask()

    def run(self):
        self.cancelled = False
        self.videofiles_queue = {}
        utils.communicator.updategui.emit('Searching for video files...'
                )
        self.check_and_add()
        self.process_queues()
        self.print_not_found()
        utils.communicator.updategui.emit('Done...')
        utils.communicator.all_download_complete.emit(self.videos_pathlist)
        
    def check_and_add(self):
        for path in self.videos_pathlist:
            if os.path.isfile(path):
                if utils.is_video_file(path):
                    self.add_to_processing_queues(os.path.basename(path),
                            os.path.dirname(path))
            else:
                for (root, _, files) in os.walk(path):
                    for filename in files:
                        if not self.cancelled:
                            if utils.is_video_file(filename):
                                self.add_to_processing_queues(filename,
                                        root)
                        else:
                            return

    def add_to_processing_queues(self, filename, parentdir):
        utils.communicator.updategui.emit('Found: ' + filename)
        utils.communicator.found_video_file.emit(filename)

        filehash = utils.calc_file_hash(os.path.join(parentdir,
                filename))
        filesize = os.path.getsize(os.path.join(parentdir, filename))
        save_to_path = os.path.join(parentdir,
                                    os.path.splitext(filename)[0]
                                    + '.srt')

        if utils.check_tvshow(filename):
            self.queue['Addic7ed'].append({'file_name': filename,
                    'save_subs_to': save_to_path,
                    'moviehash':filehash,
                    'moviebytesize': str(filesize)})
        else:
            self.queue['OpenSubtitles'][filehash] = {
                    'file_name': filename,
                    'moviehash':filehash,
                    'save_subs_to': save_to_path,
                    'moviebytesize': str(filesize)}

    def process_queues(self):
        for (site, files) in sorted(self.queue.iteritems()):
            if files:
                try:
                    self.sites[site].process(files, self.lang)
                    self.sites[site].wait()
                except utils.NoInternetConnectionFound:
                    utils.communicator.updategui.emit('No active Internet connection found. Kindly check and try again.'
                            )
                    utils.communicator.all_download_complete.emit(self.videos_pathlist)
                    return
                except utils.IncorrectResponseRecieved:
                    utils.communicator.updategui.emit('Exception: IncorrectResponseRecieved'
                            )
                except UserWarning, uw:
                    utils.communicator.updategui.emit(uw)
                except utils.DailyDownloadLimitExceeded:
                    utils.communicator.updategui.emit('You have reached your daily download limit for Addic7ed.com')
                    continue
                except:
                    utils.communicator.updategui.emit('Following exception occured:\n%s'
                             % traceback.format_exc())    

    @pyqtSlot(object)
    def append_to_not_found(self, filename):
        self.not_found.append(filename)

    def print_not_found(self):
        self.not_found.sort(key=str.lower)
        for file_name in self.not_found:
            utils.communicator.updategui.emit('No subtitles found for: ' + file_name)