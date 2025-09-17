# The Impact of Caching in ASG-SFDP Runtime

Preliminary experiments with ASG-runtime clearly demonstrate the significant performance and efficiency gains achievable through layered caching. In a test scenario with repeated requests for transformed data derived from a large dataset (~47 MB, 1M records), enabling both origin and response caches reduced processing time by 92%, data transferred from the origin by 90%, and eliminated redundant transformations. In contrast to the baseline (no caching), these improvements yield orders-of-magnitude reductions in backend load and network I/O, directly translating to lower latency, reduced infrastructure stress, and greater scalability—especially critical in federated deployments where origin servers may be remote or rate-limited.

This validates the SFDP model's two-layer caching approach as not only a performance optimization but a core enabler of sustainable federated data sharing, allowing for more responsive apps, efficient compute utilization, and significant cost savings.

In addition to reducing redundant origin requests and transformation costs, the ASG runtime leverages binary encoding (e.g., via orjson) before caching origin and response payloads. This significantly reduces the size of cache entries — by up to 40% compared to raw JSON — improving storage efficiency in persistent caches and reducing network usage when serving cached responses.

## Limited Case Study
For this is limited preliminary case study of the ASG-driven approach to cerating and executing SFDPs in TEADAL, we run `10` requests for the data endpoints (5 requests for each endpoint), for different cache configurations.

Information common to all the runs:

- Both data endpoints fetch the same origin dataset, `/persons`
- Origin dataset size in bytes is `4,7041,911` and it contains `1,000,000` records with `18` elements each.
- The first SFDP data endpoint returns reduced dataset of `21,547` with `2` each; when encoded, this dataset's size in bytes is `816,452`
- The first SFDP data endpoint returns reduced dataset of `63,786` with `2` each; when encoded, this dataset's size in bytes is `2,416,915`



1. With both caches disabled, we see that origing dataset is fetched ten times, and the transormations were loaded and applied ten times:
```sh
{
  "app": {
    "requests_received": 10,
    "requests_failed": 0,
    "requests_served": 10,
    "bytes_served": 16166835,    # orjson encoded size here
    "processing_time": 426.22
  },
  "rest": {
    "requests_issued": 10,
    "bytes_received": 470419110, # bytes transfered here
    "fetching_time": 356.91
  }
}
```

1. With only origin cache enabled, we see that origin dataset was only fetched once (although every time dataset freshness was checked before reusing cached data), but the transormations were loaded and applied ten times:
```sh
{
  "app": {
    "requests_received": 10,
    "requests_failed": 0,
    "requests_served": 10,
    "bytes_served": 16166835,   # orjson encoded size here
    "processing_time": 80.74
  },
  "rest": {
    "requests_issued": 1,
    "bytes_received": 47041911, # bytes transfered here
    "fetching_time": 29.69
  },
  "origin_cache": {
    "hits": 9,
    "misses": 1
  }
}
```

1. With only response cache enabled, we see that origin dataset was fetched twice, and the transormations were loaded and applied twice, once for each data endpoint:
```sh
{
  "app": {
    "requests_received": 10,
    "requests_failed": 0,
    "requests_served": 10,
    "bytes_served": 16166835,
    "processing_time": 57.88
  },
  "rest": {
    "requests_issued": 2,
    "bytes_received": 94083822,
    "fetching_time": 45.65
  },
  "response_cache": {
    "hits": 8,
    "misses": 2
  }
}
```

1. With both caches enabled, we see that origin dataset was fetched only once, and the transormations were loaded and applied twice, once for each data endpoint. 
```sh
{
  "app": {
    "requests_received": 10,
    "requests_failed": 0,
    "requests_served": 10,
    "bytes_served": 16166835,
    "processing_time": 32.77
  },
  "rest": {
    "requests_issued": 1,
    "bytes_received": 47041911,
    "fetching_time": 21.81
  },
  "response_cache": {
    "hits": 8,
    "misses": 2
  },
  "origin_cache": {
    "hits": 1,
    "misses": 1
  }
}
```

Note that with response cache enabled, the origin data freshness is not checked before using the cached response so this configuration is only applicable for FDPs that are known to be mostly static. Whe we know FDP data was refreshed, the SFDP caches can be purged through `/service` endpoints.

## Towards Automated Case-Study 
> this will be done as part of KPI validation

Preliminary study can be extended to receive more solid data:
1. Create `pytest` based suite with fixtures that will select settings combinations, send data enpoint requests, followed by `/service/stats` requests, agregate and report the results.
2. In addition to reporting cache stats, extend the exposed stats to also print the encodings stats (already aggregated by the asg-runtime) and report the storage savings aspect of the proach.
3. When/if the telemetry postings are implemented, the reporting can be integrated with the monitoring subsystem, both for system wide observability and for helping to validate the project KPIs.
