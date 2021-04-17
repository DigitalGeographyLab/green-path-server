# Green paths routing API
This page contains useful information of the green paths routing API:
- Endpoints
- Path variables
- Status codes
- Response schema

When exploring the API and the source codes, please bear in mind that the word "clean" (paths) is used to refer to "fresh air" (paths). As the routing API is mainly being used by [github.com/DigitalGeographyLab/hope-green-path-ui](https://github.com/DigitalGeographyLab/hope-green-path-ui), it can be worthwhile to take a look at it when familiarizing with it. 

## Endpoints
- www.greenpaths.fi/
- www.greenpaths.fi/paths/{travel_mode}/{routing_mode}/{orig_coords}/{dest_coords}
- e.g. www.greenpaths.fi/paths/walk/green/60.20772,24.96716/60.2037,24.9653
- e.g. www.greenpaths.fi/paths/bike/quiet/60.20772,24.96716/60.2037,24.9653

## Path variables
- travel_mode:
  - `walk`
  - `bike`
- routing_mode:
  - `green`
  - `quiet`
  - `clean` (i.e. fresh air paths)
  - `fast` (only shortest/fastest route)
  - `short` (only shortest route)
  - `safe`  (only safest route, only available for travel mode `bike`)
- orig/dest_coords: {latitude},{longitude}, e.g. 60.20772,24.96716

## Status codes
- Successful routing requests return route data and status code `200`
- Possible status codes for unsuccessful requests are `400`, `404`, `500` and `503`
- All routing errors and their status codes are defined in [src/gp_server/app/constants.py](../src/gp_server/app/constants.py)
- In the case of an routing error, the error message is included in the property `error_key` of the response

## Response schema
### Body
- 2 X GeoJSON FeatureCollection
- Path_FC & Edge_FC

```
  const response = await axios.get(https://www.greenpaths.fi/paths/bike/green/60.20772,24.96716/60.2037,24.9653)
  const Path_FC = response.data.path_FC
```

### Path_FC
- Contains both fastest and exposure optimized (green/quiet/clean) paths
- Each path as a GeoJSON feature
- One line geometry per path
- Several properties on greenery, air quality and noise exposure
- Properties on differences in length and exposures compared to the fastest path
  - Only available for exposure optimized paths (null values for the fastest path)

| Property | Type | Nullable | Description  |
| ------------- | ---- | --- | ----------- |
| type | string | no | Type of the path, one of the following: “green”, "quiet", "clean", “fast” or "safe" (clean = fresh air). |
| id | string | no | Unique name of the path within the returned FeatureCollection. |
| cost_coeff | number | no | Noise or AQI sensitivity coefficient with which the green path was optimized. |
| length | number | no | Length of the path (m). |
| bike_time_cost | number | no | Total cost (index) for biking, proportional to travel time. |
| bike_safety_cost | number | no | Total cost (index) for biking, based on both travel time and biking safety. |
| len_diff | number | no | Difference in path length compared to the fastest path (m). |
| len_diff_rat | number | yes | Difference in path length compared to the fastest path (%). |
| aqc | number | no | Air pollution exposure index. |
| aqc_diff | number | yes | Difference in the air pollution exposure index compared to the fastest path. |
| aqc_diff_rat | number | yes | Difference in the air pollution exposure index compared to the fastest path (%). |
| aqc_diff_score | number | yes | Ratio between the difference in the air pollution exposure index and the length (compared to the fastest path) - i.e. reduction in air pollution exposure index per each additional meter walked. |
| aqc_norm | number | no | Distance normalized air pollution exposure index. |
| aqi_m | number | no | Mean AQI. |
| aqi_m_diff | number | yes | Difference in mean AQI compared to the fastest path. |
| aqi_cl_exps | object | no | Exposures (m) to different AQI classes. Keys represent class names and values exposures as meters. AQI classes are calculated as `floor(aqi * 2) - 1` and they represent (8 x) 0.5 intervals in the original AQI scale from 1.0 to 5.0, class 9 represents the highest possible AQI (5). Class ranges are 1: 1.0-1.5, 2: 1.5-2.0, 3: 2.0-2.5 etc. |
| aqi_cl_pcts | object | no | Exposures (%) to different AQI classes. Keys represent class names and values exposures as percentages. |
| gvi_m | number | no | Mean green view index (GVI) on the path. |
| gvi_m_diff | number | yes | Difference in mean GVI compared to the fastest path. |
| gvi_cl_exps | object | no | Exposures (m) to different GVI ranges (classes). Each class (object key) represents 0.1 wide interval in the original GVI range from 0 to 1, e.g. 1: 0.0-0.1, 2: 0.1-0.2, 3: 0.2-0.3 etc. (`GVI class = ceil(gvi * 10)`). |
| gvi_cl_pcts | object | no | Exposures (%) to different GVI ranges (classes). Same as above but object values are relative shares as percentages. |
| missing_aqi | boolean | no | A boolean variable indicating whether AQI data was available for all edges of the path. |
| missing_gvi | boolean | no | A boolean variable indicating whether GVI data was available for all edges of the path. |
| missing_noises | boolean | no | A boolean variable indicating whether noise data was available for all edges of the path. |
| mdB | number | no | dBmean |
| mdB_diff | number | yes | Difference in dBmean compared to the fastest path. |
| nei | number | no | Noise exposure index (EI). See the method: utils.noise_exposures.get_noise_cost() |
| nei_diff | number | yes | Difference in noise exposure index (EIdiff) compared to the fastest path. |
| nei_diff_rat | number | yes | Difference in noise exposure index (EIdiff) as percentages compared to the fastest path. |
| nei_norm | number | no | Distance-normalized noise exposure index (EIn). |
| noise_range_exps | object | no | Exposures (m) to different 10 dB noise level ranges. Keys represent noise levels and values distances (m). |
| noise_pcts | object | no | Exposures (%) to different noise level ranges. Keys represent noise levels and values percentages. |
| noises | object | no | Exposures to different noise levels. Keys represent noise levels and values distances (m). |

### Additional path properties in research mode
| Property | Type | Nullable | Description  |
| ------------- | ---- | --- | ----------- |
| edge_ids | list | yes | List of edge IDs of the edges that the path consists of. Note that the first and last edge may not exist in the graph as they can be virtual/temporary edges between O/D location and the nearest "real" vertex. |
| edge_data | list | yes | Edge data (length, aqi, gvi, mdB, coords_wgs) as list of dictionaries. |

### Edge_FC
- Contains edge geometries of both fastest and exposure optimized (green/quiet/clean) paths
- Edge geometries are aggregated by greenery, noise level or air quality (depending on routing mode)
- For visualizing variation in environmental data on the paths

| Property | Type | Nullable | Description  |
| ------------- | ---- | --- | ----------- |
| path | string | no | The name of the path to which the edge belongs to. |
| value | number | no | Either GVI class, AQI class or noise level range of the edge. |
| p_length | number | no | The length of the path to which the edge belongs to (m). |
| p_len_diff | number | no | Difference in length between the fastest path and the path to which the edge belongs to (m). |

### Example Path_FC
```yaml
Path_FC: {
  features: [ {
    geometry: { coordinates: [...], type: "LineString" },
    properties: {
      type: "short",
      id: "short",
      cost_coeff: 0,
      length: 492.92,
      bike_time_cost: 521.0,
      bike_safety_cost: 551.0,
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
      aqi_cl_pcts: {
        2: 100
      },
      aqi_m: 2.3,
      aqi_m_diff: null,
      gvi_m: 0.67,
      gvi_m_diff: null,
      gvi_cl_exps: {
        2: 375.2,
        3: 117.74
      },
      gvi_cl_pcts: {
        2: 76.11,
        3: 23.89
      },
      mdB: 67.5,
      mdB_diff: null,
      missing_aqi: false,
      missing_gvi: false,
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
      }
    },
    type: “Feature”
  }, {
    geometry: { coordinates: [...], type: "LineString" },
    properties: {
      type: "quiet",
      id: "q_20",
      cost_coeff: 20,
      length: 629.29,
      bike_time_cost: 521.0,
      bike_safety_cost: 551.0,
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
      aqi_cl_pcts: {
        2: 100
      },
      aqi_m: 2.31,
      aqi_m_diff: 0.01,
      gvi_m: 0.75,
      gvi_m_diff: 0.08,
      gvi_cl_exps: {
        2: 273.8,
        3: 355.49
      },
      gvi_cl_pcts: {
        2: 43.51,
        3: 56.49
      },
      mdB: 55.4,
      mdB_diff: -12.1,
      missing_aqi: false,
      missing_gvi: false,
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
      }
    },
    type: “Feature”
    },
    {...}, {...}, ... ],
type: "FeatureCollection"
}
```
