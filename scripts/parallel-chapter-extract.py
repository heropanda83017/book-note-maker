#!/usr/bin/env python3
"""
parallel-chapter-extract.py

Usage:
  python3 scripts/parallel-chapter-extract.py <book_text.txt> <chapter_definitions.json> [max_concurrent=3]

Purpose:
  Parallelize chapter content extraction for large books (200+ pages).
  Distributes chapters across delegate_task subagents (up to max_concurrent=3)
  and merges results into a single structured output.

Input:
  book_text.txt: Full text extracted from PDF
  chapter_definitions.json: JSON array of chapter objects:
    [
      {"id": "ch1", "title": "第1课", "start_line": 157, "end_line": 503, "label": "lesson"},
      {"id": "ch2", "title": "第2课", "start_line": 504, "end_line": 908, "label": "lesson"},
      ...
    ]

Output:
  Per-chapter markdown files in /tmp/book_chapter_extracts/
  Combined report in /tmp/book_all_chapters_combined.md

Notes:
  - max_concurrent_children defaults to 3 in Hermes config.
  - For books with 9+ chapters, split into batches of 3 for sequential parallel rounds.
  - Each subagent task receives text range + extraction instructions.
  - Subagent returns: ## Core Arguments, ## Key Concepts (table), ## Case Studies, ## Quotes
"""

import json
import sys
import os

def build_chapter_prompt(chapter_title, start_line, end_line, text_path):
    """Build the extraction prompt for one chapter."""
    return f"""
Context: Book text is at {text_path}, lines {start_line}-{end_line}.
Read this section and extract structured content for chapter "{chapter_title}":

## Core Arguments (what problem does this chapter solve, what is its main claim)
## Key Concepts (table: concept name, definition, example from book)
## Case Studies (name, background, process, argument role)
## Key Quotes (3-5 most valuable original sentences)

Return structured markdown.
"""

def batch_chapters(chapters, batch_size=3):
    """Split chapters into sequential batches for parallel execution."""
    return [chapters[i:i+batch_size] for i in range(0, len(chapters), batch_size)]

if __name__ == '__main__':
    print("This script is designed to be used within Hermes via delegate_task.")
    print("It provides the batching logic and prompt templates.")
    print()
    print("Usage flow:")
    print("  1. Detect chapters -> get chapter_definitions.json")
    print("  2. Batch into groups of 3 -> build prompts")
    print("  3. Call delegate_task with each batch")
    print("  4. Merge results into final reading notes")
