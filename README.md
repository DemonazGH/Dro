# Dro

Dro is a fruit fly that makes one decision a day.

More exactly: Dro is a simulation of the complete wiring diagram of a male
fruit fly's nervous system (165,122 neurons, 10.4 million connections). Once
a day a GitHub Actions job shows it two options, counts which way its
steering neurons fire, and commits the result to this repository.

Dro is not conscious, not alive and not an "uploaded" fly. It is a wiring
diagram with a very simple neuron model on top.

Status on 2026-11-12: the neuron model passes a check against a published
result and the pictures reach the steering neuron. Of 42 test pairs, 34 gave
the same winner in at least 16 of 20 runs. In 30 of those 34 the winner is
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

# Ask the fly the next question in questions.json.
python -m dro.decide --graph data/compiled

# Optional: check the model against a published result (about a minute).
python -m dro.sanity --graph data/compiled
```

The build takes a few minutes, most of it download, and needs about 2 GB of
memory. One decision takes about a quarter of a minute. No GPU is needed.

None of this is needed to run Dro: the daily run, the posts and new
questions are all handled on GitHub, see "Running it without a computer".

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
started by hand from the Actions tab. GitHub starts scheduled workflows
late, or not at all, when it is busy, so the workflow tries again at 08:23,
10:23, 13:23 and 17:23; an attempt that finds today's log stops at once. On a free GitHub-hosted runner it takes
about a minute; the first run also downloads the tables and builds the
graph, later runs restore it from the Actions cache. Each run:

1. Takes the next question from `questions.json`: the first one that has
   not been asked yet, and once all have been asked, the one asked longest
   ago.
2. Asks the fly and writes `runs/YYYY-MM-DD.json` (question, options,
   choice, what the rig's contrast number alone would have chosen, input
   rates and spike counts per trial, seed, model constants, graph
   fingerprint) and `runs/YYYY-MM-DD.png` (every neuron that fired, in both
   trials, with the two steering neurons on top).
3. Writes the post to `runs/YYYY-MM-DD.md` and shows it on the page of the
   run.
4. Commits these three files.
5. Sends the post to the channels that are switched on.

### The post

A post has the text in the persona's voice and a footer. The text comes
from a fixed template, or from a language model that is given only the
question, the winner and the spike counts. The footer is built from the log
by code, never by the language model:

```text
Decided by the fly: "tabs", 33 steering spikes against 0.
Done by the rig: the question, the two pictures and the early vision. The picture with more contrast usually wins; today it did.
Worded from a template. Automatic post, no human edited it.
Dro is a simulation of a fly's wiring diagram. It is not alive and it cannot read.
```

It says what the fly decided, what the rig did, whether the fly agreed
with the rig's contrast number, and who worded the post. A question without
a `repeatability` note gets a warning that it may be a coin toss. A post
from the language model is thrown away, and a template used instead, if it
is too long or contains words such as "conscious", "alive" or "invest".

## Running it without a computer

Everything below is done in the browser, on the repository's GitHub page.

**Add a question.** Actions, "Add a question", "Run workflow". Give the
question and two short options. The workflow asks the fly the pair 20 times
with different seeds. If one option wins at least 16 times, the question
goes to the end of `questions.json` with a sentence on what was measured;
otherwise it is not added and the run page says why. To remove or reorder
questions, edit `questions.json` in the browser.

**Switch on Telegram.** Create a bot with @BotFather, make it an
administrator of the channel, and add two repository secrets (Settings,
"Secrets and variables", "Actions"): `TELEGRAM_BOT_TOKEN` and
`TELEGRAM_CHAT_ID` (the channel name such as `@flycorp`, or a numeric id).
From the next run on, the post and the activity picture go to the channel,
and the footer says that nobody edited it.

**Switch on the language model.** Add the secret `ANTHROPIC_API_KEY`. From
the next run on, the text of the post is worded by Claude instead of a
template. This path has not yet run against the real API.

**Send the latest post again.** Actions, "Send the latest post again",
"Run workflow". Use it after fixing a secret, when a run asked the fly but
could not deliver the post. It sends the newest post in `runs/` and asks
the fly nothing.

**Switch something off.** Delete its secret. To pause the whole thing,
disable the workflow on its page in the Actions tab.

Without any secrets the daily run still writes the post to `runs/`, where
it can be copied by hand.

### The same from a command line

```bash
python -m dro.repeat --a tabs --b spaces --question "Tabs or spaces?" --add-to questions.json
python -m dro.draft                      # newest log in runs/ to drafts/, with notes for an editor
python -m dro.draft --llm                # the same, worded by a language model
python -m dro.publish runs/2026-11-13.md # send a post; needs the Telegram variables
```

## Fly Gate

Fly Gate lets the fly look at pull requests. Add this workflow to any
repository:

```yaml
name: Fly Gate
on: pull_request
permissions:
  contents: read
  pull-requests: write
jobs:
  fly-gate:
    runs-on: ubuntu-latest
    steps:
      - uses: DemonazGH/Dro@v1
```

On every pull request, and on every push to it, the action:

1. Draws the first lines the pull request adds as one picture and the first
   lines it removes as another: about eight lines of twenty characters each.
2. Shows the simulated brain one picture per eye, then swaps the eyes, as in
   the daily run.
3. Posts one comment, and updates it on later pushes: "LGTM" if the
   steering neuron fired more towards the new lines, "changes requested" if
   towards the old ones, "no opinion" if equally. The comment shows the
   spikes of the steering neuron, says what the fly did and what the rig
   did, and says that this is not a code review.

`v1` is a branch of this repository that is moved forward only to states
of `main` whose tests pass.

The seed comes from the repository, the pull request number and the head
commit, so running the job again on the same commit gives the same answer.
The first run in a repository downloads the wiring diagram (about 1.1 GB)
and takes about a minute; later runs restore it from the cache.

By default the action never fails a job. With `enforce: "true"` it fails
when the fly prefers the old lines:

```yaml
      - uses: DemonazGH/Dro@v1
        with:
          enforce: "true"
```

Pull requests from forks get a read-only token, so there the verdict
appears on the page of the run instead of as a comment. The activity
picture is attached to the run as an artifact named `fly-gate`.

### In Azure Pipelines

`azure-pipelines/fly-gate.yml` holds the same thing as the steps of an Azure
Pipelines job. It has not yet run in a real Azure DevOps project.

The simplest way to use it: create a pipeline in your project with the
following file, and add that pipeline to the target branch as a build
validation policy (Project settings, Repositories, Policies).

```yaml
trigger: none
pool:
  vmImage: ubuntu-latest
resources:
  repositories:
    - repository: dro
      type: github
      name: DemonazGH/Dro
      ref: refs/heads/v1
      endpoint: github # the name of a GitHub service connection in your project
steps:
  - template: azure-pipelines/fly-gate.yml@dro
```

Without a GitHub service connection, copy the steps of
`azure-pipelines/fly-gate.yml` into the pipeline instead; they fetch this
repository themselves.

For a pull request in Azure Repos the verdict is posted as a comment thread
that is already closed, so it does not count as an unresolved comment, and
it is updated on later pushes. For that the build service of the project
needs the permission "Contribute to pull requests" on the repository
(Project settings, Repositories, Security). Without it, and for
repositories hosted elsewhere, the verdict appears on the summary page of
the build. `enforce: true` as a template parameter fails the job when the
fly prefers the old lines.

The job needs a Linux agent with Python 3.12 and internet access.

### From a command line

To ask the fly about any diff:

```bash
git diff main... | python -m dro.gate --patch -
```

Fly Gate decides nothing about the code. The fly cannot read; pictures of
code are dense, the two sides suppress each other, and the margin is often
a few spikes, which the comment then calls a coin toss.

## Portrait through a fly's eyes

A poster of how the simulated brain reacted to a photo
([example](docs/sample-portrait/grace.png), made from a public-domain
photograph of Grace Hopper).

The photo is cropped to a square and shown to both eyes for one second. The
poster shows what reached the eyes (32 x 32 points of light), what the
object-detecting cells reported (one dot per LC10a cell, at the spot where
that cell looks, over a faint copy of the photo, larger where the picture
has more contrast), and every
neuron that fired, with the two steering neurons on top. The same photo
always gives the same poster. The fly sees no face, only light and dark,
and the poster says so.

**By Telegram.** Send the bot a photo in a private chat; a caption becomes
the name on the poster. The "Portraits" workflow is scheduled to look into
the bot's inbox three times an hour and answer. GitHub skips many scheduled
runs, so an answer can take hours; to get it at once, start the workflow by
hand from the Actions tab. Only administrators of the channel are
served; anyone else is told that portraits are not open yet, and their
photo is not fetched. A photo is kept only for the seconds it takes to make
the poster, and nothing about a message is written to the log.

**From a command line.**

```bash
python -m dro.portrait photo.jpg --out portrait.png --name "Grace"
```

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
| `dro/draft.py` | Turns a run log into a post with the "who did what" footer |
| `dro/publish.py` | Sends a post to the channels that are switched on |
| `dro/portrait.py` | Portrait through a fly's eyes: a photo in, a poster out |
| `dro/portrait_bot.py` | Answers photos sent to the Telegram bot with portraits |
| `dro/telegram.py` | The calls to the Telegram Bot API |
| `dro/gate.py` | Fly Gate: shows the fly a pull request and comments on it |
| `action.yml` | Fly Gate as a GitHub Action for other repositories |
| `azure-pipelines/fly-gate.yml` | Fly Gate as the steps of an Azure Pipelines job |
| `questions.json` | The queue of questions, each measured before it was added |
| `runs/` | One log and one picture per run |
| `tests/` | Tests on tiny hand-made networks (`python -m pytest`) |
| `docs/` | Concept, calibration notes, roadmap, a sample run and a sample portrait |
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
  contrast of the picture and hands it to the LC10a cells. Of 42 pairs, each
  run 20 times, 34 gave the same winner at least 16 times, and in 30 of
  those the winner was the picture with more contrast. The brain passes the
  difference on and sharpens it; it overturns it in about one pair in
  nine. Every log gives the
  input rate the rig produced for each option, so this can be checked.
- **One pair in five is a coin toss.** Pairs whose pictures have nearly the
  same contrast do not repeat ("ship on Friday / wait until Monday" split 9
  to 9). Such pairs are kept out of the question queue: a question is added
  only after it has been measured.
- **Some choices rest on a handful of spikes.** With both eyes driven the
  two sides suppress each other, and seven of the 42 pairs were decided by
  fewer than five spikes in total.
- **The right side dominates.** When both eyes are driven, the right
  steering neuron fires more than the left, in all 24 pairs where this was
  recorded. The dataset has
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
