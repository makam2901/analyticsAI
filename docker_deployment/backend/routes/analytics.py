from fastapi import APIRouter

router = APIRouter()

@router.get("/queries")
def get_sample_queries():
    # This endpoint is now a placeholder.
    return {"message": "No sample queries available."}