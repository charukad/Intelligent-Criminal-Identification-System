import os
from pathlib import Path

from src.services.ai.pipeline import FaceProcessingPipeline
from src.services.ai.strategies import (
    DEFAULT_EMBEDDING_VERSION,
    MTCNNStrategy,
    get_face_embedding_strategy,
    normalize_embedding_version,
)


ACTIVE_EMBEDDING_VERSION = normalize_embedding_version(
    os.getenv("FACE_EMBEDDING_VERSION", DEFAULT_EMBEDDING_VERSION)
)
_pipeline_cache: dict[tuple[str, str | None], FaceProcessingPipeline] = {}


# Load the detector once per process so recognition, enrollment, and migrations share it.
mtcnn = MTCNNStrategy()


def get_pipeline(
    embedding_version: str | None = None,
    *,
    model_path: str | Path | None = None,
) -> FaceProcessingPipeline:
    resolved_version = normalize_embedding_version(embedding_version or ACTIVE_EMBEDDING_VERSION)
    cache_key = (resolved_version, str(Path(model_path).resolve()) if model_path else None)
    cached_pipeline = _pipeline_cache.get(cache_key)
    if cached_pipeline is not None:
        return cached_pipeline

    embedder = get_face_embedding_strategy(
        resolved_version,
        model_path=model_path,
        device=getattr(mtcnn, "device", None),
    )
    face_pipeline = FaceProcessingPipeline(mtcnn, embedder)
    _pipeline_cache[cache_key] = face_pipeline
    return face_pipeline


pipeline = get_pipeline()
