# Requerimientos del sistema interno del negocio

Estado: borrador para completar antes de desarrollar.

## Cómo completar este documento

- Reemplazar `[Completar]` con respuestas concretas. Si algo no está definido, escribir `Pendiente`.
- Marcar cada definición como **Confirmada**, **Propuesta** o **Pendiente**. Los ejemplos no son requisitos aprobados.
- Describir primero la necesidad y el resultado esperado; las pantallas y decisiones técnicas se definen después.
- Priorizar procesos que puedan completarse de principio a fin.
- Usar como referencia del sistema actual [arquitectura_y_uso.md](arquitectura_y_uso.md) e [historias_de_usuario_as_is.md](historias_de_usuario_as_is.md), verificando que sigan vigentes.

## 1. Objetivo y alcance

### Dirección conversada

**Propuesta:** evolucionar el proyecto de facturas hacia un sistema interno del negocio que incorpore McGard y un CRM pequeño, con una base de datos y un sistema de acceso comunes. Falta cerrar alcance, prioridades y decisiones técnicas.

**Objetivo propuesto:** gestionar la recepción y carga de facturas de proveedores, consultar llaves McGard y dar seguimiento a consultas comerciales, con usuarios y permisos comunes.

Objetivo definitivo: [Completar]

Problemas que queremos resolver, en orden de importancia:

1. [Completar]
2. [Completar]
3. [Completar]

¿Cómo vamos a medir que el sistema resulta útil? Indicar situación actual y resultado deseado, por ejemplo tiempo de revisión o cantidad de consultas sin seguimiento.

| Indicador | Situación actual | Resultado deseado |
|---|---|---|
| [Completar] | [Completar] | [Completar] |

### Límites e integración con otras herramientas

| Herramienta | Qué seguirá resolviendo | Qué resolverá el nuevo sistema | Datos que deben intercambiarse |
|---|---|---|---|
| Cianbox | [Completar] | [Completar] | [Completar] |
| Correo electrónico | [Completar] | [Completar] | [Completar] |
| WhatsApp / otros canales | [Completar] | [Completar] | [Completar] |

Fuera de alcance de la primera versión:

- [Completar]

## 2. Usuarios y permisos

Cantidad de usuarios: [Completar]

Cantidad estimada de usuarios simultáneos: [Completar]

Dispositivos utilizados (computadora, celular, ambos): [Completar]

Roles tentativos; modificar según las tareas reales:

| Rol | Personas / cantidad | Tareas principales | Módulos habilitados |
|---|---|---|---|
| Administrador | [Completar] | [Completar] | [Completar] |
| Administración / compras | [Completar] | [Completar] | [Completar] |
| Ventas | [Completar] | [Completar] | [Completar] |

Completar cada permiso con `Sí`, `No` o una condición:

| Acción | Administrador | Administración / compras | Ventas |
|---|---|---|---|
| Crear usuarios y cambiar permisos | Pendiente | Pendiente | Pendiente |
| Ver facturas y sus archivos | Pendiente | Pendiente | Pendiente |
| Corregir datos de facturas | Pendiente | Pendiente | Pendiente |
| Aprobar / reintentar una carga | Pendiente | Pendiente | Pendiente |
| Consultar el buscador McGard | Pendiente | Pendiente | Pendiente |
| Crear y editar clientes | Pendiente | Pendiente | Pendiente |
| Ver consultas de otros empleados | Pendiente | Pendiente | Pendiente |
| Asignar responsables y cerrar consultas | Pendiente | Pendiente | Pendiente |
| Eliminar / archivar registros | Pendiente | Pendiente | Pendiente |
| Exportar información | Pendiente | Pendiente | Pendiente |

## 3. Estado actual y necesidades

### Facturas

Referencia técnica observada: usa SQLite y tiene modelos para proveedores, comprobantes, ítems, registros de proceso y configuración. Esto no implica que todo el circuito esté validado para uso diario.

- Qué funciona hoy y ya se utiliza: [Completar]
- Qué funciona pero requiere revisión: [Completar]
- Qué falta: [Completar]
- Problemas frecuentes y ejemplos reales: [Completar]
- Proveedores y tipos de comprobantes necesarios en la primera versión: [Completar]
- Volumen diario / mensual y picos: [Completar]

### McGard y CRM

Referencia técnica observada: el buscador local usa un catálogo estático generado desde planillas; el despliegue está preparado con Nginx y credenciales de acceso. El CRM es una ampliación por definir.

- Funciones actuales que deben conservarse: [Completar]
- Cómo se reciben las consultas hoy: [Completar]
- Dónde se anotan clientes y seguimientos hoy: [Completar]
- Problemas frecuentes y ejemplos reales: [Completar]
- Cantidad de consultas diarias / mensuales: [Completar]
- ¿El CRM será solo para McGard o para otras ventas del negocio?: [Completar]

## 4. Procesos del negocio

### 4.1 Recepción y procesamiento de facturas

Flujo de ejemplo a validar:

> Llega un comprobante → se identifica proveedor → se extraen datos → se revisa si corresponde → se carga en Cianbox → se registra el resultado.

- Evento que inicia el proceso: [Completar]
- Persona responsable: [Completar]
- Entradas necesarias: [Completar]
- Pasos reales y cuáles requieren intervención humana:
  1. [Completar]
  2. [Completar]
  3. [Completar]
- Resultado que permite darlo por terminado: [Completar]
- Notificaciones necesarias, destinatarios y canal: [Completar]

| Situación | Comportamiento esperado | Quién la resuelve |
|---|---|---|
| Comprobante duplicado | [Completar] | [Completar] |
| Proveedor desconocido | [Completar] | [Completar] |
| PDF ilegible o extracción incompleta | [Completar] | [Completar] |
| Importes o datos inconsistentes | [Completar] | [Completar] |
| Cianbox no disponible | [Completar] | [Completar] |
| Se interrumpe la carga y no se sabe si se completó | [Completar] | [Completar] |
| Nota de crédito u otro caso especial | [Completar] | [Completar] |

### 4.2 Consulta McGard y seguimiento comercial

Flujo de ejemplo a validar:

> Llega una consulta → se identifica al cliente → se busca la llave → se registra la respuesta → se agenda seguimiento → se cierra con un resultado.

- Evento que inicia el proceso y canales de entrada: [Completar]
- Persona responsable: [Completar]
- Pasos reales:
  1. [Completar]
  2. [Completar]
  3. [Completar]
- ¿Cuándo se crea un cliente y cuándo alcanza con registrar una consulta?: [Completar]
- ¿Qué se considera una venta concretada y dónde se registra?: [Completar]
- ¿Se necesitan precios, presupuestos o stock? ¿De dónde salen?: [Completar]
- ¿Cómo se decide cuándo hacer seguimiento?: [Completar]
- ¿Qué pasa si cambia el empleado responsable?: [Completar]

| Situación | Comportamiento esperado | Quién la resuelve |
|---|---|---|
| Código inválido o sin coincidencia | [Completar] | [Completar] |
| Varias llaves compatibles | [Completar] | [Completar] |
| Cliente ya registrado | [Completar] | [Completar] |
| Cliente sin datos de contacto | [Completar] | [Completar] |
| Consulta sin respuesta / seguimiento vencido | [Completar] | [Completar] |
| Venta perdida o consulta cancelada | [Completar] | [Completar] |

### 4.3 Estados y transiciones

Definir estados del negocio, no solo nombres de botones. Ejemplos para discutir: consulta nueva, respondida, pendiente de seguimiento, ganada o perdida.

| Entidad | Estado actual | Acción / condición | Estado siguiente | Quién puede hacerlo |
|---|---|---|---|---|
| Factura | [Completar] | [Completar] | [Completar] | [Completar] |
| Consulta | [Completar] | [Completar] | [Completar] | [Completar] |

## 5. Datos necesarios

Definir datos desde el negocio; el esquema de tablas se diseña después. Aclarar qué sistema es la fuente válida cuando un dato existe en más de uno.

| Entidad | Datos necesarios | Obligatorios | Cómo evitar duplicados | Origen / fuente válida |
|---|---|---|---|---|
| Usuario | [Completar] | [Completar] | [Completar] | [Completar] |
| Cliente | [Completar] | [Completar] | [Completar] | [Completar] |
| Consulta comercial | [Completar] | [Completar] | [Completar] | [Completar] |
| Seguimiento / tarea | [Completar] | [Completar] | [Completar] | [Completar] |
| Proveedor | [Completar] | [Completar] | [Completar] | [Completar] |
| Factura y sus ítems | [Completar] | [Completar] | [Completar] | [Completar] |
| Catálogo McGard | [Completar] | [Completar] | [Completar] | [Completar] |

- Datos existentes que hay que importar o conservar: [Completar]
- Archivos adjuntos necesarios (PDF, imágenes, otros): [Completar]
- Información que debe conservar historial de cambios: [Completar]
- Reglas para archivar, eliminar y conservar información: [Completar]
- Responsable y procedimiento de actualización del catálogo McGard: [Completar]

## 6. Acceso y administración

Objetivo: un acceso común sencillo para los empleados, con permisos controlados en el servidor.

| Decisión | Respuesta | Estado |
|---|---|---|
| Acceso con contraseña propia o cuenta Google / Microsoft | [Completar] | Pendiente |
| Quién crea y habilita cuentas | [Completar] | Pendiente |
| Cómo se recupera el acceso | [Completar] | Pendiente |
| Cuánto dura una sesión | [Completar] | Pendiente |
| Uso en computadoras compartidas | [Completar] | Pendiente |
| Necesidad de segundo factor y para qué roles | [Completar] | Pendiente |
| Cómo se da de baja un empleado y se revocan sus sesiones | [Completar] | Pendiente |

Requisitos técnicos propuestos para validar: HTTPS, cookies de sesión seguras, protección ante intentos repetidos, almacenamiento seguro de contraseñas si corresponde y verificación de permisos en cada operación del servidor.

## 7. Catálogo de funcionalidades y prioridades

Prioridades:

- **V1:** imprescindible para operar la primera versión.
- **V2:** mejora importante que puede esperar a la siguiente entrega.
- **Después:** posible mejora futura.
- **Fuera:** no se desarrollará dentro de este alcance.

Las filas siguientes son propuestas para discutir, no compromisos de desarrollo. Ordenar considerando frecuencia de uso, tiempo ahorrado, errores evitados y dependencias. Estimar esfuerzo después de aclarar el requisito.

| ID | Funcionalidad | Beneficio / problema resuelto | Prioridad | Dependencias | Estado de definición |
|---|---|---|---|---|---|
| ACC-01 | Login y cierre de sesión | Acceso individual al sistema | Pendiente | — | Propuesta |
| ACC-02 | Gestión de usuarios y permisos | Control de acceso por módulo | Pendiente | ACC-01 | Propuesta |
| FAC-01 | Recepción y extracción de comprobantes | Reducir carga manual | Pendiente | [Completar] | Propuesta |
| FAC-02 | Revisión y corrección de facturas | Resolver datos incompletos o incorrectos | Pendiente | FAC-01 | Propuesta |
| FAC-03 | Carga en Cianbox y control de resultado | Completar el circuito sin duplicaciones | Pendiente | FAC-02 | Propuesta |
| MCG-01 | Buscador McGard integrado | Consultar llaves desde el sistema común | Pendiente | ACC-01 | Propuesta |
| CRM-01 | Registro de clientes | Conservar datos de contacto | Pendiente | ACC-02 | Propuesta |
| CRM-02 | Registro de consultas | Conservar contexto e historial comercial | Pendiente | [Completar] | Propuesta |
| CRM-03 | Responsables y seguimientos | Evitar consultas olvidadas | Pendiente | CRM-02 | Propuesta |
| OPS-01 | Respaldo y restauración | Recuperar datos y archivos | Pendiente | [Completar] | Propuesta |

### Ficha para copiar por cada funcionalidad

#### [ID] — [Nombre]

- **Estado de definición:** [Confirmada / Propuesta / Pendiente]
- **Usuario / rol:** [Completar]
- **Necesidad:** Como [rol], necesito [acción] para [resultado].
- **Situación actual:** [Completar]
- **Alcance:** [Completar]
- **Fuera de alcance:** [Completar]
- **Datos de entrada y obligatorios:** [Completar]
- **Resultado esperado:** [Completar]
- **Reglas de negocio y permisos:** [Completar]
- **Errores y casos especiales:** [Completar]
- **Dependencias:** [Completar]
- **Prioridad y motivo:** [Completar]
- **Frecuencia de uso / impacto:** [Completar]
- **Esfuerzo estimado:** [Pendiente de análisis técnico]
- **Dudas pendientes:** [Completar]

**Criterios de aceptación** — condiciones observables que permiten comprobar que está terminada:

- [ ] Dado [contexto], cuando [acción], entonces [resultado esperado].
- [ ] Si ocurre [error o excepción], el sistema [comportamiento esperado].
- [ ] Un usuario sin permiso [resultado esperado].

**Ejemplo real para validar:** [Completar con datos ficticios o anonimizados]

## 8. Funcionamiento y operación

| Aspecto | Necesidad / respuesta |
|---|---|
| Raspberry: memoria, almacenamiento y espacio disponible | [Completar] |
| Horarios de uso y de procesamiento automático | [Completar] |
| Tiempo de respuesta aceptable en tareas habituales | [Completar] |
| Tiempo máximo tolerable de caída | [Completar] |
| Cantidad máxima de información que se acepta perder ante una falla | [Completar] |
| Frecuencia, destino y retención de respaldos | [Completar] |
| Responsable de verificar respaldos y probar restauraciones | [Completar] |
| Comportamiento ante cortes de internet o energía | [Completar] |
| Alertas por fallas: destinatarios y canal | [Completar] |
| Quién realiza actualizaciones y en qué horario | [Completar] |

Los respaldos deben contemplar tanto la base como los archivos necesarios para recuperar el sistema.

## 9. Entregas propuestas

Secuencia inicial para revisar según las prioridades del negocio. La base común puede entregarse junto con el primer módulo útil.

| Entrega | Resultado utilizable | IDs incluidos | Condición para considerarla lista |
|---|---|---|---|
| 1. Base común y facturas | Usuarios habilitados pueden completar el circuito de facturas y resolver errores | [Completar] | [Completar] |
| 2. Buscador integrado | Los empleados consultan McGard dentro del mismo sistema | [Completar] | [Completar] |
| 3. CRM mínimo | Se registran consultas, responsables y seguimientos pendientes | [Completar] | [Completar] |
| 4. Mejoras | Funciones elegidas a partir del uso real | [Completar] | [Completar] |

- Fecha deseada para la primera versión y motivo: [Completar]
- Personas que probarán cada entrega: [Completar]
- Cómo se hará la transición desde las herramientas actuales: [Completar]
- Qué tiene que estar validado antes de retirar el McGard independiente: [Completar]

## 10. Decisiones técnicas pendientes

Estas propuestas se evaluarán contra los requisitos; no reemplazan su definición.

| Tema | Propuesta conversada | Estado / decisión final |
|---|---|---|
| Organización | Una aplicación con módulos de facturas, McGard/CRM y administración | Pendiente |
| Backend | Aprovechar el proyecto Python de facturas | Pendiente |
| Base de datos | PostgreSQL común, con tablas organizadas por módulo | Pendiente |
| Acceso | Un login con permisos por módulo | Pendiente |
| Procesos automáticos | Correo y Selenium separados del servidor web | Pendiente |
| Alojamiento | Raspberry Pi 5 y acceso mediante el túnel existente | Pendiente de verificar capacidad y despliegue |

## 11. Preguntas abiertas y registro de decisiones

| ID | Pregunta | Quién la responde | ¿Bloquea una entrega? | Respuesta |
|---|---|---|---|---|
| P-01 | ¿Qué problema conviene resolver primero? | [Completar] | [Completar] | [Completar] |
| P-02 | ¿Qué tareas seguirán exclusivamente en Cianbox? | [Completar] | [Completar] | [Completar] |
| P-03 | ¿El CRM abarca solo McGard? | [Completar] | [Completar] | [Completar] |
| P-04 | ¿Qué falta para operar facturas diariamente? | [Completar] | [Completar] | [Completar] |

| Fecha | Decisión confirmada | Motivo | Requisitos afectados |
|---|---|---|---|
| [Completar] | [Completar] | [Completar] | [Completar] |

## 12. Checklist antes de empezar cada entrega

- [ ] El proceso y sus responsables están definidos.
- [ ] Está claro qué entra y qué queda fuera.
- [ ] Los requisitos tienen prioridad y criterios de aceptación.
- [ ] Los permisos y datos obligatorios están definidos.
- [ ] Se definió qué sucede ante errores, duplicados e interrupciones relevantes.
- [ ] Las dudas que bloquean la entrega están resueltas.
- [ ] Se identificaron datos a migrar y funciones actuales a conservar.
- [ ] Hay ejemplos para probar y una persona responsable de validarlos.
