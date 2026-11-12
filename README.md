# Dro

Dro is a fruit fly that makes one decision a day.

More exactly: Dro is a simulation of the complete wiring diagram of a male
fruit fly's nervous system (165,122 neurons, 10.4 million connections). Once
a day a GitHub Actions job shows it two options, counts which way its
steering neurons fire, and commits the result to this repository.

Dro is not conscious, not alive and not an "uploaded" fly. It is a wiring
diagram with a very simple neuron model on top.

Status on 2026-11-12: the neuron model passes a check against a published
result and the pictures reach the steering neuron. Of 24 test pairs, 18 gave
the same winner in at least 16 of 20 runs. In 17 of those 18 the winner is
the picture with more contrast, a number the rig computes before the brain
runs. See "Known limitations".

## Who did what

Every run log says which part came from the fly and which from the rig
around it. The split never changes:

| The fly | The rig (code and a human) |
| --- | --- |
| Where each of its object-detecting cells looks | The question and the two options |
| How their firing spreads and competes between the two sides | Drawing the options as pictures |
| Which side its steering neuron fired on | The early vision: turning picture contrast into firing of those cells |
| Therefore: the choice | The rule that reads a turn as a choice |
| | Every word written about the result |

## Quick start

Python 3.12 or newer.

```bash
pip install -r requirements.txt

# One time: download three public tables (about 1.1 GB) and compile the graph.
python -m dro.graph --raw data/raw --out data/compiled

# Ask the fly the question in question.json.
python -m dro.decide --question question.json --graph data/compiled

# Optional: check the model against a published result (about a minute).
python -m dro.sanity --graph data/compiled
```

The build takes a few minutes, most of it download, and needs about 2 GB of
memory. One decision takes about a quarter of a minute. No GPU is needed.

To change the question, edit `question.json`:

```json
{
  "question": "Tabs or spaces?",
  "a": "tabs",
  "b": "spaces",
  "repeatability": "Measured with python -m dro.repeat: tabs won 20 of 20 runs."
}
```

An option is either a short text or the path of an image file next to
`question.json`. `repeatability` is optional: a sentence on how often this
pair gave the same winner when measured. It is copied into the run log
unchanged. Measure a new pair with `python -m dro.repeat` before asking it;
a pair that has not been measured may be a coin toss.

## How a decision is made

1. **Picture.** Each option is drawn as a 96 x 96 grayscale picture. Text is
   drawn dark on a bright page. The fly cannot read: to it, text is a texture.
2. **Early vision, done by the rig.** The picture is not fed into the eye.
   It is handed to the LC10a cells, about 140 cells per side that respond to
   visual objects. Where each cell looks is taken from the wiring. How
   strongly it fires is a rule of the rig: the more contrast the picture has
   in that spot, the more input, up to 150 spikes a second. A uniform spot
   gives none.
3. **Two trials.** Trial 1 shows option A to the left eye and option B to
   the right eye. Trial 2 swaps them, so a built-in preference for one side
   cancels out.
4. **Readout.** In each trial the spikes of the steering neuron DNa02 are
   counted on the left and on the right. More spikes on one side is read as
   a turn towards that side, and so towards the option shown there.
5. **Choice.** The option the fly turned towards more, summed over both
   trials, wins. Equal sums are logged as `undecided`.

Between step 2 and step 4 everything is the simulated brain: LC10a excites
neurons of the anterior optic tubercle, these excite DNa02 of their own side
and inhibit the other side.

The random seed is derived from the date and the question, so a run cannot
be repeated until a nicer answer comes out.

## The daily run

`.github/workflows/decide.yml` runs every day at 06:23 UTC and can also be
started by hand from the Actions tab. On a free GitHub-hosted runner the
first run took 63 seconds in all: 18 for downloading the tables and building
the graph, 13 for the decision. It restores the compiled graph from the
Actions cache (the first run builds it), asks the question in `question.json`
and commits two files to `runs/`:

- `YYYY-MM-DD.json`: question, options, choice, what the rig's contrast
  number alone would have chosen, input rates and spike counts per trial,
  seed, model constants, graph fingerprint.
- `YYYY-MM-DD.png`: which neurons fired when in trial 1.

Nothing is posted anywhere. Publishing is a human's job.

## From a log to a post

```bash
python -m dro.draft                        # newest log in runs/
python -m dro.draft runs/2026-11-12.json   # a particular log
python -m dro.draft --llm                  # worded by a language model
```

This writes a draft to `drafts/`, which is not committed. A draft holds the
post in the persona's voice, a footer, and notes for the person who edits
it. The post comes from a fixed template, or with `--llm` from a language
model that is given only the question, the winner and the spike counts
(`pip install anthropic` and an API key in `ANTHROPIC_API_KEY`).

The footer is built from the log by code, never by the language model. It
says what the fly decided, what the rig did, whether the fly agreed with the
rig's contrast number, and who worded the post:

```text
Decided by the fly: "tabs", 33 steering spikes against 0.
Done by the rig: the question, the two pictures and the early vision. The picture with more contrast usually wins; today it did.
Worded from a template, edited by the human.
Dro is a simulation of a fly's wiring diagram. It is not alive and it cannot read.
```

A pair without a `repeatability` note gets a warning in the footer that it
may be a coin toss.

## Layout

| Path | What it holds |
| --- | --- |
| `dro/graph.py` | Downloads the release tables and compiles the signed graph |
| `dro/sim.py` | The neuron model and the simulation loop |
| `dro/stimulus.py` | Options to pictures, pictures to input for the LC10a cells |
| `dro/decide.py` | The two trials, the readout, the run log |
| `dro/sanity.py` | Check against a published result: sugar neurons drive MN9 |
| `dro/paths.py` | Graph search for routes to a target, and direct tests of them |
| `dro/repeat.py` | Runs one pair many times: how often does the same option win? |
| `dro/draft.py` | Turns a run log into a draft post with the "who did what" footer |
| `question.json` | Today's question |
| `runs/` | One log and one picture per run |
| `tests/` | Tests on tiny hand-made networks (`python -m pytest`) |
| `docs/` | Concept, calibration notes, roadmap, one sample run |
| `CLAUDE.md` | Project guide for Claude Code |

## Model

All neurons are identical leaky integrate-and-fire units. `dro/sim.py` is a
step-by-step port of the published code of Shiu et al. (2024) with its
constants: rest and reset -52 mV, threshold -45 mV, membrane time constant
20 ms, synaptic time constant 5 ms, refractory period 2.2 ms, synaptic
delay 1.8 ms.

One constant is fitted: the strength of a synapse. It is the paper's single
free parameter, 0.275 mV there, fitted on another dataset. Here it is
0.10 mV, chosen by repeating the paper's first experiment on MaleCNS:
activating the sugar-sensing neurons of the mouthparts must make the
proboscis motor neuron MN9 fire, more strongly at higher input rates, while
activity stays within a few hundred neurons. `python -m dro.sanity` runs
this check. Nothing else is trained or fitted, and no two-option decision
was looked at when choosing the value. `docs/CALIBRATION_NOTES.md` has the
numbers.

Choices made in this repository, all of them open to change:

- Only neurons with status `Traced` are kept.
- Connections with fewer than 3 synapses are dropped.
- A connection's sign comes from the presynaptic neuron's consensus
  transmitter: acetylcholine excites; GABA, glutamate and histamine inhibit.
  Dopamine, serotonin and octopamine connections are dropped. Neurons with an
  unclear transmitter are treated as excitatory.
- Sugar-sensing neurons are taken to be the labellar types LB3a to LB3d,
  because of what they connect to. The release does not label taste quality.
- The picture enters at the LC10a cells, skipping the eye and the optic
  lobe. Each cell's view is the set of eye columns that feed it, directly or
  through one cell in between, weighted by synapse count.
- An LC10a cell's input rate is the local contrast of the picture in its
  view times 150 Hz.
- Only DNa02 is read. DNa01, the other steering neuron, has almost no
  excitatory visual input in this dataset.

## Known limitations

Read these before trusting an answer from a fly.

- **The rig's contrast number decides most choices.** A picture fed into
  the eye is lost two cells later in this model, so the rig computes the
  contrast of the picture and hands it to the LC10a cells. Of 24 pairs, each
  run 20 times, 18 gave the same winner at least 16 times, and in 17 of
  those the winner was the picture with more contrast. The brain passes the
  difference on and sharpens it; it rarely overturns it. Every log gives the
  input rate the rig produced for each option, so this can be checked.
- **One pair in four is a coin toss.** Pairs whose pictures have nearly the
  same contrast do not repeat ("ship on Friday / wait until Monday" split 9
  to 9). `python -m dro.repeat` measures any pair. Until a pair has been
  measured, do not present its answer as reliable.
- **Some choices rest on a handful of spikes.** With both eyes driven the
  two sides suppress each other, and four of the 24 pairs were decided by
  fewer than five spikes in total.
- **The right side dominates.** When both eyes are driven, the right
  steering neuron fires more than the left, in all 24 pairs. The dataset has
  about 20 % more synapses per cell in the right optic lobe than in the
  left, in nearly every cell type, and one neuron (AOTU019) that lets each
  side silence the other turns this into a lead. This is probably the
  reconstruction, not the animal. Swapping the sides between the two trials
  cancels it in the count. A correction was tried and rejected because it
  did not make the two sides behave alike.
- **Earlier choices were an artefact.** The first version of the simulator
  left out one step of the published model (clearing a neuron's input when
  it fires) and used a synapse strength fitted to another dataset. The
  network then ran away into activity in tens of thousands of neurons.
- **The synapse strength sits in a narrow window.** Slightly above 0.10 mV
  the olfactory system (antennal lobe and mushroom body) goes into
  self-sustained activity. Below about 0.09 mV MN9 no longer responds.
- **Left and right are not equal in the sanity check either.** It passes for
  sugar neurons on the right. On the left the early part of the circuit
  responds the same way, but MN9 stays silent: the motor neuron that side
  reaches has about a fourteenth of the input synapses of its twin in this
  dataset.
- **Mood is not usable yet.** The log reports firing rates of the dopamine
  neurons linked to reward (PAM) and punishment (PPL1). Both are zero.
- **Eye orientation is not verified.** Where each LC10a cell looks comes
  from the release's hexagonal column coordinates, but which way is up, and
  whether the two eyes mirror each other, has not been checked against the
  anatomy.
- **The sanity check is partial.** It was compared with the published code
  and its example notebook, not yet with the firing rates in the paper.

The next engineering goal is to move work from the rig to the wiring: a
stand-in for the optic lobe that is closer to what LC10a responds to in the
animal, and a measure of how often the brain's choice differs from the
choice by contrast alone.

## Data, credits and licences

- **Connectome:** MaleCNS v1.0 by the FlyEM Project Team at HHMI Janelia, the
  Cambridge Connectomics Group, the MRC Laboratory of Molecular Biology and
  Google Research. Licensed under
  [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/). Berg et al.,
  Cell 189:5504-5526 (2026), doi:10.1016/j.cell.2026.08.015.
  Download page: <https://male-cns.janelia.org/download/>.
  The data is not stored in this repository; it is downloaded at build time
  and its SHA-256 hashes are written to `data/compiled/info.json` and into
  every run log.
- **Neuron model:** Shiu et al., "A Drosophila computational brain model
  reveals sensorimotor processing", Nature (2024).
- **Code:** MIT, see `LICENSE`.
