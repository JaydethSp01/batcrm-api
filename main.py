import os
import importlib
import pkgutil
from fastapi import FastAPI, APIRouter
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

# Auto-incluir todos los routers definidos bajo el paquete 'app'.
def _autoload_routers():
    try:
        import app as app_pkg
    except Exception:
        return
    for mod in pkgutil.walk_packages(app_pkg.__path__, 'app.'):
        try:
            m = importlib.import_module(mod.name)
        except Exception:
            continue
        r = getattr(m, 'router', None)
        if isinstance(r, APIRouter):
            try:
                app.include_router(r)
            except Exception:
                pass

_autoload_routers()
