


from collections import defaultdict
import json
from typing import Dict, List
from bs4 import BeautifulSoup, Tag

import requests
from src.utils import moodle_course_url, href_header

class extractor:
    class_id: str
    login_cookie: Dict[str, str]
    store_path: str
    
    def __init__(self, class_id: str, login_cookie: Dict[str, str], store_path: str) -> None:
        self.class_id = class_id
        self.login_cookie = login_cookie
        self.store_path = store_path

        self.extract_sections()

        
    def extract_sections(self):
        res = requests.get(moodle_course_url.format(self.class_id), cookies=self.login_cookie)
        res_cont = res.content.decode(encoding='utf-8')
        # with open (path, 'r', encoding='utf-8') as f:
        #     res_cont = f.read()
        soup = BeautifulSoup(res_cont, 'html.parser')
        sections: List[Tag] = soup.find_all('li', class_='section main clearfix')
        info_dict = defaultdict(dict)
        for index, section in enumerate(sections):
            info_dict[section['id']]['title'] = section['aria-label']
            section_page_elements = section.find(id=f"collapse-{index}")
            self.extract_section_info(section_page_elements, info_dict[section['id']])
            # print(json.dumps(info_dict, indent=4))

        with open(self.store_path, 'w', encoding='utf-8') as record:
            record.write(json.dumps(info_dict, indent=4))

    def extract_section_info(self, section_page_elements: Tag, section_info: Dict):
        # title = result.contents[0].text
        # section_info['title'] = section_text.contents[0].text
        content: List[Tag] = section_page_elements.find_all('li')
        if len(content) == 0:
            return
        for elem in content:
            # id='module-1916049'
            elem_id = elem['id'].split('-')[1]
            section_info[elem_id] = dict()
            item_info = section_info[elem_id]
            item_info['id'] = elem_id
            # ['activity', 'url', 'modtype_url']
            item_info['type'] = elem['class'][1]
            item_info['title'] = elem.find('span', class_ ='instancename').contents[0].text
            item_info['link'] = href_header.format(item_info['type'], elem_id)
            # check if there is a text to describe the link/content
            activity_instance = elem.find('div', class_="activityinstance")
            siblings = [sibling for sibling in list(activity_instance.next_siblings) if sibling != '\n']
            if len(siblings) == 0: continue
            item_info['content'] = list()
            for sibling in siblings:
                item_info['content'].append(sibling.get_text().replace('\xa0', ''))