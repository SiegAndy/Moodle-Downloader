# moodle-downloader

## Download Config

#### Put ".config" File Under Root Directory

    DOWNLOAD_MODE: 
        Options are: [ALL, FileOnly]
        Default:
            "DOWNLOAD_MODE=FileOnly"
    FILE_MODE: 
        Options are: [UnderSection, InOneFolder, Both]
        Default:
            "FILE_MODE=UnderSection"
    ZIP_MODE: 
        Options are: [ZIP, UNZIP]
        Default:
            "ZIP_MODE=ZIP"
    PAGE_MODE: 
        Options are: [HTML, PDF]
        Default:
            "PAGE_MODE=PDF"
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
            "FILENAME_FORMAT=%section_index%-%section_file_index%-%section_title%.%url_file_extension%"

