import torch
import numpy as np
from PIL import Image
from typing import List, Tuple, cast
from facenet_pytorch import MTCNN, InceptionResnetV1

from src.services.ai.interfaces import FaceDetectionStrategy, FaceEmbeddingStrategy
from src.core.logging import logger

class MTCNNStrategy(FaceDetectionStrategy):
    def __init__(self, device: str = None):
        self.device = device or ('cuda' if torch.cuda.is_available() else 'cpu')
        # MPS support for Mac
        if not torch.cuda.is_available() and torch.backends.mps.is_available():
            self.device = 'mps'
            
        logger.info(f"Initializing MTCNN on device: {self.device}")
        self.mtcnn = MTCNN(
            keep_all=True, 
            device=self.device,
            min_face_size=40,
            thresholds=[0.6, 0.7, 0.7]
        )

    def detect_faces(self, image: np.ndarray) -> List[Tuple[int, int, int, int]]:
        """
        Expects RGB numpy array.
        """
        try:
            # Convert Numpy (OpenCV uses BGR usually, but let's assume RGB input or handle it)
            # Safe bet: Ensure PIL image
            pil_img = Image.fromarray(image)
            
            # Detect
            boxes, _ = self.mtcnn.detect(pil_img)
            
            if boxes is None:
                return []
                
            # Convert to list of integers
            result: List[Tuple[int, int, int, int]] = []
            for box in boxes:
                # box is [x1, y1, x2, y2]
                x1, y1, x2, y2 = [int(b) for b in box]
                w = x2 - x1
                h = y2 - y1
                result.append((x1, y1, w, h))
                
            return result
        except Exception as e:
            logger.error(f"MTCNN Detection Error: {e}")
            return []

class InceptionResnetStrategy(FaceEmbeddingStrategy):
    def __init__(self, device: str = None):
        self.device = device or ('cuda' if torch.cuda.is_available() else 'cpu')
        if not torch.cuda.is_available() and torch.backends.mps.is_available():
            self.device = 'mps'
            
        logger.info(f"Initializing FaceNet (InceptionResnetV1) on device: {self.device}")
        # Load pretrained on vggface2 (better for generic features)
        self.resnet = InceptionResnetV1(pretrained='vggface2').eval().to(self.device)

    def embed_face(self, face_image: np.ndarray) -> List[float]:
        """
        Expects a cropped, aligned face image (RGB).
        Resizes to 160x160 as required by InceptionResnetV1.
        """
        try:
            pil_img = Image.fromarray(face_image)
            
            # Preprocessing: Resize/Normalize
            # Note: InceptionResnetV1 expects fixed size (160x160 usually)
            pil_img = pil_img.resize((160, 160))
            
            # Convert to Tensor and Normalize
            # Standard normalization for this model is handled if we use their utilities, 
            # but doing it manually: [0,1] range then (x - mean) / std
            img_tensor = torch.from_numpy(np.array(pil_img)).float()
            img_tensor = img_tensor.permute(2, 0, 1) # HWC -> CHW
            
            # Whitening (Standardization)
            mean = img_tensor.mean()
            std = img_tensor.std()
            img_tensor = (img_tensor - mean) / std
            
            # Add batch dimension
            img_tensor = img_tensor.unsqueeze(0).to(self.device)
            
            # Inference
            with torch.no_grad():
                embedding = self.resnet(img_tensor)
                
            # Return as list
            return cast(List[float], embedding[0].cpu().numpy().tolist())

        except Exception as e:
            logger.error(f"FaceNet Embedding Error: {e}")
            raise e
