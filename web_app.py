from datetime import date, datetime
import io
from pathlib import Path

import pandas as pd
import streamlit as st

from SPREADS import compute_spreads

st.set_page_config(
    page_title="BESSpread",
    layout="wide",
    page_icon=str(Path(__file__).parent / "images" / "logo.png"),
)

st.markdown(
    """
    <style>
    * {font-family: 'Calibri', sans-serif;}
    .stApp {
        background: linear-gradient(135deg, #D4EDDA, #C3E6CB);
        color: #333333;
    }
    h1, h2, h3, h4, h5, h6 {
        color: #39e5ff;
        text-shadow: 0 0 10px #39e5ff;
    }
    .stButton>button {
        background: linear-gradient(135deg, #8EC6C5, #A9E5D0);
        color: #000000;
        border: none;
        border-radius: 8px;
        font-weight: bold;
    }
    .stButton>button:hover {
        box-shadow: 0 0 12px #00ffcc;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

st.image(Path(__file__).parent / "images" / "logo.png", width=200)
st.title("BESSpread")
st.write(
    "BESSpread es una herramienta que calcula el spread diario y el spread medio mensual. "
    "Los datos se obtienen en tiempo real desde la API de ESIOS (https://api.esios.ree.es/indicators/600). "
    "Permite descargar los resultados en formato Excel."
)
st.markdown(
    "[Cómo usar la aplicación](#como-usar-la-aplicacion)", unsafe_allow_html=True
)

st.markdown("""### Cómo usar la aplicación
1. Selecciona el rango de fechas que deseas analizar.
2. Introduce el número de horas de almacenamiento.
3. Pulsa **Calcular** para obtener los datos de la API y generar los resultados.
""")

with st.form("spread_form"):
    col1, col2, col3 = st.columns(3)
    start_date = col1.date_input(
        "Fecha de inicio",
        value=date.today(),
        help="Fecha inicial del análisis (AAAA-MM-DD)",
    )
    end_date = col2.date_input(
        "Fecha de fin",
        value=date.today(),
        help="Fecha final del análisis (AAAA-MM-DD)",
    )
    horas = col3.number_input(
        "Horas",
        min_value=1,
        max_value=24,
        value=6,
        help="Horas de almacenamiento (1-24)",
    )

    errors = False
    if start_date > end_date:
        st.error("La fecha inicial debe ser anterior o igual a la final.")
        errors = True
    if not (1 <= horas <= 24):
        st.error("Las horas deben estar entre 1 y 24.")
        errors = True

    submitted = st.form_submit_button("Calcular", disabled=errors)

if submitted:
    try:
        with st.spinner("Obteniendo datos de la API de ESIOS y calculando spreads..."):
            (
                daily_stats,
                monthly_stats,
                fig_daily,
                fig_monthly,
            ) = compute_spreads(
                datetime.combine(start_date, datetime.min.time()),
                datetime.combine(end_date, datetime.min.time()),
                int(horas),
                None,  # None para obtener datos desde la API
            )

        col_img1, col_text1 = st.columns([1, 8])
        col_img1.image(Path(__file__).parent / "images" / "b.png", width=40)
        col_text1.subheader("Spread diario")
        st.plotly_chart(fig_daily, use_container_width=True)

        col_img2, col_text2 = st.columns([1, 8])
        col_img2.image(Path(__file__).parent / "images" / "c.png", width=40)
        col_text2.subheader("Spread mensual")
        st.plotly_chart(fig_monthly, use_container_width=True)

        st.subheader("Precio medio y volatilidad")
        metrics_cols = st.columns(len(monthly_stats["geo_name"].unique()))
        for col, geo in zip(metrics_cols, monthly_stats["geo_name"].unique()):
            data_geo = monthly_stats[monthly_stats["geo_name"] == geo]
            avg_price = data_geo["price_avg"].mean()
            vol = data_geo["volatility"].mean()
            col.metric(f"{geo} precio medio", f"{avg_price:.2f} €/MWh")
            col.metric(f"{geo} volatilidad", f"{vol:.2f} €/MWh")
        st.caption(
            "Precio medio: media simple de los precios horarios filtrados por día/mes. "
            "Volatilidad: desviación estándar de los precios horarios como indicador de riesgo.",
        )

        daily_buffer = io.BytesIO()
        with pd.ExcelWriter(daily_buffer, engine="openpyxl") as writer:
            daily_stats.to_excel(writer, index=False)
        daily_buffer.seek(0)

        monthly_buffer = io.BytesIO()
        with pd.ExcelWriter(monthly_buffer, engine="openpyxl") as writer:
            monthly_stats.to_excel(writer, index=False)
        monthly_buffer.seek(0)

        st.download_button(
            "Descargar Spread Diario",
            data=daily_buffer,
            file_name="spread_diario.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )

        st.download_button(
            "Descargar Spread Mensual",
            data=monthly_buffer,
            file_name="spread_mensual.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
    except Exception as exc:
        st.error(f"Ocurrió un error: {exc}")
