import json
import os
from collections import defaultdict
from typing import Dict, List, Type

from src.cookie_reader import retreive_cookies
from src.utils.enums import container_mode, custom_enum
from src.utils.func import checksum as checksum_func
from src.utils.func import load_config

info_dict_path = "course_info.json"
fix_resource_store_dir = "Resources"


class info:
    def __enter__(self) -> Type["info"]:
        return self

    def __exit__(self, *args, **kwargs) -> None:
        return

    @classmethod
    def from_json(cls, input_json: Dict) -> Type["info"]:
        return cls()

    def to_json(self) -> Dict:
        return {}

    def __str__(self) -> str:
        return json.dumps(self.to_json(), indent=4, default=lambda x: x.to_json())

    def __repr__(self) -> str:
        return str(self)


class item_info(info):
    is_modified: bool
    checksum: str
    id: str
    title: str
    type: str
    link: str
    detail: Dict
    content: List[str]

    def __init__(
        self,
        id: str = None,
        title: str = None,
        type: str = None,
        link: str = None,
        content: List = None,
        detail: Dict = None,
        checksum: str = None,
        raw_content: str = None,
    ) -> None:
        self.is_modified = False
        self.id = id
        self.title = title
        self.type = type
        self.link = link
        self.detail = detail
        if detail is None:
            self.detail = dict()
        self.content = content
        if content is None:
            self.content = list()
        self.checksum = checksum
        if raw_content is not None:
            self.checksum = checksum_func(raw_content)

    @classmethod
    def from_json(cls, input_json: Dict) -> "item_info":
        input_json.pop("is_modified", None)
        return cls(**input_json)

    def to_json(self) -> Dict:
        return self.__dict__


class section_info(info):
    is_modified: bool
    title: str
    checksum: str
    items: Dict[str, item_info]

    def __init__(
        self, title: str = None, checksum: str = None, raw_content: str = None
    ) -> None:
        self.is_modified = False
        self.title = title
        self.checksum = checksum
        if raw_content is not None:
            self.checksum = checksum_func(raw_content)
        self.items = dict()

    @property
    def items_length(self) -> int:
        return len(self.items.items())

    @classmethod
    def from_json(cls, input_json: Dict) -> "section_info":
        items = input_json.pop("items", dict())
        input_json.pop("is_modified", None)
        new_instance = cls(**input_json)
        for key, value in items.items():
            new_instance.items[key] = item_info.from_json(value)
        return new_instance

    def to_json(self) -> Dict:
        return self.__dict__


class course_info(info):
    course_id: str
    course_title: str
    target_website: str
    course_cookie: Dict[str, str]
    config: Dict[str, custom_enum | str]
    contents: Dict[str, section_info]
    mode: container_mode

    store_dir: str
    fixed_resource_store_dir: str

    def __init__(
        self,
        course_id: str,
        store_dir: str,
        target_website: str = None,
        login_cookie: Dict[str, str] = None,
    ) -> None:
        self.course_id = course_id
        self.course_title = ""
        self.target_website = target_website
        self.store_dir = store_dir
        self.fixed_resource_store_dir = os.path.join(store_dir, fix_resource_store_dir)
        self.course_cookie = login_cookie
        self.mode = None
        self.contents = defaultdict(dict)

        self.config = load_config()
        self.try_load_prev_info_dict()
        if self.course_cookie is None:
            if self.target_website is None:
                raise ValueError(
                    "Error! Missing target website url, need to specify one of [target_website, login_cookie]!"
                )
            self.course_cookie = retreive_cookies(target_website=self.target_website)
            print(json.dumps(self.course_cookie, indent=4))

    def init_params(self) -> None:
        if self.contents is not None:
            self.contents.clear()
        else:
            self.contents = defaultdict(dict)

    def __enter__(self) -> "course_info":
        return self

    def save(self) -> None:
        with open(
            os.path.join(self.store_dir, "course_info.json"), "w", encoding="utf-8"
        ) as record:
            record.write(str(self))

    def try_load_prev_info_dict(self, target_file_path: str = None) -> None:
        if target_file_path is None:
            prev_info_dict_path = os.path.join(self.store_dir, info_dict_path)
            if self.mode is not None and self.mode == container_mode.overwrite:
                return self.init_params()
        else:
            prev_info_dict_path = target_file_path

        if not os.path.isfile(prev_info_dict_path):
            return self.init_params()

        with open(prev_info_dict_path, "r", encoding="utf-8") as input:
            info_dict: Dict = json.load(input)
            if info_dict is None:
                return self.init_params()
            general_dict = info_dict["general"]
            # found class is not the class we currently working on
            if (
                "course-id" in general_dict
                and general_dict["course-id"] != self.course_id
            ):
                raise ValueError(
                    "Error! Folder contains existing course, please select another folder to continue!"
                )
            if (
                "target-website" in general_dict
                and general_dict["target-website"] != self.target_website
            ):
                raise ValueError(
                    "Error! Folder contains existing course, please select another folder to continue!"
                )
            if "contents" in info_dict:
                for key, value in info_dict["contents"].items():
                    self.contents[key] = section_info.from_json(value)
                self.mode = container_mode.update
            else:
                self.contents = dict()
                self.mode = container_mode.create

    def to_json(self) -> Dict:
        return {
            "general": {
                "course-id": self.course_id,
                "course-title": self.course_title,
                "target-website": self.target_website,
                "config": self.config,
            },
            "contents": self.contents,
        }
