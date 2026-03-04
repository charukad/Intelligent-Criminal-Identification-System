from pydantic import BaseModel


class ModelVersionMetadata(BaseModel):
    version: str
    display_name: str
    family: str
    embedding_dimensions: int
    default_template_version: str
    notes: str | None = None


class ModelBenchmarkSummary(BaseModel):
    version: str
    display_name: str
    decision_status: str
    own_template_top1_rate: float | None = None
    match_far: float | None = None
    evaluated_image_count: int
    failed_image_count: int
    benchmark_report_path: str | None = None
    threshold_report_path: str | None = None
