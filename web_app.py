from datetime import date, datetime
import io
import zipfile
import os

import streamlit as st

from SPREADS import compute_spreads

st.set_page_config(page_title="Spreads eléctricos", layout="wide")

st.markdown(
    """
    <style>
    * {font-family: 'Calibri', sans-serif;}
    </style>
    """,
    unsafe_allow_html=True,
)

st.title("Calculadora de Spreads de Precios Eléctricos")

with st.form("spread_form"):
    api_token = st.text_input("Token ESIOS API", type="password")
    col1, col2, col3 = st.columns(3)
    start_date = col1.date_input("Fecha de inicio", value=date.today())
    end_date = col2.date_input("Fecha de fin", value=date.today())
    horas = col3.number_input("Horas", min_value=1, max_value=24, value=6)
    submitted = st.form_submit_button("Calcular")

if submitted:
    if api_token:
        os.environ["TOKEN"] = api_token
    try:
        daily_spread, monthly_spread, fig_daily, fig_monthly = compute_spreads(
            datetime.combine(start_date, datetime.min.time()),
            datetime.combine(end_date, datetime.min.time()),
            int(horas),
        )
        st.subheader("Spread diario")
        st.plotly_chart(fig_daily, use_container_width=True)

        st.subheader("Spread mensual")
        st.plotly_chart(fig_monthly, use_container_width=True)

        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, "w") as zf:
            zf.writestr("daily_spread.csv", daily_spread.to_csv(index=False))
            zf.writestr("monthly_spread.csv", monthly_spread.to_csv(index=False))
        buffer.seek(0)
        st.download_button(
            "Descargar resultados",
            data=buffer,
            file_name="spreads.zip",
            mime="application/zip",
        )
    except EnvironmentError as err:
        st.error(str(err))
    except Exception as exc:
        st.error(f"Ocurrió un error: {exc}")
