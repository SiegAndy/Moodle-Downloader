# moodle-downloader

## Download Config

#### Put ".config" File Under Root Directory

    EXTRACTION_MODE: 
        Options are: [ALL, FileOnly]
        Default:
            "EXTRACTION_MODE=FileOnly"
    EXTRACT_FILE_MODE: 
        Options are: [UnderSection, InOneFolder, Both]
        Default:
            "EXTRACT_FILE_MODE=UnderSection"
    ZIP_MODE: 
        Options are: [ZIP, UNZIP]
        Default:
            "ZIP_MODE=ZIP"
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

