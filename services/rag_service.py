import re
import logging
from typing import List, Dict, Any


# Common English stop words to ignore during search
STOP_WORDS = {
    "a", "an", "and", "are", "as", "at", "be", "been", "by", "for", "from",
    "has", "have", "had", "he", "her", "hers", "him", "his", "how", "i",
    "if", "in", "into", "is", "it", "its", "me", "my", "of", "on", "or",
    "our", "she", "the", "their", "them", "then", "there", "these", "they",
    "this", "to", "was", "we", "were", "what", "when", "where", "which",
    "who", "why", "will", "with", "would", "you", "your", "be", "been",
    "being", "do", "does", "did", "can", "could", "should", "would", "may",
    "might", "must", "shall", "will", "about", "above", "after", "again",
    "against", "all", "am", "any", "because", "before", "below", "between",
    "both", "but", "by", "can", "did", "do", "does", "doing", "down",
    "during", "each", "few", "for", "further", "had", "has", "have",
    "having", "he", "her", "here", "hers", "herself", "him", "himself",
    "his", "how", "i", "if", "in", "into", "is", "it", "its", "itself",
    "just", "me", "more", "most", "my", "myself", "no", "nor", "not",
    "now", "of", "off", "on", "once", "only", "or", "other", "ought",
    "our", "ours", "ourselves", "out", "over", "own", "re", "same", "she",
    "should", "so", "some", "such", "than", "that", "the", "their",
    "theirs", "them", "themselves", "then", "there", "these", "they",
    "this", "those", "through", "to", "too", "under", "until", "up",
    "very", "was", "we", "were", "what", "when", "where", "which", "while",
    "who", "whom", "why", "will", "with", "you", "your", "yours", "yourself",
    "yourselves"
}


def chunk_text(text: str, max_chunk_size: int = 500, overlap: int = 50) -> List[str]:
    """
    Split text into overlapping chunks of reasonable size.

    Args:
        text: The full text to chunk
        max_chunk_size: Maximum characters per chunk
        overlap: Number of characters to overlap between chunks

    Returns:
        List of text chunks
    """
    if not text or not text.strip():
        return []

    # Clean up the text
    text = text.strip()
    text = re.sub(r'\s+', ' ', text)  # Normalize whitespace

    # If text is short enough, return as single chunk
    if len(text) <= max_chunk_size:
        return [text]

    chunks = []
    start = 0

    while start < len(text):
        end = start + max_chunk_size

        # If we're not at the end, try to break at a sentence boundary
        if end < len(text):
            # Look for sentence ending within the last 100 chars of the chunk
            search_start = max(start, end - 100)
            sentence_end = -1
            for i in range(end, search_start, -1):
                if text[i] in '.!?':
                    sentence_end = i + 1
                    break

            if sentence_end > start:
                end = sentence_end

        chunk = text[start:end].strip()
        if chunk:
            chunks.append(chunk)

        # Move start position, accounting for overlap
        start = end - overlap
        if start <= 0:
            start = end

    return chunks


def chunk_lecture(lecture_id: int, text: str) -> List[Dict[str, Any]]:
    """
    Chunk a lecture's text and return chunk data ready for storage.

    Args:
        lecture_id: ID of the lecture
        text: Full lecture text

    Returns:
        List of dicts with chunk_index and chunk_text
    """
    chunks = chunk_text(text)
    return [
        {"lecture_id": lecture_id, "chunk_index": i, "chunk_text": chunk}
        for i, chunk in enumerate(chunks)
    ]


def normalize_query(query: str) -> List[str]:
    """
    Normalize query by lowercasing, removing punctuation, and filtering stop words.
    
    Args:
        query: Raw query string
        
    Returns:
        List of meaningful query words (lowercase, no stop words, no punctuation)
    """
    if not query or not query.strip():
        return []
    
    # Lowercase and replace punctuation with spaces
    text = query.lower()
    text = re.sub(r'[^\w\s]', ' ', text)
    text = re.sub(r'\s+', ' ', text).strip()
    
    # Split into words and filter stop words
    words = text.split()
    meaningful_words = [w for w in words if w not in STOP_WORDS and len(w) > 1]
    
    return meaningful_words


def search_chunks(query: str, chunks: List[Dict[str, Any]], top_k: int = 3) -> List[Dict[str, Any]]:
    """
    Simple text-based search for relevant chunks with improved scoring.
    
    Args:
        query: User's search query
        chunks: List of chunk dicts with 'chunk_text' key
        top_k: Maximum number of chunks to return
        
    Returns:
        List of most relevant chunks with score
    """
    if not query or not query.strip():
        return []
    
    # Normalize query - extract meaningful words only
    query_words = normalize_query(query)
    
    if not query_words:
        return []
    
    scored_chunks = []
    
    for chunk in chunks:
        chunk_text = chunk.get("chunk_text", "").lower()
        if not chunk_text:
            continue
        
        # Normalize chunk text for matching
        chunk_words = set(re.findall(r'\b\w+\b', chunk_text.lower()))
        
        # Count distinct query words found in chunk
        matches = len(set(query_words) & chunk_words)
        
        if matches == 0:
            continue
            
        # Score: prioritize chunks with more distinct query terms
        # Base score from distinct matches, small boost from frequency
        freq_score = sum(chunk_text.count(word) for word in query_words)
        # Weight distinct matches heavily, frequency lightly
        total_score = matches * 20 + min(freq_score, 10)
        
        scored_chunks.append({
            **chunk,
            "score": total_score
        })
    
    # Sort by score descending
    scored_chunks.sort(key=lambda x: x["score"], reverse=True)
    
    return scored_chunks[:top_k]


def get_chunk_context(chunks: List[Dict[str, Any]], max_chars: int = 2000) -> str:
    """
    Combine chunks into a context string for LLM.
    
    Args:
        chunks: List of chunk dicts
        max_chars: Maximum total characters
        
    Returns:
        Combined context string
    """
    context_parts = []
    total_chars = 0
    
    for chunk in chunks:
        chunk_text = chunk.get("chunk_text", "")
        if total_chars + len(chunk_text) > max_chars:
            break
        context_parts.append(chunk_text)
        total_chars += len(chunk_text)
    
    return "\n\n".join(context_parts)


def retrieve_context(
    lecture_id: int,
    user_id: int,
    task_type: str,
    top_k: int = 5,
    max_context_chars: int = 3000
) -> Dict[str, Any]:
    """
    Retrieve relevant context for a lecture and task.
    
    Args:
        lecture_id: ID of the lecture
        user_id: ID of the user (for ownership verification)
        task_type: One of "summary", "notes", "questions", "mcqs"
        top_k: Maximum chunks to retrieve
        max_context_chars: Maximum context characters
        
    Returns:
        Dict with context, chunks_used, fallback_used, and diagnostic info
    """
    from database import get_lecture_chunks, get_lecture_by_id
    
    # Task-specific search terms for better relevance
    task_search_terms = {
        "summary": "summary overview key concepts main ideas",
        "notes": "definitions concepts examples important details",
        "questions": "concepts definitions how why what explain",
        "mcqs": "definitions concepts facts rules syntax examples"
    }
    
    search_terms = task_search_terms.get(task_type, task_type)
    
    # Get lecture and verify ownership
    lecture = get_lecture_by_id(lecture_id, user_id)
    if not lecture:
        return {
            "context": "",
            "chunks_used": 0,
            "fallback_used": False,
            "error": "Lecture not found"
        }
    
    # Get all chunks for this lecture
    chunks = get_lecture_chunks(lecture_id, user_id)
    if not chunks:
        return {
            "context": "",
            "chunks_used": 0,
            "fallback_used": False,
            "error": "No chunks available for lecture"
        }
    
    # Build search query
    search_query = f"{lecture['title']} {search_terms}"
    
    # Retrieve relevant chunks
    results = search_chunks(search_query, chunks, top_k=top_k)
    fallback_used = False
    
    if not results:
        # Fallback: use first chunks if no keyword matches
        # but limit to top_k chunks and log fallback
        logging.info(
            f"RAG fallback used: lecture_id={lecture_id}, task_type={task_type}, "
            f"available_chunks={len(chunks)}, retrieved=0"
        )
        results = chunks[:top_k]
        fallback_used = True
    else:
        logging.info(
            f"RAG retrieval: lecture_id={lecture_id}, task_type={task_type}, "
            f"available_chunks={len(chunks)}, retrieved={len(results)}, "
            f"fallback_used={fallback_used}"
        )
    
    context = get_chunk_context(results, max_chars=max_context_chars)
    
    return {
        "context": context,
        "chunks_used": len(results),
        "fallback_used": fallback_used,
        "lecture_id": lecture_id,
        "lecture_title": lecture["title"],
        "task_type": task_type,
        "available_chunks": len(chunks),
        "search_query": search_query
    }