import pandas as pd
import matplotlib.pyplot as plt

#ESPAÑA PASADO
import requests
import pandas as pd
from datetime import datetime, timedelta
 
indicador_tecnologia = {
    "1295": "Generación T.Real FV [MWh]",
    "550": "Generación T.Real Ciclo Combinado [MWh]",
    "551": "Generación T.Real Eólica [MWh]",
    "1294": "Generación T.Real CSP [MWh]",
    "1296": "Generación T.Real Biomasa [MWh]",
    "546": "Hidroeléctrica [MWh]",
    "600": "Precio mercado spot [€/MWh]"
}
 
# Lista de indicadores de temperatura real
# lista_indicadores_T_real = ['1295', '550', '551', '1294', '1296', '546']
# Indicador SPOT
indicador_SPOT = '600'
# Lista total de indicadores
# lista_total_indicadores = lista_indicadores_T_real + [indicador_SPOT]
lista_total_indicadores = indicador_SPOT
# URL base de la API de ESIOS
url_base = "https://api.esios.ree.es/"
# Extremo de la API para indicadores
endpoint = "indicators/"
 
# Fechas de inicio y fin
start_date = datetime(2025, 1, 1)
end_date = datetime(2025, 8, 25)
 
# Diccionario para almacenar los DataFrames de cada tecnología
resultados_por_tecnologia = pd.DataFrame()
 
# Iterar sobre cada indicador
url = url_base + endpoint + indicador_SPOT
API_TOKEN = "64500d1f9e6a67020b341fcb883699470df2fc274597ca06308b324db345e8ad"
headers = {'Host': 'api.esios.ree.es', 'x-api-key': API_TOKEN}
# Lista para almacenar los DataFrames de cada día
dfs = pd.DataFrame()
# Iterar sobre cada día del año
current_date = start_date
while current_date <= end_date:
    date_str = current_date.strftime('%Y-%m-%dT00:00')
    date_str_end = current_date.strftime('%Y-%m-%dT23:59')
    params = {'start_date': date_str, 'end_date': date_str_end, 'groupby': 'hour'}
    res = requests.get(url, headers=headers, params=params)
    data = res.json()
    df = pd.DataFrame(data['indicator']['values'])
    df = df[['datetime', 'geo_name','value']]
    # Renombrar columnas para evitar conflictos
    df = df.rename(columns={'datetime': f'datetime_{indicador_SPOT}', 
                            'value': indicador_tecnologia[indicador_SPOT]})
    dfs = pd.concat([dfs, df], axis = 0)
    current_date += timedelta(days=1)

sheet_data = dfs

import pandas as pd
import plotly.express as px

# Convertir columna 'datetime' a formato de fecha y hora (sin ajuste UTC)
sheet_data['datetime'] = pd.to_datetime(sheet_data['datetime_600'].str.replace(r'\+.*$', '', regex=True), errors='coerce')

# Extraer año, día y hora de la columna datetime
sheet_data['year'] = sheet_data['datetime'].dt.year
sheet_data['day'] = sheet_data['datetime'].dt.date
sheet_data['hour'] = sheet_data['datetime'].dt.hour

horas = 6
# Calcular precios medios por hora
hourly_avg_prices = sheet_data.groupby(['year', 'day', 'hour', 'geo_name'])['Precio mercado spot [€/MWh]'].mean().reset_index()

# Identificar las horas más baratas y más caras por día
cheapest_hours = hourly_avg_prices.groupby(['year', 'day', 'geo_name']).apply(
    lambda x: x.nsmallest(horas, 'Precio mercado spot [€/MWh]')['Precio mercado spot [€/MWh]'].mean()
).reset_index(name='cheapest_avg')

expensive_hours = hourly_avg_prices.groupby(['year', 'day', 'geo_name']).apply(
    lambda x: x.nlargest(horas, 'Precio mercado spot [€/MWh]')['Precio mercado spot [€/MWh]'].mean()
).reset_index(name='expensive_avg')

# Calcular el spread diario
daily_spread = pd.merge(cheapest_hours, expensive_hours, on=['year', 'day', 'geo_name'])
daily_spread['spread'] = daily_spread['expensive_avg'] - daily_spread['cheapest_avg']

# Calcular spread mensual por país
daily_spread['month'] = pd.to_datetime(daily_spread['day']).dt.to_period('M')
monthly_spread = daily_spread.groupby(['month', 'geo_name'])['spread'].mean().reset_index()
monthly_spread['month'] = monthly_spread['month'].astype(str)

# Generar una gráfica interactiva del spread diario con Plotly
fig_daily = px.line(
    daily_spread,
    x='day',
    y='spread',
    color='geo_name',
    title="Spread Diario para Operaciones de Batería por País",
    labels={'day': 'Día', 'spread': 'Spread (€)', 'geo_name': 'País'},
    markers=True
)

# Ajustar diseño de la gráfica diaria
fig_daily.update_layout(
    xaxis=dict(tickangle=45),
    yaxis_title='Spread '+'de '+str(horas)+' horas (€/MWh)',
    legend_title="País",
    template="plotly_white"
)

# Mostrar la gráfica interactiva del spread diario
fig_daily.show()

# Generar una gráfica interactiva del spread mensual con Plotly
fig_monthly = px.bar(
    monthly_spread,
    x='month',
    y='spread',
    color='geo_name',
    barmode = 'group',
    title="Spread Mensual Mercado Diario por País",
    labels={'month': 'Mes', 'spread': 'Spread (€/MWh)', 'geo_name': 'País'},
)

# Ajustar diseño de la gráfica mensual
fig_monthly.update_layout(
    xaxis=dict(tickangle=45),
    yaxis_title='Spread '+'de '+str(horas)+' horas (€/MWh)',
    legend_title="País",
    template="plotly_white"
)

# Mostrar la gráfica interactiva del spread mensual
fig_monthly.show()
