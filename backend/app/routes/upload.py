"""Resume resource routes.

POST /api/resumes        upload and parse a resume (multipart field ``file``)
GET  /api/resumes/<id>   parsed text, sections, contact and parse quality
"""

from __future__ import annotations

from flask import Blueprint, jsonify, request
from werkzeug.datastructures import FileStorage
from werkzeug.utils import secure_filename

from app import config
from app.db import get_resume, insert_resume
from app.errors import ApiError
from app.services.parser import ParseError, detected_section_names, parse_resume

bp = Blueprint("upload", __name__, url_prefix="/api")

_DOCX_SIGNATURE = b"PK\x03\x04"   # DOCX is a ZIP container
_PDF_SIGNATURE = b"%PDF"


@bp.post("/resumes")
def upload_resume():
    """Validate, parse and store an uploaded resume.

    Returns:
        201 with ``{resume_id, filename, parse_quality, sections_detected}``.
    """
    upload = _require_file()
    file_type = _file_type(upload.filename or "")
    data = _read_validated(upload, file_type)
    try:
        parsed = parse_resume(data, file_type).to_dict()
    except ParseError as exc:
        raise ApiError(422, "unreadable_file", str(exc)) from exc

    filename = secure_filename(upload.filename or "") or f"resume.{file_type}"
    resume_id = insert_resume(filename, file_type, parsed)
    return jsonify({
        "resume_id": resume_id,
        "filename": filename,
        "parse_quality": parsed["parse_quality"],
        "sections_detected": detected_section_names(parsed["sections"]),
    }), 201


@bp.get("/resumes/<int:resume_id>")
def get_resume_detail(resume_id: int):
    """Return the stored parse result for one resume."""
    record = get_resume(resume_id)
    if record is None:
        raise ApiError(404, "resume_not_found", f"No resume with id {resume_id}.")
    return jsonify({
        "resume_id": record["id"],
        "filename": record["filename"],
        "file_type": record["file_type"],
        "created_at": record["created_at"],
        "text": record["clean_text"],
        "sections": record["sections"],
        "sections_detected": detected_section_names(record["sections"]),
        "contact": record["contact"],
        "parse_quality": record["parse_quality"],
        "stats": record["stats"],
    })


def _require_file() -> FileStorage:
    """Return the uploaded file or raise 400."""
    upload = request.files.get("file")
    if upload is None:
        raise ApiError(400, "missing_file", "Send the resume as multipart form field 'file'.")
    if not upload.filename:
        raise ApiError(400, "missing_file", "No file was selected.")
    return upload


def _file_type(filename: str) -> str:
    """Return the lowercase extension if allowed, else raise 415."""
    extension = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    if extension not in config.ALLOWED_EXTENSIONS:
        raise ApiError(415, "unsupported_file_type", "Only PDF and DOCX files are supported.")
    return extension


def _read_validated(upload: FileStorage, file_type: str) -> bytes:
    """Read the file and check it is non-empty, within size, and really that type."""
    data = upload.read()
    if not data:
        raise ApiError(400, "empty_file", "The uploaded file is empty.")
    if len(data) > config.MAX_FILE_SIZE_BYTES:
        limit_mb = config.MAX_FILE_SIZE_BYTES // (1024 * 1024)
        raise ApiError(413, "file_too_large", f"Files must be {limit_mb} MB or smaller.")
    if not _signature_matches(data, file_type):
        raise ApiError(
            415, "content_mismatch",
            f"The file content is not a valid {file_type.upper()} despite its extension.",
        )
    return data


def _signature_matches(data: bytes, file_type: str) -> bool:
    """Check the file starts with the magic bytes of its claimed type."""
    if file_type == "pdf":
        return _PDF_SIGNATURE in data[: config.PDF_SIGNATURE_SEARCH_BYTES]
    return data.startswith(_DOCX_SIGNATURE)
