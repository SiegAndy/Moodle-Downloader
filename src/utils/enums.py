from enum import Enum


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


class extraction_mode(custom_enum):
    All = "all"
    FileOnly = "FileOnly"


class extract_file_mode(custom_enum):
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
    forum = "forum"
    undefined = "undefined"


# print(extract_file_mode.get_class_name())
