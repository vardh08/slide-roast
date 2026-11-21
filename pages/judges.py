"""Registry of the three judges, in display order. Add a 4th judge by adding it here."""
from prompts import customer_prompt, investor_prompt, professor_prompt

JUDGES = {
    m.KEY: {
        "key": m.KEY,
        "name": m.NAME,
        "icon": m.ICON,
        "color": m.COLOR,
        "personality": m.PERSONALITY,
        "opening_line": m.OPENING_LINE,
        "system_prompt": m.SYSTEM_PROMPT,
    }
    for m in (investor_prompt, professor_prompt, customer_prompt)
}
