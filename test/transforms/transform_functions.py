from asg_runtime import make_tool


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
        output (str) : the new column name, the target.
    Returns:
        df with new output column of the concatenation of col1 and col2
    """
    # Convert the columns to strings and concatenate their values
    df[output] = df[col1].astype(str) + df[col2].astype(str)
    return df


@make_tool
def filter_by_year(df, year_col, input_year):
    """
    Filters a DataFrame to return rows where the year matches the given input_year.

    Args:
        df (any): The input pandas DataFrame.
        year_col (str): The name of the column containing the year values.
        input_year (integer): The year to filter the DataFrame by.

    Returns:
        DataFrame: A filtered DataFrame with rows where the year matches input_year.
    """
    return df[df[year_col] == input_year]


@make_tool
def filter_by_quarter(df, month_col, quarter):
    """
    Filters a DataFrame to return rows where the month falls within the specified quarter.

    Args:
        df (any): The input pandas DataFrame.
        month_col (str): The name of the column containing the month values.
        quarter (integer): The quarter to filter by (1 for Q1, 2 for Q2, 3 for Q3, 4 for Q4).

    Returns:
        DataFrame: A filtered DataFrame with rows where the month falls within the given quarter.

    Raises:
        ValueError: If the quarter is not between 1 and 4.
    """
    quarters = {
        1: [1, 2, 3],  # Q1: January, February, March
        2: [4, 5, 6],  # Q2: April, May, June
        3: [7, 8, 9],  # Q3: July, August, September
        4: [10, 11, 12],  # Q4: October, November, December
    }

    if quarter not in quarters:
        raise ValueError("Quarter must be between 1 and 4.")

    return df[df[month_col].isin(quarters[quarter])]
