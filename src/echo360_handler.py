# https://echo360.org/lesson/G_60d13195-1ffd-4686-855d-d8bf004c89fd_a17b816d-a847-4a00-9e77-97532c1b0fa5_2023-02-07T13:00:00.000_2023-02-07T14:15:00.000/classroom#sortDirection=desc
# https://content.echo360.org/0000.c4a29c15-265c-404e-9ed7-17f518602cf7/e6da5055-1fed-4f31-aea3-024cb7cc8d6c/1/hd1.mp4
# https://content.echo360.org/0000.c4a29c15-265c-404e-9ed7-17f518602cf7/e6da5055-1fed-4f31-aea3-024cb7cc8d6c/1/hd2.mp4
# https://thumbnails.echo360.org/0000.c4a29c15-265c-404e-9ed7-17f518602cf7/e6da5055-1fed-4f31-aea3-024cb7cc8d6c/1/poster1.jpg
import json
from pathlib import PurePosixPath
from queue import Queue
from threading import Event, Thread
from time import sleep
from typing import Callable, Dict, List, Tuple
from urllib.parse import unquote, urlparse

import requests
from bs4 import BeautifulSoup, Tag
from selenium import webdriver
from selenium.webdriver.remote.webdriver import WebDriver as WebDriverClass


class loading(Thread):
    signs = ["—", "\\", "|", "/"]
    sign_index: int = 0
    exit_signal: Event
    message_queue: Queue
    already_paused: bool

    def __init__(
        self, message_queue: Queue, is_pause: bool = False, keep_log: bool = False
    ):
        self.exit_signal = Event()
        self.pause_signal = Event()
        self.keep_log = keep_log
        self.already_paused = False
        self.pause(is_pause, True)
        self.message_queue = message_queue
        self.prev_message = (None, False)
        Thread.__init__(self=self)

    def stop(self):
        self.pause_signal.set()
        self.exit_signal.set()

    @property
    def is_paused(self):
        return self.pause_signal.is_set()

    def pause(self, is_pause: bool = True, is_init: bool = False):
        if is_pause:
            self.pause_signal.set()
            if not is_init and not self.keep_log:
                print("\033[F\033[1G\033[K", end="\r")
        else:
            self.already_paused = False
            self.pause_signal.clear()

    def print_message(self, message_tuple: Tuple[str, bool]):
        # col = len(message) + self.dot_limit
        # sign_index = int(floor(time()) / 0.5) % len(self.signs)
        # if with_new_line:
        #     header = "\n"
        message, _ = message_tuple
        print(message + " " + self.signs[self.sign_index])
        self.sign_index = (self.sign_index + 1) % len(self.signs)
        sleep(0.5)
        # if self.pause_signal.set() and not self.already_paused:
        #     self.already_paused = True
        #     print("\n")
        # else:
        # if not with_new_line:
        print("\033[F\033[1G\033[K", end="\r")
        # print("\033[A{}\033[A".format(" " * col))

    def run(self):
        while not self.exit_signal.is_set():
            if self.pause_signal.is_set() and self.already_paused:
                continue
            curr_message = ""
            if self.message_queue.empty():
                curr_message = self.prev_message
            else:
                curr_message = self.message_queue.get()
                if curr_message[1] and self.prev_message[0] is not None:
                    print(self.prev_message[0])
                self.prev_message = curr_message
            if self.prev_message[0] is None: continue
            self.print_message(curr_message)
        print(self.prev_message[0])


def cleanup_prev_line(num_lines: int = 1) -> None:
    if num_lines < 1:
        return
    if num_lines == 1:
        print("\033[K", end="\r")
        return
    for i in range(num_lines):
        print("\033[F\033[1G\033[K", end="")
    print("\033[K", end="\r")


class Echo360Extractor:
    base_url: str = "https://echo360.org/"
    video_base_url: str = "https://echo360.org/lesson/{}/classroom#sortDirection=desc"
    video_download_url_head: str = "https://content.echo360.org/"
    course_url: str
    course_id: str
    cookies: List[Dict[str, str]]
    driver: WebDriverClass
    video_info: List[Dict]
    json_store_path: str
    display_info_queue: Queue
    display_info_thread: loading

    def __init__(self, json_store_path: str = "./echo360.json"):
        self.json_store_path = json_store_path
        self.driver = None
        self.video_info = []
        self.cookies = []
        self.display_info_queue = None
        self.display_info_thread = None
        

    def __enter__(self):
        if self.display_info_thread is not None:
            self.display_info_thread.join(1)
            self.display_info_thread = None
        if self.display_info_queue is not None:
            while not self.display_info_queue.empty():
                self.display_info_queue.get()
        else:
            self.display_info_queue = Queue()
        self.display_info_thread = loading(self.display_info_queue, True, True)
        self.display_info_thread.daemon = True
        self.display_info_thread.start()        
        return self

    def __exit__(self, *args, **kwargs):
        if self.display_info_queue is not None:
            while not self.display_info_queue.empty():
                continue
        if self.display_info_thread is not None:
            self.display_info_thread.stop()
            self.display_info_thread.join(1)
            self.display_info_thread = None

        with open(self.json_store_path, "w", encoding="utf-8") as f:
            f.write(json.dumps(self.video_info, indent=4))

    def setup(self, redirect_url: str, cookie: Dict):
        self.fetch_echo360(redirect_url, cookie)
        self.setup_driver()

    def display_message(
        self, is_show: bool = True, message: str = "", with_new_line: bool = True
    ) -> None:
        if self.display_info_thread is None:
            return
        if not is_show:
            if not self.display_info_thread.is_paused:
                self.display_info_thread.pause(True)
        else:
            self.display_info_queue.put((message, with_new_line))
            if self.display_info_thread.is_paused:
                self.display_info_thread.pause(False)

    def fetch_url_part(self, target_path: str, index: int) -> str:
        components = PurePosixPath(unquote(urlparse(target_path).path)).parts
        if len(components) < index + 1:
            return ""
        return components[index]

    def fetch_echo360(self, target_url: str, data: Dict) -> None:
        self.display_message(message="[Ongoing] Echo360 Course Page")
        # fetch echo360 course url
        tmp = requests.post(url=target_url, data=data, allow_redirects=True)
        self.course_url = tmp.request.url
        self.course_id = self.fetch_url_part(self.course_url, 2)
        self.display_message(message=f"[Ongoing] Echo360 Course Page {self.course_id}", with_new_line=False)

        # retreive valid cookie from tmp request
        cookies_str = tmp.request.headers.get("Cookie").split(";")
        for cookie_str in cookies_str:
            # print(cookie_str)
            name = cookie_str.lstrip(" ").split("=")[0]
            value = cookie_str.lstrip(" ").lstrip(name + "=")
            if name == "PLAY_SESSION":
                curr_cookie = {
                    "name": name,
                    "value": value,
                    "domain": "echo360.org",
                    "path": "/",
                    "httpOnly": True,
                    "sameSite": "None",
                }
            else:
                curr_cookie = {
                    "name": name,
                    "value": value,
                    "domain": ".echo360.org",
                    "path": "/",
                    "httpOnly": True,
                    "sameSite": "None",
                }
            self.cookies.append(curr_cookie)
        self.display_message(message=f"[Finished] Echo360 Course Page {self.course_id}")

    def setup_driver(self) -> bool:
        self.display_message(
            message=f"[Ongoing] Setting up webdriver for rendering dynamic pages"
        )
        if self.driver is not None:
            print("WebDriver has already set!")
            return False

        # not show the test instance of browser
        options = webdriver.ChromeOptions()
        options.add_argument("--headless")
        options.add_argument("--log-level=3")
        # init webdriver
        self.driver = webdriver.Chrome(options=options)
        # access echo360 for webdriver identify the pattern of cookie
        self.driver.get(self.base_url)
        # delete the current un-login cookies
        self.driver.delete_all_cookies()
        # add valid cookie to the driver
        for cookie in self.cookies:
            self.driver.add_cookie(cookie)
        self.display_message(
            message=f"[Finished] Setting up webdriver for rendering dynamic pages"
        )
        return True

    def fetch_content(
        self,
        target_url: str,
        checking_callback: Callable,
        target_tag: str,
        target_attrs: Dict = dict(),
        waiting_render_time: int = 2,
        retries: int = 4,
    ) -> List[Tag]:
        wait_intervel = waiting_render_time
        while retries > 0:
            self.driver.get(target_url)
            sleep(wait_intervel)
            # print(target_url)
            # with open("./test/lti5.html", "w", encoding="utf-8") as f:
            #     f.write(self.driver.page_source)
            curr_page_url = self.driver.current_url
            # echo360 redirect page to other page rather than target page
            if checking_callback(curr_page_url):
                continue
            page = BeautifulSoup(self.driver.page_source, "html.parser")

            content = page.find(target_tag, attrs=target_attrs)
            # elements = list(content.children)
            # print(target_url, retries, wait_intervel, len(list(content.children)), any(True for _ in content.children))
            if any(True for _ in content.children):
                return content.children

            wait_intervel *= 2
            retries -= 1
        return []

    def fetch_video_download_link(
        self,
        video_url: str,
        info_dict: Dict,
        waiting_render_time: int = 2,
        retries: int = 4,
    ) -> None:
        self.display_message(
            message=f"[Ongoing] Fetching Video Info for {info_dict['date']} {info_dict['time']}"
        )
        video_sections = self.fetch_content(
            target_url=video_url,
            checking_callback=lambda x: self.fetch_url_part(x, 1) != "lesson",
            target_tag="div",
            target_attrs={"class": "screens"},
            waiting_render_time=waiting_render_time,
            retries=retries,
        )
        # if len(list(video_sections)) == 0:
        #     return
        # f = open("./test/lti3.html", "w", encoding="utf-8")
        info_dict["videos"] = list()
        for section in video_sections:
            # f.write(str(section))
            curr_video_info = dict()
            curr_video_tag = section.find("video")
            curr_video_info["id"] = curr_video_tag["id"]
            component_1 = self.fetch_url_part(curr_video_tag["poster"], 1)
            component_2 = self.fetch_url_part(curr_video_tag["poster"], 2)
            component_3 = self.fetch_url_part(curr_video_tag["poster"], 3)
            component_4 = self.fetch_url_part(curr_video_tag["poster"], 4)
            component_4 = component_4.replace("poster", "hd").replace(".jpg", ".mp4")
            curr_video_info[
                "download_link"
            ] = f"/{component_1}/{component_2}/{component_3}/{component_4}"
            info_dict["videos"].append(curr_video_info)
            # print(json.dumps(curr_video_info, indent=4))
        self.display_message(
            message=f"[Finished] {len(info_dict['videos'])} Videos Fetched for {info_dict['date']} {info_dict['time']}"
        )

    def fetch_video_info(self, waiting_render_time: int = 2, retries: int = 4) -> None:
        self.display_message(
            message=f"[Ongoing] Fetching Video Info for course {self.course_id}"
        )
        video_elements = self.fetch_content(
            target_url=self.course_url,
            checking_callback=lambda x: self.fetch_url_part(x, -1) != "home",
            target_tag="div",
            target_attrs={"class": "contents-wrapper"},
            waiting_render_time=waiting_render_time,
            retries=retries,
        )
        self.video_info = []

        # f = open("./test/lti4.html", "w", encoding="utf-8")
        for elem in video_elements:
            # f.write(str(elem))
            is_available = False
            # class-row future means video not uploaded
            if elem["class"][0] == "class-row" and len(elem["class"]) == 1:
                is_available = True

            curr_info = dict()
            curr_info["video_id"] = elem["data-test-lessonid"]
            curr_info["date"] = elem.find("span", attrs={"class": "date"}).text
            curr_info["time"] = elem.find("span", attrs={"class": "time"}).text
            # if "March" not in curr_info["date"] or "21" not in curr_info["date"]:
            #     continue
            # print(curr_info["date"], str(is_available) + '\n\n')
            if not is_available:
                self.video_info.append(curr_info)
                continue

            curr_video_url = self.video_base_url.format(curr_info["video_id"])
            self.fetch_video_download_link(
                video_url=curr_video_url,
                info_dict=curr_info,
                waiting_render_time=waiting_render_time,
                retries=retries,
            )
            self.video_info.append(curr_info)
            # break
        self.display_message(
            message=f"[Finished] Fetching Video Info for course {self.course_id}"
        )
        # print(json.dumps(self.video_info, indent=4))
        # with open("./test/lti3.html", "w", encoding="utf-8") as f:
        #     elem: Tag
        #     f.write(elem[])

        # print(video_elements[0])
        # div class="contents-wrapper"


if __name__ == "__main__":

    params = {
        "url": "https://umass.moonami.com/mod/lti/launch.php?id=2046322",
        "timeout": 120.0,
        "cookies": {
            "MDL_SSP_AuthToken": "_910303e49a58c1a3e09a284b474e27ebdb55e15826",
            "MDL_SSP_SessID": "00d26be39e3804c1f7ea20a98ab8890d",
            "MOODLEID1_": "i%2517%2525%258F%2595%2510%25DEU%250D",
            "MoodleSession": "gilps2qujde5o93c4h2rl0nhdk",
        },
        "allow_redirects": True,
    }

    res = requests.get(**params)
    soup = BeautifulSoup(res.content, "html.parser")
    form = soup.find(
        "form", attrs={"name": "ltiLaunchForm", "id": "ltiLaunchForm", "method": "post"}
    )
    lti_url = form["action"]
    # print(res.url)
    inputs = form.find_all("input")
    detail = dict()
    for input in inputs:
        detail[input["name"]] = input["value"]

    with Echo360Extractor("./test/echo360.json") as echo360:
        echo360.setup(lti_url, detail)
        echo360.fetch_video_info()
