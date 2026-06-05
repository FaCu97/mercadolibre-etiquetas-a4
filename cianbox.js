// ==UserScript==
// @name         Importador Automático - Cianbox
// @namespace    http://tampermonkey.net/
// @version      2.1
// @description  Inyección y automatización masiva de facturas desde JSON en Cianbox
// @author       Antigravity
// @match        *://*.cianbox.org/equipstore/*
// @match        *://cianbox.org/equipstore/*
// @grant        none
// ==/UserScript==

(function() {
    'use strict';

    const STORAGE_KEY = 'cola_facturacion_cianbox';
    const LOG_KEY = 'importador_cianbox_logs';
    const RUNNING_KEY = 'importador_cianbox_activo';

    // =============================================================================
    // 1. INYECCIÓN DE LA INTERFAZ FLOTANTE (CSS & HTML)
    // =============================================================================
    function inyectarInterfaz() {
        if (document.getElementById('importador-cianbox-root')) return;

        // Estilos base
        const style = document.createElement('style');
        style.innerHTML = `
            #importador-cianbox-root {
                position: fixed;
                bottom: 20px;
                right: 20px;
                width: 350px;
                background: rgba(26, 26, 26, 0.95);
                backdrop-filter: blur(10px);
                color: #e0e0e0;
                border: 1px solid rgba(255, 255, 255, 0.1);
                border-radius: 14px;
                box-shadow: 0 10px 40px rgba(0, 0, 0, 0.6);
                font-family: 'Segoe UI', -apple-system, BlinkMacSystemFont, Roboto, sans-serif;
                z-index: 999999;
                display: flex;
                flex-direction: column;
                overflow: hidden;
                font-size: 13px;
                transition: height 0.3s ease;
            }
            .imp-header {
                padding: 12px 16px;
                background: rgba(255, 255, 255, 0.03);
                border-bottom: 1px solid rgba(255, 255, 255, 0.08);
                display: flex;
                justify-content: space-between;
                align-items: center;
                font-weight: 600;
                color: #fff;
            }
            .imp-body {
                padding: 16px;
                display: flex;
                flex-direction: column;
                gap: 12px;
            }
            .imp-textarea {
                width: 100%;
                height: 120px;
                background: rgba(0, 0, 0, 0.3);
                border: 1px solid rgba(255, 255, 255, 0.15);
                border-radius: 6px;
                color: #fff;
                font-family: monospace;
                font-size: 11px;
                padding: 8px;
                resize: none;
                box-sizing: border-box;
            }
            .imp-textarea:focus {
                outline: none;
                border-color: #4f46e5;
            }
            .imp-btn {
                background: #4f46e5;
                color: #fff;
                border: none;
                padding: 8px 16px;
                border-radius: 6px;
                cursor: pointer;
                font-weight: 600;
                transition: background 0.2s;
                display: flex;
                justify-content: center;
                align-items: center;
                gap: 6px;
            }
            .imp-btn:hover { background: #4338ca; }
            .imp-btn.danger {
                background: #dc2626;
            }
            .imp-btn.danger:hover { background: #b91c1c; }
            .imp-progress-container {
                display: none;
                flex-direction: column;
                gap: 6px;
            }
            .imp-progress-bar-bg {
                width: 100%;
                height: 6px;
                background: rgba(255, 255, 255, 0.1);
                border-radius: 3px;
                overflow: hidden;
            }
            .imp-progress-bar-fill {
                height: 100%;
                width: 0%;
                background: #10b981;
                transition: width 0.3s ease;
            }
            .imp-log-title {
                font-weight: 600;
                font-size: 11px;
                text-transform: uppercase;
                color: #9ca3af;
                margin-top: 4px;
            }
            .imp-logs {
                height: 100px;
                background: rgba(0, 0, 0, 0.4);
                border: 1px solid rgba(255, 255, 255, 0.08);
                border-radius: 6px;
                padding: 6px 10px;
                overflow-y: auto;
                font-family: monospace;
                font-size: 11px;
                color: #a7f3d0;
                display: flex;
                flex-direction: column;
                gap: 4px;
                box-sizing: border-box;
            }
            .imp-log-entry {
                line-height: 1.4;
                word-break: break-all;
            }
            .imp-log-entry.error { color: #f87171; }
            .imp-log-entry.warn { color: #fbbf24; }
            .imp-log-entry.info { color: #60a5fa; }
        `;
        document.head.appendChild(style);

        // Crear elemento root
        const root = document.createElement('div');
        root.id = 'importador-cianbox-root';
        root.innerHTML = `
            <div class="imp-header">
                <span>🤖 Importador Cianbox</span>
                <span id="imp-status" style="font-size: 11px; color: #10b981;">Listo</span>
            </div>
            <div class="imp-body">
                <div id="imp-setup-view">
                    <div style="margin-bottom: 8px; font-weight: 500;">Pega el lote de facturas JSON:</div>
                    <textarea class="imp-textarea" id="imp-json-input" placeholder='[ { "cabecera": {...}, "productos": [...] }, ... ]'></textarea>
                    <button class="imp-btn" id="imp-start-btn" style="margin-top: 10px; width: 100%;">
                        🚀 Iniciar Importación
                    </button>
                </div>
                <div id="imp-run-view" style="display: none; flex-direction: column; gap: 10px;">
                    <div class="imp-progress-container" id="imp-progress-box" style="display: flex;">
                        <div style="display: flex; justify-content: space-between; font-weight: 500;">
                            <span>Progreso de Carga</span>
                            <span id="imp-progress-text">0/0</span>
                        </div>
                        <div class="imp-progress-bar-bg">
                            <div class="imp-progress-bar-fill" id="imp-progress-fill"></div>
                        </div>
                    </div>
                    <div class="imp-log-title">Registro de ejecución</div>
                    <div class="imp-logs" id="imp-logs-box"></div>
                    <button class="imp-btn danger" id="imp-stop-btn" style="width: 100%;">
                        🛑 Detener Proceso
                    </button>
                </div>
            </div>
        `;
        document.body.appendChild(root);

        // Asignar listeners
        document.getElementById('imp-start-btn').addEventListener('click', iniciarCargaNueva);
        document.getElementById('imp-stop-btn').addEventListener('click', detenerCarga);
    }

    // =============================================================================
    // 2. LOGGING Y CONTROL DE INTERFAZ
    // =============================================================================
    function log(mensaje, tipo = 'normal') {
        console.log(`[Importador] ${mensaje}`);
        const box = document.getElementById('imp-logs-box');
        if (!box) return;

        const date = new Date();
        const timeStr = `${date.getHours().toString().padStart(2, '0')}:${date.getMinutes().toString().padStart(2, '0')}:${date.getSeconds().toString().padStart(2, '0')}`;
        
        const entry = document.createElement('div');
        entry.className = `imp-log-entry ${tipo}`;
        entry.textContent = `[${timeStr}] ${mensaje}`;
        box.appendChild(entry);
        box.scrollTop = box.scrollHeight;

        // Persistir logs
        let savedLogs = JSON.parse(localStorage.getItem(LOG_KEY) || '[]');
        savedLogs.push({ time: timeStr, text: mensaje, type: tipo });
        if (savedLogs.length > 50) savedLogs.shift();
        localStorage.setItem(LOG_KEY, JSON.stringify(savedLogs));
    }

    function cargarLogsPersistidos() {
        const box = document.getElementById('imp-logs-box');
        if (!box) return;
        
        const savedLogs = JSON.parse(localStorage.getItem(LOG_KEY) || '[]');
        box.innerHTML = '';
        savedLogs.forEach(l => {
            const entry = document.createElement('div');
            entry.className = `imp-log-entry ${l.type}`;
            entry.textContent = `[${l.time}] ${l.text}`;
            box.appendChild(entry);
        });
        box.scrollTop = box.scrollHeight;
    }

    function actualizarProgreso(actual, total) {
        const txt = document.getElementById('imp-progress-text');
        const fill = document.getElementById('imp-progress-fill');
        if (txt && fill) {
            txt.textContent = `${actual}/${total}`;
            const pct = total > 0 ? (actual / total) * 100 : 0;
            fill.style.width = `${pct}%`;
        }
    }

    // =============================================================================
    // 3. LOGICA DE CONTROL DE LA COLA
    // =============================================================================
    function iniciarCargaNueva() {
        const input = document.getElementById('imp-json-input').value.trim();
        if (!input) {
            alert("Por favor, pega un lote JSON válido.");
            return;
        }

        try {
            const lote = JSON.parse(input);
            if (!Array.isArray(lote)) {
                alert("El lote debe ser un array JSON de facturas.");
                return;
            }

            localStorage.setItem(STORAGE_KEY, JSON.stringify(lote));
            localStorage.setItem(RUNNING_KEY, 'true');
            localStorage.setItem(LOG_KEY, '[]'); // reset logs
            
            log(`Lote cargado con ${lote.length} comprobantes.`, 'info');
            
            // Cambiar a vista ejecucion
            document.getElementById('imp-setup-view').style.display = 'none';
            document.getElementById('imp-run-view').style.display = 'flex';
            document.getElementById('imp-status').textContent = 'Ejecutando';
            document.getElementById('imp-status').style.color = '#34d399';

            ejecutarCiclo();
        } catch (e) {
            alert(`Error al parsear el JSON: ${e.message}`);
        }
    }

    function detenerCarga() {
        localStorage.setItem(RUNNING_KEY, 'false');
        localStorage.removeItem(STORAGE_KEY);
        log("Carga masiva cancelada y cola vaciada.", 'warn');
        
        document.getElementById('imp-setup-view').style.display = 'block';
        document.getElementById('imp-run-view').style.display = 'none';
        document.getElementById('imp-status').textContent = 'Listo';
        document.getElementById('imp-status').style.color = '#10b981';
    }

    // =============================================================================
    // 4. MOTOR AUTOMÁTICO DE ENTRADA DE DATOS
    // =============================================================================
    async function ejecutarCiclo() {
        const activo = localStorage.getItem(RUNNING_KEY) === 'true';
        if (!activo) return;

        let cola = JSON.parse(localStorage.getItem(STORAGE_KEY) || '[]');
        if (cola.length === 0) {
            log("✨ Proceso terminado. No quedan facturas en la cola.", 'info');
            detenerCarga();
            return;
        }

        // Cargar vista ejecucion si estaba recargado
        document.getElementById('imp-setup-view').style.display = 'none';
        document.getElementById('imp-run-view').style.display = 'flex';
        document.getElementById('imp-status').textContent = 'Ejecutando';
        document.getElementById('imp-status').style.color = '#34d399';

        const totalOriginal = JSON.parse(localStorage.getItem(STORAGE_KEY + '_total') || '0');
        const totalActual = cola.length;
        const totalInicial = totalOriginal > totalActual ? totalOriginal : totalActual;
        if (totalInicial > totalOriginal) {
            localStorage.setItem(STORAGE_KEY + '_total', totalInicial.toString());
        }
        
        const completadas = totalInicial - totalActual;
        actualizarProgreso(completadas, totalInicial);

        const factura = cola[0];
        log(`Procesando factura: ${factura.cabecera.numero} (${factura.cabecera.proveedor})`, 'info');

        try {
            // 1. Cargar Cabecera
            await cargarCabecera(factura.cabecera);
            
            // 2. Cargar Productos
            for (let idx = 0; idx < factura.productos.length; idx++) {
                const prod = factura.productos[idx];
                await cargarProducto(prod, idx + 1, factura.productos.length);
                await new Promise(r => setTimeout(r, 600)); // Pausa breve entre items
            }

            // 2.5. Cargar Percepciones
            if (factura.cabecera.percepciones_iibb && factura.cabecera.percepciones_iibb.length > 0) {
                await cargarPercepciones(factura.cabecera.percepciones_iibb);
            }

            // 3. Quitar de la cola
            cola.shift();
            localStorage.setItem(STORAGE_KEY, JSON.stringify(cola));
            log("💾 Fila procesada de forma local. Enviando...", 'info');

            // 4. Click guardar
            await new Promise(r => setTimeout(r, 600));
            const btnSubmit = document.querySelector('input.button.send.continue[value="Aceptar y Nueva"]');
            if (btnSubmit) {
                log("🚀 Guardando factura...", 'info');
                btnSubmit.click();
            } else {
                log("❌ No se encontró el botón 'Aceptar y Nueva' de guardado.", 'error');
                // Devolvemos a la cola
                cola.unshift(factura);
                localStorage.setItem(STORAGE_KEY, JSON.stringify(cola));
                localStorage.setItem(RUNNING_KEY, 'false');
            }

        } catch (e) {
            log(`Fallo en factura ${factura.cabecera.numero}: ${e.message}`, 'error');
            localStorage.setItem(RUNNING_KEY, 'false');
            document.getElementById('imp-status').textContent = 'PAUSADO POR ERROR';
            document.getElementById('imp-status').style.color = '#f87171';
        }
    }

    // =============================================================================
    // 5. MÉTODOS DE FORMULARIO (INYECTORES DOM)
    // =============================================================================
    async function cargarCabecera(datos) {
        log("Cargando campos de cabecera...");
        
        // Campos de texto simples
        let inputFecha = document.querySelector('input[name="fecha_comprobante"]');
        if (inputFecha) inputFecha.value = datos.fecha;
        
        let inputPV = document.querySelector('input[name="punto_venta"]');
        if (inputPV) inputPV.value = datos.pv || datos.puntoVenta;
        
        let inputNum = document.querySelector('input[name="numero"]');
        if (inputNum) inputNum.value = datos.numero;

        // Select Tipo de Comprobante
        const MAPEO_COMPROBANTES = { "FACTURA": "1", "NOTA DE CREDITO": "5", "NOTA DE DEBITO": "6", "REMITO": "7" };
        let selectTipo = document.querySelector('select[name="id_comprobante"]');
        if (selectTipo && datos.tipo) {
            const valTipo = MAPEO_COMPROBANTES[datos.tipo.toUpperCase()] || "1";
            selectTipo.value = valTipo;
            selectTipo.dispatchEvent(new Event('change', { bubbles: true }));
            log(`📋 Tipo Comprobante seleccionado: ${datos.tipo} (ID ${valTipo})`);
        }

        // Select Letra
        const MAPEO_LETRAS = { "A": "1", "B": "2", "C": "3", "M": "4", "E": "8" };
        let selectLetra = document.querySelector('select[name="id_tipo"]');
        if (selectLetra && datos.letra) {
            const valLetra = MAPEO_LETRAS[datos.letra.toUpperCase()] || "1";
            selectLetra.value = valLetra;
            selectLetra.dispatchEvent(new Event('change', { bubbles: true }));
            log(`📋 Letra seleccionada: ${datos.letra} (ID ${valLetra})`);
        }

        // Control de Stock
        let selectStock = document.querySelector('select[name="recibida"]');
        if (selectStock) {
            const mueveStock = datos.mueve_stock !== false;
            selectStock.value = mueveStock ? "toda_sr" : "no_stock";
            selectStock.dispatchEvent(new Event('change', { bubbles: true }));
            log(`📦 Control de Stock: ${mueveStock ? 'MUEVE STOCK (toda_sr)' : 'NO MUEVE STOCK (no_stock)'}`);
        }

        // Búsqueda de proveedor vía AJAX
        const queryProv = datos.proveedor;
        log(`Buscando ID de proveedor: "${queryProv}"...`);
        
        const response = await fetch("/equipstore/modules/pv_proveedores/acomplete.php", {
            headers: { 'content-type': 'application/x-www-form-urlencoded; charset=UTF-8', 'x-requested-with': 'XMLHttpRequest' },
            body: "userlevel=1&userid=5&rrhh=1&sec=pv_compras&box=alta&bsearch=" + encodeURIComponent(queryProv),
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
                inputVisual.value = data.nombre || data.razon_social || queryProv;
                inputVisual.dispatchEvent(new Event('input', { bubbles: true }));
            }
            log(`✅ Proveedor asignado ID: ${data.id}`);
        } else {
            log(`⚠️ Proveedor "${queryProv}" no encontrado en el sistema.`, 'warn');
        }
    }

    async function cargarProducto(datos, index, total) {
        log(`Cargando item ${index}/${total} [Cód: ${datos.codigo}]...`);
        
        const response = await fetch("/equipstore/modules/pv_productos/acomplete.php", {
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
        
        let idFinal = data ? data.id : "0";
        let nombreFinal = data ? data.nombre : datos.codigo;

        if (idFinal === "0") {
            log(`⚠️ Cód. "${datos.codigo}" no coincide exacto. Se inyecta como texto genérico.`, 'warn');
        }

        // Llenar inputs de productos
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
            inputDesc.value = datos.descuento || "0,00";
            inputDesc.dispatchEvent(new Event('change', { bubbles: true }));
        }

        let inputCant = document.querySelector('input[name="add_cantidad"]');
        if (inputCant) inputCant.value = datos.cantidad;

        // Click agregar item
        await new Promise(r => setTimeout(r, 100));
        let btnAdd = document.getElementById('add_producto');
        if (btnAdd) btnAdd.click();
    }

    async function cargarPercepciones(percepciones) {
        log("⚖️ Cargando Percepciones...");
        
        const tab = document.querySelector("a[rel='percepcion']");
        if (tab) {
            tab.click();
            await new Promise(r => setTimeout(r, 600));
        } else {
            log("❌ No se encontró la pestaña de Percepciones.", "error");
            return;
        }

        const MAPEO_PROVINCIAS = {
            "Capital Federal": "2", "Ciudad de Buenos Aires": "2", "C.A.B.A.": "2",
            "Santa Fe": "3", "Córdoba": "4", "Tucuman": "6", "Misiones": "7",
            "Corrientes": "9", "Mendoza": "12", "Buenos Aires": "23", "Provincia de Buenos Aires": "23"
        };

        for (const perc of percepciones) {
            const idProv = MAPEO_PROVINCIAS[perc.jurisdiccion] || "23";
            log(`📍 Cargando percepción IIBB ${perc.jurisdiccion} (ID ${idProv}): $${perc.monto}`);

            let selectProv = document.querySelector('select[name="add_percepcion"]');
            if (selectProv) {
                selectProv.value = idProv;
                selectProv.dispatchEvent(new Event('change', { bubbles: true }));
            }

            let inputMonto = document.querySelector('input[name="add_monto"]');
            if (inputMonto) {
                inputMonto.value = perc.monto.replace(/\./g, "");
                inputMonto.dispatchEvent(new Event('change', { bubbles: true }));
            }

            await new Promise(r => setTimeout(r, 200));
            
            let btnAdd = document.getElementById('add_impuesto');
            if (btnAdd) btnAdd.click();
            
            await new Promise(r => setTimeout(r, 500));
        }
    }

    // =============================================================================
    // 6. INICIALIZADOR DE PÁGINA
    // =============================================================================
    function iniciar() {
        inyectarInterfaz();
        cargarLogsPersistidos();

        const activo = localStorage.getItem(RUNNING_KEY) === 'true';
        if (activo) {
            ejecutarCiclo();
        } else {
            // Verificar si hay cola residual
            let cola = JSON.parse(localStorage.getItem(STORAGE_KEY) || '[]');
            if (cola.length > 0) {
                // Restaurar vista de ejecución pausada
                document.getElementById('imp-setup-view').style.display = 'none';
                document.getElementById('imp-run-view').style.display = 'flex';
                document.getElementById('imp-status').textContent = 'Pausado';
                document.getElementById('imp-status').style.color = '#fbbf24';
                
                const totalOriginal = parseInt(localStorage.getItem(STORAGE_KEY + '_total') || cola.length.toString(), 10);
                actualizarProgreso(totalOriginal - cola.length, totalOriginal);
            }
        }
    }

    // Ejecutar cuando el DOM esté listo
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', iniciar);
    } else {
        iniciar();
    }

})();