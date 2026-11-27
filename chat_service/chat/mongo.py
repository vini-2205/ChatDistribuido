import os
from datetime import datetime, timezone
from functools import lru_cache

from pymongo import MongoClient
from bson import ObjectId


@lru_cache(maxsize=1)
def obter_colecao():
    client = MongoClient(
        os.environ["MONGO_URL"],
        tz_aware=True,
        serverSelectionTimeoutMS=5000
    )

    db = client[
        os.getenv("MONGO_DB_NAME", "chat_messages")
    ]

    colecao = db["mensagens"]

    colecao.create_index([
        ("conversa_id", 1),
        ("enviada_em", -1),
        ("_id", -1)
    ])

    return colecao


def salvar(conversa_id, remetente, conteudo):
    documento = {
        "conversa_id": int(conversa_id),
        "remetente_id": int(remetente["id"]),
        "remetente_username": remetente["username"],
        "conteudo": conteudo,
        "enviada_em": datetime.now(timezone.utc)
    }

    obter_colecao().insert_one(documento)

    return documento


def serializar(documento):
    return {
        "id": str(documento["_id"]),
        "conversa_id": documento["conversa_id"],
        "remetente_id": documento["remetente_id"],
        "remetente_username": documento["remetente_username"],
        "conteudo": documento["conteudo"],
        "enviada_em": documento["enviada_em"].isoformat()
    }


def buscar_mensagens(conversa_id, antes=None, limite=50):
    colecao = obter_colecao()
    filtro = {"conversa_id": int(conversa_id)}

    if antes:
        referencia = colecao.find_one({
            "_id": ObjectId(antes),
            "conversa_id": int(conversa_id)
        })

        if referencia is None:
            return []

        filtro["$or"] = [
            {
                "enviada_em": {
                    "$lt": referencia["enviada_em"]
                }
            },
            {
                "enviada_em": referencia["enviada_em"],
                "_id": {"$lt": referencia["_id"]}
            }
        ]

    documentos = list(
        colecao.find(filtro)
        .sort([("enviada_em", -1), ("_id", -1)])
        .limit(limite)
    )

    return [
        serializar(doc)
        for doc in reversed(documentos)
    ]


def ultima_mensagem(conversa_id):
    documento = obter_colecao().find_one(
        {"conversa_id": int(conversa_id)},
        sort=[("enviada_em", -1), ("_id", -1)]
    )

    return serializar(documento) if documento else None