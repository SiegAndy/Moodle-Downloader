from typing import Callable, Dict

from src.container import item_info
from src.downloader import downloader
from src.utils.func import html_to_pdf


def construct_page(
    target: item_info, info_param: Dict, callback: Callable
) -> downloader:
    info_param["url_filename"] = target.title
    the_downloader = downloader(
        url=target.link,
        cookies=info_param["cookie"],
        suppress_url_file_check=True,
        url_filename=info_param["url_filename"],
    )
    info_param["url_file_extension"] = "html"

    file_paths = callback(the_downloader)

    for file_path in file_paths:
        html_to_pdf(html_path=file_path)
    return the_downloader
