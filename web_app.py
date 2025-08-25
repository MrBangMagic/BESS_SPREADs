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
        background: radial-gradient(circle at center, #0f0f0f 0%, #000000 100%);
        color: #e0ffff;
    }
    h1, h2, h3, h4, h5, h6 {
        color: #39e5ff;
        text-shadow: 0 0 10px #39e5ff;
    }
    .stButton>button {
        background: linear-gradient(135deg, #00ffcc, #0099ff);
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
    "BESSpread es una herramienta que calcula el spread diario, y el spread medio mensual. "
    "El cálculo se basa en curvas Spot de ESIOS (https://api.esios.ree.es/indicators/600). Permite descargar los resultados en formato Excel."
)

with st.form("spread_form"):
    col1, col2, col3 = st.columns(3)
    start_date = col1.date_input("Fecha de inicio", value=date.today())
    end_date = col2.date_input("Fecha de fin", value=date.today())
    horas = col3.number_input("Horas", min_value=1, max_value=24, value=6)
    submitted = st.form_submit_button("Calcular")

if submitted:
    try:
        (
            daily_stats,
            monthly_stats,
            fig_daily,
            fig_monthly,
        ) = compute_spreads(
            datetime.combine(start_date, datetime.min.time()),
            datetime.combine(end_date, datetime.min.time()),
            int(horas),
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
            "Volatilidad: desviación estándar de los precios horarios como indicador de riesgo."
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
