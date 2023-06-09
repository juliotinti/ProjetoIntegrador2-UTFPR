import streamlit as st
import pandas as pd
import pymysql.cursors
import numpy as np
import plotly.express as px 
from datetime import time
from datetime import datetime, timedelta

def seconds_to_hours(seconds):
    hours = round((seconds / 3600),2)
    return f"{hours} Horas"


@st.cache_data
def load_data(date_select):
    cursor = conn.cursor()
    cursor.execute("SELECT moment, voltage, current, power_W, energy_WH, power_factor_measured, power_factor_calc, phase_angle_measured, phase_angle_calc, opMode FROM " + tableName)
    data = cursor.fetchall()
    df = pd.DataFrame(data, columns=['moment', 'voltage', 'current', 'power_W', 'energy_WH', 'power_factor_measured', 'power_factor_calc', 'phase_angle_measured', 'phase_angle_calc', 'opMode'])
    df['moment'] = pd.to_datetime(df['moment'])
    df["week"] = df["moment"].apply(lambda x: x.strftime("%Y-%U"))
    df = df[(df['moment']>=date_select[0]) & (df['moment']<date_select[1])]
    
    # Get the unique weeks represented in the data
    
    return df


charts = {
    'Tensão': lambda df: px.scatter(df, x = 'moment', y = 'voltage', title='Tensão [V]', labels = {'voltage': 'Tensão', 'moment': 'Horário'}),
    'Corrente': lambda df: px.scatter(df, x = 'moment', y = 'current', title='Corrente [A]',  labels = {'current': 'Corrente', 'moment': 'Horário'}),
    'Potência': lambda df: px.scatter(df, x = 'moment', y = 'power_W', title='Potência [W]',  labels = {'power_W': 'Potência', 'moment': 'Horário'}),
    'Energia ': lambda df: px.scatter(df, x = 'moment', y = 'energy_WH', title='Energia [W/h]',  labels = {'energy_WH': 'Energia', 'moment': 'Horário'}),
    'Fator de Potência': lambda df: px.scatter(df, x = 'moment', y = ['power_factor_measured', 'power_factor_calc'], title='Fator de Potência',  color_discrete_map = {'power_factor_measured': 'green', 'power_factor_calc': 'blue'} , labels = {'power_factor_measured': 'Medido', 'power_factor_calc': 'Calculado', 'moment': 'Horário'}),
    'Ângulo de Fase' : lambda df: px.scatter(df, x = 'moment', y = ['phase_angle_measured', 'phase_angle_calc'],  title='Ângulo de Fase [Graus]',  color_discrete_map = {'phase_angle_measured': 'green', 'phase_angle_calc': 'blue'} , labels = {'phase_angle_measured': 'Medido', 'phase_angle_calc': 'Calculado', 'moment': 'Horário'}),
}

mapping = {1: 'On', 2: 'StandBy', 0: 'Off'}

measuringTime = 5
tableName = 'compressor_measurements'
#tableName = 'imported'

conn = pymysql.connect(host='192.168.18.27',
                       user='piuser',
                       password='piuser',
                       database='pi2')

# conn = pymysql.connect(host='localhost',
#                        user='root',
#                        password='root',
#                        database='node_test')


if 'min' not in st.session_state:
    cursor = conn.cursor()
    cursor.execute("SELECT Min(moment) FROM "+ tableName)
    st.session_state.min = cursor.fetchone()[0]

    cursor.execute("SELECT Max(moment) FROM "+ tableName)
    st.session_state.max= cursor.fetchone()[0]
    
    if isinstance(st.session_state.min, str):
        st.session_state.min = datetime.strptime(st.session_state.min, '%Y-%m-%d %H:%M:%S')
    if isinstance(st.session_state.max, str):
        st.session_state.max = datetime.strptime(st.session_state.max, '%Y-%m-%d %H:%M:%S')


page1 = "Monitoramento Compressor - UTFPR"
st.set_page_config(page_title=page1)
st.markdown("# " + page1)
st.write(
    "Escolha os limites de data que você quer ver o funcionamento do compressor da UTFPR: "
)

date_select = st.slider('Select the time range:',
                        value=(st.session_state.min, st.session_state.max),
                        min_value=st.session_state.min,
                        max_value=st.session_state.max,
                        format="DD/MM/YY - hh:mm",
                        key=("slider", st.session_state.min, st.session_state.max))


st.sidebar.header("Data das informações: \n" + str(date_select[0]) + " até \n" + str(date_select[1]))
charts_selected = st.multiselect('Selecione os gráficos que deseja ver:', list(charts.keys()), default=list(charts.keys()))

df = load_data(date_select)

for chart_name in charts_selected:
    chart_function = charts[chart_name]
    with st.container():
        fig = chart_function(df)
        st.plotly_chart(fig, use_container_width=True)


qtyOff = df[df['opMode'] == 0]['opMode'].count()
qtyOffSec = qtyOff * measuringTime

qtyOn = df[df['opMode'] == 1]['opMode'].count()
qtyOnSec = qtyOn * measuringTime

qtyStandby = df[df['opMode'] == 2]['opMode'].count()
qtyStandbySec = qtyStandby * measuringTime

with st.container():
    st.write("Modos de operação")
    stackeddf = df
    stackeddf['moment'] = pd.to_datetime(stackeddf['moment']).dt.strftime('%Y-%m-%d')
    dailyValues = stackeddf.groupby(['moment','opMode']).size()
    result_df = dailyValues.apply(lambda x: round((x*5)/60),2).reset_index(name='result')
    groupedAgain = result_df.groupby(['moment', 'opMode'])['result'].sum().reset_index()
    groupedAgain['opMode'] = groupedAgain['opMode'].replace(mapping)
    fig = px.bar(groupedAgain,  x='moment',  y='result', color='opMode', labels = {'result': 'Tempo de operação (m)', 'moment': 'Horário','opMode':'Modo de Operação' })
    st.plotly_chart(fig, use_container_width=True)

# st.dataframe(result_df)
# st.dataframe(groupedAgain)

#Para as métricas de modo de operação, quantas vezes ficou ligado, quantas vezes desligado, o outro modo de operação lá e por fim a qtd de Ah do período
with st.sidebar:
    if (len(df['current']) != 0):
        currentAvg = df['current'].mean()
        powerFacAvg = df['power_factor_calc'].mean()
        st.metric("Corrente Média no período",  str(round(currentAvg, 3)) + " A")
        st.metric("Fator de Potência calculado no período", round(powerFacAvg, 3))
        st.metric("Tempo desligado durante o período", seconds_to_hours(qtyOffSec))
        st.metric("Tempo ligado durante o período", seconds_to_hours(qtyOnSec))
        st.metric("Tempo em standby durante o período", seconds_to_hours(qtyStandbySec))

st.text('Lucas Moletta')