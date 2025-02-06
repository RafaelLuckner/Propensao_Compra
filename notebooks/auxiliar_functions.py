import pickle
import random
import sklearn
import inflection
import numpy             as np
import pandas            as pd 
import seaborn           as sns 
# import scikitplot        as skplt

import scipy.stats       as stats
import matplotlib.pyplot as plt

from IPython.display         import Image
from boruta                  import BorutaPy

from sklearn.pipeline          import Pipeline
from sklearn                   import metrics as mt
from sklearn.compose           import ColumnTransformer
from sklearn                   import model_selection as ms
from sklearn.feature_selection import SelectKBest, f_classif
from sklearn.model_selection   import cross_val_score, StratifiedKFold
from sklearn.metrics           import roc_curve, auc, make_scorer, precision_score, recall_score
from sklearn.preprocessing     import MinMaxScaler, RobustScaler, OneHotEncoder, LabelEncoder, StandardScaler

from sklearn.linear_model    import LogisticRegression
from sklearn.ensemble        import RandomForestClassifier
from sklearn.tree            import DecisionTreeClassifier, plot_tree

def preparation_train(X_train, y_train):
    """Prepara os dados de treino e retorna o conjunto processado e os encoders."""
    X_train['response'] = y_train  # Adiciona a coluna de resposta ao DataFrame
    
    # Normalização
    ss = StandardScaler()
    X_train['annual_premium'] = ss.fit_transform(X_train[['annual_premium']])
    
    # Rescaling
    mms_age = MinMaxScaler()
    mms_vintage = MinMaxScaler()
    mms_damage = MinMaxScaler()
    X_train['age'] = mms_age.fit_transform(X_train[['age']].values)
    # X_train['vintage'] = mms_vintage.fit_transform(X_train[['vintage']])
    X_train['pct_damage_region'] = mms_damage.fit_transform(X_train[['pct_damage_region']])
    
    # Encoders
    # target_gender = X_train.groupby('gender')['response'].mean()
    # X_train['gender'] = X_train['gender'].map(target_gender)
    
    target_policy_sales = X_train.groupby('policy_sales_channel')['response'].mean()
    X_train['policy_sales_channel'] = X_train['policy_sales_channel'].map(target_policy_sales)
    
    target_vehicle_damage = X_train.groupby('vehicle_damage')['response'].mean()
    X_train['vehicle_damage'] = X_train['vehicle_damage'].map(target_vehicle_damage)
    
    frequency_region_code = X_train['region_code'].value_counts(normalize=True)
    X_train['region_code'] = X_train['region_code'].map(frequency_region_code)
    
    X_train['vehicle_age'] = X_train['vehicle_age'].apply(lambda x: 0 if x == '< 1 Year'
                                                          else 1 if x == '1-2 Year'
                                                          else 2 if x == '> 2 Years' else x)
    
    X_train.drop(columns=['response'], inplace=True)  # Remove a coluna extra antes de retornar

    return X_train, [ss, mms_age, mms_vintage, mms_damage, target_policy_sales, target_vehicle_damage, frequency_region_code]
    
def preparation_val(X_val, encoders):
    """Aplica os encoders no conjunto de validação."""
    ss, mms_age, mms_vintage, mms_damage, target_policy_sales, target_vehicle_damage, frequency_region_code = encoders

    X_val['annual_premium'] = ss.transform(X_val[['annual_premium']])
    X_val['age'] = mms_age.transform(X_val[['age']].values)
    # X_val['vintage'] = mms_vintage.transform(X_val[['vintage']])
    X_val['pct_damage_region'] = mms_damage.transform(X_val[['pct_damage_region']])
    
    X_val['policy_sales_channel'] = X_val['policy_sales_channel'].map(target_policy_sales)
    X_val['vehicle_damage'] = X_val['vehicle_damage'].map(target_vehicle_damage)
    X_val['region_code'] = X_val['region_code'].map(frequency_region_code)
    
    X_val['vehicle_age'] = X_val['vehicle_age'].apply(lambda x: 0 if x == '< 1 Year'
                                                      else 1 if x == '1-2 Year'
                                                      else 2 if x == '> 2 Years' else x)
    return X_val

# Cross-validation com preparação dos dados
def cross_validation_pipeline(df, model, n_splits=5, k=2000):
    skf = StratifiedKFold(n_splits=n_splits, shuffle=True, random_state=12)
    columns = ['vehicle_damage', 'previously_insured', 'age','policy_sales_channel',
           'annual_premium', 'region_code', 'pct_damage_region', 'vehicle_age','response']
    X = df[columns].drop('response', axis=1).copy()
    y = df['response'].copy()

    precision_results = []  
    recall_results = []
    
    for train_idx, val_idx in skf.split(X, y):
        X_train, X_validation = X.iloc[train_idx].copy(), X.iloc[val_idx].copy()
        y_train, y_validation = y.iloc[train_idx], y.iloc[val_idx]
        
        # Preparar os dados do fold de treino
        X_train, encoders = preparation_train(X_train, y_train)
        
        # Preparar os dados do fold de validação
        X_val = preparation_val(X_validation, encoders)
        
        # Treinar o modelo com os dados de treino
        model.fit(X_train, y_train)
        
        # Fazer previsões no conjunto de validação
        y_proba = model.predict_proba(X_val)  # Probabilidades

        df_validation = pd.concat([X_validation, y_validation],axis=1)

        precision = precision_top_k(df_validation, y_proba, k = k)
        recall = recall_top_k(df_validation, y_proba, k=k)
        
        precision_results.append(precision)
        recall_results.append(recall)
        
        
    return (np.round(np.mean(precision_results),4)),(np.round(np.mean(recall_results),4))

def params_tuning(model, param_grid, df, max_iters=50 ):
    best_params = []
    best_k = 0
    for n in range(max_iters):
        params = {key: random.choice(values) for key, values in param_grid.items()}
        model.set_params(**params)
    
        cross_val_result = cross_validation_pipeline(df, n_splits=5, model=model)
        if cross_val_result > best_k:
            best_k = cross_val_result
            best_params = params
            print(f'Melhor k: {best_k}')
            print(f'Melhores_parametros: {best_params}')
            
        print(f'n iterações{n}')

    return best_params, best_k

def curva_ganho(yproba, y_val, close=False, subplot = 2, figsize =(15,4), text=(0.03,0.85), pct_clientes = 0.40):
    data = {
        'prob_compra': yproba[:,1],
        'real_compra': y_val
    }
    df = pd.DataFrame(data)
    
    # Ordenar os dados pela probabilidade prevista (decrescente)
    df = df.sort_values(by='prob_compra', ascending=False)
    
    # Calcular a proporção acumulada de respostas capturadas pelo modelo
    df['resposta_acumulada'] = df['real_compra'].cumsum()
    df['proporcao_resposta'] = df['resposta_acumulada'] / df['real_compra'].sum()
    
    # Calcular a proporção de clientes acumulada
    df['proporcao_clientes'] = np.arange(1, len(df) + 1) / len(df)
    
    # Curva aleatória (baseline)
    baseline = df['proporcao_clientes']

    plt.figure(figsize=figsize)
    plt.subplot(1,subplot,1)
    # Criar a figura e o gráfico
    plt.plot(df['proporcao_clientes'], df['proporcao_resposta'], label='Modelo')
    plt.plot(df['proporcao_clientes'], baseline, label='Baseline', linestyle='--', color='red')
    
    # Configurar os eixos para 0 a 1
    plt.xlim(0, 1.001)
    plt.ylim(0, 1.001)
    
    # Configurar títulos e legendas
    plt.title('Curva de Ganho')
    plt.xlabel('Proporção de Clientes')
    plt.ylabel('Proporção de Respostas Capturadas')
    plt.legend()
    plt.grid(True)

    best = df.loc[df['proporcao_clientes']>= pct_clientes,'proporcao_resposta'].reset_index(drop=True)[1]

    plt.annotate(
            f'{np.round(best,4)*100:.2f}% dos interessados',                 # Texto da anotação
        xy=(pct_clientes,best),             # Coordenadas do ponto (x, y) onde a seta aponta
        xytext=(text),          # Posição do texto da anotação
        arrowprops=dict(arrowstyle='->', color='black'),  # Estilo da seta
        fontsize=12, color='black' # Estilo do texto
    )

    # grafico de densidade
    plt.subplot(1,subplot,2)
    plt.title('Distribuição dos Interessados')
    sns.kdeplot(x = df['prob_compra'],hue =df['real_compra'], fill=True, alpha=0.6, multiple="stack" )
    plt.ylabel('Densidade de Clientes')
    plt.xlabel('Probabilidade de Compra')
    plt.legend(['Interessados','Não Interessados'])
    if close:
        plt.close(fig)

def precision_top_k(df_validation, yproba, k=1000):
    data = df_validation.copy()
    data['proba'] = yproba[:,1]
    
    data = data.sort_values(by='proba', ascending=False).reset_index(drop=True)
    data['total_previsoes'] = data.index+1
    data = data[['total_previsoes','response','proba']]
    data['previsoes_corretas'] = data['response'].cumsum()
    data['precision_top_k'] = data['previsoes_corretas'] / data['total_previsoes']
    # print(f'Precision top K: {data['precision_top_k'].iloc[k]}')
    return data['precision_top_k'].iloc[k]

def recall_top_k(df_validation, yproba, k=1000):
    data = df_validation.copy()
    data['proba'] = yproba[:,1]
    
    data = data.sort_values(by='proba', ascending=False).reset_index(drop=True)
    data['total_response'] = data['response'].sum()
    data = data[['total_response','response','proba']]
    data['previsoes_corretas'] = data['response'].cumsum()

    data['recall_top_k'] = data['previsoes_corretas'] / data['total_response']
    return data['recall_top_k'].iloc[k]




    