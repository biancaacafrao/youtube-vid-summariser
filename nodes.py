import logging

import yaml
from pocketflow import Node

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

    def post(self, shared, _prep_res, exec_res):
        shared["transcript"] = exec_res
        logger.info("Transcript fetched (%s chars)", len(exec_res))


class ExtractTopics(Node):
    def prep(self, shared):
        return shared["transcript"]

    def exec(self, transcript):
        prompt = f"""You are helping a learner study a YouTube video. Below is the video's transcript.

Identify the {MIN_TOPICS}-{MAX_TOPICS} KEY topics the video actually teaches, in the order they appear.
For each topic, list the 2-4 specific key points from the video that belong to it.

Rules:
- Topics must NOT overlap. Each covers a different idea or part of the video.
- Every key point belongs to exactly ONE topic. Never list the same fact under two topics.
- If two candidate topics would share most of their key points, merge them into one.
- Prefer fewer, clearly distinct topics over many similar ones.
- Do not make the video's intro or overall goal its own topic if a later topic explains it.
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
      One sentence on what this topic covers
    key_points:
      - A specific point the video makes, only under this topic
      - Another specific point
```"""
        result = parse_yaml_reply(call_llm(prompt))
        topics = result.get("topics")
        assert isinstance(topics, list) and 1 <= len(topics) <= MAX_TOPICS, f"Bad topic count: {topics!r}"
        cleaned = []
        for t in topics:
            assert isinstance(t, dict) and t.get("title"), f"Topic missing title: {t!r}"
            points = t.get("key_points")
            assert isinstance(points, list) and points, f"Topic missing key points: {t!r}"
            cleaned.append({
                "title": str(t["title"]).strip(),
                "summary": str(t.get("summary", "")).strip(),
                "key_points": [str(p).strip() for p in points],
            })
        return cleaned

    def post(self, shared, _prep_res, exec_res):
        shared["topics"] = exec_res
        logger.info("Topics: %s", [t["title"] for t in exec_res])


class ExplainTopics(Node):
    """Writes every topic's explanation and Q&A in ONE call, so questions never repeat across topics."""

    def prep(self, shared):
        return shared["transcript"], shared["topics"]

    def exec(self, inputs):
        transcript, topics = inputs
        topic_lines = []
        for i, t in enumerate(topics, 1):
            points = "\n".join(f"     - {p}" for p in t["key_points"])
            topic_lines.append(f"{i}. {t['title']}\n   Summary: {t['summary']}\n   Key points (this topic only):\n{points}")
        topic_block = "\n".join(topic_lines)

        prompt = f"""You are helping a learner study a YouTube video. Below is the video's transcript,
followed by the {len(topics)} topics of the study guide, each with the key points that belong ONLY to it.

For EACH topic, in the same order:
1. Explain it very simply, as if to a smart beginner with no background.
   Use everyday words and short sentences. If the video relies on a technical term,
   explain it. A small everyday analogy is welcome, but use a different one for each topic.
   2 short paragraphs at most. Stay within the topic's own key points.
2. Write EXACTLY {QUESTIONS_PER_TOPIC} flash-card questions, each with a short, clear answer (1-2 sentences).
   Good questions:
   - Are SPECIFIC to what this video says (its examples, numbers that matter, and reasoning).
   - Come from THAT topic's key points, not another topic's.
   - Have ONE clear correct answer the learner can check themselves against.
   - Mix recall (what/which) with understanding (why/how, or "what happens if...").
   Across the WHOLE guide, no two questions may test the same fact, even in different words.
   Avoid generic questions that could be asked about any video, such as
   "What is X?", "Why is X important?", or "How would you apply X?".
   Ask about the SUBJECT, not about the video itself: no questions like "What does the video
   focus on first?", "What example does the video use?" or "What will the next video cover?".
   Also skip trivia about labels or names that doesn't help understanding.

Use ONLY what the video says. Write in the same language as the transcript.

TRANSCRIPT:
{transcript}

TOPICS:
{topic_block}

Reply with YAML only, one entry per topic in the same order, in exactly this format:
```yaml
topics:
  - title: |
      Topic title, copied from above
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
        written = result.get("topics")
        assert isinstance(written, list) and len(written) == len(topics), (
            f"Expected {len(topics)} topics, got {len(written) if isinstance(written, list) else written!r}"
        )
        out = []
        for t in written:
            assert isinstance(t, dict), f"Bad topic entry: {t!r}"
            explanation = str(t.get("explanation", "")).strip()
            questions = t.get("questions")
            assert explanation, f"Missing explanation: {t!r}"
            assert isinstance(questions, list) and len(questions) == QUESTIONS_PER_TOPIC, (
                f"Expected {QUESTIONS_PER_TOPIC} questions, got {questions!r}"
            )
            cleaned = []
            for qa in questions:
                assert isinstance(qa, dict) and qa.get("question") and qa.get("answer"), f"Bad Q&A: {qa!r}"
                cleaned.append({"question": str(qa["question"]).strip(), "answer": str(qa["answer"]).strip()})
            out.append({"explanation": explanation, "questions": cleaned})
        return out

    def post(self, shared, _prep_res, exec_res):
        for topic, res in zip(shared["topics"], exec_res):
            topic.update(res)
        logger.info("Explained %s topics (%s questions)", len(exec_res), sum(len(r["questions"]) for r in exec_res))


class RenderHTML(Node):
    def prep(self, shared):
        return shared["url"], shared["topics"]

    def exec(self, inputs):
        url, topics = inputs
        return render_study_guide(url, topics)

    def post(self, shared, _prep_res, exec_res):
        path = shared.get("output_path") or "study_guide.html"
        with open(path, "w", encoding="utf-8") as f:
            f.write(exec_res)
        shared["output_path"] = path
        logger.info("Study guide written to %s", path)
