# Eredivisie for Home Assistant

## Context

Validated gap: TeamTracker (the most popular HA sports integration, ESPN-based,
~1000s of installs) does **not** natively support Eredivisie — only via a
fiddly, unverified "Custom API Configuration". The one integration that could
cover it (`lone-baggie/football_data`, using football-data.org) has **zero**
stars/forks/adoption — effectively undiscoverable. Meanwhile
**football-data.org's free tier explicitly includes Eredivisie** (one of 12
free competitions, alongside Premier League/Bundesliga/etc.), with standings,
fixtures and results, no credit card needed.

Goal: a discoverable, Eredivisie-first HA integration — live score, league
position, next/last match for your club(s) — filling the gap the popular
ESPN-based option leaves open for Dutch users.

## API facts (confirmed against football-data.org's docs)

- Base: `https://api.football-data.org/v4/`, auth via `X-Auth-Token` header
  (free API key, email signup, no card).
- Eredivisie competition code: **`DED`**.
- Free tier: **10 requests/minute**. Response headers `X-RequestsAvailable`
  and `X-RequestCounter-Reset` self-report remaining quota — the coordinator
  should read these rather than guess (unlike the Open-Meteo situation
  earlier, this API tells you exactly where you stand).
- Relevant endpoints: `/v4/competitions/DED/standings`,
  `/v4/competitions/DED/matches`, `/v4/teams/{id}/matches`.

## Architecture

Standard custom-integration layout (`dm-utils/eredivisie`, matches the
`travelforecast`/`climatenormals` pattern): manifest, config_flow,
coordinator, sensor platform. Built generically against football-data.org
(works for any of its 12 free competitions under the hood) but named and
positioned around Eredivisie specifically, since that's the validated gap —
same naming logic as "Travel Forecast"/"Climate Normals".

- **Config flow**: API key, then a team picker — fetch `DED` teams from the
  API and let the user select their club(s) rather than tracking the whole
  competition blindly (matches how people actually use this: "how's Ajax
  doing", not "dump all 18 clubs on my dashboard").
- **Adaptive polling** (this is what the generous 10 req/min budget buys us):
  - Normal cadence: every 10 minutes (1-2 calls: standings + next/last
    match) — cheap, most of the season.
  - **Live mode**: when a selected team's match is `TIMED` and close to
    kickoff, or already `IN_PLAY`/`PAUSED`, switch to polling every ~60
    seconds for near-live score updates, then drop back to normal cadence
    once the match is `FINISHED`. Well within the 10/min budget even during
    a live match.
- **Entities per selected team**: league position (rank, points, W/D/L,
  goal difference), next match (opponent, kickoff, home/away), last result,
  and a live-score sensor that's only meaningfully "live" during match mode.

## First concrete step (validate before building the integration)

Same pattern as the last two projects: prove the API mechanics with a
standalone script before wiring up a coordinator.

1. Free football-data.org account + API key (email signup, no card).
2. `dev/test_football_data.py`: fetch `DED` standings, fetch one real club's
   matches (next + last), and confirm the `X-RequestsAvailable` header
   behaves as documented. Pick a well-known club (e.g. Ajax) for this
   technical check — the real config flow will let any club be selected
   later.
3. Only after that: build the real integration (config_flow, adaptive-poll
   coordinator, sensors), reusing the proven request logic from the script.

## Verification

- Step 2's script output: standings for DED look right, one club's
  next/last match populated correctly, rate-limit headers present and sane.
- After installing on the real HAOS box: confirm entities show the correct
  league position and next fixture for a real selected club; manually
  trigger around an actual match time (or simulate by lowering the
  live-mode threshold) to confirm the coordinator actually switches to the
  faster poll cadence and back.
