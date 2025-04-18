import json
import logging
import time
import traceback

import requests
from urllib3 import Retry
from itertools import chain
from .misc import ThreadPool
from requests.adapters import HTTPAdapter
from .constants import VERSION, VERSION_CHECK_API
from aqt import QObject, pyqtSignal, QThread, mw
import os
from tempfile import gettempdir


class VersionCheckWorker(QObject):
    haveNewVersion = pyqtSignal(str, str)
    finished = pyqtSignal()
    start = pyqtSignal()
    logger = logging.getLogger('dict2Anki.workers.UpdateCheckWorker')

    def run(self):
        try:
            self.logger.info('检查新版本')
            rsp = requests.get(VERSION_CHECK_API, timeout=20).json()
            version = rsp['tag_name']
            changeLog = rsp['body']
            if version != VERSION:
                self.logger.info(f'检查到新版本:{version}--{changeLog.strip()}')
                self.haveNewVersion.emit(version.strip(), changeLog.strip())
            else:
                self.logger.info(f'当前为最新版本:{VERSION}')
        except Exception as e:
            self.logger.error(f'版本检查失败{e}')

        finally:
            self.finished.emit()


class LoginStateCheckWorker(QObject):
    start = pyqtSignal()
    logSuccess = pyqtSignal(str)
    logFailed = pyqtSignal()

    def __init__(self, checkFn, cookie):
        super().__init__()
        self.checkFn = checkFn
        self.cookie = cookie

    def run(self):
        loginState = self.checkFn(self.cookie)
        if loginState:
            self.logSuccess.emit(json.dumps(self.cookie))
        else:
            self.logFailed.emit()


class RemoteWordFetchingWorker(QObject):
    start = pyqtSignal()
    tick = pyqtSignal()
    setProgress = pyqtSignal(int)
    done = pyqtSignal()
    doneThisGroup = pyqtSignal(list)
    logger = logging.getLogger('dict2Anki.workers.RemoteWordFetchingWorker')

    def __init__(self, selectedDict, selectedGroups: [tuple]):
        super().__init__()
        self.selectedDict = selectedDict
        self.selectedGroups = selectedGroups

    def run(self):
        currentThread = QThread.currentThread()

        def _pull(*args):
            if currentThread.isInterruptionRequested():
                return
            wordPerPage = self.selectedDict.getWordsByPage(*args)
            self.tick.emit()
            return wordPerPage

        for groupName, groupId in self.selectedGroups:
            totalPage = self.selectedDict.getTotalPage(groupName, groupId)
            self.setProgress.emit(totalPage)
            with ThreadPool(max_workers=3) as executor:
                for i in range(totalPage):
                    executor.submit(_pull, i, groupName, groupId)
            remoteWordList = list(chain(*[ft for ft in executor.result]))
            self.doneThisGroup.emit(remoteWordList)

        self.done.emit()


class QueryWorker(QObject):
    start = pyqtSignal()
    tick = pyqtSignal()
    thisRowDone = pyqtSignal(int, dict)
    thisRowFailed = pyqtSignal(int)
    allQueryDone = pyqtSignal()
    logger = logging.getLogger('dict2Anki.workers.QueryWorker')

    def __init__(self, wordList: [dict], api):
        super().__init__()
        self.wordList = wordList
        self.api = api

    def run(self):
        currentThread = QThread.currentThread()

        def _query(word, row):
            if currentThread.isInterruptionRequested():
                return
            queryResult = self.api.query(word)
            if queryResult:
                # self.logger.info(f'查询成功: {word} -- {queryResult}')
                self.thisRowDone.emit(row, queryResult)
            else:
                self.logger.warning(f'查询失败: {word}')
                self.thisRowFailed.emit(row)

            self.tick.emit()
            return queryResult

        with ThreadPool(max_workers=1) as executor:
            count = 0
            for word in self.wordList:
                count += 1
                # 若果查询次数过多,则等待
                if count % 10 == 0:
                    time.sleep(1)
                executor.submit(_query, word['term'], word['row'])

        self.allQueryDone.emit()


class AudioDownloadWorker(QObject):
    start = pyqtSignal()
    tick = pyqtSignal()
    done = pyqtSignal()
    logger = logging.getLogger('dict2Anki.workers.AudioDownloadWorker')
    retries = Retry(total=5, backoff_factor=3, status_forcelist=[500, 502, 503, 504])
    session = requests.Session()
    session.mount('http://', HTTPAdapter(max_retries=retries))
    session.mount('https://', HTTPAdapter(max_retries=retries))

    def __init__(self, audios: [tuple]):
        super().__init__()
        self.audios = audios

    def run(self):
        currentThread = QThread.currentThread()

        def __download(file_name, url, retry=True):
            try:
                if currentThread.isInterruptionRequested():
                    return

                # Anki媒体文件地址
                media_dir = mw.col.media.dir()

                # 如果文件存在, 则跳过
                if mw.col.media.have(media_dir + "/" + file_name):
                    self.logger.info(f'{file_name} 已存在')
                    return

                # fix macos can't create file, so create file in temp dir
                filePath = gettempdir() + "/anki_temp/" + file_name
                r = self.session.get(url, stream=True)
                # 判断响应参数
                if r.status_code != 200:
                    self.logger.warning(f'下载{filePath}:{url}失败: {r.status_code}')
                    time.sleep(60)
                    return

                # 检查Content-Type头部判断是否是音频
                content_type = r.headers.get('Content-Type', '').lower()

                if content_type.startswith('audio/') is False:
                    self.logger.warning(f'{file_name} 不是音频文件')
                    data = r.json()
                    if data.get("code") == 403:
                        self.logger.warning(f'{file_name} 访问被禁')
                        time.sleep(60)
                    return

                # 处理音频文件
                with open(filePath, 'wb') as f:
                    for chunk in r.iter_content(chunk_size=1024):
                        if chunk:
                            f.write(chunk)
                    # self.logger.info(f'{fileName} 下载完成')

                # 获取服务器端文件大小（需服务器支持Content-Length）
                file_size = int(r.headers.get('Content-Length', 0))
                # 下载完成后检查本地文件大小
                if os.path.getsize(filePath) != file_size:
                    os.remove(filePath)
                    self.logger.warning(f"{file_name} 可能未完整下载")
                    return

                mw.col.media.add_file(filePath)
                os.remove(filePath)
                # self.logger.info(f"{fileName} 添加到媒体库,临时文件已删除")
            except requests.exceptions.RetryError:
                self.logger.warning(f'下载{file_name}:{url}重试失败')
                if retry:
                    # 如果url中存在type=1, 则替换为type=2
                    # 如果url中存在type=2, 则替换为type=1
                    if 'type=1' in url:
                        url = url.replace('type=1', 'type=2')
                    elif 'type=2' in url:
                        url = url.replace('type=2', 'type=1')
                    # 递归调用一次之后不再重试
                    self.logger.info(f'递归调用下载{file_name}:{url}')
                    __download(file_name, url, False)

            except Exception as e:
                self.logger.warning(f'下载{file_name}:{url}异常: {e}')
                traceback.print_exc()
            finally:
                self.tick.emit()

        with ThreadPool(max_workers=3) as executor:
            count = 0
            for fileName, url in self.audios:
                count += 1
                # 若果下载次数过多,则等待
                if count % 10 == 0:
                    time.sleep(1)
                executor.submit(__download, fileName, url)
        self.done.emit()
        self.logger.info('下载完成')
