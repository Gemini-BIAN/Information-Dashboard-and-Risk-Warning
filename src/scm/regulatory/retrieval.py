"""Local version-scoped lexical BM25 baseline; no embeddings, LLM or legal conclusions."""

import json
import math
import re
from collections import Counter

from sqlalchemy import select

from scm.regulatory.models import RegulationChunk, RegulationDocument
from scm.regulatory.parsing import tokenize
from scm.regulatory.storage import checked_path

GLOSSARY = {
    "碳足迹": ["carbon", "footprint"],
    "电池": ["battery", "batteries"],
    "危险品": ["dangerous", "goods"],
    "化学品": ["chemical", "chemicals"],
    "供应商": ["supplier", "suppliers"],
    "分类": ["classification"],
    "标签": ["labelling", "label"],
    "安全数据表": ["safety", "data", "sheet"],
    "运输": ["transport", "carriage"],
}
STOP = {
    "the",
    "a",
    "an",
    "is",
    "are",
    "what",
    "which",
    "and",
    "or",
    "of",
    "to",
    "in",
    "for",
    "requirements",
    "requirement",
    "article",
    "annex",
}


def retrieve(session, query, document_id, root, include_test=False, limit=5):
    """Explicit document_id is mandatory: do not silently choose latest or merge versions."""
    row = session.get(RegulationDocument, document_id)
    if not row or row.download_status != "downloaded" or row.parse_status not in ["parsed", "needs_review"]:
        return []
    if row.verification_type != "LIVE_HTTP" and not include_test:
        return []
    try:
        checked_path(row, root)
    except ValueError:
        return []
    meta = json.loads(row.metadata_json)
    if meta["language"] != "EN":
        return []
    if any(
        name in query.lower() and name not in (meta["title"] + " " + meta["regulation_number"]).lower()
        for name in ["reach", "clp"]
    ):
        return []
    laws = re.findall(r"\b(?:19|20)\d{2}/\d+\b", query)
    if laws and any(law not in meta["regulation_number"] for law in laws):
        return []
    terms = set(tokenize(query)) - STOP
    focus = []
    for zh, en in GLOSSARY.items():
        if zh in query:
            terms.update(en)
        if zh == "碳足迹" and zh in query:
            focus = ["carbon", "footprint"]
    if re.search(r"iso[ -]?tank", query, re.I):
        focus = ["iso", "tank"]
    if not terms:
        return []
    match = re.search(r"(?:article\s*|第\s*)(\d+[a-z]?)\s*(?:条)?", query, re.I)
    unit = match.group(1).lower() if match else None
    annex = re.search(r"(?:annex\s*|附件\s*)([IVXLCDM]+|\d+)", query, re.I)
    annex_label = annex.group(1).upper() if annex else None
    if annex_label and not unit:
        terms.add("annex")

    chunks = list(session.scalars(select(RegulationChunk).where(RegulationChunk.document_id == document_id)))
    vectors = {c.id: Counter(json.loads(c.terms_json)) for c in chunks}
    avg = sum(sum(v.values()) for v in vectors.values()) / max(len(vectors), 1)
    results = []
    for chunk in chunks:
        if unit and (chunk.unit_type != "article" or chunk.unit_label.lower() != unit):
            continue
        if annex_label and (chunk.unit_type != "annex" or chunk.unit_label.upper() != annex_label):
            continue
        tf = vectors[chunk.id]
        if focus and not all(tf[t] for t in focus):
            continue
        score = 0
        for term in terms:
            if not tf[term]:
                continue
            df = sum(bool(v[term]) for v in vectors.values())
            idf = math.log(1 + (len(chunks) - df + 0.5) / (df + 0.5))
            score += idf * tf[term] * 2.2 / (tf[term] + 1.2 * (0.25 + 0.75 * sum(tf.values()) / max(avg, 1)))
        if score <= 0:
            continue
        results.append(
            {
                "chunk_id": chunk.id,
                "document_id": document_id,
                "celex": meta["celex"],
                "eli": meta.get("eli"),
                "regulation_number": meta["regulation_number"],
                "version_kind": meta["version_kind"],
                "version_date": meta.get("version_date") or meta.get("publication_date"),
                "unit_type": chunk.unit_type,
                "unit_label": chunk.unit_label,
                "quote": chunk.text,
                "locator": chunk.locator,
                "page_start": chunk.page_start,
                "page_end": chunk.page_end,
                "official_url": meta["official_url"],
                "download_url": meta["download_url"],
                "citation_url": meta["download_url"]
                + (f"#page={chunk.page_start}" if meta["format"] == "pdf" and chunk.page_start else ""),
                "language": meta["language"],
                "source_file": row.local_path,
                "source_sha256": row.sha256,
                "legal_status": meta["legal_status"],
                "verification_status": meta["verification_status"],
                "verification_type": row.verification_type,
                "quality_flags": json.loads(chunk.quality_json),
                "score": round(score, 6),
            }
        )
    return sorted(results, key=lambda x: (-x["score"], x["chunk_id"]))[:limit]


def answer(session, question, document_id, root, include_test=False):
    evidence = retrieve(session, question, document_id, root, include_test=include_test)
    document = session.get(RegulationDocument, document_id)
    meta = json.loads(document.metadata_json) if document else {}
    # No unsourced answer about present applicability from a historical original snapshot.
    current_question = any(word in question for word in ["目前", "当前", "现行", "截至"])
    if current_question:
        return {
            "mode": "retrieval_only_no_llm",
            "evidence": [],
            "answer_zh": "证据不足：尚未完成修订链与条款适用日期核验，不能把原始或整合文本当作当前适用结论。",
            "direct_requirements": "需要适用日期与完整修订证据。",
            "indirect_electrolyte_impact": "待核实，不作确定性推断。",
        }

    return {
        "mode": "retrieval_only_no_llm",
        "evidence": evidence,
        "answer_zh": "以下是指定版本的检索原文摘录，不是AI法律分析；条款语义和适用日期仍待核实。"
        + (
            " 整合文本仅作阅读参考，不是独立法源。"
            if meta.get("version_kind") == "consolidated"
            else " 原始OJ快照不等于当前已修订文本。"
        )
        if evidence
        else "证据不足：知识库未覆盖或没有合格原文。不能依据模型常识生成法律结论。",
        "direct_requirements": "仅提供下列原文证据，不自动确认法规对特定主体的直接义务。",
        "indirect_electrolyte_impact": "对电解液企业的间接影响尚无充分证据，需核实产品、主体、运输方式和具体条款。",
    }
