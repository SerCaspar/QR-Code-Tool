# qr_quality.py

import numpy as np
from PIL import Image
import cv2
import logging

"""
This module contains functions to assess the quality of a generated QR code and to optimize
an image of a QR code for better scanning.
"""

def check_qr_quality(qr_img):
    """
    Assess QR Code quality by evaluating several criteria:

    1. Contrast Ratio:
       - Convert the QR image to grayscale.
       - Apply a fixed threshold (e.g., 128) to separate dark and light areas.
       - Compute the average intensity for the white (light) pixels and the dark pixels.
       - The contrast ratio is defined as the difference between these two averages.
         A higher value suggests better contrast between modules and background.

    2. Quiet Zone Verification:
       - Extract the pixel values along the border (all four edges).
       - Verify that these border pixels have high brightness (above a specified threshold)
         to ensure that an adequate quiet zone is present.

    3. Data Density:
       - Calculate the proportion of dark pixels in the entire QR code.
         Too high or too low a data density might negatively impact scanability.

    4. Readability Score:
       - Use a heuristic to compute a readability score (e.g., 100 minus a factor 
         based on the data density). This provides a rough measure of how likely the QR code 
         is to be read reliably.

    The function returns a multi-line string with these metrics.

    :param qr_img: A PIL Image of the QR code.
    :return: A string with the quality assessment.
    """
    # Convert the image to grayscale.
    gray_img = qr_img.convert("L")
    gray_array = np.array(gray_img)

    # Define a threshold to distinguish dark (QR modules) and light areas.
    threshold = 128
    # Separate pixels into light and dark groups.
    white_pixels = gray_array[gray_array >= threshold]
    dark_pixels = gray_array[gray_array < threshold]

    # Compute the average intensity for each group.
    white_avg = np.mean(white_pixels) if white_pixels.size > 0 else 255
    dark_avg = np.mean(dark_pixels) if dark_pixels.size > 0 else 0

    # Contrast Ratio is defined as the difference between the average white and dark values.
    contrast = white_avg - dark_avg

    # Verify quiet zone by checking that all border pixels exceed a high brightness threshold.
    quiet_threshold = 230  # Expect very high brightness for a proper quiet zone.
    top_border = gray_array[0, :]
    bottom_border = gray_array[-1, :]
    left_border = gray_array[:, 0]
    right_border = gray_array[:, -1]
    quiet_zone_present = (np.all(top_border > quiet_threshold) and
                          np.all(bottom_border > quiet_threshold) and
                          np.all(left_border > quiet_threshold) and
                          np.all(right_border > quiet_threshold))

    # Calculate the data density (proportion of dark pixels).
    data_density = np.sum(gray_array < threshold) / gray_array.size

    # Compute a heuristic readability score (e.g., subtract a factor of the data density from 100).
    readability_score = 100 - (data_density * 80)

    # Return a formatted string with all quality metrics.
    quality_info = (
        f"Contrast Ratio: {contrast:.2f} (White Avg: {white_avg:.2f}, Dark Avg: {dark_avg:.2f})\n"
        f"Quiet Zone: {'Present' if quiet_zone_present else 'Missing'}\n"
        f"Data Density: {data_density:.2f}\n"
        f"Readability Score: {readability_score:.1f}/100"
    )
    return quality_info

def optimize_qr_for_scanning(image):
    """
    Enhance QR code image quality by:
      - Converting the image to grayscale (if not already).
      - Applying histogram equalisation.
      - Applying adaptive thresholding to improve contrast.
    
    :param image: A PIL Image.
    :return: An optimized PIL Image suitable for scanning.
    """
    # Convert the PIL image to a numpy array and ensure it is of type uint8.
    np_img = np.array(image).astype(np.uint8)
    
    # If the image already has one channel (grayscale), use it directly.
    if np_img.ndim == 2:
        gray = np_img
    elif np_img.shape[-1] == 3:
        # If the image has three channels, assume RGB and convert to grayscale.
        gray = cv2.cvtColor(np_img, cv2.COLOR_RGB2GRAY)
    elif np_img.shape[-1] == 4:
        # If the image has four channels (e.g. RGBA), convert to grayscale.
        gray = cv2.cvtColor(np_img, cv2.COLOR_RGBA2GRAY)
    else:
        # Fallback: if channels are unknown, attempt a default conversion.
        gray = cv2.cvtColor(np_img, cv2.COLOR_BGR2GRAY)
    
    # Apply histogram equalisation and adaptive thresholding.
    gray = cv2.equalizeHist(gray)
    gray = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                                 cv2.THRESH_BINARY, 11, 2)
    return Image.fromarray(gray)
