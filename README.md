# Traffic Sign Inventory for QGIS

The Traffic Sign Inventory is a QGIS plugin that creates roadway traffic-sign
and point-feature inventories from Mapillary map-feature data. This tool
supports transportation engineers, planners, and researchers in collecting,
reviewing, and exporting traffic asset information for a selected corridor or
study area.

## Description

The plugin allows users to fetch traffic signs and selected point features from
Mapillary, classify them, map supported traffic signs to MUTCD codes, and add
the results directly to the QGIS map canvas.

It supports current map extent selection, manual coordinate entry, and drawing a
bounding box on the map. Results can be exported to GeoJSON, Shapefile, or CSV
for use in GIS workflows, reports, and inventory review.

This plugin aims to make Mapillary-based traffic sign inventory work easier to
perform inside QGIS.

## Features

Traffic sign inventory:

- Fetch traffic signs from Mapillary vector tiles
- Map supported signs to MUTCD code, description, and category
- Filter by regulatory, warning, information/guide, stop/yield, or speed limit
- Mark unsupported signs as `UNMAPPED`

Point feature inventory:

- Fetch traffic signals
- Fetch pavement markings such as crosswalks, stop lines, and lane arrows
- Fetch infrastructure features such as fire hydrants, street lights, utility
  poles, manholes, and mailboxes
- Fetch street furniture and traffic-control features

Map selection:

- Use current QGIS map extent
- Enter bounding box coordinates manually
- Draw the search area directly on the map
- Re-draw the search area when needed

Output and export:

- Adds a categorized `Feature Inventory` layer to QGIS
- Exports to GeoJSON
- Exports to Shapefile
- Exports to CSV
- Optional enrichment for more accurate coordinates, observation counts,
  first/last seen dates, and Mapillary links

## Installation

Download the plugin ZIP file from the GitHub repository or release page.

In QGIS:

1. Go to **Plugins > Manage and Install Plugins**
2. Select **Install from ZIP**
3. Browse to the downloaded ZIP file
4. Click **Install Plugin**
5. Enable the plugin from the installed plugins list

For source installation, clone the repository into the QGIS plugin directory
using the folder name `traffic_sign_inventory`.

## Mapillary Token Setup

The plugin requires a Mapillary access token with `read` scope.

Create a token from:

<https://www.mapillary.com/dashboard/developers>

Then in QGIS:

1. Go to **Plugins > Traffic Sign Inventory > Settings...**
2. Paste the Mapillary token
3. Click **Test Connection**
4. Click **Save**

The token is stored in the QGIS user profile using `QSettings`. It is not saved
inside the plugin folder.

## Usage

Launch the plugin:

Go to **Plugins > Traffic Sign Inventory > Traffic Sign Inventory**

Set the search area:

- Use the current map extent
- Enter west, south, east, and north coordinates manually
- Draw a rectangle on the map

Choose what to fetch:

- Traffic signs
- Point features
- Both traffic signs and point features

Set filters:

- Choose a sign category or group
- Choose a point feature category
- Enable or disable detailed metadata enrichment

Generate the inventory:

1. Click **Fetch Features**
2. Review the summary
3. Check the new `Feature Inventory` layer on the map
4. Export the results if needed

## Input Requirements

- QGIS 3.6 or later
- Mapillary access token with `read` scope
- Internet connection
- Mapillary coverage in the selected area
- Bounding box in WGS84 coordinates, either entered manually or selected from
  the map canvas

## Example Output Attributes

| Attribute | Description |
| --- | --- |
| `mapillary_id` | Mapillary feature identifier |
| `mapillary_value` | Original Mapillary object value |
| `feature_type` | Traffic sign or point feature |
| `category` | Inventory category used for styling |
| `mutcd_code` | MUTCD code for supported traffic signs |
| `description` | Human-readable feature description |
| `first_seen` | First observation date, when available |
| `last_seen` | Last observation date, when available |
| `num_observations` | Number of linked Mapillary observations |
| `mapillary_link` | Link to the feature in Mapillary |

## Credits

Developer:

- Raswanth Prasath S V

## Acknowledgments

Mapillary data is provided by Mapillary and its contributors.

## License

This plugin is licensed under the GNU General Public License v2.0 or later.

## Support

For issues, feature requests, or questions, please use the GitHub issue tracker:

<https://github.com/Raswanth-Prasath/qgis-traffic-sign-inventory/issues>
