# QR Code Tool

QR Code Tool is a versatile desktop application designed to generate, decode, assess, and optimise QR codes. It is particularly useful for ticketing systems and other structured data applications. With built-in support for various compression techniques and data encodings, this tool streamlines QR code operations and ensures high-quality outputs.

## Table of Contents

- [Features](#features)
- [Installation](#installation)
  - [Python Requirements](#python-requirements)
  - [System Dependencies](#system-dependencies)
- [Usage](#usage)
  - [Starting the Application](#starting-the-application)
  - [Generating QR Codes](#generating-qr-codes)
  - [Decoding QR Codes](#decoding-qr-codes)
  - [Assessing QR Quality](#assessing-qr-quality)
  - [Batch Processing](#batch-processing)
- [Testing](#testing)
- [Project Structure](#project-structure)
- [Logging](#logging)
- [License](#license)

## Features

- **QR Code Generation**  
  Create QR codes from plain text or JSON data, with options for compression (`zlib`, `gzip`) or CBOR encoding (with Base64 wrapping).

- **Auto-detection and Decoding**  
  Automatically detect and decode various compression formats when scanning QR codes from images or pasted data.

- **Quality Assessment**  
  Evaluate QR code quality by checking contrast, quiet zones, data density, and a readability score.

- **SVG Optimisation**  
  Generate SVG files from QR codes and optionally optimise them using SVGO for a smaller file size.

- **User-Friendly GUI**  
  A Tkinter-based interface that supports theme toggling (light/dark) and provides a preview of the generated QR codes.

- **Batch Processing**  
  Process multiple TXT or JSON files from a selected folder to generate QR codes in bulk.

## Installation

### Python Requirements

Ensure you have Python 3.8 or newer installed.

Install the necessary Python packages using the provided `requirements.txt`:

```bash
pip install -r requirements.txt
```

Alternatively, install the dependencies manually:

```bash
pip install pillow qrcode pyzbar opencv-python cbor2 numpy
```

### System Dependencies

#### ZBar (for QR decoding via `pyzbar`)

- **Ubuntu/Debian**:  
  ```bash
  sudo apt install libzbar0
  ```
- **macOS**:  
  ```bash
  brew install zbar
  ```
- **Windows**:  
  [Manual installation required](https://github.com/NaturalHistoryMuseum/pyzbar#installation)

#### SVGO (Optional, for SVG optimisation)

- Requires [Node.js](https://nodejs.org/)  
- Install globally via npm:  
  ```bash
  npm install -g svgo
  ```

## Usage

### Starting the Application

Run the following command to launch the graphical user interface:

```bash
python main.py
```

### Generating QR Codes

1. **File Selection**: Choose a TXT or JSON file containing the data.
2. **Options**:  
   - Select compression method and error correction level.  
   - Enable debug information or auto-determination of the QR version.  
   - Choose output format (PNG or SVG).
3. **Preview & Save**:  
   - Optionally preview the QR code before saving.  
   - The file is saved automatically in the `generated_qr` folder or via a custom save dialog.

### Decoding QR Codes

- Load an image file (PNG, JPG, etc.) containing a QR code.  
- The tool automatically detects and decodes the data, displaying the output in a text window.  
- You can also paste QR data directly into the provided text box for decoding.

### Assessing QR Quality

- Open a QR code image and the tool will analyse its quality based on contrast, quiet zone integrity, and data density.
- A detailed quality report is then displayed, assisting in ensuring the QR code is scan-friendly.

### Batch Processing

- Select a folder containing multiple TXT/JSON files.
- QR codes are generated for each file, with the results saved in the `generated_qr` directory.
- Each generated file includes metadata such as use case, compression method, and timestamp.

## Testing

Unit tests are provided to ensure the reliability of the core functionalities. Run the tests with:

```bash
python -m unittest test_qr_processor.py
```

Test logs are saved to `unittest.log` for review.

## Project Structure

```text
.
├── gui.py                # Tkinter-based GUI implementation
├── main.py               # Entry point and logging setup
├── qr_processor.py       # QR generation, compression, and encoding logic
├── qr_decoder.py         # QR decoding and decompression functionality
├── qr_quality.py         # QR image quality assessment and optimisation
├── test_qr_processor.py  # Unit tests for core functionality
├── generated_qr/         # Auto-created directory for output QR codes
└── README.md             # Project documentation (this file)
```

## Logging

- **Application Logs**: Stored in `qr_processor.log`
- **Test Logs**: Saved in `unittest.log`

Logging helps track the internal processes and aids in debugging or verifying operations.

## License

This project is licensed under the MIT License. Please refer to the `LICENSE` file for more details.
