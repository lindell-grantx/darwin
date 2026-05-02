# Darwin Demo Assets

This folder contains the DAR-13 demo recording materials.

These files are not application code. They are coordination assets for recording, rehearsing, and safely presenting the Darwin demo.

## Files

### `voiceover.md`

Use this for the 60-75 second recorded demo video.

Purpose:

- Gives the narrator a complete voiceover script.
- Explains Darwin's core story: genomes, retrieval strategies, fitness, and evolution.
- Keeps the recorded video concise and consistent.

Use this when:

- Recording the final demo video.
- Practicing timing before recording.
- Explaining the project to someone who has not followed the implementation details.

### `live_anchor.md`

Use this for the short live presentation before, during, or after the video.

Purpose:

- Provides a 15-30 second live talk track.
- Helps the presenter explain what the audience is seeing.
- Includes a very short fallback version if time is tight.

Use this when:

- Introducing the live demo.
- Explaining the terminal or UI output in real time.
- Closing the presentation with the main takeaway.

### `backup_query.md`

Use this if live services fail.

Purpose:

- Provides a pre-staged query and expected answer.
- Gives backup retrieved chunks and expected facts.
- Lets the presenter explain the full Darwin loop even if WiFi, Atlas, the API, or the UI is unavailable.

Use this when:

- The live API is down.
- MongoDB Atlas is unreachable.
- The UI is not ready.
- The presenter needs a deterministic fallback story.

### `recording_checklist.md`

Use this before recording or rehearsing.

Purpose:

- Lists setup checks before screen recording.
- Documents the preferred shot flow.
- Includes terminal commands for preview, scripted mode, API-backed mode, and MongoDB-backed mode.
- Reminds the team to hide secrets and use fallback commands if needed.

Use this when:

- Preparing OBS, QuickTime, or another recorder.
- Doing a dress rehearsal.
- Checking that the terminal fallback works before presenting.

## Recommended Workflow

1. Read `recording_checklist.md`.
2. Run the terminal fallback command once:

```bash
python3 -m darwin.demo.scripted_run --seed 42 --generations 5 --delay 0.5 --plain
```

3. Practice the short version in `live_anchor.md`.
4. Record the 60-75 second video using `voiceover.md`.
5. Keep `backup_query.md` open during the live demo in case services fail.

## Relationship To DAR-16

DAR-16 added the runnable terminal demo under `src/darwin/demo/`.

DAR-13 uses that demo to produce presentation material:

- `src/darwin/demo/` contains the runnable demo code.
- `demo/` contains scripts, recording guidance, and fallback presentation assets.

## Success Criteria

The demo is ready when:

- The team can explain Darwin in under 30 seconds.
- The recorded video is under 75 seconds.
- The terminal fallback can run without live services.
- The backup query can explain the system if the UI or network fails.
- No secrets are visible in the recording.
