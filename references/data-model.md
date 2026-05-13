# Data model

Useful to know before you start poking at the JSON.

## Biomarker entry

A single recorded measurement looks like:

```json
{
  "seid": "eb89b98b-…",          // submission-entry id
  "sid": "1d126f6c-…",           // submission id (groups entries from one upload)
  "value": "1.79",               // canonical (internal) value, ALWAYS in canonical unit
  "originalValue": "1.79",       // what the lab actually wrote on the sheet
  "date": 1756771200,            // unix epoch (seconds)
  "originalUnitId": 9            // unit the lab used; map via measurement-units thesaurus
}
```

**Always display `originalValue + measurement-units[originalUnitId]`.** `value` is the canonical form, e.g. mmol/L cholesterol is stored as a huge number — that's not a bug.

## Biomarker block

```json
{
  "id": 38,
  "categoryId": 17,
  "isUnitless": false,
  "status": "N",          // 'N' = within reference, 'A' = abnormal
  "entries": [ …list of measurements… ]
}
```

`status` reflects the latest entry. Older entries may have been abnormal even if the current one is normal — to see that, walk `entries` and compare each one to the ref range yourself.

## Reference ranges (`refs`)

The top-level `refs` map looks like:

```json
"refs": {
  "38": {
    "common":      [4.0, 5.6],      // baseline ref range (canonical units!)
    "optimal":     [],              // free Ornament "optimal" hint
    "paidOptimal": [4.8, 5.1],      // tighter range from Ornament's paid tier
    "custom":      { "ref": […], "originalRef": […], "originalUnit": …, "timePeriod": [a, b] }
  },
  ...
}
```

- `common` is the most universally available range. Always exists.
- `optimal` and `paidOptimal` are tighter; treat as advisory. Both are **canonical** units.
- `custom` is a manually-overridden range for that specific profile (e.g. a doctor changed it). When present and `timePeriod` covers the entry's `date`, prefer it.

### Converting ref to original units

Canonical → original via `biomarker.unitsFactors`:

```
unitsFactors = [[unitId, factor], …]   // canonical = original * factor
```

Inverse: `original = canonical / factor`. The helper `_lib.reference_in_original_unit` does this. For unit-less biomarkers (`isUnitless: true`) the ranges are already in their natural scale.

## Identifiers

| Id              | What it is                                                        |
|-----------------|-------------------------------------------------------------------|
| `pid`           | UUID of a profile / patient                                       |
| `ssoId`         | UUID of an account; one ssoId may own multiple pids               |
| `sid`           | UUID of a submission (one upload of one or more reports)          |
| `seid`          | UUID of a single entry inside a submission                        |
| `biomarker.id`  | Integer; key into the biomarker thesaurus                         |
| `unitId` etc.   | Integer; key into the measurement-units thesaurus                 |

## Thesaurus

The thesaurus is huge (~5,000 biomarkers, ~hundreds of units). Cache locally — it changes rarely. Use `digest` from the response to detect updates if you want to be polite about refreshes.

Localisation strings accepted by `lang`: ISO-2 codes (`EN`, `RU`, …) or combinations (`EN+RU`) which return both.

## Status quirks

- `isPaid: true` in the thesaurus means the *biomarker insight* (paid optimal range, interpretation) is paywalled, **not** that you can't read the value.
- `displayCategoryId` is what to render UI under (e.g. "Lipid profile"); `categoryId` on a measurement is the same in practice but the thesaurus value is the source of truth.
- Dates from labs may have `hasDate: false` on submissions — Ornament guessed when it wasn't on the sheet.
