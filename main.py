from src import constructor

if __name__ == "__main__":
    course_id = 35816
    inputs = {
        "course_id": course_id,
        "store_dir": f"course-{course_id}",
        "target_website": "umass.moonami.com",
    }

    content = constructor(**inputs)
    content.extraction()
    content.construct_sections()
