import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import numpy as np
from uuid import uuid4
from src.services.recognition_service import RecognitionService
from src.domain.models.audit import AuditLog

@pytest.mark.asyncio
@patch('cv2.imdecode')
@patch('cv2.cvtColor')
async def test_identify_suspects_success(mock_cvtColor, mock_imdecode):
    # Mock cv2 behavior
    mock_imdecode.return_value = np.zeros((100, 100, 3), dtype=np.uint8)
    mock_cvtColor.return_value = np.zeros((100, 100, 3), dtype=np.uint8)
    
    # Mock dependencies
    pipeline = MagicMock()
    face_repo = AsyncMock()
    criminal_repo = AsyncMock()
    audit_repo = AsyncMock()
    
    # Setup mock data
    mock_embedding = [0.1] * 128
    pipeline.process_image.return_value = [
        {'box': [10, 10, 50, 50], 'embedding': mock_embedding}
    ]
    
    mock_face = MagicMock()
    mock_face.criminal_id = uuid4()
    face_repo.find_nearest_neighbors.return_value = [(mock_face, 0.4)]
    
    mock_criminal = MagicMock()
    mock_criminal.id = mock_face.criminal_id
    mock_criminal.first_name = "John"
    mock_criminal.last_name = "Doe"
    mock_criminal.nic = "123456789V"
    mock_criminal.threat_level = "HIGH"
    criminal_repo.get.return_value = mock_criminal
    
    service = RecognitionService(pipeline, face_repo, criminal_repo, audit_repo)
    
    # Execute with dummy bytes (cv2 is mocked)
    results = await service.identify_suspects(b"fake_bytes", threshold=0.6)
    
    # Verify
    assert len(results) == 1
    assert results[0]['status'] == 'match'
    assert results[0]['criminal']['name'] == "John Doe"
    assert results[0]['confidence'] > 90 # Based on 0.4 distance and sigmoid calibration
    
    # Verify audit log was created
    audit_repo.create.assert_called_once()
    args, _ = audit_repo.create.call_args
    assert isinstance(args[0], AuditLog)
    assert args[0].action == "IDENTIFY"


@pytest.mark.asyncio
@patch('cv2.imdecode')
@patch('cv2.cvtColor')
async def test_identify_suspects_uses_largest_face_only(mock_cvtColor, mock_imdecode):
    mock_imdecode.return_value = np.zeros((200, 200, 3), dtype=np.uint8)
    mock_cvtColor.return_value = np.zeros((200, 200, 3), dtype=np.uint8)

    pipeline = MagicMock()
    face_repo = AsyncMock()
    criminal_repo = AsyncMock()
    audit_repo = AsyncMock()

    pipeline.process_image.return_value = [
        {'box': [0, 0, 40, 40], 'embedding': [0.1] * 128},
        {'box': [10, 10, 120, 120], 'embedding': [0.2] * 128},
        {'box': [30, 30, 25, 25], 'embedding': [0.3] * 128},
    ]

    mock_face = MagicMock()
    mock_face.criminal_id = uuid4()
    face_repo.find_nearest_neighbors.return_value = [(mock_face, 0.3)]

    mock_criminal = MagicMock()
    mock_criminal.id = mock_face.criminal_id
    mock_criminal.first_name = "Jane"
    mock_criminal.last_name = "Doe"
    mock_criminal.nic = "987654321V"
    mock_criminal.threat_level = "HIGH"
    criminal_repo.get.return_value = mock_criminal

    service = RecognitionService(pipeline, face_repo, criminal_repo, audit_repo)
    results = await service.identify_suspects(b"fake_bytes")

    assert len(results) == 1
    assert results[0]['box'] == [10, 10, 120, 120]
    face_repo.find_nearest_neighbors.assert_awaited_once_with([0.2] * 128, limit=5)


@pytest.mark.asyncio
@patch('cv2.imdecode')
@patch('cv2.cvtColor')
async def test_identify_suspects_rejects_ambiguous_match(mock_cvtColor, mock_imdecode):
    mock_imdecode.return_value = np.zeros((100, 100, 3), dtype=np.uint8)
    mock_cvtColor.return_value = np.zeros((100, 100, 3), dtype=np.uint8)

    pipeline = MagicMock()
    face_repo = AsyncMock()
    criminal_repo = AsyncMock()
    audit_repo = AsyncMock()

    pipeline.process_image.return_value = [
        {'box': [10, 10, 50, 50], 'embedding': [0.1] * 128}
    ]

    best_face = MagicMock()
    best_face.criminal_id = uuid4()
    second_face = MagicMock()
    second_face.criminal_id = uuid4()
    face_repo.find_nearest_neighbors.return_value = [
        (best_face, 0.38),
        (second_face, 0.42),
    ]

    service = RecognitionService(pipeline, face_repo, criminal_repo, audit_repo)
    results = await service.identify_suspects(b"fake_bytes")

    assert len(results) == 1
    assert results[0]['status'] == 'unknown'
    assert results[0]['confidence'] == 0.0
    criminal_repo.get.assert_not_called()
