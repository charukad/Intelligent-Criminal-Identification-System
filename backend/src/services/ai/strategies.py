import os
from pathlib import Path

import torch
import torch.nn.functional as F
import numpy as np
from PIL import Image
from typing import List, Tuple, cast
from torchvision import transforms
from facenet_pytorch import MTCNN, InceptionResnetV1

from src.services.ai.interfaces import FaceDetectionStrategy, FaceEmbeddingStrategy
from src.services.ai.tracenet_model import TraceNet
from src.core.logging import logger

# Default path to the trained TraceNet checkpoint
_MODELS_DIR = Path(__file__).resolve().parents[3] / "models"
DEFAULT_TRACENET_PATH = _MODELS_DIR / "TraceNet_deployment.pth"


class MTCNNStrategy(FaceDetectionStrategy):
    """Face detection using MTCNN from facenet-pytorch."""

    def __init__(self, device: str | None = None) -> None:
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
        """Detect faces in an RGB numpy array.

        Returns:
            List of bounding boxes as (x, y, w, h) tuples.
        """
        try:
            pil_img = Image.fromarray(image)
            boxes, _ = self.mtcnn.detect(pil_img)
            
            if boxes is None:
                return []
                
            result: List[Tuple[int, int, int, int]] = []
            for box in boxes:
                x1, y1, x2, y2 = [int(b) for b in box]
                w = x2 - x1
                h = y2 - y1
                result.append((x1, y1, w, h))
                
            return result
        except Exception as e:
            logger.error(f"MTCNN Detection Error: {e}")
            raise RuntimeError(f"MTCNN Face Detection failed: {e}") from e


class InceptionResnetStrategy(FaceEmbeddingStrategy):
    """Face embedding using InceptionResnetV1 (VGGFace2 pretrained).

    Kept as a fallback strategy. Uses 160×160 input with per-image whitening.
    """

    def __init__(self, device: str | None = None) -> None:
        self.device = device or ('cuda' if torch.cuda.is_available() else 'cpu')
        if not torch.cuda.is_available() and torch.backends.mps.is_available():
            self.device = 'mps'
            
        logger.info(f"Initializing FaceNet (InceptionResnetV1) on device: {self.device}")
        self.resnet = InceptionResnetV1(pretrained='vggface2').eval().to(self.device)

    def embed_face(self, face_image: np.ndarray) -> List[float]:
        """Generate embedding from a cropped face image (RGB).

        Resizes to 160×160 and applies per-image whitening normalization.
        """
        try:
            pil_img = Image.fromarray(face_image)
            pil_img = pil_img.resize((160, 160))
            
            img_tensor = torch.from_numpy(np.array(pil_img)).float()
            img_tensor = img_tensor.permute(2, 0, 1)  # HWC -> CHW
            
            # Per-image whitening
            mean = img_tensor.mean()
            std = img_tensor.std()
            img_tensor = (img_tensor - mean) / std
            
            img_tensor = img_tensor.unsqueeze(0).to(self.device)
            
            with torch.no_grad():
                embedding = self.resnet(img_tensor)
                
            return cast(List[float], embedding[0].cpu().numpy().tolist())

        except Exception as e:
            logger.error(f"FaceNet Embedding Error: {e}")
            raise e


class TraceNetStrategy(FaceEmbeddingStrategy):
    """Face embedding using the custom-trained TraceNet model.

    Uses 112×112 input with fixed [0.5, 0.5, 0.5] mean/std normalization,
    matching the training preprocessing. Outputs L2-normalized 512-dim embeddings.

    Args:
        model_path: Path to the TraceNet deployment checkpoint (.pth file).
        device: Device to run inference on (cuda/mps/cpu). Auto-detected if None.
    """

    def __init__(
        self,
        model_path: str | Path | None = None,
        device: str | None = None,
    ) -> None:
        self.device = device or ('cuda' if torch.cuda.is_available() else 'cpu')
        if not torch.cuda.is_available() and torch.backends.mps.is_available():
            self.device = 'mps'

        resolved_path = Path(model_path) if model_path else DEFAULT_TRACENET_PATH
        logger.info(
            f"Initializing TraceNet on device: {self.device}, "
            f"checkpoint: {resolved_path}"
        )

        if not resolved_path.exists():
            raise FileNotFoundError(
                f"TraceNet checkpoint not found at {resolved_path}. "
                f"Please place TraceNet_deployment.pth in {_MODELS_DIR}/"
            )

        # Build model and load weights
        self.model = TraceNet(embedding_size=512)
        checkpoint = torch.load(
            str(resolved_path),
            map_location=self.device,
            weights_only=True,
        )

        # The notebook saves {'model_state_dict': ...}
        if isinstance(checkpoint, dict) and "model_state_dict" in checkpoint:
            self.model.load_state_dict(checkpoint["model_state_dict"])
        else:
            # Fallback: the checkpoint IS the state_dict directly
            self.model.load_state_dict(checkpoint)

        self.model.eval().to(self.device)
        logger.info("✅ TraceNet model loaded successfully!")

        # Preprocessing transform — must match training exactly
        self.transform = transforms.Compose([
            transforms.Resize((112, 112)),
            transforms.ToTensor(),
            transforms.Normalize([0.5, 0.5, 0.5], [0.5, 0.5, 0.5]),
        ])

    def embed_face(self, face_image: np.ndarray) -> List[float]:
        """Generate a 512-dim L2-normalized embedding from a cropped face (RGB).

        Args:
            face_image: Cropped face as an RGB numpy array (any size).

        Returns:
            512-dimensional list of floats (L2-normalized).
        """
        try:
            pil_img = Image.fromarray(face_image)
            img_tensor: torch.Tensor = self.transform(pil_img)
            img_tensor = img_tensor.unsqueeze(0).to(self.device)

            with torch.no_grad():
                embedding = self.model(img_tensor)
                # L2-normalize, matching the notebook's extract_embedding()
                embedding = F.normalize(embedding, p=2, dim=1)

            return cast(List[float], embedding[0].cpu().numpy().tolist())

        except Exception as e:
            logger.error(f"TraceNet Embedding Error: {e}")
            raise e
