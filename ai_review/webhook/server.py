import asyncio
from contextlib import asynccontextmanager

from ai_review.libs.logger import get_logger

logger = get_logger("WEBHOOK_SERVER")


def create_app():
    """Create FastAPI app only when webhook is enabled"""
    from fastapi import FastAPI, Request, HTTPException, BackgroundTasks
    from ai_review.config import settings
    from ai_review.webhook.handler import handle_gitlab_mr_event

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        logger.info(
            f"AI Review webhook server started on "
            f"{settings.webhook.host}:{settings.webhook.port}"
        )
        logger.info(f"Review command: {settings.webhook.review_command}")
        yield
        logger.info("AI Review webhook server stopped")

    app = FastAPI(
        title="AI Review Webhook Server",
        lifespan=lifespan,
    )

    @app.post("/webhook/gitlab")
    async def gitlab_webhook(request: Request, background_tasks: BackgroundTasks):
        # Secret token check
        if settings.webhook.secret:
            token = request.headers.get("X-Gitlab-Token")
            if token != settings.webhook.secret:
                raise HTTPException(status_code=403, detail="Invalid webhook secret")

        payload = await request.json()
        object_kind = payload.get("object_kind")

        if object_kind != "merge_request":
            return {"status": "ignored", "reason": f"Not a merge_request event: {object_kind}"}

        action = payload.get("object_attributes", {}).get("action")
        if action not in ("open", "reopen", "update"):
            return {"status": "ignored", "reason": f"MR action not relevant: {action}"}

        mr_attrs = payload["object_attributes"]
        project = payload["project"]

        mr_info = {
            "project_id": str(project["id"]),
            "merge_request_iid": str(mr_attrs["iid"]),
            "source_branch": mr_attrs.get("source_branch"),
            "target_branch": mr_attrs.get("target_branch"),
            "title": mr_attrs.get("title"),
            "action": action,
        }

        logger.info(
            f"Received MR webhook: project={mr_info['project_id']} "
            f"MR!{mr_info['merge_request_iid']} action={action}"
        )

        # Run review in background
        background_tasks.add_task(handle_gitlab_mr_event, mr_info)

        return {
            "status": "accepted",
            "project_id": mr_info["project_id"],
            "merge_request_iid": mr_info["merge_request_iid"],
        }

    @app.get("/health")
    async def health():
        return {"status": "ok", "webhook_enabled": settings.webhook.enabled}

    return app