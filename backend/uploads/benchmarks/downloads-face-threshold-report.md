# Threshold Governance Report

- Decision: `no_go`
- Dataset: `downloads-face-heldout`
- Evaluated images: `15`
- Failed images: `1`

## Recommended Policy

- Match threshold: `0.004495`
- Possible-match threshold: `0.024116`
- Match separation margin: `6.6e-05`
- Possible-match separation margin: `5.1e-05`

## Checks

- `enough_probe_faces`: FAIL (actual=`15`, required=`20`)
- `own_template_top1_rate`: FAIL (actual=`0.666667`, required=`0.9`)
- `match_far`: PASS (actual=`0.0`, required=`0.01`)

## Release Checklist

- [ ] Attach the benchmark report JSON to the release or model-change record.
- [ ] Record the chosen match and possible-match thresholds in deployment notes.
- [ ] Document the benchmark dataset name and image count.
- [ ] Do not change production thresholds without a new benchmark report.
