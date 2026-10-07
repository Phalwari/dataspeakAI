import re
from fastapi import HTTPException, status
import logging

logger = logging.getLogger(__name__)

class SecurityService:
    """
    A service that intercepts and sanitizes natural language queries before they 
    reach the LLM engine, protecting against prompt injection, XSS, and SQL injection.
    """

    MAX_QUERY_LENGTH = 10000

    # Patterns commonly used in jailbreak attempts or prompt injections
    PROMPT_INJECTION_PATTERNS = [
        r"(?i)\bignore\s+(all\s+)?(previous\s+)?instructions\b",
        r"(?i)\byou\s+are\s+(now\s+)?(a\s+)?(DAN|developer|admin|root)\b",
        r"(?i)\bsystem\s+prompt\b",
        r"(?i)\bbypass\s+rules\b",
        r"(?i)\bforget\s+(about\s+)?your\s+instructions\b"
    ]

    # Explicit SQL commands that should almost never be in a natural language query
    # Used as a heuristic to stop basic SQL injection disguised as natural language.
    MALICIOUS_SQL_PATTERNS = [
        r"(?i)\bDROP\s+TABLE\b",
        r"(?i)\bDELETE\s+FROM\b",
        r"(?i)\bTRUNCATE\s+TABLE\b",
        r"(?i)\bALTER\s+TABLE\b",
        r"(?i)\bGRANT\s+ALL\b",
        r"(?i)\bEXEC(\s|\()",
        r"(?i)\bUNION\s+ALL\s+SELECT\b"
    ]

    # Basic XSS tag catching
    HTML_SCRIPT_PATTERNS = [
        r"(?i)<\s*script.*?>",
        r"(?i)<\s*iframe.*?>",
        r"(?i)javascript:"
    ]

    @classmethod
    def sanitize_and_validate(cls, query: str) -> str:
        """
        Validates the incoming query string. Raises HTTPException if malicious intent is detected.
        Returns a cleanly stripped query if safe.
        """
        if not query:
            return ""

        # 1. Length validation to prevent token exhaustion
        if len(query) > cls.MAX_QUERY_LENGTH:
            logger.warning(f"Security Alert: Query exceeded max length ({len(query)} chars).")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Query is too long. Maximum allowed length is {cls.MAX_QUERY_LENGTH} characters."
            )

        # 2. Check for Prompt Injection / Jailbreaks
        for pattern in cls.PROMPT_INJECTION_PATTERNS:
            if re.search(pattern, query):
                logger.warning("Security Alert: Prompt Injection detected.")
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Your query contains restricted phrases and cannot be processed."
                )

        # 3. Check for SQL Injection in NL
        for pattern in cls.MALICIOUS_SQL_PATTERNS:
            if re.search(pattern, query):
                logger.warning("Security Alert: Malicious SQL keywords detected in natural language.")
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Query contains restricted database manipulation keywords."
                )

        # 4. Check for XSS / HTML scripts
        for pattern in cls.HTML_SCRIPT_PATTERNS:
            if re.search(pattern, query):
                logger.warning("Security Alert: HTML/Script tags detected.")
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Query contains invalid HTML or script tags."
                )

        # Basic text stripping
        return query.strip()
