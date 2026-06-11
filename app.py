from fastapi import FastAPI, UploadFile, File, Form
from fastapi.responses import HTMLResponse, StreamingResponse
from pypdf import PdfReader
import docx as python_docx
import os
import re
import json
import io
import anthropic
from fastapi import Request
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from uuid import uuid4
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
from reportlab.lib.enums import TA_LEFT, TA_CENTER
from database import SessionLocal, CVResult

app = FastAPI()

templates = Jinja2Templates(directory="templates")
app.mount("/static", StaticFiles(directory="static"), name="static")

model = SentenceTransformer("all-MiniLM-L6-v2")

UPLOAD_FOLDER = "uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# ---------------------------------------------------------------------------
# Skill aliases
# ---------------------------------------------------------------------------
SKILL_ALIASES: dict[str, list[str]] = {
    "Python":             ["python"],
    "Java":               ["java"],
    "C++":                ["c++", "cpp"],
    "C#":                 ["c#", "csharp", "c sharp"],
    "Go":                 ["golang", "go"],
    "Rust":               ["rust"],
    "Swift":              ["swift"],
    "Kotlin":             ["kotlin"],
    "TypeScript":         ["typescript", "ts"],
    "JavaScript":         ["javascript", "js", "node.js", "nodejs", "node js"],
    "PHP":                ["php"],
    "Ruby":               ["ruby", "ruby on rails", "rails"],
    "R":                  ["r programming", "r language"],
    "MATLAB":             ["matlab"],
    "Scala":              ["scala"],
    "Bash":               ["bash", "shell scripting", "shell script"],
    "HTML":               ["html", "html5"],
    "CSS":                ["css", "css3", "sass", "scss"],
    "React":              ["react", "react.js", "reactjs"],
    "Vue":                ["vue", "vue.js", "vuejs"],
    "Angular":            ["angular", "angularjs"],
    "Next.js":            ["next.js", "nextjs"],
    "Tailwind CSS":       ["tailwind", "tailwindcss"],
    "Bootstrap":          ["bootstrap"],
    "FastAPI":            ["fastapi"],
    "Django":             ["django"],
    "Flask":              ["flask"],
    "Spring Boot":        ["spring boot", "spring"],
    "Express":            ["express", "express.js", "expressjs"],
    "REST API":           ["rest api", "restful", "rest"],
    "GraphQL":            ["graphql"],
    "SQL":                ["sql", "mysql", "postgresql", "postgres", "sqlite",
                           "oracle", "mssql", "sql server", "mariadb"],
    "MongoDB":            ["mongodb", "mongo"],
    "Redis":              ["redis"],
    "Elasticsearch":      ["elasticsearch", "elastic search"],
    "Firebase":           ["firebase"],
    "Cassandra":          ["cassandra"],
    "Docker":             ["docker"],
    "Kubernetes":         ["kubernetes", "k8s"],
    "Git":                ["git", "github", "gitlab", "bitbucket", "version control"],
    "Linux":              ["linux", "ubuntu", "centos", "unix", "debian"],
    "AWS":                ["aws", "amazon web services", "ec2", "s3", "lambda"],
    "Azure":              ["azure", "microsoft azure"],
    "GCP":                ["gcp", "google cloud", "google cloud platform"],
    "CI/CD":              ["ci/cd", "cicd", "jenkins", "github actions",
                           "gitlab ci", "travis ci", "circle ci"],
    "Terraform":          ["terraform"],
    "Ansible":            ["ansible"],
    "Nginx":              ["nginx"],
    "Machine Learning":   ["machine learning", "ml"],
    "Deep Learning":      ["deep learning", "dl"],
    "AI":                 ["artificial intelligence", " ai "],
    "NLP":                ["nlp", "natural language processing"],
    "Computer Vision":    ["computer vision"],
    "TensorFlow":         ["tensorflow", "tf"],
    "PyTorch":            ["pytorch", "torch"],
    "Keras":              ["keras"],
    "Scikit-learn":       ["scikit-learn", "sklearn", "scikit learn"],
    "Pandas":             ["pandas"],
    "NumPy":              ["numpy"],
    "OpenCV":             ["opencv", "open cv"],
    "YOLO":               ["yolo"],
    "Hugging Face":       ["hugging face", "huggingface", "transformers"],
    "LangChain":          ["langchain", "lang chain"],
    "Data Analysis":      ["data analysis", "data analytics", "data analyst"],
    "Data Visualization": ["data visualization", "matplotlib", "seaborn",
                           "plotly", "tableau", "power bi", "powerbi"],
    "Android":            ["android"],
    "iOS":                ["ios", "xcode"],
    "React Native":       ["react native"],
    "Flutter":            ["flutter"],
    "Agile":              ["agile", "scrum", "kanban", "jira"],
    "Testing":            ["unit testing", "pytest", "jest", "selenium",
                           "test driven", "tdd", "bdd"],
    "Microservices":      ["microservices", "micro services"],
    "WebSockets":         ["websockets", "websocket"],
}

SKILLS = list(SKILL_ALIASES.keys())

DEFAULT_REQUIRED_SKILLS = [
    "Python", "SQL", "Git", "Machine Learning", "Linux", "AI"
]

CAREER_PATHS = {
    "AI Engineer":              {"skills": ["Python","AI","Machine Learning","TensorFlow","PyTorch","Deep Learning","NLP","Scikit-learn"], "min_match": 3},
    "Computer Vision Engineer": {"skills": ["Python","OpenCV","YOLO","Computer Vision","Deep Learning","TensorFlow","PyTorch"], "min_match": 2},
    "Data Scientist":           {"skills": ["Python","Machine Learning","SQL","Pandas","NumPy","Data Analysis","Scikit-learn","Data Visualization"], "min_match": 3},
    "Backend Developer":        {"skills": ["Python","SQL","FastAPI","Git","Docker","REST API","Django","Flask"], "min_match": 3},
    "Frontend Developer":       {"skills": ["HTML","CSS","JavaScript","React","TypeScript","Vue","Angular"], "min_match": 3},
    "DevOps Engineer":          {"skills": ["Docker","Kubernetes","Linux","CI/CD","AWS","Git","Terraform","Ansible"], "min_match": 3},
    "Full Stack Developer":     {"skills": ["HTML","CSS","JavaScript","React","Python","SQL","Git","REST API"], "min_match": 4},
    "Mobile Developer":         {"skills": ["Android","iOS","React Native","Flutter","Kotlin","Swift"], "min_match": 2},
}

SECTION_HEADERS = {
    "skills":     ["skills", "technical skills", "core competencies", "technologies", "tools", "expertise"],
    "experience": ["experience", "work experience", "employment", "professional experience", "career history"],
    "education":  ["education", "academic", "qualifications", "degree"],
    "projects":   ["projects", "personal projects", "portfolio"],
    "summary":    ["summary", "objective", "profile", "about"],
}

SKILL_ADVICE = {
    "Python":          "Improve your Python experience with real-world projects.",
    "Git":             "Add Git and GitHub projects to demonstrate version control skills.",
    "Docker":          "Learn Docker to improve deployment and DevOps skills.",
    "Linux":           "Mention Linux experience or system administration knowledge.",
    "SQL":             "Add database projects and SQL experience.",
    "Machine Learning":"Build and share ML projects on GitHub to demonstrate practical experience.",
    "AWS":             "Get the AWS Cloud Practitioner certification to validate cloud skills.",
    "Kubernetes":      "Learn Kubernetes to complement your Docker skills.",
    "TypeScript":      "Adopt TypeScript in your JavaScript projects to show modern web skills.",
    "React":           "Build portfolio projects using React to demonstrate frontend skills.",
}

# ---------------------------------------------------------------------------
# Text extraction
# ---------------------------------------------------------------------------

def extract_text_from_pdf(filepath: str) -> str:
    reader = PdfReader(filepath)
    text = ""
    for page in reader.pages:
        extracted = page.extract_text()
        if extracted:
            text += extracted
    return text


def extract_text_from_docx(filepath: str) -> str:
    doc = python_docx.Document(filepath)
    return "\n".join(p.text for p in doc.paragraphs if p.text.strip())


# ---------------------------------------------------------------------------
# Skill & section helpers
# ---------------------------------------------------------------------------

def parse_sections(text: str) -> dict[str, str]:
    sections: dict[str, str] = {s: "" for s in SECTION_HEADERS}
    sections["other"] = ""
    lines = text.splitlines()
    current_section = "other"
    for line in lines:
        stripped = line.strip().lower()
        matched = False
        for section, headers in SECTION_HEADERS.items():
            if any(stripped == h or stripped.startswith(h + ":") for h in headers):
                current_section = section
                matched = True
                break
        if not matched:
            sections[current_section] += " " + line
    return sections


def skill_in_text(skill: str, text: str) -> bool:
    aliases = SKILL_ALIASES.get(skill, [skill.lower()])
    for alias in aliases:
        pattern = r'\b' + re.escape(alias) + r'\b'
        if re.search(pattern, text, re.IGNORECASE):
            return True
    return False


def detect_skills(text: str) -> tuple[list[str], dict[str, list[str]]]:
    sections = parse_sections(text)
    found: set[str] = set()
    section_map: dict[str, list[str]] = {}
    for skill in SKILLS:
        found_in: list[str] = []
        for section_name, section_text in sections.items():
            if skill_in_text(skill, section_text):
                found_in.append(section_name)
        if found_in:
            found.add(skill)
            section_map[skill] = found_in
    found_skills = [s for s in SKILLS if s in found]
    return found_skills, section_map


def compute_weighted_ats(
    found_skills: list[str],
    section_map: dict[str, list[str]],
    required: list[str]
) -> tuple[int, list[str], str]:
    total_weight = len(required)
    if total_weight == 0:
        return 0, [], ""
    earned = 0.0
    missing = []
    explanation_parts = []
    for skill in required:
        if skill not in found_skills:
            missing.append(skill)
            explanation_parts.append(f"✗ {skill}: not found")
        else:
            locations = section_map.get(skill, [])
            if any(loc in ("skills", "experience", "projects") for loc in locations):
                earned += 1.0
                explanation_parts.append(f"✓ {skill}: found in {', '.join(locations)}")
            else:
                earned += 0.5
                explanation_parts.append(
                    f"△ {skill}: only mentioned in {', '.join(locations)} (add to Skills/Experience)"
                )
    score = int((earned / total_weight) * 100)
    return score, missing, "\n".join(explanation_parts)


# ---------------------------------------------------------------------------
# PDF report generation
# ---------------------------------------------------------------------------

def build_pdf_report(result: CVResult) -> bytes:
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer, pagesize=A4,
        leftMargin=2*cm, rightMargin=2*cm,
        topMargin=2*cm, bottomMargin=2*cm
    )

    styles = getSampleStyleSheet()
    accent = colors.HexColor("#2d5a3d")
    light  = colors.HexColor("#edf4ef")
    red    = colors.HexColor("#c0392b")
    muted  = colors.HexColor("#6b6760")

    h1  = ParagraphStyle("h1",  parent=styles["Heading1"], textColor=accent,  fontSize=22, spaceAfter=4)
    h2  = ParagraphStyle("h2",  parent=styles["Heading2"], textColor=accent,  fontSize=13, spaceBefore=14, spaceAfter=6)
    bod = ParagraphStyle("bod", parent=styles["Normal"],   textColor=muted,   fontSize=10, leading=16)
    sml = ParagraphStyle("sml", parent=styles["Normal"],   textColor=muted,   fontSize=9,  leading=14)

    story = []

    # Title
    story.append(Paragraph("CV Analysis Report", h1))
    story.append(Paragraph(
        f"File: {result.original_filename or result.filename} &nbsp;|&nbsp; "
        f"Date: {result.created_at.strftime('%Y-%m-%d %H:%M') if result.created_at else '—'}",
        sml
    ))
    story.append(Spacer(1, 0.3*cm))
    story.append(HRFlowable(width="100%", color=accent, thickness=1))
    story.append(Spacer(1, 0.3*cm))

    # Scores table
    story.append(Paragraph("Scores", h2))
    score_data = [
        ["ATS Score", "Job Match", "AI Match"],
        [f"{int(result.ats_score)}%", f"{int(result.match_score)}%", f"{int(result.semantic_score)}%"],
    ]
    score_table = Table(score_data, colWidths=[5*cm, 5*cm, 5*cm])
    score_table.setStyle(TableStyle([
        ("BACKGROUND",  (0,0), (-1,0), accent),
        ("TEXTCOLOR",   (0,0), (-1,0), colors.white),
        ("FONTSIZE",    (0,0), (-1,0), 10),
        ("FONTSIZE",    (0,1), (-1,1), 18),
        ("TEXTCOLOR",   (0,1), (-1,1), accent),
        ("ALIGN",       (0,0), (-1,-1), "CENTER"),
        ("VALIGN",      (0,0), (-1,-1), "MIDDLE"),
        ("ROWBACKGROUNDS", (0,1), (-1,-1), [light]),
        ("BOX",         (0,0), (-1,-1), 0.5, colors.HexColor("#e8e4dd")),
        ("INNERGRID",   (0,0), (-1,-1), 0.5, colors.HexColor("#e8e4dd")),
        ("TOPPADDING",  (0,0), (-1,-1), 8),
        ("BOTTOMPADDING",(0,0),(-1,-1), 8),
    ]))
    story.append(score_table)

    # Summary
    if result.summary:
        story.append(Paragraph("Summary", h2))
        story.append(Paragraph(result.summary, bod))

    # ATS breakdown
    if result.ats_explanation:
        story.append(Paragraph("ATS Score Breakdown", h2))
        for line in result.ats_explanation.splitlines():
            story.append(Paragraph(line, sml))

    # Skills found
    found = [s.strip() for s in (result.found_skills or "").split(",") if s.strip()]
    if found:
        story.append(Paragraph("Skills Found", h2))
        story.append(Paragraph(", ".join(found), bod))

    # Missing skills
    missing = [s.strip() for s in (result.missing_skills or "").split(",") if s.strip()]
    if missing:
        story.append(Paragraph("Missing Required Skills", h2))
        miss_style = ParagraphStyle("miss", parent=bod, textColor=red)
        story.append(Paragraph(", ".join(missing), miss_style))

    # Recommended roles
    roles = json.loads(result.recommended_roles or "[]")
    if roles:
        story.append(Paragraph("Recommended Roles", h2))
        role_data = [["Role", "Match %", "Matched Skills"]]
        for r in roles:
            role_data.append([r["role"], f"{r['match_pct']}%", ", ".join(r["matched"])])
        role_table = Table(role_data, colWidths=[5*cm, 2.5*cm, 9.5*cm])
        role_table.setStyle(TableStyle([
            ("BACKGROUND",  (0,0), (-1,0), accent),
            ("TEXTCOLOR",   (0,0), (-1,0), colors.white),
            ("FONTSIZE",    (0,0), (-1,-1), 9),
            ("ROWBACKGROUNDS", (0,1), (-1,-1), [colors.white, light]),
            ("BOX",         (0,0), (-1,-1), 0.5, colors.HexColor("#e8e4dd")),
            ("INNERGRID",   (0,0), (-1,-1), 0.5, colors.HexColor("#e8e4dd")),
            ("TOPPADDING",  (0,0), (-1,-1), 6),
            ("BOTTOMPADDING",(0,0),(-1,-1), 6),
            ("LEFTPADDING", (0,0), (-1,-1), 8),
        ]))
        story.append(role_table)

    # Recommendations
    recs = json.loads(result.recommendations or "[]")
    if recs:
        story.append(Paragraph("Recommendations", h2))
        for rec in recs:
            story.append(Paragraph(f"• {rec}", bod))

    doc.build(story)
    return buffer.getvalue()


# ---------------------------------------------------------------------------
# Claude AI summary
# ---------------------------------------------------------------------------

def generate_ai_summary(
    cv_text: str,
    ats_score: int,
    match_score: int,
    semantic_score: int,
    found_skills: list[str],
    missing_skills: list[str],
    missing_job_skills: list[str],
    recommended_roles: list[dict],
    job_description: str,
) -> str:
    """Call the Anthropic API to generate a personalised CV summary.
    Falls back to a plain text summary if the API call fails."""
    try:
        client = anthropic.Anthropic()

        top_roles = ", ".join(r["role"] for r in recommended_roles[:2]) or "no clear role match"
        missing_text = ", ".join(missing_job_skills) if missing_job_skills else "none"
        missing_required = ", ".join(missing_skills) if missing_skills else "none"

        prompt = f"""You are an expert career advisor and CV analyst. Analyze this CV data and write a concise, honest, and encouraging 3-4 sentence summary for the candidate.

CV Analysis Results:
- ATS Score: {ats_score}% (based on required skills match)
- Job Match Score: {match_score}% (skills matched to job description)
- AI Semantic Match: {semantic_score}% (overall CV-to-job similarity)
- Skills Found: {", ".join(found_skills) or "none detected"}
- Missing Required Skills: {missing_required}
- Missing Job Skills: {missing_text}
- Best Matching Roles: {top_roles}
- Job Description Provided: {"Yes" if job_description.strip() else "No"}

Write a personalized summary that:
1. Opens with an honest assessment of the CV's overall strength
2. Highlights what the candidate does well
3. Clearly identifies the most important gaps to address
4. Ends with one specific, actionable next step

Keep it direct, professional, and under 100 words. Do not use bullet points."""

        message = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=300,
            messages=[{"role": "user", "content": prompt}]
        )
        return message.content[0].text.strip()

    except Exception:
        # Fallback to hardcoded summary if API call fails
        top_roles_text = ", ".join(r["role"] for r in recommended_roles[:2]) or "No suitable role detected"
        missing_text   = ", ".join(missing_job_skills) or "no major skill gaps"
        return (
            f"Your CV achieved an ATS score of {ats_score}%. "
            f"The profile is most suitable for: {top_roles_text}. "
            f"To improve your chances, focus on: {missing_text}."
        )


# ---------------------------------------------------------------------------
# Core analysis — shared by upload and re-used by detail page
# ---------------------------------------------------------------------------

def analyse_text(
    text: str,
    job_description: str,
    required_skills: list[str]
) -> dict:
    # Semantic score
    if job_description.strip():
        cv_emb  = model.encode(text)
        job_emb = model.encode(job_description)
        sim     = cosine_similarity([cv_emb], [job_emb])[0][0]
        semantic_match_score = int(sim * 100)
    else:
        semantic_match_score = 0

    found_skills, section_map = detect_skills(text)
    ats_score, missing_skills, ats_explanation = compute_weighted_ats(
        found_skills, section_map, required_skills
    )

    recommended_roles = []
    for role, config in CAREER_PATHS.items():
        matched = [s for s in config["skills"] if s in found_skills]
        if len(matched) >= config["min_match"]:
            pct = int((len(matched) / len(config["skills"])) * 100)
            recommended_roles.append({"role": role, "match_pct": pct, "matched": matched})
    recommended_roles.sort(key=lambda x: x["match_pct"], reverse=True)

    job_found_skills, _ = detect_skills(job_description)
    matched_job_skills  = [s for s in found_skills if s in job_found_skills]
    missing_job_skills  = [s for s in job_found_skills if s not in found_skills]

    match_score = (
        int((len(matched_job_skills) / len(job_found_skills)) * 100)
        if job_found_skills else 0
    )

    recommendations = [
        SKILL_ADVICE.get(s, f"Consider learning {s} to improve your match score.")
        for s in missing_job_skills
    ]

    summary = generate_ai_summary(
        cv_text=text,
        ats_score=ats_score,
        match_score=match_score,
        semantic_score=semantic_match_score,
        found_skills=found_skills,
        missing_skills=missing_skills,
        missing_job_skills=missing_job_skills,
        recommended_roles=recommended_roles,
        job_description=job_description,
    )

    return dict(
        ats_score=ats_score,
        ats_explanation=ats_explanation,
        match_score=match_score,
        semantic_match_score=semantic_match_score,
        summary=summary,
        found_skills=found_skills,
        missing_skills=missing_skills,
        recommended_roles=recommended_roles,
        matched_job_skills=matched_job_skills,
        missing_job_skills=missing_job_skills,
        recommendations=recommendations,
        section_map=section_map,
        characters=len(text),
    )


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@app.get("/")
async def home(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={"default_skills": ", ".join(DEFAULT_REQUIRED_SKILLS)}
    )


@app.get("/history")
async def history(request: Request):
    db = SessionLocal()
    results = db.query(CVResult).order_by(CVResult.id.desc()).all()
    db.close()
    return templates.TemplateResponse(
        request=request, name="history.html", context={"results": results}
    )


@app.get("/history/{result_id}")
async def history_detail(request: Request, result_id: int):
    db = SessionLocal()
    result = db.query(CVResult).filter(CVResult.id == result_id).first()
    db.close()
    if not result:
        return templates.TemplateResponse(
            request=request, name="history.html",
            context={"results": [], "error": "Result not found."}
        )
    # Deserialise stored JSON fields
    recommended_roles = json.loads(result.recommended_roles or "[]")
    recommendations   = json.loads(result.recommendations   or "[]")
    found_skills      = [s.strip() for s in (result.found_skills      or "").split(",") if s.strip()]
    missing_skills    = [s.strip() for s in (result.missing_skills     or "").split(",") if s.strip()]
    matched_job_skills= [s.strip() for s in (result.matched_job_skills or "").split(",") if s.strip()]
    missing_job_skills= [s.strip() for s in (result.missing_job_skills or "").split(",") if s.strip()]

    return templates.TemplateResponse(
        request=request,
        name="result.html",
        context={
            "ats_score":            result.ats_score,
            "ats_explanation":      result.ats_explanation or "",
            "match_score":          result.match_score,
            "semantic_match_score": result.semantic_score,
            "summary":              result.summary or "",
            "found_skills":         found_skills,
            "missing_skills":       missing_skills,
            "recommended_roles":    recommended_roles,
            "matched_job_skills":   matched_job_skills,
            "missing_job_skills":   missing_job_skills,
            "recommendations":      recommendations,
            "characters":           0,
            "section_map":          {},
            "from_history":         True,
            "result_id":            result_id,
            "original_filename":    result.original_filename or result.filename,
        }
    )


@app.get("/report/{result_id}")
async def download_report(result_id: int):
    db = SessionLocal()
    result = db.query(CVResult).filter(CVResult.id == result_id).first()
    db.close()
    if not result:
        return {"error": "Result not found."}

    pdf_bytes = build_pdf_report(result)
    filename  = f"cv_report_{result_id}.pdf"
    return StreamingResponse(
        io.BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )


@app.post("/upload")
async def upload_cv(
    request: Request,
    file: UploadFile = File(...),
    job_description: str = Form(""),
    required_skills_input: str = Form(""),
):
    fname = file.filename or ""
    is_pdf  = fname.lower().endswith(".pdf")
    is_docx = fname.lower().endswith(".docx")

    if not is_pdf and not is_docx:
        return {"error": "Only PDF and DOCX files are accepted."}

    ext      = ".pdf" if is_pdf else ".docx"
    filename = f"{uuid4()}{ext}"
    filepath = os.path.join(UPLOAD_FOLDER, filename)

    content = await file.read()
    if not content:
        return {"error": "Uploaded file is empty"}
    if len(content) > 5 * 1024 * 1024:
        return {"error": "File too large. Maximum size is 5MB."}

    with open(filepath, "wb") as buffer:
        buffer.write(content)

    try:
        text = extract_text_from_pdf(filepath) if is_pdf else extract_text_from_docx(filepath)
    except Exception as e:
        if os.path.exists(filepath):
            os.remove(filepath)
        return {"error": f"Could not read file: {str(e)}"}

    if os.path.exists(filepath):
        os.remove(filepath)

    if len(text.strip()) < 100:
        return {"error": "Could not extract enough text. If it's a scanned PDF, please use a text-based one."}

    # Parse custom required skills (comma-separated input from the form)
    if required_skills_input.strip():
        required_skills = [s.strip() for s in required_skills_input.split(",") if s.strip()]
    else:
        required_skills = DEFAULT_REQUIRED_SKILLS

    r = analyse_text(text, job_description, required_skills)

    # Save to DB
    db = SessionLocal()
    try:
        new_result = CVResult(
            filename=filename,
            original_filename=fname,
            ats_score=r["ats_score"],
            match_score=r["match_score"],
            semantic_score=r["semantic_match_score"],
            summary=r["summary"],
            ats_explanation=r["ats_explanation"],
            found_skills=", ".join(r["found_skills"]),
            missing_skills=", ".join(r["missing_skills"]),
            recommended_roles=json.dumps(r["recommended_roles"]),
            matched_job_skills=", ".join(r["matched_job_skills"]),
            missing_job_skills=", ".join(r["missing_job_skills"]),
            recommendations=json.dumps(r["recommendations"]),
            job_description=job_description,
            required_skills=", ".join(required_skills),
        )
        db.add(new_result)
        db.commit()
        db.refresh(new_result)
        result_id = new_result.id
    finally:
        db.close()

    return templates.TemplateResponse(
        request=request,
        name="result.html",
        context={
            **r,
            "from_history":      False,
            "result_id":         result_id,
            "original_filename": fname,
        }
    )