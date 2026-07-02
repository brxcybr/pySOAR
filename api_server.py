"""FastAPI REST layer for PySOAR."""

from typing import Optional

from classes import ConfigurationManager, Log
from core.api_auth import verify_api_token, api_auth_enabled
from core.manifests import ManifestRegistry
from integrations.health import check_playbook_integrations
from playbook_validator import validate_playbook, format_validation_result


def create_app(config_mgr: Optional[ConfigurationManager] = None):
    from fastapi import Depends, FastAPI, Header, HTTPException
    from fastapi.responses import JSONResponse
    from pydantic import BaseModel

    log = Log.get_instance()
    app = FastAPI(
        title='PySOAR API',
        description='REST interface for playbook and integration management',
        version='0.6.0',
    )
    cm = config_mgr or ConfigurationManager()
    pm = cm.playbook_mgr

    def require_auth(authorization: Optional[str] = Header(None)):
        if not verify_api_token(authorization):
            raise HTTPException(status_code=401, detail='Invalid or missing API token')
        return True

    auth_dependency = [Depends(require_auth)] if api_auth_enabled() else []

    @app.middleware('http')
    async def auth_middleware(request, call_next):
        if not api_auth_enabled():
            return await call_next(request)
        public_paths = {'/health', '/docs', '/openapi.json', '/redoc'}
        if request.url.path in public_paths:
            return await call_next(request)
        if not verify_api_token(request.headers.get('Authorization')):
            return JSONResponse(
                status_code=401,
                content={'detail': 'Invalid or missing API token'},
            )
        return await call_next(request)

    class RunRequest(BaseModel):
        once: bool = True
        skip_validation: bool = False

    class ScheduleRequest(BaseModel):
        interval_seconds: int = 300
        once: bool = True

    @app.get('/health')
    def health():
        return {
            'status': 'ok',
            'service': 'pysoar-api',
            'auth_required': api_auth_enabled(),
        }

    class IntelConvertRequest(BaseModel):
        content: str
        source_format: str
        target_format: str = 'cidm'

    @app.get('/intel/formats', dependencies=auth_dependency)
    def list_intel_formats():
        from core.cidm.converter import IntelConverter

        return IntelConverter().list_formats()

    @app.post('/intel/convert', dependencies=auth_dependency)
    def convert_intel(body: IntelConvertRequest):
        from core.cidm.converter import IntelConverter

        converter = IntelConverter()
        try:
            result = converter.convert(body.content, body.source_format, body.target_format)
        except NotImplementedError as exc:
            raise HTTPException(status_code=501, detail=str(exc)) from exc
        except Exception as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        return {'source_format': body.source_format, 'target_format': body.target_format, 'result': result}

    @app.get('/actions', dependencies=auth_dependency)
    def list_actions():
        registry = ManifestRegistry.get_instance()
        return [
            {
                'name': manifest.name,
                'integration': manifest.integration,
                'category': manifest.category,
                'risk': manifest.risk,
                'play_type': manifest.play_type,
                'producer': manifest.producer,
                'outputs': manifest.outputs,
                'description': manifest.description,
            }
            for manifest in registry.all_manifests()
        ]

    @app.get('/playbooks', dependencies=auth_dependency)
    def list_playbooks():
        pm._load_all_playbooks_if_required()
        return [
            {
                'name': name,
                'enabled': pm.playbooks_data.get(name, {}).get('enabled', False),
                'running': pm.playbooks_data.get(name, {}).get('is_running', False),
            }
            for name in pm.playbook_names
        ]

    @app.get('/playbooks/{name}', dependencies=auth_dependency)
    def get_playbook(name: str):
        pm._load_all_playbooks_if_required()
        if name not in pm.playbook_names:
            raise HTTPException(status_code=404, detail='Playbook not found')
        data = pm.playbooks_data.get(name, {})
        return {
            'name': name,
            'enabled': data.get('enabled', False),
            'integration_dependencies': data.get('integration_dependencies', []),
            'logic_steps': len(data.get('logic', [])),
        }

    @app.post('/playbooks/{name}/validate', dependencies=auth_dependency)
    def validate_playbook_endpoint(name: str):
        from classes import Playbook

        pm._load_all_playbooks_if_required()
        if name not in pm.playbook_names:
            raise HTTPException(status_code=404, detail='Playbook not found')
        playbook = Playbook(name, pm.playbooks_data[name])
        result = validate_playbook(playbook, cm)
        return {
            'valid': result.is_valid,
            'report': format_validation_result(result),
            'errors': [
                {'level': i.level, 'code': i.code, 'message': i.message}
                for i in result.errors
            ],
            'warnings': [
                {'level': i.level, 'code': i.code, 'message': i.message}
                for i in result.warnings
            ],
        }

    @app.get('/playbooks/{name}/health', dependencies=auth_dependency)
    def playbook_health(name: str):
        from classes import Playbook

        pm._load_all_playbooks_if_required()
        if name not in pm.playbook_names:
            raise HTTPException(status_code=404, detail='Playbook not found')
        playbook = Playbook(name, pm.playbooks_data[name])
        results = check_playbook_integrations(cm, playbook)
        return [
            {
                'integration': r.integration,
                'healthy': r.healthy,
                'message': r.message,
            }
            for r in results
        ]

    @app.post('/playbooks/{name}/run', dependencies=auth_dependency)
    def run_playbook(name: str, body: RunRequest = RunRequest()):
        pm._load_all_playbooks_if_required()
        if name not in pm.playbook_names:
            raise HTTPException(status_code=404, detail='Playbook not found')
        try:
            pm.launch_playbook(
                name,
                cm,
                once=body.once,
                skip_validation=body.skip_validation,
            )
        except Exception as exc:
            log.error(f'API playbook run failed: {exc}')
            raise HTTPException(status_code=500, detail=str(exc)) from exc
        return {'status': 'completed', 'playbook': name, 'once': body.once}

    @app.get('/integrations', dependencies=auth_dependency)
    def list_integrations():
        cm.update_enabled_items()
        return [
            {
                'name': item.name,
                'enabled': item.enabled,
                'url': item.url,
                'functions': item.playbook_functions,
            }
            for item in cm.enabled_integrations
        ]

    @app.get('/scheduler/jobs', dependencies=auth_dependency)
    def scheduler_jobs():
        sched = getattr(app.state, 'scheduler', None)
        if sched is None:
            return []
        return sched.list_jobs()

    @app.post('/scheduler/playbooks/{name}', dependencies=auth_dependency)
    def schedule_playbook(name: str, body: ScheduleRequest = ScheduleRequest()):
        from scheduler import PlaybookScheduler

        pm._load_all_playbooks_if_required()
        if name not in pm.playbook_names:
            raise HTTPException(status_code=404, detail='Playbook not found')
        if not hasattr(app.state, 'scheduler') or app.state.scheduler is None:
            app.state.scheduler = PlaybookScheduler(cm)
        sched = app.state.scheduler
        job_id = sched.schedule_interval(
            name,
            body.interval_seconds,
            once=body.once,
        )
        sched.start()
        return {'scheduled': name, 'job_id': job_id, 'interval_seconds': body.interval_seconds}

    return app


def serve(host='127.0.0.1', port=8088, config_mgr=None):
    import uvicorn

    app = create_app(config_mgr)
    uvicorn.run(app, host=host, port=port, log_level='info')
