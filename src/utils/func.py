from typing import Dict


def checksum(input: str | bytes, num: int = 8) -> str:
    if not isinstance(input, bytes):
        input = input.encode("utf-8")
    sum = 0
    for i in range(len(input)):
        sum += input[i]
    return format(int(sum % pow(10, num)), f"0{num}d")


def progress_bar(current, total, bar_length=20, string_in_front: str = ""):
    fraction = current / total

    arrow = int(fraction * bar_length - 1) * "-" + ">"
    padding = int(bar_length - len(arrow)) * " "

    ending = "\n" if current == total else "\r"

    return (
        f"{string_in_front}{current}/{total}: [{arrow}{padding}] {int(fraction*100)}% ",
        ending,
    )


def dict_to_str(target: Dict[str, str]) -> str:
    if not isinstance(target, dict):
        raise TypeError(f"Expect a dict but '{type(target)}'")

    target_list = [f"{key}={value}" for key, value in target.items()]
    return "; ".join(target_list)


# path = "files/test4.html"
# with open (path, 'r', encoding='utf-8') as f:
#     content = f.read()
# result = checksum(content)
# print(result)
# print(str(hex(12648430)[2:]))
# print('str'.encode('utf-8'))
