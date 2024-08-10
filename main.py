import streamlit as st
import pandas as pd
import requests
from io import BytesIO
from datetime import datetime, timedelta
import re
from collections import Counter
from difflib import get_close_matches
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders


st.set_page_config(
    page_title="YZF Scraping", layout="wide", initial_sidebar_state="expanded"
)
st.markdown(
    """
    <style>
    /* Streamlit menüsünü gizle */
    .streamlit-expander.closed > .streamlit-expander-header {
        padding: 0 10px;
    }
    .streamlit-expander.closed > .streamlit-expander-content {
        margin-left: 10px;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

API_KEY = open("API_KEY").read().strip()
SEARCH_ENGINE_ID = open("SEARCH_ENGINE_ID").read().strip()

startups = {
    "Sağlık (Healthcare)": ["Albert Health", "Enbiosis", "Hevi AI"],
    "Robotik (Robotics)": ["Atlas Robotics", "Hummingdrone"],
    "Siber Güvenlik (Cybersecurity)": ["Brandefense"],
    "Dijital Pazarlama (Digital Marketing)": ["DFX Digital", "Evercopy"],
    "Müşteri Deneyimi (Customer Experience)": ["AlternaCX"],
    "Yaratıcı Teknolojiler (Creative Technologies)": ["Artlabs"],
    "Kontrol Sistemleri (Control Systems)": ["ERG Controls"],
    "Finans (Finance)": ["More Wealth"],
    "Teknoloji ve Yazılım (Technology and Software)": [
        "Adapha",
        "Adin.ai",
        "Aivisiontech",
        "Co-One",
        "Cuebric",
        "Faradai AI",
        "Khenda",
        "Syntonym",
        "Lumion",
        "Phitech",
    ],
    "Analitik ve Veri (Analytics and Data)": ["RNV Analytics", "Sensemore"],
    "Moda ve Tekstil (Fashion and Textile)": ["T-Fashion"],
    "Görüntüleme ve Görüntü İşleme (Imaging and Image Processing)": ["Vispera"],
    "Diğer (Other)": [
        "Adastec",
        "Crait.it",
        "Lifespin GMBH",
        "Madlen",
        "Rem People",
        "Tazi",
    ],
}

prioritized_sites = [
    "webrazzi.com",
    "tomorrow.com.tr",
    "swipeline.co",
    "egirisim.com",
    "girisimhaber",
    "startupwatch",
]


def google_search(
    query, api_key, search_engine_id, start_date=None, end_date=None, num_results=100
):
    url = "https://www.googleapis.com/customsearch/v1"
    results = []
    params = {
        "q": query + " " + " OR ".join([f"site:{site}" for site in prioritized_sites]),
        "key": api_key,
        "cx": search_engine_id,
        "sort": "date",
        "num": 10,
        "start": 1,
    }

    if start_date and end_date:
        params["sort"] = f"date:r:{start_date}:{end_date}"

    while len(results) < num_results:
        response = requests.get(url, params=params)
        if response.status_code == 200:
            items = response.json().get("items", [])
            if not items:
                break
            for item in items:
                date, cleaned_snippet = extract_and_clean_date(item["snippet"])
                item["date"] = date or item.get("pagemap", {}).get("metatags", [{}])[
                    0
                ].get("article:published_time", "")
                item["date"] = format_date(item["date"])
                item["snippet"] = cleaned_snippet
                item["site_name"] = extract_site_name(item["displayLink"])
                results.append(item)
            params["start"] += 10
        else:
            st.error(f"Hata: {response.status_code}")
            break

    return results[:num_results]


def extract_and_clean_date(snippet):
    date_patterns = [
        r"(\b\d{1,2} [A-Za-z]+ \d{4}\b)",
        r"(\b\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[\+\-]\d{2}:\d{2})\b)",
        r"(\b[A-Za-z]{3} \d{1,2}, \d{4}\b)",
    ]

    for pattern in date_patterns:
        match = re.search(pattern, snippet)
        if match:
            date_str = match.group(1)
            cleaned_snippet = snippet.replace(date_str, "").strip()
            return date_str, cleaned_snippet

    return "", snippet


def format_date(date_str):
    try:
        if "T" in date_str:
            date_obj = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
            return date_obj.strftime("%d %B %Y")
        elif re.match(r"\b\d{1,2} [A-Za-z]+ \d{4}\b", date_str):
            date_obj = datetime.strptime(date_str, "%d %B %Y")
            return date_obj.strftime("%d %B %Y")
        else:
            return date_str

    except ValueError:
        return date_str


def extract_site_name(display_link):
    return re.sub(r"^www\d*\.", "", display_link.split("/")[0])


def suggest_corrections(keyword, results):
    keywords_in_results = []
    for item in results:
        keywords_in_results.extend(item["title"].split())
        keywords_in_results.extend(item["snippet"].split())

    keyword_counts = Counter(keywords_in_results)
    most_common_keywords = [
        word
        for word, count in keyword_counts.most_common()
        if word.lower() != keyword.lower()
    ]

    return get_close_matches(keyword, most_common_keywords, n=3, cutoff=0.8)


def send_email(
    recipient_email, subject, body, attachment=None, filename="attachment.xlsx"
):
    sender_email = "BUNU DOLDUR"  # Gönderici e-posta adresi girilecek, sorun yaşanmaması için 2 faktörlü kimlik doğrulama aktif hesap kullanılmalı. Google Hesabı yönet denip uygulama şifresi alınması lazım.
    sender_password = "BUNU DOLDUR"  # Alınan uygulama şifresi bu kısma girilecek aradaki boşluklar olmadan eklenmeli örneğin: "tkbnvwfblfvajsdy".

    message = MIMEMultipart()
    message["From"] = sender_email
    message["To"] = recipient_email
    message["Subject"] = subject

    message.attach(MIMEText(body, "plain"))

    if attachment:
        part = MIMEBase("application", "octet-stream")
        part.set_payload(attachment.read())
        encoders.encode_base64(part)
        part.add_header(
            "Content-Disposition",
            f"attachment; filename= {filename}",
        )
        message.attach(part)

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        server.login(sender_email, sender_password)
        server.sendmail(sender_email, recipient_email, message.as_string())


def main():
    st.title("YZF Scraping")
    st.markdown(
        """
        <h2>📊 Startup ve Anahtar Kelime Analizi ve Takibi</h2>
        <p>Bu uygulama belirli Startup ve anahtar kelimeler için Google arama sonuçlarını gösterir ve analiz eder.</p>
        """,
        unsafe_allow_html=True,
    )

    st.info(
        "Bu uygulama belirli Startup ve anahtar kelimeler için Google arama sonuçlarını gösterir ve analiz eder."
    )
    st.info(
        "Bu uygulama ile sektör ve şirket özelinde Google arama sonuçlarını görüntüleyebilirsiniz."
    )
    st.warning(
        "Sonuçları göndermeden önce alıcının email adresini doğru girdiğinizden emin olunuz."
    )

    sector = st.selectbox("Sektör Seçiniz", list(startups.keys()))
    company = st.selectbox("Şirket Seçiniz", startups[sector])
    keyword = st.text_input("Anahtar Kelimeler", value=company)

    st.sidebar.subheader("Tarih Filtreleme")
    start_date = st.sidebar.date_input(
        "Başlangıç Tarihi", datetime.today() - timedelta(days=1)
    )
    end_date = st.sidebar.date_input("Bitiş Tarihi", datetime.today())

    recipient_email = st.text_input("E-posta adresi giriniz")

    if st.button("Ara"):
        results = google_search(
            keyword,
            API_KEY,
            SEARCH_ENGINE_ID,
            start_date.strftime("%Y%m%d"),
            end_date.strftime("%Y%m%d"),
        )
        if results:
            df = pd.json_normalize(results)
            df = df[["site_name", "title", "link", "snippet", "date"]]
            df = df.fillna("")

            st.write(df)

            suggestions = suggest_corrections(keyword, results)
            if suggestions:
                st.warning(f"Potansiyel düzeltme önerileri: {', '.join(suggestions)}")

            excel_buffer = BytesIO()
            with pd.ExcelWriter(excel_buffer, engine="xlsxwriter") as writer:
                df.to_excel(writer, index=False, sheet_name="Sonuçlar")
            excel_buffer.seek(0)

            file_name = f"{keyword}_arama_sonuclari.xlsx"

            st.download_button(
                label="Sonuçları Excel Olarak İndir",
                data=excel_buffer.getvalue(),
                file_name=file_name,
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )

            if recipient_email:
                send_email(
                    recipient_email,
                    f"{keyword} Arama Sonuçları",
                    "Arama sonuçlarını ekli dosyada bulabilirsiniz.",
                    excel_buffer,
                    file_name,
                )
                st.success(f"E-posta {recipient_email} adresine gönderildi.")
        else:
            st.warning("Arama sonuç bulunamadı.")


if __name__ == "__main__":
    main()
