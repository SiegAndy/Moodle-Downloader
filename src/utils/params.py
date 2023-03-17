import os

# width of the terminal can use for printout
terminal_cols = os.get_terminal_size().columns

config_path = ".config"

# type, id
view_url = "https://umass.moonami.com/mod/{}/view.php?id={}"

# 34311
moodle_course_url = "https://umass.moonami.com/course/view.php?id={}"

# use to download content in the folder
download_folder_url = "https://umass.moonami.com/mod/folder/download_folder.php"

launch_url = "https://umass.moonami.com/mod/{}/launch.php?id={}"


# extract info is valid for one day
modified_expire_time = 60 * 60 * 24
