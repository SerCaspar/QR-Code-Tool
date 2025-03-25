import unittest
import itertools
import json
import base64
import zlib
import gzip
import cbor2
import qrcode
import numpy as np
from qr_processor import (
    process_data, determine_optimal_qr_version, generate_qr_code,
    extract_essential_ticket_details, encode_ticket_details_to_cbor
)
from qr_decoder import decompress_data, decode_qr_image, decode_qr_data
from qr_quality import check_qr_quality, optimize_qr_for_scanning
from PIL import Image

import logging
import io
import tempfile
import os
import textwrap

"""
This module contains unit tests for the QR processing functions.
Run tests with: python -m unittest test_qr_processor.py

Logging enhancements:
  - A base class (LoggedTestCase) logs a friendly header for each test.
  - Separator lines clearly mark test boundaries.
  - Multi-line log messages are dedented and then uniformly indented by 4 spaces.
"""

# Define a custom formatter that dedents and re-indents multi-line messages.
class IndentFormatter(logging.Formatter):
    def format(self, record):
        message = super().format(record)
        lines = message.splitlines()
        if len(lines) > 1:
            # Dedent the subsequent lines, then indent them by 4 spaces.
            block = "\n".join(lines[1:])
            block = textwrap.dedent(block)
            indented_block = textwrap.indent(block, "                                  ")
            message = lines[0] + "\n" + indented_block
        return message

# Configure logging with the custom formatter.
log_handler = logging.FileHandler("unittest.log", mode="w", encoding="utf-8")
log_handler.setLevel(logging.DEBUG)
log_formatter = IndentFormatter("%(asctime)s - %(levelname)s - %(message)s")
log_handler.setFormatter(log_formatter)
root_logger = logging.getLogger()
root_logger.handlers = []  # Clear any default handlers.
root_logger.addHandler(log_handler)
root_logger.setLevel(logging.DEBUG)

# A custom logging handler to capture log records for test verification.
class LogCaptureHandler(logging.Handler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.records = []
    def emit(self, record):
        self.records.append(record)

# Base class to add friendly logging for each test.
class LoggedTestCase(unittest.TestCase):
    def setUp(self):
        # Use the class name as the logger name.
        self.logger = logging.getLogger(self.__class__.__name__)
        # Compute a friendly test name from the full test id.
        self.friendly_name = self.friendly_test_name(self.id())
        self.logger.debug("=" * 80)
        self.logger.debug("Test: %s", self.friendly_name)
        self.logger.debug("=" * 80)
        self.logger.debug("# Starting test: %s", self.id())
    def tearDown(self):
        self.logger.debug("# Finished test: %s", self.id())
    def friendly_test_name(self, test_id):
        # Convert a test id like "test_qr_processor.TestQRProcessing.test_auto_detection_with_zlib"
        # into "Auto Detection With Zlib"
        parts = test_id.split('.')
        method_name = parts[-1]
        if method_name.startswith("test_"):
            method_name = method_name[5:]
        return method_name.replace('_', ' ').title()

# Now update each test class to inherit from LoggedTestCase.

class TestQRProcessingWithLogs(LoggedTestCase):
    def setUp(self):
        super().setUp()
        # Setup custom log capture handler.
        self.log_handler = LogCaptureHandler()
        self.log_handler.setLevel(logging.DEBUG)
        self.logger.addHandler(self.log_handler)
        self.payload = "This is a test payload for QR code generation."
    def tearDown(self):
        super().tearDown()
        self.logger.removeHandler(self.log_handler)
        # Optionally dump captured logs if errors occurred.
        error_logs = [r for r in self.log_handler.records if r.levelno >= logging.ERROR]
        if error_logs:
            for record in self.log_handler.records:
                self.logger.error("Captured log: %s", record.getMessage())

    def test_no_error_logs_plaintext(self):
        self.logger.debug("Testing process_data and decompress_data with plaintext payload.")
        processed = process_data(self.payload, method="none")
        self.logger.debug("Processed output: %s", processed)
        decompressed = decompress_data(processed, method="none")
        self.logger.debug("Decompressed output: %s", decompressed)
        self.assertEqual(decompressed, self.payload)
        error_logs = [r for r in self.log_handler.records if r.levelno >= logging.ERROR]
        self.assertEqual(len(error_logs), 0, "There were error messages in the logs.")

class TestQRProcessing(LoggedTestCase):
    def setUp(self):
        super().setUp()
        self.txt_data = "This is a sample plain text for testing QR code generation."
        self.json_data = json.dumps({"message": "Hello, world!", "value": 42})
    def test_plaintext_no_compression_no_base64(self):
        self.logger.debug("Starting test_plaintext_no_compression_no_base64 with data: %s", self.txt_data)
        processed = process_data(self.txt_data, method="none")
        self.logger.debug("Processed data: \n%s", processed)
        decompressed = decompress_data(processed, method="none")
        self.logger.debug("Decompressed data: \n%s", decompressed)
        self.assertEqual(processed, self.txt_data)
        self.assertEqual(decompressed, self.txt_data)
    def test_plaintext_with_zlib_and_base64(self):
        self.logger.debug("Starting test_plaintext_with_zlib_and_base64 with data: %s", self.txt_data)
        processed = process_data(self.txt_data, method="zlib")
        self.logger.debug("Processed data: \n%s", processed)
        decompressed = decompress_data(processed, method="auto")
        self.logger.debug("Decompressed data: \n%s", decompressed)
        self.assertEqual(decompressed, self.txt_data)
    def test_plaintext_with_gzip_and_base64(self):
        self.logger.debug("Starting test_plaintext_with_gzip_and_base64 with data: %s", self.txt_data)
        processed = process_data(self.txt_data, method="gzip")
        self.logger.debug("Processed data: \n%s", processed)
        decompressed = decompress_data(processed, method="auto")
        self.logger.debug("Decompressed data: \n%s", decompressed)
        self.assertEqual(decompressed, self.txt_data)
    def test_json_with_cbor_and_base64(self):
        self.logger.debug("Starting test_json_with_cbor_and_base64 with data: %s", self.json_data)
        processed = process_data(self.json_data, method="cbor")
        self.logger.debug("Processed data: \n%s", processed)
        decompressed = decompress_data(processed, method="auto")
        self.logger.debug("Decompressed data: \n%s", decompressed)
        self.assertEqual(json.loads(decompressed), json.loads(self.json_data))
    def test_generate_qr_image_returns_pil(self):
        self.logger.debug("Starting test_generate_qr_image_returns_pil with data: %s", self.txt_data)
        processed = process_data(self.txt_data, method="none")
        self.logger.debug("Processed data: \n%s", processed)
        qr_img = generate_qr_code(processed, qr_version=1, error_correction=qrcode.constants.ERROR_CORRECT_M)
        if hasattr(qr_img, "get_image"):
            img = qr_img.get_image()
            self.logger.debug("Obtained image via get_image method.")
        else:
            img = qr_img
            self.logger.debug("Obtained image directly.")
        self.assertTrue(isinstance(img, Image.Image))
    def test_determine_optimal_qr_version(self):
        self.logger.debug("Starting test_determine_optimal_qr_version")
        small_text = "Short text"
        large_text = "A" * 1000
        version_small = determine_optimal_qr_version(small_text, "none", "M")
        self.logger.debug("Optimal QR version for small text: %s", version_small)
        version_large = determine_optimal_qr_version(large_text, "none", "M")
        self.logger.debug("Optimal QR version for large text: %s", version_large)
        self.assertTrue(version_small < version_large)
    def test_decode_qr_image(self):
        self.logger.debug("Starting test_decode_qr_image")
        payload = "Test payload for QR decoding."
        processed = process_data(payload, method="none")
        self.logger.debug("Processed payload: %s", processed)
        qr_img = generate_qr_code(processed, qr_version=1, error_correction=qrcode.constants.ERROR_CORRECT_M)
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
            tmp_filename = tmp.name
            qr_img.save(tmp_filename, optimize=True)
            self.logger.debug("Saved QR image to temporary file: %s", tmp_filename)
        decoded = decode_qr_image(tmp_filename)
        self.logger.debug("Decoded payload from QR image: %s", decoded)
        os.remove(tmp_filename)
        self.logger.debug("Removed temporary file: %s", tmp_filename)
        self.assertEqual(decoded, payload)
    def test_auto_detection_with_zlib(self):
        self.logger.debug("Starting test_auto_detection_with_zlib with data: %s", self.txt_data)
        processed = process_data(self.txt_data, method="zlib")
        self.logger.debug("Processed data: \n%s", processed)
        decompressed = decompress_data(processed, method="auto")
        self.logger.debug("Decompressed data: \n%s", decompressed)
        self.assertEqual(decompressed, self.txt_data)

class TestQRQuality(LoggedTestCase):
    def setUp(self):
        super().setUp()
        self.img = Image.new("RGB", (100, 100), "white")
        for x in range(100):
            self.img.putpixel((x, 0), (0, 0, 0))
            self.img.putpixel((x, 99), (0, 0, 0))
        for y in range(100):
            self.img.putpixel((0, y), (0, 0, 0))
            self.img.putpixel((99, y), (0, 0, 0))
    def test_check_qr_quality_returns_expected_format(self):
        self.logger.debug("Starting test_check_qr_quality_returns_expected_format")
        quality_str = check_qr_quality(self.img)
        self.logger.debug("QR quality string: %s", quality_str)
        self.assertIn("Contrast Ratio:", quality_str)
        self.assertIn("Quiet Zone", quality_str)
        self.assertIn("Readability Score:", quality_str)
    def test_optimize_qr_for_scanning_returns_pil_image(self):
        self.logger.debug("Starting test_optimize_qr_for_scanning_returns_pil_image")
        optimized_img = optimize_qr_for_scanning(self.img)
        self.logger.debug("Obtained optimised image.")
        self.assertIsInstance(optimized_img, Image.Image)

class TestTicketEncoding(LoggedTestCase):
    def setUp(self):
        super().setUp()
        self.full_json = {
            "provider": "TRAIN TICKET COMPANY",
            "ticket_id": "78433201",
            "ticket_type": "Full",
            "ticket_type_details": "Standard fare, fully refundable",
            "departure_time": "2025-03-17T15:35:00Z",
            "arrival_time": "2025-03-17T23:05:00Z",
            "train_number": "IC 2045",
            "train_operator": "National Rail",
            "route_id": "NR-2045-2025-03-17",
            "coach": "B",
            "seat_number": "32A",
            "platform_start": "4",
            "platform_end": "12",
            "stops": [
                {"station_id": "110050", "station_name": "Station M", "arrival_time": "17:10", "departure_time": "17:15"},
                {"station_id": "110080", "station_name": "Station N", "arrival_time": "19:30", "departure_time": "19:35"}
            ],
            "station_start": {"id": "110001", "name": "Station L", "city": "City X", "country": "Country Y"},
            "station_end": {"id": "112100", "name": "Station O", "city": "City Z", "country": "Country Y"},
            "class": "2nd Class",
            "currency": "EUR",
            "price": 115.00,
            "payment_method": "Credit Card",
            "payment_status": "Paid",
            "booking_date": "2025-03-10T14:45:00Z",
            "reference_number": "784AP43B2-33905D-0001",
            "holder": {"holder_id": "CUST-568902", "first_name": "John", "last_name": "Doe"},
            "security_hash": "La=oPG9h2uHdh3jqA194GMKw1K4=KXUJ+oq4Uh1IoXxZ+D6hHOzZ42w/gEdNGgGCo08/HHOnc=yyC=eytxHAPDMOphsPKUHMvnqgu3tWtdfjYRBQlHfNATrlh6sL1h1TpnZ7cV0gBOx+dVXmAemO+pRfH=PCyxDzFdcrzLGu+G/a=XX+bnBHO+eSiN9KyS76Df=Z9OiXSYyg5bB+d+XFVo=0u0OGPcReJ5DUody3f6vDYdy8srLv49n3=xVjoQIg"
        }
        self.json_string = json.dumps(self.full_json)
    def test_extract_essential(self):
        self.logger.debug("Starting test_extract_essential")
        essential = extract_essential_ticket_details(self.full_json)
        self.logger.debug("Extracted essential ticket details: %s", essential)
        expected_keys = [
            "provider", "ticket_id", "ticket_type", "departure_time", "arrival_time",
            "train", "from", "to", "coach", "seat", "class", "price", "status",
            "reference", "passenger", "security_hash"
        ]
        for key in expected_keys:
            self.assertIn(key, essential)
        self.assertEqual(essential["ticket_id"], "78433201")
    def test_cbor_encoding_with_base64(self):
        self.logger.debug("Starting test_cbor_encoding_with_base64")
        encoded = encode_ticket_details_to_cbor(self.json_string, use_base64=True)
        self.logger.debug("Encoded CBOR string: %s", encoded)
        self.assertIsInstance(encoded, str)
        decoded_bytes = base64.b64decode(encoded.encode('utf-8'))
        decoded = cbor2.loads(decoded_bytes)
        essential = extract_essential_ticket_details(self.full_json)
        self.logger.debug("Decoded CBOR to: %s", decoded)
        self.assertEqual(decoded, essential)

class TestRoundTripPlainText(LoggedTestCase):
    def setUp(self):
        super().setUp()
        self.payloads = [
            "This is a test payload for QR code generation.",
            "¡Hola! ¿Cómo estás?",
            "Привіт, як справи?",
            "你好，世界",
            "مرحبا بالعالم",
            "こんにちは世界",
            "안녕하세요, 세계",
            "Line1\nLine2\nLine3",
            "Payload: #$%^&*() - Testing, 1, 2, 3!",
            "1234567890" * 10
        ]
    def test_combinations_plaintext(self):
        self.logger.debug("Starting test_combinations_plaintext for multiple payloads")
        for payload in self.payloads:
            with self.subTest(payload=payload):
                self.logger.debug("Testing payload:\n%s", payload)
                processed = process_data(payload, method="none")
                self.logger.debug("Processed data:\n%s", processed)
                decompressed = decompress_data(processed, method="none")
                self.logger.debug("Decompressed data:\n%s", decompressed)
                self.assertEqual(decompressed, payload)

if __name__ == "__main__":
    unittest.main()