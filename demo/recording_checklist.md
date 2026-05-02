# Darwin Demo Recording Checklist

Use this checklist before recording the 60-75 second demo video.

## Before Recording

- Close unrelated browser tabs and terminal windows.
- Hide secrets, connection strings, API keys, and personal notifications.
- Pull the latest `main` or the intended demo branch.
- Confirm dependencies are installed:

```bash
python3 -m pip install -e .
```

- Confirm the terminal fallback works:

```bash
python3 -m darwin.demo.narrate --preview --once
python3 -m darwin.demo.scripted_run --seed 42 --generations 5 --delay 0.5 --plain
```

## Preferred Recording Flow

1. Start with the dashboard or terminal demo already visible.
2. Say the first two lines from `demo/live_anchor.md`.
3. Run or replay the deterministic terminal demo:

```bash
python3 -m darwin.demo.scripted_run --seed 42 --generations 5 --delay 0.5 --plain
```

4. Point out the population, fitness trend, champion genome, query tournament, and winning answer.
5. Close with the final line from `demo/live_anchor.md`.

## If The Web UI Is Ready

- Open the web UI first.
- Show the three-panel view: population, fitness curve, and champion or lineage.
- Use the terminal demo as backup if the UI stalls.

## If The API Is Ready

Run the live terminal mode against the API:

```bash
DARWIN_API_URL=http://localhost:3000 python3 -m darwin.demo.narrate --live --once
```

## If Atlas Is Ready

Run the live terminal mode against MongoDB:

```bash
MONGODB_URI="mongodb+srv://..." python3 -m darwin.demo.narrate --live --once
```

Do not show the URI on screen during recording.

## Backup Plan

If live services fail, use:

```bash
python3 -m darwin.demo.scripted_run --seed 42 --generations 5 --delay 0.5 --plain
```

Then use the fallback explanation in `demo/backup_query.md`.

## Success Criteria

- The viewer understands that Darwin evolves RAG strategies.
- The recording shows generation progress, fitness improvement, and a champion genome.
- The demo makes clear that answer quality is scored and fed back into evolution.
- The video does not expose secrets or local-only setup details.
