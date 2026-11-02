import logging
import re
from urllib.parse import parse_qs, urlparse

from youtube_transcript_api import YouTubeTranscriptApi

logger = logging.getLogger(__name__)

_WATCH_HOSTS = {"youtube.com", "www.youtube.com", "m.youtube.com"}
_SHORT_HOSTS = {"youtu.be"}
_VIDEO_ID_RE = re.compile(r"^[A-Za-z0-9_-]{11}$")


def extract_video_id(url: str) -> str:
    raw = (url or "").strip()
    if not raw:
        raise ValueError("YouTube URL is empty")

    if _VIDEO_ID_RE.match(raw):
        return raw

    parsed = urlparse(raw)
    host = (parsed.netloc or "").lower()

    if host in _SHORT_HOSTS:
        video_id = parsed.path.lstrip("/").split("/")[0]
    elif host in _WATCH_HOSTS:
        path = parsed.path or ""
        if path.startswith("/embed/") or path.startswith("/shorts/") or path.startswith("/live/"):
            video_id = path.strip("/").split("/")[1]
        else:
            video_id = parse_qs(parsed.query).get("v", [""])[0]
    else:
        raise ValueError(f"Not a YouTube URL: {url}")

    if not _VIDEO_ID_RE.match(video_id):
        raise ValueError(f"Could not extract a video id from: {url}")
    return video_id


def get_youtube_transcript(url: str) -> str:
    video_id = extract_video_id(url)
    logger.info("Fetching transcript for video_id=%s", video_id)
    fetched = YouTubeTranscriptApi().fetch(video_id)
    text = " ".join(snippet.text.strip() for snippet in fetched if snippet.text)
    text = re.sub(r"\s+", " ", text).strip()
    if not text:
        raise ValueError(f"Transcript is empty for video_id={video_id}")
    logger.info("Transcript length=%s", len(text))
    return text


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    assert extract_video_id("jNQXAC9IVRw") == "jNQXAC9IVRw"
    assert extract_video_id("https://www.youtube.com/watch?v=jNQXAC9IVRw") == "jNQXAC9IVRw"
    assert extract_video_id("https://youtu.be/jNQXAC9IVRw") == "jNQXAC9IVRw"
    assert extract_video_id("https://www.youtube.com/embed/jNQXAC9IVRw") == "jNQXAC9IVRw"
    assert extract_video_id("https://www.youtube.com/shorts/jNQXAC9IVRw") == "jNQXAC9IVRw"
    print("video id parsing: ok")

    sample_url = "c"
    transcript = get_youtube_transcript(sample_url)
    print(transcript[:400])
    print(f"... ({len(transcript)} chars)")
