import io
import logging
import os
import re
import shutil
import traceback
import unicodedata
import zipfile
from typing import Any, Dict, Tuple, Type

from bs4 import BeautifulSoup
from xhtml2pdf import pisa

from src.utils.enums import custom_enum, download_mode, file_mode, page_mode, zip_mode
from src.utils.params import config_path, terminal_cols


def html_to_pdf(html_path: str) -> None:
    filename_without_ext = os.path.splitext(html_path)[0]
    src = open(html_path, "r", encoding="utf-8")
    dst = open(f"{filename_without_ext}.pdf", "w+b")
    with src, dst:
        src = src.read()
        soup = BeautifulSoup(src, "html.parser")
        content = soup.find("div", {"role": "main"})
        modified_src = f"<html><body>{content}</body></html>"
        pisa_status = pisa.CreatePDF(modified_src, dest=dst)
        dst.close()
        return pisa_status.err


def _unzip_nested_zip(zip_ref: zipfile.ZipFile, unzip_directory: str) -> None:
    for member in zip_ref.namelist():
        filename = os.path.basename(member)
        # skip directories
        target_file_name = os.path.join(unzip_directory, member)
        if not filename and not os.path.isdir(target_file_name):
            os.makedirs(target_file_name)
            continue

        source = zip_ref.open(member)
        if ".zip" == os.path.splitext(filename)[-1]:
            content = io.BytesIO(source.read())
            nested_zip_ref = zipfile.ZipFile(content)
            nested_dir = os.path.splitext(target_file_name)[0]
            _unzip_nested_zip(nested_zip_ref, nested_dir)
            target_file_name = os.path.join(nested_dir, filename)
        try:
            if not os.path.isfile(target_file_name):
                target_file_dir = target_file_name.rstrip(filename)
                if (
                    target_file_dir is not None
                    and target_file_dir != ""
                    and not os.path.isdir(target_file_dir)
                ):
                    os.makedirs(target_file_dir)
                if target_file_dir == target_file_name:
                    continue
            target = open(target_file_name, "wb")
            with source, target:
                source.seek(0)
                shutil.copyfileobj(source, target)
        except PermissionError as e:
            # traceback.print_exc()
            # logging.warning(f"Error! {str(e)}")
            pass


def unzip_file(target_zip: str, unzip_directory: str):
    try:
        if not os.path.isdir(unzip_directory):
            os.makedirs(unzip_directory)
        with zipfile.ZipFile(target_zip, "r") as zip_ref:
            _unzip_nested_zip(zip_ref, unzip_directory)

        file_name = target_zip.split(os.sep)[-1]
        shutil.move(target_zip, os.path.join(unzip_directory, file_name))
    except Exception as e:
        traceback.print_exc()
        logging.warning(f"Error! {str(e)}")


def slugify(value, allow_unicode=False):
    """
    Code copied from https://github.com/django/django/blob/main/django/utils/text.py

    Convert to ASCII if 'allow_unicode' is False. Convert spaces or repeated
    dashes to single dashes. Remove characters that aren't alphanumerics,
    underscores, or hyphens. Convert to lowercase. Also strip leading and
    trailing whitespace, dashes, and underscores.
    """
    value = str(value)
    if allow_unicode:
        value = unicodedata.normalize("NFKC", value)
    else:
        value = (
            unicodedata.normalize("NFKD", value)
            .encode("ascii", "ignore")
            .decode("ascii")
        )
    value = re.sub(r"[^\w\s-]", "", value.lower())
    return re.sub(r"[-\s]+", "-", value).strip("-_")


def cleanup_prev_line(num_lines: int = 1) -> None:
    if num_lines < 1:
        return
    if num_lines == 1:
        print("\033[K", end="\r")
        return
    for i in range(num_lines):
        print("\033[F\033[1G\033[K", end="")
    print("\033[K", end="\r")


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


def progress_bar(current, total, bar_length=-1, string_in_front: str = ""):
    is_total_unknown = False
    if total == -1:
        total = current
        is_total_unknown = True
    fraction = current / total

    division = "{} {}/ {} {}".format(*get_unit(current), *get_unit(total))

    division = "{:^24}".format(division)

    front_length = len(string_in_front)
    latter_length = 40
    bar_length = max(20, terminal_cols - front_length - latter_length)

    arrow = int(fraction * bar_length - 1) * "-" + ">"
    padding = int(bar_length - len(arrow)) * " "

    ending = "\n" if current == total and not is_total_unknown else "\r"
    # alignment = "{" + f":>{terminal_cols - len(front_print_out)}" + "}"

    return (
        f"{string_in_front}: [{arrow}{padding}] {division} {int(fraction*100)}%",
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
        if tag == "download_mode":
            value = enum_conversion(value=value, type=download_mode)
        elif tag == "file_mode":
            value = enum_conversion(value=value, type=file_mode)
        elif tag == "zip_mode":
            value = enum_conversion(value=value, type=zip_mode)
        elif tag == "page_mode":
            value = enum_conversion(value=value, type=page_mode)
        elif tag == "filename_format":
            value = parse_file_format(value=value)
        elif value.lower() == "true":
            value = True
        elif value.lower() == "false":
            value = False
        result[tag] = value

    if "download_mode" not in result:
        result["download_mode"] = download_mode.FileOnly
    if "download_mode" not in result:
        result["file_mode"] = file_mode.InOneFolder
    if "zip_mode" not in result:
        result["zip_mode"] = zip_mode.ZIP
    if "page_mode" not in result:
        result["page_mode"] = page_mode.PDF
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
