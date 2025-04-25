import datetime
import logging

from asg_runtime import make_tool

logger = logging.getLogger("med_trans")

current_date = datetime.datetime.now()


def calculate_age(row):
    # logger.debug(f"calculate_age - enter for \n{row}")
    dob = datetime.datetime(row["year_of_birth"], row["month_of_birth"], row["day_of_birth"])
    age = (current_date - dob).days // 365  # Approximation using days
    # logger.debug(f"calculate_age - return {age}")
    return age


@make_tool
def persons_above_age(df, age, target):
    """
    Filters a DataFrame to return rows where the age
      (calculated from year_of_birth, month_of_birth,day_of_birth) is bigger than the given input_age.

    Args:
        df (any): The input pandas DataFrame.
        age (integer): The age to filter the DataFrame by.
        target (str): the new column name, the target.

    Returns:
        DataFrame: A filtered DataFrame with rows where the age is bigger than input_age.
    """
    logger.debug(f"persons_above_age - enter for age={age}, target={target}")
    df[target] = df.apply(calculate_age, axis=1)
    df = df[df[target] >= age]
    # logger.debug(f"persons_above_age - return {df}")
    return df
