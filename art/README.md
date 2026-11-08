# Org art

The Dark Inc. avatar and banner: technomancer pixel art, a gritty 1980s sci-fi film poster with amber and green phosphor, neon magenta, rain and industrial night as its motifs. **The current ones (2026-11-08) come from the Retro Diffusion cloud API, RD Pro** (see "Round 5" below). The Bevy Coven art they replace (rounds 1 to 4) is kept in `coven/`.

- `avatar.png` (512×512) and `avatar-1024.png`: the current avatar, `avatar-3` of round 5: a hooded technomancer, face lit from below by a green phosphor CRT, one amber cybernetic eye, orange and magenta rim light in the rain, native 256×256 at 2× and 4× nearest-neighbour. `banner.png` (1024×512, native 256×128 at 4×): the current banner, `banner-3`: a dark factory at night from the wet street, smokestacks, one amber-lit window, a giant robotic arm against a neon-magenta sky. `../profile/banner.png` is a copy of the banner.
- `rd_api.py`: the Retro Diffusion v2 client (`python3 rd_api.py JOBS.json OUTDIR [--cost-only]`). It reads the key from `~/.config/retrodiffusion/api_key` and never takes it from an argument. `rd-jobs-dark-inc.json` holds round 5's four jobs (avatar, banner, the editor's app icon and its splash); `rd-jobs-round1.json` holds round 4's. `round5-sheet-*.png` show round 5's candidates.
- `dark_art.py`: the local generator for rounds 1 to 3. Its docstring has the job schema.
- `avatar.json`, `banner.json`, `banner-round2.json`, `banner-round3.json`: the local jobs that were run. `avatar-sheet.png`, `banner-sheet-round1.png`, `banner-sheet-round2.png`, `banner-sheet-round3.png` show their candidates. `banner-alt-wizard_storm-0.png` is the local runner-up banner.

## Round 5: Dark Inc. (2026-11-08)

RD Pro (`rd_pro__default`, 256 px, four candidates a job, 16 images for $2.88), every prompt ending ", gritty 1980s sci-fi film poster, pixel art, no text". Run on mac_air, which holds the key: `python3 rd_api.py rd-jobs-dark-inc.json OUT --cost-only`, then without `--cost-only`. The icon goes to `bevy_dark_factory`'s `crates/bevy_dark_factory/macos/icon-256.png` (and `DarkFactory.icns` through `tools/release/macos/make_icns.py`), the splash to `crates/bevy_dark_factory/assets/ui/splash.png` (256×80). The owner picked each winner from contact sheets; the scores used **d** = the motif: amber or green phosphor, neon magenta, rain, industrial night.

|Job|Seeds|0|1|2|3|Winner|
|---|---|---|---|---|---|---|
|avatar|9101-9104|8|9|8|**10**|`avatar-3`: CRT under the face, amber eye, rim light, rain; 0 has no CRT|
|banner|9201-9204|8|8|8|**10**|`banner-3`: magenta sky, arm, one amber window, clean edges; 1 has an orange edge artifact|
|icon|9301-9304|9|**10**|7|9|`icon-1`: the clearest silhouette at small sizes|
|splash|9401-9404|8|**10**|7|9|`splash-1`: arm against magenta, amber window, readable at 256×80|

## Round 4: the Retro Diffusion cloud API (2026-11-01)

RD Pro (`rd_pro__default` and `rd_pro__fantasy`, 256 px, $0.18 an image, 16 images for $2.88) draws far more detail than the local SD 1.5 checkpoints: feathers, a textured moon, rooftops with lit windows. The API is `POST https://api.retrodiffusion.ai/v2/inferences` with the header `X-RD-Token`, a fresh `Idempotency-Key` per paid request, then `GET .../tasks/{task_id}` until it succeeds; `"check_cost": true` prices a request for free (and takes no idempotency key). The reference is https://github.com/Retro-Diffusion/api-examples.

The first avatar chosen, `av_ref-0` (drawn from the v1 avatar as a `reference_images` input), was rejected by the owner: its raised wing and its folded wing read as three wings. `av_default-2` has two clearly separate wings, is symmetrical, and holds up at 40 px. Check the wing count on a bird before you pick it. The banner's winner kept the brand's yellow moon where `bn_fantasy-2` went pale lavender. A prompt names the subject and the mood only (`rd_pro` handles the pixel-art rendering), and says "no text".

## Rerun

Copy `dark_art.py` and the job file to `big:~/dark-art/`, then:

```sh
ssh big "bash -lc 'gpu-tenant run 3d --who dark-incorporated-art@big --wait --mem 16G --note \"dark-incorporated org art\" -- ~/sanctuary-icons/.venv/bin/python ~/dark-art/dark_art.py --jobs ~/dark-art/avatar.json --out ~/dark-art/runs/avatar-1'"
ssh big "bash -lc 'gpu-tenant run 3d --who dark-incorporated-art@big --wait --mem 16G --note \"dark-incorporated org art\" -- ~/sanctuary-icons/.venv/bin/python ~/dark-art/dark_art.py --jobs ~/dark-art/banner-round3.json --out ~/dark-art/runs/banner-round3-3'"
```

The avatar winner is `runs/avatar-1/candidates/raven_grimoire-1.png` (seed 1002); the banner winner is `runs/banner-round3-3/candidates/raven_moon-3.png` (seed 9204). Generation is seeded, so the same checkpoint, diffusers version and GPU give the same image.

## How the winners were picked

Each candidate scored 0-2 on five criteria, 10 in all:

- **a** the subject reads at a 40 px thumbnail (banner: at full size);
- **b** one clear subject with a strong silhouette against the sky;
- **c** no text-like glyphs, pentagrams or gore;
- **d** the motif: moon, purple-to-orange gradient, lightning or chrome;
- **e** a clean pixel grid: no `block` fallback, no smeared pixels.

The highest total wins; a tie goes to a raven, because the raven is the familiar.

### Avatar (round 1, 10 candidates; `RetroDiffusion24x-64xModel`, 512 px, 64×64 native)

|Candidate|Seed|a|b|c|d|e|Total|
|---|---|---|---|---|---|---|---|
|raven_grimoire-0|1001|2|2|2|1|2|9|
|**raven_grimoire-1**|1002|2|2|2|2|2|**10**|
|witch_moon-0|2001|1|0|2|1|2|6|
|witch_moon-1|2002|2|2|2|2|2|10|
|cat_grimoire-0|3001|1|1|2|1|2|7|
|cat_grimoire-1|3002|2|2|2|1|2|9|
|grimoire_runes-0|4001|1|1|1|2|2|7|
|grimoire_runes-1|4002|1|1|1|2|2|7|
|raven_hat-0|5001|2|2|2|1|2|9|
|raven_hat-1|5002|1|1|2|2|2|8|

`raven_grimoire-1` and `witch_moon-1` tie at 10; the raven wins the tie. It is a black raven with purple wings against a yellow-and-orange moon, ringed in purple.

### Banner, round 1 (6 candidates; `RetroDiffusion128xModel`, 768×256, `expected_factor` 4)

Pixelfixer recovered a 96×32 grid on all six, a factor of 8 rather than the uncalibrated guess of 4, so every candidate fell back to a block reduce and scored 0 on **e**.

|Candidate|Seed|a|b|c|d|e|Total|
|---|---|---|---|---|---|---|---|
|coven_altar-0|6001|1|1|2|1|0|5|
|coven_altar-1|6002|1|1|1|0|0|3|
|wizard_cliff-0|7001|1|1|2|1|0|5|
|wizard_cliff-1|7002|1|1|2|1|0|5|
|castle_brooms-0|8001|2|2|2|1|0|7|
|castle_brooms-1|8002|1|1|2|1|0|5|

### Banner, round 2 (6 candidates; the two best subjects, seeds `seed + 200`, `expected_factor` 8, `out_scale` 12)

Round 1's best reached the threshold of 7 only because its grid was wrong, so round 2 reran the two best subjects at the measured factor of 8.

|Candidate|Seed|a|b|c|d|e|Total|
|---|---|---|---|---|---|---|---|
|castle_brooms-0|8201|1|1|2|1|2|7|
|castle_brooms-1|8202|2|1|2|2|2|9|
|castle_brooms-2|8203|2|2|2|2|2|10|
|wizard_cliff-0|7201|1|0|2|1|2|6|
|wizard_cliff-1|7202|1|1|2|1|2|7|
|**wizard_cliff-2**|7203|2|2|2|2|2|**10**|

`wizard_cliff-2` and `castle_brooms-2` tie at 10; the banner goes to `wizard_cliff-2`, a dark raven-winged figure on a rock under a full moon, with airbrushed purple, orange and yellow cloud bands and a lightning streak, because its figure is a raven.

### Banner, round 3 (16 candidates; `RetroDiffusion24x-64xModel`, 1024×512, 30 steps, guidance 7.5, `expected_factor` 8, `out_scale` 9)

The owner rejected the round 2 winner: at 96×32 native pixels the figure was a smear. Round 3 used the checkpoint that made the avatar, a 2:1 frame (SD 1.5 repeats its subject across a 3:1 one) and a 128×64 native grid, with a sharper prompt (`banner-round3.json`). Every candidate recovered a clean 128×64 grid.

|Candidate|Seed|a|b|c|d|e|Total|
|---|---|---|---|---|---|---|---|
|witch_castle-0|9001|1|1|2|1|2|7|
|witch_castle-1|9002|2|1|2|1|2|8|
|witch_castle-2|9003|1|0|2|1|2|6|
|witch_castle-3|9004|1|1|2|2|2|8|
|wizard_storm-0|9101|2|2|2|1|2|9|
|wizard_storm-1|9102|1|1|2|1|2|7|
|wizard_storm-2|9103|1|1|2|1|2|7|
|wizard_storm-3|9104|1|1|2|2|2|8|
|raven_moon-0|9201|2|2|2|1|2|9|
|raven_moon-1|9202|2|2|2|1|2|9|
|raven_moon-2|9203|1|1|2|2|2|8|
|**raven_moon-3**|9204|2|2|2|2|2|**10**|
|coven_cauldron-0|9301|1|1|2|1|2|7|
|coven_cauldron-1|9302|1|1|2|1|2|7|
|coven_cauldron-2|9303|1|1|2|1|2|7|
|coven_cauldron-3|9304|1|0|2|1|2|6|

The banner is `raven_moon-3`: a black raven with spread wings flying across a yellow moon, airbrushed pink and orange clouds on a purple sky, over a black city skyline. It fills the frame edge to edge, which a banner needs. The runner-up, `wizard_storm-0` (a hooded wizard and a raven on a rock before a huge moon), is kept as `banner-alt-wizard_storm-0.png`; it loses on the motif because a dark vignette rims its corners.
