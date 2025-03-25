# qr_processor.py

import json
import qrcode
import zlib
import gzip
import base64
import cbor2
import subprocess
import logging
import xml.etree.ElementTree as ET

"""
This module handles the data processing for QR code generation. It provides functions to:
  - Process the input data (optionally compress/encode it)
  - Determine the optimal QR version based on data length and error correction level
  - Generate QR code images (or SVGs)
  - Extract essential details from ticket JSON and encode them with CBOR

Note: For any compression method (zlib, gzip, or cbor), Base64 encoding is automatically applied.
For plain text (method "none"), the data is left unchanged.
"""

def process_data(data, method):
    """
    Process input data based on the selected method.
    
    Behavior:
      - If method is "none", returns the original text unchanged.
      - For "zlib", "gzip", or "cbor":
          1. For "cbor", the input is first parsed as JSON and encoded to CBOR.
          2. For "zlib" or "gzip", the text is encoded to UTF-8 bytes.
          3. The data is compressed accordingly.
          4. The compressed bytes are automatically Base64‑encoded (so binary data can be safely embedded in the QR).
    
    :param data: Input data as a string.
    :param method: One of "none", "zlib", "gzip", or "cbor".
    :return: Processed data as a string.
    """
    original_bytes = data.encode('utf-8')
    logging.debug(f"[process_data] Original Data Size: {len(original_bytes)} bytes | Method: {method}")

    if method == "none":
        return data

    if method == "cbor":
        try:
            # Parse input as JSON then dump it as CBOR bytes.
            data = cbor2.dumps(json.loads(data))
            logging.debug(f"[process_data] CBOR Encoded Size: {len(data)} bytes")
        except Exception as e:
            logging.error(f"[process_data] CBOR Encoding Failed: {e}")
            return None
    else:
        # For gzip or zlib, encode text to bytes.
        data = data.encode('utf-8')

    if method == "gzip":
        data = gzip.compress(data)
        logging.debug(f"[process_data] Data compressed with gzip: {len(data)} bytes")
    elif method == "zlib":
        data = zlib.compress(data)
        logging.debug(f"[process_data] Data compressed with zlib: {len(data)} bytes")

    # Always apply Base64 encoding for compressed data.
    try:
        data = base64.b64encode(data).decode('utf-8')
        logging.debug(f"[process_data] Data Base64 encoded: {len(data.encode('utf-8'))} bytes")
    except Exception as e:
        logging.error(f"[process_data] Base64 Encoding Failed: {e}")
        return None

    return data
    
def determine_optimal_qr_version(data, compression_method, error_correction_level):
    """
    Determine the smallest QR version (1 to 40) that can hold the data.
    
    This is based on a capacity table for different error correction levels.
    
    :param data: The (uncompressed) data as a string.
    :param compression_method: (Not used in this calculation)
    :param error_correction_level: One of "L", "M", "Q", or "H".
    :return: The optimal QR version as an integer.
    """
    # QR Code capacity table (approximate maximum number of bytes that can be encoded) for each QR version and error correction level.
    qr_capacity = {
        "L": [25, 47, 77, 114, 154, 195, 224, 279, 335, 395, 468, 535, 619, 667, 758, 854, 938, 1046, 1153, 1249,
              1352, 1460, 1588, 1704, 1853, 1990, 2132, 2223, 2369, 2520, 2677, 2840, 3009, 3183, 3351, 3537, 3729,
              3927, 4087, 4296],
        "M": [20, 38, 61, 90, 122, 154, 178, 221, 262, 311, 366, 419, 483, 528, 600, 656, 734, 816, 909, 970,
              1035, 1134, 1248, 1326, 1451, 1542, 1637, 1732, 1839, 1994, 2113, 2238, 2369, 2506, 2632, 2780, 2923,
              3057, 3220, 3391],
        "Q": [16, 29, 47, 67, 87, 108, 125, 157, 189, 221, 259, 296, 336, 366, 419, 450, 512, 568, 614, 664,
              718, 754, 808, 871, 911, 985, 1033, 1115, 1171, 1231, 1286, 1354, 1426, 1502, 1582, 1666, 1754,
              1846, 1942, 2042],
        "H": [10, 20, 35, 50, 64, 84, 93, 122, 143, 174, 200, 227, 259, 283, 321, 365, 408, 452, 493, 535,
              593, 625, 658, 698, 742, 790, 842, 898, 958, 983, 1051, 1093, 1139, 1219, 1273, 1322, 1367, 1465,
              1528, 1594]
    }
    
    # Measure the data size in bytes (using UTF-8 encoding).
    data_length = len(data.encode('utf-8'))
    
    # Retrieve the capacity list for the given error correction level; default to "M" if not found.
    capacities = qr_capacity.get(error_correction_level, qr_capacity["M"])
    
    # Iterate through versions 1 to 40 (the list length) to find the smallest version
    # where the data_length fits within the capacity.
    for version, capacity in enumerate(capacities, start=1):
        if data_length <= capacity:
            return version

    # Fallback: if the data exceeds the capacity of even version 40, return 40.
    return 40

def generate_qr_code(data, qr_version=1, error_correction=qrcode.constants.ERROR_CORRECT_M, box_size=4, border=4):
    """
    Generate a QR code image using the qrcode library.
    
    :param data: The payload data as a string (processed with process_data).
    :param qr_version: The desired QR code version.
    :param error_correction: The error correction constant.
    :param box_size: Size of each QR code box.
    :param border: Width of the border.
    :return: A PIL Image of the generated QR code.
    """
    qr = qrcode.QRCode(
        version=qr_version,
        error_correction=error_correction,
        box_size=box_size,
        border=border
    )
    qr.add_data(data)
    qr.make(fit=True)
    return qr.make_image(fill_color="black", back_color="white")

def generate_svg(qr, file_path):
    """
    Generate an optimized SVG file from the given QR code object.
    
    Instead of adding a separate <path> command for every single black module,
    this function scans each row of the QR matrix and groups contiguous black modules 
    into one rectangle command. This reduces the number of commands and typically 
    produces a smaller file size compared to the unoptimized version.
    
    The SVG is created with a background white rectangle and a single <path> element 
    that draws all the black modules.
    
    :param qr: A QRCode object that has been prepared (using qrcode.QRCode).
    :param file_path: The path where the SVG file will be saved.
    """

   # Retrieve the QR code matrix (a 2D list of booleans indicating black/white modules).
    qr_matrix = qr.modules
    size = len(qr_matrix)
    
    # Define the pixel size for each module. This determines the overall resolution.
    pixel_size = 4
    svg_size = size * pixel_size
    viewBox = f"0 0 {size} {size}"
    
    # Create the SVG root element.
    svg = ET.Element("svg", xmlns="http://www.w3.org/2000/svg", viewBox=viewBox,
                     width=str(svg_size), height=str(svg_size))
    
    # Add a white background rectangle.
    ET.SubElement(svg, "rect", width="100%", height="100%", fill="white")
    
    # Build a list of path commands that represent contiguous black modules.
    path_commands = []
    # Iterate through each row of the QR matrix.
    for y, row in enumerate(qr_matrix):
        x = 0
        while x < len(row):
            if row[x]:
                # Found the beginning of a contiguous block of black modules.
                start_x = x
                while x < len(row) and row[x]:
                    x += 1
                width = x - start_x
                """
                Create a rectangle for this block:
                  - M{start_x},{y} moves to the starting module,
                  - h{width} draws a horizontal line covering the contiguous block,
                  - v1 draws a vertical line down one module,
                  - h-{width} draws a horizontal line back to the starting x position,
                  - z closes the path.
                """
                path_commands.append(f"M{start_x},{y}h{width}v1h-{width}z")
            else:
                x += 1
    # If any black modules were found, create a single <path> element.
    if path_commands:
        path_data = " ".join(path_commands)
        ET.SubElement(svg, "path", d=path_data, fill="black")
    
    # Write the final SVG tree to the specified file.
    tree = ET.ElementTree(svg)
    tree.write(file_path)

def optimise_svg(svg_file_path):
    """
    Optimise the SVG file using the SVGO command-line tool.

    This function calls the external SVGO (SVG Optimizer) tool via a subprocess to further reduce
    the file size of the generated SVG QR code. Depending on the content of the QR code, SVGO can
    reduce the file size by around 20% on average, leading to a more compact vector graphic.

    Requirements and configuration:
      - SVGO must be installed on the system (e.g., via npm using "npm install -g svgo").
      - It is assumed that SVGO is available in the system's PATH. If not, you can specify the full
        path to the svgo.cmd (or equivalent) executable.
      - The subprocess is run with shell=True, which is necessary on Windows to properly locate
        and execute the command. Without shell=True, you might encounter errors such as
        "[WinError 5] Access is denied".
      
    Error handling:
      - If the SVGO command fails (for instance, due to permission issues or an incorrect path),
        the function logs an error message. The QR code generation process continues even if
        SVG optimisation fails.

    Link to the repository: https://github.com/svg/svgo
    
    :param svg_file_path: The file path to the SVG file that should be optimised.
    """
    try:
        # Run the SVGO command on the specified SVG file.
        subprocess.run(["svgo", svg_file_path], check=True, shell=True)
        logging.debug(f"SVG optimized successfully: {svg_file_path}")
    except Exception as e:
        logging.error(f"SVG optimisation failed: {e}")

def extract_essential_ticket_details(json_data):
    """
    Extract only the essential fields from a full ticket JSON.
    
    :param json_data: Dictionary with full ticket data.
    :return: Dictionary containing only essential fields.
    """
    extracted = {
        "provider": json_data.get("provider", ""),
        "ticket_id": json_data.get("ticket_id", ""),
        "ticket_type": json_data.get("ticket_type", ""),
        "departure_time": json_data.get("departure_time", ""),
        "arrival_time": json_data.get("arrival_time", ""),
        "train": f"{json_data.get('train_number', '')} ({json_data.get('train_operator', '')})",
        "from": json_data.get("station_start", {}).get("name", ""),
        "to": json_data.get("station_end", {}).get("name", ""),
        "coach": json_data.get("coach", ""),
        "seat": json_data.get("seat_number", ""),
        "class": json_data.get("class", ""),
        "price": f"{json_data.get('price', 0.00)} {json_data.get('currency', '')}",
        "status": json_data.get("payment_status", ""),
        "reference": json_data.get("reference_number", ""),
        "passenger": f"{json_data.get('holder', {}).get('first_name', '')} {json_data.get('holder', {}).get('last_name', '')}",
        "security_hash": json_data.get("security_hash", "")
    }
    logging.debug(f"Extracted data: {extracted}")
    return extracted

def encode_ticket_details_to_cbor(json_string, use_base64=True):
    """
    Given a JSON string of full ticket details, extract only the essential fields,
    encode the result to CBOR, and optionally Base64‑encode it.
    
    :param json_string: Full ticket JSON as a string.
    :param use_base64: If True, return a Base64‑encoded string; otherwise return bytes.
    :return: The CBOR‑encoded ticket details.
    """
    try:
        json_data = json.loads(json_string)
        essential_data = extract_essential_ticket_details(json_data)
        cbor_encoded = cbor2.dumps(essential_data)
        logging.debug(f"[encode_ticket_details_to_cbor] CBOR encoded data size: {len(cbor_encoded)} bytes")
        if use_base64:
            b64_encoded = base64.b64encode(cbor_encoded).decode('utf-8')
            logging.debug(f"[encode_ticket_details_to_cbor] Base64 encoded CBOR size: {len(b64_encoded.encode('utf-8'))} bytes")
            return b64_encoded
        else:
            return cbor_encoded
    except Exception as e:
        logging.error(f"[encode_ticket_details_to_cbor] Failed to encode to CBOR: {e}")
        return None