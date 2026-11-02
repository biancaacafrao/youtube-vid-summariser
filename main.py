import logging
import sys
import webbrowser
from pathlib import Path

from flow import create_study_guide_flow
from utils.get_youtube_transcript import extract_video_id


def main():
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    logging.getLogger("httpx").setLevel(logging.WARNING)

    url = sys.argv[1] if len(sys.argv) > 1 else input("YouTube link: ").strip()
    shared = {
        "url": url,
        "transcript": None,  # FetchTranscript
        "topics": None,  # ExtractTopics, filled in by ExplainTopics
        "output_path": f"study_guide_{extract_video_id(url)}.html",  # RenderHTML
    }

    create_study_guide_flow().run(shared)

    n_questions = sum(len(t["questions"]) for t in shared["topics"])
    print(f"\n{len(shared['topics'])} topics, {n_questions} questions")
    for i, t in enumerate(shared["topics"], 1):
        print(f"  {i}. {t['title']}")
    path = Path(shared["output_path"]).resolve()
    print(f"\nStudy guide: {path}")
    webbrowser.open(path.as_uri())


if __name__ == "__main__":
    main()
