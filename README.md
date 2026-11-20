# Práctica: Préstamo de equipo en Odoo 20

**Estudiante:** Carlos Bardales
**Docente:** Ing. Ludwing Navarro
**Asignatura:** Programación de Negocios
**Universidad:** Universidad Católica de Honduras (UNICAH)
**Plataforma:** Odoo 20.0 · macOS Apple Silicon

> No se proporcionó número de cuenta, por lo que no se inventa ninguno.

## Descripción

Módulo `prestamo_unicah` para sustituir el control en hoja de cálculo del
préstamo de laptops, proyectores, equipo de audio y de laboratorio de la
UNICAH. Registra el catálogo de equipos, los préstamos con múltiples equipos,
el flujo de estados, las devoluciones y las validaciones de negocio.

## Objetivo

Repasar modelos, permisos, vistas, herencia y validaciones, y aprender:

- Flujo de estados: barra de estado y botones **Borrador → Prestado → Devuelto**.
- Líneas dentro de un formulario (`One2many`): un préstamo con varios equipos.
- Vista kanban: tarjetas de equipos agrupadas por estado.

## Requisitos

- Odoo 20.0 en `/Users/carlosdaniel/Documents/odoo`.
- Entorno virtual `.venv` con Python 3.12.
- PostgreSQL en `127.0.0.1:5433`, usuario `odoo`, base `odoo20_practica`.
- Módulo `mail` (dependencia del manifiesto, para el chatter).

## Instalación

La carpeta que se agrega al `addons_path` es `practica_prestamos` (no el
módulo). En `odoo.conf`:

```ini
addons_path = /Users/carlosdaniel/Documents/odoo/addons,/Users/carlosdaniel/Documents/odoo/custom_addons,/Users/carlosdaniel/Documents/odoo/practica_prestamos
```

Instalación y actualización:

```bash
cd /Users/carlosdaniel/Documents/odoo
.venv/bin/python odoo-bin -c odoo.conf -d odoo20_practica \
    -i prestamo_unicah --stop-after-init
.venv/bin/python odoo-bin -c odoo.conf -d odoo20_practica \
    -u prestamo_unicah --stop-after-init
.venv/bin/python odoo-bin -c odoo.conf -d odoo20_practica
```

## Configuración

- No se requiere configuración adicional.
- Los cuatro equipos iniciales se crean con `noupdate="1"`, por lo que no se
  sobrescriben en actualizaciones.
- Permisos: todos los usuarios internos (`base.group_user`) tienen acceso CRUD
  a los tres modelos del módulo, según la guía.
- Compatibilidad: el módulo anterior `unicah_prestamos` ya define
  `prestamo_ids` en `res.partner`. Para no alterarlo ni redefinir ese campo,
  este módulo usa `prestamo_equipo_ids` para su propia relación.

## Cómo utilizar el módulo

1. Abrir **Préstamos → Equipos**. La vista kanban muestra los equipos agrupados
   por **Disponible / Prestado / En mantenimiento**.
2. En **Préstamos → Préstamos**, crear un préstamo con motivo, solicitante,
   tipo, fechas y una o más líneas en la pestaña **Equipos**.
3. Pulsar **Prestar**. Los equipos pasan a *Prestado* y se escribe en el
   chatter. Los campos y las líneas quedan de solo lectura.
4. Opcionalmente, si ya pasó la fecha de devolución, pulsar **Marcar atrasado**.
5. Pulsar **Devolver**. Los equipos vuelven a *Disponible* y el préstamo queda
   *Devuelto*.
6. En el contacto del solicitante, la pestaña **Préstamos** muestra el historial.
7. En la lista de préstamos funcionan los filtros **Activos** y **Atrasados** y
   las agrupaciones por **Estado** y **Solicitante**.

## Modelos

| Modelo | Descripción | Campos principales |
|---|---|---|
| `prestamo.equipo` | Catálogo de equipos | `name`, `codigo` (único, `copy=False`), `categoria`, `estado`, `notas`, `active`, `veces_prestado` |
| `prestamo.prestamo` | Préstamo y su flujo | `name` (motivo), `partner_id`, `tipo_solicitante`, `fecha_prestamo`, `fecha_devolucion`, `state`, `linea_ids`, `cantidad_equipos`, `dias_prestamo` |
| `prestamo.linea` | Equipo dentro del préstamo | `prestamo_id` (Many2one, `ondelete="cascade"`), `equipo_id` (dominio: disponible), `categoria` (related), `observacion` |
| `res.partner` | Herencia para historial | `prestamo_equipo_ids` (One2many) |

### Estados y flujo

```text
Borrador --Prestar--> Prestado --Devolver--> Devuelto
                         |
                         +--Marcar atrasado--> Atrasado --Devolver--> Devuelto
```

- **Borrador:** se pueden editar todos los campos y las líneas.
- **Prestado:** los equipos están prestados; los campos se bloquean.
- **Atrasado:** la fecha de devolución ya pasó y se marcó manualmente.
- **Devuelto:** estado final; los equipos vuelven a disponible.

### Reglas de negocio

- La fecha de devolución no puede ser anterior a la de préstamo.
- Un estudiante no puede pedir más de **7 días** ni más de **2 equipos**.
- Un docente no tiene esos límites.
- Un equipo no puede repetirse en el mismo préstamo.
- Al prestar se valida que cada equipo siga **disponible** (el dominio del
  campo solo filtra la selección; la validación se ejecuta al guardar/prestar).
- Un equipo prestado no puede enviarse a mantenimiento.

### Retos implementados

1. **Marcar atrasado** con botón, validación de fecha y mensaje en chatter.
2. **Colores en lista:** atrasados en rojo (`decoration-danger`) y devueltos
   en gris (`decoration-muted`).
3. **Veces prestado:** campo calculado visible en formulario, lista y kanban.
4. **Mantenimiento:** botones *Enviar a mantenimiento* y *Marcar disponible*.

## Respuestas

### Paso 1 — Catálogo de equipos

**1. ¿Qué pasa con un equipo cuando se desmarca el campo Activo? ¿Por qué es
mejor que borrarlo?**
El equipo deja de mostrarse en las vistas y en las búsquedas habituales, pero
sigue existiendo en la base de datos con todas sus referencias. Es mejor que
borrarlo porque conserva el historial de préstamos y evita romper las líneas
(`prestamo.linea`) que apuntan a él mediante una clave foránea; borrarlo
perdería la trazabilidad y podría fallar por integridad referencial.

**2. ¿Para qué sirve `copy=False` en el campo `codigo`?**
Evita que, al duplicar un registro con la acción *Duplicar*, Odoo copie el
valor del código de inventario. Como el código debe ser único, copiarlo
generaría un conflicto; `copy=False` obliga a introducir un código nuevo.

### Paso 2 — Registro de préstamos

**1. Este modelo usa `_name` y `_inherit` al mismo tiempo. ¿Qué hace cada uno
aquí?**
`_name = "prestamo.prestamo"` crea un modelo nuevo con su propia tabla.
`_inherit = ["mail.thread"]` hereda el comportamiento de mensajería (chatter,
historial de mensajes y seguimiento), sin crear otro modelo ni otra tabla.

**2. ¿Qué hace `tracking=True` en el campo `state`?**
Hace que Odoo registre automáticamente en el chatter cada cambio de estado,
indicando valor anterior y nuevo valor, usuario y fecha. Esa es la traza que se
ve al prestar y devolver.

### Paso 3 — Equipos del préstamo

**1. En `fields.One2many("prestamo.linea", "prestamo_id")`, ¿qué indica cada
parámetro?**
El primero es el modelo destino de las líneas (`prestamo.linea`). El segundo
es el nombre del campo Many2one en ese modelo que apunta de vuelta al préstamo
(`prestamo_id`). Odoo usa esa pareja para saber qué líneas pertenecen al
registro actual y para mantener la relación inversa.

**2. ¿Qué pasa con las líneas cuando se borra un préstamo? ¿Qué parte del
código lo define?**
Se borran automáticamente las líneas asociadas. Lo define
`ondelete="cascade"` en el campo `prestamo_id` de `prestamo.linea`, que crea la
restricción `ON DELETE CASCADE` en PostgreSQL.

### Paso 4 — Flujo de estados

**1. Los botones ya se ocultan según el estado. ¿Por qué los métodos vuelven a
validar el estado?**
Porque `invisible` es solo una regla de interfaz: cualquier usuario podría
llamar al método desde código, desde una acción automatizada, desde la API o
con una petición manipulada. La validación en Python es la verdadera regla de
negocio y protege la integridad del dato.

**2. ¿Qué hace `prestamo.linea_ids.equipo_id.write({...})`? ¿Por qué no hace
falta un `for` para cada equipo?**
`mapped("equipo_id")` sobre `linea_ids` devuelve un recordset con todos los
equipos de las líneas (sin duplicados). `write()` se aplica a todo el
recordset en una sola operación, por lo que Odoo ejecuta una única actualización
SQL en lugar de recorrer equipo por equipo.

### Paso 5 — Reglas del préstamo

**1. El campo `equipo_id` ya filtra los equipos disponibles. ¿Por qué hace
falta el TODO 5?**
El `domain` solo filtra lo que se puede **seleccionar** en el formulario; no
impide que un equipo ya elegido cambie de estado a *Mantenimiento* (o a
*Prestado* en otro préstamo) antes de pulsar **Prestar**. La validación en
`action_prestar` comprueba el estado real en el momento de ejecutar la acción.

**2. ¿En qué momento se ejecuta un método con `@api.constrains`? ¿Y la
validación de `action_prestar`?**
`@api.constrains` se ejecuta automáticamente al crear o escribir el registro,
dentro de la transacción; si lanza `ValidationError`, se revierte la operación.
La validación de `action_prestar` solo se ejecuta cuando se pulsa el botón (o
se llama explícitamente al método), no al guardar un borrador. Por eso un
préstamo inválido puede guardarse en borrador pero no prestarse.

### Paso 6 — Contacto, kanban y búsqueda

**1. ¿Qué pasa si arrastra una tarjeta del kanban a otra columna? ¿Por qué?**
En esta vista no se puede: las columnas corresponden al campo `estado`, que no
está declarado como campo de agrupación editable ni se ha configurado
`default_group_by` con `editable`. El kanban es de solo lectura para ese
campo; el estado cambia únicamente con los botones del formulario, que además
validan Reglas del préstamo y actualizan el estado de los equipos. Arrastrar
no tendría efecto (o se rechazaría) porque no hay un `write` autorizado ni la
lógica de negocio asociada.

**2. El campo `prestamo_ids` se agregó a `res.partner`. ¿Se crea una columna
nueva en la tabla de contactos? Explique.**
No. Es un campo `One2many`, un campo relacional inverso calculado a partir del
Many2one `partner_id` existente en `prestamo.prestamo`. Odoo no crea columnas
en `res_partner`; la relación se resuelve con una consulta inversa. (En este
proyecto, además, se usó el nombre `prestamo_equipo_ids` para no sobrescribir
el `prestamo_ids` del módulo anterior `unicah_prestamos`.)

## Estructura de carpetas

```text
practica_prestamos/
├── prestamo_unicah/
│   ├── __init__.py
│   ├── __manifest__.py
│   ├── data/
│   │   └── prestamo_equipo_data.xml
│   ├── models/
│   │   ├── __init__.py
│   │   ├── prestamo_equipo.py
│   │   ├── prestamo_linea.py
│   │   ├── prestamo_prestamo.py
│   │   └── res_partner.py
│   ├── security/
│   │   └── ir.access.csv
│   ├── tests/
│   │   ├── __init__.py
│   │   └── test_prestamo_unicah.py
│   └── views/
│       ├── prestamo_equipo_views.xml
│       ├── prestamo_views.xml
│       └── res_partner_views.xml
└── README.md
```

## Evidencias y pruebas realizadas

Comprobaciones ejecutadas el **20 de noviembre de 2026** en la base
`odoo20_practica`:

- Sintaxis Python validada con `python -m compileall` → **OK**.
- Los 4 archivos XML analizados con `xml.etree.ElementTree` → **OK**.
- Instalación: `-i prestamo_unicah` → módulo en estado **installed**
  (`20.0.1.0`).
- Suite automatizada:

  ```bash
  .venv/bin/python odoo-bin -c odoo.conf -d odoo20_practica \
      -u prestamo_unicah --test-enable --test-tags /prestamo_unicah \
      --stop-after-init --log-level=test
  ```

  Resultado real: **20 pruebas, 0 fallos, 0 errores** (24 operaciones
  reportadas por `odoo.tests.stats`).

- Cobertura: catálogo inicial, código único, mantenimiento, fechas invertidas,
  límite de días de estudiante, docente sin límite, equipos repetidos, flujo
  prestar/devolver, préstamo sin equipos, límite de 2 equipos para estudiante,
  docente con 3 equipos, equipo en mantenimiento al prestar, marcar atrasado
  (dentro y fuera de fecha), borrado en cascada, `veces_prestado`, herencia de
  `res.partner` y existencia de vistas y menús.
- Consultas SQL posteriores confirmaron los 4 equipos iniciales en estado
  *Disponible* y los modelos `prestamo.equipo`, `prestamo.prestamo` y
  `prestamo.linea` cargados.
- Verificación de no regresión: `ventas_unicah`, `tienda_unicah` y
  `unicah_prestamos` siguen en estado **installed** con sus versiones
  originales; no se modificaron sus archivos.

## GitHub

GitHub CLI (`gh`) no está instalado en este equipo y no hay sesión autenticada
disponible. El repositorio queda preparado localmente con un commit inicial y
un ZIP de entrega. El único paso pendiente para publicarlo es:

```bash
cd /Users/carlosdaniel/Documents/odoo/practica_prestamos
git remote add origin https://github.com/TU_USUARIO/practica_prestamos.git
git branch -M main
git push -u origin main
```
