import os
import re
import numpy as np
import pytesseract
import cv2
from PIL import Image
from spellchecker import SpellChecker
from sentence_transformers import SentenceTransformer, util
from inference_sdk import InferenceHTTPClient

# Laden der bekannten Produkte
def load_produktfilter():
    path = "produktfilter.txt"
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            return [line.strip().lower() for line in f if line.strip()]
    else:
        default = ["thunfisch", "joghurt", "kidney", "bohnen", "eier", "milch", "käse"]
        with open(path, "w", encoding="utf-8") as f:
            f.write("\n".join(default))
        return default

produktfilter = load_produktfilter()
spell = SpellChecker(language="de")
model = SentenceTransformer('distiluse-base-multilingual-cased-v2')
produkt_embeddings = model.encode(produktfilter, convert_to_tensor=True)

FÜLLWÖRTER = {"a", "e", "i", "m", "z", "x", "\\", "/", "'", "-", ":", ";", *list("0123456789")}
unerkannte_produkte = set()

def preprocess_image(image_path):
    image_path = os.path.normpath(image_path)
    img = cv2.imdecode(np.fromfile(image_path, dtype=np.uint8), cv2.IMREAD_COLOR)

    client = InferenceHTTPClient(
        api_url="https://serverless.roboflow.com",
        api_key="HFbSJpYTcEanuSYbFwoM"
    )

    result = client.run_workflow(
        workspace_name="bonmodel",
        workflow_id="active-learning",
        images={"image": image_path},
        use_cache=True
    )

    if not result:
        raise ValueError("Objekterkennung fehlgeschlagen")

    result = result[0]
    article = result.get("predictions").get("predictions")[0]
    article_w, article_h, article_x, article_y, *_ = article.values()

    crop = img[int(article_y - article_h / 2):int(article_y + article_h / 2),
               int(article_x - article_w / 2):int(article_x + article_w / 2)]

    gray = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY)
    denoised = cv2.fastNlMeansDenoising(gray, h=10)
    clahe = cv2.createCLAHE(clipLimit=0.1, tileGridSize=(1, 1))
    contrast = clahe.apply(denoised)

    thresh = cv2.adaptiveThreshold(
        contrast, 255,
        cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY,
        11, 2
    )

    return Image.fromarray(thresh)

def ocr_from_image(image_path):
    processed_image = preprocess_image(image_path)
    return pytesseract.image_to_string(image=processed_image, lang="deu", config="--psm 6")

def classify_line_structure(lines):
    strukturierte_zeilen = []
    vorherige_produktzeile = ""
    for line in lines:
        line = line.strip()
        preis_match = re.search(r'(\d+[\.,]\d{2})\s*[A-Z]?$', line)
        gewicht_match = re.search(r'(\d+[\.,]\d+)\s*kg\s*[xX]\s*(\d+[\.,]\d+)', line)

        if preis_match and not gewicht_match:
            name = re.sub(r'(\d+[\.,]\d{2})\s*[A-Z]?$', '', line).strip()
            strukturierte_zeilen.append(("produktzeile", name, preis_match.group(1)))
            vorherige_produktzeile = ""
        elif gewicht_match and preis_match:
            strukturierte_zeilen.append(("gewichtzeile", vorherige_produktzeile.strip(), preis_match.group(1)))
            vorherige_produktzeile = ""
        elif not preis_match and len(line.split()) < 5:
            vorherige_produktzeile = line
    return strukturierte_zeilen

def correct_spelling_multiple(name):
    if not name.strip():
        unerkannte_produkte.add(name.strip())
        return []

    query_embedding = model.encode(name, convert_to_tensor=True)
    cos_scores = util.cos_sim(query_embedding, produkt_embeddings)[0]

    top_idx = int(np.argmax(cos_scores))
    top_score = float(cos_scores[top_idx])
    top_product = produktfilter[top_idx]

    return [top_product] if top_score > 0.95 else []

def extract_menge(name):
    match = re.search(r'(\d+)\s*[xX*]', name)
    return int(match.group(1)) if match else 1

def extract_product_lines(text):
    strukturierte_zeilen = classify_line_structure(text.splitlines())
    produkt_liste = []
    for _, name, preis in strukturierte_zeilen:
        menge = extract_menge(name)
        try:
            for produkt in correct_spelling_multiple(name):
                produkt_liste.append({
                    "Produktname": produkt,
                    "Einzelpreis": float(preis.replace(",", ".")),
                    "Menge": menge
                })
        except Exception:
            continue
    return produkt_liste

def extract_products_from_image(image_path):
    ocr_text = ocr_from_image(image_path)
    return extract_product_lines(ocr_text)
