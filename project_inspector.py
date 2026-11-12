from pathlib import Path

lines = Path("app.py").read_text(encoding="utf-8").splitlines()

keywords = [
    "def _generate_document_with_ai",
    "def _gemini_text",
    "class APIError"
]

for keyword in keywords:
    for i, line in enumerate(lines):
        if keyword in line:
            print("\n" + "=" * 65)
            print(f"FUNCTION: {keyword}")
            print("=" * 65)

            start = i
            end = min(len(lines), i + 65)

            for j in range(start, end):
                print(f"{j+1}: {lines[j]}")
            break