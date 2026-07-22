import streamlit as st
import sqlite3, re, math, json
from pathlib import Path
from urllib.parse import urlparse
import requests
from bs4 import BeautifulSoup
from pypdf import PdfReader

DB = Path(__file__).with_name("av_assistent.db")

def db():
    c = sqlite3.connect(DB)
    c.row_factory = sqlite3.Row
    return c

def init():
    c=db()
    c.executescript("""
    CREATE TABLE IF NOT EXISTS sources(
      id INTEGER PRIMARY KEY, manufacturer TEXT, title TEXT, kind TEXT,
      url TEXT, version TEXT, text TEXT, created_at DATETIME DEFAULT CURRENT_TIMESTAMP);
    CREATE TABLE IF NOT EXISTS notes(
      id INTEGER PRIMARY KEY, title TEXT, body TEXT, manufacturer TEXT,
      created_at DATETIME DEFAULT CURRENT_TIMESTAMP);
    CREATE TABLE IF NOT EXISTS orders(
      id INTEGER PRIMARY KEY, order_no TEXT UNIQUE, customer TEXT, commission TEXT,
      delivery_date TEXT, status TEXT, progress INTEGER DEFAULT 0, notes TEXT);
    """)
    c.commit(); c.close()

def clean(s): return re.sub(r"\s+", " ", s or "").strip()

def chunks(text, size=1100, overlap=180):
    text=clean(text)
    if not text: return []
    out=[]; i=0
    while i < len(text):
        out.append(text[i:i+size])
        i += size-overlap
    return out

def tokens(s):
    return [x for x in re.findall(r"[a-zA-ZäöüÄÖÜß0-9®\-\.]+", (s or "").lower()) if len(x)>2]

def score(q, txt):
    qs=tokens(q); ts=tokens(txt)
    if not qs or not ts: return 0
    freq={}
    for t in ts: freq[t]=freq.get(t,0)+1
    exact=sum(freq.get(t,0) for t in qs)
    phrase=6 if q.lower() in txt.lower() else 0
    return exact + phrase

def search(q, manufacturer="Alle", limit=8):
    c=db()
    rows=c.execute("SELECT * FROM sources" + ("" if manufacturer=="Alle" else " WHERE manufacturer=?"),
                   (() if manufacturer=="Alle" else (manufacturer,))).fetchall()
    c.close()
    hits=[]
    for r in rows:
        for n,ch in enumerate(chunks(r["text"])):
            s=score(q,ch)
            if s>0: hits.append((s,r,n,ch))
    hits.sort(key=lambda x:x[0], reverse=True)
    return hits[:limit]

def add_source(manufacturer,title,kind,url,version,text):
    c=db(); c.execute("INSERT INTO sources(manufacturer,title,kind,url,version,text) VALUES(?,?,?,?,?,?)",
                      (manufacturer,title,kind,url,version,clean(text))); c.commit(); c.close()

def ingest_url(manufacturer,url):
    r=requests.get(url, timeout=20, headers={"User-Agent":"Mozilla/5.0"})
    r.raise_for_status()
    ctype=r.headers.get("content-type","")
    if "pdf" in ctype or url.lower().endswith(".pdf"):
        tmp=Path(__file__).with_name("_tmp.pdf"); tmp.write_bytes(r.content)
        reader=PdfReader(str(tmp))
        text="\n".join((p.extract_text() or "") for p in reader.pages)
        tmp.unlink(missing_ok=True)
        title=Path(urlparse(url).path).name or "PDF"
        add_source(manufacturer,title,"PDF",url,"",text)
    else:
        soup=BeautifulSoup(r.text,"html.parser")
        for x in soup(["script","style","nav","footer"]): x.decompose()
        title=clean(soup.title.get_text()) if soup.title else url
        add_source(manufacturer,title,"Webseite",url,"",soup.get_text(" "))
    return True

def ingest_upload(manufacturer,file):
    suffix=Path(file.name).suffix.lower()
    data=file.getvalue()
    if suffix==".pdf":
        tmp=Path(__file__).with_name("_upload.pdf"); tmp.write_bytes(data)
        reader=PdfReader(str(tmp))
        text="\n".join((p.extract_text() or "") for p in reader.pages)
        tmp.unlink(missing_ok=True)
    else:
        text=data.decode("utf-8", errors="ignore")
    add_source(manufacturer,file.name,"Upload","", "", text)

def seed():
    c=db(); n=c.execute("SELECT COUNT(*) n FROM sources").fetchone()["n"]; c.close()
    if n: return
    seeds=[
      ("GEALAN","S 9000 – offizielle Systemseite","Webseite","https://www.gealan.de/de/systeme/s-9000"),
      ("GROWE","GROWE Produktwelt","Webseite","https://www.rollladen-growe.de/produkte/"),
      ("GROWE","PAKTO®","Webseite","https://www.rollladen-growe.de/produkte/pakto/"),
      ("GROWE","Vorbauelemente","Webseite","https://www.rollladen-growe.de/produkte/vorbauelemente/"),
      ("GROWE","SUN-TEX","Webseite","https://www.rollladen-growe.de/SUN-TEX/"),
      ("NÜSSING","Fenstertechnik","Webseite","https://www.nuessing.de/shop/kategorie/2/fenstertechnik"),
      ("NÜSSING","Schwellen","Webseite","https://www.nuessing.de/shop/kategorie/16390/schwellen"),
      ("NÜSSING","Verkaufsunterlagen","Webseite","https://www.nuessing.de/service-kontakt/verkaufsunterlagen"),
    ]
    for m,t,k,u in seeds:
        try:
            r=requests.get(u,timeout=12,headers={"User-Agent":"Mozilla/5.0"}); r.raise_for_status()
            soup=BeautifulSoup(r.text,"html.parser")
            for x in soup(["script","style","nav","footer"]): x.decompose()
            add_source(m,t,k,u,"öffentlich",soup.get_text(" "))
        except Exception:
            pass

st.set_page_config(page_title="AV-Assistent", page_icon="🪟", layout="wide")
init(); seed()

st.title("AV-Assistent")
st.caption("Produktsuche & Wissensbasis – Prototyp V1")

tab1,tab2,tab3,tab4=st.tabs(["🔎 Produktsuche","📚 Quellen & Dokumente","📝 Notizen","📦 Aufträge (Vorschau)"])

with tab1:
    a,b=st.columns([3,1])
    q=a.text_input("Frage oder Suchbegriff", placeholder="z. B. maximale Glasstärke S 9000")
    manufacturer=b.selectbox("Hersteller",["Alle","GEALAN","GROWE","NÜSSING"])
    if q:
        hits=search(q,manufacturer)
        if not hits:
            st.warning("Keine zuverlässige Angabe in den hinterlegten Quellen gefunden.")
        else:
            st.subheader("Gefundene Belege")
            st.info("V1 beantwortet bewusst nicht frei: Sie zeigt die relevantesten Originalstellen. Dadurch werden unbelegte technische Angaben vermieden.")
            for s,r,n,ch in hits:
                with st.expander(f'{r["manufacturer"]} · {r["title"]}'):
                    st.write(ch)
                    st.caption(f'Quelle: {r["title"]} · Abschnitt {n+1}' + (f' · Stand: {r["version"]}' if r["version"] else ""))
                    if r["url"]: st.link_button("Originalquelle öffnen",r["url"])

with tab2:
    st.subheader("Neue Quelle hinzufügen")
    c1,c2=st.columns(2)
    m=c1.selectbox("Hersteller",["GEALAN","GROWE","NÜSSING","SONSTIGE"], key="docm")
    url=c2.text_input("Öffentliche URL")
    if st.button("Webseite/PDF einlesen") and url:
        try: ingest_url(m,url); st.success("Quelle wurde eingelesen."); st.rerun()
        except Exception as e: st.error(f"Konnte Quelle nicht einlesen: {e}")
    files=st.file_uploader("Oder Dokumente hochladen (PDF/TXT)", type=["pdf","txt"], accept_multiple_files=True)
    if st.button("Uploads übernehmen") and files:
        for f in files: ingest_upload(m,f)
        st.success(f"{len(files)} Dokument(e) hinzugefügt."); st.rerun()
    c=db(); rows=c.execute("SELECT manufacturer,title,kind,version,url,created_at FROM sources ORDER BY id DESC").fetchall(); c.close()
    st.subheader("Wissensbasis")
    for r in rows:
        st.write(f'**{r["manufacturer"]}** — {r["title"]} · {r["kind"]}')

with tab3:
    c1,c2=st.columns([1,2])
    nm=c1.selectbox("Hersteller",["Allgemein","GEALAN","GROWE","NÜSSING"])
    nt=c1.text_input("Titel")
    nb=c2.text_area("Notiz",height=130)
    if st.button("Notiz speichern") and nb:
        c=db(); c.execute("INSERT INTO notes(title,body,manufacturer) VALUES(?,?,?)",(nt,nb,nm)); c.commit(); c.close(); st.rerun()
    c=db(); notes=c.execute("SELECT * FROM notes ORDER BY id DESC").fetchall(); c.close()
    for n in notes:
        with st.expander(f'{n["manufacturer"]} · {n["title"] or "Notiz"}'):
            st.write(n["body"])

with tab4:
    st.info("Dieses Modul ist vorbereitet. Die echte ELO-Anbindung kommt später, sobald Schnittstelle und Berechtigungen geklärt sind.")
    c1,c2,c3=st.columns(3)
    c1.metric("Auftragsstatus","—")
    c2.metric("Liefertermin","—")
    c3.metric("Bestellungen offen","—")
    st.text_input("Auftragsnummer", placeholder="später: Auftrag aus ELO suchen")
    st.progress(0)
    st.write("Geplant: chronologische Ereignisse · Liefertermin · offene/erledigte Bestellungen · Dokumente · Notizen")
