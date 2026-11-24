"""Dashboard interactivo - Calidad del aire en Colombia (PM2.5).

Extensión comunicativa del EDA de la Tarea 3.
Estudiante: Francisco José Velandia Rincón - UNAD - Programación para el análisis de datos.
"""
import unicodedata
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
import streamlit as st
from scipy import stats

RUTA_DATOS = Path(__file__).parent / 'dataset.csv'
NORMA_COLOMBIA = 25   # µg/m³, norma anual colombiana (Res. 2254/2017)
GUIA_OMS = 5          # µg/m³, guía anual OMS 2021
CATEGORIAS = ['Bajo (≤10)', 'Moderado (10-15]', 'Alto (15-25]', 'Excede norma (>25)']

def mostrar(fig):
    """Muestra la figura en Streamlit y la cierra para liberar memoria."""
    st.pyplot(fig)
    plt.close(fig)


st.set_page_config(page_title='Calidad del aire en Colombia', page_icon='🌫️', layout='wide')
sns.set_theme(style='whitegrid')


# ----------------------------------------------------------------------------
# Carga y limpieza (misma lógica de la Tarea 3)
# ----------------------------------------------------------------------------
@st.cache_data(show_spinner='Cargando datos...')
def cargar_datos():
    df = pd.read_csv(RUTA_DATOS, thousands=',')
    claves = ['ID Estacion', 'Variable', 'Tiempo de exposición (horas)', 'Año']
    df = df.drop_duplicates().drop_duplicates(subset=claves).reset_index(drop=True)
    df['Departamento'] = df['Nombre del Departamento'].apply(
        lambda s: unicodedata.normalize('NFKD', str(s)).encode('ascii', 'ignore').decode().upper().strip())
    pm25 = df[(df['Variable'] == 'PM2.5') & (df['Tiempo de exposición (horas)'] == 24)].copy()
    pm25['Categoría'] = pd.cut(pm25['Promedio'], [0, 10, 15, 25, np.inf], labels=CATEGORIAS)
    pm10 = df[(df['Variable'] == 'PM10') & (df['Tiempo de exposición (horas)'] == 24)]
    return pm25, pm10


try:
    pm25, pm10 = cargar_datos()
except FileNotFoundError:
    st.error('No se encontró el archivo dataset.csv junto a app.py. Revise el README para descargarlo.')
    st.stop()

# ----------------------------------------------------------------------------
# Sidebar: filtros
# ----------------------------------------------------------------------------
with st.sidebar:
    st.header('Filtros')
    deptos = sorted(pm25['Departamento'].unique())
    sel_deptos = st.multiselect('Departamento', deptos, default=[], key='f_deptos', placeholder='Todos los departamentos',
                                help='Deje vacío para ver el país completo.')
    sel_tipo = st.multiselect('Tipo de estación', ['Fija', 'Indicativa'], default=['Fija', 'Indicativa'], key='f_tipo',
                              help='Fija: permanente. Indicativa: campaña temporal de medición.')
    a_min, a_max = int(pm25['Año'].min()), int(pm25['Año'].max())
    rango_anio = st.slider('Años', a_min, a_max, (a_min, a_max), key='f_anio')
    rango_pm = st.slider('Rango de PM2.5 promedio anual (µg/m³)', 0.0, float(np.ceil(pm25['Promedio'].max())),
                         (0.0, float(np.ceil(pm25['Promedio'].max()))), step=0.5, key='f_pm')
    st.button('Restablecer filtros',
              on_click=lambda: [st.session_state.pop(k, None) for k in ('f_deptos', 'f_tipo', 'f_anio', 'f_pm')])
    st.caption('Los gráficos, las métricas y la prueba estadística se actualizan con estos filtros.')


def filtrar(d):
    d = d[d['Año'].between(*rango_anio)]
    if sel_deptos:
        d = d[d['Departamento'].isin(sel_deptos)]
    return d


f = filtrar(pm25)
f = f[f['Tipo de Estación'].isin(sel_tipo) & f['Promedio'].between(*rango_pm)]
f10 = filtrar(pm10)

# ----------------------------------------------------------------------------
# Encabezado
# ----------------------------------------------------------------------------
st.title('🌫️ ¿Qué tan limpio es el aire que respiramos en Colombia?')
st.markdown('**Análisis de partículas finas (PM2.5) · Dataset: _Calidad del Aire en Colombia (Promedio Anual)_, '
            'IDEAM / datos.gov.co · 2011–2024**')
st.caption('Francisco José Velandia Rincón · Programación para el análisis de datos · UNAD')

if f.empty:
    st.warning('Los filtros actuales no dejan ningún registro. Amplíe la selección en la barra lateral.')
    st.stop()

# ----------------------------------------------------------------------------
# Exploración de datos
# ----------------------------------------------------------------------------
st.header('1. Exploración de datos')
c1, c2, c3, c4 = st.columns(4)
c1.metric('Registros (estación-año)', f'{len(f):,}'.replace(',', '.'))
c2.metric('PM2.5 promedio (µg/m³)', f"{f['Promedio'].mean():.2f}")
c3.metric('Desviación estándar (µg/m³)', f"{f['Promedio'].std():.2f}" if len(f) > 1 else 'n/d',
          help='Qué tanto se alejan los valores del promedio: más alta = más desigualdad entre estaciones.')
c4.metric('Superan la norma de 25 µg/m³', f"{(f['Promedio'] > NORMA_COLOMBIA).mean() * 100:.1f} %")

cols_tabla = ['Año', 'Departamento', 'Nombre del Municipio', 'Estación', 'Tipo de Estación',
              'Promedio', 'Percentil 98', 'Máximo', 'No. de datos']
st.dataframe(f[cols_tabla].sort_values('Promedio', ascending=False).rename(columns={'Promedio': 'PM2.5 promedio anual'}),
             width='stretch', hide_index=True, height=300)
st.download_button('Descargar datos filtrados (CSV)', f[cols_tabla].to_csv(index=False).encode('utf-8'),
                   file_name='pm25_filtrado.csv', mime='text/csv')

# ----------------------------------------------------------------------------
# Visualizaciones
# ----------------------------------------------------------------------------
st.header('2. Visualizaciones')
tab1, tab2, tab3, tab4 = st.tabs(['Por tipo de estación', 'Evolución en el tiempo',
                                  'Relación PM10 vs PM2.5', 'Departamentos'])

with tab1:
    fig, ax = plt.subplots(figsize=(8, 4.5))
    orden = [t for t in ['Fija', 'Indicativa'] if t in f['Tipo de Estación'].unique()]
    sns.boxplot(data=f, x='Tipo de Estación', y='Promedio', order=orden, hue='Tipo de Estación', legend=False,
                palette={'Fija': '#4c72b0', 'Indicativa': '#dd8452'}, flierprops={'markerfacecolor': '#d62728', 'markersize': 4}, ax=ax)
    ax.axhline(NORMA_COLOMBIA, color='black', ls='--', lw=1.2, label='Norma de Colombia (25)')
    ax.axhline(GUIA_OMS, color='green', ls=':', lw=1.2, label='Recomendación OMS (5)')
    ax.set(title='Contaminación por partículas finas según el tipo de estación',
           xlabel='Tipo de estación', ylabel='PM2.5 promedio anual (µg/m³)')
    ax.legend(loc='upper left')
    mostrar(fig)
    st.caption('Cada caja resume dónde está la mayoría de las estaciones; los puntos rojos son casos excepcionales.')

with tab2:
    serie = f.groupby('Año')['Promedio'].agg(['median', 'count'])
    fig, ax = plt.subplots(figsize=(10, 4.5))
    ax.plot(serie.index, serie['median'], marker='o', color='#1f77b4', label='PM2.5 típico (mediana)')
    ax.axhline(NORMA_COLOMBIA, color='black', ls='--', lw=1.2, label='Norma de Colombia (25)')
    ax.set(title='¿Ha mejorado el aire? Evolución anual de las partículas finas', xlabel='Año',
           ylabel='PM2.5 típico (µg/m³)')
    ax2 = ax.twinx()
    ax2.bar(serie.index, serie['count'], alpha=0.15, color='gray', label='Mediciones disponibles')
    ax2.set_ylabel('Número de mediciones'); ax2.grid(False)
    h1, l1 = ax.get_legend_handles_labels(); h2, l2 = ax2.get_legend_handles_labels()
    ax.legend(h1 + h2, l1 + l2, loc='upper right')
    ax.set_ylim(bottom=0)
    mostrar(fig)
    st.caption('Las barras grises muestran que la red de medición creció con los años: parte de la mejora '
               'aparente puede deberse a que hoy se mide en más lugares.')

with tab3:
    ancho = (f[['ID Estacion', 'Año', 'Promedio']].rename(columns={'Promedio': 'PM2.5'})
             .merge(f10[['ID Estacion', 'Año', 'Promedio']].rename(columns={'Promedio': 'PM10'}),
                    on=['ID Estacion', 'Año']))
    if len(ancho) < 3:
        st.info('No hay suficientes estaciones con ambas mediciones para esta selección.')
    else:
        r = ancho['PM10'].corr(ancho['PM2.5'])
        fig, ax = plt.subplots(figsize=(8, 5))
        sns.regplot(data=ancho, x='PM10', y='PM2.5', scatter_kws={'alpha': 0.5, 's': 25, 'color': '#4c72b0'},
                    line_kws={'color': '#d62728'}, ax=ax)
        ax.set(title='Partículas gruesas (PM10) y finas (PM2.5): suelen subir juntas',
               xlabel='Partículas gruesas PM10 (µg/m³)', ylabel='Partículas finas PM2.5 (µg/m³)')
        mostrar(fig)
        st.caption(f'{len(ancho)} estaciones-año con ambas mediciones. Asociación entre ambas: {r:.2f} '
                   '(1 = suben exactamente juntas, 0 = sin relación). Asociación no implica que una cause la otra.')

with tab4:
    top = f.groupby('Departamento')['Promedio'].agg(['mean', 'count'])
    top = top[top['count'] >= 5].sort_values('mean', ascending=True).tail(15)
    if top.empty:
        st.info('Se necesitan al menos 5 registros por departamento para compararlos.')
    else:
        fig, ax = plt.subplots(figsize=(9, 0.4 * len(top) + 1.5))
        ax.barh(top.index, top['mean'], color='#e6550d')
        ax.axvline(NORMA_COLOMBIA, color='black', ls='--', lw=1.2, label='Norma de Colombia (25)')
        ax.set(title='Departamentos con más partículas finas (promedio de sus estaciones)',
               xlabel='PM2.5 promedio (µg/m³)', ylabel='')
        ax.legend(loc='lower right')
        mostrar(fig)
        st.caption('Solo se muestran departamentos con al menos 5 registros, para no sacar conclusiones con muy pocos datos.')

# ----------------------------------------------------------------------------
# Validación estadística
# ----------------------------------------------------------------------------
st.header('3. Validación estadística: ¿las estaciones fijas y las temporales miden lo mismo?')
st.markdown(
    '**Resultado del análisis original (todo el país, 2011–2024):** las estaciones fijas registran en promedio '
    '**16,9 µg/m³** y las temporales (indicativas) **15,2 µg/m³**. Con una prueba t, la diferencia resultó '
    '**estadísticamente significativa** (t = 2,80; p = 0,005): es muy poco probable que sea casualidad.')
st.markdown('**En lenguaje claro:** las estaciones permanentes, que están sobre todo en grandes ciudades, '
            'reportan algo más de contaminación que las campañas temporales. Pero la diferencia es pequeña '
            '(menos de 2 µg/m³) y se explica más por *dónde y por cuánto tiempo* se mide que por el tipo de estación en sí.')

fija = f.loc[f['Tipo de Estación'] == 'Fija', 'Promedio']
indic = f.loc[f['Tipo de Estación'] == 'Indicativa', 'Promedio']
st.subheader('Con los filtros que usted eligió')
if len(fija) >= 3 and len(indic) >= 3:
    t, p = stats.ttest_ind(fija, indic, equal_var=False)
    a, b = st.columns(2)
    a.metric('Estaciones fijas (promedio)', f'{fija.mean():.2f} µg/m³', help=f'{len(fija)} registros')
    b.metric('Estaciones indicativas (promedio)', f'{indic.mean():.2f} µg/m³', help=f'{len(indic)} registros')
    if p < 0.05:
        st.success(f'La diferencia de {abs(fija.mean() - indic.mean()):.2f} µg/m³ es lo bastante grande como para '
                   f'no atribuirse al azar (probabilidad de casualidad: {p:.3f}).')
    else:
        st.info(f'Con esta selección, la diferencia de {abs(fija.mean() - indic.mean()):.2f} µg/m³ podría deberse '
                f'al azar (probabilidad de casualidad: {p:.3f}); no hay evidencia suficiente de que sean distintas.')
else:
    st.info('Para comparar, la selección debe incluir ambos tipos de estación con al menos 3 registros cada uno.')

# ----------------------------------------------------------------------------
# Hallazgos / narrativa para audiencia no técnica
# ----------------------------------------------------------------------------
st.header('4. Hallazgos: qué significan estos datos')
st.caption('Las cifras de esta sección corresponden a todo el país y todos los años (no cambian con los filtros).')

n_est = pm25['ID Estacion'].nunique()
mediana_pm = pm25['Promedio'].median()
pct_excede = (pm25['Promedio'] > NORMA_COLOMBIA).mean() * 100

st.subheader('¿Qué analicé?')
st.write(f'Revisé las mediciones oficiales de calidad del aire que el IDEAM reúne de {n_est} estaciones de medición de partículas finas, repartidas en 24 '
         'departamentos de Colombia, entre 2011 y 2024. Me concentré en las **partículas finas (PM2.5)**, polvo y hollín '
         'tan pequeños que entran hasta los pulmones y se relacionan con enfermedades respiratorias y del corazón. '
         'Antes de analizar, eliminé más de 14.000 filas repetidas que traía el archivo.')

st.subheader('¿Qué encontré?')
st.markdown(
    f'- En un año típico, una estación registra unos **{mediana_pm:.0f} µg/m³** de partículas finas: **por debajo de la norma '
    f'colombiana (25)**, pero **unas {mediana_pm / GUIA_OMS:.0f} veces por encima de lo que recomienda la OMS (5)**.\n'
    f'- Aproximadamente **{pct_excede:.0f} %** de las mediciones (cerca de 1 de cada 10) supera la norma colombiana; '
    'casi ninguna cumple la recomendación de la OMS.\n'
    '- Las zonas con más contaminación son **Antioquia (Valle de Aburrá) y Bogotá**, sobre todo cerca de vías con mucho tráfico.\n'
    '- Desde 2016 la contaminación por partículas **tiende a bajar**, aunque la red de medición también creció.')

st.subheader('¿Qué significa?')
st.write('Cumplir la norma del país no significa que el aire sea seguro según los estándares de salud más '
         'exigentes. Además, las partículas finas (PM2.5) y el dióxido de nitrógeno (NO₂), un gas que sale sobre todo de '
         'los tubos de escape, tienden a subir y bajar al mismo tiempo: donde hay más NO₂ casi siempre hay más partículas. '
         'La relación es moderada, no perfecta. Esto sugiere que el **tráfico** podría ser una fuente común de ambos, pero '
         'estos datos no demuestran que uno cause al otro ni que reducir uno reduzca automáticamente el otro. '
         'Por último, la baja de los últimos años es alentadora, pero no podemos asegurar que sea una mejora real: hoy se '
         'mide en muchos más lugares que en 2011.')

st.subheader('¿Qué se recomendaría?')
st.markdown(
    '1. **Priorizar** las acciones de control de tráfico en el Valle de Aburrá y Bogotá, donde están los valores más altos.\n'
    '2. **Ampliar la medición** en regiones casi sin cobertura (Orinoquía, Amazonía y Pacífico) y usar estaciones '
    'permanentes en lugar de campañas cortas, que dan cifras poco confiables.\n'
    '3. **Corregir los errores** de la base de datos (valores imposibles y municipios mal asignados) antes de usarla para decidir.\n'
    '4. **Evaluar la meta de la OMS** como objetivo de largo plazo, no solo la norma nacional.')

g1, g2 = st.columns(2)
with g1:
    conteo = pm25['Categoría'].value_counts().reindex(CATEGORIAS)
    fig, ax = plt.subplots(figsize=(6, 4))
    ax.bar(conteo.index, conteo.values / conteo.sum() * 100, color=['#74c476', '#fed976', '#fd8d3c', '#e31a1c'])
    ax.set(title='¿Qué tan limpio es el aire donde se mide?', xlabel='Nivel de partículas finas (µg/m³)',
           ylabel='% de las mediciones')
    ax.tick_params(axis='x', labelsize=8)
    mostrar(fig)
with g2:
    anual = pm25.groupby('Año')['Promedio'].median()
    fig, ax = plt.subplots(figsize=(6, 4))
    ax.plot(anual.index, anual.values, marker='o', color='#1f77b4', label='Nivel típico')
    ax.axhline(NORMA_COLOMBIA, color='black', ls='--', label='Norma de Colombia')
    ax.axhline(GUIA_OMS, color='green', ls=':', label='Recomendación OMS')
    ax.set(title='El aire ha mejorado desde 2016', xlabel='Año', ylabel='Partículas finas (µg/m³)', ylim=(0, 30))
    ax.legend(fontsize=8)
    mostrar(fig)

st.divider()
st.caption('Fuente: IDEAM – datos.gov.co. Código y documentación en el repositorio de GitHub del proyecto.')

