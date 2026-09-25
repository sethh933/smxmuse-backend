# Rider canonical investigation — September 24, 2026

## Evidence and limits

Search Console reports supplied by the owner show Chase → Greg, Dalton's numeric
points URL → Gary's points page, Jett → Cooper, and Cole → Jarrett. Cole's recorded
crawl detected his self-canonical but Google selected another rider. Deegan was
indexed with the expected canonical. These selected examples do not measure the
percentage of all riders affected.

Later Google live tests supplied for Chase, Dalton, and Jett detected the correct
identity and canonical. The Chase and Dalton HTML included their actual stats.
Live tests do not resolve or reproduce Google's historical duplicate grouping.
We do not have the historical failed render or server logs, so the underlying
cause of those Google decisions remains unconfirmed.

Current public HTTP checks found identical empty application shells for the
Chase/Greg/Dalton examples. Jett and Cooper had distinct initial names and
canonicals, but no initial stats tables and hidden introductory shells. Numeric
rider URLs returned 200 without a server redirect. Normal browser checks loaded
the right identities, tables, and canonicals without observed console errors.

## Confirmed code weaknesses addressed locally

- Rider fetches did not check HTTP status. An error response could become invalid
  component data, or leave a generic loading page indefinitely.
- Requests had no timeout or recovery retry. The shared rider request helper now
  has a 12-second timeout per attempt and retries transient errors once.
- Results and points fetches now abort on unmount and validate response shapes.
  Points/header data is committed together to avoid a partial failed table.
- Prebuilt rider snapshots now retain their own identity and canonical while
  loading or recovering from errors. Prebuilt results/points introductions are
  visible and included in the same route-scoped snapshot mechanism.
- Recovery shows an explicit error and Try again button. Transient errors do not
  add noindex tags or change the canonical to another page.
- The earlier sitemap change adds 247 qualifying-only profiles with verified
  legacy data. It does not add empty points/results subpages for those riders.

## Verification

`node scripts/riderRequest.test.mjs` from the frontend verifies transient 503
recovery, no retry for 404, bounded hung requests, and navigation cancellation.
The production bundle/prerender build passed. Existing bundle-size warning remains.

A temporary localhost server returned deliberate API failures against the built
frontend. Jett's prebuilt profile retained its summary, identity, and canonical.
Deegan's prebuilt results/points retained identity and their respective canonicals.
Restoring the API and clicking Try again loaded Deegan's 96 result rows with the
same canonical. A route without a snapshot shows a recoverable error, but cannot
retain identity or data it has never received.

## Remaining work before calling this resolved

The existing prerender coverage cap remains, including the smaller selection for
results/points: Jett's profile is prebuilt but his two detail routes are not in the
checked manifest. This cleanup is not complete server rendering of every rider.

Numeric redirects need a production routing design that resolves rider IDs to
names on smxmuse.com. A redirect added only to the separate API host would not fix
the public page URL. No hosting, domain, or redirect configuration was changed.

After an approved deployment, repeat live tests and compare subsequent indexed
canonical reports against the recorded examples. Do not treat the current local
changes, a passing build, or a live-test success as proof of Google's resolution.

The backend and frontend have earlier uncommitted changes too; review both repos
before release. Deploy the updated backend before building/deploying the frontend.
