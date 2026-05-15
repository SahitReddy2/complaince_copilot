import pathlib, re, warnings
from bs4 import BeautifulSoup, XMLParsedAsHTMLWarning
from pdfminer.high_level import extract_text
import pandas as pd, binascii

warnings.filterwarnings("ignore", category=XMLParsedAsHTMLWarning)

ROOT = pathlib.Path(__file__).resolve().parents[1]
PDF_DIR, TXT_DIR = ROOT / "raw_pdfs", ROOT / "text"
TXT_DIR.mkdir(exist_ok=True)

def _tidy(t: str) -> str:
    t = re.sub(r"\s+\n", "\n", t)
    t = re.sub(r"\n{3,}", "\n\n", t)
    return t.strip() + "\n"

def is_valid_pdf(path: pathlib.Path) -> bool:
    try:
        with path.open("rb") as fh:
            return fh.read(4) == b"%PDF"
    except Exception:
        return False

def pdf_to_txt(pdf_path):
    if not is_valid_pdf(pdf_path):
        print(f"✗ {pdf_path.name} – not a real PDF, skipping")
        return
    try:
        txt = extract_text(pdf_path)
    except Exception as e:
        print(f"✗ {pdf_path.name} – pdfminer failed ({e}), skipping")
        return
    (TXT_DIR / f"{pdf_path.stem}.txt").write_text(_tidy(txt), encoding="utf-8")
    print(f"✓ {pdf_path.name} → .txt")

def html_to_txt(html_path):
    html = html_path.read_text(encoding="utf-8", errors="ignore")
    soup = BeautifulSoup(html, "lxml")
    for tag in soup(["script", "style", "nav", "header", "footer"]):
        tag.decompose()
    text = soup.get_text(separator="\n")
    (TXT_DIR / f"{html_path.stem}.txt").write_text(_tidy(text), encoding="utf-8")
    print(f"✓ {html_path.name} → .txt")

def xl_to_txt(xlsx_path):
    df = pd.read_excel(xlsx_path, header=None, engine="openpyxl")
    df[0].to_csv(TXT_DIR / f"{xlsx_path.stem}.txt",
                 index=False, header=False)
    print(f"✓ {xlsx_path.name} → .txt")

for f in PDF_DIR.iterdir():
    ext = f.suffix.lower()
    if ext == ".pdf":
        pdf_to_txt(f)
    elif ext in {".html", ".htm"}:
        html_to_txt(f)
    elif ext in {".xlsx", ".xls"}:
        xl_to_txt(f)
