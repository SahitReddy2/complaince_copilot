#!/usr/bin/env python3
"""
Simple compliance checker that works directly with the database,
bypassing LlamaIndex vector store issues.
"""

import sys
sys.stdout.reconfigure(encoding='utf-8')

import os
import json
import re
from typing import List, Dict, Tuple

# allow imports from project root  
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from openai import OpenAI

from backend.config import get_connection, get_ollama_client, OLLAMA_CHAT_MODEL, OLLAMA_EMBED_MODEL
from backend.industry_config import load_industry

# ───────────────────────────  SETUP  ────────────────────────────

def get_db_connection():
    """Get database connection from central config."""
    return get_connection()


def get_openai_client():
    """Get Ollama client from central config."""
    return get_ollama_client()


def embed_query(client: OpenAI, query: str) -> List[float]:
    """Create embedding for query."""
    resp = client.embeddings.create(model=OLLAMA_EMBED_MODEL, input=query)
    return resp.data[0].embedding

def cosine_similarity_sql(embedding: List[float]) -> str:
    """Generate SQL for cosine similarity."""
    embedding_str = "[" + ",".join(map(str, embedding)) + "]"
    return f"1 - (embedding <=> '{embedding_str}')"

# ────────────────────────  DIRECT RETRIEVAL  ─────────────────────

def retrieve_relevant_chunks(
    conn, 
    client: OpenAI, 
    query: str, 
    category: str = None, 
    limit: int = 10
) -> List[Tuple]:
    """
    Retrieve relevant chunks using direct database query with cosine similarity.
    """
    
    try:
        # Create query embedding
        query_embedding = embed_query(client, query)
        
        # Build SQL query
        similarity_expr = cosine_similarity_sql(query_embedding)
        
        base_query = f"""
            SELECT 
                text,
                metadata,
                document_id,
                {similarity_expr} as similarity
            FROM law_chunks 
            WHERE embedding IS NOT NULL
        """
        
        params = []
        
        # Add category filter if specified
        if category:
            base_query += " AND metadata->>'category' = %s"
            params.append(category)
        
        # Add similarity threshold and ordering
        base_query += f"""
            AND {similarity_expr} > 0.3
            ORDER BY similarity DESC
            LIMIT %s
        """
        params.append(limit)
        
        with conn.cursor() as cur:
            cur.execute(base_query, params)
            results = cur.fetchall()
            
            
            
            # Show top result if any
            if results:
                top_result = results[0]
                text_preview = top_result[0][:100].replace('\n', ' ')
                similarity = top_result[3]
            
            return results
            
    except Exception as e:
        print(f"    Retrieval failed: {e}")
        return []

def extract_json_from_response(text: str) -> Dict:
    """Extract JSON from LLM response."""
    if not text:
        raise ValueError("No response text to parse.")
    
    text = text.strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        # Try to find JSON block
        print("❌ JSON parsing failed.")
        print("Offending response:\n", text)
        raise  # So you catch it in dev

        # match = re.search(r'\{.*\}', text, re.DOTALL)
        # if match:
        #     try:
        #         return json.loads(match.group(0))
        #     except json.JSONDecodeError:
        #         pass
        
        # # Return default structure
        # return {
        #     "law": "Unknown",
        #     "compliant": True,
        #     "issues": [],
        #     "fixes": [],
        #     "confidence": 0.0,
        #     "compliance_score": 50
        # }

#Hallucinating Fix
def is_likely_ingredient_issue(text: str) -> bool:
    ingredient_keywords = ["ingredient", "listed in", "concentration", "formulation", "chemical", "compound"]
    chemical_pattern = r"\b([A-Z][a-z]?[a-z]?\s?[A-Za-z0-9()\-,]*)\b"

    return any(kw in text.lower() for kw in ingredient_keywords) or re.search(chemical_pattern, text)

# ────────────────────────  COMPLIANCE CHECK  ─────────────────────

def check_single_law_direct(
    conn,
    client: OpenAI,
    ingredients: List[str],
    claims: List[str],
    law_category: str,
    law_name: str,
    industry_cfg: Dict = None,
) -> Dict:

    industry_cfg = industry_cfg or load_industry("cosmetics")
    component_label = industry_cfg.get("component_label", "ingredients")
    component_singular = industry_cfg.get("component_singular", "ingredient")
    component_severity_guide = industry_cfg.get("component_severity_guide", "")
    claim_severity_guide = industry_cfg.get("claim_severity_guide", "")
    high_risk = [c.lower() for c in industry_cfg.get("high_risk_components", [])]

    claim_queries = []
    if claims:
        claims_text = "; ".join(claims)
        claim_queries = [
            f"{law_category} claims: {claims_text}",
            f"{law_category} marketing language: {claims_text}",
            f"{law_category} prohibited claims",
        ]

    queries = (
        [
            f"{law_category} prohibited claims",
            f"{law_category} false advertising",
            f"{law_category} labeling violations",
            *claim_queries,
        ]
        if not ingredients
        else [
            f"{law_category} " + " ".join(ingredients),
            f"{law_category} prohibited substances",
            f"{law_category} banned {component_label}",
            *[f"{law_category} {ing}" for ing in ingredients if ing.lower() in high_risk],
            *claim_queries,
        ]
    )

    all_chunks = []
    seen_doc_ids = set()

    for query in queries[:4]:
        chunks = retrieve_relevant_chunks(conn, client, query, law_category, limit=5)
        for chunk_data in chunks:
            doc_id = chunk_data[2]
            if doc_id not in seen_doc_ids:
                all_chunks.append(chunk_data)
                seen_doc_ids.add(doc_id)
                if len(all_chunks) >= 8:
                    break
        if len(all_chunks) >= 8:
            break

    if not all_chunks:
        print(f"     No relevant chunks found for {law_name}")
        return {
            "law": law_name,
            "compliant": True,
            "issues": [],
            "fixes": [],
            "confidence": 0.1,
            "compliance_score": 50,
            "note": "No relevant regulatory content found",
        }

    context = "\n".join(
        f"--- REGULATORY EXCERPT {i+1} (similarity: {similarity:.3f}) ---\n{text}\n"
        for i, (text, metadata, doc_id, similarity) in enumerate(all_chunks)
    )

    ingredient_list = ", ".join(ingredients)
    claims_text = "; ".join(claims)

    industry_name = industry_cfg.get("display_name", "the product")

    if not ingredients:
        prompt = f"""You are a regulatory compliance expert analyzing **marketing claims** for {industry_name} against {law_name}.

REGULATORY CONTEXT:
{context}

CLAIMS TO ANALYZE:
{claims_text}

INSTRUCTIONS:
1. Identify marketing claims that violate {law_name}
2. Look for misleading language, unsubstantiated effects, or restricted phrasing
3. Only report actual violations backed by excerpts
4. Ignore {component_label} entirely
5. Assign a severity rating (critical, high, medium, or low) based on regulatory scrutiny
6. For each issue, return a short "evidence" quote from the regulatory excerpts that supports the finding
7. Return arrays 'issues', 'severities', and 'evidence' all in matching order

CLAIM SEVERITY GUIDE:
{claim_severity_guide}

Return ONLY a JSON object:
{{
"law": "{law_name}",
"compliant": true or false,
"issues": ["specific issue 1", "specific issue 2"],
"fixes": ["specific fix 1", "specific fix 2"],
"evidence": ["short quote from excerpt supporting issue 1", "short quote for issue 2"],
"confidence": 0.0 to 1.0,
"compliance_score": 0 to 100,
"severities": ["critical", "high", "medium", "low"]
}}"""
    else:
        prompt = f"""You are a regulatory compliance expert analyzing {industry_name} {component_label} against {law_name}.

REGULATORY CONTEXT:
{context}

{component_label.upper()} TO ANALYZE:
{ingredient_list}

INSTRUCTIONS:
1. Review each {component_singular} against the regulatory excerpts above
2. Look for explicit prohibitions, restrictions, concentration limits, or labeling requirements
3. Consider chemical synonyms and alternate names
4. Only flag violations where there's clear regulatory support
5. If a {component_singular} is not explicitly mentioned in the excerpts, assume it is compliant. Do not infer non-compliance from absence.
6. Assign a severity rating (critical, high, medium, or low) based on regulatory scrutiny
7. For each issue, return a short "evidence" quote from the regulatory excerpts that supports the finding
8. Return arrays 'issues', 'severities', and 'evidence' all in matching order

COMPONENT SEVERITY GUIDE:
{component_severity_guide}

Return ONLY a JSON object:
{{
"law": "{law_name}",
"compliant": true or false,
"issues": ["specific issue 1", "specific issue 2"],
"fixes": ["specific fix 1", "specific fix 2"],
"evidence": ["short quote from excerpt supporting issue 1", "short quote for issue 2"],
"confidence": 0.0 to 1.0,
"compliance_score": 0 to 100,
"severities": ["critical", "high", "medium", "low"]
}}"""

    try:
        response = client.chat.completions.create(
            model=OLLAMA_CHAT_MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.1,
            max_tokens=1000,
        )

        response_text = response.choices[0].message.content
        if not response_text:
            raise ValueError("LLM response content is None")

        result = extract_json_from_response(response_text)

        # ─── Filter hallucinated ingredient issues before building issue dicts ───
        original_issues = result.get("issues", [])
        severities = result.get("severities", ["low"] * len(original_issues))
        evidence_quotes = result.get("evidence", [""] * len(original_issues))

        if not ingredients and original_issues:
            filtered_issues, filtered_severities, filtered_evidence = [], [], []
            for i, issue in enumerate(original_issues):
                if not is_likely_ingredient_issue(issue):
                    filtered_issues.append(issue)
                    filtered_severities.append(severities[i] if i < len(severities) else "low")
                    filtered_evidence.append(evidence_quotes[i] if i < len(evidence_quotes) else "")

            if filtered_issues:
                result["issues"] = filtered_issues
                result["severities"] = filtered_severities
                evidence_quotes = filtered_evidence
            else:
                result["issues"] = original_issues
                result["severities"] = severities


        result["compliant"] = len(result["issues"]) == 0
        severities = result.get("severities", ["low"] * len(result["issues"]))

        # Build top citation sources from retrieved chunks (top 3 by similarity)
        top_citations = [
            {
                "source_doc_id": doc_id,
                "source": (metadata or {}).get("source", "") if isinstance(metadata, dict) else "",
                "similarity": round(float(similarity), 3),
                "excerpt": text[:300].strip().replace("\n", " "),
            }
            for text, metadata, doc_id, similarity in all_chunks[:3]
        ]

        issue_details = []
        for i, issue in enumerate(result["issues"]):
            severity = severities[i] if i < len(severities) else "low"
            evidence = evidence_quotes[i] if i < len(evidence_quotes) else ""

            # Auto-downgrade severity for vague marketing copy
            if (
                "dermatologist recommended" in issue.lower()
                or "clinically tested" in issue.lower()
                or "gentle formula" in issue.lower()
            ):
                if severity == "high":
                    severity = "medium"

            issue_details.append({
                "law": law_name,
                "reason": issue,
                "confidence": result.get("confidence", 0.0),
                "severity": severity,
                "evidence": evidence,
                "citations": top_citations,
            })

        return {
            "law": law_name,
            "compliant": result["compliant"],
            "confidence": result.get("confidence", 0.0),
            "compliance_score": result.get("compliance_score", 50),
            "issues": issue_details,
            "fixes": result.get("fixes", []),
            "citations": top_citations,
        }

    except Exception as e:
        print(f"    LLM analysis failed: {e}")
        return {
            "law": law_name,
            "compliant": True,
            "issues": [],
            "fixes": [],
            "confidence": 0.0,
            "compliance_score": 0,
            "error": str(e)
        }


def evaluate_product_direct(
    ingredients: List[str],
    claims: List[str] = None,
    industry: str = "cosmetics",
    jurisdictions: List[str] = None,
) -> Dict:
    """
    Run compliance checks using direct database access.

    Args:
        ingredients: Component names extracted from the label.
        claims: Marketing claims extracted from the label.
        industry: Industry config name (cosmetics, food, supplements, pharma_otc).
        jurisdictions: Filter law frameworks to these jurisdictions (e.g., ["US", "EU"]).
                       If None, all jurisdictions in the industry config are checked.
    """
    print(f" EVALUATING [{industry}] {', '.join(ingredients) if ingredients else 'claims-only'}")

    try:
        industry_cfg = load_industry(industry)
    except FileNotFoundError as e:
        return {"non_compliant": [{"law": "Config Error", "reason": str(e)}]}

    try:
        conn = get_db_connection()
        client = get_openai_client()
        print(" Connected to database and LLM")
    except Exception as e:
        print(f" Setup failed: {e}")
        return {"non_compliant": [{"law": "System Error", "reason": f"Setup failed: {e}"}]}

    # Load law frameworks from industry config, optionally filtered by jurisdiction
    all_frameworks = industry_cfg.get("law_frameworks", [])
    if jurisdictions:
        law_frameworks = [f for f in all_frameworks if f.get("jurisdiction") in jurisdictions]
    else:
        law_frameworks = all_frameworks

    non_compliant_results = []
    by_jurisdiction: Dict[str, List[Dict]] = {}

    for law in law_frameworks:
        try:
            result = check_single_law_direct(
                conn, client, ingredients, claims or [],
                law["category"], law["name"],
                industry_cfg=industry_cfg,
            )

            jurisdiction = law.get("jurisdiction", "US")
            by_jurisdiction.setdefault(jurisdiction, [])

            if not result.get("compliant", True):
                issues = result.get("issues", [])
                print(f"  ⚠️ Issues detected for {law['name']}: {len(issues)} issue(s)")

                for issue in issues:
                    record = {
                        "law": issue.get("law", law["name"]) if isinstance(issue, dict) else law["name"],
                        "jurisdiction": jurisdiction,
                        "reason": issue.get("reason", "Regulatory violation") if isinstance(issue, dict) else issue,
                        "confidence": issue.get("confidence", result.get("confidence", 0.0)) if isinstance(issue, dict) else result.get("confidence", 0.0),
                        "severity": issue.get("severity", "low") if isinstance(issue, dict) else "low",
                        "evidence": issue.get("evidence", "") if isinstance(issue, dict) else "",
                        "citations": issue.get("citations", []) if isinstance(issue, dict) else result.get("citations", []),
                    }
                    non_compliant_results.append(record)
                    by_jurisdiction[jurisdiction].append(record)

        except Exception as e:
            print(f" Error checking {law['name']}: {e}")
            non_compliant_results.append({
                "law": law["name"],
                "jurisdiction": law.get("jurisdiction", "US"),
                "reason": f"Analysis error: {e}"
            })

    conn.close()

    print(f"\n COMPLIANCE SUMMARY:")
    print(f"   Industry: {industry_cfg.get('display_name', industry)}")
    print(f"   Frameworks checked: {len(law_frameworks)}")
    print(f"   Non-compliant findings: {len(non_compliant_results)}")

    return {
        "industry": industry,
        "non_compliant": non_compliant_results,
        "by_jurisdiction": by_jurisdiction,
    }

# ───────────────────────────  CLI ENTRY  ─────────────────────────

def main() -> None:
    if len(sys.argv) < 2:
        print(
            'Usage: python -m backend.check_compliance \'{"industry":"cosmetics","ingredients":["benzene"],"jurisdictions":["US"]}\'',
            file=sys.stderr,
        )
        sys.exit(1)

    arg = sys.argv[1]

    if arg.endswith(".json") and os.path.isfile(arg):
        with open(arg, "r") as f:
            payload = json.load(f)
    else:
        try:
            payload = json.loads(sys.argv[1])
        except json.JSONDecodeError:
            print("Input must be valid JSON or path to JSON file", file=sys.stderr)
            sys.exit(1)

    if not isinstance(payload, dict):
        print("JSON must be a dictionary", file=sys.stderr)
        sys.exit(1)

    ingredients = payload.get("ingredients", [])
    claims = payload.get("claims", [])
    industry = payload.get("industry", "cosmetics")
    jurisdictions = payload.get("jurisdictions")  # None = all

    if not ingredients and not claims:
        print("Must provide at least 'ingredients' or 'claims'", file=sys.stderr)
        sys.exit(1)

    result = evaluate_product_direct(ingredients, claims, industry=industry, jurisdictions=jurisdictions)
    print(json.dumps(result))

if __name__ == "__main__":
    main()