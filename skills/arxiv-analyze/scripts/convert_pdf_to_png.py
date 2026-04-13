#!/usr/bin/env python3
"""Convert PDF figures to PNG for visual analysis.

Usage:
    python convert_pdf_to_png.py <pdf_path> [dpi]

Arguments:
    pdf_path: Path to a single PDF file
    dpi: Resolution for conversion (default 150)

Output:
    Creates .png file(s) in the same directory as the PDF.
    For multi-page PDFs, appends _page{num} to the filename.
    Returns the path(s) to converted PNG files.

Dependencies: PyMuPDF (install: pip install PyMuPDF)
"""

import fitz  # PyMuPDF
import os
import sys

def convert_pdf_to_png(pdf_path, dpi=150):
    """
    Convert a single PDF file to PNG.

    Args:
        pdf_path: Path to the PDF file
        dpi: Resolution for conversion

    Returns:
        List of paths to converted PNG files (saved alongside the PDF).
    """
    if not os.path.exists(pdf_path):
        print(f"Error: File not found: {pdf_path}")
        return []

    pdf_dir = os.path.dirname(pdf_path)
    pdf_name = os.path.basename(pdf_path)

    converted = []
    try:
        doc = fitz.open(pdf_path)
        for page_num in range(len(doc)):
            page = doc[page_num]
            pix = page.get_pixmap(dpi=dpi)
            png_name = pdf_name.replace('.pdf', '.png')
            if len(doc) > 1:
                png_name = pdf_name.replace('.pdf', f'_page{page_num}.png')
            png_path = os.path.join(pdf_dir, png_name)
            pix.save(png_path)
            converted.append(png_path)
        doc.close()
    except Exception as e:
        print(f"Error converting {pdf_path}: {e}")
        return []

    return converted

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python convert_pdf_to_png.py <pdf_path> [dpi]")
        print("Output: PNG file(s) saved in the same directory as the PDF")
        sys.exit(1)

    pdf_path = sys.argv[1]
    dpi = int(sys.argv[2]) if len(sys.argv) > 2 else 150

    converted = convert_pdf_to_png(pdf_path, dpi)
    if converted:
        print(f"Converted: {pdf_path}")
        for path in converted:
            print(f"  -> {path}")