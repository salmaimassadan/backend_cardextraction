from flask import Flask, request, jsonify
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

users = {}

@app.route('/signup', methods=['POST'])
def signup():
    data = request.json
    username = data.get('username')
    password = data.get('password')
    email = data.get('email')

    if username in users:
        return jsonify({"error": "Utilisateur déjà existant"}), 409

    users[username] = {"password": password, "email": email}
    return jsonify({"message": "Utilisateur créé avec succès"}), 201

@app.route('/login', methods=['POST'])
def login():
    data = request.json
    username = data.get('username')
    password = data.get('password')

    if username not in users or users[username]['password'] != password:
        return jsonify({"error": "Nom d'utilisateur ou mot de passe incorrect"}), 400

    return jsonify({"message": "Connexion réussie"}), 200

if __name__ == '__main__':
    app.run(host="0.0.0.0", port=5000)
