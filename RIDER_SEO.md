# Rider profile SEO

The compact career summary uses the combined career rows from the existing
profile summary tables. SX counts main events; MX, SMX, and WMX count overalls.
Average finish uses the existing career average, not an average of season averages.
Disciplines without starts are omitted. No biography or personal facts are generated.

`rider_seo.py` supplies the same totals and metadata to the profile API and the
prerender manifest. The frontend no longer fetches a full profile for each sport
just to display the summary. Initial profile HTML includes the visible summary,
navigation links, canonical URL, description, and Person structured data. A small
snapshot keeps the summary visible while React loads the complete profile.

## Release order

1. Deploy the backend repository, including `rider_seo.py`.
2. Build and deploy the frontend repository. The build rejects an older manifest
   that lacks career summaries, rather than silently omitting them.
3. Check a deployed profile in Search Console URL Inspection (live test and
   rendered HTML). Local validation cannot confirm Google's indexing decisions.

## Updating data

After importing results or adding riders, run the existing rider-summary refresh
workflow. Live profiles use those refreshed tables on their next load. Static
HTML updates on the next successful frontend build; its existing daily scheduled
build runs at 09:17 UTC. This change does not add a database refresh schedule.

New riders receive profiles and summaries from their data without manual copy.
Riders without qualifying results do not get invented stats. Static prerendering
still selects the top 600 career / top 350 recently active riders (846 distinct
profiles in the checked dataset), because the existing deployment limits remain.
Other profiles continue to load through React. This is not full server rendering
of every rider or every career-results/points table.

## Verification

`python scripts/check_rider_seo.py` performs read-only comparisons against existing
stats for Jett and one-result riders in SX, MX, SMX, and WMX, and compares static
and live metadata. Frontend `npm run build` checks the production bundle and all
prerender output; `PRERENDER_API_URL` can target the local updated API for testing.
