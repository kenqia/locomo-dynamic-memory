"""Complete-version download and phase-aware explicit recovery."""
from fastapi import BackgroundTasks, FastAPI
from fastapi.responses import Response

from .builds import BuildError
from .export_schemas import MemoryExport
from .exports import ExportService


def register_version_routes(app: FastAPI, versions, retrieval, relations):
    exports = ExportService(versions)

    @app.get("/builds/{build_id}/export", response_model=MemoryExport)
    def export_version(build_id: str):
        bundle = exports.export(build_id)
        return Response(bundle.model_dump_json(), media_type="application/json", headers={"Content-Disposition": f'attachment; filename="memory-{bundle.build.build_id}.json"'})

    @app.post("/builds/{build_id}/retry-phase", status_code=202)
    def retry_phase(build_id: str, tasks: BackgroundTasks):
        build = versions.builds.get(build_id)
        if build["status"] not in {"failed", "interrupted", "index_failed", "relations_failed"}:
            raise BuildError("build_not_retryable")
        if build["phase"] == "extraction":
            result = versions.builds.retry(build_id)
            tasks.add_task(versions.builds.run, build_id)
            return result
        if build["phase"] == "indexing":
            retrieval.create_index(build_id)
        elif build["phase"] == "relations":
            relations.start(build_id)
            tasks.add_task(relations.run, build_id)
        else:
            raise BuildError("build_not_retryable")
        return versions.builds.get(build_id)
