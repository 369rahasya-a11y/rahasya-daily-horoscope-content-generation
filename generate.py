The real fix

Stop asking the model to write JSON.

Ask it to write structured text.

Example:

MOOD: Ambitious
<content>

===END===

MOOD: Adventurous
<content>

===END===

Then your Python builds the JSON.

Better architecture

Prompt:

Generate all 15 moods.

FORMAT EXACTLY:

### Ambitious
content

### Adventurous
content

### Creative
content

...

No JSON.
No markdown code blocks.

Then parse:

import re

sections = re.split(r"### ", text)

horoscopes = []

for section in sections:
    if not section.strip():
        continue

    lines = section.split("\n", 1)

    mood = lines[0].strip()
    content = lines[1].strip()

    horoscopes.append({
        "mood": mood,
        "content": content
    })

parsed = {
    "date": today,
    "sign": sign,
    "horoscopes": horoscopes
}

Now the AI can never break your JSON because Python creates the JSON, not the AI.
