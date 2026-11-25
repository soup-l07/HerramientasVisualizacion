# NASA NeoWs Dashboard

Dashboard interactivo en Streamlit para explorar asteroides cercanos a la Tierra mediante NASA Open APIs — NeoWs.

## Funciones
- Consulta por fechas (maximo 7 dias por solicitud).
- Filtro de asteroides potencialmente peligrosos.
- Indicadores de cantidad, peligrosidad, diametro y velocidad.
- Graficas de aproximaciones por dia, distribucion de diametros y relacion velocidad-distancia.
- Tabla de datos y descarga CSV.

## Instalacion
```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

Solicita una API key en https://api.nasa.gov/ y crea `.streamlit/secrets.toml`:
```toml
NASA_API_KEY = "TU_API_KEY"
```
No subas `secrets.toml` a GitHub. Esta excluido por `.gitignore`. Si no se configura una clave, la app usa `DEMO_KEY`, que tiene limites de uso.

## Ejecutar
```bash
streamlit run app.py
```

Fuente: https://api.nasa.gov/ — Asteroids NeoWs.
