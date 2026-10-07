# Knowledge base (RAG)

Every chunk in this folder is **self-authored** for this project. Role
snippets are synthesized from requirements that commonly appear in public
entry-level job postings; none is copied from a specific posting or source.

Chunk format (one HTML comment header per chunk, followed by its text):

```
<!-- chunk id=bp-001 | title=... | topic=... | roles=all | sections=contact,quality | source=self-authored -->
Chunk text...
```

- `roles`: `all` or a comma list of role ids from roles.json.
- `sections`: resume areas the chunk helps with (contact, structure, skills,
  projects, experience, education, quality, ats). Used to boost retrieval for
  weak areas.
- `source`: provenance. All chunks here are `self-authored`.

After editing, rebuild the shipped vector index:

```bash
cd backend && ./venv/bin/python -m app.services.rag build
```
