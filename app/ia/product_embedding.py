from typing import Iterable
from fastembed import TextEmbedding
import logging
from app.ia.groq_IA import groq

logger = logging.getLogger(__name__)
model = TextEmbedding(
    model_name="sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
)


def vector(text: str | Iterable[str]):
    try:
        conversion = model.embed(text)
        return conversion
    except Exception as e:
        logger.error(
            f"Ha ocurrido un error mientras se convertian los productos a vectores: \n{e}\n"
        )
        raise e


async def product_embedding(db, product: str, message: str, tenant: str) -> str:
    """Encuentra 3 productos comparando el mensaje del cliente con los embeddings de los productos en el catálogo"""
    try:
        texto_a_buscar = product if product and len(product) >= 2 else message
        vector_cliente_lista = model.embed(texto_a_buscar)
        vector_ndarray = next(vector_cliente_lista)

        # Convierte la matriz de numpy a una lista python
        if vector_ndarray.ndim > 1:
            vector_cliente_lista = vector_ndarray[0].tolist()
        else:
            vector_cliente_lista = vector_ndarray.tolist()

        vector_cliente = f"[{','.join(map(str, vector_cliente_lista))}]"
        umbral_minimo = 0.30  # Umbral de distancia de coseno mínimo para que la IA reconozca los productos

        productos = await db.fetch(
            f"""
        SELECT name,description,price,stock, 1 - (embedding <=> $1::vector) as similitud
        FROM "{tenant}".catalog 
        WHERE 1 - (embedding <=> $1::vector) > $2 
        ORDER BY similitud 
        DESC LIMIT 3;
        """,
            vector_cliente,
            umbral_minimo,
        )
        logger.info(productos)
        respuesta = ""

        if len(productos) == 0 and not product:
            respuesta = "No se encontró ningún producto"
        else:
            for i in productos:
                respuesta += f"""Producto: {i["name"]}\nPrecio: {i["price"]}$\nDescripcion:{i["description"]}Cantidad Disponible: {i["stock"]}\n\n"""

        prompt_sistema = f"""
            Eres el mejor vendedor de la tienda. Tu objetivo es ayudar al cliente, responde de forma humana simple sin tantas preguntas, no parezcas un robot.
            
            A continuación se te da una lista de productos extraídos de nuestra base de datos
            basados en lo que el cliente pidió:
            
            [DATOS DEL CATÁLOGO]
            {respuesta}
            [Fin de los datos]
            
            REGLAS ESTRICTAS:
            1. Si la sección de datos dice 'NO SE ENCONTRARON PRODUCTOS o no hay', dile al cliente 
            amablemente que no vendemos ese tipo de artículos. No inventes productos.
            2. Si el producto aparece, pero 'cantidad_disponible' es 0, informa al cliente 
            que está agotado y ofrece una alternativa de la lista si hay otra.
            3. Nunca ofrezcas un precio distinto al que aparece en los datos.
            4. Responde de forma natural, concisa y persuasiva, sin que parezcas un robot.
            
            Debes de responder en formato JSON con este formato:
            'product':'<PRODUCTOS ENCONTRADOS>','intent':'ask','text':'<RESPUESTA>'
            """
        respuesta_IA = await groq(
            [
                {"role": "system", "content": prompt_sistema},
                {
                    "role": "user",
                    "content": f"Mensaje del cliente:{message}, encontrado en la DB: {respuesta}",
                },
            ]
        )
        logger.info(respuesta)
        return respuesta_IA

    except Exception as e:
        raise e
