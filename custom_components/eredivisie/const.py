"""Constants for the Eredivisie integration."""

from datetime import timedelta

DOMAIN = "eredivisie"
COMPETITION = "DED"  # football-data.org code for the Eredivisie

CONF_TEAM_ID = "team_id"
CONF_TEAM_NAME = "team_name"
CONF_TEAM_CREST = "team_crest"

# football-data.org's free tier allows 10 requests/minute. Normal cadence
# uses ~2 calls (last result + next match); live mode adds a 3rd (in-play
# score check). Both are far inside budget even for several configured teams.
NORMAL_INTERVAL = timedelta(minutes=10)
LIVE_INTERVAL = timedelta(seconds=60)

# Start polling at live cadence this long before a TIMED match's kickoff,
# so the transition to IN_PLAY is caught promptly rather than up to
# NORMAL_INTERVAL late.
PRE_MATCH_WINDOW = timedelta(minutes=30)

LIVE_STATUSES = {"IN_PLAY", "PAUSED"}
FINISHED_STATUSES = {"FINISHED"}
UPCOMING_STATUSES = {"SCHEDULED", "TIMED"}
