from http.cookies import CookieError
from typing import Any, Dict, List, Tuple

import requests
from bs4 import BeautifulSoup, Tag

from src.container import course_info, item_info, section_info
from src.module.folder import fetch_folder_params
from src.module.lti import fetch_lti_params
from src.utils import (
    cleanup_prev_line,
    launch_url,
    mod_type,
    moodle_course_url,
    terminal_cols,
    view_url,
)


class extractor:
    extract_section_index: int
    container: course_info

    def __init__(
        self,
        container: course_info,
        extract_section_index: int = -1,
    ) -> None:
        self.container = container
        self.extract_section_index = extract_section_index

    def check_signin(
        self, url: str, cookies: Dict, check_title: bool = True
    ) -> Tuple[BeautifulSoup, str]:
        res = requests.get(url, cookies=cookies)
        res_cont = res.content.decode(encoding="utf-8")
        soup = BeautifulSoup(res_cont, "html.parser")
        with open("./test/test.html", "w", encoding="utf-8") as f:
            f.write(soup.prettify())
        if not check_title:
            return soup, ""

        res_title = soup.find("title").text
        if "Sign in" in res_title:
            raise CookieError(
                "Invalid Cookie! Please login to the Moodle First, and then try to retreive all the contents!"
            )
        return soup, res_title

    def extract_sections(self) -> None:
        soup, page_title = self.check_signin(
            url=moodle_course_url.format(self.container.course_id),
            cookies=self.container.course_cookie,
        )

        print("#" * int(terminal_cols * 3 / 4))
        print(f"Retrieving Course: '{page_title.split(':')[1].strip(' ')}'")

        # with open ("files/unlogin.html", 'w', encoding='utf-8') as f:
        #     f.write(soup.prettify())
        # update course title in container
        if self.container.course_title != page_title:
            self.container.course_title = page_title
        sections: List[Tag] = soup.find_all("li", class_="section main clearfix")
        for index, section in enumerate(sections):
            section_title = section["aria-label"]
            curr_section = section_info(title=section_title, raw_content=section)

            if self.extract_section_index != -1 and self.extract_section_index != index:
                continue

            print("#" * int(terminal_cols / 2))
            print(f"Retrieving Section {index}: '{section_title}'", end="\r")

            section_page_elements = section.find(id=f"collapse-{index}")

            self.extract_section_info(section_page_elements, curr_section)

            self.container.contents[f"section-{index}"] = curr_section
            if curr_section.items_length > 0:
                msg = f"Retrieved Section {index}: '{section_title}'"
            else:
                msg = f"Fail to Retrieved Section {index}: '{section_title}'.\nDetail: Section not containing files."

            cleanup_prev_line()
            print(msg)

        print("#" * int(terminal_cols / 2))
        print("Retrieval Complete! Now Downloading Files...")
        print("#" * int(terminal_cols * 3 / 4))

        # with open(os.path.join(self.store_dir, 'course_info.json'), "w", encoding="utf-8") as record:
        #     record.write(json.dumps(self.info_dict, indent=4))

    def extract_folder_info(self, curr_item: item_info) -> None:
        soup, page_title = self.check_signin(
            url=view_url.format(mod_type.folder.name, curr_item.id),
            cookies=self.container.course_cookie,
        )
        fetch_folder_params(curr_item=curr_item, soup=soup)

    def extract_lti_info(self, curr_item: item_info) -> None:
        # reach lti redirect form page
        soup, page_title = self.check_signin(
            url=launch_url.format(mod_type.lti.name, curr_item.id),
            cookies=self.container.course_cookie,
            check_title=False,
        )
        fetch_lti_params(
            curr_item=curr_item, soup=soup, store_dir=self.container.store_dir
        )

    def extract_section_info(
        self, section_page_elements: Tag, curr_section: section_info
    ) -> Dict[str, Dict]:
        content: List[Tag] = section_page_elements.find_all("li")
        if len(content) == 0:
            return

        for elem in content:
            # id='module-1916049'
            elem_id = elem["id"].split("-")[1]
            # ['activity', 'url', 'modtype_url']
            curr_type = elem["class"][1]
            curr_item = item_info(
                id=elem_id,
                title=elem.find("span", class_="instancename").contents[0].text,
                type=curr_type,
                link=view_url.format(curr_type, elem_id),
                raw_content=elem,
            )
            if curr_item.type == mod_type.folder.name:
                self.extract_folder_info(curr_item=curr_item)
            elif curr_item.type == mod_type.lti.name:
                self.extract_lti_info(curr_item=curr_item)

            # check if there is a text to describe the link/content
            activity_instance = elem.find("div", class_="activityinstance")
            siblings = [
                sibling
                for sibling in list(activity_instance.next_siblings)
                if sibling != "\n"
            ]
            curr_item.content = list()
            curr_section.items[elem_id] = curr_item
            for sibling in siblings:
                curr_item.content.append(sibling.get_text().replace("\xa0", ""))

        return curr_section

    def __call__(
        self, container: course_info = None, *args: Any, **kwds: Any
    ) -> course_info:
        if container is not None:
            self.container = self.container
        self.extract_sections()
        return self.container
