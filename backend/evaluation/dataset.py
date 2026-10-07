"""Evaluation set: 12 synthetic student resumes with hand-assigned score bands.

Bands were assigned from a reviewer's reading of each resume BEFORE running the
scorer on it, using these definitions:

* Excellent (85-100): complete, well-structured, quantified, role-relevant.
* Good (70-84): solid with a few clear gaps (missing links, few metrics...).
* Fair (50-69): usable but with several significant problems.
* Needs work (0-49): incomplete, vague, or unreadable.

All people, companies and numbers are fictional.
"""

from __future__ import annotations

from dataclasses import dataclass, field

BANDS: dict[str, tuple[int, int]] = {
    "Needs work": (0, 49),
    "Fair": (50, 69),
    "Good": (70, 84),
    "Excellent": (85, 100),
}
BAND_ORDER: list[str] = ["Needs work", "Fair", "Good", "Excellent"]


@dataclass(frozen=True)
class EvalCase:
    """One labelled resume."""

    id: str
    role: str                 # target role id for the ATS check
    file_format: str          # pdf | docx
    layout: str               # single | two_column | table | scanned
    expected_band: str
    rationale: str
    text: str = ""
    left: list[str] = field(default_factory=list)    # two-column / table layouts
    right: list[str] = field(default_factory=list)
    header: list[str] = field(default_factory=list)


CASES: list[EvalCase] = [
    EvalCase(
        id="E01_strong_data_analyst", role="data_analyst", file_format="pdf", layout="single",
        expected_band="Excellent",
        rationale="Every section present, categorised skills, three quantified projects, internship with metrics.",
        text="""Ananya Iyer
ananya.iyer@example.com | +91 98200 11223 | linkedin.com/in/ananya-iyer | github.com/ananyaiyer

SUMMARY
Final-year statistics student targeting data analyst roles; skilled in SQL, Python and Power BI.

EDUCATION
B.Sc. in Statistics, St. Xavier's College, Mumbai | 2022 - 2025 | CGPA 9.1/10

SKILLS
Languages: SQL, Python, R
Tools: Excel, Power BI, Tableau, Git
Concepts: Statistics, A/B testing, Data visualization, Data cleaning

EXPERIENCE
Data Analyst Intern, RetailCo | May 2024 - Jul 2024
- Wrote SQL queries across 6 tables to find the 3 categories driving 55% of returns.
- Automated a weekly Excel report with Python, saving 5 hours per week.

PROJECTS
Store Sales Dashboard | Power BI, SQL
- Built a dashboard tracking 10 KPIs across 45 stores.
Marketing A/B Test Analysis | Python, Pandas, Statistics
- Analyzed 18,000 users and found a 4.2% lift in conversion.
Customer Segmentation | Python, scikit-learn
- Clustered 9,000 customers into 5 segments used for targeting.

CERTIFICATIONS
- Google Data Analytics Certificate (2024)

ACHIEVEMENTS
- 2nd place, Inter-college Data Hackathon 2024 (120 teams)"""),
    EvalCase(
        id="E02_strong_ml_engineer", role="ai_ml_engineer", file_format="docx", layout="single",
        expected_band="Excellent",
        rationale="Complete and quantified; deployment and evaluation shown; strong verbs throughout.",
        text="""Rahul Menon
rahul.menon@example.com | +91 99887 66554 | linkedin.com/in/rahulmenon | github.com/rahulmenon

PROFESSIONAL SUMMARY
Machine learning student with two deployed NLP projects and a research internship.

EDUCATION
B.Tech in Computer Science, National Institute of Technology, Calicut | 2021 - 2025 | CGPA 8.9/10

TECHNICAL SKILLS
Languages: Python, SQL
Frameworks: PyTorch, TensorFlow, scikit-learn, Hugging Face
Tools: Docker, Git, FastAPI, AWS

EXPERIENCE
Research Intern, AI Lab, IISc | Jan 2024 - Jun 2024
- Fine-tuned a transformer classifier reaching 91% F1 on 12,000 support tickets.
- Reduced inference latency by 35% with ONNX export.

PROJECTS
Fake News Detector | Python, PyTorch, Hugging Face
- Trained a deep learning model with 93% accuracy on 40,000 articles.
Churn Prediction API | scikit-learn, FastAPI, Docker
- Engineered 30 features and deployed the model as a Docker service under 100 ms per request.
Handwriting Recognition | TensorFlow, OpenCV
- Built a CNN reaching 98% accuracy on 60,000 images with cross-validation.

CERTIFICATIONS
- Deep Learning Specialization (2023)

ACHIEVEMENTS
- Published a workshop paper on low-resource text classification (2024)"""),
    EvalCase(
        id="E03_web_dev_few_metrics", role="web_developer", file_format="pdf", layout="single",
        expected_band="Good",
        rationale="Well organised but no GitHub link and only one project has a measurable result.",
        text="""Kavya Reddy
kavya.reddy@example.com | +91 90000 12345 | linkedin.com/in/kavyareddy

SUMMARY
Frontend-focused computer science student building responsive web apps with React.

EDUCATION
B.E. in Information Technology, Osmania University | 2021 - 2025 | CGPA 8.2/10

SKILLS
Languages: JavaScript, TypeScript, HTML, CSS
Frameworks: React, Tailwind CSS, Next.js
Tools: Git, Figma, Vite

EXPERIENCE
Web Development Intern, PixelWorks | Jun 2024 - Aug 2024
- Built reusable React components for the client dashboard.
- Implemented responsive design for the marketing pages.

PROJECTS
Recipe Finder | React, REST API
- Developed a recipe search app consuming a public REST API.
Portfolio Website | Next.js, Tailwind CSS
- Designed a personal portfolio with a 97 Lighthouse score.

CERTIFICATIONS
- Meta Front-End Developer Certificate (2024)"""),
    EvalCase(
        id="E04_cloud_uncategorised", role="cloud_engineer", file_format="docx", layout="single",
        expected_band="Good",
        rationale="Relevant internship with metrics, but skills are one flat list and only two projects.",
        text="""Arjun Nair
arjun.nair@example.com | +91 91234 50000 | linkedin.com/in/arjunnair | github.com/arjun-nair

SUMMARY
Cloud and DevOps enthusiast with hands-on AWS and Kubernetes experience.

EDUCATION
B.Tech in Electronics, VIT University | 2021 - 2025

SKILLS
AWS, Linux, Docker, Kubernetes, Terraform, Jenkins, Python, Bash, Git

EXPERIENCE
DevOps Intern, CloudNine Systems | Jan 2024 - May 2024
- Automated deployments with Jenkins pipelines, cutting release time by 60%.
- Provisioned staging environments with Terraform on AWS.

PROJECTS
Kubernetes Blog Platform | Docker, Kubernetes, AWS
- Deployed a 3-service app on a Kubernetes cluster with autoscaling.
Infrastructure Monitoring | Prometheus, Grafana
- Configured dashboards and alerts for 12 services."""),
    EvalCase(
        id="E05_fullstack_two_column", role="full_stack_developer", file_format="pdf", layout="two_column",
        expected_band="Good",
        rationale="Decent content but short, no summary and no LinkedIn; two-column layout is an ATS risk.",
        header=["Neha Kapoor", "neha.kapoor@example.com | +91 98111 22334 | github.com/nehakapoor"],
        left=["SKILLS", "JavaScript, TypeScript", "React, Node.js", "Express, MongoDB", "PostgreSQL, Docker",
              "Git, REST APIs", "", "EDUCATION", "B.Tech in CSE", "Delhi Technological University", "2021 - 2025",
              "", "CERTIFICATIONS", "AWS Cloud Practitioner"],
        right=["EXPERIENCE", "Full Stack Intern, ShopEasy", "Built 12 REST endpoints in Express.", "Reduced API errors by 30%.", "",
               "PROJECTS", "Task Manager | MERN", "Built JWT auth used by 40 users.", "Designed a MongoDB schema.",
               "Chat App | Socket.io, React", "Implemented real-time chat rooms.", "Deployed on Render."]),
    EvalCase(
        id="E06_fresher_average", role="data_analyst", file_format="docx", layout="single",
        expected_band="Fair",
        rationale="No experience section, no links, projects without metrics, uncategorised skills.",
        text="""Sneha Patil
sneha.patil@example.com | +91 97000 33445

OBJECTIVE
To obtain an entry-level data analyst position.

EDUCATION
BCA, Pune University | 2022 - 2025

SKILLS
Python, SQL, Excel, Power BI, Statistics

PROJECTS
Sales Analysis
- Analyzed sales data in Excel and created charts.
COVID Dashboard | Power BI
- Created a dashboard showing cases by state."""),
    EvalCase(
        id="E07_first_person_filler", role="web_developer", file_format="docx", layout="single",
        expected_band="Fair",
        rationale="Has the sections but written in first person, full of filler and weak verbs, no metrics.",
        text="""Vikram Singh
vikram.singh@example.com | +91 98989 12121 | github.com/vikramsingh

SUMMARY
I am a hard working and passionate web developer. I am a team player and a fast learner who wants to grow.

EDUCATION
B.Sc. Computer Science, Punjab University | 2022 - 2025

SKILLS
HTML, CSS, JavaScript, React, Bootstrap, Git

EXPERIENCE
Intern, WebSolutions | Jun 2024 - Jul 2024
- I worked on the company website.
- I helped the team fix bugs in the React code.

PROJECTS
College Fest Website | HTML, CSS, JavaScript
- I made the website for my college fest.
To-do App | React
- I worked on a to-do app with my friends."""),
    EvalCase(
        id="E08_no_skills_section", role="full_stack_developer", file_format="pdf", layout="single",
        expected_band="Fair",
        rationale="Good projects and experience, but no skills section, no summary, no links.",
        text="""Rohan Das
rohan.das@example.com | +91 93300 44556

EDUCATION
B.Tech in Computer Science, Jadavpur University | 2021 - 2025 | CGPA 8.0/10

EXPERIENCE
Software Intern, FinTrack | May 2024 - Jul 2024
- Built REST APIs in Node.js and Express serving 2,000 daily users.
- Wrote PostgreSQL queries for the reporting module.

PROJECTS
Expense Tracker | React, Node.js, PostgreSQL
- Developed a full stack app with JWT authentication for 50 users.
Weather App | JavaScript, REST API
- Built a responsive weather app using a public API."""),
    EvalCase(
        id="E09_sparse_weak", role="data_analyst", file_format="docx", layout="single",
        expected_band="Needs work",
        rationale="Very short, first person, filler, one vague project, no experience or links.",
        text="""RESUME

Name: Rohit Kumar
Email: rohit123@gmail.com

Objective
I am a hard worker and team player who is passionate about computers. I want a job in a good company where I can learn.

Education
BSc Computer Science

Skills
Python, MS Office

Projects
I made a website for my college fest. I helped my friends with the code."""),
    EvalCase(
        id="E10_objective_only", role="cloud_engineer", file_format="docx", layout="single",
        expected_band="Needs work",
        rationale="Only contact, an objective and education; no skills, projects or experience.",
        text="""Pooja Sharma
pooja.sharma@example.com

Career Objective
Seeking a challenging role in a reputed organisation where I can utilise my skills and grow.

Education
B.Tech in Information Technology
Rajasthan Technical University, 2025"""),
    EvalCase(
        id="E11_table_layout", role="web_developer", file_format="docx", layout="table",
        expected_band="Fair",
        rationale="Reasonable content locked in a two-cell table; few metrics, no summary or links.",
        header=["Aditya Joshi", "aditya.joshi@example.com | +91 90909 80808"],
        left=["SKILLS", "HTML, CSS, JavaScript", "React, Git", "", "EDUCATION", "B.E. Computer Engineering",
              "Mumbai University, 2025"],
        right=["EXPERIENCE", "Frontend Intern, StartupX | Jun 2024 - Aug 2024",
               "Built landing pages in React.", "Improved page load time by 25%.", "",
               "PROJECTS", "Movie Search | React, REST API", "Developed a movie search app."]),
    EvalCase(
        id="E12_scanned", role="data_analyst", file_format="pdf", layout="scanned",
        expected_band="Needs work",
        rationale="Image-only PDF: no machine-readable text, so an ATS sees nothing."),
]
