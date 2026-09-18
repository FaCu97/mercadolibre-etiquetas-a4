# Material para Chrome Web Store

## Información de la ficha

- **Nombre:** Etiquetas 2/3 A4
- **Categoría sugerida:** Productividad
- **Idioma principal:** Español
- **Descripción breve:** Reorganiza etiquetas de envío en hojas A4 de dos tercios para aprovechar papel reutilizado.

### Descripción detallada

Prepará etiquetas de envío para imprimir en hojas A4 cortadas a dos tercios. La extensión reacomoda dos etiquetas por hoja y deja libre el último tercio, para aprovechar papel reutilizado sin imprimir fuera del área disponible.

Cómo funciona:

1. Abrí el PDF de etiquetas en Chrome y hacé clic en la extensión: el PDF se procesa y descarga automáticamente.
2. Si preferís elegir un archivo, abrí el popup de la extensión y seleccioná o arrastrá el PDF.
3. Elegí si querés descartar, separar o anexar los documentos auxiliares.

Para convertir automáticamente un PDF local que ya tenés abierto, activá **Permitir acceso a URLs de archivos**: abrí `chrome://extensions`, buscá Etiquetas 2/3 A4, elegí **Detalles** y activá esa opción. Sin este permiso, igual podés seleccionar el PDF manualmente desde el popup.

Todo el procesamiento se realiza localmente en tu navegador. La extensión no envía PDFs, direcciones, códigos de barras ni datos de ventas a servidores externos.

Para imprimir, elegí tamaño A4, orientación original y escala 100 % o tamaño real.

## Recursos para subir

- `store-assets/listing-screenshot.png` — captura de pantalla 1280 × 800 px.
- `store-assets/how-it-works.png` — ilustración del PDF original y el PDF generado, 1280 × 800 px.
- `store-assets/promo-tile.png` — mosaico promocional 440 × 280 px.
- `store-assets/marquee-promo.png` — imagen promocional de marquesina 1400 × 560 px.
- `public/icons/icon-128.png` — ícono de la tienda 128 × 128 px.

## Declaración de privacidad para el panel

- **Propósito único:** Reorganizar localmente PDFs de etiquetas de envío para imprimir en papel A4 de dos tercios.
- **Datos recopilados:** Ninguno. Los PDFs y su contenido se procesan sólo en el dispositivo de la persona usuaria y no se transmiten.
- **Código remoto:** No se utiliza código remoto.

### Justificación de permisos

- **storage:** Guarda localmente la preferencia sobre documentos auxiliares.
- **tabs:** Detecta la pestaña activa únicamente para reconocer un PDF local abierto tras un clic explícito en la extensión.
- **downloads:** Guarda los PDFs generados en la carpeta de descargas elegida por la persona usuaria.
- **offscreen:** Procesa un PDF en segundo plano sin abrir una pestaña adicional.
- **file:///*:** Lee el PDF local que la persona usuaria abrió explícitamente, sólo cuando Chrome concede el acceso a archivos.

## Pendiente antes de enviar

1. Publicá `PRIVACY.md` en una URL HTTPS accesible públicamente e ingresala en el campo **Privacy policy** del panel.
2. Completá una URL o correo de soporte en la ficha de la tienda.
3. Subí `etiquetas-2-3-a4-1.0.0.zip` y los recursos indicados arriba.
