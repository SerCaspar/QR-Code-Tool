# qr_decoder.py

import re
import json
import base64
import zlib
import gzip
import cbor2
import logging
import cv2
import numpy as np
from pyzbar.pyzbar import decode
from PIL import Image

"""
This module provides functions for decoding QR codes:
  - is_base64_string() checks whether a string is Base64‑encoded.
  - decompress_data() automatically reverses the encoding performed by process_data().
    It automatically decodes Base64 and then auto‑detects whether the data was compressed
    with gzip, zlib, or encoded as CBOR.
  - decode_qr_image() loads an image file, detects and decodes the first QR code,
    and returns its data as a UTF‑8 string.
  - decode_json_qr() and decode_qr_data() provide additional JSON processing.
"""

def is_base64_string(s):
    """
    Check if the string 's' appears to be Base64‑encoded using a round‑trip check.
    
    :param s: Input string.
    :return: True if s is Base64‑encoded; otherwise False.
    """
    s = s.strip()
    if len(s) % 4 != 0:
        return False
    if not re.fullmatch(r'^[A-Za-z0-9+/]+={0,2}$', s):
        return False
    try:
        decoded = base64.b64decode(s, validate=True)
        reencoded = base64.b64encode(decoded).decode('utf-8')
        return reencoded.rstrip('=') == s.rstrip('=')
    except Exception:
        return False

def decompress_data(data, method="auto"):
    """
    Reverse the processing performed by process_data().
    
    For method "none", returns the data as plain text.
    Otherwise, it:
      1. Checks if the data is Base64‑encoded; if not, it returns the input.
      2. Decodes the data from Base64.
      3. If method=="auto", auto-detects compression based on header bytes:
            - gzip if the bytes start with 0x1f8b,
            - zlib if the first two bytes match common zlib headers,
            - otherwise attempts CBOR decoding.
      4. Decompresses (or decodes CBOR) accordingly and returns a UTF‑8 string.
    
    :param data: Encoded data as a string.
    :param method: Compression method ("none", "zlib", "gzip", "cbor", or "auto").
    :return: Decompressed data as a UTF‑8 string.
    """
    if method == "none":
        logging.debug("[decompress_data] Method 'none' provided; returning plain text.")
        return data

    logging.debug(f"[decompress_data] Received data (first 100 chars): {repr(data[:100])}")
    logging.debug(f"[decompress_data] Initial method parameter: {method}")

    # Check if the data is Base64‑encoded automatically.
    if not is_base64_string(data):
        logging.debug("[decompress_data] No Base64 encoding detected; treating data as plain text.")
        return data

    try:
        data_bytes = base64.b64decode(data.encode('utf-8'))
        logging.debug(f"[decompress_data] After Base64 decode: {len(data_bytes)} bytes; Header: {data_bytes[:4].hex()}")
    except Exception as e:
        logging.error(f"[decompress_data] Base64 decoding failed: {e}")
        return data

    # If method is auto, detect compression by inspecting header bytes.
    if method == "auto":
        if data_bytes.startswith(b'\x1f\x8b'):
            method = "gzip"
        elif data_bytes[:2] in (b'\x78\x01', b'\x78\x5e', b'\x78\x9c', b'\x78\xda'):
            method = "zlib"
        else:
            try:
                _ = cbor2.loads(data_bytes)
                method = "cbor"
            except Exception:
                method = "none"
        logging.debug(f"[decompress_data] Auto-detected compression method: {method}")

    try:
        if method == "none":
            return data_bytes.decode('utf-8')
        elif method == "zlib":
            decompressed = zlib.decompress(data_bytes)
            logging.debug(f"[decompress_data] After zlib decompression: {len(decompressed)} bytes")
            return decompressed.decode('utf-8')
        elif method == "gzip":
            decompressed = gzip.decompress(data_bytes)
            logging.debug(f"[decompress_data] After gzip decompression: {len(decompressed)} bytes")
            return decompressed.decode('utf-8')
        elif method == "cbor":
            result = cbor2.loads(data_bytes)
            decompressed = json.dumps(result, indent=4)
            logging.debug(f"[decompress_data] After CBOR decoding: {len(decompressed.encode('utf-8'))} bytes")
            return decompressed
        else:
            logging.error(f"[decompress_data] Unknown method: {method}")
            return data_bytes.decode('utf-8', errors='replace')
    except Exception as e:
        logging.error(f"[decompress_data] Decompression error for method {method}: {e}")
        return data_bytes.decode('utf-8', errors='replace')

def decode_qr_image(file_path):
    """
    Load an image from 'file_path', detect the first QR code, and return its decoded data as a string.
    
    The function always attempts to decode the raw bytes using UTF-8.
    
    :param file_path: Path to the image file containing the QR code.
    :return: Decoded QR code data as a string.
    """
    image = cv2.imread(file_path)
    if image is None:
        logging.error("Could not read image.")
        return None

    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    qr_codes = decode(gray)
    if not qr_codes:
        logging.error("No QR code detected in the image.")
        return None

    raw_data = qr_codes[0].data  # Raw bytes from the QR code.
    try:
        decoded_str = raw_data.decode("utf-8").strip()
        logging.debug(f"[decode_qr_image] Decoded using UTF-8: {decoded_str[:100]}")
    except Exception as e:
        logging.error(f"[decode_qr_image] UTF-8 decoding failed: {e}. Falling back to Latin-1.")
        decoded_str = raw_data.decode("latin1", errors="replace").strip()
    
    return decoded_str

def decode_json_qr(data):
    """
    Attempt to decode JSON content from the provided string.
    
    :param data: Input string.
    :return: Parsed JSON object (dictionary) or None if decoding fails.
    """
    try:
        parsed_data = json.loads(data)
        return parsed_data
    except json.JSONDecodeError:
        logging.error("Failed to decode JSON.")
        return None

def decode_qr_data(data):
    """
    Attempt to parse input data as JSON. If successful, remove the 'gen_ver' field and
    return a pretty-printed JSON string. If parsing fails, return the data as-is.
    
    :param data: Decoded QR code data as a string.
    :return: Pretty-printed JSON string or the original string.
    """
    try:
        parsed = json.loads(data)
        if isinstance(parsed, dict) and "gen_ver" in parsed:
            del parsed["gen_ver"]
        return json.dumps(parsed, indent=4)
    except Exception as e:
        return data