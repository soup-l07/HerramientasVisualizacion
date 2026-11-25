import os
from datetime import date, timedelta

import pandas as pd
import plotly.express as px
import requests
import streamlit as st

st.set_page_config(page_title="NASA NeoWs", page_icon="☄️", layout="wide")
API_URL = "https://api.nasa.gov/neo/rest/v1/feed"

api_key = os.getenv("NASA_API_KEY", "")
try:
    api_key = api_key or st.secrets.get("NASA_API_KEY", "")
except Exception:
    pass
api_key = api_key or "DEMO_KEY"

st.title("☄️ Explorador de asteroides cercanos a la Tierra")
st.caption("Dashboard interactivo con NASA Open APIs — Near Earth Object Web Service (NeoWs).")
st.info("NeoWs Feed permite consultar periodos de hasta 7 días por solicitud.")

@st.cache_data(ttl=1800, show_spinner=False)
def consultar(inicio, fin, key):
    response = requests.get(
        API_URL,
        params={"start_date": inicio, "end_date": fin, "api_key": key},
        timeout=30,
    )
    if response.status_code == 403:
        raise RuntimeError("NASA rechazo la solicitud. Revisa tu API key.")
    if response.status_code == 429:
        raise RuntimeError("Se alcanzo el limite de solicitudes. Espera o usa tu propia API key.")
    response.raise_for_status()
    payload = response.json()
    rows = []
    for fecha, objetos in payload.get("near_earth_objects", {}).items():
        for obj in objetos:
            approach = (obj.get("close_approach_data") or [{}])[0]
            meters = obj.get("estimated_diameter", {}).get("meters", {})
            v = approach.get("relative_velocity", {})
            d = approach.get("miss_distance", {})
            dmin, dmax = meters.get("estimated_diameter_min"), meters.get("estimated_diameter_max")
            rows.append({
                "id": obj.get("id"),
                "nombre": obj.get("name", "Sin nombre"),
                "fecha": approach.get("close_approach_date", fecha),
                "diametro_min_m": dmin,
                "diametro_max_m": dmax,
                "diametro_promedio_m": (dmin + dmax) / 2 if dmin is not None and dmax is not None else None,
                "velocidad_kmh": pd.to_numeric(v.get("kilometers_per_hour"), errors="coerce"),
                "distancia_km": pd.to_numeric(d.get("kilometers"), errors="coerce"),
                "potencialmente_peligroso": bool(obj.get("is_potentially_hazardous_asteroid", False)),
                "orbita": approach.get("orbiting_body", "No disponible"),
                "url_nasa": obj.get("nasa_jpl_url", ""),
            })
    df = pd.DataFrame(rows)
    if not df.empty:
        df["fecha"] = pd.to_datetime(df["fecha"], errors="coerce")
        df = df.drop_duplicates(subset=["id", "fecha"])
    return df, payload.get("element_count", len(df))

with st.sidebar:
    st.header("Filtros de consulta")
    hoy = date.today()
    inicio = st.date_input("Fecha inicial", value=hoy - timedelta(days=6), max_value=hoy + timedelta(days=7))
    fin = st.date_input("Fecha final", value=hoy, max_value=hoy + timedelta(days=7))
    solo_peligrosos = st.checkbox("Solo potencialmente peligrosos", value=False)
    st.caption("Fuente: NASA Open APIs · NeoWs")

if inicio > fin:
    st.error("La fecha inicial debe ser anterior o igual a la fecha final.")
    st.stop()
if (fin - inicio).days > 6:
    st.error("Selecciona un intervalo de máximo 7 días, contando ambas fechas.")
    st.stop()

try:
    with st.spinner("Consultando asteroides en NASA NeoWs..."):
        df, total_api = consultar(inicio.isoformat(), fin.isoformat(), api_key)
except requests.exceptions.Timeout:
    st.error("La solicitud a NASA tardo demasiado. Intenta nuevamente.")
    st.stop()
except requests.exceptions.RequestException as e:
    st.error(f"No fue posible consultar NASA: {e}")
    st.stop()
except (RuntimeError, ValueError) as e:
    st.error(str(e))
    st.stop()

if df.empty:
    st.warning("La API no devolvio asteroides para el periodo seleccionado.")
    st.stop()

vista = df[df["potencialmente_peligroso"]] if solo_peligrosos else df.copy()
if vista.empty:
    st.warning("No hay asteroides que coincidan con el filtro.")
    st.stop()

st.subheader("Resumen del periodo")
c1, c2, c3, c4 = st.columns(4)
c1.metric("Asteroides detectados", f"{len(vista):,}")
c2.metric("Potencialmente peligrosos", f"{int(vista['potencialmente_peligroso'].sum()):,}")
diam = vista["diametro_max_m"].max()
vel = vista["velocidad_kmh"].max()
c3.metric("Mayor diametro estimado", f"{diam:,.2f} m" if pd.notna(diam) else "N/D")
c4.metric("Mayor velocidad", f"{vel:,.0f} km/h" if pd.notna(vel) else "N/D")
st.caption(f"Periodo: {inicio:%d/%m/%Y} al {fin:%d/%m/%Y} · Elementos reportados por la API: {total_api}")
st.divider()

left, right = st.columns(2)
with left:
    st.subheader("Asteroides por fecha")
    por_fecha = vista.groupby("fecha", as_index=False).size().rename(columns={"size": "cantidad"})
    fig = px.bar(por_fecha, x="fecha", y="cantidad", labels={"fecha": "Fecha", "cantidad": "Cantidad"})
    st.plotly_chart(fig, use_container_width=True)
with right:
    st.subheader("Distribucion de diametros")
    diametros = vista.dropna(subset=["diametro_promedio_m"])
    fig = px.histogram(diametros, x="diametro_promedio_m", nbins=20,
                       labels={"diametro_promedio_m": "Diametro promedio estimado (m)"})
    st.plotly_chart(fig, use_container_width=True)

st.subheader("Velocidad y distancia de aproximacion")
scatter = vista.dropna(subset=["velocidad_kmh", "distancia_km"])
if not scatter.empty:
    fig = px.scatter(
        scatter, x="distancia_km", y="velocidad_kmh", size="diametro_promedio_m",
        color="potencialmente_peligroso", hover_name="nombre",
        hover_data=["fecha", "diametro_promedio_m"],
        labels={"distancia_km": "Distancia (km)", "velocidad_kmh": "Velocidad (km/h)",
                "potencialmente_peligroso": "Potencialmente peligroso"},
    )
    st.plotly_chart(fig, use_container_width=True)
else:
    st.info("No hay datos suficientes para esta grafica.")

st.subheader("Detalle de asteroides")
cols = ["nombre", "fecha", "diametro_min_m", "diametro_max_m", "velocidad_kmh",
        "distancia_km", "potencialmente_peligroso", "orbita"]
tabla = vista[cols].rename(columns={
    "nombre": "Asteroide", "fecha": "Fecha de aproximacion",
    "diametro_min_m": "Diametro minimo (m)", "diametro_max_m": "Diametro maximo (m)",
    "velocidad_kmh": "Velocidad (km/h)", "distancia_km": "Distancia (km)",
    "potencialmente_peligroso": "Potencialmente peligroso", "orbita": "Cuerpo orbital",
})
st.dataframe(tabla, use_container_width=True, hide_index=True)
st.download_button("Descargar datos CSV", vista.to_csv(index=False).encode("utf-8"),
                   file_name=f"nasa_neows_{inicio}_{fin}.csv", mime="text/csv")
st.caption("Fuente: NASA/JPL mediante NASA Open APIs — NeoWs.")
