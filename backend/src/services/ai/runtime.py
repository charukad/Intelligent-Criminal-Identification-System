from src.services.ai.pipeline import FaceProcessingPipeline
from src.services.ai.strategies import MTCNNStrategy, TraceNetStrategy

# Load the AI stack once per process so recognition and enrollment share it.
mtcnn = MTCNNStrategy()
tracenet = TraceNetStrategy()
pipeline = FaceProcessingPipeline(mtcnn, tracenet)
