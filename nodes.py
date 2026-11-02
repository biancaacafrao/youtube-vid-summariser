import logging

import yaml
from pocketflow import BatchNode, Node

from utils.call_llm import call_llm
from utils.get_youtube_transcript import get_youtube_transcript
from utils.render_study_guide import render_study_guide

logger = logging.getLogger(__name__)

MIN_TOPICS, MAX_TOPICS = 3, 7
QUESTIONS_PER_TOPIC = 3


def parse_yaml_reply(reply: str) -> dict:
    """Pull the YAML block out of an LLM reply (fenced or not) and parse it."""
    text = reply
    if "```yaml" in text:
        text = text.split("```yaml", 1)[1].split("```", 1)[0]
    elif "```" in text:
        text = text.split("```", 1)[1].split("```", 1)[0]
    result = yaml.safe_load(text.strip())
    assert isinstance(result, dict), "LLM reply is not a YAML mapping"
    return result


class FetchTranscript(Node):
    def prep(self, shared):
        return shared["url"]

    def exec(self, url):
        return get_youtube_transcript(url)

    def post(self, shared, prep_res, exec_res):
        shared["transcript"] = exec_res
        logger.info("Transcript fetched (%s chars)", len(exec_res))


class ExtractTopics(Node):
    def prep(self, shared):
        return shared["transcript"]

    def exec(self, transcript):
        prompt = f"""You are helping a learner study a YouTube video. Below is the video's transcript.

Identify the {MIN_TOPICS}-{MAX_TOPICS} KEY topics the video actually teaches, in the order they appear.
- Topics must NOT overlap. Each one covers a different idea or part of the video.
  If two candidate topics would need the same explanation, merge them into one.
- Prefer fewer, clearly distinct topics over many similar ones.
- Do not make the video's overall goal or intro its own topic if a later topic explains it.
- Skip tangents, jokes, sponsor segments, and calls to subscribe.
- If the video is very short or covers little, return fewer topics, but at least 1.
- Write in the same language as the transcript.

TRANSCRIPT:
{transcript}

Reply with YAML only, in exactly this format:
```yaml
topics:
  - title: |
      Short topic title (max ~8 words)
    summary: |
      One sentence on what this topic covers that no other topic does
```"""
        result = parse_yaml_reply(call_llm(prompt))
        topics = result.get("topics")
        assert isinstance(topics, list) and 1 <= len(topics) <= MAX_TOPICS, f"Bad topic count: {topics!r}"
        cleaned = []
        for t in topics:
            assert isinstance(t, dict) and t.get("title"), f"Topic missing title: {t!r}"
            cleaned.append({"title": str(t["title"]).strip(), "summary": str(t.get("summary", "")).strip()})
        return cleaned

    def post(self, shared, prep_res, exec_res):
        shared["topics"] = exec_res
        logger.info("Topics: %s", [t["title"] for t in exec_res])


class ExplainTopics(BatchNode):
    def prep(self, shared):
        transcript = shared["transcript"]
        topics = shared["topics"]
        items = []
        for i, t in enumerate(topics):
            others = [o["title"] for j, o in enumerate(topics) if j != i]
            items.append((transcript, t["title"], t["summary"], others))
        return items

    def exec(self, item):
        transcript, title, summary, others = item
        other_topics = "\n".join(f"- {o}" for o in others) or "- (none)"
        prompt = f"""You are helping a learner study a YouTube video. Below is the video's transcript.

Focus on ONE topic from the video:
Title: {title}
Summary: {summary}

The study guide covers these OTHER topics separately. Do not explain them or ask about them here;
mention them only briefly if needed for context:
{other_topics}

1. Explain this topic very simply, as if to a smart beginner with no background.
   Use everyday words and short sentences. If the video relies on a technical term,
   explain it. A small everyday analogy is welcome. 2 short paragraphs at most.
2. Write EXACTLY {QUESTIONS_PER_TOPIC} questions about this topic, each with a short, clear answer (1-2 sentences).
   Make them different kinds, checking real understanding rather than trivia:
   - one "what": what is it / what does it do
   - one "why" or "how": why it matters or how it works
   - one "apply": use the idea in a small example or scenario
   No two questions may test the same fact.

Use ONLY what the video says. Write in the same language as the transcript.

TRANSCRIPT:
{transcript}

Reply with YAML only, in exactly this format:
```yaml
explanation: |
  First paragraph.

  Second paragraph.
questions:
  - question: |
      The question?
    answer: |
      The answer.
```"""
        result = parse_yaml_reply(call_llm(prompt))
        explanation = str(result.get("explanation", "")).strip()
        questions = result.get("questions")
        assert explanation, "Missing explanation"
        assert isinstance(questions, list) and len(questions) == QUESTIONS_PER_TOPIC, (
            f"Expected {QUESTIONS_PER_TOPIC} questions, got {questions!r}"
        )
        cleaned = []
        for qa in questions:
            assert isinstance(qa, dict) and qa.get("question") and qa.get("answer"), f"Bad Q&A: {qa!r}"
            cleaned.append({"question": str(qa["question"]).strip(), "answer": str(qa["answer"]).strip()})
        logger.info("Explained topic %r (%s questions)", title, len(cleaned))
        return {"explanation": explanation, "questions": cleaned}

    def post(self, shared, prep_res, exec_res_list):
        for topic, res in zip(shared["topics"], exec_res_list):
            topic.update(res)


class RenderHTML(Node):
    def prep(self, shared):
        return shared["url"], shared["topics"]

    def exec(self, inputs):
        url, topics = inputs
        return render_study_guide(url, topics)

    def post(self, shared, prep_res, exec_res):
        path = shared.get("output_path") or "study_guide.html"
        with open(path, "w", encoding="utf-8") as f:
            f.write(exec_res)
        shared["output_path"] = path
        logger.info("Study guide written to %s", path)
