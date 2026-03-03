from pydantic import BaseModel


class RecognitionPolicyResponse(BaseModel):
    match_threshold: float
    possible_match_threshold: float
    match_separation_margin: float
    possible_match_separation_margin: float
