# Etiquetas 2/3 A4

Extensión de Chrome para reorganizar etiquetas de Mercado Libre —incluidas las etiquetas Full—, Gestionar, Correo Argentino y Vía Cargo y aprovechar hojas A4 cortadas a dos tercios. El procesamiento ocurre completamente en el navegador: las direcciones, códigos y PDFs no se envían a ningún servidor.

## Uso

1. Descargá y abrí el PDF de etiquetas.
2. Hacé clic en el ícono de la extensión para abrir el procesador.
3. Elegí o arrastrá uno o varios PDF descargados para agrupar sus etiquetas.
4. Elegí qué hacer con los listados de carrito y hojas de control.
5. Generá el PDF e imprimí las etiquetas con tamaño A4 y escala 100% / tamaño real.

Para convertir automáticamente un PDF local que ya está abierto en Chrome, activá **Permitir acceso a URLs de archivos** desde `chrome://extensions` → **Detalles** de la extensión. Sin ese permiso, podés seleccionar el PDF manualmente desde el popup.

Las etiquetas se colocan en los dos tercios derechos de cada A4. El último tercio queda vacío para que el papel reciclado de 2/3 A4 no intente imprimir fuera de la hoja.

## Datos y ejemplos privados

Los PDFs de etiquetas contienen direcciones y otros datos personales. No se incluyen en el repositorio: guardalos sólo en `private-pdfs/`, carpeta ignorada por Git. La extensión no carga ningún PDF a servidores externos.

La política de privacidad para la publicación está en [PRIVACY.md](PRIVACY.md).

## Instalar para pruebas

```bash
npm install
npm run build
```

En Chrome abrí `chrome://extensions`, activá **Modo de desarrollador**, elegí **Cargar descomprimida** y seleccioná la carpeta `dist` de este proyecto. Luego fijá el ícono de la extensión a la barra del navegador.

## Desarrollo

```bash
npm test
npm run build
```

Con los PDFs privados presentes en `private-pdfs/`, las pruebas integradas validan etiquetas individuales o múltiples, listados de carrito y una hoja de control de varias páginas. En un clon público sin esos PDFs, dichas pruebas se omiten de forma segura.

## Vía Cargo y varios archivos

La plantilla cuadrada de Vía Cargo (10 × 10 cm) se acomoda en dos filas y dos columnas: hasta cuatro etiquetas por hoja, dentro de los dos tercios derechos. Se reduce proporcionalmente a unos 9,2 cm de lado. El caso 8, con seis etiquetas, produce dos hojas.

Podés seleccionar varios PDF a la vez o arrastrarlos juntos. Se respeta el orden de la selección y de las páginas. Los otros formatos mantienen dos etiquetas por hoja; al cambiar de formato compacto a alto se inicia otra hoja. Para agrupar, usá los originales: si un archivo ya está adaptado o no contiene etiquetas compatibles, se informa cuál es y no se genera un lote incompleto.
