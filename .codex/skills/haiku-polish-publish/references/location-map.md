# Location Map Reference

Use this reference after a selected haiku introduces a new place, or when the user corrects an existing place.

## Source data

`public/content/haiku/location-map.json` is keyed by the exact plain-text location displayed by the poem after ruby notation is removed.

```json
{
  "舎人公園": {
    "lat": 35.7986629,
    "lng": 139.7733174,
    "precision": "point",
    "prefecture": "東京都"
  }
}
```

Required fields:

- `lat` and `lng`: decimal WGS84 coordinates used by Leaflet and the GSI pale map.
- `precision`: `point` for a named facility, station, park, temple, or other stable point; `area` for a city, district, broad riverbank, or intentionally approximate record.
- `prefecture`: the full current Japanese prefecture name. Use `東京都`, `北海道`, `京都府`, `大阪府`, or a value ending in `県`.

Do not store `region`. Broad labels such as `東京`, `関東`, `東海`, `関西`, and `四国` are not administrative grouping keys.

## Generated browser data

The page generator writes `public/content/haiku/generated/locations.json` and embeds the same data in the map page under prefecture groups:

```json
{
  "schemaVersion": 1,
  "prefectures": [
    {
      "name": "東京都",
      "count": 55,
      "locations": []
    }
  ],
  "defaultPrefecture": "東京都"
}
```

The generator owns `count`, sorting, and grouping. Do not hand-edit generated HTML under `public/location/`.

## Editing rules

1. Keep the poem source location human-readable and short; prefecture metadata belongs in `location-map.json`.
2. When renaming a location in Markdown, rename or add its exact map key so the generated poem and map still connect.
3. Verify the prefecture before adding a point. Use a stable official facility, municipal, or map source when the place name is ambiguous.
4. Use `precision: area` when only an approximate locality is justified. Do not imply exact coordinates for a broad or private place.
5. Leave genuinely abstract places out of the map rather than inventing a coordinate.
6. Regenerate pages and run `validate_generated_site.py`. It rejects missing prefectures, legacy regions, invalid coordinates, invalid precision, broken prefecture groups, and inconsistent poem counts.
