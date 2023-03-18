import base64
import json
import os
import sqlite3
import sys
from typing import ByteString, Dict, Tuple
from urllib.parse import urlparse

import keyring
from Crypto.Cipher import AES
from Crypto.Protocol.KDF import PBKDF2


def retreive_windows_cookies_key() -> Tuple[ByteString, str]:
    import win32crypt

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
    cookie_file = r"%LocalAppData%\Google\Chrome\User Data\Default\Network\Cookies"
    cookie_file = os.path.expandvars(cookie_file)
    return decrypted_key, cookie_file


def retreive_mac_linux_cookies_key() -> Tuple[ByteString, str]:
    # If running Chrome on OSX
    if sys.platform == "darwin":
        my_pass = keyring.get_password("Chrome Safe Storage", "Chrome")
        my_pass = my_pass.encode("utf8")
        iterations = 1003
        cookie_file = os.path.expanduser(
            "~/Library/Application Support/Google/Chrome/Default/Cookies"
        )
    # If running Chrome on Linux
    elif sys.platform == "linux":
        my_pass = "peanuts".encode("utf8")
        iterations = 1
        cookie_file = os.path.expanduser("~/.config/chromium/Default/Cookies")
    else:
        raise Exception("This Method Only Support MacOS/Linux.")

    # Generate key from values above
    return PBKDF2(my_pass, salt, length, iterations), cookie_file


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
    if sys.platform == "win32":
        decrypted_key, cookie_file = retreive_windows_cookies_key()
    elif sys.platform == "darwin":
        decrypted_key, cookie_file = retreive_mac_linux_cookies_key()
    elif sys.platform == "linux":
        decrypted_key, cookie_file = retreive_mac_linux_cookies_key()
    else:
        raise Exception("Only Support Windows/MacOS/Linux Chrome Cookie Extraction.")

    # Part of the domain name that will help the sqlite3 query pick it from the Chrome cookies
    domain = urlparse(target_website).netloc
    domain_no_sub = ".".join(domain.split(".")[-2:])

    connection = sqlite3.connect(cookie_file)
    connection.text_factory = bytes
    sql = f'select name, value, encrypted_value from cookies where host_key like "%{domain_no_sub}%"'

    cookies = dict()
    with connection:
        for key, value, encrypted_value in connection.execute(sql):
            # if there is a not encrypted value or if the encrypted value
            # doesn't start with the 'v10' prefix, return v
            if isinstance(key, bytes):
                key = key.decode("utf-8")
            if value or (encrypted_value[:3] != b"v10"):
                if isinstance(value, bytes):
                    value = value.decode("utf-8")
                cookies[key] = value
            else:
                decrypted_value = retreive_cookie_value(encrypted_value, decrypted_key)
                cookies[key] = decrypted_value
    return cookies


print(retreive_cookies("https://umass.moonami.com"))
# def chrome_decrypt(encrypted_value, key=None):

#         # Encrypted cookies should be prefixed with 'v10' according to the
#         # Chromium code. Strip it off.
#         encrypted_value = encrypted_value[3:]

#         # Strip padding by taking off number indicated by padding
#         # eg if last is '\x0e' then ord('\x0e') == 14, so take off 14.
#         # You'll need to change this function to use ord() for python2.
#         def clean(x):
#             return x[:-x[-1]].decode('utf8')

#         cipher = AES.new(key, AES.MODE_CBC, IV=iv)
#         decrypted = cipher.decrypt(encrypted_value)

#         return clean(decrypted)

# def chrome_cookies(url):

#     salt = b'saltysalt'
#     length = 16


#     if sys.platform == 'win32':
#         pass
#     else:
#         raise Exception("This script only works on OSX or Linux.")

#     # Generate key from values above
#     key = PBKDF2(my_pass, salt, length, iterations)


#     conn = sqlite3.connect(cookie_file)
#     sql = 'select name, value, encrypted_value from cookies '\
#             'where host_key like "%{}%"'.format(domain_no_sub)

#     cookies = {}
#     cookies_list = []

#     with conn:
#         for k, v, ev in conn.execute(sql):

#             # if there is a not encrypted value or if the encrypted value
#             # doesn't start with the 'v10' prefix, return v
#             if v or (ev[:3] != b'v10'):
#                 cookies_list.append((k, v))
#             else:
#                 decrypted_tuple = (k, chrome_decrypt(ev, key=key))
#                 cookies_list.append(decrypted_tuple)
#         cookies.update(cookies_list)

#     return cookies
