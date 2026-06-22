import logging
from app.ia.groq_IA import groq
from app.services.message_utils.commands.prompt_factura import prompt
from app.clients.odoo_jsonrpc import ejecutar_odoo
import base64
import uuid
import os


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
        logger.info("Extrayendo historial de mensajes")
        mensajes = await db.fetch(
            f"""
        SELECT role,content FROM "{tenant_db}".messages WHERE platform_user_id = $1 AND platform = $2 AND role != 'system' ;
        """,
            platform_user_id,
            platform,
        )
        partner_id = await db.fetchval(
            f"""SELECT partner_id FROM "{tenant_db}".clients WHERE platform_user_id = $1 AND platform = $2;  """,
            platform_user_id,
            platform,
        )

        mensajes = [dict(fila) for fila in mensajes]
        logger.info("Inyectando System Prompt")
        mensajes.insert(0, prompt)
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
        return facturacion
    except Exception as e:
        logger.error(f"Ha ocurrido un error procesando el comando facturar, {e}")
        return {"status": "error", "info": "error procesando el comando /facturar"}


async def buscar_productos(db, productos: str | list, tenant_db: str):
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


async def procesar_venta_completa(
    tenant_data: dict,
    productos_a_comprar: list,
    http_client,
    tenant_db: str,
    partner_id: int,
):
    """
    Crea el pedido, confirma entrega (descuenta inventario físico en modo silencioso),
    genera factura, registra el pago y genera la URL pública del portal.
    """
    try:
        # 1. Formatear las líneas del pedido
        lineas_pedido = []
        for item in productos_a_comprar:
            lineas_pedido.append(
                (
                    0,
                    0,
                    {
                        "product_id": item["id_odoo"],
                        "product_uom_qty": item["cantidad"],
                    },
                )
            )

        logger.info("Creando Pedido de Venta en Odoo...")
        sale_order_id = await ejecutar_odoo(
            http_client=http_client,
            odoo_url=tenant_data["odoo_url"],
            db=tenant_db,
            uid=tenant_data["odoo_bot_user"],
            api_key=tenant_data["odoo_bot_api_key"],
            modelo="sale.order",
            metodo="create",
            args=[
                {
                    "partner_id": partner_id,
                    "order_line": lineas_pedido,
                }
            ],
        )

        if isinstance(sale_order_id, list):
            sale_order_id = sale_order_id[0]

        # 2. CONFIRMAR EL PEDIDO (Genera la orden de entrega y reserva stock)
        logger.info(f"Confirmando Pedido {sale_order_id} para reservar stock...")
        await ejecutar_odoo(
            http_client=http_client,
            odoo_url=tenant_data["odoo_url"],
            db=tenant_db,
            uid=tenant_data["odoo_bot_user"],
            api_key=tenant_data["odoo_bot_api_key"],
            modelo="sale.order",
            metodo="action_confirm",
            args=[[sale_order_id]],
        )

        # ==========================================
        # 3. VALIDAR ENTREGA (Descuento físico real con parche SMS)
        # ==========================================
        logger.info("Buscando órdenes de entrega asociadas al pedido...")
        pedido_entregas = await ejecutar_odoo(
            http_client=http_client,
            odoo_url=tenant_data["odoo_url"],
            db=tenant_db,
            uid=tenant_data["odoo_bot_user"],
            api_key=tenant_data["odoo_bot_api_key"],
            modelo="sale.order",
            metodo="read",
            args=[[sale_order_id]],
            kwargs={"fields": ["picking_ids"]},
        )

        picking_ids = (
            pedido_entregas[0].get("picking_ids", []) if pedido_entregas else []
        )

        if picking_ids:
            for picking_id in picking_ids:
                logger.info(f"Validando entrega {picking_id} en modo silencioso...")

                # EL FIX: Inyectamos "skip_sms" para que Odoo no intente crear el popup
                validacion_res = await ejecutar_odoo(
                    http_client=http_client,
                    odoo_url=tenant_data["odoo_url"],
                    db=tenant_db,
                    uid=tenant_data["odoo_bot_user"],
                    api_key=tenant_data["odoo_bot_api_key"],
                    modelo="stock.picking",
                    metodo="button_validate",
                    args=[[picking_id]],
                    kwargs={"context": {"skip_sms": True}},
                )

                # Si Odoo devuelve un asistente pidiendo confirmación de "Transferencia Inmediata"
                if (
                    isinstance(validacion_res, dict)
                    and validacion_res.get("res_model") == "stock.immediate.transfer"
                ):
                    logger.info(
                        "Forzando transferencia inmediata para descontar todo el stock..."
                    )

                    # Extraemos el contexto que devuelve Odoo y le volvemos a inyectar el skip_sms
                    ctx = validacion_res.get("context", {})
                    ctx["skip_sms"] = True

                    immediate_transfer_id = await ejecutar_odoo(
                        http_client=http_client,
                        odoo_url=tenant_data["odoo_url"],
                        db=tenant_db,
                        uid=tenant_data["odoo_bot_user"],
                        api_key=tenant_data["odoo_bot_api_key"],
                        modelo="stock.immediate.transfer",
                        metodo="create",
                        args=[{"pick_ids": [[4, picking_id]]}],
                        kwargs={"context": ctx},
                    )

                    if isinstance(immediate_transfer_id, list):
                        immediate_transfer_id = immediate_transfer_id[0]

                    await ejecutar_odoo(
                        http_client=http_client,
                        odoo_url=tenant_data["odoo_url"],
                        db=tenant_db,
                        uid=tenant_data["odoo_bot_user"],
                        api_key=tenant_data["odoo_bot_api_key"],
                        modelo="stock.immediate.transfer",
                        metodo="process",
                        args=[[immediate_transfer_id]],
                        kwargs={"context": ctx},
                    )
            logger.info(
                "¡Inventario físico descontado correctamente sin alertas de SMS!"
            )
        else:
            logger.warning(
                "No se generó entrega para este pedido (¿El producto es un servicio?)."
            )
        # ==========================================

        # 4. CREAR EL ASISTENTE DE FACTURACIÓN (WIZARD)
        logger.info("Abriendo asistente de facturación en Odoo...")
        wizard_id = await ejecutar_odoo(
            http_client=http_client,
            odoo_url=tenant_data["odoo_url"],
            db=tenant_db,
            uid=tenant_data["odoo_bot_user"],
            api_key=tenant_data["odoo_bot_api_key"],
            modelo="sale.advance.payment.inv",
            metodo="create",
            args=[
                {
                    "advance_payment_method": "delivered",
                }
            ],
            kwargs={
                "context": {
                    "active_model": "sale.order",
                    "active_ids": [sale_order_id],
                    "active_id": sale_order_id,
                }
            },
        )

        if isinstance(wizard_id, list):
            wizard_id = wizard_id[0]

        # 5. GENERAR LA FACTURA DESDE EL ASISTENTE
        logger.info("Generando Factura a partir del asistente...")
        await ejecutar_odoo(
            http_client=http_client,
            odoo_url=tenant_data["odoo_url"],
            db=tenant_db,
            uid=tenant_data["odoo_bot_user"],
            api_key=tenant_data["odoo_bot_api_key"],
            modelo="sale.advance.payment.inv",
            metodo="create_invoices",
            args=[[wizard_id]],
        )

        # 6. OBTENER EL ID DE LA FACTURA GENERADA
        logger.info("Buscando el ID de la factura generada...")
        pedido_actualizado = await ejecutar_odoo(
            http_client=http_client,
            odoo_url=tenant_data["odoo_url"],
            db=tenant_db,
            uid=tenant_data["odoo_bot_user"],
            api_key=tenant_data["odoo_bot_api_key"],
            modelo="sale.order",
            metodo="read",
            args=[[sale_order_id]],
            kwargs={"fields": ["invoice_ids"]},
        )

        factura_id = None
        if pedido_actualizado and pedido_actualizado[0].get("invoice_ids"):
            factura_id = pedido_actualizado[0]["invoice_ids"][0]

        # 7. PUBLICAR LA FACTURA (Validación Contable)
        if factura_id:
            await ejecutar_odoo(
                http_client=http_client,
                odoo_url=tenant_data["odoo_url"],
                db=tenant_db,
                uid=tenant_data["odoo_bot_user"],
                api_key=tenant_data["odoo_bot_api_key"],
                modelo="account.move",
                metodo="action_post",
                args=[[factura_id]],
            )
            logger.info(f"Factura {factura_id} publicada con éxito.")

            # REGISTRAR EL PAGO AUTOMÁTICAMENTE
            logger.info("Abriendo asistente de pago para conciliar la factura...")
            register_wizard_id = await ejecutar_odoo(
                http_client=http_client,
                odoo_url=tenant_data["odoo_url"],
                db=tenant_db,
                uid=tenant_data["odoo_bot_user"],
                api_key=tenant_data["odoo_bot_api_key"],
                modelo="account.payment.register",
                metodo="create",
                args=[{}],
                kwargs={
                    "context": {
                        "active_model": "account.move",
                        "active_ids": [factura_id],
                        "active_id": factura_id,
                    }
                },
            )

            if isinstance(register_wizard_id, list):
                register_wizard_id = register_wizard_id[0]

            logger.info("Confirmando el pago en Odoo...")
            await ejecutar_odoo(
                http_client=http_client,
                odoo_url=tenant_data["odoo_url"],
                db=tenant_db,
                uid=tenant_data["odoo_bot_user"],
                api_key=tenant_data["odoo_bot_api_key"],
                modelo="account.payment.register",
                metodo="action_create_payments",
                args=[[register_wizard_id]],
            )
            logger.info(f"Factura {factura_id} marcada exitosamente como PAGADA.")

            # MANEJO DEL ACCES_TOKEN Y URL MULTI-INQUILINO
            logger.info("Verificando token de acceso público...")
            factura_data = await ejecutar_odoo(
                http_client=http_client,
                odoo_url=tenant_data["odoo_url"],
                db=tenant_db,
                uid=tenant_data["odoo_bot_user"],
                api_key=tenant_data["odoo_bot_api_key"],
                modelo="account.move",
                metodo="read",
                args=[[factura_id]],
                kwargs={"fields": ["access_token"]},
            )

            token = factura_data[0].get("access_token") if factura_data else None

            if not token:
                logger.info("Inyectando token seguro...")
                token = str(uuid.uuid4())
                await ejecutar_odoo(
                    http_client=http_client,
                    odoo_url=tenant_data["odoo_url"],
                    db=tenant_db,
                    uid=tenant_data["odoo_bot_user"],
                    api_key=tenant_data["odoo_bot_api_key"],
                    modelo="account.move",
                    metodo="write",
                    args=[[factura_id], {"access_token": token}],
                )

            public_base_url = os.getenv(
                "ODOO_URL_PUBLIC", f"http://{tenant_db}.127.0.0.1.nip.io:8069"
            )

            base_url_limpia = public_base_url.rstrip("/")
            enlace_factura = (
                f"{base_url_limpia}/my/invoices/{factura_id}?access_token={token}"
            )

            logger.info(f"Enlace de autogestión pública generado: {enlace_factura}")

            return {
                "status": "success",
                "sale_order_id": sale_order_id,
                "invoice_id": factura_id,
                "invoice_url": enlace_factura,
            }

        else:
            logger.error("No se encontró ninguna factura asociada al pedido.")
            return {
                "status": "error",
                "info": "Fallo al enlazar la factura con el pedido",
            }

    except Exception as e:
        logger.error(f"Fallo crítico generando la venta en Odoo: {e}")
        raise e
