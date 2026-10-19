# Historias de Usuario - Funcionalidades Actuales (As-Is)

A continuación se detallan las funcionalidades actuales del sistema `automatizacion-facturas`, redactadas en formato de Historias de Usuario Ágiles. Este documento sirve como punto de partida para completar las futuras funcionalidades (To-Be) y avanzar hacia un Documento de Diseño del Sistema (SDD).

---

## 1. Ingesta Automática y Continua de Comprobantes
**Historia de Usuario:**
Como administrador del sistema, quiero que un servicio en segundo plano escuche continuamente las casillas de correo configuradas, para descargar automáticamente las facturas entrantes en formato PDF sin intervención manual.

**Criterios de Aceptación:**
- El servicio (`mail_listener`) debe ejecutarse 24/7 utilizando el protocolo IMAP IDLE.
- Debe descargar los archivos PDF adjuntos y depositarlos en la carpeta `01_pendientes`.
- Debe registrar la recepción inicial del documento en la base de datos SQLite para su seguimiento.

## 2. Extracción Inteligente de Datos (Parser Multiproveedor)
**Historia de Usuario:**
Como analista contable, quiero que el sistema extraiga automáticamente los datos relevantes (cabecera, ítems, totales e impuestos) de los PDF de los proveedores (ej. Cromosol), para evitar la carga manual de datos.

**Criterios de Aceptación:**
- El sistema debe contar con un enrutador (Dispatcher) que identifique al proveedor y asigne el parser correspondiente.
- El parser debe extraer la tabla de productos mediante lectura de coordenadas y escaneo vertical.
- Debe soportar una arquitectura extensible (Patrón Strategy) que permita agregar nuevos proveedores fácilmente heredando de una clase base.

## 3. Validación Contable y Matemática
**Historia de Usuario:**
Como auditor interno, quiero que el sistema valide matemáticamente los montos extraídos de la factura antes de considerarlos válidos, para asegurar la integridad de la información que ingresará al ERP.

**Criterios de Aceptación:**
- **Validación Horizontal:** Cantidad × Precio Unitario = Subtotal de Línea.
- **Validación Vertical:** Neto + IVA + Percepciones = Total del Comprobante.
- El sistema debe admitir una tolerancia paramétrica de redondeo (ej. $0.09) para mitigar errores de coma flotante comunes en facturas.

## 4. Gestión de Estado y Trazabilidad (Base de Datos)
**Historia de Usuario:**
Como operador del sistema, quiero que todos los comprobantes, su estado de procesamiento y los motivos de error se guarden en una base de datos centralizada, para poder auditar el comportamiento del sistema.

**Criterios de Aceptación:**
- El sistema debe utilizar SQLite (`data/facturas.db`) compartida entre los contenedores.
- Cada factura debe tener un estado claro: `PENDIENTE_CARGA`, `CARGADA_CIANBOX`, `ERROR_PROCESAMIENTO` o `ERROR_CARGA`.
- Todo error de lectura o validación matemática debe registrar el motivo exacto en la base de datos (y opcionalmente en un CSV de auditoría).

## 5. Clasificación Física de Archivos
**Historia de Usuario:**
Como usuario de negocio, quiero que los archivos PDF se muevan automáticamente a directorios específicos ("Procesados" o "Errores") tras su validación, para mantener el directorio de entrada limpio y organizado.

**Criterios de Aceptación:**
- Las facturas procesadas y validadas con éxito se mueven a `02_procesados`.
- Las facturas con errores de parseo o matemáticos se mueven a `03_errores`.

## 6. Carga Desatendida Nocturna (Integración con ERP)
**Historia de Usuario:**
Como responsable de inventario, quiero que las facturas validadas se carguen automáticamente en el sistema Cianbox durante la madrugada, para no saturar ni afectar el rendimiento del portal web durante el horario comercial.

**Criterios de Aceptación:**
- Un servicio de orquestación (`scheduler_service`) debe disparar el proceso a la hora configurada.
- El sistema debe utilizar Selenium (Chromium) o integración directa vía Tampermonkey para inyectar los datos en el portal de Cianbox simulando interacción de usuario.
- Debe actualizar el estado en la base de datos a `CARGADA_CIANBOX` tras una carga exitosa.

## 7. Configuración y Operación Dinámica en Caliente
**Historia de Usuario:**
Como administrador de IT, quiero poder modificar parámetros críticos del sistema (como el horario de carga o forzar procesos manuales) mediante comandos por terminal sin necesidad de reiniciar los contenedores.

**Criterios de Aceptación:**
- Debe existir una interfaz por línea de comandos (CLI) dentro de los contenedores para actualizar parámetros en la base de datos (ej: `python main.py --set-horario 03:30`).
- Debe permitir comandos para forzar el procesamiento de un archivo específico o gatillar la carga masiva en cualquier momento.

## 8. Interfaz web
**Historia de Usuario:**
Como analista contable, quiero poder visualizar desde un panel web el estado del sistema.

**Criterios de Aceptación:**
- Debe existir una interfaz por web.
- Debe permitir ver el estado de los comprobantes.
- Debe permitir ver historial de errores
- Debe permitir modificar configuraciones.

## 9. Carga selectiva
**Historia de Usuario:**
Como analista contable, quiero poder seleccionar un conjunto de comprobantes, para forzar el modo de carga.

**Criterios de Aceptación:**
- Debe permitir forzar el procesamiento en el acto de uno o varios comprobantes.
- Debe permitir cancelar el procesamiento.
- 