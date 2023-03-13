# Partial Modified Code from Package file-downloader "https://pypi.org/project/file-downloader/"

import logging
import os
import traceback
from io import BufferedReader
from math import floor
from threading import Event, Thread
from time import sleep, time
from typing import Callable, Dict

import requests
from requests import Response

from src.utils import cleanup_prev_line, progress_bar


class loading(Thread):
    exit_signal: Event
    msg: str

    def __init__(self, msg: str = "Loading", dot_limit: int = 3):
        self.exit_signal = Event()
        self.msg = msg
        self.dot_limit = dot_limit
        Thread.__init__(self=self)

    def stop(self):
        self.exit_signal.set()

    def run(self):
        col = len(self.msg) + self.dot_limit
        while not self.exit_signal.is_set():
            dot_num = int(floor(time()) % self.dot_limit) + 1
            print(self.msg + "." * dot_num)
            sleep(1)
            print("\033[A{}\033[A".format(" " * col))


class downloader:
    url: str  # path to download target file
    cookies: Dict[str, str]
    store_path: str  # path to store the downloaded target file
    file_name: str  # downloaded target file name fetched from url
    socket_timeout: float  # time to stop and retry after x secs
    retry_limit: int  # limit of num of retries

    retry_num: int  # num of retries have occurred
    progress: float  # progress of the download
    content_length: int  # target file total length
    fetched_length: int  # downloaded target file length
    downloaded: bool  # whether the file is already downloaded

    params: Dict
    loading_thread: loading

    def __init__(
        self,
        url: str,
        cookies: Dict[str, str],
        store_path: str = "",
        socket_timeout: float = 120.0,
        retry_limit: int = 5,
    ):
        self.url = url
        self.cookies = cookies
        # self.cookies = dict_to_str(cookies)
        self.store_path = store_path
        self.socket_timeout = socket_timeout
        self.retry_limit = retry_limit
        self.retry_num = 0
        self.progress = 0
        self.fetched_length = 0
        self.downloaded = False
        self.loading_thread = None
        self.params = {
            "url": self.url,
            "timeout": self.socket_timeout,
            "cookies": self.cookies,
            "allow_redirects": True,
        }

        # self.start_loading_thread()
        # sleep(5)
        # self.stop_loading_thread()
        # return
        if not self.is_url_file_exists():
            raise FileNotFoundError("Error! File is not found on the target url!")

        self.content_length = self.get_content_length()

        self.get_local_file_size()

    def stop_loading_thread(self):
        if self.loading_thread is not None:
            self.loading_thread.stop()
            self.loading_thread.join(1)

    def start_loading_thread(self, loading_str: str = None):
        if self.loading_thread is not None:
            self.stop_loading_thread()
        if loading_str is None:
            loading_str = f"Connecting to Resource: {self.file_name}"
        self.loading_thread = loading(msg=loading_str)
        self.loading_thread.daemon = True
        self.loading_thread.start()

    def is_url_file_exists(self):
        """
        Checks to see if the target file exists in the target url
        """
        try:
            res = requests.head(**self.params)
            # if self.store_path is None:
            self.file_name = res.url.split("?")[0].split("/")[-1]
            # self.store_path += self.file_name
        except Exception:
            return False
        return True

    def get_content_length(self) -> int:
        """
        Retrieve content-length from target url
        """
        try:
            res: Response = requests.head(**self.params)
            size = res.headers.get("content-length")
            if size is None or int(size) == 0:
                raise ConnectionError(
                    "Error! File is not found on the target url or File has no content!"
                )
            self.content_length = int(size)
            return self.content_length
        except ConnectionError:
            raise
        except Exception as e:
            raise ConnectionError(
                f"Error! File is not found on the target url!\n Detail: {e}"
            )

    def get_local_file_size(self) -> int:
        """
        Retrieve file size of local file
        """
        if not os.path.isfile(self.store_path):
            return 0
        self.fetched_length = os.stat(self.store_path).st_size

        return self.fetched_length

    def __retry(self):
        """
        auto-resumes up to self.retries
        """
        if self.retry_limit > self.retry_num:
            self.retry_num += 1
            if self.get_local_file_size() != self.content_length:
                self.resume()
        else:
            raise ConnectionError(
                "Error! Maximum Number of Retry Reached! Unable to Download Target File!"
            )

    def __download_file(
        self, url_obj: Response, file_obj: BufferedReader, call_back: Callable = None
    ):
        """
        Starts the download loop
        """
        try:
            for chunk in url_obj.iter_content(chunk_size=8192):
                try:
                    # filter out keep-alive new chunks
                    if not chunk:
                        continue
                    file_obj.write(chunk)
                    self.fetched_length += len(chunk)

                    print_out, ending = progress_bar(
                        current=self.fetched_length,
                        total=self.content_length,
                        string_in_front=f"Extracting File: {self.file_name:>30}",
                    )
                    print(print_out, end=ending)
                except Exception:
                    traceback.print_exc()
                    self.__retry()
            file_obj.close()
            self.downloaded = True
            # logging.info(f"File Downloaded: {self.store_path}")
            # cleanup_prev_line(1)
            print(f"File Downloaded: '{self.store_path}'")
            if call_back:
                call_back(cursize=self.fetched_length)
        except Exception:
            traceback.print_exc()

    def download(self, download_path: str = None, call_back: Callable = None):
        """
        Starts the file download

        Reset previous download progress if needed
        """
        if download_path != None:
            self.store_path = download_path

        self.start_loading_thread()
        self.retry_num = 0
        self.progress = 0
        self.fetched_length = 0
        try:
            with open(self.store_path, "wb") as file_obj:
                res_obj: Response = requests.get(stream=True, **self.params)
                self.stop_loading_thread()
                self.__download_file(
                    url_obj=res_obj, file_obj=file_obj, call_back=call_back
                )
                return True
        except Exception as e:
            self.stop_loading_thread()
            logging.warning(f"Error! {e}")
            return False

    def duplicate(self, new_file_path: str):
        if not self.downloaded:
            self.download()

        try:
            with open(self.store_path, "rb") as file_obj:
                with open(new_file_path, "wb") as new_file_obj:
                    new_file_obj.write(file_obj.read())
            return True
        except Exception as e:
            logging.warning(f"Error! {e}")
            return False

    def resume(self, restart: bool = False, call_back: Callable = None):
        """
        Starts the file download

        Reset previous download progress if needed
        """
        self.start_loading_thread()
        self.fetched_length = self.get_local_file_size()
        if restart:
            return self.download()
        elif self.fetched_length >= self.content_length:
            logging.warning(
                "Local File Larger than Cloud File. Potential Error Found, Redownloading..."
            )
            return self.download()
        elif self.fetched_length == 0:
            return self.download()

        try:
            with open(self.store_path, "a+b") as file_obj:
                header = {"Range": f"bytes={self.fetched_length}-{self.content_length}"}
                res_obj: Response = requests.get(
                    headers=header, stream=True, **self.params
                )
                self.stop_loading_thread()
                self.__download_file(
                    url_obj=res_obj, file_obj=file_obj, call_back=call_back
                )
                return True
        except Exception as e:
            self.stop_loading_thread()
            logging.warning(f"Error! {e}")
            return False


# url = "https://umass.moonami.com/mod/resource/view.php?id=2038785"
# url = "https://umass.moonami.com/pluginfile.php/2636884/mod_resource/content/1/00-policy.pdf?forcedownload=1"
# url = "https://umass.moonami.com/pluginfile.php/2491706/mod_resource/content/2/01-Intro.pdf?forcedownload=1"
# url = "https://umass.moonami.com/mod/resource/view.php?id=1916050"
# res: Response = requests.head(url, cookies=retreive_cookies(target_website="umass.moonami.com"), allow_redirects=True)
# print(res.url)
# print(res.headers)
# dl = downloader(
#     url=url,
#     store_path="files/sample_file.pdf",
#     cookies=retreive_cookies(target_website="umass.moonami.com"),
# )
# # dl.download()