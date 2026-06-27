import logging
from app.ia.groq_IA import groq
from app.services.message_utils.commands.prompt_factura import prompt
from app.clients.odoo_jsonrpc import ejecutar_odoo
import uuid
import os
from typing import List, Dict, Any


logger = logging.getLogger(__name__)


async def procesar_factura(
    db,
    tenant_db: str,
    tenant_cache_data: dict,
    http_client,
    platform_user_id: str,
    platform: str,
):
    """Descuenta del inventario y genera factura para enviarsela al cliente"""

    try:
        logger.info("Extrayendo historial de mensajes en orden cronológico")
        mensajes = await db.fetch(
            f"""
            SELECT role, content 
            FROM "{tenant_db}".messages 
            WHERE platform_user_id = $1 AND platform = $2 AND role != 'system' 
            ORDER BY created_at ASC; 
            """,
            platform_user_id,
            platform,
        )

        partner_id = await db.fetchval(
            f"""SELECT partner_id FROM "{tenant_db}".clients WHERE platform_user_id = $1 AND platform = $2;  """,
            platform_user_id,
            platform,
        )

        prompt = tenant_cache_data["ai_system_prompt"]
        mensajes = [dict(fila) for fila in mensajes]

        logger.info("Inyectando System Prompt")
        mensajes.insert(0, {"role": "system", "content": prompt})

        logger.info(f"Enviando historial a Groq: {mensajes}")
        respuesta = await groq(mensajes)
        productos = respuesta.get("items", [])

        if not productos:
            return []

        productos_encontrados = await buscar_productos(
            db=db, tenant_db=tenant_db, productos=productos
        )

        facturacion = await procesar_venta_completa(
            tenant_data=tenant_cache_data,
            productos_a_comprar=productos_encontrados,
            http_client=http_client,
            tenant_db=tenant_db,
            partner_id=partner_id,
        )

        # --- NUEVA LÓGICA: MANEJO DE FALTA DE STOCK ---
        if (
            isinstance(facturacion, dict)
            and facturacion.get("status") == "out_of_stock"
        ):
            logger.warning("Venta detenida: No hay stock en Odoo. Avisando al dueño...")

            # Buscamos el canal de Odoo donde está hablando este cliente
            channel_id = await db.fetchval(
                f"""
                SELECT channel_id 
                FROM "{tenant_db}".messages 
                WHERE platform_user_id = $1 AND platform = $2 AND channel_id IS NOT NULL 
                ORDER BY created_at DESC LIMIT 1;
                """,
                platform_user_id,
                platform,
            )

            if channel_id:
                alerta_html = (
                    "<b>ALERTA DE VENTA FALLIDA:</b><br/>"
                    "<b>Motivo:</b> Ya no queda ese producto en el inventario"
                )
                await ejecutar_odoo(
                    http_client=http_client,
                    odoo_url=tenant_cache_data["odoo_url"],
                    db=tenant_db,
                    uid=tenant_cache_data["odoo_bot_user"],
                    api_key=tenant_cache_data["odoo_bot_api_key"],
                    modelo="discuss.channel",
                    metodo="message_post",
                    args=[channel_id],
                    kwargs={
                        "body": alerta_html,
                        "message_type": "comment",
                        "subtype_xmlid": "mail.mt_comment",
                        "body_is_html": True,
                    },
                )
            return {"status": "out_of_stock", "info": "Alerta enviada al dueño"}
        # ----------------------------------------------

        if facturacion and "error" not in str(facturacion).lower():
            logger.info(
                "Venta exitosa en Odoo. Descontando stock en base de datos local..."
            )

            valores_actualizacion = [
                (item["cantidad"], item["id_odoo"]) for item in productos_encontrados
            ]

            query_descuento = f"""
                UPDATE "{tenant_db}".catalog 
                SET stock = GREATEST(stock - $1, 0)
                WHERE id_odoo = $2;
            """

            await db.executemany(query_descuento, valores_actualizacion)
            logger.info("Stock local actualizado correctamente.")

        return facturacion

    except Exception as e:
        logger.error(f"Ha ocurrido un error procesando el comando facturar, {e}")
        return {"status": "error", "info": "error procesando el comando /facturar"}


async def buscar_productos(db, productos: str | list, tenant_db: str) -> list:
    """Busca productos en la tabla catalog"""
    try:
        # convierte texto a este formato: "%Camisa%"
        nombres_busqueda = [f"%{item['nombre_producto']}%" for item in productos]
        query = f"""
            SELECT id_odoo, name, price, stock 
            FROM "{tenant_db}".catalog 
            WHERE name ILIKE ANY($1::text[]);
        """
        resultados_db = await db.fetch(query, nombres_busqueda)

        productos_encontrados = []
        for fila in resultados_db:
            item_ia = next(
                (
                    p
                    for p in productos
                    if p["nombre_producto"].lower() in fila["name"].lower()
                ),
                None,
            )

            cantidad_solicitada = item_ia["cantidad"] if item_ia else 1

            productos_encontrados.append(
                {
                    "id_odoo": fila["id_odoo"],
                    "name": fila["name"],
                    "price": fila["price"],
                    "cantidad": cantidad_solicitada,
                }
            )

        return productos_encontrados

    except Exception as e:
        logger.error(
            f"Ha ocurrido un error mientras se buscaban los productos para factura: {e}"
        )
        return {
            "status": "error",
            "info": "error al buscar los productos en el inventario",
        }


def _obtener_ejecutor_odoo(tenant_data: dict, tenant_db: str, http_client):
    """Crea un acceso directo dinámico para evitar repetir las credenciales de Odoo."""

    async def runner(modelo: str, metodo: str, args: list = None, kwargs: dict = None):
        res = await ejecutar_odoo(
            http_client=http_client,
            odoo_url=tenant_data["odoo_url"],
            db=tenant_db,
            uid=tenant_data["odoo_bot_user"],
            api_key=tenant_data["odoo_bot_api_key"],
            modelo=modelo,
            metodo=metodo,
            args=args or [],
            kwargs=kwargs or {},
        )
        return (
            res[0]
            if isinstance(res, list) and len(res) == 1 and metodo in ("create", "write")
            else res
        )

    return runner


async def _crear_y_confirmar_pedido(
    run_odoo, partner_id: int, productos: List[dict]
) -> int:
    """Formatea las líneas, crea el Sale Order y lo confirma."""
    lineas_pedido = [
        (0, 0, {"product_id": p["id_odoo"], "product_uom_qty": p["cantidad"]})
        for p in productos
    ]

    logger.info("Creando Pedido de Venta en Odoo...")
    sale_order_id = await run_odoo(
        "sale.order",
        "create",
        [{"partner_id": partner_id, "order_line": lineas_pedido}],
    )
    if isinstance(sale_order_id, list):
        sale_order_id = sale_order_id[0]

    logger.info(f"Confirmando Pedido {sale_order_id} para reservar stock...")
    await run_odoo("sale.order", "action_confirm", [[sale_order_id]])
    return sale_order_id


async def _validar_entrega_silenciosa(run_odoo, sale_order_id: int):
    """Procesa las órdenes de entrega de stock"""
    logger.info("Buscando órdenes de entrega asociadas al pedido...")
    pedido_data = await run_odoo(
        "sale.order", "read", [[sale_order_id]], {"fields": ["picking_ids"]}
    )
    picking_ids = pedido_data[0].get("picking_ids", []) if pedido_data else []

    for picking_id in picking_ids:
        logger.info(f"Validando entrega {picking_id} en modo silencioso...")
        res = await run_odoo(
            "stock.picking",
            "button_validate",
            [[picking_id]],
            {"context": {"skip_sms": True}},
        )

        if isinstance(res, dict) and res.get("res_model") == "stock.immediate.transfer":
            logger.info(
                "Forzando transferencia inmediata para descontar todo el stock..."
            )
            ctx = res.get("context", {})
            ctx["skip_sms"] = True

            wizard_id = await run_odoo(
                "stock.immediate.transfer",
                "create",
                [{"pick_ids": [[4, picking_id]]}],
                {"context": ctx},
            )
            if isinstance(wizard_id, list):
                wizard_id = wizard_id[0]

            await run_odoo(
                "stock.immediate.transfer", "process", [[wizard_id]], {"context": ctx}
            )


async def _generar_y_publicar_factura(run_odoo, sale_order_id: int) -> int:
    """Paso 4, 5 y 6: Dispara el asistente de facturación y publica la factura."""
    logger.info("Abriendo asistente de facturación en Odoo...")
    wizard_id = await run_odoo(
        "sale.advance.payment.inv",
        "create",
        [{"advance_payment_method": "delivered"}],
        {
            "context": {
                "active_model": "sale.order",
                "active_ids": [sale_order_id],
                "active_id": sale_order_id,
            }
        },
    )
    if isinstance(wizard_id, list):
        wizard_id = wizard_id[0]

    logger.info("Generando Factura a partir del asistente...")
    await run_odoo("sale.advance.payment.inv", "create_invoices", [[wizard_id]])

    pedido_data = await run_odoo(
        "sale.order", "read", [[sale_order_id]], {"fields": ["invoice_ids"]}
    )
    return (
        pedido_data[0]["invoice_ids"][0]
        if pedido_data and pedido_data[0].get("invoice_ids")
        else None
    )


async def _registrar_pago_factura(run_odoo, factura_id: int):
    """Paso 7: Valida la factura contablemente y registra su pago completo."""
    await run_odoo("account.move", "action_post", [[factura_id]])
    logger.info(f"Factura {factura_id} publicada con éxito. Conciliando pago...")

    register_id = await run_odoo(
        "account.payment.register",
        "create",
        [{}],
        {
            "context": {
                "active_model": "account.move",
                "active_ids": [factura_id],
                "active_id": factura_id,
            }
        },
    )
    if isinstance(register_id, list):
        register_id = register_id[0]

    await run_odoo(
        "account.payment.register", "action_create_payments", [[register_id]]
    )
    logger.info(f"Factura {factura_id} marcada exitosamente como PAGADA.")


async def _garantizar_enlace_publico(run_odoo, factura_id: int, tenant_db: str) -> str:
    """Paso 8: Asegura el token de acceso público y formatea la URL final del portal."""
    factura_data = await run_odoo(
        "account.move", "read", [[factura_id]], {"fields": ["access_token"]}
    )
    token = factura_data[0].get("access_token") if factura_data else None

    if not token:
        logger.info("Inyectando token seguro...")
        token = str(uuid.uuid4())
        await run_odoo("account.move", "write", [[factura_id], {"access_token": token}])

    public_base_url = os.getenv("DOMAIN_NAME", "hola.com")

    public_base_url = f"https://{tenant_db}.{public_base_url}"
    return (
        f"{public_base_url.rstrip('/')}/my/invoices/{factura_id}?access_token={token}"
    )


async def procesar_venta_completa(
    tenant_data: dict,
    productos_a_comprar: list,
    http_client,
    tenant_db: str,
    partner_id: int,
) -> Dict[str, Any]:
    """
    Crea el pedido, confirma entrega (descuenta inventario físico en modo silencioso),
    genera factura, registra el pago y genera la URL pública del portal.
    """
    try:
        run_odoo = _obtener_ejecutor_odoo(tenant_data, tenant_db, http_client)

        sale_order_id = await _crear_y_confirmar_pedido(
            run_odoo, partner_id, productos_a_comprar
        )

        await _validar_entrega_silenciosa(run_odoo, sale_order_id)

        factura_id = await _generar_y_publicar_factura(run_odoo, sale_order_id)

        if not factura_id:
            logger.error("No se encontró ninguna factura asociada al pedido.")
            return {
                "status": "error",
                "info": "Fallo al enlazar la factura con el pedido",
            }

        await _registrar_pago_factura(run_odoo, factura_id)

        enlace_factura = await _garantizar_enlace_publico(
            run_odoo, factura_id, tenant_db
        )

        return {
            "status": "success",
            "sale_order_id": sale_order_id,
            "invoice_id": factura_id,
            "invoice_url": enlace_factura,
        }

    except Exception as e:
        error_texto = str(e)
        logger.error(f"Fallo generando la venta en Odoo: {error_texto}")

        if (
            "No se puede crear una factura" in error_texto
            or "artículos disponibles" in error_texto
        ):
            return {
                "status": "out_of_stock",
                "info": "Sin stock en Odoo para facturar.",
            }

        raise e
