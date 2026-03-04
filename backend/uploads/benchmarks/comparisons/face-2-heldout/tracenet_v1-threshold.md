# Threshold Governance Report

- Decision: `no_go`
- Dataset: `face-2-heldout`
- Evaluated images: `49`
- Failed images: `0`

## Recommended Policy

- Match threshold: `0.002417`
- Possible-match threshold: `0.021391`
- Match separation margin: `0.000261`
- Possible-match separation margin: `0.000185`

## Checks

- `enough_probe_faces`: PASS (actual=`49`, required=`20`)
- `own_template_top1_rate`: FAIL (actual=`0.306122`, required=`0.9`)
- `match_far`: PASS (actual=`0.009524`, required=`0.01`)

## Release Checklist

- [ ] Attach the benchmark report JSON to the release or model-change record.
- [ ] Record the chosen match and possible-match thresholds in deployment notes.
- [ ] Document the benchmark dataset name and image count.
- [ ] Do not change production thresholds without a new benchmark report.
