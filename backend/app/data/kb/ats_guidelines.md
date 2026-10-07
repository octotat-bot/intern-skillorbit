<!-- chunk id=ats-001 | title=How ATS read a resume | topic=ats | roles=all | sections=ats | source=self-authored -->
An applicant tracking system extracts the text from your file, splits it into sections by recognizing headings, and indexes keywords so recruiters can search and filter. If text cannot be extracted, or comes out in the wrong order, your resume may be filtered out regardless of its quality. Optimize for clean extraction first, keywords second.

<!-- chunk id=ats-002 | title=Single-column layouts | topic=layout | roles=all | sections=ats | source=self-authored -->
Use a single-column layout. Two-column templates look modern, but many parsers read straight across the page line by line, merging the left and right columns into scrambled sentences. If you like a sidebar look, keep the sidebar content (skills, contact) as normal sections in a single column instead.

<!-- chunk id=ats-003 | title=Tables, text boxes and graphics | topic=layout | roles=all | sections=ats | source=self-authored -->
Avoid tables, text boxes, icons, skill bars and charts. Parsers may skip text inside them or read cells out of order, and graphic skill ratings ("Python: 4/5 stars") carry no machine-readable information. Put contact details in the main body, not in the page header or footer, which some systems ignore.

<!-- chunk id=ats-004 | title=File type and scanned resumes | topic=file-format | roles=all | sections=ats | source=self-authored -->
Submit a text-based PDF or a DOCX exported directly from Word, Google Docs or LaTeX. A scanned page or an image exported as PDF contains no selectable text, so an ATS sees an empty document. Test your file by selecting all text in a PDF viewer and pasting it into a plain text editor: what you see is roughly what the ATS sees.

<!-- chunk id=ats-005 | title=Standard section headings | topic=headings | roles=all | sections=ats,structure | source=self-authored -->
Use conventional headings: Summary, Education, Skills, Experience, Projects, Certifications, Achievements. Creative headings such as "My Toolbox" or "Where I've Been" may not be recognized, so their contents end up in the wrong section or are ignored.

<!-- chunk id=ats-006 | title=Keywords and exact terms | topic=keywords | roles=all | sections=ats,skills | source=self-authored -->
Recruiters search ATS databases with the exact terms from the job description. Include both the full term and the common abbreviation once where natural, for example "Machine Learning (ML)" or "Continuous Integration (CI/CD)". Place important keywords in both the skills section and in bullets that show their use. Never paste hidden keywords in white text; modern systems and recruiters detect it.

<!-- chunk id=ats-007 | title=Fonts and special characters | topic=formatting | roles=all | sections=ats,quality | source=self-authored -->
Use common fonts (Calibri, Arial, Helvetica, Georgia) at 10 to 12 points. Decorative fonts, ligatures and unusual Unicode symbols can extract as garbage characters. Simple round bullets and hyphens are safe. Spell out dates and avoid putting important text in all-caps decorative lettering.

<!-- chunk id=ats-008 | title=What an ATS score means | topic=ats | roles=all | sections=ats | source=self-authored -->
Keyword match scores from resume tools, including this one, are heuristics: they estimate how well your text covers a role's common requirements and how cleanly it parses. Real employers configure their systems differently and humans make the final decision. Use the score to find gaps, not as a guarantee of passing any specific screen.
