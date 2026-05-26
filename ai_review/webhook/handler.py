import os
import asyncio
from ai_review.libs.logger import get_logger

logger = get_logger("WEBHOOK_HANDLER")


async def handle_gitlab_mr_event(mr_info: dict):

    project_id = mr_info["project_id"]
    mr_iid = mr_info["merge_request_iid"]

    logger.info(f"Starting review for project={project_id} MR!{mr_iid}")

    try:
        # VCS pipeline config dynamically override
        os.environ["VCS__PIPELINE__PROJECT_ID"] = project_id
        os.environ["VCS__PIPELINE__MERGE_REQUEST_ID"] = mr_iid

        # Reload settings with env override
        from ai_review.config import Settings
        dynamic_settings = Settings()

        # Create ReviewService with dynamic settings
        from ai_review.services.review.service import ReviewService
        review_service = ReviewService()

        command = dynamic_settings.webhook.review_command

        if command == "run":
            await review_service.run_inline_review()
            await review_service.run_summary_review()
        elif command == "run-inline":
            await review_service.run_inline_review()
        elif command == "run-context":
            await review_service.run_context_review()
        elif command == "run-summary":
            await review_service.run_summary_review()
        elif command == "run-inline-reply":
            await review_service.run_inline_reply_review()
        elif command == "run-summary-reply":
            await review_service.run_summary_reply_review()
        else:
            logger.warning(f"Unknown review command: {command}, falling back to 'run'")
            await review_service.run_inline_review()
            await review_service.run_summary_review()

        review_service.report_total_cost()
        logger.info(f"Review completed for project={project_id} MR!{mr_iid}")

    except Exception as e:
        logger.error(f"Review failed for project={project_id} MR!{mr_iid}: {e}")
        raise
    finally:
        # Clean up envs
        os.environ.pop("VCS__PIPELINE__PROJECT_ID", None)
        os.environ.pop("VCS__PIPELINE__MERGE_REQUEST_ID", None)