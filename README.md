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

## Despliegue en Railway

Este proyecto queda bien en Railway usando:

- 1 servicio web para Streamlit
- 1 base de datos MySQL o MariaDB

### 1. Crear la base de datos

En Railway crea una base `MySQL` o `MariaDB`.

### 2. Variables de entorno

En el servicio web agrega estas variables:

```text
MARIADB_HOST=
MARIADB_PORT=
MARIADB_USER=
MARIADB_PASSWORD=
MARIADB_DB=
GROQ_API_KEY=
```

Notas:

- `GROQ_API_KEY` es opcional si no vas a usar el asistente IA.
- La app tambien acepta `GROQ_API_KEY` por variable de entorno, no solo por
  `.streamlit/secrets.toml`.

### 3. Comando de inicio

El proyecto ya incluye un `Procfile` con este arranque:

```text
streamlit run app.py --server.address 0.0.0.0 --server.port $PORT
```

### 4. Crear tablas

Antes de usar la app, ejecuta el script de esquema en tu base:

```sql
docs/schema_mariadb.sql
```

### 5. Desplegar desde GitHub

1. En Railway elige `Deploy from GitHub repo`
2. Selecciona este repositorio
3. Conecta la base al servicio
4. Configura las variables de entorno
5. Espera el primer deploy
