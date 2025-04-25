from asg_runtime.gin_helper import GinHelper
from asg_runtime.models import (
    LoggingSettings,
    Settings,
)
from asg_runtime.utils import get_logger, setup_logging

loggingSettings = LoggingSettings(log_level="DEBUG")
setup_logging(loggingSettings)
logger = get_logger("test_transform")

data = {
  ".": [
    {
      "person_id": 1,
      "gender_concept_id": 101,
      "year_of_birth": 1991,
      "month_of_birth": 10,
      "day_of_birth": 19,
      "birth_datetime": "1991-10-19T00:00:00",
      "race_concept_id": 201,
      "ethnicity_concept_id": 301,
      "location_id": 401,
      "provider_id": 501,
      "care_site_id": 601,
      "person_source_value": "PSV001",
      "gender_source_value": "GSV001",
      "gender_source_concept_id": 701,
      "race_source_value": "RSV001",
      "race_source_concept_id": 801,
      "ethnicity_source_value": "ESV001",
      "ethnicity_source_concept_id": 901
    },
    {
      "person_id": 2,
      "gender_concept_id": 102,
      "year_of_birth": 1969,
      "month_of_birth": 9,
      "day_of_birth": 17,
      "birth_datetime": "1969-09-17T00:00:00",
      "race_concept_id": 202,
      "ethnicity_concept_id": 302,
      "location_id": 402,
      "provider_id": 502,
      "care_site_id": 602,
      "person_source_value": "PSV002",
      "gender_source_value": "GSV002",
      "gender_source_concept_id": 702,
      "race_source_value": "RSV002",
      "race_source_concept_id": 802,
      "ethnicity_source_value": "ESV002",
      "ethnicity_source_concept_id": 902
    },
    {
      "person_id": 3,
      "gender_concept_id": 103,
      "year_of_birth": 1951,
      "month_of_birth": 12,
      "day_of_birth": 26,
      "birth_datetime": "1951-12-26T00:00:00",
      "race_concept_id": 203,
      "ethnicity_concept_id": 303,
      "location_id": 403,
      "provider_id": 503,
      "care_site_id": 603,
      "person_source_value": "PSV003",
      "gender_source_value": "GSV003",
      "gender_source_concept_id": 703,
      "race_source_value": "RSV003",
      "race_source_concept_id": 803,
      "ethnicity_source_value": "ESV003",
      "ethnicity_source_concept_id": 903
    },
    {
      "person_id": 4,
      "gender_concept_id": 104,
      "year_of_birth": 1981,
      "month_of_birth": 12,
      "day_of_birth": 22,
      "birth_datetime": "1981-12-22T00:00:00",
      "race_concept_id": 204,
      "ethnicity_concept_id": 304,
      "location_id": 404,
      "provider_id": 504,
      "care_site_id": 604,
      "person_source_value": "PSV004",
      "gender_source_value": "GSV004",
      "gender_source_concept_id": 704,
      "race_source_value": "RSV004",
      "race_source_concept_id": 804,
      "ethnicity_source_value": "ESV004",
      "ethnicity_source_concept_id": 904
    },
    {
      "person_id": 5,
      "gender_concept_id": 105,
      "year_of_birth": 1988,
      "month_of_birth": 11,
      "day_of_birth": 3,
      "birth_datetime": "1988-11-03T00:00:00",
      "race_concept_id": 205,
      "ethnicity_concept_id": 305,
      "location_id": 405,
      "provider_id": 505,
      "care_site_id": 605,
      "person_source_value": "PSV005",
      "gender_source_value": "GSV005",
      "gender_source_concept_id": 705,
      "race_source_value": "RSV005",
      "race_source_concept_id": 805,
      "ethnicity_source_value": "ESV005",
      "ethnicity_source_concept_id": 904
    },
  ]
}

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
                                "description": "Filters a DataFrame to return rows where the age\n(calculated from year_of_birth, month_of_birth,day_of_birth) is bigger than the given input_age.",
                                "params": {"age": 60, "target": "person_age"},
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

def test_helper_create():
    settings = Settings()
    gin_helper = GinHelper(spec_string, settings.transforms_path)
    logger.debug("gin helper created")

def test_helper_get_sources():
    settings = Settings()
    gin_helper = GinHelper(spec_string, settings.transforms_path)
    logger.debug("gin helper created")

    sources = gin_helper.get_origin_sources()
    logger.debug(f"gin helper collected sources: {sources}")

def test_helper_transform():
    settings = Settings()
    gin_helper = GinHelper(spec_string, settings.transforms_path)
    logger.debug("gin helper created")

    transformed = gin_helper.apply_transforms(data)
    logger.debug(f"gin helper collected sources: {transformed}")

