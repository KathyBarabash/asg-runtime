# Example transform Functions.
from asg_runtime.gin.common.tool_decorator import make_tool


def multiply_by_value(df, column, value, output):
    df[output] = df[column] * value
    return df


def substract_columns(df, from_col, other_col, output):
    df[output] = df[from_col] - df[other_col]
    return df


@make_tool
def map_field(df, source, target):
    """
    map fields or change names from source to target.

    Args:
        df (any): input dataframe.
        source (str) : The first column name.
        target (str) : The second column name.
    Returns:
        df after mapping the source to target
    """
    df[target] = df[source]
    return df


@make_tool
def concatenate_fields(df, col1, col2, output):
    """
    concatenate Two fields.

    Args:
        df (any): input dataframe.
        col1 (str) : The first column.
        col2 (str) : The second column.
        output (str) : the new column name.
    Returns:
        df with new output column of the concatenation of col1 and col2
    """
    # Convert the columns to strings and concatenate their values
    df[output] = df[col1].astype(str) + df[col2].astype(str)
    return df


# Dictionary of available functions
functions = {
    "multiply_by_value": multiply_by_value,
    "concatenate_fields": concatenate_fields,
    "map_field": map_field,
    "substract_columns": substract_columns,
}
