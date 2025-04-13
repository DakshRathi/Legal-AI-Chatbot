# ml_core/document_processor.py
import io
import spacy
from pathlib import Path
from typing import Dict, Optional, Union, List

# OCR and Document Parsing Libraries
import pytesseract
from PIL import Image
import pypdf
import docx # python-docx

# Attempt to load SpaCy model, provide guidance if missing
try:
    nlp = spacy.load("en_core_web_lg")
    print("SpaCy model 'en_core_web_lg' loaded.")
except OSError:
    print("SpaCy model 'en_core_web_lg' not found.")
    print("Please run: python -m spacy download en_core_web_lg")
    nlp = None # Set to None if loading failed

# Configure Tesseract path if needed (uncomment and set path if necessary)
# TESSERACT_CMD = '/opt/homebrew/bin/tesseract' # Example for Homebrew on ARM Mac
# try:
#     pytesseract.pytesseract.tesseract_cmd = TESSERACT_CMD
# except Exception as e:
#     print(f"Warning: Could not set Tesseract path: {e}")
#     print("Ensure Tesseract is installed and in your PATH or configure tesseract_cmd.")


def extract_text_from_pdf(file_content: bytes) -> Optional[str]:
    """Extracts text from a PDF file content."""
    try:
        reader = pypdf.PdfReader(io.BytesIO(file_content))
        text = ""
        for page in reader.pages:
            page_text = page.extract_text()
            if page_text:
                text += page_text + "\n"
        return text if text else None # Return None if no text extracted
    except Exception as e:
        print(f"Error extracting text from PDF: {e}")
        return None

def extract_text_from_docx(file_content: bytes) -> Optional[str]:
    """Extracts text from a DOCX file content."""
    try:
        doc = docx.Document(io.BytesIO(file_content))
        text = "\n".join([para.text for para in doc.paragraphs])
        return text if text else None
    except Exception as e:
        print(f"Error extracting text from DOCX: {e}")
        return None

def extract_text_from_image(file_content: bytes) -> Optional[str]:
    """Extracts text from an image file content using OCR (Tesseract)."""
    try:
        image = Image.open(io.BytesIO(file_content))
        # Preprocessing can be added here (grayscale, thresholding) [2]
        text = pytesseract.image_to_string(image)
        return text if text else None
    except pytesseract.TesseractNotFoundError:
        print("ERROR: Tesseract is not installed or not in your PATH.")
        print("Please install Tesseract: https://tesseract-ocr.github.io/tessdoc/Installation.html")
        return None
    except Exception as e:
        print(f"Error extracting text from image: {e}")
        return None

def extract_entities(text: str) -> Dict[str, List[str]]:
    """Extracts named entities (Date, Org, Person) using SpaCy."""
    entities = {"DATE": [], "ORG": [], "PERSON": []} # Add other relevant types like GPE, MONEY etc.
    if not nlp:
        print("Warning: SpaCy model not loaded. Cannot extract entities.")
        return entities
    if not text:
        return entities

    try:
        doc = nlp(text)
        for ent in doc.ents:
            if ent.label_ in entities:
                entities[ent.label_].append(ent.text.strip())

        # Deduplicate entities
        for key in entities:
            entities[key] = sorted(list(set(entities[key])))
        return entities
    except Exception as e:
        print(f"Error during entity extraction: {e}")
        return entities # Return empty dict on error

def process_document_content(file_content: bytes, filename: str) -> Optional[Dict[str, Union[str, Dict]]]:
    """
    Processes uploaded file content to extract text and entities.
    Supports PDF, DOCX, PNG, JPG, JPEG.
    """
    file_ext = Path(filename).suffix.lower()
    text = None

    print(f"Processing document: {filename} (Extension: {file_ext})")

    if file_ext == ".pdf":
        text = extract_text_from_pdf(file_content)
        # If PDF text extraction fails (e.g., scanned PDF), try OCR
        if not text:
            print("PDF text extraction failed or yielded no text, attempting OCR...")
            text = extract_text_from_image(file_content)
    elif file_ext == ".docx":
        text = extract_text_from_docx(file_content)
    elif file_ext in [".png", ".jpg", ".jpeg"]:
        text = extract_text_from_image(file_content)
    else:
        print(f"Unsupported file type: {file_ext}")
        return None

    if not text:
        print(f"Failed to extract text from {filename}")
        return None

    print(f"Successfully extracted text from {filename} (Length: {len(text)} chars)")
    entities = extract_entities(text)
    print(f"Extracted entities: {entities}")

    return {"text": text, "entities": entities}

if __name__ == '__main__':
    # Example usage (requires creating dummy files or adapting paths)
    print("\nTesting document processor...")
    # Create a dummy text file for entity extraction test
    test_text = ("This agreement was signed by Alice Smith of Globex Corp. on 2024-01-15. "
                 "Another party, Bob Jones from Acme Inc., reviewed it on 2024-01-20.")
    print(f"\nTesting entity extraction on text:\n{test_text}")
    if nlp:
        entities = extract_entities(test_text)
        print(f"Extracted Entities: {entities}")
    else:
        print("Skipping entity extraction test as SpaCy model is not loaded.")

    # Add more tests with actual PDF/DOCX/Image files if needed
    test_pdf_path = Path(__file__).parent.parent / "testdoc.pdf"
    if test_pdf_path.exists():
        with open(test_pdf_path, "rb") as f:
            content = f.read()
        result = process_document_content(content, test_pdf_path.name)
        print(f"\nProcessing result for {test_pdf_path.name}: {result is not None}")

