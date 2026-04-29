import pdfplumber
import pytesseract
from pdf2image import convert_from_path
from PIL import Image
import cv2
import numpy as np
from typing import List
from dataclasses import dataclass
import time
import re


@dataclass
class PageChunk:
    chunk_index: int
    start_page: int
    end_page: int
    pages_text: List[str]


def preprocess_image(image):
    img = np.array(image)
    gray = cv2.cvtColor(img, cv2.COLOR_RGB2GRAY)
    gray = cv2.convertScaleAbs(gray, alpha=2.0, beta=10)
    gray = cv2.GaussianBlur(gray, (1, 1), 0)
    gray = cv2.adaptiveThreshold(
        gray, 255,
        cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY, 31, 2
    )
    return Image.fromarray(gray)


def extract_text_from_page(pdf_path: str, page_index: int) -> str:
    """Ek page se text nikalo"""
    try:
        with pdfplumber.open(pdf_path) as pdf:
            text = pdf.pages[page_index].extract_text()
            if text:
                cleaned = ' '.join(text.split())
                if len(cleaned) > 20:
                    return cleaned
    except Exception as e:
        print(f"  [WARN] Page {page_index+1} pdfplumber error: {e}")

    try:
        print(f"  🖼️  Page {page_index+1}: OCR chal raha hai...")
        ocr_start = time.time()
        images = convert_from_path(
            pdf_path,
            first_page=page_index + 1,
            last_page=page_index + 1,
            dpi=200
        )
        if not images:
            return ""

        clean_image = preprocess_image(images[0])
        ocr_text = pytesseract.image_to_string(
            clean_image,
            lang='eng',
            config=r'--oem 3 --psm 6'
        )
        elapsed = time.time() - ocr_start
        result = ocr_text.strip()

        # Garbage filter
        words = result.split()
        good_words = [w for w in words if len(w) > 1]
        result = ' '.join(good_words)

        print(f"  ✅ Page {page_index+1}: OCR done ({len(result)} chars, {elapsed:.1f}s)")
        return result

    except Exception as e:
        print(f"  ❌ Page {page_index+1}: OCR error — {e}")
        return ""


def is_garbage_text(text: str) -> bool:
    """Garbage OCR text detect karo"""
    if not text:
        return True
    words = text.split()
    if not words:
        return True
    avg_len = sum(len(w) for w in words) / len(words)
    if avg_len < 3:
        return True
    real_words = [w for w in words if len(w) > 2]
    ratio = len(real_words) / len(words)
    if ratio < 0.5:
        return True
    return False


def extract_paragraphs(text: str, min_chars: int = 200) -> List[str]:
    """Text se paragraphs nikalo — minimum 200 chars"""
    if not text:
        return []

    raw_paragraphs = re.split(r'\n\n+|(?<=[.!?])\s{2,}', text)

    paragraphs = []
    buffer = ""

    for para in raw_paragraphs:
        para = para.strip()
        if not para:
            continue

        buffer += " " + para

        if len(buffer.strip()) >= min_chars:
            paragraphs.append(buffer.strip())
            buffer = ""

    if buffer.strip() and len(buffer.strip()) >= 50:
        if paragraphs:
            paragraphs[-1] += " " + buffer.strip()
        else:
            paragraphs.append(buffer.strip())

    return paragraphs


def split_book_into_chunks(pdf_path: str, chunk_size: int = 20) -> List[PageChunk]:
    """
    PDF ko paragraph-based chunks mein split karo!
    Har paragraph = 1 chunk (minimum 200 chars)
    """
    chunks = []

    with pdfplumber.open(pdf_path) as pdf:
        total_pages = len(pdf.pages)

    print(f"\n{'='*50}")
    print(f"📚 PDF: {pdf_path}")
    print(f"📄 Total pages: {total_pages}")
    print(f"🔤 Mode: Paragraph-based chunking")
    print(f"📏 Min paragraph size: 200 chars")
    print(f"{'='*50}\n")

    total_start = time.time()
    chunk_index = 0

    for page_num in range(total_pages):

        # Page ka text nikalo
        page_text = extract_text_from_page(pdf_path, page_num)

        # Empty check
        if not page_text:
            continue

        # Garbage check — skip karo
        if is_garbage_text(page_text):
            print(f"  ⚠️ Page {page_num+1}: Garbage text — skip!")
            continue

        # Paragraphs nikalo
        paragraphs = extract_paragraphs(page_text, min_chars=200)

        if not paragraphs:
            if len(page_text) >= 200:
                paragraphs = [page_text]
            else:
                continue

        # Har paragraph = 1 chunk
        for para in paragraphs:
            chunks.append(PageChunk(
                chunk_index=chunk_index,
                start_page=page_num + 1,
                end_page=page_num + 1,
                pages_text=[para]
            ))
            print(f"  ✅ Chunk {chunk_index}: Page {page_num+1}, {len(para)} chars")
            chunk_index += 1

        # Har 10 pages pe summary
        if (page_num + 1) % 10 == 0:
            elapsed = time.time() - total_start
            remaining_pages = total_pages - (page_num + 1)
            avg = elapsed / (page_num + 1)
            eta = avg * remaining_pages
            print(f"\n📊 Progress: {page_num+1}/{total_pages} pages")
            print(f"📦 Chunks so far: {chunk_index}")
            print(f"⏱️  Elapsed: {elapsed:.0f}s | ETA: {eta:.0f}s ({eta/60:.1f} min)\n")

    total_time = time.time() - total_start
    print(f"\n{'='*50}")
    print(f"🎉 Split done!")
    print(f"   📄 Pages processed: {total_pages}")
    print(f"   📦 Total chunks: {chunk_index}")
    print(f"   ⏱️  Total time: {total_time:.1f}s ({total_time/60:.1f} min)")
    print(f"{'='*50}\n")

    return chunks