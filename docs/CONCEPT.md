# Dro: concept

As of 2026-11-11. English version of the owner's working concept document.

## Summary

The wave started on 4 September 2026 and within two weeks reached Doom, Beat
Saber and LinkedIn posts. A one-off "the fly does X" stunt is no longer
news. The remaining chance is a persistent character with an honest
mechanic, plus niches the wave has not reached: DevOps humour and a
Russian-language Telegram channel.

Treat it as an experiment with a chance of one viral episode.

## Character

Dro is a self-assured corporate guru with 166,700 neurons and not a single
thought of his own.

- **Name and title:** Dro S. Melanogaster, Chief Fruit Officer at FlyCorp.
- **Bio line:** "166,700 neurons. Zero MBAs. Disrupting rotten fruit since
  2026."
- **Voice:** explains business, career and life through light, windows and
  overripe bananas. Never breaks character.
- **Honesty rule:** every post ends with a line saying what the fly decided
  and what the human wrote.
- **Language:** English first, because that is where the audience is.
  Russian in a separate Telegram channel.
- **Look:** dark background, amber neuron flashes, one accent colour. The
  avatar is an original stylised fly in a tie. In videos Dro lives in an
  office the size of a matchbox.

Note: the simulation keeps the 165,122 neurons marked as traced. The bio
line uses the release's headline figure. Decide which number the persona
uses and keep it consistent.

## How it works

The fly chooses, a language model words it, a human publishes.

1. **Data.** MaleCNS v1.0, licensed CC BY.
2. **Stimulus.** The fly cannot read. Options are shown as pictures.
3. **Simulation.** A simple "charge up, then fire" neuron model, run in
   GitHub Actions on a free runner. No GPU.
4. **Readout.** Descending neurons give the turn, and so the choice.
   Dopamine neurons for reward and punishment give the "mood" of the post.
5. **Text.** A language model receives only the choice and the mood and
   writes the post in Dro's voice.
6. **Publishing.** Scheduled run in a public repository, log of every run
   committed there, keys in secrets. A human presses "publish".

## Formats by platform

A personal profile for a fly would be banned on LinkedIn and Facebook, so
pages are used everywhere.

| Platform | Format | Role |
| --- | --- | --- |
| YouTube Shorts | "Dro decides": 10 to 20 seconds, question, brain flashes, choice, punchline | Reach |
| YouTube long videos | "A fly made my decisions for 30 days", build logs | Depth |
| LinkedIn, FlyCorp page | Parodies of guru posts, 3 a week | Audience |
| X | Daily decision log, threads | Where the trend lives |
| Telegram, Russian channel | Dro in Russian and a pet bot | Open niche |
| Facebook page | Reposts of vertical videos | Reposts |
| GitHub | Code and the log of all runs | Trust, launches on Hacker News and Reddit |

Two sample LinkedIn posts:

> I hit the same window 47 times today. On attempt 48 I hit it again.
> Persistence is not a strategy. It is just all my descending neurons had.
>
> *Decided by the fly: direction. Written by the human: every word.*

> We asked 166,700 neurons whether to ship on Friday. Dopamine said yes. The
> punishment neurons said nothing. We shipped. Ask me on Monday.
>
> *Decided by the fly: yes. Written by the human: the regret.*

## Bold ideas

Start with the first three: they build on the owner's own skills and nobody
has taken them yet.

1. **Fly Gate.** An extension for Azure DevOps and GitHub Actions: a fly
   brain approves or rejects a pull request, with the activity picture and
   "LGTM by a fly" in the comment. Free, as a calling card for developers.
2. **Portrait through a fly's eyes.** A person sends a photo and gets a
   poster of how the neurons reacted to it.
3. **The fly is my boss.** For 30 days Dro makes one everyday decision a
   day for the owner. A real person on camera also answers YouTube's
   originality question.
4. **Round-the-clock stream with viewer-chosen stimuli.** Viewers give the
   fly sugar, wind or darkness and watch the brain react live.
5. **Music from spikes.** Neuron firing turned into notes: an ambient album
   "written by a fly".
6. **Fly oracle.** Weekly match predictions in the spirit of Paul the
   octopus. Entertainment only, no betting.
7. **Fly in hardware.** A cheap camera car drives to a banana under
   connectome control. Material for a long video.
8. **Telegram pet bot.** A tamagotchi with a real wiring diagram.
9. **Fly versus model versus human.** A weekly three-way contest on one
   task.

Already done by others, not worth repeating: Minecraft, Doom, Beat Saber,
Super Mario 64, bitcoin and memecoin trading, a token launch, "bi fly", a
brewery campaign.

## Risks

- **Data licence.** MaleCNS is CC BY: use is allowed with credit to FlyEM
  Janelia, the Cambridge Connectomics Group and Google Research. The female
  FlyWire connectome is reported to be CC BY-NC
  ([source](https://www.modpackindex.com/mod/204327/flybrain)), which would
  limit what can be done with the project, so it is not used here.
- **YouTube's "inauthentic content" rules.** Since 16 July 2026, templated,
  repetitive videos and AI personas talking about finance, health and law
  are penalised
  ([The Desk](https://thedesk.net/2026/07/youtube-clamps-down-loq-quality-ai-slop/)).
  Protection: own simulation, own code, the owner's voice or commentary on
  screen, varied formats. Dro gives no financial advice.
- **Automated posting.** A human publishes. Accounts are labelled as
  automated where the platform provides for it.
- **Tokens.** A regulated financial product with a reputational tail. Out
  of scope.
- **Big words.** No "uploaded consciousness", no "living fly". A connectome
  is a wiring diagram without biochemistry.
- **Fading interest.** The peak of the wave was two months ago. If 30 days
  bring no response, the project stays a portfolio line.

## 30-day plan

The goal of the month is to find out whether Dro catches any audience at
all.

**Week 1: the fly comes alive**

- [x] Compile MaleCNS once and run the simulation
- [x] Run it in GitHub Actions with the graph in the cache, measure runtime
- [x] One "left or right" choice with an activity picture. For now the
      winner is usually the picture with more contrast; see `README.md`
- [x] Open the repository with the code and the run log

**Week 2: the character**

- [ ] Avatar, bio, FlyCorp pages on LinkedIn and Facebook, X account,
      Telegram channel
- [ ] Ten posts written ahead, three "Dro decides" Shorts

**Week 3: Fly Gate launch**

- [ ] Release the pull-request extension
- [ ] Post on Hacker News, Reddit and LinkedIn

**Week 4: formats**

- [ ] Five free "Portrait through a fly's eyes" posters for reviews
- [ ] Start "The fly is my boss", first long video
- [ ] Review: followers, views, inbound interest. Decide whether to
      continue

## Sources

- [404 Media: A Digital Fly Brain Has Taken Over the Internet](https://www.404media.co/a-digital-fly-brain-has-taken-over-the-internet/)
- [Janelia: MaleCNS download and licence](https://male-cns.janelia.org/download/)
- [The Desk: YouTube's inauthentic content clarification](https://thedesk.net/2026/07/youtube-clamps-down-loq-quality-ai-slop/)
- [ForkLog: uses of the male connectome](https://forklog.com/en/open-male-fruit-fly-brain-map-enables-simulations-from-games-to-crypto-trading/)
- [ModpackIndex: FlyBrain mod, licence notes](https://www.modpackindex.com/mod/204327/flybrain)
