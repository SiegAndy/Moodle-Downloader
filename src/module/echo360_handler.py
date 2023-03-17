# https://echo360.org/lesson/G_60d13195-1ffd-4686-855d-d8bf004c89fd_a17b816d-a847-4a00-9e77-97532c1b0fa5_2023-02-07T13:00:00.000_2023-02-07T14:15:00.000/classroom#sortDirection=desc
# https://content.echo360.org/0000.c4a29c15-265c-404e-9ed7-17f518602cf7/e6da5055-1fed-4f31-aea3-024cb7cc8d6c/1/hd1.mp4
# https://content.echo360.org/0000.c4a29c15-265c-404e-9ed7-17f518602cf7/e6da5055-1fed-4f31-aea3-024cb7cc8d6c/1/hd2.mp4
# https://thumbnails.echo360.org/0000.c4a29c15-265c-404e-9ed7-17f518602cf7/e6da5055-1fed-4f31-aea3-024cb7cc8d6c/1/poster1.jpg
import json
from pathlib import PurePosixPath
from queue import Queue
from time import sleep
from typing import Callable, Dict, List
from urllib.parse import unquote, urlparse

import requests
from bs4 import BeautifulSoup, Tag
from selenium import webdriver
from selenium.webdriver.remote.webdriver import WebDriver as WebDriverClass

from src.utils.func import cleanup_prev_line
from src.utils.loading import loading


class Echo360Extractor:
    base_url: str = "https://echo360.org/"
    video_base_url: str = "https://echo360.org/lesson/{}/classroom#sortDirection=desc"
    video_download_url_head: str = "https://content.echo360.org"
    course_url: str
    course_id: str
    cookies: List[Dict[str, str]]
    driver: WebDriverClass
    video_info: Dict[str, str | int | List]
    json_store_path: str
    display_info_queue: Queue
    display_info_thread: loading
    container_mode: str

    def __init__(self, json_store_path: str = "./echo360.json"):
        self.json_store_path = json_store_path
        self.driver = None
        self.video_info = dict()
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

    def get_cookie(self) -> Dict[str, str]:
        result = dict()
        for cookie in self.cookies:
            result[cookie["name"]] = cookie["value"]
        return result

    def display_message(
        self,
        is_show: bool = True,
        message: str = "",
        with_new_line: bool = True,
        callback: Callable = None,
    ) -> None:
        if self.display_info_thread is None:
            return
        if not is_show:
            if not self.display_info_thread.is_paused:
                self.display_info_thread.pause(True)
        else:
            self.display_info_queue.put((message, with_new_line, callback))
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
        self.display_message(
            message=f"[Ongoing] Echo360 Course Page {self.course_id}",
            with_new_line=False,
        )

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
        self.display_message(
            message=f"[Finished] Echo360 Course Page {self.course_id}",
            callback=lambda x: cleanup_prev_line(2),
        )

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
        target_attrs: Dict = None,
        waiting_render_time: int = 2,
        retries: int = 4,
    ) -> List[Tag]:
        if target_attrs is None:
            target_attrs = dict()
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
            curr_video_info["downloaded"] = False
            info_dict["videos"].append(curr_video_info)
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
        if self.video_info is not None:
            self.video_info.clear()
        else:
            self.video_info = dict()

        self.video_info["num_video"] = 0
        self.video_info["course_id"] = self.course_id
        self.video_info["videos"] = list()
        # f = open("./test/lti4.html", "w", encoding="utf-8")
        for index, elem in enumerate(video_elements):
            # f.write(str(elem))
            is_available = False
            # class-row future means video not uploaded
            if elem["class"][0] == "class-row" and len(elem["class"]) == 1:
                is_available = True

            curr_info = dict()
            curr_info["video_id"] = elem["data-test-lessonid"]
            curr_info["date"] = elem.find("span", attrs={"class": "date"}).text
            curr_info["time"] = elem.find("span", attrs={"class": "time"}).text
            if not is_available:
                self.video_info["videos"].append(curr_info)
                continue

            curr_video_url = self.video_base_url.format(curr_info["video_id"])
            self.fetch_video_download_link(
                video_url=curr_video_url,
                info_dict=curr_info,
                waiting_render_time=waiting_render_time,
                retries=retries,
            )
            self.video_info["num_video"] += len(curr_info["videos"])
            self.video_info["videos"].append(curr_info)
            if index == 1:
                break
        self.display_message(
            message=f"[Finished] Fetching Video Info for course {self.course_id}"
        )

    def to_json(self) -> Dict:
        return {
            "echo360-course-id": self.course_id,
            "echo360-course-url": self.course_url,
            "echo360-course-cookie": self.cookies,
            "echo360-course-store-path": self.json_store_path,
        }

    def __str__(self) -> str:
        return json.dumps(self.to_json(), indent=4, default=lambda x: x.to_json())

    def __repr__(self) -> str:
        return str(self)
