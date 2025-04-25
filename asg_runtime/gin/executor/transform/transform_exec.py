import operator

import pandas as pd

from asg_runtime.utils import get_logger

from .load_functions import load_user_functions
from .transform_funtions import functions

logger = get_logger("transform_exec")


def apply_transformations_json(
    json_data :any, 
    process_data_set, 
    user_functions_path=None
) -> list[dict]:
    """
    Create a pandas data frame from json_output and path, and apply transformations defined in process_data_set.

    Args:
        json_data (json): json data to transform.
        process_data_set (ProcessDataSet): Dataset transformation specification object.
    Returns:
        (list[dict]): transformed json data
    """
    logger.debug(
        f"apply_transformations_json enter process_data_set = {process_data_set}"
    )

    input_df = pd.json_normalize(json_data)
    logger.debug(f"input dataframe shape={input_df.shape}")

    res_df = pd.DataFrame()
    for field_name, transform_funcs in process_data_set.fields.items():
        logger.debug(f"processing field field_name={field_name}, transform_funcs={transform_funcs}")
        res_df[field_name] = _apply_transformations(
            input_df, transform_funcs, field_name, user_functions_path)

    res_df = res_df.dropna()
    logger.debug(f"result dataframe shape={res_df.shape}")

    res_json = res_df.to_dict(orient='records')
    logger.debug(f"transformed input data into {len(res_json)} transformed data items")
    return res_json


def _apply_transformations(
    df, transform_functions, export_column_name, user_functions_path=None
) -> pd.DataFrame:
    """
    apply transformation functions on a dataframe and export the output series.

    Args:
        df (pd.DataFrame): dataframe to apply transformation on.
        transform_functions (List[TransformFunction]): transformation functions specification list.
        export_column_name (str): name of the output field in the output dataframe.
    Returns:
        pd.DataFrame (series): Returns pandas dataframe of the data after transformation specified in column export_column_name.
    """
    logger.debug(f"_apply_transformations enter for export_column_name={export_column_name}")
    for transform_func in transform_functions:
        func_name = transform_func.function
        params = transform_func.params
        logger.debug(f"func_name={func_name}, params={params}")

        if func_name.startswith("pd.DataFrame"):
            func = getattr(df, func_name.split(".")[-1], None)
            if func is not None:
                logger.debug("invoking pandas function")
                df = func(**params)
            else:
                raise ValueError(
                    f"Unsupported function, pandas doesn't have function called: {func_name}"
                )
        elif func_name == "operator":
            operator = params.pop("operator")
            if operator in SUPPORTED_OPERATIONS:
                logger.debug("invoking supported operator")
                df.loc[:, params["output"]] = SUPPORTED_OPERATIONS[operator](
                    df[params["col1"]], df[params["col2"]]
                )
            else:
                raise ValueError(f"Unsupported operator: {operator}")
        elif func_name in functions:
            logger.debug(f"invoking custom function: {functions[func_name]}")
            df = functions[func_name](df, **params)
        elif user_functions_path is not None:
            logger.debug("loading user functions")
            user_functions = load_user_functions(user_functions_path)
            if func_name in user_functions:
                logger.debug(f"Running {func_name} from user defined package")
                df = user_functions[func_name](df, **params)
        else:
            raise ValueError(f"Unsupported function: {func_name}")

    logger.debug("_apply_transformations exit")
    return df[export_column_name]


# Define supported operations for arithmetic, since they need special handling
SUPPORTED_OPERATIONS = {
    "subtract": operator.sub,
    "multiply": operator.mul,
    "add": operator.add,
    "divide": operator.truediv,
}
