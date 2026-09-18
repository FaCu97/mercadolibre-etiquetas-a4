# Etiquetas 2/3 A4

Extensión de Chrome para reorganizar etiquetas de Mercado Libre y aprovechar hojas A4 cortadas a dos tercios. El procesamiento ocurre completamente en el navegador: las direcciones, códigos y PDFs no se envían a ningún servidor.

## Uso

1. Descargá y abrí el PDF de Mercado Libre.
2. Hacé clic en el ícono de la extensión para abrir el procesador.
3. Elegí o arrastrá el PDF descargado.
4. Elegí qué hacer con los listados de carrito y hojas de control.
5. Generá el PDF e imprimí las etiquetas con tamaño A4 y escala 100% / tamaño real.

Para convertir automáticamente un PDF local que ya está abierto en Chrome, activá **Permitir acceso a URLs de archivos** desde `chrome://extensions` → **Detalles** de la extensión. Sin ese permiso, podés seleccionar el PDF manualmente desde el popup.

Las etiquetas se colocan en los primeros dos tercios de cada A4. El último tercio queda vacío para que el papel reciclado de 2/3 A4 no intente imprimir fuera de la hoja.

## Datos y ejemplos privados

Los PDFs descargados de Mercado Libre contienen direcciones y otros datos personales. No se incluyen en el repositorio: guardalos sólo en `private-pdfs/`, carpeta ignorada por Git. La extensión no carga ningún PDF a servidores externos.

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
