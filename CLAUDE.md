# Dro: project guide for Claude Code

Dro is a persona built on a simulation of the male fruit fly connectome
(MaleCNS v1.0). Once a day a GitHub Actions job takes the next question from
a queue, shows the simulated brain its two options, reads a choice from a
steering neuron, commits a run log and a post, and sends the post to the
channels the owner (GitHub: DemonazGH) has switched on. The owner wants the
whole process to run without him and without a local setup.

Read `README.md` for how the pipeline works, `docs/CONCEPT.md` for the persona
and the formats, `docs/CALIBRATION_NOTES.md` for what has been tried on
the model, and `docs/ROADMAP.md` for what to do next.

## Current state (2026-11-12)

- The pipeline runs end to end on the real connectome: build about 25 s
  after download, one decision about 12 s on one CPU core, about 2 GB of
  memory.
- Fifty tests pass (`python -m pytest -q`).
- The repository is public at `DemonazGH/Dro`. Both workflows have run on
  GitHub: "Tests" passes, "Dro decides" took 63 s by hand, including the
  first graph build, and about 50 s on the second run with the graph
  restored from the cache.
- **The neuron model is checked.** `dro/sim.py` matches the published code
  of Shiu et al. and the synapse strength is re-fitted to 0.10 mV with the
  paper's sugar-to-MN9 experiment (`python -m dro.sanity` passes for the
  right side). There is no runaway any more.
- **The picture enters at LC10a and DNa02 is the only readout.** A picture
  fed into L1 and L2 is lost one step later (experiment 14), so the rig
  computes local contrast and drives the LC10a cells, whose views come from
  the wiring (experiment 15). The rule was fixed before any decision was
  run; do not change it to improve a result.
- **The choice repeats for 34 of 42 pairs, and mostly follows the rig.**
  The same-picture control passes. 34 of 42 pairs give the same winner in
  at least 16 of 20 runs; in 30 of those the winner is the picture with
  more contrast, which the rig computes (experiments 21 and 22). Say so
  whenever a result is described.
- **The right DNa02 dominates** whenever both eyes are driven: the dataset
  has about 20 % more synapses in the right optic lobe, and AOTU019 turns
  that into a lead (experiment 18). A hemisphere correction failed its own
  symmetry test and is not used (experiment 19); do not reintroduce it
  without a new independent check. See the open questions in
  `docs/CALIBRATION_NOTES.md`.
- `questions.json` is the queue of questions. Every entry was measured
  with `dro.repeat` and carries the result in its `repeatability` field.
  The daily run asks the first entry not asked yet, then starts over with
  the one asked longest ago. The "Add a question" workflow measures a new
  pair and appends it only if one option wins at least 16 of 20 runs.
- Every log records `choice_by_input_alone`: what the rig's contrast
  number would have chosen without the brain.
- The daily run writes the post to `runs/YYYY-MM-DD.md`. The footer comes
  from the log, never from a language model. With the secret
  `ANTHROPIC_API_KEY` the text is worded by Claude; that path uses the
  Anthropic SDK and has been tested only with a stand-in client, not
  against the real API.
- **Fly Gate** (`action.yml`, `dro/gate.py`) shows the fly the lines a pull
  request adds against the lines it removes and comments with the verdict.
  It runs on pull requests to this repository through
  `.github/workflows/fly-gate.yml` and never blocks a merge. The comment
  always says it is not a code review. Its first real run was on
  DemonazGH/Dro#1. The Azure Pipelines version
  (`azure-pipelines/fly-gate.yml`, the Azure branch of `dro/gate.py`) has
  been tested only with a stand-in for the Azure DevOps API and has never
  run in a real project.
- **Portraits** (`dro/portrait.py`, `dro/portrait_bot.py`): a photo sent
  to the Telegram bot is answered with a poster of how the brain reacted to
  it. The "Portraits" workflow looks into the bot's inbox once an hour.
  Only administrators of the channel are served. It answered its first
  real photo from the owner on 2026-11-13.
- `v1` is the release branch that other repositories pin
  (`DemonazGH/Dro@v1`). Both the GitHub Action and the Azure template run
  this repository's code at that branch. Move it forward with
  `git push origin main:v1` only when the tests on `main` pass and Fly Gate
  still works; never force it. Tags cannot be pushed from a Claude Code
  session, which is why it is a branch.
- `dro/publish.py` sends the post to Telegram when the secrets
  `TELEGRAM_BOT_TOKEN` and `TELEGRAM_CHAT_ID` exist. Both secrets are set
  and the first post reached the owner's channel on 2026-11-12, sent by the
  "Send the latest post again" workflow. A delivery from the scheduled
  daily run has not been seen yet. No other channel is automated.

## Commands

```bash
pip install -r requirements.txt pytest
python -m pytest -q                                   # tests, under 1 s, no data needed
python -m dro.graph --raw data/raw --out data/compiled  # one-time build, downloads ~1.1 GB
python -m dro.decide --graph data/compiled            # next question in questions.json
python -m dro.decide --date 2026-11-12 --no-raster    # fixed date = fixed seed
python -m dro.sanity --graph data/compiled            # sugar neurons to MN9, ~1 min
python -m dro.paths rank DNa02 --side R               # which visual types lead to DNa02
python -m dro.paths drive LC10a --side R              # fire LC10a, read the steering neurons
python -m dro.repeat --a yes --b no                   # same pair, 20 seeds, ~4 min
python -m dro.repeat --a yes --b no --question "Yes or no?" --add-to questions.json
python -m dro.draft                                   # newest run log to drafts/
python -m dro.draft --llm                             # same, worded by a language model
python -m dro.publish runs/2026-11-13.md              # send a post; needs the Telegram variables
python -m dro.portrait photo.jpg --out portrait.png   # portrait through a fly's eyes
python -m dro.portrait_bot --peek                     # messages waiting for the bot
git diff main... | python -m dro.gate --patch -       # Fly Gate on any diff
```

## Code map

- `dro/graph.py`: download release tables, keep `Traced` neurons, sign
  connections by transmitter, write `graph.npz`, `neurons.csv`, `info.json`.
- `dro/sim.py`: leaky integrate-and-fire loop (`Params`, `simulate`), a
  step-by-step port of the reference `model.py`. Do not change the order of
  operations in a step without checking it against that file. It updates
  only neurons that have received input; any further speed-up must give the
  same spikes, neuron for neuron (experiment 20).
- `dro/sanity.py`: the sugar-to-MN9 check (`run`, `verdict`). Run it after
  any change to `sim.py`, `graph.py` or the synapse strength.
- `dro/paths.py`: graph search for excitatory routes to a target (`rank`,
  `path_strength`) and direct tests of a route (`drive`).
- `dro/stimulus.py`: option to picture (`render`), where each LC10a cell
  looks (`views`), the contrast rule (`local_contrast`), picture to LC10a
  input (`input_rates`).
- `dro/decide.py`: the question queue (`next_question`), two
  counterbalanced trials, DNa02 readout, run log, raster picture, CLI.
- `dro/repeat.py`: one pair over many seeds (`run`, `summary`), the
  sentence on what was measured (`note`) and the queue writer
  (`add_to_queue`). A measuring tool only; never use it to choose a seed
  for a real decision.
- `dro/draft.py`: run log to post (`facts`, `template_post`, `llm_post`,
  `acceptable`, `footer`, `editor_notes`, `post_text`). `anthropic` is
  imported only for `--llm` and is not in `requirements.txt`; the daily job
  installs it only when the key exists.
- `dro/telegram.py`: the calls to the Telegram Bot API. Standard library
  only and no imports from the project, so it works before the
  simulation's dependencies are installed.
- `dro/publish.py`: sends a post to Telegram (`send_telegram`).
- `dro/portrait.py`: photo to poster (`load_square`, `look`, `save_poster`,
  `make`). The seed comes from the photo's bytes.
- `dro/portrait_bot.py`: answers photos in the bot's inbox (`waiting`,
  `administrators`, `serve`). It imports the simulation only when there is
  a photo to look at, so `--peek` runs on bare Python.
- `dro/gate.py`: Fly Gate (`changed_lines`, `look`, `comment`,
  `post_comment` for GitHub, `azure_context` and `post_azure_thread` for
  Azure DevOps). Talks to both APIs with the standard library.
- `action.yml`: Fly Gate as a composite GitHub Action. Other repositories
  use it as `DemonazGH/Dro@v1`: the action installs `requirements.txt` and
  runs `dro.graph` and `dro.gate` from the checked-out action.
- `azure-pipelines/fly-gate.yml`: the same as steps of an Azure Pipelines
  job. It clones this repository at the branch given by its `ref` parameter,
  cuts the diff from the merge commit the build checked out and passes it
  to `dro.gate --patch`.
- `.github/workflows/`: `decide.yml` (daily run), `add-question.yml`
  (measure a pair and queue it), `publish.yml` (send the newest post again
  after a failed delivery), `portraits.yml` (hourly look into the bot's
  inbox), `fly-gate.yml` (Fly Gate on this repository's pull requests),
  `tests.yml`.

## Rules

- **English only.** All code, comments, docs, logs and commit messages in
  this repository are in English. The owner chats in Russian; reply to him in
  Russian, write files in English.
- **Honesty is the product.** Never describe Dro as conscious, alive or an
  uploaded fly. Every log and every post keeps the "who did what" split
  between the fly and the rig. Do not hide or soften known limitations.
- **Do not tune for a nicer answer.** The seed comes from the date and the
  question. Never add a way to rerun until the result looks good. Model
  changes must be justified by neuroscience or by a sanity check, not by the
  output of a particular question.
- **Data stays out of git.** `data/` is ignored. The connectome is downloaded
  at build time; its SHA-256 hashes go into `info.json` and every run log.
- **MaleCNS only.** It is CC BY 4.0, so any use is allowed with
  attribution. Do not add FlyWire data: it is reported to be CC BY-NC, which
  would limit what can be done with this project. Keep the attribution text in
  `README.md` and in `dro/decide.py` (`ATTRIBUTION`).
- **Posting is automatic only where the owner switched it on.** A channel
  is switched on by adding its secrets, never by code alone. Every automatic
  post says in its footer that no human edited it. Do not add a channel
  whose rules forbid automated accounts. Workflows may write to `runs/` and
  to `questions.json`, and nothing else.
- **The footer is never optional.** No code path may publish a post without
  the footer built by `dro/draft.py`.
- **Photos of people are personal data.** The portrait bot serves only
  administrators of the channel. Do not open it to everyone without the
  owner's decision and a privacy notice. Never store a photo or a poster in
  the repository, in an artifact or in a log, and never log who wrote.
- **No secrets in the repository.** Keys go into GitHub Actions secrets.
- **Dro gives no financial, medical or legal advice**, not even as a joke
  format. No tokens or coins.
- Keep dependencies small: numpy, scipy, pandas, pyarrow, pillow, matplotlib.
  The daily job must fit a free GitHub-hosted runner without a GPU.
- Changing `dro/graph.py` invalidates the Actions cache key on purpose, which
  triggers a rebuild and a 1.1 GB download. Do it deliberately.
- Record every calibration experiment, including failed ones, in
  `docs/CALIBRATION_NOTES.md` with the exact settings and numbers.

## Publishing the repository

The repository `DemonazGH/Dro` is public since 2026-11-12. Everything pushed
is visible to anyone, `docs/CONCEPT.md` included. The daily job and the
"Add a question" workflow commit to `main`; pull before pushing.
