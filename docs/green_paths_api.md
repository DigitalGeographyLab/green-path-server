# Green paths routing API
This page contains useful information of the green paths routing API:
- Endpoints
- Schema
- Exceptions

When exploring the API and the source codes, please bear in mind that the word "clean" (paths) is used to refer to "fresh air" (paths). As the routing API is already being used by [github.com/DigitalGeographyLab/hope-green-path-ui](https://github.com/DigitalGeographyLab/hope-green-path-ui), it's probably a good idea to take a look at it when familiarizing with the API. 

## Endpoints
- www.greenpaths.fi/
- www.greenpaths.fi/quietpaths/<orig_coords>/<dest_coords>
- www.greenpaths.fi/cleanpaths/<orig_coords>/<dest_coords>
- e.g. www.greenpaths.fi/quietpaths/60.20772,24.96716/60.2037,24.9653
- e.g. www.greenpaths.fi/cleanpaths/60.20772,24.96716/60.2037,24.9653

## Response
- 2 X GeoJSON FeatureCollections
- Edge_FC & Path_FC

```
  const response = await axios.get(https://www.greenpaths.fi/cleanpaths/60.20772,24.96716/60.2037,24.9653)
  const Path_FC = response.data.path_FC
```

## Edge_FC
- Contains both short and green (quiet/clean) paths
- Geometry of the paths is split to separate lines by noise level or air quality
- For visualizing pollutants on the paths by colours on the map
- To be shown on top of the Path_FC layer

| Property | Type | Nullable | Description  |
| ------------- | ---- | --- | ----------- |
| path | string | no | The name of the path to which the edge belongs to. |
| value | number | no | Either AQI class or noise level range of the edge. |
| p_length | number | no | The length of the path to which the edge belongs to (m). |
| p_len_diff | number | no | Difference in length between the shortest path and the path to which the edge belongs to (m). |

## Path_FC
- Contains both short and green (quiet/clean) paths
- Each path as a GeoJSON feature
- One line geometry per path
- Several properties on noise exposure, AQI exposure and length
- Properties on differences in length and exposures compared to the shortest path
  - Only available for green paths (null values for the shortest path)

| Property | Type | Nullable | Description  |
| ------------- | ---- | --- | ----------- |
| type | string | no | Type of the path: either “short”, “quiet” or "clean" (clean = fresh air). |
| id | string | no | Unique name of the path (e.g. “short” or “qp_0.2”). |
| cost_coeff | number | no | Noise or AQI sensitivity coefficient with which the green path was optimized. |
| length | number | no | Length of the path (m). |
| len_diff | number | no | Difference in path length compared to the shortest path (m). |
| len_diff_rat | number | yes | Difference in path length compared to the shortest path (%). |
| aqc | number | no | Air pollution exposure index. |
| aqc_diff | number | yes | Difference in the air pollution exposure index compared to the shortest path. |
| aqc_diff_rat | number | yes | Difference in the air pollution exposure index compared to the shortest path (%). |
| aqc_diff_score | number | yes | Ratio between the difference in the air pollution exposure index and the length (compared to the shortest path) - i.e. reduction in air pollution exposure index per each additional meter walked. |
| aqc_norm | number | no | Distance normalized air pollution exposure index. |
| aqi_cl_exps | object | no | Exposures (m) to different AQI classes. Keys are class names and values exposures as meters. |
| aqi_m | number | no | Mean AQI. |
| aqi_m_diff | number | yes | Difference in mean AQI compared to the shortest path. |
| aqi_pcts | object | no | Exposures (%) to different AQI classes. Keys are class names and values exposures as shares. |
| missing_aqi | boolean | no | A boolean variable indicating whether AQI data was available for all of the edges of the path. |
| missing_noises | boolean | no | A boolean variable indicating whether noise data was available for all of the edges of the path. |
| mdB | number | no | dBmean |
| mdB_diff | number | yes | Difference in dBmean compared to the shortest path. |
| nei | number | no | Noise exposure index (EI). |
| nei_diff | number | yes | Difference in noise exposure index (EIdiff) compared to the shortest path. |
| nei_diff_rat | number | yes | Difference in noise exposure index (EIdiff) as percentages compared to the shortest path. |
| nei_norm | number | no | Distance-normalized noise exposure index (EIn). |
| noise_pcts | object | no | Exposures (%) to different noise levels. Keys represent noise levels and values shares. |
| noise_range_exps | object | no | Exposures (m) to different 10 dB noise level ranges. Keys represent noise levels and values distances (m). |
| noises | object | no | Exposures to different noise levels. Keys represent noise levels and values distances (m). |
| noises_diff | object | yes | Differences in exposures to different noise levels. Keys represent noise levels and values differences distances (m). |
| path_score | number | yes | Ratio between difference in noise exposure index and length compared to the shortest path - i.e. reduction in noise exposure index per each additional meter walked. |

## Exceptions
- Currently, only very simple exception forwarding is implemented at the server. 
- In case anything goes wrong during routing, the server returns a descriptive error message (in the error property of the data) to be shown to the user. 
- One way to check and catch a potential routing error is presented below:

```
  const response = await axios.get(https://www.greenpaths.fi/cleanpaths/60.20772,24.96716/60.2037,24.9653)
  if (response.data.error) throw response.data.error
```

## Example Path_FC
```yaml
Path_FC: {
  features: [ {
    geometry: { coordinates: [...], type: "LineString" },
    properties: {
      type: "short",
      id: "short",
      cost_coeff: 0,
      length: 492.92,
      len_diff: 0,
      len_diff_rat: null,
      aqc: 160.62,
      aqc_diff: null,
      aqc_diff_rat: null,
      aqc_diff_score: null,
      aqc_norm: 0.326,
      aqi_cl_exps: {
        2: 492.94
      },
      aqi_m: 2.3,
      aqi_m_diff: null,
      aqi_pcts: {
        2: 100
      },
      mdB: 67.5,
      mdB_diff: null,
      missing_aqi: false,
      missing_noises: false,
      nei: 286.1,
      nei_diff: null,
      nei_diff_rat: null,
      nei_norm: 0.58,
      noise_pcts: {
        40: 11.7,
        50: 8.7,
        55: 0.9,
        60: 1.1,
        65: 2,
        70: 75.6
      },
      noise_range_exps: {
        40: 57.82,
        50: 43,
        55: 4.31,
        60: 5.51,
        65: 9.66,
        70: 372.62
      },
      noises: {
        45: 57.81,
        50: 43,
        55: 4.31,
        60: 5.51,
        65: 9.66,
        70: 372.62
      },
      noises_diff: null,
      path_score: null,
    },
    type: “Feature”
  }, {
    geometry: { coordinates: [...], type: "LineString" },
    properties: {
      type: "quiet",
      id: "q_20",
      cost_coeff: 20,
      length: 629.29,
      len_diff: 136.4,
      len_diff_rat: 27.7,
      aqc: 206.76,
      aqc_diff: 46.14,
      aqc_diff_rat: 28.7,
      aqc_diff_score: -0.3,
      aqc_norm: 0.329,
      aqi_cl_exps: {
        2: 629.31
      },
      aqi_m: 2.31,
      aqi_m_diff: 0.01,
      aqi_pcts: {
        2: 100
      },
      mdB: 55.4,
      mdB_diff: -12.1,
      missing_aqi: false,
      missing_noises: false,
      nei: 158.3,
      nei_diff: -127.8,
      nei_diff_rat: -44.7,
      nei_norm: 0.25,
      noise_pcts: {
        40: 38.3,
        50: 9.5,
        55: 19.2,
        60: 21.1,
        65: 6.5,
        70: 5.4
      },
      noise_range_exps: {
        40: 241.22,
        50: 59.88,
        55: 120.93,
        60: 132.5,
        65: 40.85,
        70: 33.91
      },
      noises: {
        45: 209.22,
        50: 59.88,
        55: 120.93,
        60: 132.5,
        65: 40.85,
        70: 33.91
      },
      noises_diff: {
        40: 0,
        45: 151.41,
        50: 16.88,
        55: 116.62,
        60: 126.99,
        65: 31.19,
        70: -338.71,
        75: 0
      },
      path_score: 0.9,
      },
    type: “Feature”
    },
    {...}, {...}, ... ],
type: "FeatureCollection"
}
```
