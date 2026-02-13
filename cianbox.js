// =============================================================================
// 1. TU LOTE DE FACTURAS (Pegá acá toda tu lista)
// =============================================================================
const LOTE_DE_FACTURAS = [
    {
        cabecera: { proveedor: "ABC ACCES", fecha: "10/02/2026", pv: "0005", numero: "00000001" },
        productos: [
            { codigo: "6275", precio: "1500,00", iva: "1.2100", descuento: "10,00", cantidad: "1" },
            { codigo: "6276", precio: "2500,50", iva: "1.1050", descuento: "0,00", cantidad: "2" }
        ]
    },
    {
        cabecera: { proveedor: "PROVEEDOR_2", fecha: "11/02/2026", pv: "0005", numero: "00000002" },
        productos: [
            { codigo: "8888", precio: "100,00", iva: "1.2100", descuento: "0,00", cantidad: "10" }
        ]
    }
    // ... Agregá todas las que quieras
];

// =============================================================================
// 2. MOTOR DE PROCESAMIENTO (NO TOCAR)
// =============================================================================

async function iniciarSistema() {
    console.clear();
    const STORAGE_KEY = 'cola_facturacion_cianbox';
    
    // A. GESTIÓN DE LA COLA
    let cola = JSON.parse(localStorage.getItem(STORAGE_KEY));

    // Si no hay cola, o la cola está vacía, cargamos el lote nuevo
    if (!cola || cola.length === 0) {
        // ¿Es la primera vez? Cargamos el lote definido arriba
        if (confirm(`¿Iniciar carga de ${LOTE_DE_FACTURAS.length} facturas nuevas?`)) {
            localStorage.setItem(STORAGE_KEY, JSON.stringify(LOTE_DE_FACTURAS));
            cola = LOTE_DE_FACTURAS;
            console.log("📥 Lote cargado en memoria. Iniciando...");
        } else {
            console.log("🛑 Cancelado por el usuario.");
            return;
        }
    } else {
        console.log(`🔄 Retomando trabajo... Quedan ${cola.length} facturas.`);
    }

    // B. TOMAR LA SIGUIENTE FACTURA
    const facturaActual = cola[0]; // Siempre tomamos la primera
    console.log(`⚡ PROCESANDO FACTURA: ${facturaActual.cabecera.numero} (${facturaActual.cabecera.proveedor})`);

    try {
        // 1. CARGAR CABECERA
        await cargarCabecera(facturaActual.cabecera);
        
        // 2. CARGAR PRODUCTOS (Uno por uno)
        for (const producto of facturaActual.productos) {
            await cargarProducto(producto);
            // Pequeña pausa entre productos para no saturar
            await new Promise(r => setTimeout(r, 1000));
        }

        // 3. ELIMINAR DE LA COLA (Antes de enviar, para que al recargar tome la siguiente)
        cola.shift(); // Borra el primer elemento
        localStorage.setItem(STORAGE_KEY, JSON.stringify(cola));
        console.log("💾 Cola actualizada. Listo para el siguiente ciclo.");

        // 4. CLICK EN "ACEPTAR Y NUEVA"
        console.log("🚀 ENVIANDO FACTURA...");
        await new Promise(r => setTimeout(r, 1000)); // Pausa dramática final
        
        const btnSubmit = document.querySelector('input.button.send.continue[value="Aceptar y Nueva"]');
        if (btnSubmit) {
            btnSubmit.click();
            console.log("✅ Formulario enviado. Esperando recarga...");
        } else {
            console.error("❌ NO ENCONTRÉ EL BOTÓN DE ENVIAR.");
            // Si falla el botón, devolvemos la factura a la cola para no perderla
            cola.unshift(facturaActual);
            localStorage.setItem(STORAGE_KEY, JSON.stringify(cola));
        }

    } catch (e) {
        console.error("🔥 Error fatal en esta factura:", e);
        alert("Hubo un error. El proceso se detuvo. Revisá la consola.");
    }
}

// --- FUNCIONES AUXILIARES (Tus herramientas probadas) ---

async function cargarCabecera(datos) {
    console.log("📝 Cargando Cabecera...");
    // 1. CAMPOS SIMPLES
    let inputFecha = document.querySelector('input[name="fecha_comprobante"]');
    if (inputFecha) inputFecha.value = datos.fecha;
    
    let inputPV = document.querySelector('input[name="punto_venta"]');
    if (inputPV) inputPV.value = datos.pv;
    
    let inputNum = document.querySelector('input[name="numero"]');
    if (inputNum) inputNum.value = datos.numero;

    // 2. PROVEEDOR (Fetch + Inyección)
    const response = await fetch("https://cianbox.org/equipstore/modules/pv_proveedores/acomplete.php", {
        headers: { 'content-type': 'application/x-www-form-urlencoded; charset=UTF-8', 'x-requested-with': 'XMLHttpRequest' },
        body: "userlevel=1&userid=5&rrhh=1&sec=pv_compras&box=alta&bsearch=" + encodeURIComponent(datos.proveedor),
        method: "POST",
        credentials: "include"
    });
    const html = await response.text();
    const div = document.createElement('div');
    div.innerHTML = html;
    const fila = div.querySelector('tr[rel]');
    
    if (fila) {
        const data = JSON.parse(fila.getAttribute('rel').replace(/&quot;/g, '"'));
        
        let inputId = document.querySelector('input[name="id_proveedor"]') || document.querySelector('input[type="hidden"][name*="id_prov"]');
        if (inputId) inputId.value = data.id;

        let inputVisual = document.querySelector('input[autocomplete="no_auto"].fc.required');
        if (inputVisual) {
            inputVisual.value = data.nombre || data.razon_social || datos.proveedor;
            inputVisual.dispatchEvent(new Event('input', { bubbles: true }));
        }
        console.log("   ✅ Proveedor OK");
    } else {
        console.warn("   ⚠️ Proveedor no encontrado.");
    }
}

async function cargarProducto(datos) {
    console.log(`   📦 Item: ${datos.codigo}`);
    const response = await fetch("https://cianbox.org/equipstore/modules/pv_productos/acomplete.php", {
        headers: { 'content-type': 'application/x-www-form-urlencoded; charset=UTF-8', 'x-requested-with': 'XMLHttpRequest' },
        body: "id_usuario=5&incluye_insumos=1&cotizaciones%5B1%5D=1&cotizaciones%5B2%5D=1000&id_moneda=1&cotizacion=1&userid=5&userlevel=1&sec=pv_compras&box=alta&bsearch=" + encodeURIComponent(datos.codigo),
        method: "POST",
        credentials: "include"
    });
    
    const html = await response.text();
    let data = null;
    const match = html.match(/rel="([^"]+)"/) || html.match(/rel='([^']+)'/);
    if (match && match[1]) {
        try { data = JSON.parse(match[1].replace(/&quot;/g, '"')); } catch(e){}
    }
    
    // Valores
    let idFinal = data ? data.id : "0";
    let nombreFinal = data ? data.nombre : datos.codigo;

    // Llenar
    let inputId = document.querySelector('input[name="add_id_producto"]');
    if (inputId) inputId.value = idFinal;

    let inputNombre = document.querySelector('.box_main_field');
    if (inputNombre) {
        inputNombre.value = nombreFinal;
        inputNombre.dispatchEvent(new Event('input', { bubbles: true }));
    }

    let inputPrecio = document.querySelector('input[name="add_precio_unitario"]');
    if (inputPrecio) {
        inputPrecio.value = datos.precio;
        inputPrecio.dispatchEvent(new Event('change', { bubbles: true }));
    }

    let selectIva = document.querySelector('select[name="add_alicuota_iva"]');
    if (selectIva) {
        selectIva.value = datos.iva;
        selectIva.dispatchEvent(new Event('change', { bubbles: true }));
    }
    
    let inputDesc = document.querySelector('input[name="add_desc"]');
    if (inputDesc) {
        inputDesc.value = datos.descuento;
        inputDesc.dispatchEvent(new Event('change', { bubbles: true }));
    }

    let inputCant = document.querySelector('input[name="add_cantidad"]');
    if (inputCant) inputCant.value = datos.cantidad;

    // Click Agregar
    await new Promise(r => setTimeout(r, 300));
    let btnAdd = document.getElementById('add_producto');
    if (btnAdd) btnAdd.click();
}

// ARRANCA
iniciarSistema();

// Todavia no carga todas las facturas juntas