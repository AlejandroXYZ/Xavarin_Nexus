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
