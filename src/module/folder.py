from typing import Callable, Dict, List

from bs4 import BeautifulSoup, Tag

from src.container import item_info
from src.downloader import downloader
from src.utils.enums import request_method, zip_mode
from src.utils.func import checksum, unzip_file
from src.utils.params import download_folder_url


def fetch_folder_params(curr_item: item_info, soup: BeautifulSoup) -> None:
    forms: List[Tag] = soup.find_all("form", attrs={"method": "post"})
    file_section = soup.find("section", attrs={"id": "region-main"})
    for form in forms:
        if "download_folder" not in form.attrs["action"]:
            continue
        inputs = form.find_all("input")
        post_params = dict()
        for input in inputs:
            post_params[input["name"]] = input["value"]
        curr_item.detail["post_params"] = post_params
        if "checksum" not in curr_item.detail:
            curr_item.detail["checksum"] = checksum(file_section)


def construct_folder(
    target: item_info, mode: zip_mode, info_param: Dict, callback: Callable
) -> downloader:
    info_param["url_filename"] = target.title
    the_downloader = downloader(
        url=download_folder_url,
        cookies=info_param["cookie"],
        method=request_method.POST,
        params={"data": target.detail["post_params"]},
        suppress_url_file_check=True,
        url_filename=info_param["url_filename"],
    )
    info_param["url_file_extension"] = "zip"

    file_paths = callback(curr_downloader=the_downloader)

    if mode == zip_mode.UNZIP:
        for file_path in file_paths:
            unzip_file(target_zip=file_path, unzip_directory=file_path[:-4])

    return the_downloader
