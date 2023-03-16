import json
from collections import defaultdict
from http.cookies import CookieError
from typing import Any, Dict, List, Tuple

import requests
from bs4 import BeautifulSoup, Tag

from src.cookie_reader import retreive_cookies
from src.utils import (
    checksum,
    cleanup_prev_line,
    view_url,
    launch_url,
    mod_type,
    moodle_course_url,
    terminal_cols,
)


class extractor:
    class_id: str
    store_path: str
    login_cookie: Dict[str, str]
    info_dict: Dict[str, Dict]
    extract_section_index: int

    def __init__(
        self,
        class_id: str,
        store_path: str,
        target_website: str = None,
        login_cookie: Dict[str, str] = None,
        extract_section_index: int = -1,
    ) -> None:
        self.class_id = class_id
        self.store_path = store_path
        self.extract_section_index = extract_section_index

        if login_cookie is None:
            if target_website is None:
                raise ValueError(
                    "Error! Missing target website url, need to specify one of [target_website, login_cookie]!"
                )
            self.login_cookie = retreive_cookies(target_website=target_website)
            print(json.dumps(self.login_cookie, indent=4))
        else:
            self.login_cookie = login_cookie

        self.info_dict = defaultdict(dict)

    def check_signin(self, url: str, cookies: Dict) -> Tuple[BeautifulSoup, str]:
        res = requests.get(url, cookies=cookies)
        res_cont = res.content.decode(encoding="utf-8")
        # with open (path, 'r', encoding='utf-8') as f:
        #     res_cont = f.read()
        soup = BeautifulSoup(res_cont, "html.parser")

        res_title = soup.find("title").text
        if "Sign in" in res_title:
            raise CookieError(
                "Invalid Cookie! Please login to the Moodle First, and then try to retreive all the contents!"
            )
        return soup, res_title

    def extract_sections(self) -> Dict[str, Dict]:
        soup, page_title = self.check_signin(
            url=moodle_course_url.format(self.class_id), cookies=self.login_cookie
        )

        print("#" * int(terminal_cols * 3 / 4))
        print(f"Retrieving Course: '{page_title.split(':')[1].strip(' ')}'")

        # with open ("files/unlogin.html", 'w', encoding='utf-8') as f:
        #     f.write(soup.prettify())
        self.info_dict.clear()
        self.info_dict["course-title"] = page_title
        sections: List[Tag] = soup.find_all("li", class_="section main clearfix")
        for index, section in enumerate(sections):
            section_title = section["aria-label"]
            self.info_dict[section["id"]]["title"] = section_title
            self.info_dict[section["id"]]["checksum"] = checksum(section)
            self.info_dict[section["id"]]["items"] = dict()

            if self.extract_section_index != -1 and self.extract_section_index != index:
                continue

            print("#" * int(terminal_cols / 2))
            print(f"Retrieving Section {index}: '{section_title}'", end="\r")

            section_page_elements = section.find(id=f"collapse-{index}")

            self.extract_section_info(
                section_page_elements, self.info_dict[section["id"]]["items"]
            )

            if len(self.info_dict[section["id"]]["items"].items()) > 0:
                msg = f"Retrieved Section {index}: '{section_title}'"
            else:
                msg = f"Fail to Retrieved Section {index}: '{section_title}'.\nDetail: Section not containing files."

            cleanup_prev_line()
            print(msg)

        print("#" * int(terminal_cols / 2))
        print("Retrieval Complete! Now Downloading Files...")
        print("#" * int(terminal_cols * 3 / 4))

        with open(self.store_path, "w", encoding="utf-8") as record:
            record.write(json.dumps(self.info_dict, indent=4))

        return self.info_dict

    def extract_folder_info(self, item_info: Dict) -> None:
        soup, page_title = self.check_signin(
            url=view_url.format(mod_type.folder.name, item_info["id"]),
            cookies=self.login_cookie,
        )
        forms: List[Tag] = soup.find_all("form", attrs={"method": "post"})
        file_section = soup.find("section", attrs={"id": "region-main"})
        for form in forms:
            if "download_folder" not in form.attrs["action"]:
                continue
            inputs = form.find_all("input")
            if "detail" not in item_info:
                item_info["detail"] = dict()
                item_info["detail"]["checksum"] = checksum(file_section)
            if "post_params" not in item_info["detail"]:
                item_info["detail"]["post_params"] = dict()
            for input in inputs:
                item_info["detail"]["post_params"][input["name"]] = input["value"]

    def extract_lti_info(self, item_info: Dict) -> None:
        # reach lti redirect form page
        soup, page_title = self.check_signin(
            url=launch_url.format(mod_type.lti.name, item_info["id"]),
            cookies=self.login_cookie,
        )
        # retreive the form
        form: Tag = soup.find(
            "form",
            attrs={"name": "ltiLaunchForm", "id": "ltiLaunchForm", "method": "post"},
        )
        # retreive the target url from form
        lti_url = form["action"]
        # retreive the post params from form
        inputs = form.find_all("input")
        detail = dict()
        for input in inputs:
            detail[input["name"]] = input["value"]
        if "detail" not in item_info:
            item_info["detail"] = dict()
            item_info["detail"]["checksum"] = checksum(form)
        if "post_params" not in item_info["detail"]:
            item_info["detail"]["post_params"] = dict()
        item_info["detail"]["post_params"] = detail

    def extract_section_info(
        self, section_page_elements: Tag, section_info: Dict
    ) -> Dict[str, Dict]:
        content: List[Tag] = section_page_elements.find_all("li")
        if len(content) == 0:
            return

        for elem in content:
            # id='module-1916049'
            elem_id = elem["id"].split("-")[1]
            section_info[elem_id] = dict()

            item_info = section_info[elem_id]
            item_info["id"] = elem_id

            item_checksum = checksum(elem)
            item_info["checksum"] = item_checksum

            # ['activity', 'url', 'modtype_url']
            item_info["type"] = elem["class"][1]

            item_info["title"] = (
                elem.find("span", class_="instancename").contents[0].text
            )
            item_info["link"] = view_url.format(item_info["type"], elem_id)
            if item_info["type"] == mod_type.folder.name:
                self.extract_folder_info(item_info=item_info)
            # check if there is a text to describe the link/content
            activity_instance = elem.find("div", class_="activityinstance")
            siblings = [
                sibling
                for sibling in list(activity_instance.next_siblings)
                if sibling != "\n"
            ]
            if len(siblings) == 0:
                continue
            item_info["content"] = list()
            for sibling in siblings:
                item_info["content"].append(sibling.get_text().replace("\xa0", ""))

        return section_info

    def __call__(self, *args: Any, **kwds: Any) -> Dict[str, Dict]:
        self.extract_sections()
        return self.info_dict
