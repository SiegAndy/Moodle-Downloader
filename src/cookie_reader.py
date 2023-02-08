import os
import json
import sqlite3
import base64
import win32crypt
from typing import ByteString, Dict
from Crypto.Cipher import AES


def retreive_cookies_key() -> ByteString:
    key_path = r"%LocalAppData%\Google\Chrome\User Data\Local State"
    key_path = os.path.expandvars(key_path)
    with open(key_path, "r") as file:
        encrypted_key = json.loads(file.read())["os_crypt"]["encrypted_key"]

    # Base64 decoding
    encrypted_key = base64.b64decode(encrypted_key)
    # Remove DPAPI
    encrypted_key = encrypted_key[5:]
    # Decrypt key
    decrypted_key = win32crypt.CryptUnprotectData(encrypted_key, None, None, None, 0)[1]
    # print(decrypted_key)
    return decrypted_key


def retreive_cookie_value(input: bytes | str, decrypted_key: ByteString) -> str:
    data = bytes(input)
    nonce = data[3 : 3 + 12]
    ciphertext = data[3 + 12 : -16]
    tag = data[-16:]
    cipher = AES.new(decrypted_key, AES.MODE_GCM, nonce=nonce)
    # the decrypted cookie
    plaintext = cipher.decrypt_and_verify(ciphertext, tag)
    return plaintext.decode("utf-8")


def retreive_cookies(target_website: str, debug: bool = False) -> Dict[str, str]:
    decrypted_key = retreive_cookies_key()

    cookie_file = r"%LocalAppData%\Google\Chrome\User Data\Default\Network\Cookies"
    cookie_file = os.path.expandvars(cookie_file)
    connection = sqlite3.connect(cookie_file)
    cursor = connection.cursor()
    cursor.execute("SELECT * FROM cookies;")
    entries = cursor.fetchall()

    cookies = dict()
    for curr in entries:
        site = curr[1]
        name = curr[3]
        encrypted_value = bytes(curr[5])
        is_site = site.find(target_website) > -1
        if is_site:
            decrypted_value = retreive_cookie_value(encrypted_value, decrypted_key)
            cookies[name] = decrypted_value
            if debug:
                print(f"{site}:")
                print(f"cookie name :\t{name}")
                print(f"cookie value:\t{decrypted_value}\n")
    cursor.close()
    connection.close()
    return cookies
