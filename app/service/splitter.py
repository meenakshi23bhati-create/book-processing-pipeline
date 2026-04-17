import pdfplumber
import pytesseract
from pdf2image import convert_from_path
from PIL import Image
import cv2
import numpy as np
from typing import List
from dataclasses import dataclass


# ✅ Pehle dataclass define karo
@dataclass
class PageChunk:
    chunk_index: int
    start_page: int
    end_page: int
    pages_text: List[str]


# ✅ Phir helper functions
def preprocess_image(image):
    """OCR accuracy badhane ke liye image clean karo"""
    img = np.array(image)
    gray = cv2.cvtColor(img, cv2.COLOR_RGB2GRAY)
    gray = cv2.convertScaleAbs(gray, alpha=1.5, beta=0)
    gray = cv2.medianBlur(gray, 3)
    _, thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    return Image.fromarray(thresh)


def extract_text_from_page(pdf_path: str, page_index: int) -> str:
    """Ek page se text nikalta hai — pehle normal, phir OCR"""
    with pdfplumber.open(pdf_path) as pdf:
        text = pdf.pages[page_index].extract_text()
        if text and len(text.strip()) > 50:
            return text.strip()

    images = convert_from_path(
        pdf_path,
        first_page=page_index + 1,
        last_page=page_index + 1,
        dpi=300
    )
    clean_image = preprocess_image(images[0])
    custom_config = r'--oem 3 --psm 6'
    ocr_text = pytesseract.image_to_string(clean_image, lang='eng', config=custom_config)
    return ocr_text.strip()


# ✅ Sabse last mein main function
def split_book_into_chunks(pdf_path: str, chunk_size: int = 20) -> List[PageChunk]:
    """PDF ko chunk_size pages ke group mein split karta hai"""
    chunks = []
    with pdfplumber.open(pdf_path) as pdf:
        total_pages = len(pdf.pages)

    for i, start in enumerate(range(0, total_pages, chunk_size)):
        end = min(start + chunk_size, total_pages)
        pages_text = [
            extract_text_from_page(pdf_path, p)
            for p in range(start, end)
        ]
        print(f"Chunk {i}: pages {start+1}-{end}, text sample: {pages_text[0][:100] if pages_text[0] else 'EMPTY'}")
        chunks.append(
            PageChunk(
                chunk_index=i,
                start_page=start + 1,
                end_page=end,
                pages_text=pages_text
            )
        )
    return chunks