import json
from enum import Enum
from typing import Dict, List

from bs4 import Tag

from src.utils.enums import mod_type


class url:
    def __init__(self, link: str) -> None:
        request_type, *other = link.split("://")[0]
        print(type(other))


class section_container:
    _id: str
    _title: str
    _type: mod_type
    _link: str
    _content: List[str]

    def __init__(self, id: str, section_tag: Tag) -> None:
        self._id = id
        self._title = ""
        self._type = mod_type.undefined
        self._link = ""
        self._content = []

    def to_json(self) -> Dict:
        return {
            "id": self._id,
            "type": self._type,
            "title": self._title,
            "link": self._link,
            "content": self._content,
        }

    def __str__(self) -> str:
        return json.dumps(self.to_json(), indent=4)

    def __repr__(self) -> str:
        return str(self)
