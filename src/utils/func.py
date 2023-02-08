def checksum(input: str | bytes, num: int = 8) -> str:
    if not isinstance(input, bytes):
        input = input.encode("utf-8")
    sum = 0
    for i in range(len(input)):
        sum += input[i]
    return format(int(sum % pow(10, num)), f"0{num}d")


# path = "files/test4.html"
# with open (path, 'r', encoding='utf-8') as f:
#     content = f.read()
# result = checksum(content)
# print(result)
# print(str(hex(12648430)[2:]))
# print('str'.encode('utf-8'))
