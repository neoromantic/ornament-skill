# Ornament Health API — full reference

Compiled from https://ornament.readme.io/reference (41 readme pages, 60 OAS endpoints, 161 schemas).

## Auth, base, conventions

**Base hosts**
- Production: `https://api.ornament.health`
- Sandbox: `https://sandbox-api.ornament.health` (same paths, prepend `sandbox-`). Auto-digitization is OFF in sandbox; use Ornament's pre-digitized sample PDFs.

**Sub-APIs (path prefixes after the base host)**

| API | Prefix |
|---|---|
| Accounting | `/accounting-api/public/v1.0` |
| File | `/public/file-api/v1.0` |
| Image Set (digitization) | `/public/imageset-api/<version>` |
| Medical Data | `/medical-data-api/public/v1.0` |
| Health Advisor | `/public/health-advisor-api/v1.0` |
| Thesaurus | `/thesaurus-api/public/{v1.0|v1.1}` |

**Auth** — `Authorization: Bearer <JWE>`. Token obtained from Ornament Pro → Account → Developer tools → Get API Key. Sandbox keys are issued separately at `sandbox-pro.ornament.health`. No OAuth, no refresh — the JWE is long-lived.

**Errors** — uniform: `401` unauthorized · `403` forbidden (Health Advisor) · `404` not found · `422` validation (`{detail:[{loc,msg,type}]}`) · `400` bad request · `500` internal. No rate-limit numbers published — Ornament's guidance is "don't poll the thesaurus, use the `digest` mechanism".

**Localization** — Thesaurus endpoints take `lang` (ISO-2). The big biomarkers endpoint accepts combos matching `^[A-Za-z]{2}(\+[A-Za-z]{2})?$` — e.g. `EN+RU` (English title, English+Russian synonyms), `RU+EN` (Russian title, RU+EN synonyms). Single-language for `EN`, `RU`, `DE`, `ES`, `PT`, `BR`.

**Digest pattern** — Large thesaurus endpoints (`/v1.1/biomarkers`, `/v1.0/diseases`, `/v1.0/medical-exams`, imageset list endpoints) accept an optional `digest` (opaque hex string from previous response). Server returns `{needToUpdate:false, digest:"…"}` and omits the payload when unchanged.

**Idiom — IDs**

| Key | Scope | What |
|---|---|---|
| `pid` | profile | Patient identity. UUID. |
| `ssoId` | account | Account-level UUID; one account may own multiple PIDs. |
| `sid` | submission | One submission = one digitized lab report. UUID. |
| `seid` | entry | One biomarker row inside a submission. UUID. |
| `iid` | imageset | Pre-digitization image bundle. UUID. |
| `iiid` | image | One page inside an imageset. UUID. |
| `originImagesetId` | submission | Numeric link back to the imageset. |

---

## Profiles (Accounting API)

### `GET /accounting-api/public/v1.0/healer/linked-profiles`

List patients linked to the calling API key. No params.

```json
[{
  "pid":"uuid","ssoId":"uuid","createdAt":1740678724,"name":"Patient 1",
  "sex":"M","birthday":"1990-09-04","lastSubmissionsUpdate":1740739547,
  "isTransferred":false,"isArchived":false,"isFavorite":false,"isDemoPatient":false
}]
```

`birthday` here is `YYYY-MM-DD`. `lastSubmissionsUpdate` is Unix seconds (absent if none).

### `POST /accounting-api/public/v1.0/user/linked-profiles/{pid_or_email}`

Create a linked patient profile. Path segment is either an email or an existing PID.

```json
{ "sex":"M", "connectType":"HEALER", "birthday":605863553, "name":"John Doe" }
```

- `birthday` here is **Unix timestamp** (different from the GET form!).
- `connectType: HEALER` gives the doctor read+write on that PID.
- Returns `{linkedPid, profileSsoId}`. `400` if duplicate.
- No documented PUT/DELETE/archive for an existing profile.

---

## Medical data (`/medical-data-api/public/v1.0`)

### `GET /profile/biomarkers`  — main lab data endpoint

| Param | In | Req | Notes |
|---|---|---|---|
| `pid` | query | yes | uuid |
| `limit` | query | no | int, `0` = no limit |
| `skip` | query | no | int offset |
| `search` | query | no | full-text |
| `abnormal` | query | no | bool. `true` → only `A`; `false` (default) → only `N`. To get both, **omit this param**. |
| `dateFrom` | query | no | `YYYY-MM-DD` or Unix timestamp (`0` = all time) |
| `dateTo` | query | no | `YYYY-MM-DD` |

Returns `ProfileMarkersResponse`:
```json
{ "total":143,
  "biomarkers":[
    {"id":21, "categoryId":10, "isUnitless":false, "status":"N",
     "entries":[{"seid":"uuid","sid":"uuid","value":"18210.0","originalValue":"18.21",
                 "date":1614733200,"originalUnitId":9}]}],
  "refs":{ "21":{"common":[15000,20000],"optimal":[],"paidOptimal":[18000,20000]} } }
```

### `GET /profile/biomarker/{biomarker_id}`

Single biomarker time-series. Path: `biomarker_id` (int). Query: `pid` (req), `dateFrom`, `dateTo`. Returns `ProfileMarkerResponse` — same shape as one element of the list above but with its own `refs` map.

### `POST /medical-data-api/public/v1.0/ai/profile/biomarkers`

Body-driven variant of the GET. Query `pid` (req). Body example:
```json
{ "notPermanentSubmissionsDateRange": { "dateFrom":"2024-01-10","dateTo":"2024-04-10" } }
```
Returns `AIProfileMarkersResponse` — richer (each entry includes `title`, `permanentFactor`, `unitId`, `unitTitle`).

### `GET /profile/submissions`

Patient's submissions (digitized lab reports). Query: `pid` (req), `limit`, `skip`, `search`, `dateFrom`, `dateTo`.

> **Known bug**: the production server returns 500 if `limit` or `skip` are sent. The CLI works around this with client-side slicing.

```json
{ "total":N,
  "submissions":[{
    "pid":"uuid","sid":"uuid","date":1711380197,"hasDate":true,"isDeleted":false,
    "originImagesetId":1234,"comment":"...","laboratory":{"title":"CMD"},
    "examTypeObjectId":12,
    "entries":[{"seid":"uuid","value":"...","rowOrder":1,"biomarkerId":23,
                "originalValue":"...","originalUnitId":123}],
    "mcdDiseases":[], "medicines":[]
  }],
  "refs":{ "<biomarkerId>":{...} } }
```

Entries inside a submission lack `sid`/`date` (they're on the parent submission). `hasDate=false` means the lab document didn't carry a date.

### `GET /profile/submission/{sid}`

One submission detail. Path: `sid`. Query: `pid` (req). Returns `ProfileSubmissionResponse`.

### `GET /profile/diseases`

```json
[ { "diseaseId":176, "status":"CONFIRMED", "updatedAt":1741629086 } ]
```
Query: `pid` (req). `status` is `CONFIRMED` (default) or `REJECTED`.

### `POST /profile/imagesets/images`

Fetch image data for imagesets. Body `{pid, ids:[int], size:{...}}`.

### `GET /linked-profile/{pid}/reporting-profile/favorite`

Patient's favorite biomarkers list. Returns array of `{biomarkerId, isFavorite}`.

### `POST /linked-profile/{pid}/reporting-profile/favorite`

Set favorites: body `{biomarkers:[{biomarkerId, isFavorite}]}`.

### Health Conditions (Medical Data scope)

| Method | Path | Query | Returns |
|---|---|---|---|
| GET | `/profile/health-conditions` | `pid` | array of `{partId, score:{value,effectiveDate}, biomarkers, diseases, expiredDiseases, notEnoughData}` |
| GET | `/profile/health-condition/{part_id}` | `pid` | `{healthConditions: ActualStates, biomarkers:[FullInfoProfileMarker], refs}` |
| GET | `/profile/health-conditions-raw` | `pid` | `{scores:[ScoreRaw], scoreTraces:[ScoreTraceRaw], diseases:[DiseaseRaw]}` |

`ScoreRaw` adds `rawScore` + `statistics`. `DiseaseRaw` adds `rawScore`, `rules`, `ruleId`.

---

## Health Advisor (`/public/health-advisor-api/v1.0`)

Canonical "Interpretation Engine" — scores, traces, diseases.

### `GET /v1.0/profile-health-conditions-raw`

Query `pid` (req). Returns `ActualStatesRawObfuscate`:
```json
{ "scores":[ScoreRawObfuscate],
  "scoreTraces":[ScoreTraceRaw],
  "diseases":[DiseaseRawObfuscate] }
```

- **ScoreRawObfuscate**: `scoreId(uuid), effectiveDate(date), partId, score(1–5), scoreLowBoundary, isAggregatable`.
- **ScoreTraceRaw**: `scoreId, scoreTraceId, seid, effectiveDate(date), biomarkerId, isActual, isAffectedScore, isPermanentFactorAlarm, expirationDate(Unix)`.
- **DiseaseRawObfuscate**: `scoreTraceId, seid, diseaseId, relationTypeId (1=current, 2=possible future), status: CONFIRMED|REJECTED`.

### `GET /v1.0/actual-states`

Query `pid` (req). Returns `ActualStatesBase`:
```json
{ "pid":"uuid", "hasAhSubmissions":true,
  "ha": {"pid":"uuid","version":"2.0.0","scores":[HumanPartScoreBase]},
  "conditions":[Condition], "integralScore":<number> }
```

### `POST /thesaurus-api/public/v1.0/health-conditions/explainer`

Localised explainers for `conditionCode` values. Body:
```json
{ "code":"SUGGESTION_WEAK_SPECIFIC_BAD_DISEASE", "human_part_id":42, "locale":"EN" }
```
Returns `{code, explainer:{humanPartId, title, message}}`.

---

## Files & Digitization

### File API (`/public/file-api/v1.0`)

Markdown-only docs (no formal OAS).

| Method | Path | Body | Returns |
|---|---|---|---|
| POST | `/fileset/` | `{pid}` | `{id, filegroupId}` |
| POST | `/filegroup` | `{filesetId}` | `{id}` |
| POST | `/filegroup/{filegroup_id}/attach_file/` | multipart `file=...` | `{id, fileId, ssoId, filename, filetype, createdAt, hash}` |

One file per multipart request — no bulk upload. Allowed per filegroup (ONE OF): images (JPEG/PNG, any count) · 1 PDF · 1 PDF + 1 XML · 1 PDF + 1 JSON.

### Imageset API (`/public/imageset-api`)

| Method | Path | Body / Query | Notes |
|---|---|---|---|
| POST | `/v1.0/imageset/digitalize-fileset` | `{filesetId}` | Hand off fileset for digitization. Returns `{imagesetIds, unprocessedFilegroups, errorCode?, description?}`. |
| POST | `/v1.0/imageset/new` | `{pid, source}` | Create empty imageset. |
| POST | `/v1.0/imageset/new/xml` | `?pid&fileUrl&source` | XML upload by URL. |
| POST | `/v1.1/imageset/pro/new` | `{pid, source:"web"}` | Pro-app empty imageset. |
| POST | `/v1.1/imageset/pro/new/pdf` | multipart | Pro-app PDF in one shot. |
| POST | `/v1.1/imageset/pro/{imageset_id}/add/page` | multipart `file` | Append page. |
| POST | `/v1.1/imageset/pro/{imageset_id}/delete/page` | `{pid, iiid}` | Delete page. |
| POST | `/v1.1/imageset/pro/{imageset_id}/submitted` | `{pid}` | Mark ready for processing. |
| GET | `/v1.1/imageset/pro/{pid}/{imageset_id}` | — | Imageset detail. |
| POST | `/v1.1/imageset/pro/list` | `{pid, digest?}` | List imagesets (uses digest). |
| POST | `/v1.1/imageset/pro/imageset/remove` | `{iids:[...], pid}` | Bulk remove. |
| GET | `/v1.1/imageset/pro/pages-limit` | — | `{images:20, pdf:40}` |
| GET | `/v1.3/imageset/list` | `?digest` | List, digest-aware. |
| POST | `/v1.2/imageset/remove` | `{iids:[...]}` | Remove. No body. |
| POST | `/v1.2/thumbnails` | `{iids, size}` | Thumbnail URLs. |
| POST | `/v1.2/imageset/rejection_reasons/list` | `{lang}` | Localized rejection reasons. |

### B2B alternative (`/b2b/v1.0/imageset`)

| Method | Path | Notes |
|---|---|---|
| PUT | `/b2b/v1.0/imageset` | multipart `file`. Creates imageset directly. |
| POST | `/b2b/v1.0/imageset/list` | filter by `iids`, `createdAt`, `statusIds`. |
| GET | `/b2b/v1.0/imageset/statuses` | `[{id,title}]`. |
| DELETE | `/b2b/v1.0/imageset/{iid}` | 204. |
| POST | `/b2b/v1.0/rejection-reasons/list` | localized. |

### Webhooks

Not self-service — Ornament provisions via support. Events:

| `eventTypeTitle` | Trigger | `payload` |
|---|---|---|
| `NEW_SUBMISSION` | Imageset successfully processed | `{iid, sid}` |
| `REJECT_IMAGESET` | Imageset rejected | `{iid, comment?, rejectionReasonId}` |
| `SPLIT_IMAGESET` | Imageset split into multiple (different dates) | `{iids, origin_imageset_iid, event:"new_sorted_imagesets"}` |

Envelope: `{id, transactionId, eventTypeTitle, version:"1.0", payload, createdAt, deliveredAt}`. Duplicate-file detection sends `REJECT_IMAGESET` with `rejectionReasonId=41` referencing the **original** `iid` (biomarkers from the dup are still ingested).

### Rejection reason IDs (selected)

1 Unsupported language · 2 Not a lab report · 3 Low image quality · 5 No tests recognized · 6 Tests written by hand · 7 Unsupported structure · 8 Unsupported type of analysis · 23 Other unsupported tests · 24 Unsupported biomaterial · 29 Other · 30 Insufficient information · 31 Names/values/units missing · 32 Biomaterial not specified · 33 Sampling location not specified · 34 Not a lab/instrumental test · 35 Multiple people/dates/studies on one sheet · 38 Document upload error · 40 Multiple values of same biomarker · 41 Duplicate of previously uploaded file.

---

## Thesaurus (`/thesaurus-api/public`)

| Method | Path | Body / Query | Returns |
|---|---|---|---|
| GET | `/v1.0/biomarker-categories` | `?lang` | array `{id, parentId?, title}` (hierarchical) |
| GET | `/v1.0/biomaterials` | `?lang` (req) | array `{id, title}` |
| POST | `/v1.0/diseases` | `{lang, digest?}` | `{needToUpdate, digest, diseases:[Disease]}` |
| GET | `/v1.0/medical-disease` | `?title=` | array `{id, title}` (search) |
| POST | `/v1.0/medical-disease` | `{ids:[int]}` | array `{id, title}` (bulk) |
| POST | `/v1.0/medical-exams` | `{digest?}` | `{needToUpdate, digest, exams:[{typeId, titles, objects, subtypes}]}` |
| GET | `/v1.0/medical-medicine` | `?title=` | search medications by title |
| POST | `/v1.0/medical-medicine` | `{ids:[int]}` | medications by IDs |
| GET | `/v1.0/substances` | `?lang` (req) | array `{id, title, ...}` |
| GET | `/v1.0/health-advisor/human-parts` | `?lang` (req) | `{common:[...], conditions:[...]}` |
| GET | `/v1.0/popular-labs` | `?lang` (req) | array (PopularLab) |
| POST | `/v1.1/biomarkers` | `{lang, digest?, limited?}` | `{needToUpdate, digest, biomarkers:[Biomarker1_1]}` |
| GET | `/v1.1/measurement-units` | `?lang` (req) | array `{id, title, synonymsString, valueType}` |
| GET | `/v1.1/messenger-types` | — | array `{id, name}` |
| GET | `/v1.1/healer-specialities` | `?lang?` | array `{id, title}` |

### `Biomarker1_1` shape

```
id (int)
title (str)
synonyms [{title, language}]
possibleValueMax / possibleValueMin (num)  — in default unit
isAllowAutounit (bool)
biomaterialId (int)             — → /biomaterials
substanceId (int)               — → /substances
displayCategoryId (int)         — → /biomarker-categories
pregnancyCorrelation (int)
sortOrder (int)
isPaid (bool)
articleId (int)                 — wiki article id
unitsFactors [[unitId, factor]] — conversion table
isUnitless (bool)
```

---

## Data model details

### Units conversion

Every measurement carries `value` (canonical) + `originalValue` + `originalUnitId`. `unitsFactors` (from thesaurus) is `[[unitId, factor], …]`.

- `value = originalValue * factor[originalUnitId]` (factor scales original → canonical)
- `convertedValue = value / factor[targetUnitId]` (for any other unit)

Same rule applies to **all numbers in `refs`** — they live in canonical units. `isUnitless=true` skips conversion. `valueType=2` (boolean unit) → the value is a 0/1 indicator.

### Status codes

- Biomarker `status`: `N` (Normal, within reference) or `A` (Abnormal). Spec leaves room for more values but only N/A are documented.
- Disease `status`: `CONFIRMED` (default) or `REJECTED`.
- Imageset `createdBy`: `DOCTOR` or `OTHER`.

### Refs hierarchy

```
common      [lo, hi]   — used for scoring this PID (age/sex-adjusted)
optimal     [lo, hi]   — "healthy" range (advisory; may be empty)
paidOptimal [lo, hi]   — same notion, surfaced to premium users
custom      {ref, originalRef, originalUnit, timePeriod} — per-PID override
```

Priority for scoring/display: `custom` (if `timePeriod` covers the entry date) > B2B partner override > `common`. `optimal` and `paidOptimal` are advisory only.

### `categoryId` vs `displayCategoryId`

- Profile responses use `categoryId`.
- Thesaurus `Biomarker1_1` uses `displayCategoryId`.
- Same vocabulary; resolve either via `/v1.0/biomarker-categories`.

### Language combinations for `/v1.1/biomarkers`

| `lang` | Behaviour |
|---|---|
| `RU` | russian title, russian synonyms |
| `RU+EN` | russian title, ru+en synonyms |
| `EN+RU` | english title, en+ru synonyms |
| `EN` | english title, english synonyms |

Same single-language pattern for `DE`, `ES`, `PT`, `BR`. Other thesaurus endpoints accept only ISO-2 `lang`.

---

## Rate limits & errors

| Code | Meaning |
|---|---|
| 400 | Bad request (validation other than 422) |
| 401 | Unauthorized — missing/invalid Bearer JWE |
| 403 | Forbidden (Health Advisor only) |
| 404 | Not found |
| 422 | Validation error — `{detail:[{loc,msg,type}]}` |
| 500 | Internal server error |

No explicit rate-limit headers documented. Guidance: cache thesaurus responses, refresh via `digest`. Files: one per multipart request. Contact: `support@ornament.health`.

---

## Known issues / gaps

- `GET /profile/submissions?limit=...` returns **500** if `limit` is provided. Workaround: omit `limit` and slice client-side. The CLI does this.
- No documented endpoints to (a) update an existing linked profile's name/sex/birthday, (b) list filesets, (c) self-register webhook URLs, (d) explicit rate-limit values.
- `/health-conditions/explainer` is documented only as markdown text, not in any parsable OAS block.
