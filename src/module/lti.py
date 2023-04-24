# Side note: I believe lti stands for Learning Tools Interoperability
import os
from typing import Callable, Dict

from bs4 import BeautifulSoup, Tag

from src.container import item_info
from src.downloader import downloader
from src.module.echo360_handler import Echo360Extractor
from src.utils.enums import download_mode, video_mode
from src.utils.func import checksum


def fetch_lti_params(curr_item: item_info, soup: BeautifulSoup, store_dir: str) -> None:
    # retreive the form
    form: Tag = soup.find(
        "form",
        attrs={"name": "ltiLaunchForm", "id": "ltiLaunchForm", "method": "post"},
    )
    # retreive the target url from form
    lti_url = form["action"]
    if "echo360" not in lti_url:
        print(f"Only support donwloading echo360 video, but '{lti_url}' received.")
        return
    # retreive the post params from form
    inputs = form.find_all("input")
    post_params = dict()
    for input in inputs:
        post_params[input["name"]] = input["value"]
    curr_item.detail["post_params"] = post_params
    if "checksum" not in curr_item.detail:
        curr_item.detail["checksum"] = checksum(form)

    if "echo360" in curr_item.detail:
        echo360_extractor = Echo360Extractor.from_json(curr_item.detail["echo360"])
    else:
        echo360_extractor = Echo360Extractor(
            json_store_path=os.path.join(store_dir, "echo360.json")
        )
    with echo360_extractor:
        echo360_extractor.setup(redirect_url=lti_url, cookie=post_params)
        echo360_extractor.fetch_video_info()

    curr_item.detail["echo360"] = echo360_extractor


def construct_echo360(
    target: item_info,
    mode: video_mode,
    info_param: Dict,
    callback: Callable,
    config: Dict = None,
) -> downloader:
    if config is not None and config["download_mode"] == download_mode.FileOnly:
        print(f"Ignoring external learning tool type.")
        return
    if "echo360" not in target.detail:
        print(
            f"Only support donwloading echo360 video for external learning tool type."
        )
        return
    echo360_extractor: Echo360Extractor = target.detail["echo360"]
    # echo360_json_path = target.detail["echo360"].json_store_path

    # with open(echo360_json_path, 'r', encoding="utf-8") as echo360_info:
    #     echo360_info = json.load(echo360_info)
    #     videos = echo360_info
    if mode == video_mode.NONE:
        return

    info_param["url_file_extension"] = "mp4"

    if isinstance(echo360_extractor, Dict):
        echo360_extractor = Echo360Extractor.from_json(target.detail["echo360"])
        is_valid = echo360_extractor.check_existed_file()

        if not is_valid:
            raise Exception(
                "Error! Stored Echo360 Info is not Valid! Please clear all the JSON files to continue!"
            )

    video_sections = echo360_extractor.video_info["videos"]
    for video_section in video_sections:

        info_param["url_filename"] = f"{video_section['date']}-{video_section['time']}-"
        if "videos" not in video_section:
            continue
        videos = video_section["videos"]
        for index, video in enumerate(videos, start=1):
            curr_file_name = info_param["url_filename"] + str(index)
            the_downloader = downloader(
                url=echo360_extractor.video_download_url_head + video["download_link"],
                cookies=echo360_extractor.get_cookie(),
            )
            # print(the_downloader.url)
            file_paths = callback(
                curr_downloader=the_downloader,
                intermediate_folder="Lecture Recordings",
                url_filename=curr_file_name,
            )

    return the_downloader
