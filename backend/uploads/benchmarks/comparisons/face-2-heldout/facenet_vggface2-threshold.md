# Threshold Governance Report

- Decision: `go`
- Dataset: `face-2-heldout`
- Evaluated images: `49`
- Failed images: `0`

## Recommended Policy

- Match threshold: `0.821888`
- Possible-match threshold: `0.821888`
- Match separation margin: `0.289717`
- Possible-match separation margin: `0.270798`

## Checks

- `enough_probe_faces`: PASS (actual=`49`, required=`20`)
- `own_template_top1_rate`: PASS (actual=`1.0`, required=`0.9`)
- `match_far`: PASS (actual=`0.006667`, required=`0.01`)

## Release Checklist

- [ ] Attach the benchmark report JSON to the release or model-change record.
- [ ] Record the chosen match and possible-match thresholds in deployment notes.
- [ ] Document the benchmark dataset name and image count.
- [ ] Do not change production thresholds without a new benchmark report.
