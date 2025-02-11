import pickle
import inflection
import pandas as pd
import numpy as np

class PropensityScore():

    def __init__(self, data ):
        self.data = data
        self.encoders = pickle.load(open("../src/features/encoders.pkl", "rb"))

    def visualize(self):
        return self.data
    
    def rename_cols(self):
        df = self.data
        cols = list(df.columns)
        lista = [inflection.underscore(coluna) for coluna in cols ]
        df.columns = lista
        self.data = df
        return df


    def transform(self):
        ss, mms_age,mms_vintage, mms_damage, target_policy_sales, target_vehicle_damage, frequency_region_code, damage_region = self.encoders

        df = self.data.copy()
        df['pct_damage_region'] = df['region_code'].map(damage_region)

        df['annual_premium'] = ss.transform(df[['annual_premium']])
        
        df['age'] = mms_age.transform(df[['age']].values)
        df['pct_damage_region'] = mms_damage.transform(df[['pct_damage_region']])
        df['pct_damage_region'] = df['pct_damage_region'].fillna(0)

        df['policy_sales_channel'] = df['policy_sales_channel'].map(target_policy_sales)
        df['vehicle_damage'] = df['vehicle_damage'].map(target_vehicle_damage)
        df['region_code'] = df['region_code'].map(frequency_region_code)
        
        df['vehicle_age'] = df['vehicle_age'].apply(lambda x: 0 if x == '< 1 Year'
                                                        else 1 if x == '1-2 Year'
                                                        else 2 if x == '> 2 Years' else x)

        df.set_index('id', inplace=True)
        df = df[['age', 'region_code', 'previously_insured', 'vehicle_age',
                'vehicle_damage', 'annual_premium', 'policy_sales_channel','pct_damage_region']]
        
        self.data = df  
        return df
        

    def predict(self, model):
        """ Retorna o dataframe com as probabilidades. """
        df = self.data.copy()
        df['score'] = model.predict_proba(self.data)[:,1]

        return df.to_json(orient = 'records', date_format='iso') 
