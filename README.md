# Sistema contable Hot Dogs

Aplicacion Streamlit para registrar carritos, ventas, gastos, clientes, facturas,
inventario, reportes, predicciones y un asistente IA opcional con Groq.

La app ahora puede trabajar con PostgreSQL o con MariaDB/MySQL. Para despliegues
en la nube se recomienda PostgreSQL.

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

### Opcion recomendada: PostgreSQL

1. Crea la base `perrospacho` en tu servidor PostgreSQL.
2. Ejecuta el esquema:

```powershell
psql -U postgres -d perrospacho -f docs\schema_postgresql.sql
```

3. Configura `.env` con una de estas opciones:

```text
DATABASE_URL=postgresql://usuario:password@host:5432/perrospacho
```

o por componentes:

```text
POSTGRES_HOST=
POSTGRES_PORT=5432
POSTGRES_USER=postgres
POSTGRES_PASSWORD=
POSTGRES_DB=perrospacho
```

### Compatibilidad: MariaDB / MySQL

Si prefieres seguir con MariaDB/MySQL local, crea la base y tablas con:

```powershell
mysql -u root -p < docs\schema_mariadb.sql
```

Luego configura `.env` usando `.env.example` como referencia.

### Migrar la base local antigua

Si tenias datos en la base SQLite local `accounting.db`, puedes pasarlos al
esquema nuevo de PostgreSQL o MariaDB/MySQL con:

```powershell
python tools\migrar_sqlite_a_mariadb.py
```

Ese script:

- crea las tablas del esquema actual si faltan
- migra el usuario local existente
- recrea carritos, cuentas, ventas, gastos, clientes y facturas
- deja la base alineada con la version actual de la app

Valores por defecto si no defines variables:

- PostgreSQL por componentes: puerto `5432`, usuario `postgres`
- MariaDB/MySQL por componentes: host `127.0.0.1`, puerto `3307`, usuario `root`
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

## Despliegue sugerido

Para la web en la nube, lo mas simple hoy es:

- web en Render
- base en PostgreSQL

Variables minimas del servicio web:

```text
DATABASE_URL=postgresql://usuario:password@host:5432/perrospacho
GROQ_API_KEY=
```

El proyecto ya incluye un `Procfile` con este arranque:

```text
streamlit run app.py --server.address 0.0.0.0 --server.port $PORT
```
