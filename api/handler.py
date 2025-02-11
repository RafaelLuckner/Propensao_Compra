from propensityscore.PropensityScore import PropensityScore
import os
import json
import pickle
import pandas as pd
from flask import Flask, request, Response

# loading model 
model = pickle.load(open('models/rf.pkl', 'rb'))

app = Flask(__name__)

@app.route('/predict', methods=['POST'])
def predict():
    test_json = request.get_json()


    if test_json: # there is data
        if isinstance(test_json, dict):  # unique instance
            raw_data = pd.DataFrame(test_json, index=[0])

        else: # multiple instances
            raw_data = pd.DataFrame(json.loads(test_json))


        pipeline = PropensityScore(raw_data)
        pipeline.rename_cols()
        pipeline.transform()
        predict = pipeline.predict(model)
        
        return predict

    else: 
        return Response('{}', status=200, mimetype='application/json')

    

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)