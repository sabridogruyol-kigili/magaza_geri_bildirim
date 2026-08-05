import streamlit as st
import requests
import pandas as pd
from datetime import datetime
from io import BytesIO

# ==================== AYARLAR ====================
# Apps Script'i "Web Uygulaması" olarak yayınladıktan sonra aldığınız URL'yi buraya yapıştırın
APPS_SCRIPT_URL = "https://script.google.com/macros/s/AKfycbxS1WWlDieTqGvq35Pnr_30HPCuA1RLz3TkZDR1k-xGb6jSWNhHKHIKviXciMCUlOm2/exec"

UNVAN_LISTESI = [
    "Mağaza Müdür Yardımcısı", "Satış Şefi", "Satış Danışmanı",
    "Terzi Satış Danışmanı", "Terzi", "Kasiyer", "Depo Görevlisi", "Servis Görevlisi"
]

CEYREK_AYLAR = {1: [1, 2, 3], 2: [4, 5, 6], 3: [7, 8, 9], 4: [10, 11, 12]}

LOGO_DOSYASI = "Kiğılı IK Logo.png"

# ---------------------------------------------------------------- PAGE CONFIG (favicon = logo)
try:
    from PIL import Image
    _favicon = Image.open(LOGO_DOSYASI)
    st.set_page_config(page_title="Personel Değerlendirme Sistemi", page_icon=_favicon, layout="wide")
except Exception:
    st.set_page_config(page_title="Personel Değerlendirme Sistemi", page_icon="📋", layout="wide")

# ---------------------------------------------------------------- STYLE
st.markdown("""
<style>
    h1, h2, h3 { font-family: Georgia, serif; }
    .pill { display:inline-block; padding:2px 10px; border-radius:14px; font-size:12px; font-weight:600; background:rgba(122,35,49,0.14); color:#A9394A; }
    .info-box {
        background: var(--secondary-background-color, #FFFFFF);
        border: 1px solid rgba(128,128,128,0.25);
        border-radius: 10px; padding:16px 20px; margin-bottom:14px;
    }
    .empty-box {
        background: var(--secondary-background-color, #FFFFFF);
        border: 1.5px dashed rgba(122,35,49,0.35);
        border-radius: 12px; padding: 32px 20px; text-align:center; margin: 12px 0;
    }
    .empty-box .icon { font-size: 28px; margin-bottom: 8px; }
    .empty-box .msg { font-weight:600; font-size:14px; opacity:0.85; }
    .home-card {
        background: var(--secondary-background-color, #FFFFFF);
        border: 1px solid rgba(128,128,128,0.25);
        border-radius: 12px; padding: 22px 20px 8px; margin-bottom: 8px;
        transition: transform .15s ease, box-shadow .15s ease;
    }
    .home-card:hover { transform: translateY(-3px); box-shadow: 0 6px 18px rgba(122,35,49,0.15); border-color: rgba(122,35,49,0.4); }
    .small-muted { color:#6B6259; font-size:12.5px; }
    .metric-row { display:flex; gap:14px; flex-wrap:wrap; margin-bottom:16px; }

    div[data-testid="stProgress"] > div > div > div > div { background-color: #7A2331 !important; }
</style>
""", unsafe_allow_html=True)


def empty_state(icon, message):
    st.markdown(f"<div class='empty-box'><div class='icon'>{icon}</div><div class='msg'>{message}</div></div>", unsafe_allow_html=True)


# ==================== YARDIMCI FONKSİYONLAR ====================
def api_cagir(action, **kwargs):
    payload = {"action": action, "ip": get_ip(), "user_agent": get_user_agent()}
    payload.update(kwargs)
    try:
        r = requests.post(APPS_SCRIPT_URL, json=payload, timeout=60)
        return r.json()
    except Exception as e:
        return {"success": False, "error": f"Bağlantı hatası: {e}"}


def get_ip():
    try:
        headers = st.context.headers
        return headers.get("X-Forwarded-For", "bilinmiyor").split(",")[0].strip()
    except Exception:
        return "bilinmiyor"


def get_user_agent():
    try:
        return st.context.headers.get("User-Agent", "bilinmiyor")
    except Exception:
        return "bilinmiyor"


def donem_etiket(donem_adi):
    yil, ay = donem_adi.split("-")
    aylar = ["", "Ocak", "Şubat", "Mart", "Nisan", "Mayıs", "Haziran",
             "Temmuz", "Ağustos", "Eylül", "Ekim", "Kasım", "Aralık"]
    return f"{aylar[int(ay)]} {yil}"


# ==================== OTURUM DURUMU ====================
if "view" not in st.session_state:
    st.session_state.view = "home"  # home | kullanici_giris | yonetici_giris
if "giris_tipi" not in st.session_state:
    st.session_state.giris_tipi = None  # "kullanici" | "yonetici"
if "kullanici_adi" not in st.session_state:
    st.session_state.kullanici_adi = None
if "ad_soyad" not in st.session_state:
    st.session_state.ad_soyad = None
if "bolge" not in st.session_state:
    st.session_state.bolge = None
if "magaza" not in st.session_state:
    st.session_state.magaza = None
if "magaza_kodu" not in st.session_state:
    st.session_state.magaza_kodu = None


# ==================== SIDEBAR ====================
def sidebar_ciz():
    with st.sidebar:
        try:
            st.image(LOGO_DOSYASI, use_container_width=True)
        except Exception:
            st.markdown("""
                <div style="text-align:center;">
                    <div style="font-family:Georgia,serif; font-size:24px; font-weight:700; color:#211C1A;">KİĞILI</div>
                </div>
            """, unsafe_allow_html=True)
            st.caption("⚠️ Logo dosyası bulunamadı — dosya adını kontrol edin.")
        st.markdown("""
            <div style="text-align:center; padding: 0 0 18px;">
                <div style="font-size:11px; text-transform:uppercase; letter-spacing:0.12em; color:#7A2331; font-weight:600; margin-top:2px;">Personel Değerlendirme Sistemi</div>
            </div>
        """, unsafe_allow_html=True)
        st.divider()

        if st.session_state.giris_tipi is None:
            nav_items = [("home", "🏠 Ana Sayfa"), ("kullanici_giris", "👤 Kullanıcı Girişi"), ("yonetici_giris", "🔑 Yönetici Girişi")]
            for view_key, label in nav_items:
                is_active = st.session_state.view == view_key
                if st.button(label, key=f"nav_{view_key}", use_container_width=True,
                             type="primary" if is_active else "secondary"):
                    st.session_state.view = view_key
                    st.rerun()
        else:
            if st.session_state.giris_tipi == "kullanici":
                baslik = f"👤 {st.session_state.ad_soyad}"
                st.markdown(f"**{baslik}**")
                if st.session_state.magaza:
                    magaza_etiket = st.session_state.magaza
                    if st.session_state.magaza_kodu:
                        magaza_etiket += f" ({st.session_state.magaza_kodu})"
                    st.caption(f"📍 {magaza_etiket}" + (f" — {st.session_state.bolge}" if st.session_state.bolge else ""))
            else:
                st.markdown("**🔑 Yönetici Paneli**")
            if st.button("🔒 Çıkış Yap", use_container_width=True):
                st.session_state.giris_tipi = None
                st.session_state.kullanici_adi = None
                st.session_state.ad_soyad = None
                st.session_state.bolge = None
                st.session_state.magaza = None
                st.session_state.magaza_kodu = None
                st.session_state.view = "home"
                st.rerun()

        st.divider()
        st.markdown("""
            <div style="text-align:center;opacity:0.6;">
                <div style="font-size:11.5px;">© 2026 Kiğılı İnsan Kaynakları ve KYS Direktörlüğü</div>
                <div style="font-size:10px;margin-top:2px;">Organizasyonel Gelişim</div>
            </div>
        """, unsafe_allow_html=True)


# ==================== ANA SAYFA ====================
def ana_sayfa():
    st.markdown("""
        <div style="background:linear-gradient(135deg,#7A2331 0%,#591722 100%);border-radius:14px;
                    padding:28px 30px;margin-bottom:20px;color:#fff;">
            <div style="font-size:11px;text-transform:uppercase;letter-spacing:0.15em;opacity:0.75;">Kiğılı İnsan Kaynakları ve KYS Direktörlüğü</div>
            <div style="font-size:10px;opacity:0.65;margin-bottom:8px;">Organizasyonel Gelişim</div>
            <div style="font-family:Georgia,serif;font-size:24px;font-weight:700;">Personel Değerlendirme Sistemi</div>
            <div style="font-size:13.5px;opacity:0.85;margin-top:6px;max-width:520px;">
                Her mağaza kendi girişinden personelini aylık olarak değerlendirir; yönetici tüm dönemleri, soruları ve sonuçları tek yerden yönetir.
            </div>
        </div>
    """, unsafe_allow_html=True)

    st.write("")
    c1, c2 = st.columns(2)
    with c1:
        st.markdown("""
            <div class="home-card">
                <div style="font-size:26px;">👤</div>
                <div style="font-family:Georgia,serif;font-size:17px;font-weight:700;margin:8px 0 4px;">Kullanıcı Girişi</div>
                <div style="font-size:13px;opacity:0.75;margin-bottom:14px;">Kendi kullanıcı adı ve şifrenizle girin, personelinizi değerlendirin.</div>
            </div>
        """, unsafe_allow_html=True)
        if st.button("Kullanıcı Girişine Geç →", key="home_user_btn", use_container_width=True, type="primary"):
            st.session_state.view = "kullanici_giris"
            st.rerun()
    with c2:
        st.markdown("""
            <div class="home-card">
                <div style="font-size:26px;">🔑</div>
                <div style="font-family:Georgia,serif;font-size:17px;font-weight:700;margin:8px 0 4px;">Yönetici Paneli</div>
                <div style="font-size:13px;opacity:0.75;margin-bottom:14px;">Dönemleri, soruları ve raporları yönetin.</div>
            </div>
        """, unsafe_allow_html=True)
        if st.button("Yönetici Paneline Geç →", key="home_admin_btn", use_container_width=True, type="primary"):
            st.session_state.view = "yonetici_giris"
            st.rerun()

    st.write("")
    st.markdown("---")
    st.markdown("#### Nasıl Çalışır")
    s1, s2, s3 = st.columns(3)
    step_style = "text-align:center;padding:10px;"
    circle_style = ("display:inline-flex;align-items:center;justify-content:center;width:36px;height:36px;"
                     "border-radius:50%;background:#7A2331;color:#fff;font-weight:700;font-family:Georgia,serif;margin-bottom:10px;")
    with s1:
        st.markdown(f"""<div style="{step_style}"><div style="{circle_style}">1</div>
            <div style="font-weight:600;margin-bottom:4px;">Yönetici Dönemi Açar</div>
            <div style="font-size:12.5px;opacity:0.75;">İlgili ay için değerlendirme dönemi aktif edilir.</div></div>""", unsafe_allow_html=True)
    with s2:
        st.markdown(f"""<div style="{step_style}"><div style="{circle_style}">2</div>
            <div style="font-weight:600;margin-bottom:4px;">Kullanıcı Girer</div>
            <div style="font-size:12.5px;opacity:0.75;">Çalışan sayısını beyan eder, her personeli değerlendirir.</div></div>""", unsafe_allow_html=True)
    with s3:
        st.markdown(f"""<div style="{step_style}"><div style="{circle_style}">3</div>
            <div style="font-weight:600;margin-bottom:4px;">Rapor Oluşur</div>
            <div style="font-size:12.5px;opacity:0.75;">Doldurma durumu ve Excel raporları otomatik hazırlanır.</div></div>""", unsafe_allow_html=True)

    st.write("")
    st.markdown("""
        <div style='text-align:center;opacity:0.5;padding-top:10px;'>
            <div style='font-size:11.5px;'>Kiğılı İnsan Kaynakları ve KYS Direktörlüğü</div>
            <div style='font-size:10px;margin-top:2px;'>Organizasyonel Gelişim</div>
        </div>
    """, unsafe_allow_html=True)


# ==================== GİRİŞ EKRANLARI ====================
def kullanici_giris_ekrani():
    st.markdown("#### 👤 Kullanıcı Girişi")
    with st.form("kullanici_giris_form"):
        ka = st.text_input("Kullanıcı Adı")
        sf = st.text_input("Şifre", type="password")
        gonder = st.form_submit_button("Giriş Yap", use_container_width=True, type="primary")
    if gonder:
        if not ka or not sf:
            st.warning("Kullanıcı adı ve şifre gerekli.")
        else:
            sonuc = api_cagir("login", kullanici_adi=ka, sifre=sf)
            if sonuc.get("success"):
                st.session_state.giris_tipi = "kullanici"
                st.session_state.kullanici_adi = ka
                st.session_state.ad_soyad = sonuc.get("ad_soyad")
                st.session_state.bolge = sonuc.get("bolge")
                st.session_state.magaza = sonuc.get("magaza")
                st.session_state.magaza_kodu = sonuc.get("magaza_kodu")
                st.rerun()
            else:
                st.error(sonuc.get("error", "Giriş başarısız."))
    if st.button("← Ana Sayfaya Dön"):
        st.session_state.view = "home"
        st.rerun()


def yonetici_giris_ekrani():
    st.markdown("#### 🔑 Yönetici Girişi")
    with st.form("yonetici_giris_form"):
        sf2 = st.text_input("Yönetici Şifresi", type="password", key="admin_sf")
        gonder2 = st.form_submit_button("Yönetici Girişi", use_container_width=True, type="primary")
    if gonder2:
        sonuc = api_cagir("admin_login", sifre=sf2)
        if sonuc.get("success"):
            st.session_state.giris_tipi = "yonetici"
            st.rerun()
        else:
            st.error(sonuc.get("error", "Giriş başarısız."))
    if st.button("← Ana Sayfaya Dön"):
        st.session_state.view = "home"
        st.rerun()


# ==================== KULLANICI PANELİ ====================
def kullanici_paneli(kullanici_adi=None, ad_soyad=None, bolge=None, magaza=None, magaza_kodu=None, onizleme=False, key_prefix=""):
    ka = kullanici_adi if kullanici_adi is not None else st.session_state.kullanici_adi
    ads = ad_soyad if ad_soyad is not None else st.session_state.ad_soyad
    bl = bolge if bolge is not None else st.session_state.bolge
    mg = magaza if magaza is not None else st.session_state.magaza
    mk = magaza_kodu if magaza_kodu is not None else st.session_state.magaza_kodu

    if onizleme:
        st.info("🧪 **Önizleme modu** — bu ekran kullanıcıların göreceği ekranın birebir aynısıdır. Buradan yapılan kayıtlar/güncellemeler sisteme gerçekten kaydedilir.", icon="🧪")

    bolge_magaza_satiri = ""
    if bl or mg:
        mg_etiket = f"{mg} ({mk})" if (mg and mk) else (mg or "")
        parcalar = [p for p in [bl, mg_etiket] if p]
        bolge_magaza_satiri = f'<div style="font-size:12px;opacity:0.7;margin-top:2px;">📍 {" — ".join(parcalar)}</div>'

    st.markdown(f"""
        <div style="background:linear-gradient(135deg,#7A2331 0%,#591722 100%);border-radius:14px;
                    padding:20px 26px;margin-bottom:20px;color:#fff;">
            <div style="font-size:11px;text-transform:uppercase;letter-spacing:0.15em;opacity:0.75;">Personel Değerlendirme Sistemi</div>
            <div style="font-family:Georgia,serif;font-size:22px;font-weight:700;">Aylık Değerlendirme Formu</div>
            <div style="font-size:13px;opacity:0.85;margin-top:4px;">Hoş geldiniz, {ads}</div>
            {bolge_magaza_satiri}
        </div>
    """, unsafe_allow_html=True)

    donemler_res = api_cagir("get_periods")
    if not donemler_res.get("success"):
        st.error("Dönemler alınamadı.")
        return
    aktif_donemler = [d["donem_adi"] for d in donemler_res["donemler"] if d["aktif"]]
    if not aktif_donemler:
        empty_state("🗓️", "Şu anda aktif bir değerlendirme dönemi bulunmuyor. Yönetici tarafından bir dönem açıldığında burada görünecektir.")
        return

    donem = st.selectbox("Dönem Seçin", aktif_donemler, format_func=donem_etiket, key=f"{key_prefix}donem_sec")

    # --- Beyan sayısı ---
    beyan_res = api_cagir("get_declaration", kullanici_adi=ka, donem=donem)
    mevcut_beyan = beyan_res.get("beyan_sayisi", 0)

    st.markdown('<span class="pill">1. ADIM</span>', unsafe_allow_html=True)
    st.markdown("##### Çalışan Sayınızı Girin")
    col1, col2 = st.columns([2, 1])
    with col1:
        yeni_beyan = st.number_input("Bu dönem için toplam çalışan sayınız", min_value=0, value=int(mevcut_beyan), step=1, key=f"{key_prefix}beyan_sayi")
    with col2:
        st.write("")
        st.write("")
        if st.button("Kaydet / Güncelle", key=f"{key_prefix}beyan_kaydet"):
            api_cagir("save_declaration", kullanici_adi=ka, donem=donem, beyan_sayisi=yeni_beyan)
            st.success("Çalışan sayısı kaydedildi.")
            st.rerun()

    # --- Mevcut kayıtlar ---
    kayit_res = api_cagir("get_records", kullanici_adi=ka, donem=donem)
    personeller = kayit_res.get("personeller", [])

    st.markdown('<span class="pill">2. ADIM</span>', unsafe_allow_html=True)
    st.markdown("##### İlerleme Durumu")
    girilen = len(personeller)
    st.progress(min(girilen / yeni_beyan, 1.0) if yeni_beyan else 0)
    st.caption(f"{girilen} / {yeni_beyan} personel girildi")

    st.divider()
    st.markdown('<span class="pill">3. ADIM</span>', unsafe_allow_html=True)
    st.markdown("##### Personel Ekle / Düzenle")

    sorular_res = api_cagir("get_questions")
    sorular = sorular_res.get("sorular", [])
    if not sorular:
        empty_state("❓", "Henüz soru tanımlanmamış. Yöneticinizle iletişime geçin.")
        return

    mod = st.radio("İşlem", ["Yeni Personel Ekle", "Mevcut Personeli Düzenle"], horizontal=True, key=f"{key_prefix}mod_sec")

    if mod == "Mevcut Personeli Düzenle" and personeller:
        secilecekler = {f"{p['sicil_no']} - {p['personel_ad_soyad']}": p for p in personeller}
        secim = st.selectbox("Personel Seçin", list(secilecekler.keys()), key=f"{key_prefix}personel_sec")
        aktif_kayit = secilecekler[secim]
        sicil_no_deger = aktif_kayit["sicil_no"]
        ad_soyad_deger = aktif_kayit["personel_ad_soyad"]
        unvan_deger = aktif_kayit["unvan"]
        onceki_cevaplar = aktif_kayit["cevaplar"]
    elif mod == "Mevcut Personeli Düzenle":
        empty_state("👤", "Henüz eklenmiş personel yok.")
        return
    else:
        sicil_no_deger, ad_soyad_deger, unvan_deger, onceki_cevaplar = "", "", UNVAN_LISTESI[0], {}

    with st.form(f"{key_prefix}personel_form"):
        c1, c2, c3 = st.columns(3)
        with c1:
            sicil_no = st.text_input("Sicil Numarası", value=str(sicil_no_deger), disabled=(mod == "Mevcut Personeli Düzenle"))
        with c2:
            ad_soyad_girdi = st.text_input("Ad Soyad", value=ad_soyad_deger)
        with c3:
            unvan = st.selectbox("Unvan", UNVAN_LISTESI, index=UNVAN_LISTESI.index(unvan_deger) if unvan_deger in UNVAN_LISTESI else 0)

        st.markdown("**Değerlendirme Soruları**")
        cevap_girisleri = {}
        for s in sorular:
            onceki_deger = onceki_cevaplar.get(str(s["soru_no"]), onceki_cevaplar.get(s["soru_no"], ""))
            if s["cevap_tipi"] == "metin":
                cevap_girisleri[s["soru_no"]] = st.text_area(s["soru_metni"], value=str(onceki_deger) if onceki_deger else "", key=f"{key_prefix}soru_{s['soru_no']}")
            elif s["cevap_tipi"] == "sayisal":
                try:
                    varsayilan = float(onceki_deger) if onceki_deger else 0.0
                except ValueError:
                    varsayilan = 0.0
                cevap_girisleri[s["soru_no"]] = st.number_input(s["soru_metni"], value=varsayilan, key=f"{key_prefix}soru_{s['soru_no']}")
            elif s["cevap_tipi"] in ("secmeli", "skala"):
                secenekler = [x.strip() for x in (s.get("secenekler") or "").split(",") if x.strip()]
                idx = secenekler.index(onceki_deger) if onceki_deger in secenekler else 0
                cevap_girisleri[s["soru_no"]] = st.selectbox(s["soru_metni"], secenekler, index=idx, key=f"{key_prefix}soru_{s['soru_no']}")
            else:
                cevap_girisleri[s["soru_no"]] = st.text_input(s["soru_metni"], value=str(onceki_deger), key=f"{key_prefix}soru_{s['soru_no']}")

        gonder = st.form_submit_button("💾 Kaydet", use_container_width=True, type="primary")

    if gonder:
        if not sicil_no or not ad_soyad_girdi:
            st.warning("Sicil numarası ve ad soyad zorunludur.")
        else:
            cevaplar_payload = [{"soru_no": s["soru_no"], "soru_metni": s["soru_metni"], "cevap": cevap_girisleri[s["soru_no"]]} for s in sorular]
            sonuc = api_cagir("save_record", kullanici_adi=ka, donem=donem,
                               sicil_no=sicil_no, personel_ad_soyad=ad_soyad_girdi, unvan=unvan, cevaplar=cevaplar_payload)
            if sonuc.get("success"):
                st.success("Kayıt başarıyla kaydedildi.")
                st.rerun()
            else:
                st.error(sonuc.get("error", "Kayıt sırasında hata oluştu."))

    if personeller:
        st.divider()
        st.markdown("##### Girilen Personel Listesi")
        df = pd.DataFrame([{"Sicil No": p["sicil_no"], "Ad Soyad": p["personel_ad_soyad"], "Unvan": p["unvan"]} for p in personeller])
        st.dataframe(df, use_container_width=True, hide_index=True)


# ==================== YÖNETİCİ PANELİ ====================
def yonetici_paneli():
    st.markdown("""
        <div style="background:linear-gradient(135deg,#7A2331 0%,#591722 100%);border-radius:14px;
                    padding:20px 26px;margin-bottom:20px;color:#fff;">
            <div style="font-size:11px;text-transform:uppercase;letter-spacing:0.15em;opacity:0.75;">Personel Değerlendirme Sistemi</div>
            <div style="font-family:Georgia,serif;font-size:22px;font-weight:700;">Yönetici Kontrol Paneli</div>
        </div>
    """, unsafe_allow_html=True)

    sekmeler = st.tabs(["🧪 Test / Önizleme", "👥 Kullanıcı Ayarları", "📅 Dönemler", "❓ Sorular", "📊 Doldurma Durumu", "📥 Excel İndir", "🗂️ Loglar"])

    # --- TEST / ÖNİZLEME ---
    with sekmeler[0]:
        st.markdown("##### Kullanıcı Ekranını Önizle")
        st.caption("Kullanıcıların formu doldururken göreceği ekranın birebir aynısını burada görebilirsiniz.")

        kaynak = st.radio("Kimin ekranını görmek istersiniz?",
                           ["Kayıtlı bir kullanıcıyı seç", "Örnek/test kullanıcısı ile önizle"], horizontal=True)

        if kaynak == "Kayıtlı bir kullanıcıyı seç":
            kullanicilar_res = api_cagir("get_users")
            kullanicilar = kullanicilar_res.get("kullanicilar", [])
            if not kullanicilar:
                empty_state("👥", "Henüz kullanıcı tanımlanmadı. Önce 'Kullanıcı Ayarları' sekmesinden ekleyin.")
            else:
                secilecekler = {f"{k['kullanici_adi']} — {k['magaza'] or 'Mağaza belirtilmemiş'}": k for k in kullanicilar}
                secim = st.selectbox("Kullanıcı Seçin", list(secilecekler.keys()))
                secili = secilecekler[secim]
                st.divider()
                kullanici_paneli(kullanici_adi=secili["kullanici_adi"], ad_soyad=secili["ad_soyad"],
                                  bolge=secili["bolge"], magaza=secili["magaza"], magaza_kodu=secili.get("magaza_kodu"),
                                  onizleme=True, key_prefix="onizleme_")
        else:
            st.divider()
            kullanici_paneli(kullanici_adi="TEST_ONIZLEME", ad_soyad="Test Kullanıcısı",
                              bolge="Test Bölge", magaza="Test Mağaza", magaza_kodu="TST01",
                              onizleme=True, key_prefix="onizleme_")

    # --- KULLANICI AYARLARI ---
    with sekmeler[1]:
        st.markdown("##### Kullanıcı Yönetimi")
        st.caption("Her satır bir mağaza girişini temsil eder. Kullanıcı adı, şifre, bölge, mağaza ve mağaza kodu bilgisini buradan yönetin.")

        kullanicilar_res = api_cagir("get_users")
        kullanicilar = kullanicilar_res.get("kullanicilar", [])

        with st.expander("📥 Excel'den Toplu İçe Aktar"):
            st.caption("Sütun başlıkları: **Bölge, Mağaza, Mağaza Kodu, Kullanıcı Adı, Şifre** (sırası ve büyük/küçük harf önemli değil). "
                       "Zaten var olan bir kullanıcı adı gelirse bilgileri güncellenir, yeni ise eklenir.")
            ornek_df = pd.DataFrame([
                {"Bölge": "Marmara", "Mağaza": "Kadıköy AVM", "Mağaza Kodu": "1001", "Kullanıcı Adı": "kadikoy01", "Şifre": "kdk2026"},
                {"Bölge": "Ege", "Mağaza": "Alsancak", "Mağaza Kodu": "1002", "Kullanıcı Adı": "alsancak01", "Şifre": "als2026"},
            ])
            ornek_buf = BytesIO()
            with pd.ExcelWriter(ornek_buf, engine="openpyxl") as writer:
                ornek_df.to_excel(writer, index=False, sheet_name="Kullanicilar")
            st.download_button("📄 Örnek Şablonu İndir", data=ornek_buf.getvalue(), file_name="kullanici_sablonu.xlsx",
                                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

            yuklenen = st.file_uploader("Excel dosyası seçin (.xlsx)", type=["xlsx", "xls"], key="kullanici_excel")
            if yuklenen is not None:
                df_excel = pd.read_excel(yuklenen, sheet_name=0)
                baslik_haritasi = {}
                for kolon in df_excel.columns:
                    norm = str(kolon).strip().lower().replace("ı", "i").replace("ğ", "g").replace("ö", "o").replace("ü", "u").replace("ş", "s").replace("ç", "c")
                    if "kod" in norm:
                        baslik_haritasi[kolon] = "magaza_kodu"
                    elif "bolge" in norm:
                        baslik_haritasi[kolon] = "bolge"
                    elif "magaza" in norm:
                        baslik_haritasi[kolon] = "magaza"
                    elif "kullanici" in norm:
                        baslik_haritasi[kolon] = "kullanici_adi"
                    elif "sifre" in norm:
                        baslik_haritasi[kolon] = "sifre"

                eksik = {"bolge", "magaza", "kullanici_adi", "sifre"} - set(baslik_haritasi.values())
                if eksik:
                    st.error(f"Excel dosyasında şu sütunlar tanınamadı: {', '.join(eksik)}. Örnek şablonu indirip başlıkları kontrol edin.")
                else:
                    df_map = df_excel.rename(columns=baslik_haritasi)
                    if "magaza_kodu" not in df_map.columns:
                        df_map["magaza_kodu"] = ""
                    df_map = df_map[["bolge", "magaza", "magaza_kodu", "kullanici_adi", "sifre"]]
                    st.dataframe(df_map, use_container_width=True, hide_index=True)

                    tekrar_eden_adlar = df_map["kullanici_adi"].astype(str).str.strip()
                    tekrar_eden_adlar = tekrar_eden_adlar[tekrar_eden_adlar.duplicated(keep=False) & (tekrar_eden_adlar != "")]
                    if not tekrar_eden_adlar.empty:
                        st.warning(f"⚠️ Excel'de birden fazla satırda aynı kullanıcı adı kullanılmış: **{', '.join(sorted(set(tekrar_eden_adlar)))}**. "
                                   "Her mağazanın kullanıcı adı FARKLI olmalı — devam ederseniz bu isimlerden sadece sonuncusu kaydedilir, diğerleri kaybolur.")

                    if st.button("✅ İçe Aktarımı Onayla", type="primary"):
                        satirlar = df_map.fillna("").astype(str).to_dict(orient="records")
                        sonuc = api_cagir("import_users", kullanicilar=satirlar)
                        if sonuc.get("success"):
                            mesaj = f"İçe aktarıldı: {sonuc.get('eklenen', 0)} yeni, {sonuc.get('guncellenen', 0)} güncellendi, {sonuc.get('atlanan', 0)} atlandı (eksik bilgi)."
                            if sonuc.get("tekrar_eden"):
                                mesaj += f" ⚠️ {sonuc.get('tekrar_eden')} satırda AYNI kullanıcı adı Excel içinde birden fazla kez geçiyordu, sadece sonuncusu kaydedildi — Excel dosyanızı kontrol edin (her mağazanın kullanıcı adı FARKLI olmalı)."
                            st.success(mesaj)
                            st.rerun()
                        else:
                            st.error(sonuc.get("error", "İçe aktarım başarısız."))

        with st.expander("➕ Yeni Kullanıcı Ekle", expanded=(len(kullanicilar) == 0)):
            with st.form("yeni_kullanici_form", clear_on_submit=True):
                c1, c2, c3, c4, c5 = st.columns(5)
                y_bolge = c1.text_input("Bölge")
                y_magaza = c2.text_input("Mağaza")
                y_magaza_kodu = c3.text_input("Mağaza Kodu")
                y_kadi = c4.text_input("Kullanıcı Adı")
                y_sifre = c5.text_input("Şifre")
                ekle_kullanici = st.form_submit_button("Ekle", type="primary")
            if ekle_kullanici:
                if not y_kadi or not y_sifre:
                    st.warning("Kullanıcı adı ve şifre zorunludur.")
                else:
                    sonuc = api_cagir("save_user", kullanici_adi=y_kadi, sifre=y_sifre,
                                       ad_soyad=y_magaza or y_kadi, bolge=y_bolge, magaza=y_magaza, magaza_kodu=y_magaza_kodu)
                    if sonuc.get("success"):
                        st.success("Kullanıcı eklendi.")
                        st.rerun()
                    else:
                        st.error(sonuc.get("error", "Eklenemedi."))

        if not kullanicilar:
            empty_state("👥", "Henüz kullanıcı tanımlanmadı. Yukarıdan ilk kullanıcıyı ekleyin.")
        else:
            st.markdown("**Kayıtlı Kullanıcılar**")

            fc1, fc2 = st.columns([2, 2])
            arama_metni = fc1.text_input("🔍 Ara", placeholder="Kullanıcı adı, mağaza, bölge veya mağaza kodu...", key="kullanici_ara")
            tum_bolgeler = sorted(set(k["bolge"] for k in kullanicilar if k["bolge"]))
            bolge_filtre = fc2.multiselect("Bölge Filtrele", tum_bolgeler, key="kullanici_bolge_filtre")

            gosterilecekler = kullanicilar
            if arama_metni:
                q = arama_metni.strip().lower()
                gosterilecekler = [
                    k for k in gosterilecekler
                    if q in str(k["kullanici_adi"]).lower() or q in str(k["magaza"]).lower()
                    or q in str(k["bolge"]).lower() or q in str(k.get("magaza_kodu", "")).lower()
                ]
            if bolge_filtre:
                gosterilecekler = [k for k in gosterilecekler if k["bolge"] in bolge_filtre]

            st.caption(f"{len(gosterilecekler)} / {len(kullanicilar)} kullanıcı gösteriliyor")

            if not gosterilecekler:
                empty_state("🔍", "Bu filtrelere uygun kullanıcı bulunamadı.")
            else:
                hc0, hc1, hc2, hc3, hc4, hc5, hc6 = st.columns([0.5, 2, 2, 1.5, 2, 2, 1])
                hc0.markdown("**Seç**")
                hc1.markdown("**Bölge**")
                hc2.markdown("**Mağaza**")
                hc3.markdown("**Mağaza Kodu**")
                hc4.markdown("**Kullanıcı Adı**")
                hc5.markdown("**Şifre**")
                hc6.markdown("**Sil**")

                secilenler = []
                for k in sorted(gosterilecekler, key=lambda x: (x["bolge"], x["magaza"])):
                    c0, c1, c2, c3, c4, c5, c6 = st.columns([0.5, 2, 2, 1.5, 2, 2, 1])
                    secildi = c0.checkbox("Seç", key=f"sec_{k['kullanici_adi']}", label_visibility="collapsed")
                    if secildi:
                        secilenler.append(k["kullanici_adi"])
                    yeni_bolge = c1.text_input("Bölge", value=k["bolge"], key=f"kb_{k['kullanici_adi']}", label_visibility="collapsed")
                    yeni_magaza = c2.text_input("Mağaza", value=k["magaza"], key=f"km_{k['kullanici_adi']}", label_visibility="collapsed")
                    yeni_magaza_kodu = c3.text_input("Mağaza Kodu", value=k.get("magaza_kodu", ""), key=f"kmk_{k['kullanici_adi']}", label_visibility="collapsed")
                    yeni_kadi = c4.text_input("Kullanıcı Adı", value=k["kullanici_adi"], key=f"kk_{k['kullanici_adi']}", label_visibility="collapsed")
                    yeni_sifre = c5.text_input("Şifre", value=k["sifre"], key=f"ks_{k['kullanici_adi']}", label_visibility="collapsed")

                    degisti = (yeni_bolge != k["bolge"] or yeni_magaza != k["magaza"] or
                               yeni_magaza_kodu != k.get("magaza_kodu", "") or
                               yeni_kadi != k["kullanici_adi"] or yeni_sifre != k["sifre"])
                    if degisti:
                        if c6.button("💾", key=f"kaydet_{k['kullanici_adi']}", help="Değişikliği kaydet"):
                            sonuc = api_cagir("save_user", orijinal_kullanici_adi=k["kullanici_adi"],
                                               kullanici_adi=yeni_kadi, sifre=yeni_sifre,
                                               ad_soyad=yeni_magaza or yeni_kadi, bolge=yeni_bolge, magaza=yeni_magaza,
                                               magaza_kodu=yeni_magaza_kodu)
                            if sonuc.get("success"):
                                st.success(f"'{yeni_kadi}' güncellendi.")
                                st.rerun()
                            else:
                                st.error(sonuc.get("error", "Güncellenemedi."))
                    else:
                        if c6.button("🗑️", key=f"sil_{k['kullanici_adi']}", help="Bu kullanıcıyı sil"):
                            api_cagir("delete_user", kullanici_adi=k["kullanici_adi"])
                            st.rerun()

                st.divider()
                if secilenler:
                    st.warning(f"⚠️ {len(secilenler)} kullanıcı seçili: {', '.join(secilenler[:8])}{' ...' if len(secilenler) > 8 else ''}")
                    onay = st.checkbox(f"Bu {len(secilenler)} kullanıcıyı kalıcı olarak silmek istediğimi onaylıyorum", key="toplu_sil_onay")
                    if st.button(f"🗑️ Seçilenleri Sil ({len(secilenler)})", type="primary", disabled=not onay):
                        sonuc = api_cagir("delete_users_toplu", kullanici_adilari=secilenler)
                        if sonuc.get("success"):
                            st.success(f"{sonuc.get('silinen', 0)} kullanıcı silindi.")
                            st.rerun()
                        else:
                            st.error(sonuc.get("error", "Silinemedi."))
                else:
                    st.caption("Toplu silmek için yukarıdan kullanıcı satırlarını seçin.")

    # --- DÖNEMLER ---
    with sekmeler[2]:
        st.markdown("##### Dönem Yönetimi")
        with st.form("yeni_donem_form"):
            c1, c2 = st.columns([3, 1])
            with c1:
                yeni_donem = st.text_input("Yeni Dönem (YYYY-AA formatında, örn. 2026-09)")
            with c2:
                st.write("")
                st.write("")
                ekle = st.form_submit_button("Ekle", type="primary")
        if ekle and yeni_donem:
            sonuc = api_cagir("create_period", donem_adi=yeni_donem)
            if sonuc.get("success"):
                st.success("Dönem eklendi.")
                st.rerun()
            else:
                st.error(sonuc.get("error"))

        donemler_res = api_cagir("get_periods")
        donemler = donemler_res.get("donemler", [])
        if not donemler:
            empty_state("🗓️", "Henüz dönem tanımlanmadı. Yukarıdan yeni bir dönem ekleyin.")
        for d in sorted(donemler, key=lambda x: x["donem_adi"], reverse=True):
            c1, c2 = st.columns([3, 1])
            c1.markdown(f"<div class='info-box' style='padding:10px 16px;margin-bottom:8px;'><b>{donem_etiket(d['donem_adi'])}</b> <span class='small-muted'>({d['donem_adi']})</span></div>", unsafe_allow_html=True)
            yeni_durum = c2.toggle("Aktif", value=d["aktif"], key=f"toggle_{d['donem_adi']}")
            if yeni_durum != d["aktif"]:
                api_cagir("toggle_period", donem_adi=d["donem_adi"], aktif=yeni_durum)
                st.rerun()

    # --- SORULAR ---
    with sekmeler[3]:
        st.markdown("##### Soru Yönetimi")
        sorular_res = api_cagir("get_questions")
        sorular = sorular_res.get("sorular", [])

        with st.expander("📥 Excel'den Toplu İçe Aktar"):
            st.caption("Sütun başlıkları: **Soru No (opsiyonel), Soru Metni, Cevap Tipi, Seçenekler (opsiyonel)**. "
                       "Cevap Tipi olarak şunları yazabilirsiniz: **Sayısal**, **Sözel** (metin), **Seçmeli**, **1-10** (otomatik 1'den 10'a seçenek oluşturur).")
            ornek_df = pd.DataFrame([
                {"Soru No": 1, "Soru Metni": "Mağaza Ciro Hedef Gerçekleşme", "Cevap Tipi": "Sayısal", "Seçenekler": ""},
                {"Soru No": 2, "Soru Metni": "Yakaladığın hedefi nasıl değerlendiriyorsun?", "Cevap Tipi": "Sözel", "Seçenekler": ""},
                {"Soru No": 3, "Soru Metni": "Çalışan Değerlendirmesi", "Cevap Tipi": "1-10", "Seçenekler": ""},
            ])
            ornek_buf = BytesIO()
            with pd.ExcelWriter(ornek_buf, engine="openpyxl") as writer:
                ornek_df.to_excel(writer, index=False, sheet_name="Sorular")
            st.download_button("📄 Örnek Şablonu İndir", data=ornek_buf.getvalue(), file_name="soru_sablonu.xlsx",
                                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", key="soru_sablon_indir")

            mod = st.radio("İçe aktarma şekli", ["Mevcut soruların üzerine ekle/güncelle", "Tüm soruları bununla değiştir"], key="soru_import_mod")
            yuklenen_soru = st.file_uploader("Excel dosyası seçin (.xlsx)", type=["xlsx", "xls"], key="soru_excel")

            if yuklenen_soru is not None:
                df_excel = pd.read_excel(yuklenen_soru, sheet_name=0)
                baslik_haritasi = {}
                for kolon in df_excel.columns:
                    norm = str(kolon).strip().lower().replace("ı", "i").replace("ğ", "g").replace("ö", "o").replace("ü", "u").replace("ş", "s").replace("ç", "c")
                    if "no" in norm:
                        baslik_haritasi[kolon] = "soru_no"
                    elif "metni" in norm or "soru" == norm:
                        baslik_haritasi[kolon] = "soru_metni"
                    elif "tip" in norm:
                        baslik_haritasi[kolon] = "cevap_tipi"
                    elif "secenek" in norm:
                        baslik_haritasi[kolon] = "secenekler"

                if "soru_metni" not in baslik_haritasi.values() or "cevap_tipi" not in baslik_haritasi.values():
                    st.error("Excel dosyasında 'Soru Metni' ve 'Cevap Tipi' sütunları bulunamadı. Örnek şablonu indirip başlıkları kontrol edin.")
                else:
                    df_map = df_excel.rename(columns=baslik_haritasi)
                    if "soru_no" not in df_map.columns:
                        df_map["soru_no"] = None
                    if "secenekler" not in df_map.columns:
                        df_map["secenekler"] = ""

                    def tip_normalize(deger):
                        d = str(deger).strip().lower().replace("ı", "i")
                        if "sayisal" in d or "sayı" in d.lower():
                            return "sayisal", ""
                        if "sozel" in d or "metin" in d:
                            return "metin", ""
                        if "1-10" in d or "1 10" in d:
                            return "secmeli", "1,2,3,4,5,6,7,8,9,10"
                        if "secmeli" in d or "seçmeli" in deger.lower():
                            return "secmeli", ""
                        if "skala" in d:
                            return "skala", ""
                        return "metin", ""

                    onizleme_satirlari = []
                    for _, row in df_map.iterrows():
                        tip_sonuc, varsayilan_sec = tip_normalize(row["cevap_tipi"])
                        secenek_deger = str(row.get("secenekler") or "").strip() or varsayilan_sec
                        onizleme_satirlari.append({
                            "soru_no": None if pd.isna(row.get("soru_no")) else int(row.get("soru_no")),
                            "soru_metni": str(row["soru_metni"]).strip(),
                            "cevap_tipi": tip_sonuc,
                            "secenekler": secenek_deger,
                        })

                    st.dataframe(pd.DataFrame(onizleme_satirlari), use_container_width=True, hide_index=True)

                    if mod == "Tüm soruları bununla değiştir":
                        st.warning("⚠️ Bu seçenek mevcut TÜM soruları siler ve yerine yukarıdakileri yazar.")

                    if st.button("✅ İçe Aktarımı Onayla", type="primary", key="soru_import_onayla"):
                        mod_kodu = "degistir" if mod == "Tüm soruları bununla değiştir" else "ekle"
                        sonuc = api_cagir("import_questions", sorular=onizleme_satirlari, mod=mod_kodu)
                        if sonuc.get("success"):
                            st.success(f"İçe aktarıldı: {sonuc.get('eklenen', 0)} yeni, {sonuc.get('guncellenen', 0)} güncellendi.")
                            st.rerun()
                        else:
                            st.error(sonuc.get("error", "İçe aktarım başarısız."))

        if not sorular:
            empty_state("❓", "Henüz soru tanımlanmadı. Yukarıdan toplu içe aktarın veya aşağıdan tek tek ekleyin.")

        for s in sorular:
            with st.expander(f"Soru {s['soru_no']}: {s['soru_metni'][:50]}"):
                with st.form(f"soru_duzenle_{s['soru_no']}"):
                    metin = st.text_input("Soru Metni", value=s["soru_metni"], key=f"metin_{s['soru_no']}")
                    tip = st.selectbox("Cevap Tipi", ["metin", "sayisal", "secmeli", "skala"],
                                        index=["metin", "sayisal", "secmeli", "skala"].index(s["cevap_tipi"]),
                                        key=f"tip_{s['soru_no']}")
                    secenek = st.text_input("Seçenekler (virgülle ayırın, sadece seçmeli/skala için)",
                                             value=s.get("secenekler", ""), key=f"sec_{s['soru_no']}")
                    c1, c2 = st.columns(2)
                    guncelle = c1.form_submit_button("Güncelle", type="primary", use_container_width=True)
                    sil = c2.form_submit_button("🗑️ Soruyu Sil", use_container_width=True)
                if guncelle:
                    api_cagir("save_question", soru_no=s["soru_no"], soru_metni=metin, cevap_tipi=tip, secenekler=secenek, aktif=True)
                    st.success("Soru güncellendi.")
                    st.rerun()
                if sil:
                    api_cagir("delete_question", soru_no=s["soru_no"])
                    st.success("Soru silindi.")
                    st.rerun()

        st.divider()
        st.markdown("**Yeni Soru Ekle**")
        with st.form("yeni_soru_form"):
            yeni_metin = st.text_input("Soru Metni")
            yeni_tip = st.selectbox("Cevap Tipi", ["metin", "sayisal", "secmeli", "skala"], key="yeni_tip")
            yeni_secenek = st.text_input("Seçenekler (virgülle ayırın, örn: 1,2,3,4,5)", key="yeni_sec")
            soru_ekle = st.form_submit_button("Soru Ekle", type="primary")
        if soru_ekle and yeni_metin:
            api_cagir("save_question", soru_no=None, soru_metni=yeni_metin, cevap_tipi=yeni_tip, secenekler=yeni_secenek, aktif=True)
            st.success("Soru eklendi.")
            st.rerun()

    # --- DOLDURMA DURUMU ---
    with sekmeler[4]:
        st.markdown("##### Doldurma Durumu")
        donemler_res = api_cagir("get_periods")
        tum_donemler = [d["donem_adi"] for d in donemler_res.get("donemler", [])]
        secilen_donemler = st.multiselect("Dönem(ler) Seçin", tum_donemler, default=tum_donemler[:1], format_func=donem_etiket)
        durum_filtre = st.multiselect("Durum Filtrele", ["tamamlandi", "kismen", "doldurmadi"], default=["doldurmadi"])

        if secilen_donemler:
            res = api_cagir("get_fill_status", donemler=secilen_donemler)
            df = pd.DataFrame(res.get("durumlar", []))
            if not df.empty:
                if durum_filtre:
                    df = df[df["durum"].isin(durum_filtre)]
                etiketler = {"tamamlandi": "✅ Tamamlandı", "kismen": "🟡 Kısmen", "doldurmadi": "🔴 Doldurmadı"}
                df["durum"] = df["durum"].map(etiketler)
                st.dataframe(df.rename(columns={
                    "kullanici_adi": "Kullanıcı", "ad_soyad": "Ad Soyad", "donem": "Dönem",
                    "beyan_sayisi": "Beyan Edilen", "girilen_sayi": "Girilen", "durum": "Durum"
                }), use_container_width=True, hide_index=True)
            else:
                empty_state("📊", "Seçilen filtrelere uygun kayıt bulunamadı.")

    # --- EXCEL İNDİR ---
    with sekmeler[5]:
        st.markdown("##### Excel Raporu İndir")
        donemler_res = api_cagir("get_periods")
        tum_donemler = sorted([d["donem_adi"] for d in donemler_res.get("donemler", [])], reverse=True)
        kullanicilar_res = api_cagir("get_fill_status", donemler=[])
        tum_kullanicilar = sorted(set(d["kullanici_adi"] for d in kullanicilar_res.get("durumlar", [])))

        st.markdown("**Çeyreklik Hızlı Filtre**")
        cc1, cc2, cc3, cc4 = st.columns(4)
        ceyrek_secim = None
        if cc1.button("Ç1 (Oca-Mar)"): ceyrek_secim = 1
        if cc2.button("Ç2 (Nis-Haz)"): ceyrek_secim = 2
        if cc3.button("Ç3 (Tem-Eyl)"): ceyrek_secim = 3
        if cc4.button("Ç4 (Eki-Ara)"): ceyrek_secim = 4

        varsayilan_donem = tum_donemler
        if ceyrek_secim:
            aylar = CEYREK_AYLAR[ceyrek_secim]
            varsayilan_donem = [d for d in tum_donemler if int(d.split("-")[1]) in aylar]

        secilen_donemler = st.multiselect("Dönem(ler)", tum_donemler, default=varsayilan_donem, format_func=donem_etiket, key="export_donem")
        secilen_kullanicilar = st.multiselect("Kullanıcı(lar) (boş = tümü)", tum_kullanicilar, key="export_kullanici")
        secilen_unvanlar = st.multiselect("Unvan(lar) (boş = tümü)", UNVAN_LISTESI, key="export_unvan")

        if st.button("📥 Excel Oluştur ve İndir", type="primary"):
            res = api_cagir("get_export_data", donemler=secilen_donemler, kullanicilar=secilen_kullanicilar, unvanlar=secilen_unvanlar)
            veriler = res.get("veriler", [])
            if not veriler:
                st.warning("Seçilen filtrelere uygun veri bulunamadı.")
            else:
                df = pd.DataFrame(veriler)
                df = df.rename(columns={
                    "kullanici_adi": "Kullanıcı", "sicil_no": "Sicil No", "personel_ad_soyad": "Ad Soyad",
                    "unvan": "Unvan", "donem": "Dönem", "soru_no": "Soru No", "soru_metni": "Soru",
                    "cevap": "Cevap", "gonderim_tarihi": "Gönderim Tarihi", "guncelleme_tarihi": "Güncelleme Tarihi"
                })
                buf = BytesIO()
                with pd.ExcelWriter(buf, engine="openpyxl") as writer:
                    df.to_excel(writer, index=False, sheet_name="Rapor")
                st.download_button("İndir: rapor.xlsx", data=buf.getvalue(),
                                    file_name=f"rapor_{datetime.now().strftime('%Y%m%d_%H%M')}.xlsx",
                                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

    # --- LOGLAR ---
    with sekmeler[6]:
        st.markdown("##### Giriş / İşlem Logları")
        c1, c2, c3 = st.columns(3)
        ka_filtre = c1.text_input("Kullanıcı Adı Filtrele (boş = tümü)")
        bas_tarih = c2.date_input("Başlangıç Tarihi", value=None)
        bit_tarih = c3.date_input("Bitiş Tarihi", value=None)

        if st.button("Logları Getir", type="primary"):
            params = {}
            if ka_filtre: params["kullanici_adi"] = ka_filtre
            if bas_tarih: params["baslangic"] = str(bas_tarih)
            if bit_tarih: params["bitis"] = str(bit_tarih)
            res = api_cagir("get_logs", **params)
            df = pd.DataFrame(res.get("loglar", []))
            if not df.empty:
                st.dataframe(df.rename(columns={
                    "tarih_saat": "Tarih/Saat", "kullanici_adi": "Kullanıcı", "islem": "İşlem",
                    "ip_adresi": "IP Adresi", "tarayici_bilgisi": "Tarayıcı", "detay": "Detay"
                }), use_container_width=True, hide_index=True)
            else:
                empty_state("🗂️", "Kayıt bulunamadı.")


# ==================== YÖNLENDİRME ====================
if APPS_SCRIPT_URL == "BURAYA_APPS_SCRIPT_WEB_APP_URL_YAPISTIRIN":
    st.warning("⚠️ Lütfen app.py içinde APPS_SCRIPT_URL değişkenini kendi Apps Script Web App URL'niz ile değiştirin.")

sidebar_ciz()

if st.session_state.giris_tipi == "kullanici":
    kullanici_paneli()
elif st.session_state.giris_tipi == "yonetici":
    yonetici_paneli()
elif st.session_state.view == "kullanici_giris":
    kullanici_giris_ekrani()
elif st.session_state.view == "yonetici_giris":
    yonetici_giris_ekrani()
else:
    ana_sayfa()
