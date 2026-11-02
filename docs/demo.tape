# Renders docs/demo.gif with charmbracelet/vhs (needs vhs, ttyd and ffmpeg on PATH).
# Run from the repo root, with the deps installed in .venv:  vhs docs/demo.tape
# Follows DEMO.md: YAML config -> scrape the bundled 3-page sample site -> clean CSV -> offline tests.
Output docs/demo.gif

Set Shell "bash"
Set FontSize 18
Set Width 1200
Set Height 700
Set Padding 24
Set Theme "Catppuccin Mocha"
Set WindowBar Colorful
Set TypingSpeed 40ms

Hide
Type "VIRTUAL_ENV_DISABLE_PROMPT=1 source .venv/bin/activate"
Enter
Wait@120s
Type "rm -rf out"
Enter
Wait@120s
Type "clear"
Enter
Wait@120s
Show
Sleep 500ms

Type "grep -vE '^\s*#' configs/books.yaml | cat -s"
Sleep 400ms
Enter
Wait@120s
Sleep 4s

Hide
Type "clear"
Enter
Sleep 200ms
Show
Type "python -m scrape_to_sheet configs/books.yaml"
Sleep 400ms
Enter
Wait@120s
Sleep 2.5s

Type "cat out/data.csv"
Sleep 400ms
Enter
Wait@120s
Sleep 3.5s

Type "pytest -q"
Sleep 400ms
Enter
Wait@120s
Sleep 2s

Sleep 1s
