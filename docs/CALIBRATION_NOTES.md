# Calibration notes

A log of what has been tried on the model, with numbers. Add new experiments
at the bottom. Keep failed ones.

## Setup for experiments 1 to 5 (2026-11-11 and 2026-11-12)

- Graph: MaleCNS v1.0, 165,122 traced neurons, 10,402,660 connections with
  3 or more synapses.
- Signs: acetylcholine +1; GABA, glutamate, histamine -1; dopamine,
  serotonin, octopamine dropped; unclear treated as +1.
- Transmitter counts among traced neurons: acetylcholine 103,718; glutamate
  29,296; GABA 22,055; histamine 5,910; unclear 3,602; dopamine 392;
  octopamine 101; serotonin 48.
- Model: the first version of `dro/sim.py` with the Shiu et al. 2024 constants
  (0.275 mV per synapse) unless stated. Experiment 7 shows that this version
  did not match the paper's code, so the numbers in experiments 1 to 5
  describe that version only.
- Input: Poisson spikes into L1 and L2 (3,534 cells with eye coordinates:
  1,749 left, 1,785 right). One input spike adds 68.75 mV of synaptic drive.
- Readout: spikes of DNa01 + DNa02 by soma side ("steering L / R").
- Machine: 2 CPU cores, about 4 s of wall time per 300 ms simulated in the
  active regime.

## Experiment 1: uniform drive, one eye or both, 300 ms

All L1/L2 of an eye driven at the same rate.

| Left eye | Right eye | Total spikes | Active neurons | DNa02 L / R | All descending L / R | PAM spikes | PPL1 spikes |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 150 Hz | 0 | 417,079 | 25,302 | 0 / 2 | 2,629 / 2,839 | 5,009 | 930 |
| 0 | 150 Hz | 502,500 | 26,178 | 5 / 0 | 3,455 / 3,593 | 6,203 | 1,140 |
| 150 Hz | 150 Hz | 596,852 | 31,431 | 4 / 0 | 3,274 / 3,392 | 6,226 | 1,146 |
| 150 Hz | 150 Hz, other seed | 592,142 | 31,452 | 4 / 0 | 3,285 / 3,361 | 6,162 | 1,142 |
| 120 Hz | 45 Hz | 113,435 | 9,666 | 0 / 0 | 0 / 3 | 0 | 0 |

Observations:

- One-eye drive produced DNa02 spikes on the opposite side, in both
  directions. The counts are tiny, so this is a hint, not a result.
- Symmetric drive gives a left bias (4 / 0), identical across seeds. The
  network is nearly deterministic once it is strongly driven.
- A modest drop in drive (150 to 120 Hz) removes all descending activity.

## Experiment 2: text as bright strokes on a dark page, 150 Hz max, 2 x 1 s

Mean picture brightness 0.06 to 0.11.

| Options | Seeds 1, 2, 3: steering towards a / b | Total spikes |
| --- | --- | --- |
| ship on Friday / wait until Monday | 0 / 0 in all three | about 293,000 |
| pizza / salad | 0 / 0 in all three | about 247,000 |
| yes / no | 0 / 2, 3 / 0, 0 / 2 | 150,000 to 570,000 |
| tea / coffee | 0 / 0 in all three | about 192,000 |

Activity stays in the optic lobes. Only "yes / no" sometimes ignited the rest
of the network, depending on the seed.

## Experiment 3: text as dark strokes on a bright page, 150 Hz max, 2 x 1 s

This is the current default.

| Options | Seed 1 | Seed 2 | Seed 3 |
| --- | --- | --- | --- |
| ship on Friday / wait until Monday | a 6, b 7 | a 9, b 10 | a 8, b 6 |
| pizza / salad | a 7, b 15 | a 13, b 17 | a 9, b 7 |
| yes / no | a 8, b 9 | a 12, b 6 | a 11, b 8 |
| tea / coffee | a 12, b 11 | a 6, b 12 | a 9, b 11 |

- Total spikes about 4.7 million per decision. PAM about 94 Hz, PPL1 about
  305 Hz per neuron: saturated.
- Right steering neurons fired 0 times in every trial. All steering spikes
  are on the left, so "towards a / b" is just the left count of trial 1
  versus the left count of trial 2.
- The winner changes with the seed in all four pairs. The choice is noise.

## Experiment 4: input strength sweep, pizza / salad, 500 ms per trial

| Picture style | Max rate | Total spikes per trial | Steering L / R | PAM, PPL1 rate |
| --- | --- | --- | --- | --- |
| bright on dark | 150 Hz | 62,000 | 0 / 0 | 0, 0 |
| bright on dark | 250 Hz | 96,000 | 0 / 0 | 0, 0 |
| bright on dark | 400 Hz | 830,000 to 845,000 | 10 / 0 and 7 / 0 | 72 Hz, 246 to 251 Hz |
| dark on bright | 30 Hz | 68,000 | 0 / 0 | 0, 0 |
| dark on bright | 50 Hz | 108,000 | 0 / 0 | 0, 0 |
| dark on bright | 70 Hz | 145,000 | 0 / 0 | 0, 0 |
| dark on bright | 100 Hz | 822,000 to 878,000 | 6 / 0 and 6 / 0 | 64 to 71 Hz, 229 to 247 Hz |

There is a sharp threshold between "quiet" and "runaway". No setting in
between was found.

## Experiment 5: weaker synapses, dark on bright, 500 ms per trial

Synapse strength lowered; the size of one input spike kept at 68.75 mV.

| mV per synapse | Max rate | Total spikes per trial | Steering L / R | Descending L / R | PAM, PPL1 rate |
| --- | --- | --- | --- | --- | --- |
| 0.11 | 100 Hz | 188,000 | 0 / 0 | 0 / 0 | 0, 0 |
| 0.11 | 150 Hz | 280,000 | 0 / 0 | 0 / 0 | 0, 0 |
| 0.15 | 100 Hz | 196,000 | 0 / 0 | 0 / 0 | 0, 0 |
| 0.15 | 150 Hz | 297,000 | 0 / 0 | 0 / 0 | 0, 0 |
| 0.20 | 100 Hz | 202,000 | 0 / 0 | 0 / 0 | 0, 0 |
| 0.20 | 150 Hz | 604,000 to 629,000 | 1 / 4 and 1 / 3 | about 2,650 / 3,230 | 13 Hz, 140 to 156 Hz |

Still two regimes. At 0.20 mV and 150 Hz the runaway is milder, 448
descending neurons are active and steering fires on both sides. This is the
closest point to a usable regime so far.

## Setup for experiments 6 to 23 (2026-11-12)

- Graph: as above. A second graph with 5 or more synapses per connection
  (6,185,843 connections) was built for comparison.
- Reference: the authors' Brian2 code, `model.py` and `example.ipynb` in
  <https://github.com/philshiu/Drosophila_brain_model>. The paper itself
  could not be opened from the machine these experiments ran on, so its
  published MN9 rates were not compared. The notebook says that activating
  21 sugar neurons gives "more than 400,000 spikes" in 30 one-second trials
  (about 13,000 per trial) and "about 400 neurons" active.
- Machine: 4 CPU cores, about 11 s of wall time per simulated second in the
  contained regime.
- All runs are 1,000 ms unless stated. "Active" means at least one spike.

## Experiment 6: finding the sugar pathway in MaleCNS

- MN9 exists once per side: body 10331 (`MN9_L`) and body 16949 (`MN9_R`).
  In the compiled graph `MN9_L` has 133 input connections (2,987 excitatory
  and 2,846 inhibitory synapses); `MN9_R` has 42 (218 and 219). The right
  MN9 is far less complete.
- The release labels the feeding circuit of Shiu et al. 2022 in the
  `synonyms` column (G2N-1, Usnea, FMIn, Zorro, Phantom, Clavicle, Fudog,
  Roundtree, Roundup, Rounddown, Sternum, Fdg and others), two neurons each.
- Taste quality is not labelled. Share of each taste neuron family's output
  synapses that land on the seven second-order sugar types (G2N-1, Usnea,
  FMIn, Zorro, Phantom, Clavicle, Fudog):

| Family | Neurons | Synapses onto second-order sugar neurons | Share of all output |
| --- | --- | --- | --- |
| LB3 (LB3a to LB3d) | 78 | 7,499 | 29.4 % |
| LB4 | 12 | 242 | 5.9 % |
| LB2 | 18 | 152 | 2.4 % |
| LB1 | 57 | 181 | 0.7 % |
| Pharyngeal (PhG) | 48 | 111 | 0.2 % |
| Taste peg | 60 | 0 | 0 % |

Decision: LB3a to LB3d are used as the sugar-sensing neurons (40 right,
37 left). This rests on connectivity, not on a receptor label.

## Experiment 7: the first `sim.py` against the reference code

Reading `model.py` showed four differences in the first version of
`dro/sim.py`:

1. The reference sets the synaptic drive `g` to zero when a neuron spikes.
   The port kept it.
2. The reference freezes `v` and `g` during the refractory period. The port
   froze only `v`.
3. The reference adds external input to `v`, so each input spike causes
   exactly one spike. The port added it to `g`.
4. In the reference, neurons with external input have no refractory period.

A reference-faithful simulator was written and each difference switched
back on its own. Right sugar neurons, seed 1:

| Variant | mV per synapse | Input | Spikes | Active neurons | MN9_L |
| --- | --- | --- | --- | --- | --- |
| Reference-faithful | 0.1375 | 100 Hz | 7,779 | 239 | 42 Hz |
| No reset of `g` on spike | 0.1375 | 100 Hz | 542,539 | 7,328 | 436 Hz |
| `g` decays while refractory | 0.1375 | 100 Hz | 7,610 | 211 | 39 Hz |
| Input into `g` | 0.1375 | 100 Hz | 5,647 | 153 | 23 Hz |
| Input neurons refractory | 0.1375 | 100 Hz | 7,559 | 217 | 45 Hz |
| First `sim.py` as it was | 0.1375 | 100 Hz | 24,861 | 824 | 222 Hz |
| Reference-faithful | 0.275 | 100 Hz | 952,135 | 15,665 | 55 Hz |
| No reset of `g` on spike | 0.275 | 100 Hz | 4,164,486 | 30,171 | 445 Hz |

The missing reset of `g` is the difference that matters: on its own it
multiplies activity about 70 times at 0.1375 mV. `dro/sim.py` now follows
the reference in all four points and integrates each step exactly, as
Brian2 does for these equations.

## Experiment 8: the paper's constants on MaleCNS

Reference-faithful model, 0.275 mV per synapse, right sugar neurons, seed 1.

| Input | Spikes (3+ synapses) | Active | MN9_L | Spikes (5+ synapses) | Active | MN9_L |
| --- | --- | --- | --- | --- | --- | --- |
| 10 Hz | 596,315 | 16,182 | 8 Hz | 547,244 | 15,432 | 7 Hz |
| 50 Hz | 244,591 | 6,171 | 250 Hz | 236,017 | 5,911 | 245 Hz |
| 100 Hz | 952,135 | 15,665 | 55 Hz | 239,360 | 5,888 | 256 Hz |
| 150 Hz | 838,869 | 15,945 | 134 Hz | 605,751 | 15,447 | 230 Hz |
| 200 Hz | 1,012,536 | 15,275 | 266 Hz | 792,396 | 15,187 | 245 Hz |

The check fails with the paper's value: thousands of neurons become active
even at 10 Hz and the MN9 rate is not graded. Raising the synapse threshold
from 3 to 5 does not help. This is expected to some degree: 0.275 mV is the
paper's one free parameter, fitted on FlyWire, and MaleCNS reports far more
synapses per neuron. The release table holds 311,833,243 synapses; the
compiled graph holds 103,443,120, a mean of 626 input synapses per neuron
(1,121 for central brain interneurons). FlyWire is usually quoted at about
50 million synapses for about 139,000 neurons, roughly 360 per neuron; that
figure comes from secondary sources and was not checked here.

## Experiment 9: synapse strength sweep, right sugar neurons

Reference-faithful model, graph with 3+ synapses, seeds 1, 2, 3.

| mV per synapse | Input | MN9_L, Hz | Active neurons | Spikes |
| --- | --- | --- | --- | --- |
| 0.07 | 200 Hz | 0 (seed 1 only) | 95 | 10,245 |
| 0.08 | 200 Hz | 0, 0, 0 | 107, 105, 105 | 10,804, 10,694, 10,714 |
| 0.09 | 200 Hz | 5, 0, 5 | 131, 129, 129 | 11,630, 11,437, 11,463 |
| 0.10 | 50 Hz | 0, 0, 0 | 76, 73, 74 | 2,564, 2,616, 2,674 |
| 0.10 | 100 Hz | 0, 0, 0 | 100, 99, 101 | 5,817, 5,746, 5,818 |
| 0.10 | 150 Hz | 5, 4, 3 | 131, 120, 127 | 9,071, 8,942, 9,055 |
| 0.10 | 200 Hz | 17, 20, 25 | 158, 154, 158 | 12,450, 12,278, 12,328 |
| 0.11 | 200 Hz | 40, 38, 42 | 183, 183, 193 | 13,341, 13,192, 13,319 |
| 0.12 | 50 Hz | 0, 0, 0 | 91, 87, 104 | 2,939, 2,960, 3,095 |
| 0.12 | 100 Hz | 11, 8, 11 | 129, 143, 127 | 6,623, 6,581, 6,612 |
| 0.12 | 150 Hz | 38, 35, 34 | 203, 179, 184 | 10,555, 10,385, 10,446 |
| 0.12 | 200 Hz | 69, 65, 69 | 252, 245, 246 | 14,723, 14,472, 14,460 |
| 0.13 | 200 Hz | 89, 82, 90 | 323, 295, 296 | 16,356, 15,860, 15,941 |
| 0.14 | 150 Hz | 92, 91, 99 | 340, 344, 368 | 13,477, 13,330, 13,841 |
| 0.14 | 200 Hz | 115, 117, 114 | 421, 6,450, 6,522 | 19,151, 236,569, 238,927 |
| 0.15 | 200 Hz | 136 (seed 1) | 7,017 | 148,192 |
| 0.175 | 200 Hz | 188 (seed 1) | 7,155 | 64,534 |
| 0.20 | 100 Hz | 92 (seed 1) | 11,013 | 562,566 |
| 0.25 | 100 Hz | 55 (seed 1) | 14,203 | 843,139 |

- From 0.09 to 0.13 mV the result has the shape of the published one: a few
  hundred active neurons, about 10,000 to 16,000 spikes, and an MN9 rate
  that rises with the input rate and repeats across seeds.
- At 0.14 mV and above a second, much larger population switches on. In a
  run at 0.1375 mV and 200 Hz it started at about 400 ms and added about
  5,000 central brain neurons within 100 ms. The most active types were
  Kenyon cells (KCg-m, KCab) and antennal lobe local and projection neurons
  (lLN1, lLN2, PNs): the olfactory system goes into self-sustained activity.
- The second-order sugar neurons respond at every strength tried, on the
  same side as the input (G2N-1: about 100 Hz at 0.10 mV and 200 Hz input).

## Experiment 10: left sugar neurons

| mV per synapse | Input | MN9, Hz | Active neurons | Spikes |
| --- | --- | --- | --- | --- |
| 0.10 | 100 Hz | 0, 0, 0 | 80, 78, 79 | 4,902, 4,910, 4,935 |
| 0.10 | 150 Hz | 0, 0, 0 | 100, 98, 103 | 7,660, 7,702, 7,715 |
| 0.10 | 200 Hz | 0, 0, 0 | 115, 116, 112 | 10,402, 10,397, 10,353 |
| 0.11 | 150 Hz | 0, 0, 0 | 106, 107, 125 | 8,024, 8,056, 8,137 |
| 0.11 | 200 Hz | 18, 20, 16 | 4,657, 4,681, 4,633 | 247,794, 265,140, 213,185 |
| 0.12 | 100 Hz | 0, 0, 0 | 105, 95, 104 | 5,393, 5,427, 5,444 |
| 0.12 | 150 Hz | 25, 22, 25 | 5,231, 5,263, 5,270 | 282,039, 265,767, 270,104 |

- On the left the olfactory ignition starts earlier: at 0.11 mV and 200 Hz.
  The ignited population is the same (Kenyon cells, antennal lobe neurons).
- Below ignition MN9 never fires for left input. The second-order neurons
  respond as on the right (at 0.10 mV and 200 Hz: G2N-1 93 against 101
  spikes, FMIn 97 against 101, Zorro 87 against 97, Clavicle 156 against
  166). The difference is further down: Roundup fires 5 times on the left
  against 39 on the right, and the MN9 that the left pathway reaches is the
  poorly reconstructed `MN9_R` (experiment 6).

## Decision: 0.10 mV per synapse

Rule: the largest value on a 0.01 mV grid at which sugar input of 10 to
200 Hz on either side, over three seeds, never activates more than 1,000
neurons. That value is 0.10 mV. At 0.10 mV the right-side check passes
(`python -m dro.sanity`: MN9 at 0, 0, 0, 3 to 5 and 17 to 25 Hz for 10, 50,
100, 150 and 200 Hz). The left-side check stays contained but reports a
silent MN9, for the reconstruction reason above.

What this value is and is not:

- It is the paper's free parameter re-fitted on this dataset with the
  paper's own first experiment. It was not chosen by looking at any
  two-option decision.
- The usable window is narrow: MN9 starts to respond at about 0.09 mV and
  the left side ignites at 0.11 mV. A single global strength is a blunt
  tool; open question 5 below is the better fix.
- The MN9 response at 0.10 mV is weak. The published model reaches MN9 at
  lower input rates.

## Experiment 11: the two-option picture in the corrected model

"ship on Friday" against "wait until Monday", seed 1, 500 ms per trial.
Rows show trial 1; trial 2 differed by less than 2 %.

| mV per synapse | Picture | Max rate | Spikes | Active, all in optic lobe unless noted | Steering L / R | Descending spikes |
| --- | --- | --- | --- | --- | --- | --- |
| 0.10 | dark on bright | 50 Hz | 82,737 | 4,700 | 0 / 0 | 0 |
| 0.10 | dark on bright | 100 Hz | 170,756 | 7,272 (1 visual projection) | 0 / 0 | 0 |
| 0.10 | dark on bright | 150 Hz | 268,827 | 9,492 (3 visual projection) | 0 / 0 | 0 |
| 0.10 | bright on dark | 150 Hz | 41,590 | 2,053 | 0 / 0 | 0 |
| 0.12 | dark on bright | 150 Hz | 283,752 | 10,399 (6 visual projection) | 0 / 0 | 0 and 1 |
| 0.13 | dark on bright | 150 Hz | 290,595 | 10,752 (8 visual projection, 2 central brain) | 0 / 0 | 0 and 2 |

The default pipeline (`python -m dro.decide --date 2026-11-12`, 2 x 1 s,
150 Hz, 0.10 mV) gives: undecided, 0 against 0 steering spikes, 1,085,284
spikes, about 9,950 active neurons per trial, reward and punishment rates
both 0, 27 s of wall time. `docs/sample-run/` now holds this run.

- There is no runaway any more. Activity stays in the optic lobes: about
  10,000 of 89,390 optic lobe neurons, almost no visual projection neurons,
  no descending neurons.
- So the earlier choices (experiment 3) were produced by the simulator
  error and the runaway, not by the pictures.
- In this dataset L1 is predicted glutamatergic (1,776 cells) and L2
  cholinergic (1,779 cells). Under the sign rule, driving L1 only inhibits
  its targets; all excitation enters through L2.

The stimulus, not the neuron model, is now what stops a decision from
reaching the steering neurons.

## Experiment 12: what feeds the steering neurons (graph search)

No simulation. Inputs of the four steering neurons in the compiled graph:

| Neuron | Input connections | Excitatory synapses | Inhibitory synapses | Direct from visual projection neurons (exc. / inh.) |
| --- | --- | --- | --- | --- |
| DNa02_R | 723 | 15,490 | 7,965 | 446 / 250 |
| DNa02_L | 701 | 15,681 | 7,606 | 324 / 224 |
| DNa01_R | 409 | 6,795 | 5,982 | 51 / 423 |
| DNa01_L | 399 | 6,357 | 5,511 | 58 / 461 |

- DNa02's largest direct visual input is LLPC1 of the same side (312
  synapses from 45 cells on the right, 167 from 27 on the left), then the
  horizontal-system cells HSS, HSE, HSN and H2 (4 to 47 synapses each).
  Other strong inputs: one ascending neuron AN03A008 (717 and 741), PFL3 of
  the opposite side (380 and 356 from 12 cells), and AOTU015, AOTU025,
  AOTU001 and AOTU012 of the same side.
- AOTU019 of the opposite side is predicted GABAergic and inhibits DNa02
  (289 and 297 synapses).
- DNa01 has almost no direct excitatory visual input. Its largest visual
  input is inhibitory: LT51 of the same side (423 and 439 synapses).

`python -m dro.paths rank DNa02 --side R` ranks visual projection types by
the summed strength of excitatory paths of one, two and three steps. A
connection counts as its share of the receiving neuron's input synapses and
shares are multiplied along a path.

| Target | Type, side | Cells | 1 step | 2 steps | 3 steps |
| --- | --- | --- | --- | --- | --- |
| DNa02_R | LC10a, R | 140 | 0 | 0.0171 | 0.0050 |
| DNa02_R | LLPC1, R | 142 | 0.0133 | 0.0064 | 0.0017 |
| DNa02_R | LC10d, R | 106 | 0 | 0.0096 | 0.0023 |
| DNa02_R | LC10a, L | 135 | 0 | 0.0044 | 0.0017 |
| DNa02_L | LC10a, L | 135 | 0 | 0.0164 | 0.0051 |
| DNa02_L | LLPC1, L | 143 | 0.0072 | 0.0056 | 0.0016 |
| DNa02_L | LC10d, L | 108 | 0 | 0.0106 | 0.0021 |
| DNa01_R | LPLC4, L | 48 | 0 | 0.0042 | 0.0004 |
| DNa01_R | LPC1, L | 115 | 0 | 0.0039 | 0.0007 |
| DNa01_L | LPC1, R | 109 | 0 | 0.0048 | 0.0008 |
| DNa01_L | LPLC4, R | 49 | 0 | 0.0046 | 0.0006 |

- DNa02 is reached from the eye of the same side, through LC10a and LC10d
  (two steps, via the AOTU neurons) and LLPC1 (one step). This matches the
  published role of LC10a in steering towards a visual object.
- DNa01 is reached more weakly and from the opposite eye.
- From L2 the shortest excitatory route to DNa02 of the same side has three
  steps and a summed strength of 0.00017 (right) and 0.00009 (left); with
  four steps 0.0010 and 0.0007. No excitatory path starts at L1, which is
  inhibitory under the sign rule.
- Inside the optic lobe, LLPC1 is fed mainly by T4a and T5a (about 170
  synapses per LLPC1 cell from each), the detectors of front-to-back motion.
  LC10a is fed by other LC10a cells (79 per cell), Tm5Y (57), LC9 (37),
  TmY21 (29) and Tm5a (23).

## Experiment 13: driving the candidates directly

`python -m dro.paths drive LC10a --side R`: every cell of a type on one side
fires at a fixed rate for 1 s, seed 1, 0.10 mV. Spikes of the steering
neurons in that second:

| Driven | Cells | Rate | DNa02 same side | DNa02 other side | DNa01 either side | Active neurons |
| --- | --- | --- | --- | --- | --- | --- |
| LC10a, R | 140 | 50 Hz | 62 | 0 | 0 | 313 |
| LC10a, R | 140 | 100 Hz | 107 | 0 | 0 | 465 |
| LC10a, R | 140 | 200 Hz | 169 | 0 | 0 | 799 |
| LC10a, L | 135 | 50 Hz | 72 | 0 | 0 | 308 |
| LC10a, L | 135 | 100 Hz | 111 | 0 | 0 | 412 |
| LC10a, L | 135 | 200 Hz | 168 | 0 | 0 | 554 |
| LLPC1, R | 142 | 50 Hz | 87 | 0 | 0 | 335 |
| LLPC1, R | 142 | 100 Hz | 142 | 0 | 1 | 685 |
| LLPC1, R | 142 | 200 Hz | 194 | 0 | 12 | 1,007 |
| LC10a, LC10c-1, LC10c-2, LC10d, R | 378 | 100 Hz | 175 | 0 | 0 | 1,035 |

Part of the LC10a cells of the right side (random subsets, seed 0):

| Cells driven | 100 Hz: DNa02_R | 200 Hz: DNa02_R |
| --- | --- | --- |
| 10 | 1 | 31 |
| 20 | 5 | 22 |
| 40 | 38 | 55 |
| 70 | 81 | 120 |

Both sides at once, LC10a, seeds 1, 2, 3:

| Left rate | Right rate | DNa02_L | DNa02_R |
| --- | --- | --- | --- |
| 100 Hz | 100 Hz | 38, 34, 29 | 28, 32, 27 |
| 50 Hz | 100 Hz | 0, 0, 1 | 48, 51, 49 |
| 100 Hz | 50 Hz | 50, 48, 43 | 1, 0, 0 |
| 80 Hz | 100 Hz | 17, 20, 17 | 36, 38, 35 |
| 100 Hz | 80 Hz | 37, 35, 36 | 17, 19, 15 |

- The last part of the route works in the model. DNa02 answers LC10a and
  LLPC1 of its own side in a graded way, the other DNa02 stays silent, and
  left and right behave alike. DNa01 hardly takes part.
- With both sides driven, the stronger side wins and the weaker side is
  suppressed, the same way round after swapping sides and in all three
  seeds. Equal drive gives a near tie with a small lean to the left (101
  against 87 spikes over three seeds).
- This is the first setting in which the readout follows the input and not
  the seed.

## Experiment 14: where the picture is lost

`L2` (893 cells with eye coordinates) of the right eye at 150 Hz, 500 ms,
seed 1. Mean rate per cell type on that side:

| mV per synapse | Tm1 | Tm2 | Tm4 | T5a to T5d | LC10a, LLPC1, HS | Active outside the optic lobe |
| --- | --- | --- | --- | --- | --- | --- |
| 0.10 | 14 Hz | 8 Hz | 13 Hz | 0 | 0 | 3 |
| 0.15 | 18 Hz | 11 Hz | 24 Hz | 0 | 0 | 37 |
| 0.20 | 20 Hz | 12 Hz | 31 Hz | 0 | 0 | about 1,400 |
| 0.275 | 21 Hz | 12 Hz | 39 Hz | 0 | 0 | about 16,000 |

- The input is lost at the second step. L2 at 148 Hz gives 8 to 14 Hz in
  Tm1, Tm2 and Tm4, and nothing in the motion detectors T5. Tm9, Tm3, Mi1
  and the T4 cells stay silent as well; they depend on L1 and L3.
- A stronger synapse does not help. At 0.275 mV the rest of the brain is in
  runaway and T5, LC10a and LLPC1 are still silent. This suggests that the
  steering spikes of experiments 1 to 5 did not come through the route of
  experiment 12.
- Driving L1 as well changes nothing downstream (it only inhibits).
- Only 15 cell types carry eye coordinates in the release, all of them
  inside the optic lobe. LC10a and LLPC1 carry none, so placing a picture on
  them needs positions derived through their inputs.

Conclusion: steady input into L1 and L2 cannot reach the steering neurons
in this model at any synapse strength. The optic lobe is the part that this
neuron model handles worst: its cells are graded, not spiking, and the
motion detectors need timing that identical point neurons do not have.

## Experiment 15: where each LC10a cell looks

LC10a cells carry no eye coordinates in the release. `dro/stimulus.py`
(`views`) derives each cell's view from the wiring:

- Sources: optic lobe cells with eye coordinates, from the 12 types that
  have them on both sides (C3, L1, L2, L5, Mi1, Mi4, Mi9, T1, Tm1, Tm2,
  Tm20, Tm9). C2, L3 and Tm4 have coordinates on the right only and are
  left out so both eyes are treated alike. 10,668 source cells on the
  right, 10,453 on the left.
- Every other optic lobe cell of that side is placed on the eye by the
  source cells that feed it (all synapses, any sign), if at least 5 of its
  input synapses come from source cells.
- An LC10a cell's view is its excitatory input from source cells, directly
  and through one placed cell in between, weighted by synapse count.

| | Right | Left |
| --- | --- | --- |
| LC10a cells | 140 | 135 |
| Share of a cell's excitatory input that the view accounts for (median) | 40 % | 35 % |
| Size of a view, standard deviation along the two picture axes (median) | 1.6 and 2.9 | 1.6 and 2.8 |
| Extent of the whole eye along the same axes | 35 and 65 | 34 and 64 |
| Effective number of source cells in a view (median) | 61 | 46 |

Check that does not use the coordinates of LC10a's own input: LC10a cells
synapse onto each other. Pairs joined by 10 or more synapses lie a median
of 6.4 units apart (right; 6.7 left), unconnected pairs 20.9 (21.1). Rank
correlation between synapse count and distance: -0.37 on both sides. The
derived positions therefore carry real neighbourhood structure. The views
cover the whole eye, more densely towards one corner.

## Decision: the rule from picture to LC10a

Fixed on 2026-11-12, before any two-option run with this input.

- Each option is drawn on a 96 x 96 picture and averaged into 3 x 3 pixel
  patches, as before. A source cell sees the patch at its eye position.
- An LC10a cell fires at `max rate x local contrast`. Local contrast is the
  standard deviation of the brightness its source cells see, weighted by
  the view, divided by 0.5 (the largest possible value) and capped at 1.
- Maximum rate: 150 Hz, the value the pipeline already used.
- Readout: DNa02 only, left against right, in two trials with the sides
  swapped.

Why contrast: LC10a responds to visual objects, not to the overall light
level. A uniform patch, bright or dark, gives no input under this rule. It
is still a stand-in for the optic lobe, chosen by the rig. The size of this
stand-in's say is logged in every run as the mean input rate per side.

What to expect, stated before the runs: experiment 13 showed that the
stronger side wins. So the option with more contrast in LC10a's view should
win, and repeat across seeds. If the two options give nearly equal input,
the outcome should be decided by noise.

## Experiment 16: repeatability and control with the LC10a input

`python -m dro.repeat --a <a> --b <b>`: the full pipeline (2 x 1 s, 150 Hz
maximum, 0.10 mV), 20 runs with seeds 10, 20, ... 200. The seeds are spaced
because the two trials of a run use seed + 1 and seed + 2; a first series
with seeds 1 to 20 shared random numbers between neighbouring runs and is
not reported.

"Input" is the mean LC10a rate the rig produced for that option, on the
left and on the right eye.

| Pair | Input a (L, R) | Input b (L, R) | a won | b won | Undecided | Mean steering spikes a / b |
| --- | --- | --- | --- | --- | --- | --- |
| yes / no | 34.5, 34.6 Hz | 23.7, 24.0 Hz | 20 | 0 | 0 | 66.3 / 13.1 |
| pizza / salad | 49.4, 51.0 Hz | 50.9, 52.9 Hz | 18 | 1 | 1 | 2.0 / 0.3 |
| tea / coffee | 27.8, 28.0 Hz | 40.3, 41.5 Hz | 13 | 5 | 2 | 17.9 / 16.6 |
| ship on Friday / wait until Monday | 44.4, 42.9 Hz | 42.3, 44.9 Hz | 9 | 9 | 2 | 71.1 / 69.6 |

Control, the same picture on both sides:

| Picture | "a" won | "b" won | Undecided | Mean DNa02 spikes per trial, left / right |
| --- | --- | --- | --- | --- |
| yes | 7 | 10 | 3 | 0.1 / 28.7 |
| coffee | 8 | 8 | 4 | 0.1 / 7.4 |
| ship on Friday | 8 | 12 | 0 | 37.6 / 60.4 |

- Activity stays contained in every run: at most 467 active neurons, 32,000
  to 50,000 spikes per decision, about 22 s of wall time.
- The control passes: with the same picture on both sides neither label is
  favoured.
- The repeatability target (same winner in 16 of 20) is met by two of four
  pairs. "yes / no" repeats with a wide margin. "pizza / salad" repeats, but
  on one to five spikes in total. "tea / coffee" and "ship / wait" do not.
- The expectation written down before the runs was only half right. "yes"
  has more input than "no" and wins. But "coffee" has much more input than
  "tea" and does not win, and "pizza" wins with slightly less input than
  "salad". More contrast does not simply win.
- **The right side dominates.** Whenever both eyes are driven, the right
  DNa02 fires more than the left, often against zero, even when the left
  eye gets the stronger input ("tea / coffee", trial 2: left 40.3 Hz, right
  28.0 Hz, mean spikes 0.7 left and 17.9 right). Swapping the sides cancels
  this in the count, but it leaves little room for the pictures to matter.

## Experiment 17: one eye at a time

Each picture shown to one eye, the other eye blank, 1 s, seed 1.

| Picture | Mean input | DNa02 of that side, left eye / right eye | AOTU019 of that side, left / right |
| --- | --- | --- | --- |
| no | 24 Hz | 112 / 125 | 179 / 201 |
| tea | 28 Hz | 111 / 119 | 195 / 224 |
| yes | 35 Hz | 112 / 109 | 228 / 256 |
| coffee | 41 Hz | 82 / 78 | 216 / 246 |
| wait until Monday | 43 Hz | 130 / 124 | 220 / 252 |
| ship on Friday | 44 Hz | 139 / 134 | 205 / 227 |
| pizza | 50 Hz | 57 / 54 | 251 / 271 |
| salad | 52 Hz | 45 / 56 | 246 / 271 |

- One eye alone drives DNa02 of its own side only, and left and right
  answer alike.
- The answer does not follow the amount of input: "no" (24 Hz) gives twice
  the spikes of "pizza" (50 Hz). Which cells are driven matters, not only
  how many. This part is the wiring's doing, not the rig's.
- AOTU019, which inhibits the DNa02 of the other side, fires 8 to 15 % more
  on the right in every picture. This is the likely source of the right
  side's dominance in experiment 16. Whether it reflects the animal or the
  reconstruction is not known: right LC10a cells have 799 input synapses on
  average in this dataset, left ones 639.

## Experiment 18: why the right side dominates

**The dataset has more synapses on the right.** Mean synapses per cell,
right divided by left, for cell types with at least 20 cells per side:

| Group | Types | Output, median (10th to 90th percentile) | Types with more on the right |
| --- | --- | --- | --- |
| Optic lobe cells | 163 | 1.22 (1.07 to 1.39) | 94 % |
| Visual projection neurons | 54 | 1.21 (1.07 to 1.34) | 98 % |
| Central brain interneurons | 24 | 1.04 (0.87 to 1.15) | 67 % |

Cell counts are equal on both sides (44,599 against 44,789 optic lobe
cells). The excess is the same in medulla, lobula and lobula plate types.
For LC10a: 966 output synapses per cell on the right, 842 on the left.
Right LC10a makes 7,580 synapses onto AOTU019, left LC10a 6,604; onto
AOTU025 3,722 against 3,296. From the AOTU neurons to DNa02 the two sides
are alike (for example AOTU019: 297 and 289).

A uniform excess in nearly every cell type of one optic lobe, with equal
cell counts, looks like a property of the reconstruction rather than of the
animal. This cannot be settled from the data here.

**AOTU019 turns the excess into dominance.** AOTU019 is fed by LC10a of its
own side and inhibits DNa02 of the other side. The same picture on both
eyes, 1 s, seeds 1 and 2, spikes of DNa02 left / right:

| Picture | Intact | Both AOTU019 silenced | Right AOTU019 silenced | Left AOTU019 silenced |
| --- | --- | --- | --- | --- |
| yes | 0 / 29, 0 / 28 | 81 / 94, 85 / 94 | 93 / 9, 96 / 7 | 0 / 112, 0 / 111 |
| coffee | 0 / 9, 0 / 6 | 69 / 60, 67 / 61 | 76 / 1, 76 / 1 | 0 / 79, 0 / 77 |

- Without AOTU019 the two sides answer almost alike. With it, the pair acts
  as a switch: whichever AOTU019 fires more silences the other side's
  DNa02. In the intact model the right AOTU019 fires about 20 % more
  (233 against 194 spikes for "yes").
- The switch also explains why strong pictures give few spikes: with both
  eyes driven the two sides suppress each other.
- With equal uniform drive of all LC10a cells the sides are close to equal
  (100 Hz: 38 / 28 and 34 / 32; 150 Hz: 50 / 53 and 58 / 56). The dominance
  appears with pictures, where fewer cells are driven and the switch is
  nearer its tipping point.

## Experiment 19: a hemisphere correction (not adopted)

Idea: scale the output of every right-side optic lobe cell and visual
projection neuron by the left-to-right ratio of mean output per cell of its
group (0.824 and 0.857). The factors come from the whole dataset, not from
any decision. Test: do the two sides then behave alike?

| Test, spikes of DNa02 left / right | No correction | With correction |
| --- | --- | --- |
| Same picture, "yes" | 0 / 29 | 2 / 11 |
| Same picture, "no" | 2 / 38 | 8 / 19 |
| Same picture, "tea" | 1 / 25 | 4 / 13 |
| Same picture, "ship on Friday" | 37 / 63 | 53 / 35 |
| Same picture, "wait until Monday" | 3 / 47 | 12 / 16 |
| Uniform, 100 Hz both sides | 38 / 28 | 36 / 20 |
| Uniform, 150 Hz both sides | 50 / 53 | 60 / 35 |
| Uniform, left 80 Hz, right 100 Hz | 17 / 36 | 18 / 25 |
| Uniform, left 100 Hz, right 80 Hz | 37 / 17 | 40 / 8 |

(Seed 1; seed 2 agreed within a few spikes.) The correction reduces the
right side's lead with pictures but does not remove it, and it creates a
left lead with uniform drive. It fails its own test and is **not used**.
The switch reacts to differences smaller than any group-wide factor can
remove. Scaling only LC10a's output by 0.87 gave the same mixed result.

## Experiment 20: faster simulator, same spikes

`dro/sim.py` now updates only neurons that have received input so far; a
neuron at rest with no input stays exactly at rest. Compared with the
previous version, spike for spike (neuron and time):

| Run | Identical | Spikes | Before | After |
| --- | --- | --- | --- | --- |
| Sugar neurons, 200 Hz, 1 s | yes | 12,328 | 9.2 s | 1.7 s |
| Pictures "yes" / "no", 1 s | yes | 16,038 | 11.2 s | 5.6 s |
| Pictures "ship" / "wait", 1 s | yes | 22,280 | 10.1 s | 5.9 s |
| Runaway at 0.275 mV, 0.3 s | yes | 88,808 | 3.6 s | 6.4 s |

One decision now takes about 12 s instead of 22 s.

## Experiment 21: 24 pairs, 20 runs each

The list of pairs was written down before the runs. Full pipeline, seeds
10 to 200 in steps of 10. "Input" is the mean LC10a rate the rig produced
for the option (average of left and right eye).

| Pair (a / b) | a won | b won | Undecided | Mean steering spikes a / b | Input a / b, Hz | Winner has more input |
| --- | --- | --- | --- | --- | --- | --- |
| yes / no | 20 | 0 | 0 | 66.3 / 13.1 | 34.6 / 23.9 | yes |
| tabs / spaces | 20 | 0 | 0 | 34.6 / 0.1 | 41.8 / 34.2 | yes |
| deploy / rollback | 20 | 0 | 0 | 6.6 / 0.0 | 33.5 / 28.0 | yes |
| stay / go | 20 | 0 | 0 | 71.1 / 30.9 | 41.3 / 30.2 | yes |
| beach / mountains | 20 | 0 | 0 | 19.4 / 0.0 | 38.4 / 20.9 | yes |
| call / text | 20 | 0 | 0 | 19.6 / 11.1 | 34.6 / 33.9 | yes |
| monolith / microservices | 20 | 0 | 0 | 7.2 / 0.0 | 22.6 / 17.1 | yes |
| light / dark | 20 | 0 | 0 | 19.9 / 1.3 | 55.4 / 43.3 | yes |
| early / late | 20 | 0 | 0 | 19.4 / 3.2 | 48.9 / 31.6 | yes |
| left / right | 0 | 20 | 0 | 4.0 / 47.4 | 33.3 / 57.0 | yes |
| cat / dog | 0 | 20 | 0 | 13.2 / 39.6 | 29.1 / 41.5 | yes |
| red / blue | 0 | 20 | 0 | 9.2 / 22.2 | 32.9 / 43.3 | yes |
| approve / reject | 0 | 20 | 0 | 0.0 / 19.8 | 29.6 / 45.3 | yes |
| banana / apple | 0 | 20 | 0 | 0.0 / 38.5 | 29.2 / 47.9 | yes |
| window / door | 0 | 20 | 0 | 0.0 / 17.8 | 28.5 / 43.4 | yes |
| refactor / rewrite | 0 | 19 | 1 | 0.1 / 5.1 | 26.5 / 33.0 | yes |
| hotfix / revert | 18 | 0 | 2 | 3.0 / 0.1 | 43.4 / 39.0 | yes |
| pizza / salad | 18 | 1 | 1 | 2.0 / 0.3 | 50.2 / 51.9 | no |
| walk / bus | 15 | 3 | 2 | 7.2 / 4.4 | 44.0 / 34.5 | yes |
| tea / coffee | 13 | 5 | 2 | 17.9 / 16.6 | 27.9 / 40.9 | no |
| now / later | 13 | 6 | 1 | 13.1 / 10.3 | 42.4 / 40.7 | yes |
| sleep / work | 3 | 13 | 4 | 1.4 / 2.7 | 46.2 / 44.2 | no |
| ship on Friday / wait until Monday | 9 | 9 | 2 | 71.1 / 69.6 | 43.7 / 43.6 | (tie) |
| merge / rebase | 9 | 9 | 2 | 0.8 / 0.8 | 35.2 / 35.4 | (tie) |

- **18 of 24 pairs** gave the same winner in at least 16 of 20 runs; 15 of
  them in all 20.
- **In 17 of those 18 the winner is the option with more input.** The one
  exception, "pizza / salad", is decided by two spikes. So for most pairs
  the outcome is already set by the rig's contrast number; the brain passes
  the difference on and sharpens it through the AOTU019 switch. The size of
  the margin is the brain's: "call / text" differ by 0.7 Hz of input and
  still give 20 of 20.
- Of the six pairs that do not reach 16 of 20, four have nearly equal input
  ("now / later", "sleep / work", "ship / wait", "merge / rebase"), "tea /
  coffee" goes against the input, and "walk / bus" missed by one run.
- Four pairs are decided by fewer than five steering spikes in total.
- The right DNa02 fired more than the left in all 24 pairs: 13.7 against
  2.2 spikes per trial on average.
- Activity stayed contained: at most 467 active neurons in any trial.

The first four pairs (experiment 16) were not typical: they held two of
the six pairs that do not repeat and the only repeating pair that goes
against the input.

## Experiment 22: 18 more pairs, for the question queue

`python -m dro.repeat`, 20 runs per pair, seeds 10 to 200. The list was
written down before the runs.

| Pair (a / b) | a won | b won | Undecided | Mean steering spikes a / b | Input a / b, Hz | Winner has more input |
| --- | --- | --- | --- | --- | --- | --- |
| vim / emacs | 20 | 0 | 0 | 16.6 / 3.5 | 28.2 / 35.0 | no |
| linux / windows | 20 | 0 | 0 | 47.1 / 0.0 | 43.2 / 26.0 | yes |
| monday / friday | 0 | 20 | 0 | 0.0 / 35.1 | 28.2 / 46.0 | yes |
| office / remote | 20 | 0 | 0 | 36.5 / 0.1 | 44.2 / 33.4 | yes |
| docker / podman | 20 | 0 | 0 | 6.2 / 0.8 | 31.0 / 28.4 | yes |
| bug / feature | 20 | 0 | 0 | 57.2 / 0.0 | 41.6 / 32.1 | yes |
| plan / improvise | 20 | 0 | 0 | 101.0 / 0.0 | 48.9 / 24.1 | yes |
| meeting / email | 0 | 20 | 0 | 0.0 / 13.0 | 27.9 / 44.8 | yes |
| test / pray | 0 | 20 | 0 | 6.5 / 40.6 | 35.0 / 47.9 | yes |
| cloud / basement | 20 | 0 | 0 | 13.4 / 0.0 | 44.4 / 23.7 | yes |
| lunch / deadline | 20 | 0 | 0 | 10.6 / 0.0 | 38.6 / 26.1 | yes |
| python / powershell | 20 | 0 | 0 | 23.6 / 0.0 | 34.2 / 24.0 | yes |
| squash / merge commit | 0 | 20 | 0 | 0.0 / 53.8 | 31.6 / 50.9 | yes |
| ask / search | 20 | 0 | 0 | 37.9 / 0.1 | 30.4 / 34.4 | no |
| yaml / json | 0 | 19 | 1 | 3.6 / 10.1 | 51.7 / 40.4 | no |
| standup / sit-down | 19 | 0 | 1 | 3.1 / 0.0 | 35.0 / 25.4 | yes |
| kanban / scrum | 0 | 13 | 7 | 0.1 / 1.4 | 30.1 / 41.9 | yes |
| frontend / backend | 0 | 10 | 10 | 0.2 / 0.8 | 27.6 / 26.1 | no |

- 16 of 18 pairs repeat (same winner in at least 16 of 20 runs).
- In 13 of those 16 the winner has more input. Three pairs repeat against
  the contrast: "vim / emacs" and "ask / search" in all 20 runs, "yaml /
  json" in 19. So the brain does overturn the rig's number at times, and
  when it does, it does so consistently.
- The two pairs that do not repeat are decided by about one spike in total.

Together with experiment 21: 34 of 42 pairs repeat, and in 30 of those 34
the winner is the picture with more contrast. Seven of the 42 are decided
by fewer than five steering spikes in total.

`questions.json` holds the repeating pairs of both experiments.

## Experiment 23: Fly Gate on four real diffs, ten seeds each

`dro.gate.look`: the added lines of a diff as one picture, the removed
lines as the other (`render_lines`: font size 9, drawn from the top left,
cut off at the edges), then the usual two trials. Diffs taken from this
repository's history, seeds 10 to 100.

| Diff | Lines added / removed | Input new / old, Hz | New won | Old won | Undecided | Steering spikes new / old, range |
| --- | --- | --- | --- | --- | --- | --- |
| `dro/repeat.py` in d0aa092 | 54 / 0 | 44.2 / 0.0 | 10 | 0 | 0 | 128 to 142 / 0 |
| `dro/publish.py` in 2b0623b | 19 / 3 | 43.9 / 22.4 | 10 | 0 | 0 | 61 to 71 / 0 |
| `dro/decide.py` in d8c58b2 | 93 / 25 | 41.2 / 44.0 | 8 | 2 | 0 | 3 to 11 / 4 to 7 |
| `docs/CONCEPT.md` in a5c4a16 | 32 / 66 | 43.0 / 44.6 | 1 | 8 | 1 | 1 to 12 / 7 to 13 |

- When one side has few lines or none, its picture is nearly empty, the
  other eye drives the brain alone, and the verdict is the same in every
  seed with a wide margin.
- When both sides fill their picture, the two pictures have almost the same
  contrast, the sides suppress each other, and the verdict rests on a few
  spikes. It leans the same way in 8 of 10 seeds in both such diffs, but
  the margin is often below five spikes; the comment then says "treat it as
  a coin toss".
- In the `dro/decide.py` diff the fly went against the contrast (the old
  lines had slightly more) in 8 of 10 seeds.

First run on a real pull request (DemonazGH/Dro#1, the one that added Fly
Gate, 521 lines added and 9 removed): the old lines won, 28 steering spikes
against 4. Nine removed lines are enough to fill the picture, since only
about eight lines fit, so this was a contest between two full pictures and
the old one had more contrast.

So the verdict does not follow the size of a change. It is clear only when
one side has fewer than about eight lines; otherwise it compares the
texture of the first eight lines on each side. The comment says that the
rig drew the first lines and that contrast usually decides.

## Open questions and ideas

Done or partly done:

- **Sanity check against the paper** (was 1). Done on the right side with
  the reference code, experiments 6 to 10. Still open: compare with the MN9
  rates printed in the paper, which could not be opened here.
- **Synapse count threshold** (was 2). 5 instead of 3 changes little at
  either 0.275 or 0.10 mV (experiment 8; at 0.10 mV and 200 Hz: MN9 15 to
  17 Hz against 17 to 25 Hz). The threshold stays at 3.

- **Picture into LC10a, DNa02 as the only readout.** Done, experiments 15
  to 17 and 21. The picture reaches the steering neuron, the control passes
  and 18 of 24 pairs repeat.
- **The right side's dominance.** Cause found, experiment 18: more synapses
  on the right side of the dataset, turned into a switch by AOTU019. A
  hemisphere correction was tried and rejected, experiment 19.

Not yet tried, most useful first:

1. **How much of the choice is the fly's.** In 17 of 18 repeating pairs the
   option with more input wins (experiment 21). Measure it directly: for
   many pairs, compare the pipeline's winner with the winner by input alone,
   and report both in every log and post.
2. **A less blunt stand-in for the optic lobe.** The contrast rule is the
   rig's. Anything closer to what LC10a responds to in the animal (small
   moving objects) would shift work from the rig to the wiring. Fix any new
   rule before looking at decisions.
3. **Why more input can mean fewer spikes with one eye.** "pizza" and
   "salad" drive many LC10a cells and leave DNa02 nearly silent even alone
   (experiment 17). Find the inhibitory route.
4. **Moving pictures through T4 and T5 to LLPC1**, as a second route. Needs
   a way to make the optic lobe pass motion, or input at T4 and T5.
5. **Weight scale between datasets.** Instead of one global strength,
   normalise each connection by the postsynaptic neuron's total input, or
   rescale by region. This may widen the narrow window found in
   experiment 9.
6. **Olfactory ignition.** Find why Kenyon cells and antennal lobe neurons
   become self-sustaining just above 0.10 mV: missing inhibition, wrong
   transmitter predictions for local neurons, or neurons with an unclear
   transmitter (3,602, all treated as excitatory). Try dropping the unclear
   ones.
7. **Left and right.** Check whether `MN9_R` is truncated in the release and
   whether other readouts have the same asymmetry. The steering readout
   compares left with right, so this matters directly.
8. **Eye orientation.** Verify how the hex coordinates map onto the visual
   field.
9. **Compare with other open implementations** on MaleCNS: the `flycns`
   package on PyPI and the `fruitflydev/flycoinrh` repository.
