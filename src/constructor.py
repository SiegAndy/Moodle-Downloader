import logging
import logging.config
import os
from typing import Dict, List

from src.container import course_info, section_info
from src.downloader import downloader
from src.extractor import extractor
from src.module.folder import construct_folder
from src.module.lti import construct_echo360
from src.module.page import construct_page
from src.module.resource import construct_file
from src.utils.enums import custom_enum, download_mode, file_mode, mod_type
from src.utils.func import slugify
from src.utils.params import terminal_cols

info_dict_path = "course_info.json"

# Implementation from:
# https://docs.python.org/3/library/functools.html#functools.partial
def partial(func, /, *args, **keywords):
    def newfunc(*fargs, **fkeywords):
        newkeywords = {**keywords, **fkeywords}
        return func(*args, *fargs, **newkeywords)

    newfunc.func = func
    newfunc.args = args
    newfunc.keywords = keywords
    return newfunc


class constructor:
    container: course_info

    def __init__(
        self,
        course_id: str,
        store_dir: str,
        target_website: str,
        config: str = "./log_config.ini",
    ) -> None:
        self.container = course_info(
            course_id=course_id, store_dir=store_dir, target_website=target_website
        )

        try:
            if not os.path.isdir(store_dir):
                os.makedirs(store_dir)
            if self.config["file_mode"] != file_mode.UNDERSECTION:
                if not os.path.isdir(self.fixed_resource_store_dir):
                    os.makedirs(self.fixed_resource_store_dir)
            if not os.path.isdir("./src/data/"):
                os.makedirs("./src/data/")
            if not os.path.isfile("./src/data/log_file.log"):
                with open("./src/data/log_file.log", "w") as f:
                    pass
            logging.config.fileConfig(config)
        except Exception as e:
            raise ValueError(
                "Error! Unable to create root directory! Please make sure you have privilege role!"
            )

    @property
    def config(self) -> Dict[str, str | List | custom_enum]:
        return self.container.config

    @property
    def cookie(self) -> Dict[str, str]:
        return self.container.course_cookie

    @property
    def store_dir(self) -> str:
        return self.container.store_dir

    @property
    def fixed_resource_store_dir(self) -> str:
        return self.container.fixed_resource_store_dir

    def __enter__(self) -> "constructor":
        return self

    def __exit__(self) -> None:
        self.container.save()

    def extraction(self, index: int = -1) -> Dict[str, Dict]:
        new_extractor = extractor(
            container=self.container,
            extract_section_index=index,
        )
        new_extractor()
        self.container.save()

    def format_filename(self, info_param: Dict[str, int | str]) -> str:
        try:
            input_param = info_param.copy()
            input_param["url_filename"] = slugify(input_param["url_filename"])
            input_param["file_index"] = format(info_param["file_index"], "02d")
            input_param["section_index"] = format(info_param["section_index"], "02d")
            input_param["section_file_index"] = format(
                info_param["section_file_index"], "02d"
            )
            return self.config["filename_format"].format(**input_param)
        except Exception as e:
            logging.warning(f"Error! Unable to Format Filename. Detail: {e}")

    def downloader_callback(
        self,
        dir_name: str,
        info_param: Dict[str, int | str],
        curr_downloader: downloader,
        intermediate_folder: str = None,
        url_filename: str = None,
    ) -> List[str]:

        if self.config["download_mode"] != download_mode.All:
            info_param["file_index"] += 1
            info_param["section_file_index"] += 1

        file_name = self.format_filename(info_param=info_param)
        if url_filename is not None:
            file_name = slugify(url_filename) + f".{info_param['url_file_extension']}"
        if intermediate_folder is not None:
            file_name = os.path.join(intermediate_folder, file_name)
            os.makedirs(
                os.path.join(
                    dir_name,
                    intermediate_folder,
                ),
                exist_ok=True,
            )
            os.makedirs(
                os.path.join(
                    self.fixed_resource_store_dir,
                    intermediate_folder,
                ),
                exist_ok=True,
            )

        file_paths = []
        if (
            self.config["file_mode"] == file_mode.BOTH
            or self.config["file_mode"] == file_mode.UNDERSECTION
        ):
            file_paths = [os.path.join(dir_name, file_name)]
            curr_downloader.download(download_path=file_paths[0])
            if self.config["file_mode"] == file_mode.BOTH:
                file_paths.append(
                    os.path.join(self.fixed_resource_store_dir, file_name)
                )
                curr_downloader.duplicate(new_file_path=file_paths[1])
        elif self.config["file_mode"] == file_mode.INONEFOLDER:
            file_paths = [os.path.join(self.fixed_resource_store_dir, file_name)]
            curr_downloader.download(download_path=file_paths[0])

        return file_paths

    def construct_section(
        self, info_param: Dict[str, int | str], section: section_info
    ) -> None:
        section_index = format(info_param["section_index"], "02d")
        partial_dir_name = f"{section_index}-{section.title}"
        dir_name = os.path.join(self.store_dir, partial_dir_name)
        try:
            if not os.path.isdir(dir_name):
                os.makedirs(dir_name)
            if not os.path.isdir(dir_name):
                raise ValueError()
        except Exception as e:
            raise ValueError(
                f"Error! Unable to create subdirectory for section {partial_dir_name}!"
            )

        for item_id, item in section.items.items():
            if self.config["download_mode"] == download_mode.All:
                info_param["file_index"] += 1
                info_param["section_file_index"] += 1

            partial_callback = partial(
                self.downloader_callback,
                dir_name=dir_name,
                info_param=info_param,
            )
            if item.type == mod_type.resource.name:
                curr_downloader = construct_file(
                    target=item, info_param=info_param, callback=partial_callback
                )
            elif item.type == mod_type.folder.name:
                curr_downloader = construct_folder(
                    target=item,
                    mode=self.config["zip_mode"],
                    info_param=info_param,
                    callback=partial_callback,
                )
            elif item.type == mod_type.page.name:
                curr_downloader = construct_page(
                    target=item,
                    mode=self.config["page_mode"],
                    info_param=info_param,
                    callback=partial_callback,
                )
            elif item.type == mod_type.lti.name:
                curr_downloader = construct_echo360(
                    target=item,
                    mode=self.config["video_mode"],
                    info_param=info_param,
                    callback=partial_callback,
                )
            else:
                continue
            # if index == 2:
            #     break

    def construct_sections(self, index: int = -1) -> None:
        print("#" * int(terminal_cols * 3 / 4))
        print(f"Downloading Course: '{self.container.course_title}'")
        info_param = {
            "file_index": -1,
            "section_index": -1,
            "section_title": "",
            "section_file_index": -1,
            "url_filename": "",
            "url_file_extension": "",
            "cookie": self.cookie,
        }

        for iter_index, (section_id, section) in enumerate(
            self.container.contents.items()
        ):
            section_index = int(section_id.split("-")[-1])
            if index != -1 and index != section_index:
                continue
            if section.items_length == 0:
                continue
            info_param["section_index"] = section_index
            info_param["section_title"] = section.title
            info_param["section_file_index"] = -1
            print("#" * int(terminal_cols / 2))
            print(f"Section {section_index} '{section.title}': Downloading")
            self.construct_section(info_param=info_param, section=section)
            print(f"Section {section_index} '{section.title}': Downloaded")

        print("#" * int(terminal_cols / 2))
        print(f"Download Complete! Downloaded File are stored in '{self.store_dir}'.")
        print("#" * int(terminal_cols * 3 / 4))

    def construction(self, index: int = -1) -> None:
        return self.construct_sections(index)
