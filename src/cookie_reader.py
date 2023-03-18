import base64
import json
import os
import sqlite3
import sys
from typing import ByteString, Dict, List, Tuple
from urllib.parse import urlparse

from Crypto.Cipher import AES
from Crypto.Protocol.KDF import PBKDF2


def retreive_windows_cookies_key() -> Tuple[ByteString, List[str]]:
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
    return decrypted_key, [cookie_file]


def retreive_mac_linux_cookies_key() -> Tuple[ByteString, List[str]]:
    import keyring

    salt = b"saltysalt"
    length = 16
    # If running Chrome on OSX
    if sys.platform == "darwin":
        my_pass = keyring.get_password("Chrome Safe Storage", "Chrome")
        my_pass = my_pass.encode("utf8")
        iterations = 1003
        cookie_file_header = os.path.expanduser(
            "~/Library/Application Support/Google/Chrome"
        )
        cookie_file_tail = "Cookies"
        possible_profiles = [
            profile
            for profile in os.listdir(cookie_file_header)
            if profile == "Default" or "Profile" in profile
        ]
        possible_cookie_files = [
            os.path.join(cookie_file_header, profile, cookie_file_tail)
            for profile in possible_profiles
        ]
    # If running Chrome on Linux
    elif sys.platform == "linux":
        my_pass = "peanuts".encode("utf8")
        iterations = 1
        possible_cookie_files = [
            os.path.expanduser("~/.config/chromium/Default/Cookies")
        ]
    else:
        raise Exception("This Method Only Support MacOS/Linux.")

    # Generate key from values above
    return PBKDF2(my_pass, salt, length, iterations), possible_cookie_files


def retreive_cookie_value(input: bytes | str, decrypted_key: ByteString) -> str:
    data = bytes(input)

    if sys.platform == "win32":
        nonce = data[3 : 3 + 12]
        ciphertext = data[3 + 12 : -16]
        tag = data[-16:]
        cipher = AES.new(decrypted_key, AES.MODE_GCM, nonce=nonce)
        # the decrypted cookie
        plaintext = cipher.decrypt_and_verify(ciphertext, tag)
        return plaintext.decode("utf-8")
    iv = b" " * 16
    ciphertext = data[3:]
    cipher = AES.new(decrypted_key, AES.MODE_CBC, IV=iv)
    from Crypto.Util.Padding import unpad

    plaintext = unpad(cipher.decrypt(ciphertext), AES.block_size)
    return plaintext.decode("utf-8")


def retreive_cookies(target_website: str, debug: bool = False) -> Dict[str, str]:
    if sys.platform == "win32":
        decrypted_key, possible_cookie_files = retreive_windows_cookies_key()
    elif sys.platform == "darwin":
        decrypted_key, possible_cookie_files = retreive_mac_linux_cookies_key()
    elif sys.platform == "linux":
        decrypted_key, possible_cookie_files = retreive_mac_linux_cookies_key()
    else:
        raise Exception("Only Support Windows/MacOS/Linux Chrome Cookie Extraction.")

    # Part of the domain name that will help the sqlite3 query pick it from the Chrome cookies
    domain = urlparse(target_website).netloc
    domain_no_sub = ".".join(domain.split(".")[-2:])
    # urlparse might need https:// header for a valid parse on MacOS
    if domain == "":
        domain = target_website
        domain_no_sub = target_website

    cookies = dict()
    for cookie_file in possible_cookie_files:
        connection = sqlite3.connect(cookie_file)
        connection.text_factory = bytes
        # host_key, path, secure, expires_utc, name, value, encrypted_value, is_httponly
        sql = f'select host_key, expires_utc, name, value, encrypted_value from cookies where host_key like "%{domain_no_sub}%"'

        with connection:
            for host_key, expire, key, value, encrypted_value in connection.execute(
                sql
            ):
                # if there is a not encrypted value or if the encrypted value
                # doesn't start with the 'v10' prefix, return v
                # if 'umass' in host_key.decode("utf-8"): print(host_key.decode("utf-8"))
                if host_key.decode("utf-8") not in domain:
                    continue
                if isinstance(key, bytes):
                    key = key.decode("utf-8")
                if value or (encrypted_value[:3] != b"v10"):
                    if isinstance(value, bytes):
                        value = value.decode("utf-8")
                    cookies[key] = value
                else:
                    decrypted_value = retreive_cookie_value(
                        encrypted_value, decrypted_key
                    )
                    cookies[key] = decrypted_value
    if len(list(cookies.keys())) == 0:
        raise Exception(
            f"No Cookie Stored for {target_website}. Please login to the website first!"
        )
    return cookies
