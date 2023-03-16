from enum import Enum

import requests


class custom_enum(Enum):
    @classmethod
    def get_class_name(cls):
        return cls.__name__

    @classmethod
    def get_options(cls):
        result = []
        for key, value in cls.__dict__.items():
            if not key.startswith("_") and type(value) == cls:
                result.append(key)
        return result


class request_method(custom_enum):
    GET = "GET"
    POST = "POST"

    def get_req_method(self):
        if self == request_method.GET:
            return requests.get
        elif self == request_method.POST:
            return requests.post


class page_mode(custom_enum):
    HTML = "HTML"
    PDF = "PDF"


class zip_mode(custom_enum):
    ZIP = "ZIP"
    UNZIP = "UNZIP"


class download_mode(custom_enum):
    All = "all"
    FileOnly = "FileOnly"


class file_mode(custom_enum):
    UnderSection = "UnderSection"
    InOneFolder = "InOneFolder"
    Both = "Both"


class mod_type(custom_enum):
    assign = "assignment"
    quiz = "quiz"
    folder = "folder"
    resource = "resource"
    url = "url"
    page = "page"
    lti = "lti"
    forum = "forum"
    undefined = "undefined"


# print(file_mode.get_class_name())
