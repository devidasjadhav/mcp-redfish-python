from langchain.tools import tool
import math

@tool
def calculate(expression: str) -> str:
    """Calculate the result of a mathematical expression.

    Args:
        expression: A mathematical expression to evaluate, e.g. "2 + 2" or "sqrt(16)"
    """
    try:
        # Use eval for simple expressions, but be careful with security
        # In production, use a safer math evaluator
        result = eval(expression, {"__builtins__": None}, {
            "sqrt": math.sqrt,
            "sin": math.sin,
            "cos": math.cos,
            "tan": math.tan,
            "pi": math.pi,
            "e": math.e,
            "log": math.log,
            "exp": math.exp,
            "abs": abs,
            "pow": pow,
        })
        return str(result)
    except Exception as e:
        return f"Error calculating expression: {e}"