from genericpath import isdir
import os
from typing import Dict

from src.extractor import extractor
from src.utils import mod_type
from src.downloader import downloader

info_dict_path = "info.json"


class constructor:
    class_id: str
    store_dir: str
    target_website: str
    cookie: Dict[str, str]
    info_dict: Dict[str, Dict]

    def __init__(self, class_id: str, store_dir: str, target_website: str) -> None:
        self.class_id = class_id
        self.store_dir = store_dir
        self.target_website = target_website
        self.info_dict = None
        self.cookie = None

        try:
            if not os.path.isdir(self.store_dir):
                os.makedirs(self.store_dir)
        except Exception as e:
            raise ValueError(
                "Error! Unable to create root directory! Please make sure you have privilege to do so!"
            )

    def extraction(self, index: int = -1) -> Dict[str, Dict]:
        if self.info_dict is not None:
            self.info_dict.clear()
        dict_store_path = os.path.join(self.store_dir, info_dict_path)
        new_extractor = extractor(
            class_id=self.class_id,
            store_path=dict_store_path,
            target_website=self.target_website,
            extract_section_index=index,
        )
        self.info_dict = new_extractor()
        self.cookie = new_extractor.login_cookie

    def construct_section(self, section_index: int, section: Dict[str, Dict]) -> None:
        section_index = format(section_index, "02d")
        partial_dir_name = f"{section_index}-{section['title']}"
        dir_name = os.path.join(self.store_dir, partial_dir_name)
        try:
            if not os.path.isdir(dir_name):
                os.makedirs(dir_name)
            if not os.path.isdir(dir_name):
                raise ValueError()
        except Exception as e:
            raise ValueError(
                f"Error! Unable to create subdirectory for section {partial_dir_name}!"
            )

        valid_resource = 0
        for item_id, item in section["items"].items():
            file_index = format(valid_resource, "02d")
            file_name = f'{file_index}-{item["title"]}-'
            file_path = os.path.join(dir_name, file_name)
            if item["type"] == mod_type.resource.name:
                curr_downloader = downloader(
                    url=item["link"], cookies=self.cookie, store_path=file_path
                )
                curr_downloader.download()
                valid_resource += 1

    def construct_sections(self, index: int = -1) -> None:
        for section_index, (section_id, section) in enumerate(self.info_dict.items()):
            if index != -1 and index != section_index:
                continue
            self.construct_section(section_index=section_index, section=section)

    def construction(self, index: int = -1) -> None:
        return self.construct_sections(index)
