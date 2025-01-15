import cv2
import numpy as np
from flask import Flask, request, jsonify
import pytesseract
import re
from googletrans import Translator

app = Flask(__name__)

# Chemin vers l'exécutable Tesseract OCR
pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

# Dimensions standardisées de la carte
STANDARD_WIDTH = 515
STANDARD_HEIGHT = 321

# Zones régionales de la carte (ajustées pour une meilleure extraction)
REGIONS = {
    # Nom (en français)
    "last_name_fr": (175 / 515, 60 / 321, 300 / 515, 100 / 321),
    
    # Prénom (en français)
    "first_name_fr": (175 / 515, 100 / 321, 300 / 515, 140 / 321),
    
    # Nom (en arabe)
    "last_name_ar": (370 / 515, 50 / 321, 510 / 515, 90 / 321),
    
    # Prénom (en arabe)
    "first_name_ar": (370 / 515, 90 / 321, 510 / 515, 130 / 321),
    
    "birth_date": (295 / 515, 117 / 321, 381 / 515, 144 / 321),
    "birth_place_fr": (185 / 515, 152 / 321, 346 / 515, 183 / 321),
    
    # Numéro de carte d’identité
    "card_id": (50 / 515, 275 / 321, 200 / 515, 310 / 321),
    
    # Date d'expiration
    "expiry_date": (339 / 515, 270 / 321, 460 / 515, 310 / 321),
}


# Initialiser le traducteur
translator = Translator()

@app.route('/')
def home():
    return "<h1>Carte d'identité API</h1> <p>Utilisez /upload pour envoyer une image.</p>"

@app.route('/upload', methods=['POST'])
def upload_image():
    if 'file' not in request.files:
        return jsonify({'error': 'Aucun fichier téléchargé'}), 400

    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'Aucun fichier sélectionné'}), 400

    # Vérifier si le fichier est une image
    if not file.filename.lower().endswith(('.png', '.jpg', '.jpeg')):
        return jsonify({'error': 'Format de fichier non supporté. Utilisez PNG, JPG ou JPEG.'}), 400

    # Lire l'image depuis le fichier
    file_bytes = np.frombuffer(file.read(), np.uint8)
    image = cv2.imdecode(file_bytes, cv2.IMREAD_COLOR)

    if image is None:
        return jsonify({'error': 'Format d\'image invalide'}), 400
    try:
        # Extraction des données de la carte
        extracted_data = extract_id_card_data(image)
        return jsonify(extracted_data)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

def preprocess_image(image):
    """Prétraitement de l'image (redimensionnement et conversion en niveaux de gris)."""
    resized = cv2.resize(image, (STANDARD_WIDTH, STANDARD_HEIGHT))
    gray = cv2.cvtColor(resized, cv2.COLOR_BGR2GRAY)
    return gray

def extract_region(image, region):
    """Découpe une région spécifique de l'image."""
    h, w = image.shape[:2]
    x_start, y_start, x_end, y_end = region
    x1, y1 = int(x_start * w), int(y_start * h)
    x2, y2 = int(x_end * w), int(y_end * h)
    return image[y1:y2, x1:x2]

def clean_text(text, field_name):
    """Nettoie le texte extrait."""
    text = text.strip()
    if field_name in ["first_name_fr", "last_name_fr", "birth_place_fr"]:
        text = re.sub(r'[^A-Za-z\s]', '', text)
    elif field_name in ["first_name_ar", "last_name_ar", "birth_place_ar"]:
        text = re.sub(r'[^\u0600-\u06FF\s]', '', text)  # Conserver uniquement les caractères arabes
    elif field_name == "card_id":
        text = re.sub(r'[^A-Za-z0-9]', '', text)  # Garder lettres et chiffres uniquement
    return text.strip()

def translate_text(text, src_lang, dest_lang):
    """Traduit un texte d'une langue à une autre."""
    try:
        translation = translator.translate(text, src=src_lang, dest=dest_lang)
        return translation.text
    except Exception as e:
        return f"Erreur traduction: {e}"

def extract_id_card_data(image):
    """Extrait les données de la carte d'identité."""
    processed_image = preprocess_image(image)
    data = {}

    for field, region in REGIONS.items():
        region_image = extract_region(processed_image, region)
        try:
            lang = 'fra' if 'ar' not in field else 'ara'
            text = pytesseract.image_to_string(region_image, lang=lang, config='--psm 6')
            cleaned_text = clean_text(text, field)

            # Ajouter une traduction si nécessaire
            if field in ["first_name_fr", "last_name_fr"]:
                data[field] = cleaned_text
                if cleaned_text:
                    translated_text = translate_text(cleaned_text, 'fr', 'ar')
                    data[f"{field}_ar"] = translated_text
            elif field in ["first_name_ar", "last_name_ar"]:
                data[field] = cleaned_text
            else:
                data[field] = cleaned_text

        except Exception as e:
            data[field] = f"Erreur: {e}"

    return data

if __name__ == '__main__':
    app.run(debug=True)