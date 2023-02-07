
from enum import Enum


# type, id
href_header = "https://umass.moonami.com/mod/{}/view.php?id={}"


# 34311
moodle_course_url = "https://umass.moonami.com/course/view.php?id={}"



class mod_type(Enum):
    assign = 'assignment'
    quiz = 'quiz'
    folder = 'folder'
    resource = 'resource'
    url = 'url'
    page = 'page'
    forum = 'forum'
    undefined = 'undefined'