
EXPANSION_PROMPT = (
    "You rewrite an informal insurance claim description into formal, "
    "policy-style search terms to improve document retrieval.\n\n"
    "Given a claim description, output a single concise line of formal "
    "insurance terminology covering the coverage concepts likely relevant to it. "
    "Do NOT decide whether the claim is covered. Do NOT invent policy rules. "
    "Only translate the situation into the vocabulary a policy document would use.\n\n"
    "Examples:\n"
    "Claim: my cat scratched me and it got infected, need to see a doctor\n"
    "Terms: medical treatment for animal-inflicted injury, infection, "
    "emergency or urgent care coverage, physician visit reimbursement\n\n"
    "Claim: my basement flooded after heavy rain\n"
    "Terms: water damage to dwelling, flood damage, groundwater intrusion, "
    "home structural coverage, flood exclusion\n\n"
    "Claim: {description}\n"
    "Terms:"
)


def expand_query(description: str, llm=None) -> str:
    if not description or not description.strip():
        return description

    if llm is None:
        from app.llm import get_llm
        llm = get_llm()

    try:
        resp = llm.invoke(EXPANSION_PROMPT.format(description=description))
        expanded = resp.content.strip() if hasattr(resp, "content") else str(resp).strip()
        if not expanded:
            return description
        return f"{description} {expanded}"
    except Exception:
        return description