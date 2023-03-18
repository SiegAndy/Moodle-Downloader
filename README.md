# Moodle-Downloader
The Moodle-Downloader is used for downloading and syncing the file from the moodle page. It now only support [page, file, folder, echo360-video] resources and is expected to implement more categories downloads in the future along with the parallel downloading queue.

## Supported Operating System
    Windows
    MacOS
    Linux

## Package Requirements

    pip install -r requirements.txt

## Download Config

#### Put ".config" File Under Root Directory

    DOWNLOAD_MODE: 
        Options are: [ALL, FILEONLY]
        Default:
            "DOWNLOAD_MODE=FILEONLY"
    FILE_MODE: 
        Options are: [UNDERSECTION, INONEFOLDER, BOTH]
        Default:
            "FILE_MODE=UNDERSECTION"
    ZIP_MODE: 
        Options are: [ZIP, UNZIP]
        Default:
            "ZIP_MODE=ZIP"
    PAGE_MODE: 
        Options are: [HTML, PDF]
        Default:
            "PAGE_MODE=PDF"
    Video_MODE: 
        Options are: [ECHO360, NONE]
        Default:
            "Video_MODE=ECHO360"
    FILENAME_FORMAT:
        Flags are: [
            "file_index",
            "section_index",
            "section_file_index",
            "section_title",
            "url_filename",
            "url_file_extension",
        ]
        Default:
            "FILENAME_FORMAT=%section_index%-%section_file_index%-%url_filename%.%url_file_extension%"

