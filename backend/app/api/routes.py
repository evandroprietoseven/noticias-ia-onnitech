from fastapi import APIRouter
from app.services.pipeline import run_pipeline

router = APIRouter()

@router.get('/health')
def health():
    return {'status': 'ok'}

@router.post('/run')
def run_now():
    result = run_pipeline()
    return {'status': 'completed', 'result': result}
