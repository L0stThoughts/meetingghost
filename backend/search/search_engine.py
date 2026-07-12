"""Hybrid search engine combining SQLite FTS5 and semantic vector search."""
import json
import logging
from dataclasses import dataclass
from typing import List, Optional

from sqlalchemy import text
from sqlalchemy.orm import Session

from backend.audio.diarizer import DiarizedSegment
from backend.intelligence.embedder import TextEmbedder

logger = logging.getLogger(__name__)


@dataclass
class SearchResult:
    meeting_id: int
    snippet: str
    score: float
    speaker: Optional[str] = None
    timestamp: Optional[float] = None


class MeetingSearchEngine:
    def __init__(self, db_session: Session, embedder: TextEmbedder) -> None:
        self.db = db_session
        self.embedder = embedder

    def index_transcript(self, meeting_id: int, segments: List[DiarizedSegment]) -> None:
        if not segments:
            return

        texts = [s.text for s in segments]
        embeddings = self.embedder.embed_batch(texts)

        for i, seg in enumerate(segments):
            # Insert into transcript_embeddings
            self.db.execute(text(
                "INSERT INTO transcript_embeddings "
                "(meeting_id, segment_index, speaker, start_time, end_time, text, embedding) "
                "VALUES (:mid, :idx, :spk, :st, :et, :txt, :emb)"
            ), {
                "mid": meeting_id, "idx": i, "spk": seg.speaker,
                "st": seg.start, "et": seg.end, "txt": seg.text,
                "emb": json.dumps(embeddings[i]),
            })

            # Insert into FTS5
            self.db.execute(text(
                "INSERT INTO transcripts_fts (meeting_id, speaker, text) "
                "VALUES (:mid, :spk, :txt)"
            ), {"mid": meeting_id, "spk": seg.speaker, "txt": seg.text})

        self.db.commit()
        logger.info("Indexed %d segments for meeting %d", len(segments), meeting_id)

    def search_fts(self, query: str, limit: int = 10) -> List[SearchResult]:
        try:
            rows = self.db.execute(text(
                "SELECT meeting_id, speaker, text, rank "
                "FROM transcripts_fts WHERE transcripts_fts MATCH :q "
                "ORDER BY rank LIMIT :lim"
            ), {"q": query, "lim": limit}).fetchall()

            return [SearchResult(
                meeting_id=int(r[0]), snippet=r[2], score=-float(r[3]),
                speaker=r[1], timestamp=None,
            ) for r in rows]
        except Exception as exc:
            logger.error("FTS search failed: %s", exc)
            return []

    def search_semantic(self, query: str, limit: int = 10) -> List[SearchResult]:
        try:
            query_emb = self.embedder.embed(query)
            rows = self.db.execute(text(
                "SELECT id, meeting_id, speaker, start_time, text, embedding "
                "FROM transcript_embeddings"
            )).fetchall()

            scored: List[SearchResult] = []
            for r in rows:
                emb = json.loads(r[5])
                sim = self.embedder.cosine_similarity(query_emb, emb)
                scored.append(SearchResult(
                    meeting_id=int(r[1]), snippet=r[4], score=sim,
                    speaker=r[2], timestamp=float(r[3]) if r[3] else None,
                ))

            scored.sort(key=lambda x: x.score, reverse=True)
            return scored[:limit]
        except Exception as exc:
            logger.error("Semantic search failed: %s", exc)
            return []

    def search_hybrid(self, query: str, limit: int = 10) -> List[SearchResult]:
        """Reciprocal rank fusion of FTS + semantic results."""
        fts_results = self.search_fts(query, limit=limit * 2)
        sem_results = self.search_semantic(query, limit=limit * 2)

        k = 60  # RRF constant
        scores: dict[str, float] = {}
        result_map: dict[str, SearchResult] = {}

        for rank, r in enumerate(fts_results):
            key = f"{r.meeting_id}:{r.snippet[:50]}"
            scores[key] = scores.get(key, 0) + 1.0 / (k + rank + 1)
            result_map[key] = r

        for rank, r in enumerate(sem_results):
            key = f"{r.meeting_id}:{r.snippet[:50]}"
            scores[key] = scores.get(key, 0) + 1.0 / (k + rank + 1)
            if key not in result_map:
                result_map[key] = r

        sorted_keys = sorted(scores, key=lambda x: scores[x], reverse=True)[:limit]
        return [SearchResult(
            meeting_id=result_map[k_].meeting_id,
            snippet=result_map[k_].snippet,
            score=scores[k_],
            speaker=result_map[k_].speaker,
            timestamp=result_map[k_].timestamp,
        ) for k_ in sorted_keys]
