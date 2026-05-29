# Dialog-Style Chinese Book Chapter Detection

## Problem

Chinese dialog-style books (对话体) and training/workbook-style books (教科书/训练书) commonly use "第X课" / "第X章" as their chapter structure. However, the conversational format causes extensive cross-references in the body text, such as:

- "第3课中提到的'代表性偏差'..."
- "第1课学过的技巧又派上用场了——..."
- "正如第5课将详细解析的因果关系认知..."
- "第2课末尾引用的皮尔士语录..."

These are NOT chapter headers — they are inline references. Standard regex matching (`第\d+课` or `第[一二三四五六七八九十百零]+课`) will capture all of them as false positives, yielding 30-50+ "chapters" when the book only has 9-15.

## Solution: Two-Pass Context-Aware Filtering

### Pass 1: Initial Regex (as standard)

Use the standard multi-pattern matching from `book-note-maker` SKILL.md phase 3.

### Pass 2: False Positive Filtering

Apply two context-based filters:

#### Filter A: Line length

Real chapter titles are short lines — typically standalone headers. Filter candidates to only those where the matched line's stripped content is ≤ 25 characters.

```python
if len(stripped_line) > 25:
    continue  # likely a body-text cross-reference
```

#### Filter B: Previous-line context

Real chapter titles typically appear after a blank line or a page number line:

```python
prev_line = lines[line_no - 1].strip() if line_no > 0 else ''
is_real_chapter = (
    prev_line == '' or                       # blank line
    re.match(r'^\d+$', prev_line) or         # page number only
    len(prev_line) < 5                       # very short (possible page marker)
)
```

#### Filter C: Table of Contents awareness

Many Chinese books include a "本书内容" or "目录" section near the front that lists all chapter titles. Matches within this section should be flagged as TOC references, not actual chapter boundaries. The real chapter content is located after the TOC, deeper in the file.

Signal: if multiple chapter matches appear clustered within a 20-line window near the beginning of the book (first 15% of lines), and none of them have preceding blank/page-number lines in the normal pattern, those are likely TOC entries — skip them for actual chapter boundary detection.

### Full Detection Script

```python
import re

with open('/tmp/book_full_text.txt', 'r', encoding='utf-8') as f:
    text = f.read()
lines = text.split('\n')

# ── Round 1: Standard pattern detection ──
all_candidates = []
for i, line in enumerate(lines):
    stripped = line.strip()
    for pattern, label in [
        (r'第\s*[一二三四五六七八九十百零]+\s*[课章]', 'cn_num'),
        (r'第\s*\d+\s*[课章]', 'cn_digit'),
    ]:
        if re.search(pattern, stripped):
            all_candidates.append((stripped, i, label))

# ── Round 2: Context-aware filtering ──
real_chapters = []
for title, line_no, label in all_candidates:
    # Length filter: chapter titles are short
    if len(title) > 25:
        continue
    # Context filter: previous line is blank, page number, or very short
    prev = lines[line_no - 1].strip() if line_no > 0 else ''
    if prev == '' or re.match(r'^\d+$', prev) or len(prev) < 5:
        real_chapters.append((title, line_no, label))

# ── Round 3: Deduplication (5-line proximity) ──
seen_buckets = set()
deduped = []
for title, line_no, label in real_chapters:
    bucket = line_no // 5
    if bucket not in seen_buckets:
        seen_buckets.add(bucket)
        deduped.append((title, line_no, label))

deduped.sort(key=lambda x: x[1])
```

### Verification

- Expected: 10-15 genuine chapters detected (matching actual book structure)
- If > 30: filter was too loose — tighten the line-length threshold to 20
- If < 3: book may use non-standard chapter markers — fall back to 4+ consecutive newlines

## Known Book Types Where This Applies

| Book type | Example | Chapter marker |
|-----------|---------|----------------|
| Chinese dialog-style training | 《慢思术》植原亮 | "第X课" + subtitle |
| Japanese-origin self-help (Chinese translation) | Many | "第X课" or "Lesson X" |
| Chinese textbook-style | Various | "第X章" or "第X讲" |
| Chinese workbook/interactive | Various | "第X天" or "第X回" |
