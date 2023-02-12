import logging
import os
from typing import Dict

from src.extractor import extractor
from src.utils import mod_type, custom_enum, check_config, load_config
from src.downloader import downloader
from src.utils.enums import extract_file_mode, extraction_mode

info_dict_path = "info.json"


class constructor:
    class_id: str
    store_dir: str
    target_website: str
    cookie: Dict[str, str]
    info_dict: Dict[str, Dict]
    config: Dict[str, custom_enum | str]

    def __init__(self, class_id: str, store_dir: str, target_website: str) -> None:
        self.class_id = class_id
        self.store_dir = store_dir
        self.fixed_resource_store_dir = os.path.join(store_dir, "Resources")
        self.target_website = target_website
        self.config = load_config()
        self.info_dict = None
        self.cookie = None

        try:
            if not os.path.isdir(self.store_dir):
                os.makedirs(self.store_dir)
            if self.config["extract_file_mode"] != extract_file_mode.UnderSection:
                if not os.path.isdir(self.fixed_resource_store_dir):
                    os.makedirs(self.fixed_resource_store_dir)
        except Exception as e:
            raise ValueError(
                "Error! Unable to create root directory! Please make sure you have privilege role!"
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

    def format_filename(self, info_param: Dict[str, int | str]) -> str:
        try:
            input_param = info_param.copy()
            input_param["file_index"] = format(info_param["file_index"], "02d")
            input_param["section_index"] = format(info_param["section_index"], "02d")
            input_param["section_file_index"] = format(
                info_param["section_file_index"], "02d"
            )
            return self.config["filename_format"].format(**input_param)
        except Exception as e:
            logging.warning(f"Error! Unable to Format Filename. Detail: {e}")

    def construct_section(
        self, info_param: Dict[str, int | str], section: Dict[str, Dict]
    ) -> None:
        section_index = format(info_param["section_index"], "02d")
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

        for item_id, item in section["items"].items():
            if self.config["extraction_mode"] == extraction_mode.All:
                info_param["file_index"] += 1
                info_param["section_file_index"] += 1

            if item["type"] == mod_type.resource.name:
                info_param["file_index"] += 1
                info_param["section_file_index"] += 1
                curr_downloader = downloader(url=item["link"], cookies=self.cookie)
                info_param["url_filename"] = curr_downloader.file_name
                info_param["url_file_extension"] = curr_downloader.file_name.split(".")[
                    -1
                ]

                file_name = self.format_filename(info_param=info_param)
                if (
                    self.config["extract_file_mode"] == extract_file_mode.Both
                    or self.config["extract_file_mode"]
                    == extract_file_mode.UnderSection
                ):
                    curr_downloader.download(
                        download_path=os.path.join(dir_name, file_name)
                    )
                    if self.config["extract_file_mode"] == extract_file_mode.Both:
                        curr_downloader.duplicate(
                            new_file_path=os.path.join(
                                self.fixed_resource_store_dir, file_name
                            )
                        )
                elif self.config["extract_file_mode"] == extract_file_mode.InOneFolder:
                    curr_downloader.download(
                        download_path=os.path.join(
                            self.fixed_resource_store_dir, file_name
                        )
                    )
            else:
                pass

    def construct_sections(self, index: int = -1) -> None:
        info_param = {
            "file_index": -1,
            "section_index": -1,
            "section_title": "",
            "section_file_index": -1,
            "url_filename": "",
            "url_file_extension": "",
        }

        for section_index, (section_id, section) in enumerate(self.info_dict.items()):
            if index != -1 and index != section_index:
                continue
            info_param["section_index"] = section_index
            info_param["section_title"] = section["title"]
            info_param["section_file_index"] = -1
            self.construct_section(info_param=info_param, section=section)

    def construction(self, index: int = -1) -> None:
        return self.construct_sections(index)
