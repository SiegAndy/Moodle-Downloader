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

    def __eq__(self, other):
        return self.name.lower() == str(other).lower()

    def __str__(self) -> str:
        return self.name

    def to_json(self) -> str:
        return self.name


class request_method(custom_enum):
    GET = "GET"
    POST = "POST"

    def get_req_method(self):
        if self == request_method.GET:
            return requests.get
        elif self == request_method.POST:
            return requests.post


class video_mode(custom_enum):
    ECHO360 = "ECHO360"
    NONE = "NONE"


class page_mode(custom_enum):
    HTML = "HTML"
    PDF = "PDF"


class zip_mode(custom_enum):
    ZIP = "ZIP"
    UNZIP = "UNZIP"


class download_mode(custom_enum):
    All = "ALL"
    FileOnly = "FILEONLY"


class file_mode(custom_enum):
    UNDERSECTION = "UNDERSECTION"
    INONEFOLDER = "INONEFOLDER"
    BOTH = "BOTH"


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


class container_mode(custom_enum):
    create = "create"
    read = "read"
    update = "update"
    overwrite = "overwrite"


# print(file_mode.get_class_name())
