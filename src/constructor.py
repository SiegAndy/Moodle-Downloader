import logging
import logging.config
import os
from typing import Dict

from src.downloader import downloader
from src.extractor import extractor
from src.utils.enums import (
    custom_enum,
    download_mode,
    file_mode,
    mod_type,
    page_mode,
    request_method,
    zip_mode,
)
from src.utils.func import load_config, slugify, unzip_file, html_to_pdf
from src.utils.params import download_folder_url, terminal_cols

info_dict_path = "info.json"


class constructor:
    class_id: str
    store_dir: str
    target_website: str
    cookie: Dict[str, str]
    info_dict: Dict[str, Dict]
    config: Dict[str, custom_enum | str]

    def __init__(
        self,
        class_id: str,
        store_dir: str,
        target_website: str,
        config: str = "./log_config.ini",
    ) -> None:
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
            if self.config["file_mode"] != file_mode.UnderSection:
                if not os.path.isdir(self.fixed_resource_store_dir):
                    os.makedirs(self.fixed_resource_store_dir)
            if not os.path.isdir("./src/data/"):
                os.makedirs("./src/data/")
            if not os.path.isfile("./src/data/log_file.log"):
                with open("./src/data/log_file.log", "w") as f:
                    pass
            logging.config.fileConfig(config)
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
            input_param["url_filename"] = slugify(input_param["url_filename"])
            input_param["file_index"] = format(info_param["file_index"], "02d")
            input_param["section_index"] = format(info_param["section_index"], "02d")
            input_param["section_file_index"] = format(
                info_param["section_file_index"], "02d"
            )
            return self.config["filename_format"].format(**input_param)
        except Exception as e:
            logging.warning(f"Error! Unable to Format Filename. Detail: {e}")

    def construct_file(self, target: Dict, info_param: Dict) -> downloader:
        the_downloader = downloader(url=target["link"], cookies=self.cookie)
        info_param["url_filename"] = the_downloader.file_name
        info_param["url_file_extension"] = the_downloader.file_name.split(".")[-1]
        return the_downloader

    def construct_folder(self, target: Dict, info_param: Dict) -> downloader:
        info_param["url_filename"] = target["title"]
        the_downloader = downloader(
            url=download_folder_url,
            cookies=self.cookie,
            method=request_method.POST,
            params={"data": target["detail"]["post_params"]},
            suppress_url_file_check=True,
            url_filename=info_param["url_filename"],
        )
        info_param["url_file_extension"] = "zip"
        return the_downloader

    def construct_page(self, target: Dict, info_param: Dict) -> downloader:
        info_param["url_filename"] = target["title"]
        the_downloader = downloader(
            url=target["link"],
            cookies=self.cookie,
            suppress_url_file_check=True,
            url_filename=info_param["url_filename"],
        )
        info_param["url_file_extension"] = "html"
        return the_downloader

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
            if self.config["download_mode"] == download_mode.All:
                info_param["file_index"] += 1
                info_param["section_file_index"] += 1

            if item["type"] == mod_type.resource.name:
                curr_downloader = self.construct_file(
                    target=item, info_param=info_param
                )
            elif item["type"] == mod_type.folder.name:
                curr_downloader = self.construct_folder(
                    target=item, info_param=info_param
                )
            elif item["type"] == mod_type.page.name:
                curr_downloader = self.construct_page(
                    target=item, info_param=info_param
                )
            else:
                continue

            if self.config["download_mode"] != download_mode.All:
                info_param["file_index"] += 1
                info_param["section_file_index"] += 1
            file_name = self.format_filename(info_param=info_param)
            if (
                self.config["file_mode"] == file_mode.Both
                or self.config["file_mode"] == file_mode.UnderSection
            ):
                file_paths = [os.path.join(dir_name, file_name)]
                curr_downloader.download(download_path=file_paths[0])
                if self.config["file_mode"] == file_mode.Both:
                    file_paths.append(
                        os.path.join(self.fixed_resource_store_dir, file_name)
                    )
                    curr_downloader.duplicate(new_file_path=file_paths[1])
            elif self.config["file_mode"] == file_mode.InOneFolder:
                file_paths = [os.path.join(self.fixed_resource_store_dir, file_name)]
                curr_downloader.download(download_path=file_paths[0])

            if (
                info_param["url_file_extension"] == "zip"
                and self.config["zip_mode"] == zip_mode.UNZIP
            ):
                for file_path in file_paths:
                    unzip_file(target_zip=file_path, unzip_directory=file_path[:-4])
            elif item["type"] == "page" and self.config["page_mode"] == page_mode.PDF:
                for file_path in file_paths:
                    html_to_pdf(html_path=file_path)

    def construct_sections(self, index: int = -1) -> None:
        print("#" * int(terminal_cols * 3 / 4))
        print(f"Downloading Course: '{self.info_dict['course-title']}'")
        info_param = {
            "file_index": -1,
            "section_index": -1,
            "section_title": "",
            "section_file_index": -1,
            "url_filename": "",
            "url_file_extension": "",
        }

        for section_index, (section_id, section) in enumerate(
            self.info_dict.items(), start=-1
        ):
            if section_index == -1 or (index != -1 and index != section_index):
                continue
            info_param["section_index"] = section_index
            info_param["section_title"] = section["title"]
            info_param["section_file_index"] = -1
            print("#" * int(terminal_cols / 2))
            print(f"Section {section_index} '{section['title']}': Downloading")
            self.construct_section(info_param=info_param, section=section)
            print(f"Section {section_index} '{section['title']}': Downloaded")

        print("#" * int(terminal_cols / 2))
        print(f"Download Complete! Downloaded File are stored in '{self.store_dir}'.")
        print("#" * int(terminal_cols * 3 / 4))

    def construction(self, index: int = -1) -> None:
        return self.construct_sections(index)
