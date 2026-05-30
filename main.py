import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title='API')
origins = os.environ.get('CORS_ORIGINS', '*').split(',')
app.add_middleware(CORSMiddleware, allow_origins=origins, allow_credentials=True,
                   allow_methods=['*'], allow_headers=['*'])

@app.get('/health')
def health():
    return {'status': 'ok'}

@app.get('/')
def root():
    return {'service': 'api', 'status': 'ok'}
