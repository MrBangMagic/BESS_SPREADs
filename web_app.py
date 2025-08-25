import io
from datetime import date, datetime

import pandas as pd
import streamlit as st

from SPREADS import compute_spreads

st.set_page_config(page_title="Spreads Mercado Eléctrico", layout="wide")

st.markdown(
    """
    <style>
    * {
        font-family: 'Calibri', sans-serif;
    }
    .stButton>button {
        background-color: #1f77b4;
        color: white;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

st.title("Análisis de Spreads del Mercado Eléctrico")

st.caption(
    "Define la variable de entorno ESIOS_API_TOKEN antes de ejecutar la aplicación."
)

start_date = st.date_input("Fecha de inicio", value=date(2025, 1, 1))
end_date = st.date_input("Fecha de fin", value=date(2025, 1, 2))
horas = st.number_input(
    "Horas baratas/caras", min_value=1, max_value=12, value=6, step=1
)

if st.button("Calcular"):
    with st.spinner("Descargando datos..."):
        daily_spread, monthly_spread, fig_daily, fig_monthly = compute_spreads(
            datetime.combine(start_date, datetime.min.time()),
            datetime.combine(end_date, datetime.min.time()),
            int(horas),
        )
    st.plotly_chart(fig_daily, use_container_width=True)
    st.plotly_chart(fig_monthly, use_container_width=True)

    output = io.BytesIO()
    with pd.ExcelWriter(output, engine="xlsxwriter") as writer:
        daily_spread.to_excel(writer, index=False, sheet_name="daily")
        monthly_spread.to_excel(writer, index=False, sheet_name="monthly")
    st.download_button(
        "Descargar resultados",
        data=output.getvalue(),
        file_name="spreads.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )
