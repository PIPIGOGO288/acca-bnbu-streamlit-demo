import re
from datetime import datetime
from typing import Dict, List, Tuple

import pandas as pd
import streamlit as st

# Optional imports for live public-page fetching.
# The app works even if internet access is blocked.
try:
    import requests
    from bs4 import BeautifulSoup
except Exception:  # pragma: no cover
    requests = None
    BeautifulSoup = None


# =============================
# Page config
# =============================
st.set_page_config(
    page_title="ACCA PathFinder｜BMBU 学生路线规划小助手",
    page_icon="🧭",
    layout="wide",
    initial_sidebar_state="expanded",
)


# =============================
# Demo data
# =============================
IMPORTANT_LINKS = {
    "ACCA Important Dates": "https://www.accaglobal.com/gb/en/student/getting-started/important-dates.html",
    "ACCA Exemptions Calculator": "https://www.accaglobal.com/gb/en/help/exemptions-calculator.html",
    "ACCA Exam Timetables": "https://www.accaglobal.com/gb/en/student/exam-entry-and-administration/exam-timetables.html",
    "ACCA Webinar Support": "https://www.accaglobal.com/gb/en/student/prepare-for-exams/InSession-exam-countdown-emails/webinar-support.html",
    "ACCA Learning and Events": "https://www.accaglobal.com/learning-and-events.html",
}

EXAM_STRUCTURE = {
    "Applied Knowledge 基础阶段": [
        ("BT", "Business and Technology", "商业与科技", "on-demand CBE 随时机考"),
        ("MA", "Management Accounting", "管理会计", "on-demand CBE 随时机考"),
        ("FA", "Financial Accounting", "财务会计", "on-demand CBE 随时机考"),
    ],
    "Applied Skills 技能阶段": [
        ("LW", "Corporate and Business Law", "公司法与商法", "部分版本可 on-demand，其余为季考"),
        ("PM", "Performance Management", "业绩管理", "季考"),
        ("TX", "Taxation", "税务", "季考"),
        ("FR", "Financial Reporting", "财务报告", "季考"),
        ("AA", "Audit and Assurance", "审计与鉴证", "季考"),
        ("FM", "Financial Management", "财务管理", "季考"),
    ],
    "Strategic Professional 战略专业阶段": [
        ("SBL", "Strategic Business Leader", "战略商业领袖", "季考"),
        ("SBR", "Strategic Business Reporting", "战略商业报告", "季考"),
        ("AFM", "Advanced Financial Management", "高级财务管理", "选修 / 季考"),
        ("APM", "Advanced Performance Management", "高级业绩管理", "选修 / 季考"),
        ("AAA", "Advanced Audit and Assurance", "高级审计", "选修 / 季考"),
        ("ATX", "Advanced Taxation", "高级税务", "选修 / 季考"),
    ],
}

EXEMPTION_RULES = {
    "BT": {
        "name": "Business and Technology",
        "cn": "商业与科技",
        "keywords": ["business", "management", "organization", "organisation", "marketing", "business technology", "商业", "管理", "组织", "市场营销"],
        "reason": "课程内容可能覆盖商业组织、管理基础或商业环境。",
    },
    "MA": {
        "name": "Management Accounting",
        "cn": "管理会计",
        "keywords": ["management accounting", "cost accounting", "budgeting", "variance", "成本", "预算", "差异", "管理会计"],
        "reason": "课程内容可能覆盖成本、预算、差异分析和管理决策。",
    },
    "FA": {
        "name": "Financial Accounting",
        "cn": "财务会计",
        "keywords": ["financial accounting", "accounting principles", "financial reporting", "intermediate accounting", "财务会计", "会计原理", "中级会计", "财务报告"],
        "reason": "课程内容可能覆盖会计基础、报表和基础准则。",
    },
    "LW": {
        "name": "Corporate and Business Law",
        "cn": "公司法与商法",
        "keywords": ["business law", "company law", "commercial law", "principle of law", "legal", "law", "商法", "公司法", "商业法", "法律"],
        "reason": "课程内容可能覆盖合同、公司法、商法或商业法律环境。",
    },
}

CAREER_ROADMAPS = {
    "四大审计 / 外资审计": {
        "tagline": "重点能力：逻辑 + 报告 + 判断",
        "target_roles": "Big4 Audit / External Audit / Assurance",
        "stages": [
            ("第一阶段：快速完成基础", ["BT", "MA", "FA", "LW"], "先打牢商业、会计、管理和法律基础；如果已免考，就直接跳到核心科目。"),
            ("第二阶段：审计核心优先", ["FR", "AA", "SBR"], "审计师首先要看懂财报，再判断报表是否真实、公允，所以 FR、AA、SBR 最关键。"),
            ("第三阶段：高级审计强化", ["SBL", "AAA"], "AAA 与审计职业高度相关，适合目标为四大或外资审计的学生。"),
        ],
        "key_papers": ["FR", "AA", "SBR", "AAA"],
    },
    "企业财务 / FP&A / 投行支持": {
        "tagline": "重点能力：分析 + 决策 + 管理",
        "target_roles": "FP&A / Corporate Finance / Investment Banking Support",
        "stages": [
            ("第一阶段：建立商业与会计语言", ["BT", "MA", "FA", "LW"], "先理解企业如何运作、数据如何记录、规则如何影响商业决策。"),
            ("第二阶段：财务分析核心", ["FM", "PM", "FR"], "企业财务重视预算、绩效分析、资金决策和报表理解。"),
            ("第三阶段：战略与管理提升", ["SBL", "APM"], "APM 更贴近管理决策、绩效管理和企业战略分析。"),
        ],
        "key_papers": ["FM", "PM", "FR", "SBL", "APM"],
    },
    "税务 / 财税咨询": {
        "tagline": "重点能力：规则 + 细节 + 报表理解",
        "target_roles": "Tax Advisory / Corporate Tax / Cross-border Tax",
        "stages": [
            ("第一阶段：补足会计与法律基础", ["BT", "MA", "FA", "LW"], "税务方向也需要基本商业、会计和法律基础。"),
            ("第二阶段：税务核心优先", ["TX", "FR", "FM"], "税务方向最需要税法规则、财报理解和财务管理能力。"),
            ("第三阶段：高级税务强化", ["ATX", "SBL"], "ATX 适合未来想做税务咨询、企业税务或跨境税务方向的学生。"),
        ],
        "key_papers": ["TX", "ATX", "FR", "FM"],
    },
}

MOCK_EVENTS = [
    {
        "title": "ACCA Exam Support Webinar｜考前备考与答题策略",
        "topic": "Exam Support",
        "date": "滚动更新",
        "source": "ACCA Webinar Support",
        "link": IMPORTANT_LINKS["ACCA Webinar Support"],
        "why": "适合准备 FR / AA / PM / FM 等季考的同学，帮助理解考试要求。",
    },
    {
        "title": "ACCA Learning｜Sustainability and ESG learning resources",
        "topic": "ESG",
        "date": "长期开放",
        "source": "ACCA Learning and Events",
        "link": IMPORTANT_LINKS["ACCA Learning and Events"],
        "why": "适合想把财会与 ESG、可持续发展、企业披露联系起来的同学。",
    },
    {
        "title": "Career Development Event｜财会职业路径与国际资格介绍",
        "topic": "Career",
        "date": "滚动更新",
        "source": "ACCA Events and Webinars",
        "link": "https://www.accaglobal.com/uk/en/member/membership/new-to-membership/your-community/events-and-webinars.html",
        "why": "适合大一、大二同学初步了解审计、税务、企业财务等职业方向。",
    },
]

EXAM_SESSIONS = pd.DataFrame(
    [
        ["3月考季", "约前一年 11月–1月", "3月", "约4月", "适合提前规划春季考试"],
        ["6月考季", "约2月–4月", "6月", "约7月", "适合春季学期结束后参加"],
        ["9月考季", "约5月–8月", "9月", "约10月", "适合暑假后参加"],
        ["12月考季", "约8月–10月", "12月", "约次年1月", "适合秋季学期末参加"],
    ],
    columns=["考季", "大致报名窗口", "考试月份", "大致出分时间", "规划提示"],
)


# =============================
# Helper functions
# =============================
def inject_css() -> None:
    st.markdown(
        """
        <style>
        .main {background: #fffdf7;}
        .block-container {padding-top: 1.5rem; padding-bottom: 2rem;}
        .hero {
            padding: 1.4rem 1.6rem;
            border-radius: 22px;
            background: linear-gradient(135deg, #d71920 0%, #ff6b6b 100%);
            color: white;
            box-shadow: 0 8px 24px rgba(215, 25, 32, 0.18);
            margin-bottom: 1rem;
        }
        .hero h1 {font-size: 2.2rem; margin: 0 0 0.4rem 0;}
        .hero p {font-size: 1.05rem; margin: 0; opacity: 0.95;}
        .card {
            padding: 1rem 1.1rem;
            border-radius: 18px;
            background: #ffffff;
            border: 1px solid #f1d4d4;
            box-shadow: 0 4px 18px rgba(0,0,0,0.04);
            margin-bottom: 0.8rem;
        }
        .soft-card {
            padding: 1rem;
            border-radius: 16px;
            background: #fff7e6;
            border: 1px solid #ffd89a;
            margin-bottom: 0.8rem;
        }
        .red-pill {
            display: inline-block;
            padding: 0.25rem 0.7rem;
            background: #d71920;
            color: white;
            border-radius: 999px;
            font-weight: 700;
            margin-bottom: 0.4rem;
        }
        .gray-small {font-size: 0.86rem; color: #666;}
        .paper-code {
            display: inline-block;
            padding: 0.18rem 0.55rem;
            border-radius: 8px;
            background: #fff0f0;
            color: #c0161d;
            border: 1px solid #ffc8c8;
            font-weight: 800;
            margin: 0.15rem;
        }
        .success-box {
            padding: 0.8rem 1rem;
            border-radius: 14px;
            background: #f2fff5;
            border: 1px solid #bfe7c8;
        }
        .warning-box {
            padding: 0.8rem 1rem;
            border-radius: 14px;
            background: #fff8e8;
            border: 1px solid #ffe0a3;
        }
        a {text-decoration: none;}
        </style>
        """,
        unsafe_allow_html=True,
    )


def normalize_text(text: str) -> str:
    return re.sub(r"\s+", " ", text.strip().lower())


def parse_courses(raw_text: str) -> List[str]:
    parts = re.split(r"[\n,;；，]+", raw_text)
    return [p.strip() for p in parts if p.strip()]


def estimate_exemptions(courses: List[str]) -> List[Dict[str, str]]:
    results = []
    normalized_courses = [(course, normalize_text(course)) for course in courses]

    for code, rule in EXEMPTION_RULES.items():
        matched = []
        hit_count = 0
        for original, normalized in normalized_courses:
            for keyword in rule["keywords"]:
                if normalize_text(keyword) in normalized:
                    matched.append(original)
                    hit_count += 1
                    break

        if matched:
            confidence = "High" if hit_count >= 2 else "Medium"
            results.append(
                {
                    "科目代码": code,
                    "ACCA科目": rule["name"],
                    "中文名称": rule["cn"],
                    "匹配课程": "、".join(sorted(set(matched))),
                    "预估信心": confidence,
                    "说明": rule["reason"],
                }
            )

    return results


def get_exam_dataframe() -> pd.DataFrame:
    rows = []
    for level, papers in EXAM_STRUCTURE.items():
        for code, name, cn, exam_type in papers:
            rows.append(
                {
                    "阶段": level,
                    "代码": code,
                    "英文科目": name,
                    "中文科目": cn,
                    "考试形式": exam_type,
                }
            )
    return pd.DataFrame(rows)


def render_papers(papers: List[str]) -> str:
    if not papers:
        return "<span class='gray-small'>无，需要看是否已免考或另选科目</span>"
    return " ".join([f"<span class='paper-code'>{p}</span>" for p in papers])


def fetch_public_acca_titles() -> Tuple[List[Dict[str, str]], str]:
    """
    Optional live fetch from public ACCA webpages.
    This is intentionally conservative and has mock fallback data.
    """
    if requests is None or BeautifulSoup is None:
        return MOCK_EVENTS, "当前环境缺少 requests / BeautifulSoup，已显示内置示例数据。"

    sources = [
        ("ACCA Webinar Support", IMPORTANT_LINKS["ACCA Webinar Support"]),
        ("ACCA Learning and Events", IMPORTANT_LINKS["ACCA Learning and Events"]),
    ]
    events: List[Dict[str, str]] = []
    headers = {"User-Agent": "ACCA-PathFinder-Demo/1.0 (student project)"}

    try:
        for source_name, url in sources:
            resp = requests.get(url, headers=headers, timeout=8)
            resp.raise_for_status()
            soup = BeautifulSoup(resp.text, "html.parser")
            candidates = soup.find_all(["h1", "h2", "h3", "a"])
            for item in candidates:
                title = item.get_text(" ", strip=True)
                if not title or len(title) < 8:
                    continue
                if any(k in title.lower() for k in ["webinar", "event", "learning", "exam", "support", "acca"]):
                    link = item.get("href") or url
                    if link.startswith("/"):
                        link = "https://www.accaglobal.com" + link
                    events.append(
                        {
                            "title": title[:120],
                            "topic": "Official Update",
                            "date": "实时抓取",
                            "source": source_name,
                            "link": link,
                            "why": "来自 ACCA 官方公开页面。请点击官网链接查看最新详情。",
                        }
                    )

        # deduplicate
        seen = set()
        unique_events = []
        for event in events:
            key = (event["source"], event["title"])
            if key not in seen:
                unique_events.append(event)
                seen.add(key)

        if not unique_events:
            return MOCK_EVENTS, "未抓取到清晰标题，已显示内置示例数据。"
        return unique_events[:12], f"已尝试从 ACCA 官方公开页面更新，更新时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
    except Exception as exc:
        return MOCK_EVENTS, f"当前环境可能无法联网或官网拒绝请求，已显示内置示例数据。错误信息：{exc}"


def ai_style_summary(career_goal: str, exemptions: List[str]) -> str:
    """
    This is a placeholder for future DeepSeek/DeepC integration.
    It produces deterministic text so the demo can run without an API key.
    """
    exempt_text = "、".join(exemptions) if exemptions else "暂无免考科目"
    if "审计" in career_goal:
        return f"你当前目标是审计方向，已选择免考：{exempt_text}。建议优先关注 FR、AA 和 SBR，因为审计工作需要先看懂财报，再形成审计判断。未来如果想强化四大/外资审计竞争力，可以把 AAA 作为高级阶段重点。"
    if "财务" in career_goal or "FP&A" in career_goal:
        return f"你当前目标是企业财务或 FP&A，已选择免考：{exempt_text}。建议优先关注 FM、PM 和 FR，因为这些科目更贴近预算、绩效分析、资金决策和报表理解。"
    if "税" in career_goal:
        return f"你当前目标是税务方向，已选择免考：{exempt_text}。建议优先关注 TX、FR 和 ATX，因为税务岗位需要规则理解、细节处理和报表基础。"
    return f"已选择免考：{exempt_text}。建议先完成基础阶段，再根据职业目标选择核心科目。"


# =============================
# App starts
# =============================
inject_css()

with st.sidebar:
    st.image("https://www.accaglobal.com/etc.clientlibs/settings/wcm/designs/acca/clientlibs/images/acca-logo.svg", width=120)
    st.title("ACCA PathFinder")
    st.caption("BMBU 学生专属 ACCA 路线规划 Demo")
    st.markdown("---")
    st.markdown("**Demo 目标**")
    st.markdown("1. 免考预估\n2. 职业路线图\n3. 考试总览\n4. 讲座资讯")
    st.markdown("---")
    st.warning("本工具仅供学习规划和校园推广参考。最终免考、考试日期、讲座安排，请以 ACCA 官网和 myACCA 为准。")

st.markdown(
    """
    <div class="hero">
        <h1>🧭 ACCA PathFinder｜BMBU 学生路线规划小助手</h1>
        <p>让同学快速了解：我可能能免什么？我该先考什么？最近有什么 ACCA 讲座可以听？</p>
    </div>
    """,
    unsafe_allow_html=True,
)

st.caption("适合 ACCA 校园大使展示：把 ACCA 从“证书名称”转化成同学可以直接使用的职业规划工具。")

tab1, tab2, tab3, tab4 = st.tabs(["① 免考预估", "② 个性化路线图", "③ 考试总览", "④ 讲座资讯"])


# =============================
# Tab 1: Exemption estimator
# =============================
with tab1:
    st.subheader("① BMBU 学生免考预估")
    st.markdown(
        """
        <div class="warning-box">
        <b>注意：</b>这里是基于“课程名称关键词”的初步预估，不代表 ACCA 官方免考结果。正式结果需要通过 ACCA Exemptions Calculator 和 ACCA 审核确认。
        </div>
        """,
        unsafe_allow_html=True,
    )

    col1, col2 = st.columns([1, 1])
    with col1:
        university = st.text_input("学校 / University", value="BMBU")
        major = st.selectbox("专业 / Major", ["Accounting", "Finance", "Business", "Economics", "Other"])
        year = st.selectbox("年级 / Year", ["大一 Freshman", "大二 Sophomore", "大三 Junior", "大四 Senior"])
    with col2:
        raw_courses = st.text_area(
            "已学课程 / Completed courses（每行一门，或用逗号分隔）",
            value="Financial Accounting\nManagement Accounting\nPrinciple of Law\nBusiness Management\nIntermediate Accounting",
            height=160,
        )

    if st.button("🔍 开始预估我的可能免考科目", type="primary"):
        courses = parse_courses(raw_courses)
        estimates = estimate_exemptions(courses)
        st.session_state["estimated_exemptions"] = [item["科目代码"] for item in estimates]
        st.session_state["student_profile"] = {"university": university, "major": major, "year": year}

        if estimates:
            st.success(f"根据你输入的 {len(courses)} 门课程，系统预估你可能匹配 {len(estimates)} 门 ACCA 科目。")
            st.dataframe(pd.DataFrame(estimates), use_container_width=True, hide_index=True)
        else:
            st.info("暂未匹配到明显的免考科目。可以尝试输入更完整的英文课程名称，例如 Financial Accounting / Management Accounting / Business Law。")

        st.markdown(
            f"""
            <div class="soft-card">
            <b>下一步：</b>前往 <a href="{IMPORTANT_LINKS['ACCA Exemptions Calculator']}" target="_blank">ACCA Exemptions Calculator</a> 查询官方可能免考结果，并保留截图或记录。
            </div>
            """,
            unsafe_allow_html=True,
        )

    if "estimated_exemptions" in st.session_state:
        st.markdown("**当前已保存的预估免考：** " + " ".join([f"`{x}`" for x in st.session_state["estimated_exemptions"]]))


# =============================
# Tab 2: Personalized roadmap
# =============================
with tab2:
    st.subheader("② 个性化 ACCA 考试路线图")
    st.write("不同职业目标，对 ACCA 科目的优先级不同。请选择你的目标方向，系统会生成一条更贴近职业发展的考试路线。")

    col1, col2 = st.columns([0.9, 1.1])
    with col1:
        career_goal = st.radio("选择职业目标", list(CAREER_ROADMAPS.keys()), horizontal=False)
        all_papers = [paper[0] for papers in EXAM_STRUCTURE.values() for paper in papers]
        default_exemptions = st.session_state.get("estimated_exemptions", [])
        exemptions = st.multiselect("已免考 / 可能免考科目", all_papers, default=default_exemptions)
        st.markdown("<span class='gray-small'>你可以先在 Tab 1 做免考预估，也可以在这里手动选择。</span>", unsafe_allow_html=True)

    with col2:
        roadmap = CAREER_ROADMAPS[career_goal]
        st.markdown(
            f"""
            <div class="card">
                <span class="red-pill">{career_goal}</span>
                <h3>{roadmap['tagline']}</h3>
                <p><b>目标岗位：</b>{roadmap['target_roles']}</p>
                <p><b>关键科目：</b>{render_papers(roadmap['key_papers'])}</p>
            </div>
            """,
            unsafe_allow_html=True,
        )

    st.markdown("### 推荐路线")
    for stage_title, papers, reason in roadmap["stages"]:
        remaining = [p for p in papers if p not in exemptions]
        skipped = [p for p in papers if p in exemptions]
        with st.expander(stage_title, expanded=True):
            st.markdown(f"**建议准备：** {render_papers(remaining)}", unsafe_allow_html=True)
            if skipped:
                st.markdown(f"**可能已免考，可跳过：** {render_papers(skipped)}", unsafe_allow_html=True)
            st.write(reason)

    st.markdown("### AI 个性化解释 Demo（可未来接入 DeepSeek / DeepC）")
    st.info(ai_style_summary(career_goal, exemptions))


# =============================
# Tab 3: General exam info
# =============================
with tab3:
    st.subheader("③ ACCA 考试总览")

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("主要考季", "4 次 / 年", "3月、6月、9月、12月")
    c2.metric("on-demand CBE", "BT / MA / FA", "部分 LW 版本")
    c3.metric("季考出分", "约 6 周", "以官网为准")
    c4.metric("年费", "1月1日", "通常通过 myACCA 支付")

    st.markdown("### 3.1 ACCA 科目结构")
    exam_df = get_exam_dataframe()
    st.dataframe(exam_df, use_container_width=True, hide_index=True)

    st.markdown("### 3.2 一年考试时间线（大致月份版）")
    st.dataframe(EXAM_SESSIONS, use_container_width=True, hide_index=True)

    st.markdown(
        f"""
        <div class="soft-card">
        <b>Important Dates：</b><a href="{IMPORTANT_LINKS['ACCA Important Dates']}" target="_blank">{IMPORTANT_LINKS['ACCA Important Dates']}</a><br>
        <b>Exam Timetables：</b><a href="{IMPORTANT_LINKS['ACCA Exam Timetables']}" target="_blank">{IMPORTANT_LINKS['ACCA Exam Timetables']}</a>
        </div>
        """,
        unsafe_allow_html=True,
    )


# =============================
# Tab 4: Events / webinars
# =============================
with tab4:
    st.subheader("④ ACCA 讲座资讯 / Webinars & Events")
    st.write("这里可以展示 ACCA 官方公开页面中的 webinar、event、learning 资源。Demo 默认展示内置示例；如果运行环境允许联网，可以点击按钮尝试实时抓取。")

    col1, col2 = st.columns([1, 1])
    with col1:
        topic_filter = st.selectbox("筛选主题", ["全部", "Exam Support", "ESG", "Career", "Official Update"])
    with col2:
        live_fetch = st.button("🌐 尝试抓取 ACCA 官方公开页面（可选）")

    if live_fetch:
        events, fetch_note = fetch_public_acca_titles()
        st.info(fetch_note)
    else:
        events = MOCK_EVENTS
        st.info("当前显示内置示例数据。正式版建议每天定时抓取并缓存，避免频繁请求官网。")

    if topic_filter != "全部":
        events = [event for event in events if event.get("topic") == topic_filter]

    if not events:
        st.warning("当前筛选条件下暂无内容。")

    for event in events:
        st.markdown(
            f"""
            <div class="card">
                <span class="red-pill">{event.get('topic', 'Update')}</span>
                <h3>{event.get('title', 'Untitled')}</h3>
                <p><b>来源：</b>{event.get('source', 'ACCA')} ｜ <b>时间：</b>{event.get('date', '滚动更新')}</p>
                <p>{event.get('why', '')}</p>
                <a href="{event.get('link', '#')}" target="_blank">打开官方链接 →</a>
            </div>
            """,
            unsafe_allow_html=True,
        )

    st.markdown(
        """
        <div class="warning-box">
        <b>合规提醒：</b>正式版建议只抓取 ACCA 官方公开页面；不要抓取 myACCA 登录后内容；保留来源链接；低频更新；所有活动时间以官网为准。
        </div>
        """,
        unsafe_allow_html=True,
    )


st.markdown("---")
st.caption("© ACCA PathFinder Demo｜Student project prototype. This tool is not an official ACCA product. Official information should be checked on ACCA websites and myACCA.")
