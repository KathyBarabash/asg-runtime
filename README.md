# ASG Runtime Library

ASG Runtime is a `python` library created for providing runtime support for SFDPs generated with the ASG tool. This library is doing all the `heavy lifting` related to performing the SFDP functionality while allowing the SFDP servers to stay slim and uniform through templating.

## Features

ASG runtime provides support for:
- [x] Parsing the endpoint specifications created by the ASG-tool
- [x] Fetching data form the origin FDPs using async `httpx` library and supporting timeouts, retries, pagination, and caching headers
- [x] Realizing data transformations prescribed by the endpoint specification, including loading and invoking methods (included in `transforms` library)
- [ ] **TODO:** Allowing to observe and manageme the `transforms` library at runtime
- [x] Two level caching: the `origin cache` to keep the responses by the origin FDPs and the `response cache` to keep the computed SFDP responses.
- [x] Statistics regarding the oprtational SFDP, including cache hits/misses, rest client stats, etc.
- [ ] **TODO:** Telemetry post prometheus-ready metrics
- [x] Returning the data to the SFDP endpoints as ORJSON encoded datasets 
- [x] Logging and error reporting 

## Usage

The libary is designed to be present in environments where ASG-generarted SFDPs are executed. The installation can be done from sources by standard pythonic means, e.g. the direct link to the repository, the local sources, or the wheel file. At the moment no insallable package is planned for distribution. For more information about the supported options, see these extended [usage instructions](./docs/usage.md). In addition, the libary is automatically packaged into a pre-baked image that is used by the ASG system to create the templated SFDP instances from, see explanations of this process [here](./docs/image.md).

## Repository structure

```sh
asg-runtime/        
├── README.md           # this file :-)
├── pyproject.toml      # file needed for the build system
├── .env                # example environment file
├── asg_runtime         # library sources
│   ├── caches          # cache modules
│   ├── gin             # gin dependencies
│   ├── http            # http access modules
│   ├── models          # data structures shared across the main modules
│   ├── serializers     # modules imlpementing object serialization
│   ├── telemetry       # TODO placeholder for telemetry modules
│   ├── utils           # shared code like logging
│   ├── __init__.py     # declares exported objects - Executor and Settings
│   ├── executor.py     # main module of the library containing the Executor
│   └── gin_helper.py   # helper module to process data requests
├── docs                # TODO placeholder documentation
├── test                # pytest tests, separated into numbered directories
│   ├── conftest.py     # pytest configuration file   
│   ├── 00_settings
│   ├── 01_spec
│   ├── 02_serializer
│   ├── 03_caches
│   ├── 04_httpx
│   ├── 05_gin_helper
│   ├── 06_executor
│   │
│   ├── app.py          # test app to act as a dependent SFDP
│   ├── transforms      # transforms methods needed by the test SFDP
```
