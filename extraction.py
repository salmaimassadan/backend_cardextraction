import pytesseract
import os
from PIL import Image
from flask import Flask, request, jsonify
import re
from flask_cors import CORS

app = Flask(__name__)
CORS(app)
app.config['UPLOAD_FOLDER'] = './uploads'
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# IDCard class definition
class IDCard:
    def __init__(self, first_name, last_name, date_of_birth, place_of_birth, id_code, expiration_date, director):
        self.first_name = first_name
        self.last_name = last_name
        self.date_of_birth = date_of_birth
        self.place_of_birth = place_of_birth
        self.id_code = id_code
        self.expiration_date = expiration_date
        self.director = director

    def to_dict(self):
        return {
            "first_name": self.first_name,
            "last_name": self.last_name,
            "date_of_birth": self.date_of_birth,
            "place_of_birth": self.place_of_birth,
            "id_code": self.id_code,
            "expiration_date": self.expiration_date,
            "director": self.director
        }

# Spécifiez le chemin d'accès à l'exécutable Tesseract
pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

# Spécifiez le chemin d'accès au dossier tessdata
os.environ['TESSDATA_PREFIX'] = r'C:\Program Files\Tesseract-OCR\tessdata'  # Assurez-vous que tessdata contient les fichiers de langue nécessaires

@app.route('/upload', methods=['POST'])
def upload_image():
    if 'file' not in request.files:
        return jsonify({"error": "No file part in the request"}), 400

    file = request.files['file']

    if file.filename == '':
        return jsonify({"error": "No file selected"}), 400

    if file:
        try:
            # Sauvegarder le fichier téléchargé
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], file.filename)
            file.save(file_path)

            # Prétraitement de l'image : Convertir en niveaux de gris et appliquer un seuillage
            img = Image.open(file_path).convert('L')  # Convertir en niveaux de gris
            img = img.point(lambda x: 0 if x < 128 else 255)  # Appliquer un seuillage

            # Effectuer l'OCR sur l'image téléchargée
            extracted_text = pytesseract.image_to_string(img, lang='ara+fra')  # Utilisez ara+fra pour l'arabe et le français

            # Debug : afficher le texte extrait pour vérifier si tout va bien
            print("Extracted Text:")
            print(extracted_text)

            # Diviser les lignes et supprimer les lignes vides
            lines = [line.strip() for line in extracted_text.split('\n') if line.strip()]

            # Vérifier si c'est une carte d'identité marocaine
            if "ROYAUME DU MAROC" not in extracted_text:
                os.remove(file_path)
                return jsonify({"error": "This is not a Moroccan ID card"}), 400

            # Initialiser les variables pour les champs
            first_name = ""
            last_name = ""
            date_of_birth = ""
            place_of_birth = ""
            id_code = ""
            expiration_date = ""
            director = ""

            # Extraire les informations des lignes
            for line in lines:
                # Extraire le nom de famille et le prénom
                if re.search(r"^[A-ZÀ-ÿ\s]+$", line) and "ROYAUME" not in line and "CARTE" not in line:
                    if not last_name:
                        last_name = line.strip()
                    elif not first_name and last_name:  # Prénom après le nom de famille
                        first_name = line.strip()

                # Extraire la date de naissance (format : dd.mm.yyyy)
                if re.search(r"(\d{2}.\d{2}.\d{4})", line) and not date_of_birth:
                    date_of_birth = re.search(r"(\d{2}.\d{2}.\d{4})", line).group(1)

                # Extraire le lieu de naissance (gérer les accents)
                if "à" in line:
                    place_match = re.search(r"à\s+([A-Za-zÀ-ÿ\s]+)", line)
                    if place_match:
                        place_of_birth = place_match.group(1).strip()
                        # Gérer les cas spéciaux ou mauvaises interprétations ici
                        if place_of_birth.lower().startswith('a’'):  # Gérer les erreurs OCR comme 'a’'
                            place_of_birth = place_of_birth[2:].strip()  # Supprimer le caractère spécial

                # Extraire le code d'identification (8 caractères alphanumériques avec au moins une lettre et un chiffre)
                if re.search(r"\b(?=.*[A-Za-z])(?=.*\d)[A-Za-z0-9]{8}\b", line):
                    id_code_match = re.search(r"\b(?=.*[A-Za-z])(?=.*\d)([A-Za-z0-9]{8})\b", line)
                    if id_code_match:
                        id_code = id_code_match.group(1)

                # Extraire la date d'expiration
                if "Valable jusqu'au" in line:
                    expiration_date_match = re.search(r"\d{2}.\d{2}.\d{4}", line)
                    if expiration_date_match:
                        expiration_date = expiration_date_match.group(0)

                # Extraire le directeur général
                if "مدير" in line:
                    director_match = re.search(r"([أ-ي]+(?: [أ-ي]+)*)", line)
                    if director_match:
                        director = director_match.group(1).strip()

            # Créer l'objet IDCard avec les détails extraits
            id_card = IDCard(first_name, last_name, date_of_birth, place_of_birth, id_code, expiration_date, director)

            # Supprimer le fichier téléchargé après le traitement
            os.remove(file_path)

            # Retourner l'objet IDCard sous forme de JSON
            return jsonify(id_card.to_dict())

        except Exception as e:
            return jsonify({"error": f"An error occurred: {str(e)}"}), 500

if __name__ == '__main__':
    app.run(host="0.0.0.0", port=6000)