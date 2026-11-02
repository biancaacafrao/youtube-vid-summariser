import json
import logging

from utils.get_youtube_transcript import extract_video_id

logger = logging.getLogger(__name__)


def render_study_guide(url: str, topics: list) -> str:
    video_id = extract_video_id(url)
    data = {"url": url, "video_id": video_id, "topics": topics}
    # Escape "</" so transcript-derived text can never close the <script> tag.
    data_json = json.dumps(data, ensure_ascii=False).replace("</", "<\\/")
    n_questions = sum(len(t.get("questions", [])) for t in topics)
    logger.info("Rendering study guide: %s topics, %s questions", len(topics), n_questions)
    return _TEMPLATE.replace("__DATA__", data_json)


_TEMPLATE = r"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Video Study Guide</title>
<style>
  :root {
    --bg: #f7f7f5; --surface: #ffffff; --text: #1d1d1f; --muted: #6b6b70;
    --border: #e3e3e0; --accent: #3b5bdb; --accent-soft: #e8ecfd;
    --good: #2b8a3e; --good-soft: #e6f4ea; --bad: #c92a2a; --bad-soft: #fdeaea;
    --shadow: 0 1px 2px rgba(0,0,0,.05), 0 4px 16px rgba(0,0,0,.06);
  }
  @media (prefers-color-scheme: dark) {
    :root:not([data-theme="light"]) {
      --bg: #141416; --surface: #1e1e21; --text: #ececee; --muted: #9a9aa2;
      --border: #2e2e33; --accent: #7c95ff; --accent-soft: #252b45;
      --good: #6fcf86; --good-soft: #1c3324; --bad: #ff8a8a; --bad-soft: #3a2022;
      --shadow: 0 1px 2px rgba(0,0,0,.3), 0 4px 16px rgba(0,0,0,.3);
    }
  }
  * { box-sizing: border-box; }
  body {
    margin: 0; background: var(--bg); color: var(--text);
    font: 16px/1.6 system-ui, -apple-system, "Segoe UI", Roboto, sans-serif;
  }
  .wrap { max-width: 760px; margin: 0 auto; padding: 32px 16px 64px; }
  header { display: flex; gap: 16px; align-items: center; margin-bottom: 24px; }
  header img { width: 120px; aspect-ratio: 16/9; object-fit: cover; border-radius: 8px; flex-shrink: 0; }
  header h1 { font-size: 1.5rem; margin: 0 0 4px; line-height: 1.2; }
  header a { color: var(--muted); font-size: .9rem; word-break: break-all; }
  .tabs { display: flex; gap: 4px; background: var(--border); padding: 4px; border-radius: 10px; margin-bottom: 24px; }
  .tabs button {
    flex: 1; border: 0; background: transparent; color: var(--text); padding: 10px;
    border-radius: 7px; font: inherit; font-weight: 600; cursor: pointer;
  }
  .tabs button[aria-selected="true"] { background: var(--surface); box-shadow: var(--shadow); }
  .hidden { display: none !important; }

  /* Study view */
  details.topic {
    background: var(--surface); border: 1px solid var(--border); border-radius: 12px;
    margin-bottom: 12px; box-shadow: var(--shadow);
  }
  details.topic summary { list-style: none; cursor: pointer; padding: 16px 20px; display: flex; gap: 12px; }
  details.topic summary::-webkit-details-marker { display: none; }
  .num {
    flex-shrink: 0; width: 28px; height: 28px; border-radius: 50%; background: var(--accent-soft);
    color: var(--accent); font-weight: 700; display: grid; place-items: center; font-size: .9rem;
  }
  .topic h2 { font-size: 1.1rem; margin: 0; line-height: 1.4; }
  .topic .summary { color: var(--muted); font-size: .95rem; margin: 2px 0 0; }
  .topic .body { padding: 0 20px 20px 60px; }
  .topic h3 { font-size: .8rem; text-transform: uppercase; letter-spacing: .05em; color: var(--muted); margin: 16px 0 8px; }
  .qa { border-left: 3px solid var(--accent-soft); padding: 4px 0 4px 12px; margin-bottom: 12px; }
  .qa .q { font-weight: 600; margin: 0; }
  .qa .a { margin: 2px 0 0; }

  /* Test view */
  .meta { display: flex; justify-content: space-between; color: var(--muted); font-size: .9rem; margin-bottom: 8px; }
  .bar { height: 6px; background: var(--border); border-radius: 3px; overflow: hidden; margin-bottom: 20px; }
  .bar div { height: 100%; background: var(--accent); width: 0; transition: width .3s; }
  .card { perspective: 1200px; cursor: pointer; margin-bottom: 20px; }
  .card-inner {
    position: relative; min-height: 280px; transition: transform .5s; transform-style: preserve-3d;
  }
  .card.flipped .card-inner { transform: rotateY(180deg); }
  .face {
    position: absolute; inset: 0; backface-visibility: hidden; -webkit-backface-visibility: hidden;
    background: var(--surface); border: 1px solid var(--border); border-radius: 16px; box-shadow: var(--shadow);
    padding: 28px; display: flex; flex-direction: column; overflow-y: auto;
  }
  .face.back { transform: rotateY(180deg); background: var(--accent-soft); }
  .face .label { font-size: .8rem; text-transform: uppercase; letter-spacing: .05em; color: var(--muted); margin-bottom: 12px; }
  .face .text { font-size: 1.25rem; font-weight: 600; margin: auto 0; }
  .face.back .text { font-weight: 400; font-size: 1.1rem; }
  .face .hint { color: var(--muted); font-size: .85rem; margin-top: 16px; }
  .actions { display: flex; gap: 12px; }
  .actions button, .btn {
    flex: 1; padding: 14px; font: inherit; font-weight: 600; border-radius: 10px; cursor: pointer;
    border: 1px solid var(--border); background: var(--surface); color: var(--text);
  }
  .btn-primary { background: var(--accent) !important; color: #fff !important; border-color: var(--accent) !important; }
  .btn-good { background: var(--good-soft) !important; color: var(--good) !important; border-color: var(--good) !important; }
  .btn-bad { background: var(--bad-soft) !important; color: var(--bad) !important; border-color: var(--bad) !important; }
  .keys { text-align: center; color: var(--muted); font-size: .8rem; margin-top: 12px; }
  kbd { border: 1px solid var(--border); border-radius: 4px; padding: 0 5px; font: inherit; }

  /* Results */
  .results { background: var(--surface); border: 1px solid var(--border); border-radius: 16px; padding: 28px; box-shadow: var(--shadow); }
  .score { font-size: 3rem; font-weight: 800; line-height: 1; margin: 0; }
  .score-sub { color: var(--muted); margin: 4px 0 20px; }
  .missed-list { padding-left: 20px; }
  .missed-list li { margin-bottom: 10px; }
  .missed-list .a { color: var(--muted); display: block; }
  .results .actions { margin-top: 20px; flex-wrap: wrap; }

  @media (max-width: 520px) {
    header img { width: 88px; }
    .topic .body { padding-left: 20px; }
    .face { padding: 20px; }
    .face .text { font-size: 1.1rem; }
  }
</style>
</head>
<body>
<div class="wrap">
  <header>
    <img id="thumb" alt="">
    <div>
      <h1>Video Study Guide</h1>
      <a id="src" target="_blank" rel="noopener"></a>
    </div>
  </header>

  <div class="tabs" role="tablist">
    <button role="tab" id="tab-study" aria-selected="true">Study</button>
    <button role="tab" id="tab-test" aria-selected="false">Test yourself</button>
  </div>

  <section id="study"></section>

  <section id="test" class="hidden">
    <div id="quiz">
      <div class="meta"><span id="progress-label"></span><span id="score-label"></span></div>
      <div class="bar"><div id="bar"></div></div>
      <div class="card" id="card">
        <div class="card-inner">
          <div class="face front">
            <div class="label" id="front-topic"></div>
            <p class="text" id="front-text"></p>
            <div class="hint">Tap the card to see the answer</div>
          </div>
          <div class="face back">
            <div class="label">Answer</div>
            <p class="text" id="back-text"></p>
          </div>
        </div>
      </div>
      <div class="actions" id="flip-actions">
        <button class="btn-primary" id="btn-flip">Show answer</button>
      </div>
      <div class="actions hidden" id="grade-actions">
        <button class="btn-bad" id="btn-missed">Missed it</button>
        <button class="btn-good" id="btn-got">Got it</button>
      </div>
      <div class="keys"><kbd>Space</kbd> flip &middot; <kbd>1</kbd> missed &middot; <kbd>2</kbd> got it</div>
    </div>

    <div id="results" class="results hidden">
      <p class="score" id="final-score"></p>
      <p class="score-sub" id="final-sub"></p>
      <div id="missed-wrap">
        <h3>Worth another look</h3>
        <ol class="missed-list" id="missed-list"></ol>
      </div>
      <div class="actions">
        <button class="btn-primary" id="btn-retry">Retry missed</button>
        <button class="btn" id="btn-restart">Start over (shuffled)</button>
      </div>
    </div>
  </section>
</div>

<script id="data" type="application/json">__DATA__</script>
<script>
(function () {
  var data = JSON.parse(document.getElementById("data").textContent);
  var $ = function (id) { return document.getElementById(id); };

  function el(tag, cls, text) {
    var e = document.createElement(tag);
    if (cls) e.className = cls;
    if (text != null) e.textContent = text;
    return e;
  }

  // Header
  $("thumb").src = "https://img.youtube.com/vi/" + data.video_id + "/mqdefault.jpg";
  $("src").href = data.url;
  $("src").textContent = data.url;

  // Study view
  var study = $("study");
  data.topics.forEach(function (t, i) {
    var d = el("details", "topic");
    if (i === 0) d.open = true;
    var s = el("summary");
    s.appendChild(el("span", "num", String(i + 1)));
    var head = el("div");
    head.appendChild(el("h2", null, t.title));
    if (t.summary) head.appendChild(el("p", "summary", t.summary));
    s.appendChild(head);
    d.appendChild(s);

    var body = el("div", "body");
    body.appendChild(el("h3", null, "In simple terms"));
    String(t.explanation || "").split(/\n\s*\n/).forEach(function (para) {
      if (para.trim()) body.appendChild(el("p", null, para.trim()));
    });
    if ((t.questions || []).length) {
      body.appendChild(el("h3", null, "Questions"));
      t.questions.forEach(function (qa) {
        var box = el("div", "qa");
        box.appendChild(el("p", "q", qa.question));
        box.appendChild(el("p", "a", qa.answer));
        body.appendChild(box);
      });
    }
    d.appendChild(body);
    study.appendChild(d);
  });

  // Test view
  var allCards = [];
  data.topics.forEach(function (t) {
    (t.questions || []).forEach(function (qa) {
      allCards.push({ topic: t.title, question: qa.question, answer: qa.answer });
    });
  });

  var deck = [], pos = 0, got = 0, missed = [], flipped = false;

  function shuffle(arr) {
    var a = arr.slice();
    for (var i = a.length - 1; i > 0; i--) {
      var j = Math.floor(Math.random() * (i + 1));
      var tmp = a[i]; a[i] = a[j]; a[j] = tmp;
    }
    return a;
  }

  function start(cards) {
    deck = cards; pos = 0; got = 0; missed = [];
    $("quiz").classList.remove("hidden");
    $("results").classList.add("hidden");
    show();
  }

  function setFlipped(v) {
    flipped = v;
    $("card").classList.toggle("flipped", v);
    $("flip-actions").classList.toggle("hidden", v);
    $("grade-actions").classList.toggle("hidden", !v);
  }

  function show() {
    var c = deck[pos];
    // Reset the flip without animating, so the next answer isn't briefly visible.
    var inner = $("card").querySelector(".card-inner");
    inner.style.transition = "none";
    setFlipped(false);
    void inner.offsetWidth;
    inner.style.transition = "";
    $("front-topic").textContent = c.topic;
    $("front-text").textContent = c.question;
    $("back-text").textContent = c.answer;
    $("progress-label").textContent = "Card " + (pos + 1) + " of " + deck.length;
    $("score-label").textContent = got + " correct";
    $("bar").style.width = (pos / deck.length * 100) + "%";
  }

  function grade(correct) {
    if (!flipped) return;
    if (correct) got++; else missed.push(deck[pos]);
    pos++;
    if (pos < deck.length) show(); else finish();
  }

  function finish() {
    $("bar").style.width = "100%";
    $("quiz").classList.add("hidden");
    $("results").classList.remove("hidden");
    var pct = Math.round(got / deck.length * 100);
    $("final-score").textContent = got + " / " + deck.length;
    $("final-sub").textContent = pct + "% correct" +
      (pct === 100 ? " - you've got this video covered." : pct >= 70 ? " - nearly there." : " - review the topics and try again.");
    var list = $("missed-list");
    list.innerHTML = "";
    missed.forEach(function (c) {
      var li = el("li");
      li.appendChild(el("span", null, c.question));
      li.appendChild(el("span", "a", c.answer));
      list.appendChild(li);
    });
    $("missed-wrap").classList.toggle("hidden", missed.length === 0);
    $("btn-retry").classList.toggle("hidden", missed.length === 0);
  }

  $("card").addEventListener("click", function () { setFlipped(!flipped); });
  $("btn-flip").addEventListener("click", function () { setFlipped(true); });
  $("btn-got").addEventListener("click", function () { grade(true); });
  $("btn-missed").addEventListener("click", function () { grade(false); });
  $("btn-retry").addEventListener("click", function () { start(shuffle(missed)); });
  $("btn-restart").addEventListener("click", function () { start(shuffle(allCards)); });

  document.addEventListener("keydown", function (e) {
    if ($("test").classList.contains("hidden") || !$("results").classList.contains("hidden")) return;
    if (e.key === " ") { e.preventDefault(); setFlipped(!flipped); }
    else if (e.key === "1") grade(false);
    else if (e.key === "2") grade(true);
  });

  // Tabs
  function selectTab(name) {
    var isTest = name === "test";
    $("tab-study").setAttribute("aria-selected", String(!isTest));
    $("tab-test").setAttribute("aria-selected", String(isTest));
    $("study").classList.toggle("hidden", isTest);
    $("test").classList.toggle("hidden", !isTest);
  }
  $("tab-study").addEventListener("click", function () { selectTab("study"); });
  $("tab-test").addEventListener("click", function () { selectTab("test"); });

  if (allCards.length) start(allCards);
  else $("tab-test").disabled = true;
})();
</script>
</body>
</html>
"""


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    sample_topics = [
        {
            "title": "Elephants' trunks",
            "summary": "What the narrator finds cool about elephants.",
            "explanation": "Elephants have very long trunks.\n\nThe narrator thinks that is the coolest thing about them.",
            "questions": [
                {"question": "What is special about the elephants?", "answer": "They have really long trunks."},
                {"question": "Where is the narrator?", "answer": "In front of the elephants at the zoo."},
            ],
        },
        {
            "title": "Escaping test </script>",
            "summary": "Checks that tricky text can't break the page.",
            "explanation": "Text like <b>this</b> must show as plain text.",
            "questions": [{"question": "Is <i>this</i> escaped?", "answer": "Yes."}],
        },
    ]
    page = render_study_guide("https://www.youtube.com/watch?v=jNQXAC9IVRw", sample_topics)
    assert page.count("</script>") == 2, "data must not close the script tag early"
    with open("study_guide_sample.html", "w", encoding="utf-8") as f:
        f.write(page)
    print("wrote study_guide_sample.html")
