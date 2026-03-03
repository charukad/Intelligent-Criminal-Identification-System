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
    template_repo = AsyncMock()
    face_repo = AsyncMock()
    criminal_repo = AsyncMock()
    audit_repo = AsyncMock()
    
    # Setup mock data
    mock_embedding = [0.1] * 128
    pipeline.process_image.return_value = [
        {'box': [10, 10, 50, 50], 'embedding': mock_embedding}
    ]
    
    criminal_id = uuid4()
    primary_face_id = uuid4()
    mock_template = MagicMock()
    mock_template.criminal_id = criminal_id
    mock_template.primary_face_id = primary_face_id
    mock_template.embedding_version = "tracenet_v1"
    mock_template.template_version = "tracenet_template_v1"
    mock_template.active_face_count = 2
    mock_template.support_face_count = 1
    mock_template.outlier_face_count = 0
    template_repo.find_nearest_neighbors.return_value = [(mock_template, 0.4)]
    face_repo.get.return_value = MagicMock(
        id=primary_face_id,
        image_url="uploads/faces/john.jpg",
        is_primary=True,
    )
    
    mock_criminal = MagicMock()
    mock_criminal.id = criminal_id
    mock_criminal.first_name = "John"
    mock_criminal.last_name = "Doe"
    mock_criminal.nic = "123456789V"
    mock_criminal.threat_level = "HIGH"
    criminal_repo.get.return_value = mock_criminal
    
    service = RecognitionService(pipeline, template_repo, face_repo, criminal_repo, audit_repo)
    
    # Execute with dummy bytes (cv2 is mocked)
    response = await service.identify_suspects(b"fake_bytes", threshold=0.6)
    results = response["results"]
    
    # Verify
    assert len(results) == 1
    assert results[0]['status'] == 'match'
    assert results[0]['criminal']['name'] == "John Doe"
    assert results[0]['distance'] == 0.4
    assert results[0]['decision_reason'] == 'matched'
    
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
    template_repo = AsyncMock()
    face_repo = AsyncMock()
    criminal_repo = AsyncMock()
    audit_repo = AsyncMock()

    pipeline.process_image.return_value = [
        {'box': [0, 0, 40, 40], 'embedding': [0.1] * 128},
        {'box': [10, 10, 120, 120], 'embedding': [0.2] * 128},
        {'box': [30, 30, 25, 25], 'embedding': [0.3] * 128},
    ]

    criminal_id = uuid4()
    primary_face_id = uuid4()
    mock_template = MagicMock()
    mock_template.criminal_id = criminal_id
    mock_template.primary_face_id = primary_face_id
    mock_template.embedding_version = "tracenet_v1"
    mock_template.template_version = "tracenet_template_v1"
    mock_template.active_face_count = 2
    mock_template.support_face_count = 1
    mock_template.outlier_face_count = 0
    template_repo.find_nearest_neighbors.return_value = [(mock_template, 0.3)]
    face_repo.get.return_value = MagicMock(
        id=primary_face_id,
        image_url="uploads/faces/jane.jpg",
        is_primary=True,
    )

    mock_criminal = MagicMock()
    mock_criminal.id = criminal_id
    mock_criminal.first_name = "Jane"
    mock_criminal.last_name = "Doe"
    mock_criminal.nic = "987654321V"
    mock_criminal.threat_level = "HIGH"
    criminal_repo.get.return_value = mock_criminal

    service = RecognitionService(pipeline, template_repo, face_repo, criminal_repo, audit_repo)
    response = await service.identify_suspects(b"fake_bytes", include_debug=True)
    results = response["results"]

    assert len(results) == 1
    assert results[0]['box'] == (10, 10, 120, 120)
    assert response["debug"]["detected_face_count"] == 3
    assert response["debug"]["analyzed_face_count"] == 1
    template_repo.find_nearest_neighbors.assert_awaited_once_with([0.2] * 128, limit=10)


@pytest.mark.asyncio
@patch('cv2.imdecode')
@patch('cv2.cvtColor')
async def test_identify_suspects_rejects_over_threshold_match(mock_cvtColor, mock_imdecode):
    mock_imdecode.return_value = np.zeros((100, 100, 3), dtype=np.uint8)
    mock_cvtColor.return_value = np.zeros((100, 100, 3), dtype=np.uint8)

    pipeline = MagicMock()
    template_repo = AsyncMock()
    face_repo = AsyncMock()
    criminal_repo = AsyncMock()
    audit_repo = AsyncMock()

    pipeline.process_image.return_value = [
        {'box': [10, 10, 50, 50], 'embedding': [0.1] * 128}
    ]

    best_template = MagicMock()
    best_template.criminal_id = uuid4()
    best_template.primary_face_id = uuid4()
    template_repo.find_nearest_neighbors.return_value = [
        (best_template, 0.015),
    ]

    service = RecognitionService(pipeline, template_repo, face_repo, criminal_repo, audit_repo)
    response = await service.identify_suspects(b"fake_bytes")
    results = response["results"]

    assert len(results) == 1
    assert results[0]['status'] == 'unknown'
    assert results[0]['confidence'] == 0.0
    assert results[0]['decision_reason'] == 'over_possible_threshold'
    criminal_repo.get.assert_not_called()


@pytest.mark.asyncio
@patch('cv2.imdecode')
@patch('cv2.cvtColor')
async def test_identify_suspects_returns_possible_match_for_threshold_band(mock_cvtColor, mock_imdecode):
    mock_imdecode.return_value = np.zeros((100, 100, 3), dtype=np.uint8)
    mock_cvtColor.return_value = np.zeros((100, 100, 3), dtype=np.uint8)

    pipeline = MagicMock()
    template_repo = AsyncMock()
    face_repo = AsyncMock()
    criminal_repo = AsyncMock()
    audit_repo = AsyncMock()

    pipeline.process_image.return_value = [
        {'box': [10, 10, 50, 50], 'embedding': [0.1] * 128}
    ]

    criminal_id = uuid4()
    primary_face_id = uuid4()
    mock_template = MagicMock()
    mock_template.criminal_id = criminal_id
    mock_template.primary_face_id = primary_face_id
    mock_template.embedding_version = "tracenet_v1"
    mock_template.template_version = "tracenet_template_v1"
    mock_template.active_face_count = 3
    mock_template.support_face_count = 2
    mock_template.outlier_face_count = 0
    template_repo.find_nearest_neighbors.return_value = [(mock_template, 0.0054)]
    face_repo.get.return_value = MagicMock(id=primary_face_id, image_url="uploads/faces/possible.jpg", is_primary=True)

    mock_criminal = MagicMock()
    mock_criminal.id = criminal_id
    mock_criminal.first_name = "Possible"
    mock_criminal.last_name = "Match"
    mock_criminal.nic = "555555555V"
    mock_criminal.threat_level = "MEDIUM"
    criminal_repo.get.return_value = mock_criminal

    service = RecognitionService(pipeline, template_repo, face_repo, criminal_repo, audit_repo)
    response = await service.identify_suspects(b"fake_bytes")
    results = response["results"]

    assert len(results) == 1
    assert results[0]["status"] == "possible_match"
    assert results[0]["decision_reason"] == "possible_match_threshold"
    assert results[0]["criminal"]["name"] == "Possible Match"
    assert results[0]["confidence"] > 0


@pytest.mark.asyncio
@patch('cv2.imdecode')
@patch('cv2.cvtColor')
async def test_identify_suspects_scene_mode_analyzes_all_faces(mock_cvtColor, mock_imdecode):
    mock_imdecode.return_value = np.zeros((200, 200, 3), dtype=np.uint8)
    mock_cvtColor.return_value = np.zeros((200, 200, 3), dtype=np.uint8)

    pipeline = MagicMock()
    template_repo = AsyncMock()
    face_repo = AsyncMock()
    criminal_repo = AsyncMock()
    audit_repo = AsyncMock()

    pipeline.process_image.return_value = [
        {'box': [0, 0, 40, 40], 'embedding': [0.1] * 128},
        {'box': [10, 10, 120, 120], 'embedding': [0.2] * 128},
    ]

    template_one = MagicMock()
    template_one.criminal_id = uuid4()
    template_one.primary_face_id = uuid4()
    template_one.embedding_version = "tracenet_v1"
    template_one.template_version = "tracenet_template_v1"
    template_one.active_face_count = 2
    template_one.support_face_count = 1
    template_one.outlier_face_count = 0

    template_two = MagicMock()
    template_two.criminal_id = uuid4()
    template_two.primary_face_id = uuid4()
    template_two.embedding_version = "tracenet_v1"
    template_two.template_version = "tracenet_template_v1"
    template_two.active_face_count = 2
    template_two.support_face_count = 1
    template_two.outlier_face_count = 0

    template_repo.find_nearest_neighbors.side_effect = [
        [(template_one, 0.0035)],
        [(template_two, 0.0058)],
    ]
    face_repo.get.side_effect = [
        MagicMock(id=template_one.primary_face_id, image_url="uploads/faces/one.jpg", is_primary=True),
        MagicMock(id=template_two.primary_face_id, image_url="uploads/faces/two.jpg", is_primary=True),
    ]

    criminal_repo.get.side_effect = [
        MagicMock(id=template_one.criminal_id, first_name="Face", last_name="One", nic="111", threat_level="HIGH"),
        MagicMock(id=template_two.criminal_id, first_name="Face", last_name="Two", nic="222", threat_level="LOW"),
    ]

    service = RecognitionService(pipeline, template_repo, face_repo, criminal_repo, audit_repo)
    response = await service.identify_suspects(b"fake_bytes", single_face_only=False)
    results = response["results"]

    assert len(results) == 2
    assert results[0]["status"] == "match"
    assert results[1]["status"] == "possible_match"
    assert template_repo.find_nearest_neighbors.await_count == 2
