"""Qdrant 컬렉션 초기화"""
import os
from functools import lru_cache


COLLECTIONS = {
    "inbound_history": {
        "size": 1024,
        "description": "입고 이력 + 품질 결과 벡터 (BGE-M3)",
    },
    "outbound_history": {
        "size": 1024,
        "description": "출하 이력 + 클레임 벡터 (BGE-M3)",
    },
}


@lru_cache(maxsize=1)
def get_qdrant_client():
    """Qdrant 클라이언트 싱글톤"""
    from qdrant_client import QdrantClient

    return QdrantClient(
        host=os.getenv("QDRANT_HOST", "localhost"),
        port=int(os.getenv("QDRANT_PORT", "6333")),
    )


async def initialize_collections() -> None:
    """애플리케이션 시작 시 컬렉션 초기화"""
    try:
        from qdrant_client import QdrantClient
        from qdrant_client.models import Distance, VectorParams

        client = get_qdrant_client()
        existing = {c.name for c in client.get_collections().collections}

        for name, cfg in COLLECTIONS.items():
            if name not in existing:
                client.create_collection(
                    collection_name=name,
                    vectors_config=VectorParams(
                        size=cfg["size"],
                        distance=Distance.COSINE,
                    ),
                )
    except ImportError:
        pass  # qdrant-client 미설치 환경 — 무시
    except Exception:
        pass  # Qdrant 미기동 환경 — 무시 (런타임 오류는 실제 호출 시 처리)
