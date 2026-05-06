# Diagramas UML — Sistema Contable Hot Dogs

> **Cómo usar:** Copia el código entre `@startuml` y `@enduml` y pégalo en
> [plantuml.com/plantuml](https://www.plantuml.com/plantuml/uml),
> la extensión **PlantUML** de VS Code, o cualquier herramienta compatible.

---

## 1. Diagrama de Casos de Uso

### 1.1 Descripción textual

| # | Caso de uso | Actor(es) | Descripción |
|---|------------|-----------|-------------|
| CU-01 | Registrarse | Vendedor | El usuario crea una cuenta nueva con usuario y contraseña. |
| CU-02 | Iniciar sesión | Vendedor, Administrador | El usuario ingresa sus credenciales para acceder al sistema. |
| CU-03 | Cerrar sesión | Vendedor, Administrador | El usuario finaliza su sesión activa. |
| CU-04 | Gestionar carritos | Vendedor | Crear, activar/desactivar y consultar puntos de venta (carritos). |
| CU-05 | Registrar venta | Vendedor | Registrar la venta de productos con fecha, carrito, cantidad, precio y costo. |
| CU-06 | Eliminar venta | Vendedor | Eliminar un registro de venta existente. |
| CU-07 | Registrar gasto | Vendedor | Registrar un gasto operativo asociado a un carrito. |
| CU-08 | Ver panel de KPIs | Vendedor | Consultar resumen financiero: ingresos, costos, gastos, utilidad. |
| CU-09 | Ver reporte por carrito | Vendedor | Consultar análisis financiero detallado de un carrito en un rango de fechas. |
| CU-10 | Gestionar clientes | Vendedor | Crear y consultar el directorio de clientes. |
| CU-11 | Gestionar facturas | Vendedor | Crear facturas asociadas a clientes con ítems detallados. |
| CU-12 | Gestionar cuentas contables | Vendedor | Crear y consultar el catálogo de cuentas contables. |
| CU-13 | Gestionar inventario | Vendedor | Registrar productos, stock actual, stock mínimo y eliminar registros. |
| CU-14 | Consultar chatbot IA | Vendedor | Hacer preguntas al asistente IA que responde con datos financieros reales. |
| CU-15 | Ver predicciones ML | Vendedor | Consultar predicciones de ventas generadas por el modelo predictivo (CRISP-ML). |
| CU-16 | Ver panel de administración | Administrador | Ver KPIs globales, resumen de todos los usuarios y carritos de toda la plataforma. |
| CU-17 | Entrenar modelo predictivo | Sistema | El sistema entrena/recarga automáticamente el modelo ML al iniciar sesión si detecta datos nuevos. |
| CU-18 | Generar insights automáticos | Sistema | El sistema analiza ventas, gastos y tendencias para crear conocimiento para el chatbot. |
| CU-19 | Registrar auditoría | Sistema | El sistema registra cada evento (venta, gasto, factura, etc.) en la tabla audit_log vía el Observer. |

### 1.2 Código PlantUML

```plantuml
@startuml CasosDeUso
left to right direction
skinparam actorStyle awesome
skinparam packageStyle rectangle
skinparam shadowing false

actor "Vendedor" as V
actor "Administrador" as A
actor "Sistema" as S <<system>>

A -|> V : «hereda»

rectangle "Sistema Contable Hot Dogs" {

    ' ── Autenticación ─────────────────────
    package "Autenticación" {
        usecase "Registrarse"              as CU01
        usecase "Iniciar sesión"           as CU02
        usecase "Cerrar sesión"            as CU03
    }

    ' ── Gestión operativa ─────────────────
    package "Gestión Operativa" {
        usecase "Gestionar carritos"       as CU04
        usecase "Registrar venta"          as CU05
        usecase "Eliminar venta"           as CU06
        usecase "Registrar gasto"          as CU07
        usecase "Gestionar clientes"       as CU10
        usecase "Gestionar facturas"       as CU11
        usecase "Gestionar cuentas\ncontables" as CU12
        usecase "Gestionar inventario"     as CU13
    }

    ' ── Reportes y análisis ───────────────
    package "Reportes y Análisis" {
        usecase "Ver panel de KPIs"        as CU08
        usecase "Ver reporte\npor carrito" as CU09
        usecase "Consultar chatbot IA"     as CU14
        usecase "Ver predicciones ML"      as CU15
    }

    ' ── Administración ────────────────────
    package "Administración" {
        usecase "Ver panel de\nadministración" as CU16
    }

    ' ── Procesos automáticos ──────────────
    package "Procesos Automáticos" {
        usecase "Entrenar modelo\npredictivo"     as CU17
        usecase "Generar insights\nautomáticos"   as CU18
        usecase "Registrar auditoría"             as CU19
    }
}

' ── Relaciones Vendedor ───────────────────
V --> CU01
V --> CU02
V --> CU03
V --> CU04
V --> CU05
V --> CU06
V --> CU07
V --> CU08
V --> CU09
V --> CU10
V --> CU11
V --> CU12
V --> CU13
V --> CU14
V --> CU15

' ── Relaciones Administrador ──────────────
A --> CU16

' ── Relaciones Sistema ────────────────────
S --> CU17
S --> CU18
S --> CU19

' ── Relaciones entre casos de uso ─────────
CU05 ..> CU19 : «include»
CU07 ..> CU19 : «include»
CU11 ..> CU19 : «include»
CU02 ..> CU17 : «include»
CU02 ..> CU18 : «include»
CU15 ..> CU17 : «extend»
CU14 ..> CU18 : «extend»

@enduml
```

---

## 2. Diagrama de Clases

### 2.1 Descripción textual

| Clase / Módulo | Tipo | Responsabilidad |
|---|---|---|
| `AccountingFacade` | Clase (Patrón Facade) | Punto de entrada único para todas las operaciones del dominio. Filtra por `user_id` (multitenant). Métodos: CRUD de carritos, ventas, gastos, clientes, facturas, cuentas, inventario, KPIs, chatbot knowledge base, insights automáticos. Métodos admin sin filtro de usuario. |
| `Observer` | Protocolo (interfaz) | Define el contrato `update(event, payload)` para observadores. |
| `AuditObserver` | Clase | Implementa Observer. Inserta cada evento en la tabla `audit_log`. |
| `CacheObserver` | Clase | Implementa Observer. Limpia caches de Streamlit tras cada cambio. |
| `EmailObserver` | Clase | Implementa Observer. Envía correo SMTP opcional al ocurrir un evento. |
| `Event` | Clase (constantes) | Define los nombres de eventos soportados: SALE_CREATED, EXPENSE_CREATED, etc. |
| `PrecioStrategy` | Clase abstracta (ABC) | Patrón Strategy. Define `utilidad(qty, unit_price, unit_cost)`. |
| `MargenDirecto` | Clase | Implementa PrecioStrategy con la fórmula `qty * (unit_price - unit_cost)`. |
| `PrecioFactory` | Clase (Factory) | Devuelve la estrategia de precio activa (actualmente `MargenDirecto`). |
| `ModelManager` (model.py) | Módulo funcional | Funciones: `entrenar_modelo()`, `predecir_proximos_dias()`, `guardar_modelo()`, `cargar_modelo()`, `estado_monitoreo()`, `insights_del_modelo()`. Fases 3-6 de CRISP-ML(Q). |
| `DataPreparation` (ml.py) | Módulo funcional | Funciones: `preparar_datos_ventas()`, `preparar_datos_gastos()`, `features_target()`, `resumen_preparacion()`. Fase 3 de CRISP-ML(Q). |
| `Chatbot` (chatbot.py) | Módulo funcional | Funciones: `render_chatbot_inline()`, `render_chatbot_modal()`, `render_chatbot_admin()`. Usa Groq + Llama 3.3 70B con RAG. |
| `Database` (db.py) | Módulo funcional | Funciones: `get_engine()`, `validate_login()`, `create_user()`, `get_user_id()`, `is_admin()`, `seed_basic_accounts_for_user()`, etc. Conexión SQLAlchemy a MariaDB. |

### 2.2 Entidades de la base de datos (tablas)

| Tabla | Atributos clave | Relaciones |
|---|---|---|
| `users` | id (PK), username, password_hash | 1:N con carts, cart_sales, cart_expenses, clients, invoices, accounts, inventory, knowledge_base |
| `carts` | id (PK), user_id (FK), name, location, active | 1:N con cart_sales, cart_expenses |
| `cart_sales` | id (PK), user_id (FK), cart_id (FK), sale_date, product, qty, unit_price, unit_cost, notes | N:1 con users, carts |
| `cart_expenses` | id (PK), user_id (FK), cart_id (FK), expense_date, category, description, amount | N:1 con users, carts |
| `clients` | id (PK), user_id (FK), name, email, phone, created_at | 1:N con invoices |
| `invoices` | id (PK), user_id (FK), client_id (FK), cart_id (FK), invoice_date, due_date, status, total | 1:N con invoice_items |
| `invoice_items` | id (PK), invoice_id (FK), description, qty, unit_price | N:1 con invoices |
| `accounts` | id (PK), user_id (FK), code, name, type | N:1 con users |
| `inventory` | id (PK), user_id (FK), product, current_stock, min_stock, unit, updated_at | N:1 con users |
| `knowledge_base` | id (PK), user_id (FK), category, title, content, active, created_at | N:1 con users |
| `audit_log` | id (PK), event, payload, username | Independiente (escrita por AuditObserver) |

### 2.3 Código PlantUML

```plantuml
@startuml DiagramaClases
skinparam shadowing false
skinparam classAttributeIconSize 0
skinparam linetype ortho
hide empty members

' ════════════════════════════════════════════════════
' ENTIDADES DE DOMINIO (tablas de la BD)
' ════════════════════════════════════════════════════

package "Entidades de Dominio" #f5f0eb {

    class User {
        - id : int <<PK>>
        - username : str
        - password_hash : str
    }

    class Cart {
        - id : int <<PK>>
        - user_id : int <<FK>>
        - name : str
        - location : str
        - active : bool
    }

    class CartSale {
        - id : int <<PK>>
        - user_id : int <<FK>>
        - cart_id : int <<FK>>
        - sale_date : date
        - product : str
        - qty : float
        - unit_price : float
        - unit_cost : float
        - notes : str
    }

    class CartExpense {
        - id : int <<PK>>
        - user_id : int <<FK>>
        - cart_id : int <<FK>>
        - expense_date : date
        - category : str
        - description : str
        - amount : float
    }

    class Client {
        - id : int <<PK>>
        - user_id : int <<FK>>
        - name : str
        - email : str
        - phone : str
        - created_at : datetime
    }

    class Invoice {
        - id : int <<PK>>
        - user_id : int <<FK>>
        - client_id : int <<FK>>
        - cart_id : int <<FK>>
        - invoice_date : date
        - due_date : date
        - status : str
        - total : float
    }

    class InvoiceItem {
        - id : int <<PK>>
        - invoice_id : int <<FK>>
        - description : str
        - qty : float
        - unit_price : float
    }

    class Account {
        - id : int <<PK>>
        - user_id : int <<FK>>
        - code : str
        - name : str
        - type : str
    }

    class Inventory {
        - id : int <<PK>>
        - user_id : int <<FK>>
        - product : str
        - current_stock : float
        - min_stock : float
        - unit : str
        - updated_at : datetime
    }

    class KnowledgeBase {
        - id : int <<PK>>
        - user_id : int <<FK>>
        - category : str
        - title : str
        - content : text
        - active : bool
        - created_at : datetime
    }

    class AuditLog {
        - id : int <<PK>>
        - event : str
        - payload : json
        - username : str
    }
}

' ── Relaciones entre entidades ────────────────

User "1" --> "*" Cart
User "1" --> "*" CartSale
User "1" --> "*" CartExpense
User "1" --> "*" Client
User "1" --> "*" Invoice
User "1" --> "*" Account
User "1" --> "*" Inventory
User "1" --> "*" KnowledgeBase

Cart "1" --> "*" CartSale
Cart "1" --> "*" CartExpense

Client "1" --> "*" Invoice
Invoice "1" --> "*" InvoiceItem

' ════════════════════════════════════════════════════
' PATRÓN FACADE
' ════════════════════════════════════════════════════

package "Patrón Facade" #e8f4f8 {

    class AccountingFacade <<Facade>> {
        - _user_id : int
        --
        + listar_carritos(solo_activos) : list
        + crear_carrito(name, location, active)
        + listar_ventas() : list
        + crear_venta(sale_date, cart_id, product, qty, ...)
        + eliminar_venta(sale_id)
        + listar_gastos() : list
        + crear_gasto(expense_date, cart_id, category, ...)
        + kpis() : dict
        + top_carritos_utilidad() : list
        + resumen_por_carrito(cart_id, start, end) : dict
        + detalle_ventas_carrito(cart_id, start, end) : list
        + detalle_gastos_carrito(cart_id, start, end) : list
        + listar_clientes() : list
        + crear_cliente(name, email, phone)
        + listar_facturas() : list
        + crear_factura(client_id, cart_id, ..., items) : int
        + listar_cuentas() : list
        + crear_cuenta(code, name, type_)
        + listar_stock() : list
        + stock_bajo() : list
        + guardar_stock(product, current_stock, ...)
        + eliminar_stock(stock_id)
        + listar_conocimiento(solo_activos) : list
        + agregar_conocimiento(category, title, content)
        + generar_insights_automaticos() : int
        ..
        + admin_resumen_usuarios() : list
        + admin_listar_carritos() : list
        + admin_kpis_globales() : dict
    }
}

AccountingFacade ..> Cart : gestiona
AccountingFacade ..> CartSale : gestiona
AccountingFacade ..> CartExpense : gestiona
AccountingFacade ..> Client : gestiona
AccountingFacade ..> Invoice : gestiona
AccountingFacade ..> Account : gestiona
AccountingFacade ..> Inventory : gestiona
AccountingFacade ..> KnowledgeBase : gestiona

' ════════════════════════════════════════════════════
' PATRÓN OBSERVER
' ════════════════════════════════════════════════════

package "Patrón Observer" #f0e8f8 {

    interface Observer <<Protocol>> {
        + update(event: str, payload: dict)
    }

    class Event <<constants>> {
        + {static} SALE_CREATED : str
        + {static} EXPENSE_CREATED : str
        + {static} INVOICE_CREATED : str
        + {static} CLIENT_CREATED : str
        + {static} CART_CREATED : str
        + {static} ACCOUNT_CREATED : str
    }

    class AuditObserver {
        + update(event, payload)
    }

    class CacheObserver {
        + update(event, payload)
    }

    class EmailObserver {
        + update(event, payload)
    }
}

Observer <|.. AuditObserver
Observer <|.. CacheObserver
Observer <|.. EmailObserver

AccountingFacade --> Observer : notifica
AuditObserver ..> AuditLog : escribe

' ════════════════════════════════════════════════════
' PATRÓN STRATEGY
' ════════════════════════════════════════════════════

package "Patrón Strategy" #f8f0e0 {

    abstract class PrecioStrategy <<ABC>> {
        + {abstract} utilidad(qty, unit_price, unit_cost) : float
    }

    class MargenDirecto {
        + utilidad(qty, unit_price, unit_cost) : float
    }

    class PrecioFactory <<Factory>> {
        + {static} get() : PrecioStrategy
    }
}

PrecioStrategy <|-- MargenDirecto
PrecioFactory ..> MargenDirecto : crea
AccountingFacade --> PrecioStrategy : usa

' ════════════════════════════════════════════════════
' MÓDULOS ML (CRISP-ML/Q)
' ════════════════════════════════════════════════════

package "Machine Learning (CRISP-ML/Q)" #e8f8e8 {

    class DataPreparation <<module: ml.py>> {
        + preparar_datos_ventas(ventas) : DataFrame
        + preparar_datos_gastos(gastos) : DataFrame
        + features_target(df) : tuple
        + resumen_preparacion(df) : dict
    }

    class ModelManager <<module: model.py>> {
        + entrenar_modelo(ventas) : dict
        + predecir_proximos_dias(resultado, n_dias) : DataFrame
        + insights_del_modelo(resultado, predicciones) : list
        + guardar_modelo(resultado, user_id, hash_datos)
        + cargar_modelo(user_id) : dict
        + estado_monitoreo(user_id, ventas) : dict
    }
}

ModelManager --> DataPreparation : usa
AccountingFacade <.. ModelManager : consulta ventas

' ════════════════════════════════════════════════════
' MÓDULO CHATBOT
' ════════════════════════════════════════════════════

package "Chatbot IA" #fff0e0 {

    class Chatbot <<module: chatbot.py>> {
        + render_chatbot_inline()
        + render_chatbot_modal()
        + render_chatbot_admin()
    }
}

Chatbot --> AccountingFacade : consulta datos
Chatbot --> KnowledgeBase : lee contexto RAG

' ════════════════════════════════════════════════════
' CAPA DE DATOS
' ════════════════════════════════════════════════════

package "Capa de Datos" #f0f0f0 {

    class Database <<module: db.py>> {
        + get_engine() : Engine
        + validate_login(username, password) : bool
        + create_user(username, password) : bool
        + get_user_id(username) : int
        + is_admin(username) : bool
        + get_all_users() : list
        + seed_basic_accounts_for_user(user_id)
        + seed_knowledge_base_table()
    }
}

AccountingFacade --> Database : usa Engine
Database --> User : autentica

@enduml
```

---

## 3. Patrones de diseño identificados

| Patrón | Implementación | Propósito |
|--------|---------------|-----------|
| **Facade** | `AccountingFacade` | Punto de entrada único que simplifica el acceso a todas las operaciones del dominio. Cada página de Streamlit solo interactúa con la fachada. |
| **Observer** | `AuditObserver`, `CacheObserver`, `EmailObserver` | Desacoplamiento entre las operaciones de negocio y efectos secundarios (auditoría, cache, notificaciones). La fachada notifica eventos sin saber quién los escucha. |
| **Strategy** | `PrecioStrategy` → `MargenDirecto` | Permite intercambiar la fórmula de cálculo de utilidad sin modificar la fachada. Extensible a otros métodos de pricing. |
| **Factory** | `PrecioFactory` | Encapsula la creación de la estrategia de precio activa. |
| **Multitenant** | `_user_id` en `AccountingFacade` | Cada usuario ve únicamente sus propios datos. El admin tiene métodos separados sin filtro. |

---

## 4. Instrucciones para generar los diagramas

### Opción A — Online (más rápido)
1. Ir a **https://www.plantuml.com/plantuml/uml**
2. Pegar el código entre `@startuml` y `@enduml`
3. Click en **Submit** → se genera la imagen
4. Click derecho → **Guardar imagen como** PNG/SVG

### Opción B — VS Code
1. Instalar la extensión **PlantUML** (jebbs.plantuml)
2. Crear un archivo `.puml` con el código
3. `Alt+D` para previsualizar
4. `Ctrl+Shift+P` → "PlantUML: Export Current Diagram" para exportar

### Opción C — Draw.io / Lucidchart
Usar la descripción textual de las tablas (secciones 1.1 y 2.1) para dibujar manualmente los diagramas con las relaciones indicadas.
