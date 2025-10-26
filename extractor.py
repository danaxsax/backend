import pymupdf

doc = pymupdf.open("file1.pdf") # Replace with your PDF file

for page_index in range(len(doc)):
    page = doc[page_index]  # Get the page object
    print(f"Processing page {page_index + 1}")
    # Perform operations on the page, e.g., extract text, images, etc.
    text = page.get_text()
    print(f"Text on page {page_index + 1}: {text[:10000]}...") # Print first 100 chars
doc.close()