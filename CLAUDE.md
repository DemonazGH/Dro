# Dro: project guide for Claude Code

Dro is a persona built on a simulation of the male fruit fly connectome
(MaleCNS v1.0). Once a day a GitHub Actions job shows the simulated brain two
options, reads a choice from its steering neurons and commits a run log. The
owner (GitHub: DemonazGH) publishes posts about the results by hand.

Read `README.md` for how the pipeline works, `docs/CONCEPT.md` for the persona
and the formats, `docs/CALIBRATION_NOTES.md` for what has been tried on
the model, and `docs/ROADMAP.md` for what to do next.

## Current state (2026-11-12)

- The pipeline runs end to end on the real connectome: build about 25 s
  after download, one decision about 12 s on one CPU core, about 2 GB of
  memory.
- Sixteen tests pass (`python -m pytest -q`).
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
- **The choice repeats for 18 of 24 pairs, and mostly follows the rig.**
  The same-picture control passes. 18 of 24 pairs give the same winner in
  at least 16 of 20 runs; in 17 of those the winner is the picture with
  more contrast, which the rig computes (experiment 21). Say so whenever a
  result is described.
- **The right DNa02 dominates** whenever both eyes are driven: the dataset
  has about 20 % more synapses in the right optic lobe, and AOTU019 turns
  that into a lead (experiment 18). A hemisphere correction failed its own
  symmetry test and is not used (experiment 19); do not reintroduce it
  without a new independent check. See the open questions in
  `docs/CALIBRATION_NOTES.md`.
- `question.json` holds "tabs / spaces", a pair measured at 20 of 20. A new
  question must be measured with `dro.repeat` first and carry the result in
  its `repeatability` field.
- No post writing and no publishing code exists yet.

## Commands

```bash
pip install -r requirements.txt pytest
python -m pytest -q                                   # tests, under 1 s, no data needed
python -m dro.graph --raw data/raw --out data/compiled  # one-time build, downloads ~1.1 GB
python -m dro.decide --question question.json --graph data/compiled
python -m dro.decide --date 2026-11-12 --no-raster    # fixed date = fixed seed
python -m dro.sanity --graph data/compiled            # sugar neurons to MN9, ~1 min
python -m dro.paths rank DNa02 --side R               # which visual types lead to DNa02
python -m dro.paths drive LC10a --side R              # fire LC10a, read the steering neurons
python -m dro.repeat --a yes --b no                   # same pair, 20 seeds, ~4 min
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
- `dro/decide.py`: two counterbalanced trials, DNa02 readout, run log,
  raster picture, CLI.
- `dro/repeat.py`: one pair over many seeds (`run`, `summary`). A measuring
  tool only; never use it to choose a seed for a real decision.

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
- **Nothing is posted automatically.** Workflows may write files to `runs/`
  and nothing else. Publishing to any social network is done by the owner.
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
is visible to anyone, `docs/CONCEPT.md` included. The daily job commits to
`main`; pull before pushing.
