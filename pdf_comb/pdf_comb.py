
#!/usr/bin/env python3
# How to run: /home/dev/py/.venv/bin/python /home/dev/py/pdf_comb/pdf_comb.py path_of_indivdual_pdfs

# Example usage:
# /home/dev/py/.venv/bin/python /home/dev/py/pdf_comb/pdf_comb.py /home/ts/Downloads/unz

import os
import re
import sys
import pymupdf


OUTPUT_NAME = "out.pdf"


def natural_sort_key(filename):
    """Sort filenames naturally: 2.pdf before 10.pdf."""
    parts = re.split(r"(\d+)", filename.casefold())
    return [
        (0, int(part)) if part.isdigit() else (1, part)
        for part in parts
    ]


def main():
    # Use the supplied directory, or the current directory.
    folder = os.path.abspath(sys.argv[1] if len(sys.argv) > 1 else ".")

    if not os.path.isdir(folder):
        print(f"ERROR: Directory not found: {folder}")
        sys.exit(1)

    output = os.path.join(folder, OUTPUT_NAME)

    # Find PDFs in this directory, excluding the output file.
    files = [
        filename
        for filename in os.listdir(folder)
        if filename.lower().endswith(".pdf")
        and filename.casefold() != OUTPUT_NAME.casefold()
        and os.path.isfile(os.path.join(folder, filename))
    ]

    files.sort(key=natural_sort_key)

    if not files:
        print(f"No input PDF files found in: {folder}")
        sys.exit(1)

    merged = pymupdf.open()
    bookmarks = []
    total_pages = 0

    try:
        for filename in files:
            path = os.path.join(folder, filename)

            print(f"Adding: {filename}")

            with pymupdf.open(path) as pdf:
                if pdf.page_count == 0:
                    print(f"  Skipping empty PDF: {filename}")
                    continue

                # Bookmark points to the first page of this PDF.
                bookmarks.append([
                    1,
                    os.path.splitext(filename)[0],
                    total_pages + 1
                ])

                merged.insert_pdf(pdf)
                total_pages += pdf.page_count

        if total_pages == 0:
            print("ERROR: No pages found in the input PDFs.")
            sys.exit(1)

        # Add bookmarks and display the bookmark sidebar by default.
        merged.set_toc(bookmarks)
        merged.set_pagemode("UseOutlines")

        merged.save(output, garbage=4, deflate=True)

    finally:
        merged.close()

    print()
    print("PDF MERGE COMPLETE")
    print(f"Output: {output}")
    print(f"PDF files merged: {len(bookmarks)}")
    print(f"Total pages: {total_pages}")
    print(f"Bookmarks created: {len(bookmarks)}")


if __name__ == "__main__":
    main()
