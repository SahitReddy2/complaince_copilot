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

from dotenv import load_dotenv
import psycopg2
from openai import OpenAI

# ───────────────────────────  SETUP  ────────────────────────────

def get_db_connection():
    """Get database connection."""
    load_dotenv()
    return psycopg2.connect(
        host=os.getenv("PG_HOST"),
        port=int(os.getenv("PG_PORT", 5432)),
        dbname=os.getenv("PG_DB"),
        user=os.getenv("PG_USER"),
        password=os.getenv("PG_PASSWORD"),
        sslmode="require"
    )

def get_openai_client():
    """Get OpenAI client."""
    load_dotenv()
    return OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

def embed_query(client: OpenAI, query: str) -> List[float]:
    """Create embedding for query."""
    resp = client.embeddings.create(
        model="text-embedding-3-small",
        input=query,
    )
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
) -> Dict:

    claim_queries = []
    if claims:
        claims_text = "; ".join(claims)
        claim_queries = [
            f"{law_category} claims: {claims_text}",
            f"{law_category} marketing language: {claims_text}",
            f"{law_category} prohibitied claims",
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
            f"{law_category} banned ingredients",
            *[f"{law_category} {ingredient}" for ingredient in ingredients if ingredient.lower() in ['benzene', 'formaldehyde', 'lead', 'mercury', 'arsenic', 'toluene']],
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

    if not ingredients:
        prompt = f"""You are a regulatory compliance expert analyzing **marketing claims** against {law_name}.

REGULATORY CONTEXT:
{context}

CLAIMS TO ANALYZE:
{claims_text}

INSTRUCTIONS:
1. Identify marketing claims that violate {law_name}
2. Look for misleading language, unsubstantiated effects, or restricted phrasing
3. Flag any health-related claims that imply physiological changes without FDA approval
4. Only report actual violations backed by excerpts
5. Ignore ingredients entirely
6. Assign a severity rating ( high, medium, or low) based on regulatory scrutiny
7. Return a 'severities' array matching the order of the 'issues' array.

High-risk claims include:
    - Medical/therapeutic claims
    - Drug-like claims
    - Unsubstantiated superlatives
    - Disease prevention claims
    - Structure/function claims
    
    Medium-risk claims include:
    - Efficacy claims without proof
    - Anti-aging claims
    - Specific percentage improvements
    - "Clinical" or "dermatologist" references
    
    Low-risk claims include:
    - Basic function descriptions
    - Ingredient listings
    - Texture/sensory descriptions

Return ONLY a JSON object:
{{
"law": "{law_name}",
"compliant": true or false,
"issues": ["specific issue 1", "specific issue 2"],
"fixes": ["specific fix 1", "specific fix 2"],
"confidence": 0.0 to 1.0,
"compliance_score": 0 to 100,
"severities": ["critical", "high", "medium", "low"]
}}"""
    else:
        prompt = f"""You are a regulatory compliance expert analyzing cosmetic ingredients against {law_name}.

REGULATORY CONTEXT:
{context}

INGREDIENTS TO ANALYZE:
{ingredient_list}

INSTRUCTIONS:
1. Review each ingredient against the regulatory excerpts above
2. Look for explicit prohibitions, restrictions, concentration limits, or labeling requirements  
3. Consider chemical synonyms and alternate names
4. Only flag violations where there's clear regulatory support
5. If the ingredient is not explicitly mentioned or discussed in the regulatory excerpts, assume it is compliant. Do not infer non-compliance from absence.
6. Assign a severity rating (critical, high, medium, or low) based on regulatory scrutiny
7. Return a 'severities' array matching the order of the 'issues' array.

Severity rating guidelines:
    - High: Known allergens or restricted substances (fragrance, parfum, limonene, parabens, etc.)
    - Medium: Ingredients flagged for irritation or controversial (preservatives, some surfactants)
    - Low: Safe or common ingredients (moisturizers, thickeners, emulsifiers)


Return ONLY a JSON object:
{{
"law": "{law_name}",
"compliant": true or false,
"issues": ["specific issue 1", "specific issue 2"],
"fixes": ["specific fix 1", "specific fix 2"],
"confidence": 0.0 to 1.0,
"compliance_score": 0 to 100,
"severities": ["critical", "high", "medium", "low"]
}}"""

    try:
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
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

        if not ingredients and original_issues:
            filtered_issues = []
            filtered_severities = []
            for i, issue in enumerate(original_issues):
                if not is_likely_ingredient_issue(issue):
                    filtered_issues.append(issue)
                    filtered_severities.append(severities[i])

            if filtered_issues:
                result["issues"] = filtered_issues
                result["severities"] = filtered_severities
            else:
                result["issues"] = original_issues
                result["severities"] = severities


        result["compliant"] = len(result["issues"]) == 0
        severities = result.get("severities", ["low"] * len(result["issues"]))

        issue_details = []
        for i, issue in enumerate(result["issues"]):
            severity = severities[i] if i < len(severities) else "low"

            #Auto downgrade severity for vague or soft marketing (lessening LLM aggresiveness with default phrases)
            if(
                "dermatologist recommended" in issue.lower()
                or "clinically tested" in issue.lower()
                or "gentle formula" in issue.lower()
            ):
                if severity == "high":
                    severity == "critical"

            issue_details.append({
                "law": law_name,
                "reason": issue,
                "confidence": result.get("confidence", 0.0),
                "severity": severity
            })

            

        return {
            "law": law_name,
            "compliant": result["compliant"],
            "confidence": result.get("confidence", 0.0),
            "compliance_score": result.get("compliance_score", 50),
            "issues": issue_details,
            "fixes": result.get("fixes", []),
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


def evaluate_product_direct(ingredients: List[str], claims: List[str] = None) -> Dict:
    """
    Run compliance checks using direct database access.
    """
    print(f" EVALUATING INGREDIENTS: {', '.join(ingredients)}")
    
    try:
        conn = get_db_connection()
        client = get_openai_client()
        print(" Connected to database and OpenAI")
    except Exception as e:
        print(f" Setup failed: {e}")
        return {"non_compliant": [{"law": "System Error", "reason": f"Setup failed: {e}"}]}
    
    # Define law frameworks
    law_frameworks = [
        {"category": "prop65", "name": "California Prop 65"},
        {"category": "mocra", "name": "MoCRA 2022"},
        {"category": "cosmetics", "name": "Federal Cosmetics Act"},
        {"category": "color_additives", "name": "FDA Color Additive Regulations"},
        {"category": "ftc_health", "name": "FTC Health Product Guidelines"},
    ]
    
    non_compliant_results = []
    
    for law in law_frameworks:
        try:
            result = check_single_law_direct(
                conn, client, ingredients, claims or [],
                law["category"], law["name"]
            )
            
            if not result.get("compliant", True):
                issues = result.get("issues", [])
                print(f"  ⚠️ Issues detected for {law['name']}: {issues}")

                for issue in issues:
                    if isinstance(issue, dict):
                        non_compliant_results.append({
                            "law": issue.get("law", law["name"]),
                            "reason": issue.get("reason", "Regulatory violation"),
                            "confidence": issue.get("confidence", 0.0),
                            "severity": issue.get("severity", "low")
                        })
                    else:
                        # fallback for string-based issues (older or malformed output)
                        non_compliant_results.append({
                            "law": law["name"],
                            "reason": issue,
                            "confidence": result.get("confidence", 0.0),
                            "severity": "low"  # or guess default
                        })
                            
        except Exception as e:
            print(f" Error checking {law['name']}: {e}")
            non_compliant_results.append({
                "law": law["name"],
                "reason": f"Analysis error: {e}"
            })
    
    conn.close()
    
    # Summary
    print(f"\n COMPLIANCE SUMMARY:")
    print(f"   Non-compliant: {len(non_compliant_results)}")
    print(f"   Compliant: {len(law_frameworks) - len(non_compliant_results)}")
    
    return {"non_compliant": non_compliant_results}

# ───────────────────────────  CLI ENTRY  ─────────────────────────

def main() -> None:
    if len(sys.argv) < 2:
        print("Usage: python3 simple_compliance.py '{\"ingredients\": [\"benzene\"]}'", file=sys.stderr)
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

    if isinstance(payload, dict):
        ingredients = payload.get("ingredients", [])
        claims = payload.get("claims", [])
        
        if not ingredients and not claims:
            print("Must provide at least 'ingredients' or 'claims' for compliance checking.", file=sys.stderr)
            sys.exit(1)
    else:
        print("JSON must be a dictionary with optional 'ingredients' and/or 'claims' keys", file=sys.stderr)
        sys.exit(1)

    result = evaluate_product_direct(ingredients, claims)
    # print(f"\n FINAL RESULT:")
    print(json.dumps(result))

if __name__ == "__main__":
    main()