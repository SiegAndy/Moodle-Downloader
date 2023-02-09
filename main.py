from src import extractor, constructor

mod_type = {
    "assign": "assignment",
    "quiz": "quiz",
    "folder": "folder",
    "resource": "resource",
    "url": "url",
}
cookies = {
    "MDL_SSP_AuthToken": "_260c17d4eb805d9ae3c2632b48a7f0684a5238d384",
    "MDL_SSP_SessID": "f3a7b255cfa954044d3ac03229b32205",
    "MOODLEID1_": "i%2517%2525%258F%2595%2510%25DEU%250D",
    "MoodleSession": "qv1nirji59vpjlrha7n0g1am2i",
}

path = "test"

if __name__ == "__main__":
    inputs = {
        "class_id": 34311,
        "store_dir": path,
        "target_website": "umass.moonami.com",
    }  # , "login_cookie": cookies}
    # extractor(**inputs)
    content = constructor(**inputs)
    content.extraction()
    content.construct_sections()
