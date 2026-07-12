# Technical Challenges & Solutions

## Challenge 1: Timestamp alignment between faster-whisper and pyannote diarization
### The Problem
We needed to produce diarized transcript segments where each transcript segment (from faster-whisper) is assigned to a speaker label produced by pyannote.audio. In practice, faster-whisper emits segments with start/end timestamps based on its internal chunking and VAD heuristics, while pyannote produces speaker turns with its own time base and sometimes overlapping segments. The raw outputs therefore frequently disagreed: whisper segments could cross speaker turn boundaries, pyannote labels could overlap, and slight clock drift or differing frame quantization produced fractional-second mismatches.

### Why It Was Hard
Aligning timestamps reliably is tricky because the two libraries are not synchronized: faster-whisper's segment boundaries are influenced by language model decoding and silence heuristics, whereas pyannote operates on continuous audio feature frames and may produce overlapping labels. Naive midpoint assignment (pick speaker at segment midpoint) fails for long segments that span speaker changes or when pyannote outputs highly fragmented turns. Overlap resolution, boundary smoothing, and robustness to missing diarization (fallback) are required to avoid misattributing speech and producing noisy action items or summaries.

### The Solution
We implemented a pragmatic, robust assignment strategy in SpeakerDiarizer.assign_speakers_to_transcript:
- For each whisper TranscriptSegment, compute the midpoint time and score each pyannote SpeakerSegment by temporal overlap length.
- Use the segment with the maximum overlap as the speaker label. This handles most cases where whisper segments are roughly aligned to speaker turns.
- To handle partial overlaps and very long whisper segments, we intentionally keep whisper segment granularity by not forcibly splitting segments unless diarization indicates a large internal boundary; this preserves transcript fidelity.
- Add a graceful fallback: if pyannote fails to load (missing HF token or runtime error), return a single-speaker segment covering the whole file to keep the pipeline functional.
- Log and monitor statistics (number of segments with low overlap) so the UI can warn users about potential alignment issues.

This approach trades perfect alignment for robustness and simplicity: it works well in realistic meetings where speaker turns are reasonably separated and allows downstream components (action extraction, summarizer) to operate without complex re-segmentation.

### What I Learned
Precise multimodal alignment often requires joint inference or forced-alignment tools. When integrating black-box systems, pragmatism (overlap heuristics + fallbacks) yields the best engineering ROI. Instrumentation (counting low-overlap cases) is crucial — it turns silent failures into actionable diagnostics.


## Challenge 2: Hybrid search fusion without a vector DB (FTS5 + dense embeddings)
### The Problem
Users expect both exact keyword matches and semantic fuzzy matches when searching meetings: keywords find literal references while semantic search surfaces paraphrases and related discussion. We needed to combine SQLite FTS5 results (fast, local) with dense vector similarity results produced by sentence-transformers — but the project intentionally avoided an external vector database dependency.

### Why It Was Hard
Merging two ranking systems with very different score distributions and semantics is non-trivial. FTS5 returns rank/score values tied to token matches, while cosine similarities from embeddings are in [-1,1] and depend on embedding normalization and model choice. Naively mixing raw scores biases toward one modality. Additionally, storing and searching many vectors in SQLite as JSON blobs is efficient for small datasets but requires careful memory and computation choices when scoring at query time.

### The Solution
We implemented a Reciprocal Rank Fusion (RRF) style combiner in MeetingSearchEngine.search_hybrid:
- Execute an FTS5 query to get top N keyword results and independently compute the top N semantic matches by loading stored embeddings (JSON array) and calculating cosine similarity in Python using TextEmbedder.cosine_similarity.
- Build a consistent key per candidate (meeting_id + snippet prefix) and accumulate RRF scores: score += 1 / (k + rank + 1), where k is a tunable constant (we used k=60). RRF normalizes across modalities by using ranks rather than raw scores.
- Store embeddings in a transcript_embeddings table as serialized JSON arrays to avoid pulling in an extra service. For moderate-sized corpora this in-process scoring is performant; for larger corpora we note the migration path to FAISS or an external vector DB.
- When returning results, present the fused ranking with provenance (which results came from FTS vs semantic) so the frontend can surface why an item was returned.

This hybrid approach delivered intuitive results without introducing an external vector DB and kept the system simple and auditable.

### What I Learned
Rank-based fusion (RRF) is an effective, implementation-light method to combine heterogeneous search signals. Persisting vectors as JSON in SQLite is a practical compromise for local-first tools; the design should plan for horizontal migration when corpus size grows.


## Challenge 3: Streaming pipeline progress (SSE) from background FastAPI tasks without blocking
### The Problem
Long-running audio processing (transcription, diarization, LLM calls) must not block API responsiveness. The frontend needs real-time processing updates (progress, status messages) for user feedback while the backend runs work in background tasks. Implementing Server-Sent Events (SSE) that stream messages from background workers presented concurrency challenges: the processing tasks run in separate asyncio tasks/threads, and the SSE endpoint must observe progress without polling the DB or blocking the event loop.

### Why It Was Hard
Naive approaches — e.g., blocking threads that write to global lists, or polling the database every second from the SSE generator — either blocked the event loop, consumed CPU, or introduced race conditions. Using websockets complicates the frontend and introduces lifecycle management. We needed a simple, reliable pattern that allowed background tasks to emit messages and the SSE generator to stream them efficiently to connected clients.

### The Solution
We implemented a lightweight in-memory progress queue and an SSE generator pattern:
- _progress is a dict mapping meeting_id to a list of messages. Background processing code calls _emit(meeting_id, message) to append messages.
- The SSE endpoint (meeting_status_stream) starts an async generator that keeps track of a local cursor (last_idx). In the loop it yields any new messages and then awaits asyncio.sleep(1) — non-blocking — to yield control to the event loop.
- Background processing runs as asyncio.create_task(...) so it executes concurrently without blocking the main FastAPI worker. The generator exits cleanly when a sentinel message (Processing complete) is observed.
- We avoided blocking I/O in the generator and kept message writes atomic (list append), which is safe for CPython due to the GIL for simple operations. For heavier concurrency needs, we documented the migration to asyncio.Queue or Redis pub/sub.

This pattern provides timely progress messages, keeps the API responsive, and is easy to reason about.

### What I Learned
Small, well-documented concurrency primitives (in-memory queues + SSE) are powerful for product-grade UX. Design for eventual scalability: start with simplicity but document and modularize the code paths where a future switch to Redis or an async message bus would be needed.
