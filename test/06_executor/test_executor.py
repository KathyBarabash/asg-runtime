import sys

sys.path.append(".")

import asyncio

import pytest

from asg_runtime import Executor
from asg_runtime.models import (
    Settings,
)
from asg_runtime.utils import (
    get_logger,
    setup_logging,
)

settings = Settings()
settings.logging.log_level = "DEBUG"
setup_logging(settings.logging)
logger = get_logger("exec_med")
# logger.debug(f"Executor tests starting with settings={settings.model_dump()}")

path_params = {}
query_params = {}
full_spec = {
    "apiVersion": "connector/v1",
    "kind": "connector/v1",
    "metadata": {
        "name": "TBD",
        "description": "TBD",
        "inputPrompt": "DUMMY PROMPT - SPEC IS CREATED STATICALLY",
    },
    "spec": {
        "timeout": 333,
        "apiCalls": {
            "GetPersonsAll": {
                "type": "url",
                "endpoint": "/persons",
                "method": "get",
                "arguments": [],
            }
        },
        "output": {
            "execution": "",
            "runtimeType": "python",
            "data": {"Person": {"api": "GetPersonsAll", "metadata": [], "path": "."}},
            "exports": {
                "Person": {
                    "dataframe": ".",
                    "fields": {
                        "person_ID": [
                            {
                                "function": "map_field",
                                "description": "map fields or change names from source to target.",
                                "params": {"source": "person_id", "target": "person_ID"},
                            }
                        ],
                        "person_age": [
                            {
                                "function": "persons_above_age",
                                "description": "Filters a DataFrame to return rows where the age\n      (calculated from year_of_birth, month_of_birth,day_of_birth) is bigger than the given input_age.",
                                "params": {"age": 30, "target": "person_age"},
                            }
                        ],
                        "care_site_id": [
                            {
                                "function": "map_field",
                                "description": "map fields or change names from source to target.",
                                "params": {"source": "care_site_id", "target": "care_site_id"},
                            }
                        ],
                    },
                }
            },
        },
    },
    "servers": [{"url": "http://medicine01.teadal.ubiwhere.com/fdp-medicine-node01/"}],
    "apiKey": "DUMMY_KEY",
    "auth": "apiToken",
}


@pytest.mark.asyncio
async def test_executor_med():
    executor = await Executor.async_create(settings)
    logger = get_logger("executor-test")

    for i, param in enumerate(path_params):
        if (
            full_spec["spec"]["apiCalls"]["GetPersonsAll"]["arguments"][i]["argLocation"]
            == "parameter"
        ):
            full_spec["spec"]["apiCalls"]["GetPersonsAll"]["arguments"][i]["value"] = path_params[
                param
            ]

    for i, param in enumerate(query_params):
        if (
            full_spec["spec"]["apiCalls"]["GetPersonsAll"]["arguments"][i]["argLocation"]
            == "header"
        ):
            full_spec["spec"]["apiCalls"]["GetPersonsAll"]["arguments"][i]["value"] = query_params[
                param
            ]

    spec_string = f"""{full_spec}"""
    times = 2
    while times:
        try:
            logger.debug("getting the data")
            result = await executor.async_get_endpoint_data(spec_string)
            status = result.get("status")
        except Exception as e:
            logger.error(f"Exception getting the data: {str(e)}")

        if status != "ok":
            logger.error(f"Exception getting the data: result = {result}")
            return

        data = result.get("data")
        logger.debug(f"received data of type {type(data)} and size = {len(data)}")

        if data and isinstance(data, dict):
            datasets = 1
            for key, val in data.items():
                logger.debug(f"dataset {datasets}: {key} has val of type={type(val)}")
                datasets += 1
        logger.debug(f"times={times}, stats = {executor.get_stats()}")
        times -= 1

    return


async def main(times: int | None = 2):
    test_executor_med(times)


if __name__ == "__main__":
    import asyncio

    asyncio.run(main(times=2))
