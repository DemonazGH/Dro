# Roadmap

Ordered. Do not start a later step while an earlier one is open, unless the
owner says so.

## 1. Get the repository live

- [x] Owner creates the public repository `DemonazGH/Dro`.
- [x] Push the current state.
- [x] Run the "Tests" workflow and fix whatever fails on GitHub. It passed
      on the first push, 15 tests.
- [x] Run "Dro decides" by hand once. The graph build and the commit of the
      run log work; the whole job took 63 s. The log matches a run of the
      same date on another machine spike for spike.
- [x] Check that the second run restores the graph from the cache instead
      of building it again. It does: the build step is skipped and the job
      takes about 50 s.

## 2. Calibrate the model

Goal: a regime where activity reaches the steering neurons without runaway,
and the choice depends on the options more than on the seed.

- [x] Sanity check: reproduce one published result of Shiu et al. on this
      graph. Done for sugar neurons to MN9 on the right side, against the
      published code (`python -m dro.sanity`). It exposed an error in the
      simulator and a synapse strength that did not fit this dataset; both
      are fixed.
- [ ] Postponed: compare the check with the firing rates printed in the
      paper. Needs the paper, which was not reachable so far.
- [x] Find the routes from the eye to the steering neurons
      (`python -m dro.paths`). LC10a and LLPC1 lead to DNa02 of the same
      side, and that last part works in the model. The picture never gets
      that far: it is lost one step after L2.
- [x] Place the picture on the LC10a cells and read DNa02 only. The
      picture now reaches the steering neuron.
- [ ] Postponed: work through the open questions in
      `docs/CALIBRATION_NOTES.md`.
- [x] Add a repeatability check (`python -m dro.repeat`). Result: 18 of 24
      pairs give the same winner in at least 16 of 20 runs.
- [x] Add a control: the same option on both sides comes out near 50 / 50
      (7 to 10, 8 to 8 and 8 to 12 in three pictures).
- [x] Find the cause of the right side's dominance: more synapses in the
      right optic lobe of the dataset, turned into a lead by AOTU019. A
      correction was tried and rejected.
- [x] Measure a few dozen pairs and report the share that repeat.
- [x] Put the winner by contrast alone into every log, next to the brain's
      winner (`choice_by_input_alone`). In the 24 measured pairs the
      majority winner went against the contrast in three: "pizza / salad",
      "tea / coffee" and "sleep / work".
- [ ] Postponed: try a stand-in for the optic lobe that leaves more to the
      wiring. Research with an open outcome.

The owner closed this step on 2026-11-12 with the two postponed items left
open, together with the open questions in `docs/CALIBRATION_NOTES.md`.
- [ ] Update "Known limitations" in `README.md` to match what is true.

Until this step is done, any public post must say that the rig does the
early vision and that the winner is usually the picture with more contrast.
A pair that has not been measured with `dro.repeat` may be a coin toss. Choices made with the first simulator
came from an error and must not be presented as the fly's.

## 3. Words

- [x] Script that turns a run log into a draft post in Dro's voice, with a
      fixed footer saying what the fly decided, what the rig did and who
      worded the post (`python -m dro.draft`).
- [x] Drafts go to a file for the owner to edit. No posting.
- [ ] Try `--llm` against the real API once the owner has a key.

## 3a. Run without the owner

- [x] A queue of measured questions (`questions.json`); the daily run takes
      the next one.
- [x] The daily run writes the post, commits it to `runs/` and shows it on
      the run page.
- [x] "Add a question" workflow: measures a pair in GitHub Actions and
      queues it if it repeats.
- [x] Telegram: the post and the activity picture are sent when the two
      secrets exist.
- [x] First real Telegram post: sent on 2026-11-12 by the "Send the latest
      post again" workflow, after a first attempt failed on a wrong chat id.
- [ ] See a post arrive from the scheduled daily run.
- [ ] Other channels, one at a time, where the platform allows automated
      posting and the owner has API access.

## 4. Fly Gate

- [x] GitHub Action that comments on a pull request with the fly's verdict
      (`action.yml`, `python -m dro.gate`). The comment carries the steering
      spikes as text; the picture is attached to the run, because a comment
      cannot embed an uploaded file.
- [x] See it run on a real pull request: DemonazGH/Dro#1, where the fly
      asked for changes to its own gate. 49 s, graph restored from the
      cache.
- [x] Tag a release so other repositories can pin a version (`v1`).
- [x] Same idea for Azure DevOps as a pipeline template
      (`azure-pipelines/fly-gate.yml`).
- [ ] See the Azure template run in a real Azure DevOps project.
- [ ] Package it as an Azure DevOps extension for the Marketplace.

## 5. Products and formats

See `docs/CONCEPT.md`: the "portrait through a fly's eyes" poster, the
"fly is my boss for 30 days" series, the Telegram pet bot.
