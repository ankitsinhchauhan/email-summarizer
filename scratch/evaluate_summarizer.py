import json
import re
import os
import sys

# Ensure repository root is on sys.path
sys.path.insert(0, os.path.abspath("."))

from collections import Counter
from src.summarizer import summarize_text
from src.pdf_handler import extract_pdf_text, summarize_pdf_text, PDFError

def tokenize(text: str) -> list[str]:
    """Tokenize lowercase alphanumeric words for standard n-gram metrics."""
    return re.findall(r"\b[a-z0-9]+\b", text.lower())

def get_ngrams(tokens: list[str], n: int) -> list[tuple]:
    return [tuple(tokens[i : i + n]) for i in range(len(tokens) - n + 1)]

def rouge_n(candidate_tokens: list[str], reference_tokens: list[str], n: int) -> dict:
    c_ngrams = get_ngrams(candidate_tokens, n)
    r_ngrams = get_ngrams(reference_tokens, n)
    if not c_ngrams or not r_ngrams:
        return {"precision": 0.0, "recall": 0.0, "f1": 0.0}

    c_counts = Counter(c_ngrams)
    r_counts = Counter(r_ngrams)

    overlap = 0
    for gram, count in c_counts.items():
        overlap += min(count, r_counts.get(gram, 0))

    precision = overlap / len(c_ngrams)
    recall = overlap / len(r_ngrams)
    f1 = (2 * precision * recall) / (precision + recall) if (precision + recall) > 0 else 0.0
    return {"precision": round(precision, 4), "recall": round(recall, 4), "f1": round(f1, 4)}

def lcs_length(x: list[str], y: list[str]) -> int:
    m, n = len(x), len(y)
    dp = [[0] * (n + 1) for _ in range(m + 1)]
    for i in range(1, m + 1):
        for j in range(1, n + 1):
            if x[i - 1] == y[j - 1]:
                dp[i][j] = dp[i - 1][j - 1] + 1
            else:
                dp[i][j] = max(dp[i - 1][j], dp[i][j - 1])
    return dp[m][n]

def rouge_l(candidate_tokens: list[str], reference_tokens: list[str]) -> dict:
    if not candidate_tokens or not reference_tokens:
        return {"precision": 0.0, "recall": 0.0, "f1": 0.0}
    lcs = lcs_length(candidate_tokens, reference_tokens)
    precision = lcs / len(candidate_tokens)
    recall = lcs / len(reference_tokens)
    f1 = (2 * precision * recall) / (precision + recall) if (precision + recall) > 0 else 0.0
    return {"precision": round(precision, 4), "recall": round(recall, 4), "f1": round(f1, 4)}

_STOPWORDS = {
    "a", "about", "above", "after", "again", "against", "all", "am", "an", "and",
    "any", "are", "as", "at", "be", "because", "been", "before", "being", "below",
    "between", "both", "but", "by", "for", "from", "further", "had", "has", "have",
    "in", "into", "is", "it", "its", "of", "on", "once", "only", "or", "other",
    "our", "ours", "out", "over", "own", "same", "so", "some", "such", "than",
    "that", "the", "their", "theirs", "them", "then", "there", "these", "they",
    "this", "those", "through", "to", "too", "under", "until", "up", "very", "was",
    "we", "were", "what", "when", "where", "which", "while", "who", "whom", "why",
    "with", "you", "your", "yours"
}

def check_entity_coverage(summary: str, entities_dict: dict) -> dict:
    summary_lower = summary.lower()
    summary_tokens = set(re.findall(r"\b[a-z0-9]+\b", summary_lower))
    coverage = {}
    for cat, items in entities_dict.items():
        if not items:
            continue
        found = []
        for item in items:
            item_lower = item.lower()
            if cat in ("decisions", "action_items"):
                # Semantic / key-token recall for descriptive decisions and action items
                item_tokens = [w for w in re.findall(r"\b[a-z0-9]+\b", item_lower) if w not in _STOPWORDS and len(w) > 2]
                if item_tokens:
                    matched = sum(1 for w in item_tokens if any(w in st or st in w for st in summary_tokens))
                    if matched / len(item_tokens) >= 0.6:
                        found.append(item)
                elif item_lower in summary_lower:
                    found.append(item)
            else:
                # Verbatim presence for exact entities (dates, names, amounts)
                if item_lower in summary_lower:
                    found.append(item)

        coverage[cat] = {
            "total": len(items),
            "found": len(found),
            "items_found": found,
            "items_missed": [item for item in items if item not in found],
            "recall": round(len(found) / len(items), 4) if items else 1.0
        }
    return coverage

def run_evaluation():
    with open("tests/evaluation_dataset.json", "r", encoding="utf-8") as f:
        dataset = json.load(f)

    evaluation_records = []
    
    total_rouge1_f1 = []
    total_rouge2_f1 = []
    total_rougel_f1 = []
    
    cat_entity_stats = {
        "dates_deadlines": {"total": 0, "found": 0},
        "names": {"total": 0, "found": 0},
        "amounts_numbers": {"total": 0, "found": 0},
        "decisions": {"total": 0, "found": 0},
        "action_items": {"total": 0, "found": 0},
    }

    failure_counts = {
        "lead_bias_omission": 0,
        "salutation_noise": 0,
        "length_controls_ignored": 0,
        "multipage_truncation": 0,
        "pdf_extraction_ocr_failure": 0,
        "pdf_extraction_encryption_failure": 0,
        "abbreviation_sentence_split": 0,
    }

    for item in dataset:
        doc_id = item["id"]
        category = item["category"]
        title = item["title"]
        reference = item["reference_summary"]
        text = item.get("text", "")
        entities = item["entities"]

        record = {
            "id": doc_id,
            "category": category,
            "title": title,
            "key_placement": item.get("key_placement"),
            "pdf_type": item.get("pdf_type"),
            "status": "PROCESSED",
            "extraction_error": None,
            "generated_summary": "",
            "summary_word_count": 0,
            "min_max_length_effective": False,
            "rouge": {},
            "entity_coverage": {},
            "failure_tags": []
        }

        # Handling for PDFs
        if category == "pdf":
            pdf_path = item["pdf_path"]
            with open(pdf_path, "rb") as pf:
                pdf_bytes = pf.read()
            try:
                extracted_text = extract_pdf_text(pdf_bytes)
                generated = summarize_pdf_text(extracted_text, 150, 30, summarize_text)
                record["generated_summary"] = generated
            except PDFError as exc:
                record["status"] = "EXTRACTION_FAILURE"
                record["extraction_error"] = str(exc)
                record["generated_summary"] = f"[EXTRACTION FAILED]: {str(exc)}"
                if "scanned" in str(exc).lower() or "no readable text" in str(exc).lower():
                    failure_counts["pdf_extraction_ocr_failure"] += 1
                    record["failure_tags"].append("OCR_REQUIRED")
                elif "encrypted" in str(exc).lower():
                    failure_counts["pdf_extraction_encryption_failure"] += 1
                    record["failure_tags"].append("ENCRYPTED_PDF")
                evaluation_records.append(record)
                continue
        else:
            # Regular text summarization
            generated = summarize_text(text, max_length=150, min_length=30)
            record["generated_summary"] = generated

        # Test length control sensitivity: does setting max_length=50 change output?
        gen_short = summarize_text(text, max_length=50, min_length=10) if text else ""
        if gen_short == generated and len(generated.split()) > 50:
            record["failure_tags"].append("LENGTH_CONTROLS_IGNORED")
            failure_counts["length_controls_ignored"] += 1

        record["summary_word_count"] = len(generated.split())

        # Check abbreviation splits (e.g. Dr., Oct., e.g., i.e.)
        if re.search(r"\b(Dr|Mr|Ms|Jan|Feb|Mar|Apr|Aug|Sept|Oct|Nov|Dec|e\.g|i\.e)\.$", generated.strip()):
            record["failure_tags"].append("ABBREVIATION_SPLIT_ARTIFACT")
            failure_counts["abbreviation_sentence_split"] += 1

        # Check salutation noise (e.g., "Hi Team,", "Dear Alexander,")
        if re.match(r"^(Hi |Hello |Dear |Good morning |Attention )", generated):
            record["failure_tags"].append("SALUTATION_NOISE")
            failure_counts["salutation_noise"] += 1

        # Check multi-page truncation for PDFs (verify page 2 key entities are captured)
        if item.get("pdf_type") == "text_multipage":
            page_2_entities = item.get("entities", {}).get("dates_deadlines", []) + item.get("entities", {}).get("amounts_numbers", [])
            has_page_2_content = any(e.lower() in generated.lower() for e in page_2_entities)
            if not has_page_2_content:
                record["failure_tags"].append("MULTIPAGE_TRUNCATION")
                failure_counts["multipage_truncation"] += 1

        # ROUGE calculation
        cand_tokens = tokenize(generated)
        ref_tokens = tokenize(reference)
        r1 = rouge_n(cand_tokens, ref_tokens, 1)
        r2 = rouge_n(cand_tokens, ref_tokens, 2)
        rl = rouge_l(cand_tokens, ref_tokens)
        record["rouge"] = {"rouge1": r1, "rouge2": r2, "rougeL": rl}
        
        total_rouge1_f1.append(r1["f1"])
        total_rouge2_f1.append(r2["f1"])
        total_rougel_f1.append(rl["f1"])

        # Entity coverage
        cov = check_entity_coverage(generated, entities)
        record["entity_coverage"] = cov
        
        for k, v in cov.items():
            if k in cat_entity_stats:
                cat_entity_stats[k]["total"] += v["total"]
                cat_entity_stats[k]["found"] += v["found"]

        # Tag lead-bias omission if critical action item or deadline was missed
        if cov.get("action_items", {}).get("recall", 1.0) < 0.5 or cov.get("dates_deadlines", {}).get("recall", 1.0) < 0.5:
            if item.get("key_placement") in ("tail", "middle", "page_2"):
                record["failure_tags"].append("LEAD_BIAS_OMISSION")
                failure_counts["lead_bias_omission"] += 1

        evaluation_records.append(record)

    summary_stats = {
        "total_documents_evaluated": len(dataset),
        "successfully_summarized": sum(1 for r in evaluation_records if r["status"] == "PROCESSED"),
        "extraction_failures": sum(1 for r in evaluation_records if r["status"] == "EXTRACTION_FAILURE"),
        "average_rouge1_f1": round(sum(total_rouge1_f1) / len(total_rouge1_f1), 4) if total_rouge1_f1 else 0.0,
        "average_rouge2_f1": round(sum(total_rouge2_f1) / len(total_rouge2_f1), 4) if total_rouge2_f1 else 0.0,
        "average_rougeL_f1": round(sum(total_rougel_f1) / len(total_rougel_f1), 4) if total_rougel_f1 else 0.0,
        "entity_recall": {
            k: {
                "total_items": v["total"],
                "captured_items": v["found"],
                "recall_rate": round(v["found"] / v["total"], 4) if v["total"] > 0 else 0.0
            }
            for k, v in cat_entity_stats.items()
        },
        "failure_modes": failure_counts
    }

    output_path = "scratch/evaluation_results.json"
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump({"summary_stats": summary_stats, "records": evaluation_records}, f, indent=2)

    print("=================================================================")
    print("EVALUATION RESULTS SUMMARY")
    print("=================================================================")
    print(f"Total documents evaluated: {summary_stats['total_documents_evaluated']}")
    print(f"Successfully processed:    {summary_stats['successfully_summarized']}")
    print(f"Extraction failures:       {summary_stats['extraction_failures']}")
    print(f"Average ROUGE-1 F1:        {summary_stats['average_rouge1_f1'] * 100:.2f}%")
    print(f"Average ROUGE-2 F1:        {summary_stats['average_rouge2_f1'] * 100:.2f}%")
    print(f"Average ROUGE-L F1:        {summary_stats['average_rougeL_f1'] * 100:.2f}%")
    print("\nEntity & Critical Information Recall:")
    for k, v in summary_stats["entity_recall"].items():
        print(f"  - {k:<18}: {v['captured_items']}/{v['total_items']} ({v['recall_rate'] * 100:.1f}%)")
    print("\nFailure Mode Counts:")
    for k, v in summary_stats["failure_modes"].items():
        print(f"  - {k:<35}: {v}")
    print("=================================================================")

if __name__ == "__main__":
    run_evaluation()
