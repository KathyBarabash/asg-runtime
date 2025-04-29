from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request, Response
from starlette.status import HTTP_200_OK

from asg_runtime import Executor


@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        # settings = Settings()
        executor = await Executor.async_create()
        app.state.executor = executor
        app.state.settings = executor.get_settings()

        yield  # reached if no errors
    except Exception:
        # log and exit on startup error
        import traceback
        print(traceback.format_exc())
        raise

    # clean things up if needed
    await executor.shutdown()


app = FastAPI(lifespan=lifespan)

# --- Service Endpoints ---

@app.get("/service/settings", tags=["service"])
def get_settings(request: Request) -> dict:
    return app.state.settings


@app.get("/service/stats", tags=["service"])
async def get_stats(request: Request) -> dict:
    executor: Executor = request.app.state.executor
    return executor.get_stats()


@app.post("/service/origin_cache/clean", tags=["service"])
async def clear_origin_cache(request: Request) -> str:
    executor: Executor = request.app.state.executor
    result = await executor.async_clear_origin_cache()
    return result


@app.post("/service/response_cache/clean", tags=["service"])
async def clear_response_cache(request: Request) -> str:
    executor: Executor = request.app.state.executor
    result = await executor.async_clear_response_cache()
    return result


# --- Data Endpoints ---
# helper called by all data endpoints
async def get_endpoint_data(request: Request, endpoint_spec: str) -> Response:
    executor: Executor = request.app.state.executor
    try:
        result = await executor.async_get_endpoint_data(endpoint_spec)

        if result.get("status") == "ok":
            return Response(
                content=result["data"], 
                media_type="application/json",
                status_code=HTTP_200_OK)
        
        # "status" is is not "ok" - return error
        raise HTTPException(status_code=500, detail=result.get("message", "Unknown error"))

    except HTTPException:
        raise
    except Exception as e:  
        # unhandled exception - log and return error
        import traceback
        print(traceback.format_exc())
        message = f"Unhandled exception of type {type(e)} in get_endpoint_data: {e}."
        raise HTTPException(status_code=500, detail=message)
 
# --- Generated Data Endpoints ---
@app.get("/persons_above_60", tags=["data"])
async def persons_above_60(request: Request):
    """
    This endpoint returns all the people of age > 60
    """
    path_params = {}
    query_params = {}
    # Create Yaml and run executor
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

    return await get_endpoint_data(request, spec_string)

