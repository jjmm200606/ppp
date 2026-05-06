# Sistema contable Hot Dogs

Aplicacion Streamlit para registrar carritos, ventas, gastos, clientes, facturas,
inventario, reportes, predicciones y un asistente IA opcional con Groq.

## Requisitos

- Python 3.11+
- MariaDB o MySQL
- Dependencias de `requirements.txt`

## Instalacion

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

## Base de datos

1. Crea la base y tablas con:

```powershell
mysql -u root -p < docs\schema_mariadb.sql
```

2. Crea un archivo `.env` usando `.env.example` como referencia.
   La app lee automaticamente `MARIADB_HOST`, `MARIADB_PORT`, `MARIADB_USER`,
   `MARIADB_PASSWORD` y `MARIADB_DB`.

Valores por defecto si no defines variables:

- Host: `127.0.0.1`
- Puerto: `3307`
- Usuario: `root`
- Base: `perrospacho`

## Asistente IA

El asistente usa Groq de forma opcional. Configura:

```toml
GROQ_API_KEY = "gsk_..."
```

en `.streamlit/secrets.toml`.

Para entrenarlo con conocimiento del negocio, entra a la pagina
`Entrenar chatbot` dentro de la app. Lo que guardes alli queda en
`knowledge_base` y se inyecta como contexto en cada respuesta.

## Ejecutar

```powershell
python -m streamlit run app.py
```

Luego crea una cuenta desde la pantalla inicial. El usuario `admin` abre el
panel de administracion global.
