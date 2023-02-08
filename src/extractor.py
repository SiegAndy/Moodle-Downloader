from collections import defaultdict
from http.cookies import CookieError
import json
from typing import Dict, List
from bs4 import BeautifulSoup, Tag

import requests
from src.utils import moodle_course_url, href_header, checksum
from src.cookie_reader import retreive_cookies


class extractor:
    class_id: str
    store_path: str
    login_cookie: Dict[str, str]

    def __init__(
        self, class_id: str, store_path: str, login_cookie: Dict[str, str] = None
    ) -> None:
        self.class_id = class_id
        self.store_path = store_path
        if login_cookie is None:
            self.login_cookie = retreive_cookies(target_website="umass.moonami.com")
        else:
            self.login_cookie = login_cookie

        self.extract_sections()

    def extract_sections(self):
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
        info_dict = defaultdict(dict)
        for index, section in enumerate(sections):
            section_title = section["aria-label"]
            info_dict[section["id"]]["title"] = section_title
            info_dict[section["id"]]["checksum"] = checksum(section)
            info_dict[section["id"]]["items"] = dict()

            print(
                "-" * 20
                + "''{:^80}''".format(f"Retrieving Section {index}: '{section_title}'")
                + "-" * 20
            )

            section_page_elements = section.find(id=f"collapse-{index}")
            self.extract_section_info(
                section_page_elements, info_dict[section["id"]]["items"]
            )

            if len(info_dict[section["id"]]["items"].items()) > 0:
                msg = f" Retrieved Section {index}: '{section_title}'"
            else:
                msg = f"Fail to Retrieved Section {index}: '{section_title}'.\nDetail: Section not containing files."
            print("-" * 20 + "''{:^80}''".format(msg) + "-" * 20)

        with open(self.store_path, "w", encoding="utf-8") as record:
            record.write(json.dumps(info_dict, indent=4))

    def extract_section_info(self, section_page_elements: Tag, section_info: Dict):
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
