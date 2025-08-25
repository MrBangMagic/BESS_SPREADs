from datetime import date, datetime
import io
import zipfile
from pathlib import Path

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

image_dir = Path(__file__).parent / "images"
st.image(image_dir / "a.png")
st.title("Calculadora de Spreads de Precios Eléctricos")

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
            daily_country_diff,
            monthly_country_diff,
            fig_daily,
            fig_monthly,
            fig_country_diff,
        ) = compute_spreads(
            datetime.combine(start_date, datetime.min.time()),
            datetime.combine(end_date, datetime.min.time()),
            int(horas),
        )

        col_img1, col_text1 = st.columns([1, 8])
        col_img1.image(image_dir / "b.png", width=40)
        col_text1.subheader("Spread diario")
        st.plotly_chart(fig_daily, use_container_width=True)

        col_img2, col_text2 = st.columns([1, 8])
        col_img2.image(image_dir / "c.png", width=40)
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

        st.subheader("Diferencia diaria de precios entre países")
        st.plotly_chart(fig_country_diff, use_container_width=True)

        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, "w") as zf:
            zf.writestr("daily_stats.csv", daily_stats.to_csv(index=False))
            zf.writestr("monthly_stats.csv", monthly_stats.to_csv(index=False))
            zf.writestr(
                "daily_country_diff.csv", daily_country_diff.to_csv(index=False)
            )
            zf.writestr(
                "monthly_country_diff.csv", monthly_country_diff.to_csv(index=False)
            )
        buffer.seek(0)
        st.download_button(
            "Descargar resultados",
            data=buffer,
            file_name="spreads.zip",
            mime="application/zip",
        )
    except Exception as exc:
        st.error(f"Ocurrió un error: {exc}")
