"""Interfaz Streamlit para explorar la cadena de Markov por producto.

Lee el CSV que genera notebooks/markov_01.ipynb. Corre solo en local:

    uv run streamlit run app/markov_app.py

La ruta del CSV se puede cambiar con la variable de entorno MARKOV_CSV.
"""

import io
import os
from pathlib import Path

import numpy as np
import pandas as pd
import plotly.express as px
import streamlit as st

RAIZ = Path(__file__).resolve().parents[1]
CSV_DEFECTO = RAIZ / 'data' / 'processed' / 'markov_transiciones_sku.csv'

ESTADOS = ['Verde', 'Ámbar', 'Rojo', 'FULCOM futura', 'Sin fecha', 'Baja']
COLORES = {'Verde': '#2e9e5b', 'Ámbar': '#e0a100', 'Rojo': '#c8312b',
           'FULCOM futura': '#6b7fd7', 'Sin fecha': '#9a9a9a', 'Baja': '#5a5a5a'}
ATRIBUTOS = ['CODIGO', 'DESCRIPTOR', 'LINEA', 'NOMBRE LINEA', 'POLITICA CJE AL 30SEP',
             'estado_actual', 'valorizacion_actual', 'n_meses_observados', 'periodo_inicio', 'periodo_fin']
# Siguiente estado de alerta (más grave) para el ranking de riesgo; Rojo y Baja no tienen uno peor
SIGUIENTE = {'Verde': 'Ámbar', 'Ámbar': 'Rojo'}
FILTROS = {'NOMBRE LINEA': 'Línea', 'POLITICA CJE AL 30SEP': 'Política de canje', 'estado_actual': 'Estado actual'}


def clp(valor: float) -> str:
    return f'${valor:,.0f}'


@st.cache_data(show_spinner='Cargando transiciones...')
def cargar(fuente: str | bytes) -> pd.DataFrame:
    origen = io.BytesIO(fuente) if isinstance(fuente, bytes) else fuente
    df = pd.read_csv(origen, encoding='utf-8-sig', dtype={'CODIGO': str, 'LINEA': str})
    for col in ['estado_origen', 'estado_destino']:
        df[col] = pd.Categorical(df[col], categories=ESTADOS)
    return df.sort_values(['CODIGO', 'estado_origen', 'estado_destino']).reset_index(drop=True)


def matriz(df: pd.DataFrame, columna: str, normalizar: bool = False) -> pd.DataFrame:
    m = (df.groupby(['estado_origen', 'estado_destino'], observed=False)[columna].sum()
           .unstack().reindex(index=ESTADOS, columns=ESTADOS).fillna(0))
    if normalizar:
        m = m.div(m.sum(axis=1).replace(0, np.nan), axis=0)
    return m


def proyectar(P: pd.DataFrame, estado: str, h: int) -> pd.Series:
    inicial = np.array([1.0 if e == estado else 0.0 for e in ESTADOS])
    return pd.Series(inicial @ np.linalg.matrix_power(P.to_numpy(), h), index=ESTADOS)


def heatmap(m: pd.DataFrame, titulo: str):
    fig = px.imshow(m, text_auto='.2f', color_continuous_scale='Reds', zmin=0, zmax=1, aspect='auto',
                    labels={'x': 'Estado en t + 1', 'y': 'Estado en t', 'color': 'Probabilidad'})
    fig.update_layout(title=titulo, margin={'l': 10, 'r': 10, 't': 50, 'b': 10})
    return fig


# --------------------------------------------------------------------------- Carga
st.set_page_config(page_title='Markov por producto', page_icon='📦', layout='wide')
st.title('Cadena de Markov por producto: alertas de antigüedad')

ruta = Path(os.environ.get('MARKOV_CSV', CSV_DEFECTO))
if ruta.exists():
    datos = cargar(str(ruta))
else:
    st.warning(f'No se encontró `{ruta}`. Ejecuta primero `notebooks/markov_01.ipynb`, '
               'o sube el CSV aquí (se procesa en memoria, no se guarda).')
    archivo = st.file_uploader('markov_transiciones_sku.csv', type='csv')
    if archivo is None:
        st.stop()
    datos = cargar(archivo.getvalue())

skus = datos.drop_duplicates('CODIGO')[ATRIBUTOS].set_index('CODIGO')

# --------------------------------------------------------------------------- Filtros
with st.sidebar:
    st.header('Filtros')
    mascara = pd.Series(True, index=skus.index)
    for col, etiqueta in FILTROS.items():
        opciones = sorted(skus[col].dropna().astype(str).unique(),
                          key=lambda x: ESTADOS.index(x) if x in ESTADOS else x)
        elegidas = st.multiselect(etiqueta, opciones)
        if elegidas:
            mascara &= skus[col].astype(str).isin(elegidas)
    st.caption(f'{mascara.sum():,} de {len(skus):,} SKU')

skus_f = skus[mascara]
datos_f = datos[datos['CODIGO'].isin(skus_f.index)]

if skus_f.empty:
    st.info('Ningún SKU cumple los filtros.')
    st.stop()

tab_agregada, tab_producto, tab_riesgo = st.tabs(['Matriz agregada', 'Por producto', 'Ranking de riesgo'])

# --------------------------------------------------------------------------- Matriz agregada
with tab_agregada:
    conteos = matriz(datos_f, 'conteo')
    c1, c2, c3 = st.columns(3)
    c1.metric('SKU', f'{len(skus_f):,}')
    c2.metric('Transiciones observadas', f'{int(conteos.to_numpy().sum()):,}')
    c3.metric('Valorización actual', clp(skus_f['valorizacion_actual'].sum()))

    st.plotly_chart(heatmap(matriz(datos_f, 'conteo', normalizar=True),
                            'Probabilidad de transición del segmento (MLE)'), width='stretch')
    st.caption('Suma de las transiciones observadas de los SKU filtrados, normalizada por fila. '
               'Las filas vacías no tienen observaciones.')
    with st.expander('Conteos'):
        st.dataframe(conteos.astype(int), width='stretch')

    st.subheader('Estado actual del segmento')
    resumen = (skus_f.groupby('estado_actual')
                     .agg(SKU=('DESCRIPTOR', 'size'), valorizacion=('valorizacion_actual', 'sum'))
                     .reindex(ESTADOS).dropna(how='all').fillna(0))
    fig = px.bar(resumen.reset_index(), x='estado_actual', y='valorizacion', text='SKU', color='estado_actual',
                 color_discrete_map=COLORES, labels={'estado_actual': '', 'valorizacion': 'Valorización (CLP)'})
    fig.update_layout(showlegend=False, margin={'l': 10, 'r': 10, 't': 10, 'b': 10})
    st.plotly_chart(fig, width='stretch')

# --------------------------------------------------------------------------- Por producto
with tab_producto:
    codigo = st.selectbox('SKU', skus_f.index,
                          format_func=lambda c: f'{c} · {skus_f.at[c, "DESCRIPTOR"]}')
    ficha = skus_f.loc[codigo]
    datos_sku = datos_f[datos_f['CODIGO'] == codigo]

    c1, c2, c3, c4 = st.columns(4)
    c1.metric('Estado actual', ficha['estado_actual'])
    c2.metric('Valorización actual', clp(ficha['valorizacion_actual']))
    c3.metric('Meses observados', int(ficha['n_meses_observados']))
    c4.metric('Línea / política', f'{ficha["NOMBRE LINEA"]} · {ficha["POLITICA CJE AL 30SEP"]}')
    st.caption(f'Periodo: {ficha["periodo_inicio"]} a {ficha["periodo_fin"]}')

    P = matriz(datos_sku, 'prob_suavizada')
    izq, der = st.columns([3, 2])
    with izq:
        st.plotly_chart(heatmap(P, 'Matriz suavizada del producto'), width='stretch')
        with st.expander('Conteos propios del SKU'):
            st.dataframe(matriz(datos_sku, 'conteo').astype(int), width='stretch')
        st.caption('Suavizado Dirichlet hacia la matriz global: con pocas observaciones propias, '
                   'la fila se parece a la global.')
    with der:
        h = st.slider('Horizonte (meses)', 1, 6, 1)
        dist = proyectar(P, ficha['estado_actual'], h)
        st.metric(f'P(Rojo) en {h} mes(es)', f'{dist["Rojo"]:.1%}')
        fig = px.bar(dist.rename_axis('estado').rename('probabilidad').reset_index(), x='estado', y='probabilidad',
                     color='estado', color_discrete_map=COLORES, text_auto='.1%',
                     labels={'estado': '', 'probabilidad': 'Probabilidad'})
        fig.update_layout(showlegend=False, yaxis_tickformat='.0%', yaxis_range=[0, 1],
                          title=f'Distribución proyectada desde «{ficha["estado_actual"]}»',
                          margin={'l': 10, 'r': 10, 't': 50, 'b': 10})
        st.plotly_chart(fig, width='stretch')

# --------------------------------------------------------------------------- Ranking de riesgo
with tab_riesgo:
    st.markdown('**Valor en riesgo** = P(pasar al siguiente estado de alerta el próximo mes) × valorización actual. '
                'El siguiente estado depende del estado actual de cada SKU: Verde → Ámbar, Ámbar → Rojo.')
    st.caption('Rojo y Baja no tienen un estado de alerta peor, así que no tienen probabilidad. '
               'Para comparar riesgos del mismo nivel, filtra por estado actual.')
    incluir = st.checkbox('Incluir SKU que ya están en Rojo o Baja', value=False)

    ranking = skus_f.assign(estado_siguiente=skus_f['estado_actual'].map(SIGUIENTE))
    paso = datos_f[(datos_f['estado_origen'].astype(str) == datos_f['CODIGO'].map(ranking['estado_actual']))
                   & (datos_f['estado_destino'].astype(str) == datos_f['CODIGO'].map(ranking['estado_siguiente']))]
    ranking = ranking.join(paso.set_index('CODIGO')['prob_suavizada'].rename('p_empeora_1m'))
    ranking['valor_en_riesgo'] = ranking['p_empeora_1m'] * ranking['valorizacion_actual']
    if not incluir:
        ranking = ranking[~ranking['estado_actual'].isin(['Rojo', 'Baja'])]
    ranking = ranking.sort_values('valor_en_riesgo', ascending=False)

    c1, c2 = st.columns(2)
    c1.metric('Valor en riesgo total', clp(ranking['valor_en_riesgo'].sum()))
    c2.metric('SKU con P(empeorar) ≥ 50 %', f'{(ranking["p_empeora_1m"] >= 0.5).sum():,}')

    top = st.slider('Mostrar top', 10, 200, 25, step=5)
    columnas = ['DESCRIPTOR', 'NOMBRE LINEA', 'POLITICA CJE AL 30SEP', 'estado_actual', 'estado_siguiente',
                'p_empeora_1m', 'valorizacion_actual', 'valor_en_riesgo']
    st.dataframe(
        ranking[columnas].head(top), width='stretch',
        column_config={
            'estado_actual': st.column_config.TextColumn('Estado actual'),
            'estado_siguiente': st.column_config.TextColumn('Pasa a'),
            'p_empeora_1m': st.column_config.ProgressColumn('P(pasar al siguiente) 1 mes', format='percent',
                                                            min_value=0, max_value=1),
            'valorizacion_actual': st.column_config.NumberColumn('Valorización', format='$%,.0f'),
            'valor_en_riesgo': st.column_config.NumberColumn('Valor en riesgo', format='$%,.0f'),
        })
    st.download_button('Descargar ranking (CSV)', ranking[columnas].to_csv().encode('utf-8-sig'),
                       file_name='ranking_riesgo_markov.csv', mime='text/csv')
