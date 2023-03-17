from typing import Callable, Dict

from src.container import item_info
from src.downloader import downloader


def construct_file(
    target: item_info, info_param: Dict, callback: Callable
) -> downloader:
    the_downloader = downloader(url=target.link, cookies=info_param["cookie"])
    info_param["url_filename"] = the_downloader.file_name
    info_param["url_file_extension"] = the_downloader.file_name.split(".")[-1]

    callback(the_downloader)
    return the_downloader
