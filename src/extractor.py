from collections import defaultdict
from http.cookies import CookieError
import json
from typing import Any, Dict, List
from bs4 import BeautifulSoup, Tag

import requests
from src.utils import moodle_course_url, href_header, checksum
from src.cookie_reader import retreive_cookies


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
        else:
            self.login_cookie = login_cookie

        self.info_dict = defaultdict(dict)

    def extract_sections(self) -> Dict[str, Dict]:
        res = requests.get(
            moodle_course_url.format(self.class_id), cookies=self.login_cookie
        )
        res_cont = res.content.decode(encoding="utf-8")
        # with open (path, 'r', encoding='utf-8') as f:
        #     res_cont = f.read()
        soup = BeautifulSoup(res_cont, "html.parser")

        res_title = soup.find("title").text
        if "Sign in" in res_title:
            raise CookieError(
                "Invalid Cookie! Please login to the Moodle First, and then try to retreive all the contents!"
            )
        else:
            print()
            print(
                "-" * 20
                + "''{:^80}''".format(
                    f"Retrieving Course: '{res_title.split(':')[1].strip(' ')}'"
                )
                + "-" * 20
            )
        # with open ("files/unlogin.html", 'w', encoding='utf-8') as f:
        #     f.write(soup.prettify())

        sections: List[Tag] = soup.find_all("li", class_="section main clearfix")
        self.info_dict.clear()
        for index, section in enumerate(sections):
            section_title = section["aria-label"]
            self.info_dict[section["id"]]["title"] = section_title
            self.info_dict[section["id"]]["checksum"] = checksum(section)
            self.info_dict[section["id"]]["items"] = dict()

            if self.extract_section_index != -1 and self.extract_section_index != index:
                continue

            print(
                "-" * 20
                + "''{:^80}''".format(f"Retrieving Section {index}: '{section_title}'")
                + "-" * 20
            )

            section_page_elements = section.find(id=f"collapse-{index}")

            self.extract_section_info(
                section_page_elements, self.info_dict[section["id"]]["items"]
            )

            if len(self.info_dict[section["id"]]["items"].items()) > 0:
                msg = f" Retrieved Section {index}: '{section_title}'"
            else:
                msg = f"Fail to Retrieved Section {index}: '{section_title}'.\nDetail: Section not containing files."
            print("-" * 20 + "''{:^80}''".format(msg) + "-" * 20)

        print(
            "-" * 20
            + "''{:^80}''".format("Retrieval Complete! Now Downloading Files...")
            + "-" * 20
        )
        print()

        with open(self.store_path, "w", encoding="utf-8") as record:
            record.write(json.dumps(self.info_dict, indent=4))

        return self.info_dict

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
            item_info["link"] = href_header.format(item_info["type"], elem_id)
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
