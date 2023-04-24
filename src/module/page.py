from typing import Callable, Dict

from src.container import item_info
from src.downloader import downloader
from src.utils.enums import download_mode, page_mode
from src.utils.func import html_to_pdf


def construct_page(
    target: item_info,
    mode: page_mode,
    info_param: Dict,
    callback: Callable,
    config: Dict = None,
) -> downloader:
    info_param["url_filename"] = target.title
    the_downloader = downloader(
        url=target.link,
        cookies=info_param["cookie"],
        suppress_url_file_check=True,
        url_filename=info_param["url_filename"],
    )
    info_param["url_file_extension"] = "html"

    file_paths = callback(curr_downloader=the_downloader)

    if mode == page_mode.PDF:
        for file_path in file_paths:
            html_to_pdf(html_path=file_path)
    return the_downloader
