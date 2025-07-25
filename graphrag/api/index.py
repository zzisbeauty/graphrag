# Copyright (c) 2024 Microsoft Corporation.
# Licensed under the MIT License

"""
Indexing API for GraphRAG.

WARNING: This API is under development and may undergo changes in future releases.
Backwards compatibility is not guaranteed at this time.
"""

import logging

from graphrag.callbacks.noop_workflow_callbacks import NoopWorkflowCallbacks
from graphrag.callbacks.workflow_callbacks import WorkflowCallbacks
from graphrag.config.enums import IndexingMethod
from graphrag.config.models.graph_rag_config import GraphRagConfig
from graphrag.index.run.run_pipeline import run_pipeline
from graphrag.index.run.utils import create_callback_chain
from graphrag.index.typing.pipeline_run_result import PipelineRunResult
from graphrag.index.typing.workflow import WorkflowFunction
from graphrag.index.workflows.factory import PipelineFactory
from graphrag.logger.standard_logging import init_loggers

logger = logging.getLogger(__name__)


async def build_index(
    config: GraphRagConfig,
    method: IndexingMethod | str = IndexingMethod.Standard,
    is_update_run: bool = False,
    memory_profile: bool = False,
    callbacks: list[WorkflowCallbacks] | None = None,
) -> list[PipelineRunResult]:
    """Run the pipeline with the given configuration.

    Parameters
    ----------
    config : GraphRagConfig
        The configuration.
    method : IndexingMethod default=IndexingMethod.Standard
        Styling of indexing to perform (full LLM, NLP + LLM, etc.).
    memory_profile : bool
        Whether to enable memory profiling.
    callbacks : list[WorkflowCallbacks] | None default=None
        A list of callbacks to register.

    Returns
    -------
    list[PipelineRunResult]
        The list of pipeline run results
    """
    init_loggers(config=config)

    # Create callbacks for pipeline lifecycle events if provided
    workflow_callbacks = (
        create_callback_chain(callbacks) if callbacks else NoopWorkflowCallbacks()
    )

    outputs: list[PipelineRunResult] = []

    if memory_profile:
        logger.warning("New pipeline does not yet support memory profiling.")

    logger.info("Initializing indexing pipeline...")
    # todo: this could propagate out to the cli for better clarity, but will be a breaking api change
    method = _get_method(method, is_update_run)
    pipeline = PipelineFactory.create_pipeline(config, method)

    workflow_callbacks.pipeline_start(pipeline.names())

    async for output in run_pipeline(
        pipeline,
        config,
        callbacks=workflow_callbacks,
        is_update_run=is_update_run,
    ):
        outputs.append(output)
        if output.errors and len(output.errors) > 0:
            logger.error("Workflow %s completed with errors", output.workflow)
        else:
            logger.info("Workflow %s completed successfully", output.workflow)
        logger.debug(str(output.result))

    workflow_callbacks.pipeline_end(outputs)
    return outputs


def register_workflow_function(name: str, workflow: WorkflowFunction):
    """Register a custom workflow function. You can then include the name in the settings.yaml workflows list."""
    PipelineFactory.register(name, workflow)


def _get_method(method: IndexingMethod | str, is_update_run: bool) -> str:
    m = method.value if isinstance(method, IndexingMethod) else method
    return f"{m}-update" if is_update_run else m
