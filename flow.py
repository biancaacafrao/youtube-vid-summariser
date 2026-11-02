from pocketflow import Flow

from nodes import ExplainTopics, ExtractTopics, FetchTranscript, RenderHTML


def create_study_guide_flow():
    """YouTube link -> transcript -> topics -> explanations + Q&A -> HTML page."""
    fetch = FetchTranscript(max_retries=3, wait=2)
    topics = ExtractTopics(max_retries=3, wait=2)
    explain = ExplainTopics(max_retries=3, wait=2)
    render = RenderHTML()

    fetch >> topics >> explain >> render
    return Flow(start=fetch)
