import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt

st.title("Dashboard de Calidad del Aire en Colombia")

# Cargar datos
df = pd.read_csv("calidad_aire_colombia.csv")

# Filtros
ciudad = st.sidebar.selectbox("Selecciona una ciudad", df["ciudad"].unique())
df_filtrado = df[df["ciudad"] == ciudad]

# Métricas
st.metric("Promedio PM2.5", round(df_filtrado["pm25"].mean(), 2))

# Gráfico
fig, ax = plt.subplots()
ax.plot(df_filtrado["fecha"], df_filtrado["pm25"])
ax.set_title("PM2.5 en el tiempo")
st.pyplot(fig)

# Tabla
st.dataframe(df_filtrado)
