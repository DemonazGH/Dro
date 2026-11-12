"""Turn a run log into a draft post for a human to edit.

Usage::

    python -m dro.draft                      # newest log in runs/
    python -m dro.draft runs/2026-11-12.json
    python -m dro.draft --llm                # worded by a language model

The draft is written to ``drafts/``, which is not committed. Nothing is
posted anywhere; publishing is a human's job.

A draft has three parts:

1. The post, in the voice of the persona. By default it comes from a small
   set of fixed templates. With ``--llm`` a language model words it from the
   facts of the decision; that needs the ``anthropic`` package and an API key
   in the environment.
2. The footer. It is built from the log, never by the language model, and
   says what the fly decided, what the rig did and who wrote the words.
3. Notes for the editor: the numbers behind the post and what to check
   before publishing. These are not part of the post.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

from .decide import input_by_option

DEFAULT_MODEL = "claude-opus-5-5"
NOTES_MARKER = "--- notes for the editor, not part of the post ---"

DECIDED = (
    'They asked me: {question} I did not read the question. I cannot read. Two pictures came '
    'in, one per eye, and my steering neuron leaned toward "{winner}": {won} spikes to {lost}. '
    "That is the whole strategy. Most roadmaps have less evidence behind them.",
    "{question}\n\n165,122 neurons. No offsite, no alignment meeting, no slide deck. One side "
    'fired {won} times, the other {lost}. We are going with "{winner}". If you need a second '
    "opinion, ask a second fly.",
    "People keep asking how I make decisions. Today's was: {question} I looked at "
    '"{winner}" with one eye and "{loser}" with the other, then swapped. "{winner}" won, '
    "{won} spikes to {lost}. I have no idea what either word means. This has never slowed "
    "down a career.",
    "Leadership is turning toward something before the meeting ends. Today I turned toward "
    '"{winner}" ({won} spikes) and away from "{loser}" ({lost}). The question was: {question} '
    "I was not told the question. I rarely am.",
    '{question}\n\n"{winner}". Decided in two seconds of simulated time by a wiring diagram '
    "that has never met a banana it would not walk toward. {won} spikes for, {lost} against. "
    "Disagree and commit.",
    "I do not have opinions. I have a left steering neuron and a right one. Asked "
    '"{question}", they came out {won} to {lost} for "{winner}". Call it data-driven.',
)
UNDECIDED = (
    "{question}\n\nI looked at both options and my steering neuron fired exactly as much for "
    "each: {won} and {lost}. Some call this indecision. In consulting it is called a framework.",
    "Today's question: {question} Result: a tie, {won} spikes each way. I am comfortable "
    "holding two pictures in my eyes at once. That is called strategic ambiguity.",
    'No decision today. Asked "{question}", both sides fired {won} times. When a fly cannot '
    "choose between two things, it keeps walking straight. I recommend the same.",
)

SYSTEM_PROMPT = """\
You write short social posts in the voice of Dro S. Melanogaster, Chief Fruit \
Officer at FlyCorp: a self-assured corporate guru who is, in fact, a simulated \
wiring diagram of a fruit fly. He explains business, career and life through \
light, windows and overripe fruit, in a deadpan tone, and never breaks character.

You get the facts of one decision as JSON. Dro was shown two options as \
pictures, one per eye, and his steering neuron fired more toward one of them. \
He cannot read and does not know what the question or the options mean. The \
humour lives in that gap between the confident tone and the mechanism.

Write one post of 40 to 90 words in English, as plain text. Use the question, \
the winning option and the spike counts exactly as given, and do not add other \
numbers or facts. If the result is undecided, the post is about not deciding.

Dro is a simulation, so the post must not say or imply that he is conscious, \
alive or an uploaded fly. He gives no financial, medical or legal advice, not \
even as a joke; if the question touches those, he declines in character. \
Leave out hashtags, emoji and any sign-off: a footer saying who did what is \
added after your text."""


def facts(record: dict) -> dict:
    """The few things a post may state, taken from a run log."""
    toward = record["steering_spikes_toward"]
    choice = record["choice"]
    options = record["options"]
    other = {"a": "b", "b": "a"}
    if "choice_by_input_alone" in record:
        input_rate, by_input = record["input_rate_hz"], record["choice_by_input_alone"]
    else:  # logs written before these fields existed
        input_rate, by_input = input_by_option(record["trials"])
    decided = choice in other
    return {
        "question": record["question"],
        "decided": decided,
        "winner": options[choice] if decided else None,
        "loser": options[other[choice]] if decided else None,
        "won": toward[choice] if decided else toward["a"],
        "lost": toward[other[choice]] if decided else toward["b"],
        "choice": choice,
        "toward": toward,
        "by_input": by_input,
        "input_rate_hz": input_rate,
        "options": options,
        "repeatability": record.get("repeatability"),
        "seed": record["seed"],
        "date": record.get("date"),
    }


def template_post(known: dict) -> str:
    """A post from the fixed templates. The seed picks which one."""
    templates = DECIDED if known["decided"] else UNDECIDED
    return templates[known["seed"] % len(templates)].format(**known)


def llm_post(known: dict, model: str = DEFAULT_MODEL, client=None) -> str:
    """A post worded by a language model from the facts of the decision."""
    if client is None:
        import anthropic  # needed only for this path; not a dependency of the daily job

        client = anthropic.Anthropic()
    decision = {key: known[key] for key in ("question", "decided", "winner", "loser", "won", "lost")}
    response = client.beta.messages.create(
        model=model,
        max_tokens=16000,
        # If a safety classifier declines the request, the API retries it on
        # a fallback model within the same call.
        betas=["server-side-fallback-2026-07-01"],
        fallbacks="default",
        output_config={"effort": "medium"},
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": json.dumps(decision, ensure_ascii=False)}],
    )
    if response.stop_reason == "refusal":
        raise RuntimeError("the language model declined to write this post")
    text = "".join(block.text for block in response.content if block.type == "text").strip()
    if not text:
        raise RuntimeError("the language model returned no text")
    return text


def footer(known: dict, worded_by_model: bool) -> str:
    """Who did what. Built from the log, the same way for every post."""
    if known["decided"]:
        fly = f'Decided by the fly: "{known["winner"]}", {known["won"]} steering spikes against {known["lost"]}.'
    else:
        fly = f'Decided by the fly: nothing. Its steering neuron fired {known["won"]} times for each option.'
    if not known["repeatability"]:
        fly += " This pair has not been measured for repeatability; it may be a coin toss."

    rig = "Done by the rig: the question, the two pictures and the early vision. The picture with more contrast usually wins; "
    if known["by_input"] == "tie":
        rig += "today the two had the same contrast."
    elif not known["decided"]:
        rig += f'today that was "{known["options"][known["by_input"]]}", and the fly did not follow.'
    elif known["by_input"] == known["choice"]:
        rig += "today it did."
    else:
        rig += f'today that was "{known["loser"]}", and the fly went the other way.'

    words = (
        "Worded by a language model, edited by the human."
        if worded_by_model
        else "Worded from a template, edited by the human."
    )
    return "\n".join(
        [fly, rig, words, "Dro is a simulation of a fly's wiring diagram. It is not alive and it cannot read."]
    )


def editor_notes(known: dict, log_name: str, worded_by_model: bool) -> str:
    """Numbers and warnings for the person who edits the draft."""
    rate = known["input_rate_hz"]
    lines = [
        NOTES_MARKER,
        f"Log: {log_name}, date {known['date']}, seed {known['seed']}",
        f"Steering spikes: {known['options']['a']} {known['toward']['a']}, "
        f"{known['options']['b']} {known['toward']['b']}",
        f"Input the rig produced: {known['options']['a']} {rate['a']} Hz, {known['options']['b']} {rate['b']} Hz",
        f"Choice by input alone: {known['by_input']}; choice of the pipeline: {known['choice']}",
        f"Repeatability: {known['repeatability'] or 'NOT MEASURED. Run python -m dro.repeat before presenting this as reliable.'}",
    ]
    if known["won"] + known["lost"] < 5:
        lines.append("Warning: fewer than five steering spikes in total. Say that the margin is tiny.")
    source = "a language model" if worded_by_model else "a fixed template"
    lines += [
        f"The post above came from {source}. Before publishing:",
        '- If you rewrite it in your own words, change that footer line to "Written by the human: every word."',
        "- Keep the footer. Do not describe Dro as conscious, alive or an uploaded fly.",
        "- No financial, medical or legal advice, not even as a joke.",
    ]
    return "\n".join(lines)


def build(record: dict, log_name: str, use_model: bool = False, model: str = DEFAULT_MODEL, client=None) -> str:
    """The whole draft: post, footer, notes."""
    known = facts(record)
    post = llm_post(known, model, client) if use_model else template_post(known)
    return "\n\n".join([post, footer(known, use_model), editor_notes(known, log_name, use_model)]) + "\n"


def latest_log(runs: Path) -> Path:
    """The newest run log: latest date, then the highest run number of that date."""

    def order(path: Path) -> tuple:
        match = re.fullmatch(r"(\d{4}-\d{2}-\d{2})(?:-(\d+))?", path.stem)
        return (match.group(1), int(match.group(2) or 1)) if match else ("", 0)

    logs = [path for path in runs.glob("*.json") if order(path)[0]]
    if not logs:
        raise FileNotFoundError(f"no run logs in {runs}")
    return max(logs, key=order)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Turn a run log into a draft post.")
    parser.add_argument("log", nargs="?", type=Path, help="run log (default: newest in runs/)")
    parser.add_argument("--runs", type=Path, default=Path("runs"))
    parser.add_argument("--out", type=Path, default=Path("drafts"))
    parser.add_argument("--llm", action="store_true", help="let a language model word the post")
    parser.add_argument("--model", default=DEFAULT_MODEL)
    args = parser.parse_args(argv)

    log = args.log or latest_log(args.runs)
    record = json.loads(log.read_text(encoding="utf-8"))
    use_model = args.llm
    if use_model:
        try:
            import anthropic
        except ImportError:
            print("--llm needs the anthropic package: pip install anthropic", file=sys.stderr)
            return 2
        try:
            draft = build(record, log.name, True, args.model)
        except anthropic.AuthenticationError:
            print("the API key was not accepted; using a template instead", file=sys.stderr)
            use_model = False
        except anthropic.RateLimitError:
            print("the API is rate limited right now; using a template instead", file=sys.stderr)
            use_model = False
        except anthropic.APIStatusError as error:
            print(f"the API answered with status {error.status_code}; using a template instead", file=sys.stderr)
            use_model = False
        except (anthropic.APIConnectionError, anthropic.AnthropicError, RuntimeError) as error:
            print(f"no post from the language model ({error}); using a template instead", file=sys.stderr)
            use_model = False
    if not use_model:
        draft = build(record, log.name)

    args.out.mkdir(parents=True, exist_ok=True)
    target = args.out / f"{log.stem}.md"
    target.write_text(draft, encoding="utf-8")
    print(draft)
    print(f"draft: {target}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
