
PRICE_PER_MILLION = {
    "llama-3.3-70b-versatile": {"input": 0.59, "output": 0.79},
}
DEFAULT_PRICE = {"input": 0.59, "output": 0.79}


def extract_usage(raw_message) -> dict:
    """
    Pulls token counts from an AIMessage. Falls back to response_metadata
    since usage_metadata has been reported empty in some with_structured_output
    + include_raw setups — worth verifying it actually populates here, not assuming.
    """
    usage = getattr(raw_message, "usage_metadata", None) or {}
    if usage.get("input_tokens") or usage.get("output_tokens"):
        return {"input_tokens": usage.get("input_tokens", 0), "output_tokens": usage.get("output_tokens", 0)}

    token_usage = (raw_message.response_metadata or {}).get("token_usage", {})
    return {
        "input_tokens": token_usage.get("prompt_tokens", 0),
        "output_tokens": token_usage.get("completion_tokens", 0),
    }


def estimate_cost(model_name: str, input_tokens: int, output_tokens: int) -> float:
    prices = PRICE_PER_MILLION.get(model_name, DEFAULT_PRICE)
    return (input_tokens * prices["input"] + output_tokens * prices["output"]) / 1_000_000