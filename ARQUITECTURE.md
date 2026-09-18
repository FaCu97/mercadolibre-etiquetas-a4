# Arquitectura y funcionamiento

## Propósito

**Etiquetas 2/3 A4** es una extensión de Chrome (Manifest V3) que toma PDFs de etiquetas de Mercado Libre y los recompone para imprimir dos etiquetas por hoja A4. El último tercio de la hoja queda libre, para usar papel A4 ya cortado a dos tercios.

Todo el análisis y la generación del PDF ocurren localmente en el navegador. No hay backend ni llamadas a servicios externos: los archivos, direcciones y códigos permanecen en el equipo.

## Componentes

| Componente | Archivo(s) | Responsabilidad |
| --- | --- | --- |
| Interfaz del popup | `app.html`, `src/app.js`, `src/style.css` | Permite elegir o arrastrar un PDF, configurar el destino de los documentos auxiliares, iniciar la conversión y descargar el resultado. |
| Service worker | `public/background.js` | Detecta si la pestaña activa muestra un PDF local, habilita el procesamiento con un clic y coordina el documento offscreen y las descargas. |
| Documento offscreen | `offscreen.html`, `src/offscreen.js` | Procesa un PDF local abierto en Chrome fuera de la interfaz visible; puede seguir activo mientras se prepara la descarga. |
| Adaptador de PDF | `src/pdf-processor.js` | Configura el worker de PDF.js y conecta la lógica independiente de la interfaz con la librería de lectura. |
| Núcleo de transformación | `src/pdf-core.js` | Inspecciona páginas, identifica etiquetas y documentos auxiliares, recorta y rearma los PDFs de salida. |
| Configuración persistente | `chrome.storage.local` | Guarda sólo `auxiliaryMode`: `discard`, `separate` o `combined`. |
| Pruebas | `test/pdf-core.test.mjs` | Comprueba conteos de etiquetas, hojas y documentos auxiliares usando fixtures privados cuando están disponibles. |

`options.html` y `src/options.js` contienen una vista alternativa de configuración. Actualmente el manifest no la declara como página de opciones: la configuración que usa la extensión está integrada en el popup.

## Flujo general

```text
PDF de Mercado Libre
        |
        +-- Selección/arrastre en el popup ----+
        |                                      |
        +-- PDF local abierto en Chrome --> service worker
                                               |
                                               v
                                      documento offscreen
                                               |
                                               v
                         src/pdf-processor.js + src/pdf-core.js
                                               |
                         +---------------------+---------------------+
                         |                                           |
                         v                                           v
             PDF de etiquetas 2/3 A4                  PDF auxiliar (opcional)
                         |                                           |
                         +------ descarga del navegador <------------+
```

Hay dos formas de iniciar el procesamiento:

1. **Desde el popup.** La persona selecciona o arrastra un archivo. `src/app.js` lo convierte a `Uint8Array`, llama a `processLabels` y descarga los bytes devueltos mediante un `Blob` temporal.
2. **Desde un PDF local ya abierto.** El service worker reconoce una URL `file:` directa o una URL del visor de Chrome con el parámetro `file`. Cuando existe el permiso de acceso a URLs de archivos, crea el documento offscreen y le envía el mensaje `process-active-pdf`. El offscreen lee el archivo con `fetch`, procesa el PDF y devuelve al service worker URLs `data:` listas para `chrome.downloads.download`.

El segundo recorrido necesita que la persona active **Permitir acceso a URLs de archivos** en los detalles de la extensión. Si no está disponible, el popup sigue permitiendo elegir el PDF manualmente.

## Cómo se clasifica cada página

El núcleo usa PDF.js para extraer texto y sus coordenadas. No rasteriza ni aplica OCR: se apoya en el texto embebido en el PDF original.

Para cada página, `inspectPage` determina:

- **Etiquetas:** busca el texto `Recortá esta parte de la etiqueta` o `Entregar a colecta Full` (admite acentos y mayúsculas). Sólo considera ocurrencias horizontales y calcula en cuál de las tres columnas está según su coordenada X.
- **Listado de carrito:** busca el pie `Envíe sus ventas lo antes posible`.
- **Página auxiliar genérica:** una página sin etiquetas, con más de 40 caracteres no blancos, se considera por ejemplo una hoja de control.

Una página se conserva como auxiliar si es un listado de carrito o si no contiene etiquetas pero sí texto significativo. Si no se detecta ninguna etiqueta en todo el archivo, se informa un error de PDF incompatible.

## Cómo se reconstruyen las etiquetas

Mercado Libre presenta hasta tres etiquetas visuales por A4 en formato apaisado. La implementación usa marcos con proporciones fijas (`LABEL_FRAME_STARTS` y `LABEL_FRAME_WIDTH`) basadas en los márgenes reales de su plantilla, más un padding de 2 puntos. No divide el A4 en tres tercios matemáticos para evitar desplazar el contenido.

Por cada etiqueta detectada:

1. Se recorta únicamente el marco de esa columna con `pdf-lib`.
2. Se crea una hoja destino cada dos etiquetas.
3. La primera y segunda etiqueta se dibujan en los dos marcos derechos del A4, dejando vacío el tercio restante.
4. Si queda una etiqueta sin pareja, se coloca en el marco derecho final de su propia hoja.

El resultado principal se titula `Etiquetas 2/3 A4` y su número de páginas es `ceil(cantidad_de_etiquetas / 2)`.

## Documentos auxiliares

La preferencia `auxiliaryMode` determina qué hacer con las páginas que no son etiquetas:

| Modo | Resultado |
| --- | --- |
| `discard` | No se incluyen auxiliares. Sólo se descarga el PDF de etiquetas. |
| `separate` | Se genera un segundo PDF: `*-documentos-auxiliares.pdf`. |
| `combined` | Las páginas auxiliares se agregan al final del PDF de etiquetas. |

Las hojas de control se copian completas. En cambio, los listados de carrito se recortan: se elimina el área de la etiqueta y los márgenes vacíos, y el detalle se reubica alineado con el borde derecho de una etiqueta. Esto evita conservar una franja de etiqueta junto al listado.

## Dependencias y build

- **PDF.js (`pdfjs-dist`)**: extracción de texto, coordenadas y cantidad de páginas. Su worker se resuelve como recurso de Vite en `src/pdf-processor.js`.
- **pdf-lib**: recorte, incrustación de páginas y creación de los PDFs de salida.
- **Vite**: empaqueta `app.html` y `offscreen.html`; los recursos públicos, incluido el manifest y el service worker, se copian a `dist/`.

Los comandos principales son:

```bash
npm test
npm run build
npm run package:store
```

Las pruebas con PDFs reales son deliberadamente opcionales: se ejecutan sólo si existen archivos en `private-pdfs/`, directorio que no se versiona porque puede contener datos personales.

## Límites y supuestos

- La detección está diseñada para la estructura textual actual de los PDFs de Mercado Libre. Si cambian sus textos marcadores o su plantilla, habrá que ajustar las expresiones regulares y los marcos de recorte.
- Se requiere que el PDF tenga texto seleccionable; un PDF escaneado como imagen no contiene las señales necesarias para detectar etiquetas.
- El PDF de salida debe imprimirse en A4, orientación original y escala 100 % / tamaño real para preservar las dimensiones y la ubicación de los códigos.
- La extensión sólo persiste la preferencia de documentos auxiliares; no conserva PDFs ni su contenido.
