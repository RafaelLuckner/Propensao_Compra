import os
from propensityscore.PropensityScore import PropensityScore
import json
import pickle
import pandas as pd
from flask import Flask, request, jsonify  # Importa jsonify corretamente

# Carregando o modelo
model = pickle.load(open('models/rf.pkl', 'rb'))

app = Flask(__name__)

@app.route('/predict', methods=['POST'])
def predict():
    test_json = request.get_json()

    if test_json:  # Se houver dados
        if isinstance(test_json, dict):  # Caso seja uma única instância
            raw_data = pd.DataFrame(test_json, index=[0])
        else:  # Caso sejam múltiplas instâncias
            raw_data = pd.DataFrame(json.loads(test_json))

        # Pipeline de transformação
        pipeline = PropensityScore(raw_data)
        pipeline.rename_cols()
        pipeline.transform()
        prediction = pipeline.predict(model)

        return jsonify({"prediction": prediction})  # Agora correto

    return jsonify({}), 400  # Resposta vazia com código de erro

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))  # Render define a porta dinamicamente
    app.run(host='0.0.0.0', port=port)
