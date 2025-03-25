# gui.py

import tkinter as tk
from tkinter import filedialog, messagebox
from qr_processor import (
    process_data, generate_qr_code, generate_svg, optimise_svg,
    determine_optimal_qr_version, extract_essential_ticket_details,
    encode_ticket_details_to_cbor
)
from qr_decoder import decompress_data, decode_qr_image, decode_qr_data
from qr_quality import check_qr_quality, optimize_qr_for_scanning
import qrcode
import logging
import os
import json
from datetime import datetime
from PIL import ImageTk, Image

"""
This module implements the graphical user interface (GUI) for the QR Code Tool using Tkinter.
It handles:
  - File selection for generating or decoding QR codes.
  - Displaying options (such as compression method, error correction, theme, etc.).
  - Generating QR codes by calling functions in qr_processor.py.
  - Decoding QR codes by calling functions in qr_decoder.py.
"""

# Global Tkinter variables will be initialized after creating the root window.
auto_save_var = None            # If True, QR codes are auto-saved in the "generated_qr" folder.
output_format_var = None        # "png" or "svg"
use_case_var = None             # Use case identifier, e.g., "auto"
compression_var = None          # Compression/encoding method: "none", "zlib", "gzip", or "cbor"
base64_var = None               # Used for generation only (for filename display)
debug_var = None                # Toggle for including debug information in the generated payload.
auto_version_var = None         # Toggle for auto-selecting QR version.
error_correction_var = None     # Selected error correction level ("L", "M", "Q", "H")
preview_var = None              # Toggle to show a preview after QR generation.
extract_essential_var = None    # Toggle to extract only essential JSON fields.
display_text = None             # Text widget to display decoded text or quality info.
paste_text = None               # Text widget for pasting QR data.
current_theme = None            # Stores the current theme: "light" or "dark"
root = None                     # Root variable for the Tkinter   

# Mapping for error correction levels.
error_correction_mapping = {
    "L": qrcode.constants.ERROR_CORRECT_L,
    "M": qrcode.constants.ERROR_CORRECT_M,
    "Q": qrcode.constants.ERROR_CORRECT_Q,
    "H": qrcode.constants.ERROR_CORRECT_H
}

# Define theme colors.
LIGHT_BG = "#F5F5F5"
LIGHT_FG = "#1A1A1A"
DARK_BG = "#121212"
DARK_FG = "#E0E0E0"

def apply_theme(root, theme):
    """
    Apply the selected theme to the main window.
    
    :param root: The Tkinter root window.
    :param theme: Theme name as a string, either "light" or "dark".
    """
    if theme == "light":
        root.configure(bg=LIGHT_BG)
    else:
        root.configure(bg=DARK_BG)
    # Additional widget styles can be updated here as needed.

def toggle_theme():
    """
    Toggle the theme using the global root and theme_var.
    """
    global root, theme_var
    new_theme = "dark" if theme_var.get() == "light" else "light"
    theme_var.set(new_theme)
    apply_theme(root, new_theme)

def select_file(filetypes):
    """
    Open a file selection dialog.
    
    :param filetypes: List of file type tuples (e.g., [("Text and JSON Files", "*.txt;*.json")]).
    :return: The selected file path.
    """
    return filedialog.askopenfilename(filetypes=filetypes)

def generate_filename(source_type="unknown"):
    """
    Generate a filename that includes a timestamp, source type, use case, Base64 flag, and compression method.
    
    For compressed methods (zlib, gzip, cbor), Base64 is forced to "base64".
    
    :param source_type: "json" or "txt"
    :return: A filename string.
    """
    timestamp = datetime.now().strftime("%Y%m%dT%H%M%S")
    use_case = use_case_var.get() if use_case_var else "unknown"
    # Force Base64 flag to "base64" for compressed data.
    if compression_var.get() != "none":
        b64_flag = "base64"
    else:
        b64_flag = "base64" if base64_var.get() else "nobase64"
    compression = compression_var.get() if compression_var else "none"
    ext = output_format_var.get() if output_format_var else "png"
    
    return f"qr_{timestamp}_{use_case}_{source_type}_{b64_flag}_{compression}.{ext}"

def preview_qr_image(image):
    """
    Open a new window to display the QR code image.
    
    :param image: PIL Image of the QR code.
    """
    preview_window = tk.Toplevel()
    preview_window.title("QR Code Preview")
    # Convert the PIL image to a Tkinter-compatible image.
    photo = ImageTk.PhotoImage(image)
    label = tk.Label(preview_window, image=photo)
    label.image = photo  # Keep a reference. Prevent garbage collection.
    label.pack()

def generate_qr():
    """
    Main function to generate a QR code.

    Steps:
      1. Prompt the user to select a file (JSON or TXT) and read its content as UTF‑8.
      2. If the compression method is "cbor" or if "Extract Essential JSON Details" is enabled,
         attempt to parse the input as JSON.
         - If parsing succeeds and "Extract Essential" is enabled, extract the essential fields.
         - If "Include Debug Info" is enabled, insert a "debug" key (using an OrderedDict) so that
           the debug info appears first in the JSON output.
      3. Otherwise, treat the input as plain text.
      4. Process the data using the selected compression method. (For compressed methods,
         Base64 encoding is forced.)
      5. Determine the optimal QR version and error correction.
      6. Generate the QR code image and save it.
      7. Optionally display a preview.
    """
    file_path = select_file([("Text and JSON Files", "*.txt;*.json")])
    if not file_path:
        messagebox.showerror("Error", "No file selected!")
        return
    logging.debug(f"[generate_qr] Selected file: {file_path}")

    # Read the file content as UTF‑8.
    with open(file_path, "r", encoding="utf-8") as file:
        data = file.read().strip()
    if not data:
        messagebox.showerror("Error", "File is empty or invalid!")
        return
    logging.debug(f"[generate_qr] Read {len(data)} characters from file.")

    # Decide how to process the input.
    # If the compression method is "cbor" or if extraction is enabled, try parsing as JSON.
    if compression_var.get() == "cbor" or extract_essential_var.get():
        try:
            json_data = json.loads(data)
            source_type = "json"
            if extract_essential_var.get():
                # Extract only the essential details from the full JSON.
                essential_data = extract_essential_ticket_details(json_data)
                # If debug info is enabled, add it as the first key.
                if debug_var.get():
                    from collections import OrderedDict
                    debug_info = (
                        f"Use case: {use_case_var.get()}, "
                        f"Compression: {compression_var.get()}, "
                        f"Error Correction: {error_correction_var.get()}, "
                        f"Auto QR Version: {auto_version_var.get()}"
                    )
                    new_data = OrderedDict()
                    new_data["debug"] = debug_info
                    new_data.update(essential_data)
                    essential_data = new_data
                # Convert the (optionally modified) JSON object to string.
                data = json.dumps(essential_data)
                logging.debug(f"[generate_qr] Essential details extracted: {data[:200]}")
            else:
                if debug_var.get():
                    from collections import OrderedDict
                    debug_info = (
                        f"Use case: {use_case_var.get()}, "
                        f"Compression: {compression_var.get()}, "
                        f"Error Correction: {error_correction_var.get()}, "
                        f"Auto QR Version: {auto_version_var.get()}"
                    )
                    new_data = OrderedDict()
                    new_data["debug"] = debug_info
                    new_data.update(json_data)
                    data = json.dumps(new_data)
                    logging.debug(f"[generate_qr] Extended debug info added to JSON: {debug_info}")
                else:
                    data = json.dumps(json_data)
        except json.JSONDecodeError:
            # Warn and fallback to plain text if JSON parsing fails.
            messagebox.showwarning(
                "Warning",
                "Extraction is enabled but the input is not valid JSON.\nProceeding as plain text."
            )
            source_type = "txt"
            if debug_var.get():
                debug_info = (
                    f"DEBUG: Use case: {use_case_var.get()}, "
                    f"Compression: {compression_var.get()}, "
                    f"Error Correction: {error_correction_var.get()}, "
                    f"Auto QR Version: {auto_version_var.get()}\n"
                )
                data = debug_info + data
    else:
        # Attempt to parse JSON for debug info; if it fails, treat as plain text.
        try:
            json.loads(data)
            source_type = "json"
            if debug_var.get():
                from collections import OrderedDict
                debug_info = (
                    f"Use case: {use_case_var.get()}, "
                    f"Compression: {compression_var.get()}, "
                    f"Error Correction: {error_correction_var.get()}, "
                    f"Auto QR Version: {auto_version_var.get()}"
                )
                new_data = OrderedDict()
                new_data["debug"] = debug_info
                new_data.update(json.loads(data))
                data = json.dumps(new_data)
                logging.debug(f"[generate_qr] Extended debug info added to JSON: {data[:200]}")
        except json.JSONDecodeError:
            source_type = "txt"
            if debug_var.get():
                debug_info = (
                    f"DEBUG: Use case: {use_case_var.get()}, "
                    f"Compression: {compression_var.get()}, "
                    f"Error Correction: {error_correction_var.get()}, "
                    f"Auto QR Version: {auto_version_var.get()}\n"
                )
                data = debug_info + data
                logging.debug(f"[generate_qr] Extended debug info prepended to TXT data: {data[:200]}")

    # Process the data using process_data().
    processed_data = process_data(data, method=compression_var.get())
    if processed_data is None:
        messagebox.showerror("Error", "Data processing failed!")
        return

    # Log processed data length.
    if isinstance(processed_data, bytes):
        data_length = len(processed_data)
    else:
        data_length = len(processed_data.encode('utf-8'))
    logging.debug(f"[generate_qr] Processed data length: {data_length} bytes")

    # Determine the QR version.
    if auto_version_var.get():
        qr_version = determine_optimal_qr_version(data, compression_var.get(), "M")
        logging.debug(f"[generate_qr] Auto QR version selected: {qr_version}")
    else:
        qr_version = 5
        logging.debug(f"[generate_qr] Fixed QR version used: {qr_version}")

    error_corr = error_correction_mapping.get(error_correction_var.get(), qrcode.constants.ERROR_CORRECT_M)
    logging.debug(f"[generate_qr] Error Correction level: {error_correction_var.get()} -> {error_corr}")

    # Generate the QR code image.
    try:
        qr_image = generate_qr_code(processed_data, qr_version=qr_version, error_correction=error_corr)
        logging.debug(f"[generate_qr] QR code generated successfully.")
    except Exception as e:
        logging.error(f"[generate_qr] QR generation failed: {e}")
        messagebox.showerror("Error", f"QR Code generation failed: {e}")
        return

    # Determine output format and save path.
    out_format = output_format_var.get().lower()
    if auto_save_var.get():
        output_folder = os.path.join(os.getcwd(), "generated_qr")
        os.makedirs(output_folder, exist_ok=True)
        filename = generate_filename(source_type=source_type)
        save_path = os.path.join(output_folder, filename)
        logging.debug(f"[generate_qr] Auto-save enabled. Saving to: {save_path}")
    else:
        save_path = filedialog.asksaveasfilename(
            defaultextension=f".{out_format}",
            filetypes=[("PNG Image", "*.png"), ("SVG Vector", "*.svg")]
        )
        if not save_path:
            logging.debug("[generate_qr] Save cancelled by user.")
            return
        logging.debug(f"[generate_qr] Save path chosen: {save_path}")

    try:
        if out_format == "png":
            qr_image.save(save_path, optimize=True)
        elif out_format == "svg":
            from qr_processor import generate_svg
            qr_obj = qrcode.QRCode(
                version=qr_version,
                error_correction=error_corr,
                box_size=4,
                border=4
            )
            qr_obj.add_data(processed_data)
            qr_obj.make(fit=True)
            generate_svg(qr_obj, save_path)
            # SVGO
            optimise_svg(save_path)
        else:
            messagebox.showerror("Error", "Unsupported output format selected!")
            return
        logging.debug(f"[generate_qr] QR Code saved successfully at {save_path}")
    except Exception as e:
        logging.error(f"[generate_qr] Failed to save QR Code: {e}")
        messagebox.showerror("Error", f"Failed to save QR Code: {e}")
        return

    messagebox.showinfo("Success", f"QR Code saved at {save_path}")
    if preview_var.get():
        logging.debug(f"[generate_qr] Displaying preview.")
        preview_qr_image(qr_image)

def decode_qr():
    """
    Decode a QR code from an image file and display the result.
    
    Steps:
      1. Prompt user to select an image.
      2. Use decode_qr_image() to extract the raw QR code data.
      3. Automatically detect Base64 and compression (via decompress_data() with method "auto").
      4. Process further with decode_qr_data() to pretty-print JSON if applicable.
      5. Display the final result.
    """
    file_path = select_file([("Image Files", "*.png;*.jpg;*.jpeg;*.bmp;*.tiff")])
    if not file_path:
        messagebox.showerror("Error", "No image file selected!")
        return

    # Decode the QR code from the image.
    decoded_data = decode_qr_image(file_path)
    if decoded_data is None:
        messagebox.showerror("Error", "Failed to decode QR Code from the image!")
        return

    # Automatically decompress the data (auto-detects Base64 and compression).
    decompressed = decompress_data(decoded_data, method="auto")
    final_data = decode_qr_data(decompressed)

    display_text.delete("1.0", tk.END)
    display_text.insert(tk.END, f"Decoded Data:\n{final_data}")

def assess_qr_quality():
    """
    Assess the quality of a QR code image:
      1. Prompt user to select an image.
      2. Optimize the image for scanning.
      3. Compute quality metrics (contrast, quiet zone, readability).
      4. Display the results.
    """
    file_path = select_file([("Image Files", "*.png;*.jpg;*.jpeg;*.bmp;*.tiff")])
    if not file_path:
        messagebox.showerror("Error", "No image file selected!")
        return

    # Open the image file using PIL.
    img = Image.open(file_path)
    # Optimize the image for scanning.
    optimized_img = optimize_qr_for_scanning(img)
    # Get the quality assessment details.
    quality_info = check_qr_quality(optimized_img)

    display_text.delete("1.0", tk.END)
    display_text.insert(tk.END, f"QR Quality Assessment:\n{quality_info}")

def paste_qr_data():
    """
    Decode QR data pasted into the text widget and display the result.
    """
    global paste_text
    raw_qr = paste_text.get("1.0", tk.END).strip()
    if not raw_qr:
        messagebox.showerror("Error", "No QR data pasted!")
        return
    decoded = decompress_data(raw_qr, method=compression_var.get())
    display_text.delete("1.0", tk.END)
    display_text.insert(tk.END, f"Decoded Data:\n{decoded}")

def save_decoded_text():
    """
    Save the text displayed in the output widget to a file.
    """
    decoded = display_text.get("1.0", tk.END).strip()
    if not decoded:
        messagebox.showerror("Error", "No decoded text available!")
        return
    file_path = filedialog.asksaveasfilename(defaultextension=".txt", filetypes=[("Text Files", "*.txt")])
    if not file_path:
        return
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(decoded)
    messagebox.showinfo("Success", f"Decoded text saved to {file_path}")

def batch_generate_qr():
    """
    Batch process all TXT/JSON files in a selected folder to generate QR codes.
    
    Each file is processed with the current settings and saved automatically.
    """
    global debug_var, use_case_var, compression_var, auto_version_var, error_correction_var
    folder_path = filedialog.askdirectory(title="Select Folder with Input Files")
    if not folder_path:
        messagebox.showerror("Error", "No folder selected!")
        return
    files = [f for f in os.listdir(folder_path) if f.lower().endswith((".txt", ".json"))]
    if not files:
        messagebox.showinfo("Info", "No TXT or JSON files found in the folder.")
        return
    output_folder = os.path.join(os.getcwd(), "generated_qr")
    os.makedirs(output_folder, exist_ok=True)
    count = 0
    for filename in files:
        file_path = os.path.join(folder_path, filename)
        try:
            with open(file_path, "r", encoding="utf-8") as file:
                data = file.read().strip()
        except Exception as e:
            logging.error(f"Failed to read {filename}: {e}")
            continue
        if not data:
            continue
        try:
            json.loads(data)
            source_type = "json"
            if debug_var.get():
                data_json = json.loads(data)
                debug_info = f"Use case: {use_case_var.get()}, Compression: {compression_var.get()}"
                data_json["gen_ver"] = debug_info
                data = json.dumps(data_json)
        except json.JSONDecodeError:
            source_type = "txt"
            if debug_var.get():
                debug_info = f"DEBUG: Use case: {use_case_var.get()}, Compression: {compression_var.get()}\n"
                data = debug_info + data
        processed_data = process_data(data, method=compression_var.get())
        if processed_data is None:
            continue
        if auto_version_var.get():
            qr_version = determine_optimal_qr_version(data, compression_var.get(), "M")
        else:
            qr_version = 5
        error_corr = error_correction_mapping.get(error_correction_var.get(), qrcode.constants.ERROR_CORRECT_M)
        try:
            qr_image = generate_qr_code(processed_data, qr_version=qr_version, error_correction=error_corr)
        except Exception as e:
            logging.error(f"QR generation failed for {filename}: {e}")
            continue
        base = os.path.splitext(filename)[0]
        new_filename = f"{base}_{use_case_var.get()}_{source_type}_base64_{compression_var.get()}.png"
        save_path = os.path.join(output_folder, new_filename)
        try:
            qr_image.save(save_path, optimize=True)
            count += 1
        except Exception as e:
            logging.error(f"Failed to save QR Code for {filename}: {e}")
    messagebox.showinfo("Batch Generation", f"Generated QR codes for {count} files.")

def main():
    """
    Main entry point for the QR Code Tool GUI.
    
    Initializes the Tkinter root window, sets up global variables and widgets,
    and starts the event loop.
    """
    global root, theme_var, auto_save_var, output_format_var, use_case_var, compression_var, base64_var, debug_var, auto_version_var, error_correction_var, preview_var, display_text, paste_text, current_theme, extract_essential_var

    # Create the main window.
    root = tk.Tk()
    root.title("QR Code Tool")
    
    # Initialize Tkinter variables after creating the root window.
    auto_save_var = tk.BooleanVar(master=root, value=True)
    output_format_var = tk.StringVar(master=root, value="png")
    use_case_var = tk.StringVar(master=root, value="auto")
    compression_var = tk.StringVar(master=root, value="none")  # Options: "none", "zlib", "gzip", "cbor"
    base64_var = tk.BooleanVar(master=root, value=False)  # The Base64 flag is only used during generation; decoding is automatic.
    debug_var = tk.BooleanVar(master=root, value=False)
    auto_version_var = tk.BooleanVar(master=root, value=True)
    error_correction_var = tk.StringVar(master=root, value="M")
    preview_var = tk.BooleanVar(master=root, value=True)
    extract_essential_var = tk.BooleanVar(master=root, value=True)
    theme_var = tk.StringVar(value="light")

    # Apply the initial theme.
    apply_theme(root, theme_var.get())

    # Log changes for the auto-save toggle.
    auto_save_var.trace_add("write", lambda *args: logging.debug(f"Auto-save toggled, new value: {auto_save_var.get()}"))
    # Log changes for the preview toggle.
    preview_var.trace_add("write", lambda *args: logging.debug(f"Preview toggled, new value: {preview_var.get()}"))
    # Log changes for the extraction toggle.
    extract_essential_var.trace_add("write", lambda *args: logging.debug(f"Extract essential JSON toggled, new value: {extract_essential_var.get()}"))
    # Log changes for the debug info toggle.
    debug_var.trace_add("write", lambda *args: logging.debug(f"Debug info toggled, new value: {debug_var.get()}"))
    # Log changes for the theme toggle.
    theme_var.trace_add("write", lambda *args: logging.debug(f"Theme changed, new value: {theme_var.get()}"))
    # Log changes for the auto QR version toggle.
    auto_version_var.trace_add("write", lambda *args: logging.debug(f"Auto QR version toggled, new value: {auto_version_var.get()}"))

    # Build the options frame.
    frame_options = tk.Frame(root)
    frame_options.pack(padx=10, pady=10)
    tk.Checkbutton(frame_options, text="Auto Save to generated_qr Folder", variable=auto_save_var).grid(row=0, column=0, sticky="w", padx=5, pady=2)
    tk.Label(frame_options, text="Output Format:").grid(row=1, column=0, sticky="w", padx=5, pady=2)
    tk.OptionMenu(frame_options, output_format_var, "png", "svg").grid(row=1, column=1, sticky="w", padx=5, pady=2)
    tk.Checkbutton(frame_options, text="Include Debug Info", variable=debug_var).grid(row=2, column=0, sticky="w", padx=5, pady=2)
    tk.Checkbutton(frame_options, text="Use Auto QR Version", variable=auto_version_var).grid(row=3, column=0, sticky="w", padx=5, pady=2)
    tk.Label(frame_options, text="Error Correction:").grid(row=4, column=0, sticky="w", padx=5, pady=2)
    tk.OptionMenu(frame_options, error_correction_var, "L", "M", "Q", "H").grid(row=4, column=1, sticky="w", padx=5, pady=2)
    tk.Checkbutton(frame_options, text="Show Preview", variable=preview_var).grid(row=5, column=0, sticky="w", padx=5, pady=2)
    tk.Checkbutton(frame_options, text="Extract Essential JSON Details", variable=extract_essential_var).grid(row=7, column=0, sticky="w", padx=5, pady=2)
    tk.Button(frame_options, text="Toggle Theme", command=toggle_theme).grid(row=6, column=0, sticky="w", padx=5, pady=2)

    # Compression options frame.
    frame_options2 = tk.Frame(root)
    frame_options2.pack(padx=10, pady=10)
    tk.Label(frame_options2, text="Compression Method:").grid(row=0, column=0, sticky="w", padx=5, pady=2)
    tk.OptionMenu(frame_options2, compression_var, "none", "zlib", "gzip", "cbor").grid(row=0, column=1, sticky="w", padx=5, pady=2)
    
    # Buttons for main functions.
    btn_generate = tk.Button(root, text="Generate QR Code", command=generate_qr)
    btn_generate.pack(padx=10, pady=5)
    tk.Button(root, text="Batch Generate QR Codes", command=batch_generate_qr).pack(padx=10, pady=5)
    btn_decode = tk.Button(root, text="Decode QR Image", command=decode_qr)
    btn_decode.pack(padx=10, pady=5)
    btn_assess = tk.Button(root, text="Assess QR Quality", command=assess_qr_quality)
    btn_assess.pack(padx=10, pady=5)

    # Frame for pasted QR data.
    frame_paste = tk.Frame(root)
    frame_paste.pack(padx=10, pady=10)
    tk.Label(frame_paste, text="Paste QR Data:").pack(anchor="w")
    paste_text = tk.Text(frame_paste, height=4, width=60)
    paste_text.pack(padx=5, pady=5)
    tk.Button(frame_paste, text="Decode Pasted QR Data", command=paste_qr_data).pack(padx=5, pady=5)

    # Text widget to display decoded data or quality info.
    display_text = tk.Text(root, height=10, width=60)
    display_text.pack(padx=10, pady=10)

    # Create a button to save decoded text.
    tk.Button(root, text="Save Decoded Text", command=save_decoded_text).pack(padx=10, pady=5)
    
    # Start the Tkinter event loop.
    root.mainloop()

if __name__ == "__main__":
    main()