from ctypes import Union
import logging
from typing import Any, Dict, Tuple, Type

from src.utils.params import config_path
from src.utils.enums import custom_enum, extract_file_mode, extraction_mode


def checksum(input: str | bytes, num: int = 8) -> str:
    if not isinstance(input, bytes):
        input = input.encode("utf-8")
    sum = 0
    for i in range(len(input)):
        sum += input[i]
    return format(int(sum % pow(10, num)), f"0{num}d")


def get_unit(value: int) -> Tuple[str, str]:
    if (value / 1024) >= 1:
        value /= 1024
        if (value / 1024) >= 1:
            value /= 1024
            unit = "mbs"
        else:
            unit = "kbs"
    else:
        unit = "bits"
    l_digits = str(value).split(".")[0]
    r_digits = 5 - len(l_digits)
    return format(value, f".{r_digits}f"), unit


def progress_bar(current, total, bar_length=20, string_in_front: str = ""):
    fraction = current / total

    arrow = int(fraction * bar_length - 1) * "-" + ">"
    padding = int(bar_length - len(arrow)) * " "

    ending = "\n" if current == total else "\r"

    division = "{} {}/ {} {}".format(*get_unit(current), *get_unit(total))

    division = "{:^24}".format(division)

    return (
        f"{string_in_front}{division}: [{arrow}{padding}] {int(fraction*100)}% ",
        ending,
    )


def dict_to_str(target: Dict[str, str]) -> str:
    if not isinstance(target, dict):
        raise TypeError(f"Expect a dict but '{type(target)}'")

    target_list = [f"{key}={value}" for key, value in target.items()]
    return "; ".join(target_list)


def check_config(key: str, default: Any = None, output_type: Any = None) -> bool | Any:
    with open(config_path, "r", encoding="utf-8") as config:
        config = config.readlines()

    result = default
    for line in config:
        tag, status = line.strip("\n").split("=")
        if tag != key:
            continue
        if status.lower() == "true":
            status = True
        elif status.lower() == "false":
            status = False
        result = status
        break
    if output_type is not None:
        try:
            curr_type = type(result)
            result = output_type(result)
        except Exception as e:
            logging.critical(
                f"Unable to convert {curr_type} to {output_type}. Detail: {e}"
            )
    return result


def enum_conversion(value: str, type: custom_enum) -> Type[custom_enum]:
    try:
        return type(value)
    except Exception:
        raise ValueError(
            f"Error! '{value}' is not valid option for class '{type.get_class_name()}'. Valid Options are {str(type.get_options())}."
        )


def parse_file_format(value: str) -> str:
    format_flag = [
        "file_index",
        "section_index",
        "section_file_index",
        "section_title",
        "url_filename",
        "url_file_extension",
    ]
    segments = value.split("%")
    segments_len = len(segments)
    result = ""
    for index, segment in enumerate(segments):
        if index % 2 == 0 or segments_len - 1 == index:
            result += segment
        else:
            if segment not in format_flag:
                raise ValueError(
                    f"Error! Unkown Format Flag '{segment}'. Valid Flags are {str(format_flag)}."
                )
            result += "{" + segment + "}"
    return result


def load_config() -> Dict[str, Any]:
    with open(config_path, "r", encoding="utf-8") as config:
        config = config.readlines()

    result = dict()
    for line in config:
        tag, value = line.strip("\n").split("=")
        tag = tag.lower()
        if tag == "extraction_mode":
            value = enum_conversion(value=value, type=extraction_mode)
        elif tag == "extract_file_mode":
            value = enum_conversion(value=value, type=extract_file_mode)
        elif tag == "filename_format":
            value = parse_file_format(value=value)
        elif value.lower() == "true":
            value = True
        elif value.lower() == "false":
            value = False
        result[tag] = value

    if "extraction_mode" not in result:
        result["extraction_mode"] = extraction_mode.FileOnly
    if "extraction_mode" not in result:
        result["extract_file_mode"] = extract_file_mode.InOneFolder
    if "filename_format" not in result:
        result[
            "filename_format"
        ] = "{section_index}-{section_file_index}-{section_title}.{url_file_extension}"

    return result


# path = "files/test4.html"
# with open (path, 'r', encoding='utf-8') as f:
#     content = f.read()
# result = checksum(content)
# print(result)
# print(str(hex(12648430)[2:]))
# print('str'.encode('utf-8'))
