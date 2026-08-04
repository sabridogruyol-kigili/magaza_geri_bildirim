import streamlit as st
import requests
import pandas as pd
from datetime import datetime
from io import BytesIO

# ==================== AYARLAR ====================
# Apps Script'i "Web Uygulaması" olarak yayınladıktan sonra aldığınız URL'yi buraya yapıştırın
APPS_SCRIPT_URL = "https://script.google.com/macros/s/AKfycbzOI0kAiy2CJixUf5ElBKA8O6NSijRb19pBw_uo4k9bB_mfQyEEXO7Xszb-1Pr90g5c/exec"

UNVAN_LISTESI = [
    "Mağaza Müdür Yardımcısı", "Satış Şefi", "Satış Danışmanı",
    "Terzi Satış Danışmanı", "Terzi", "Kasiyer", "Depo Görevlisi", "Servis Görevlisi"
]

CEYREK_AYLAR = {1: [1, 2, 3], 2: [4, 5, 6], 3: [7, 8, 9], 4: [10, 11, 12]}

st.set_page_config(page_title="Personel Değerlendirme Sistemi", page_icon="📋", layout="wide")


# ==================== YARDIMCI FONKSİYONLAR ====================
def api_cagir(action, **kwargs):
    payload = {"action": action, "ip": get_ip(), "user_agent": get_user_agent()}
    payload.update(kwargs)
    try:
        r = requests.post(APPS_SCRIPT_URL, json=payload, timeout=30)
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
if "giris_tipi" not in st.session_state:
    st.session_state.giris_tipi = None  # "kullanici" | "yonetici"
if "kullanici_adi" not in st.session_state:
    st.session_state.kullanici_adi = None
if "ad_soyad" not in st.session_state:
    st.session_state.ad_soyad = None


# ==================== GİRİŞ EKRANI ====================
def giris_ekrani():
    st.title("📋 Personel Değerlendirme Sistemi")
    tab1, tab2 = st.tabs(["👤 Kullanıcı Girişi", "🔑 Yönetici Girişi"])

    with tab1:
        with st.form("kullanici_giris_form"):
            ka = st.text_input("Kullanıcı Adı")
            sf = st.text_input("Şifre", type="password")
            gonder = st.form_submit_button("Giriş Yap", use_container_width=True)
        if gonder:
            if not ka or not sf:
                st.warning("Kullanıcı adı ve şifre gerekli.")
            else:
                sonuc = api_cagir("login", kullanici_adi=ka, sifre=sf)
                if sonuc.get("success"):
                    st.session_state.giris_tipi = "kullanici"
                    st.session_state.kullanici_adi = ka
                    st.session_state.ad_soyad = sonuc.get("ad_soyad")
                    st.rerun()
                else:
                    st.error(sonuc.get("error", "Giriş başarısız."))

    with tab2:
        with st.form("yonetici_giris_form"):
            sf2 = st.text_input("Yönetici Şifresi", type="password", key="admin_sf")
            gonder2 = st.form_submit_button("Yönetici Girişi", use_container_width=True)
        if gonder2:
            sonuc = api_cagir("admin_login", sifre=sf2)
            if sonuc.get("success"):
                st.session_state.giris_tipi = "yonetici"
                st.rerun()
            else:
                st.error(sonuc.get("error", "Giriş başarısız."))


# ==================== KULLANICI PANELİ ====================
def kullanici_paneli():
    st.sidebar.title(f"👤 {st.session_state.ad_soyad}")
    if st.sidebar.button("Çıkış Yap"):
        for k in ["giris_tipi", "kullanici_adi", "ad_soyad"]:
            st.session_state[k] = None
        st.rerun()

    st.title("📋 Aylık Değerlendirme Formu")

    donemler_res = api_cagir("get_periods")
    if not donemler_res.get("success"):
        st.error("Dönemler alınamadı.")
        return
    aktif_donemler = [d["donem_adi"] for d in donemler_res["donemler"] if d["aktif"]]
    if not aktif_donemler:
        st.info("Şu anda aktif bir değerlendirme dönemi bulunmuyor. Yönetici tarafından bir dönem açıldığında burada görünecektir.")
        return

    donem = st.selectbox("Dönem Seçin", aktif_donemler, format_func=donem_etiket)

    # --- Beyan sayısı ---
    beyan_res = api_cagir("get_declaration", kullanici_adi=st.session_state.kullanici_adi, donem=donem)
    mevcut_beyan = beyan_res.get("beyan_sayisi", 0)

    st.subheader("1️⃣ Çalışan Sayınızı Girin")
    col1, col2 = st.columns([2, 1])
    with col1:
        yeni_beyan = st.number_input("Bu dönem için toplam çalışan sayınız", min_value=0, value=int(mevcut_beyan), step=1)
    with col2:
        st.write("")
        st.write("")
        if st.button("Kaydet / Güncelle", key="beyan_kaydet"):
            api_cagir("save_declaration", kullanici_adi=st.session_state.kullanici_adi, donem=donem, beyan_sayisi=yeni_beyan)
            st.success("Çalışan sayısı kaydedildi.")
            st.rerun()

    # --- Mevcut kayıtlar ---
    kayit_res = api_cagir("get_records", kullanici_adi=st.session_state.kullanici_adi, donem=donem)
    personeller = kayit_res.get("personeller", [])

    st.subheader("2️⃣ İlerleme Durumu")
    girilen = len(personeller)
    st.progress(min(girilen / yeni_beyan, 1.0) if yeni_beyan else 0)
    st.caption(f"{girilen} / {yeni_beyan} personel girildi")

    st.divider()
    st.subheader("3️⃣ Personel Ekle / Düzenle")

    sorular_res = api_cagir("get_questions")
    sorular = sorular_res.get("sorular", [])
    if not sorular:
        st.warning("Henüz soru tanımlanmamış. Yöneticinizle iletişime geçin.")
        return

    mod = st.radio("İşlem", ["Yeni Personel Ekle", "Mevcut Personeli Düzenle"], horizontal=True)

    if mod == "Mevcut Personeli Düzenle" and personeller:
        secilecekler = {f"{p['sicil_no']} - {p['personel_ad_soyad']}": p for p in personeller}
        secim = st.selectbox("Personel Seçin", list(secilecekler.keys()))
        aktif_kayit = secilecekler[secim]
        sicil_no_deger = aktif_kayit["sicil_no"]
        ad_soyad_deger = aktif_kayit["personel_ad_soyad"]
        unvan_deger = aktif_kayit["unvan"]
        onceki_cevaplar = aktif_kayit["cevaplar"]
    elif mod == "Mevcut Personeli Düzenle":
        st.info("Henüz eklenmiş personel yok.")
        return
    else:
        sicil_no_deger, ad_soyad_deger, unvan_deger, onceki_cevaplar = "", "", UNVAN_LISTESI[0], {}

    with st.form("personel_form"):
        c1, c2, c3 = st.columns(3)
        with c1:
            sicil_no = st.text_input("Sicil Numarası", value=str(sicil_no_deger), disabled=(mod == "Mevcut Personeli Düzenle"))
        with c2:
            ad_soyad = st.text_input("Ad Soyad", value=ad_soyad_deger)
        with c3:
            unvan = st.selectbox("Unvan", UNVAN_LISTESI, index=UNVAN_LISTESI.index(unvan_deger) if unvan_deger in UNVAN_LISTESI else 0)

        st.markdown("**Değerlendirme Soruları**")
        cevap_girisleri = {}
        for s in sorular:
            onceki_deger = onceki_cevaplar.get(str(s["soru_no"]), onceki_cevaplar.get(s["soru_no"], ""))
            if s["cevap_tipi"] == "metin":
                cevap_girisleri[s["soru_no"]] = st.text_area(s["soru_metni"], value=str(onceki_deger) if onceki_deger else "", key=f"soru_{s['soru_no']}")
            elif s["cevap_tipi"] == "sayisal":
                try:
                    varsayilan = float(onceki_deger) if onceki_deger else 0.0
                except ValueError:
                    varsayilan = 0.0
                cevap_girisleri[s["soru_no"]] = st.number_input(s["soru_metni"], value=varsayilan, key=f"soru_{s['soru_no']}")
            elif s["cevap_tipi"] in ("secmeli", "skala"):
                secenekler = [x.strip() for x in (s.get("secenekler") or "").split(",") if x.strip()]
                idx = secenekler.index(onceki_deger) if onceki_deger in secenekler else 0
                cevap_girisleri[s["soru_no"]] = st.selectbox(s["soru_metni"], secenekler, index=idx, key=f"soru_{s['soru_no']}")
            else:
                cevap_girisleri[s["soru_no"]] = st.text_input(s["soru_metni"], value=str(onceki_deger), key=f"soru_{s['soru_no']}")

        gonder = st.form_submit_button("💾 Kaydet", use_container_width=True)

    if gonder:
        if not sicil_no or not ad_soyad:
            st.warning("Sicil numarası ve ad soyad zorunludur.")
        else:
            cevaplar_payload = [{"soru_no": s["soru_no"], "soru_metni": s["soru_metni"], "cevap": cevap_girisleri[s["soru_no"]]} for s in sorular]
            sonuc = api_cagir("save_record", kullanici_adi=st.session_state.kullanici_adi, donem=donem,
                               sicil_no=sicil_no, personel_ad_soyad=ad_soyad, unvan=unvan, cevaplar=cevaplar_payload)
            if sonuc.get("success"):
                st.success("Kayıt başarıyla kaydedildi.")
                st.rerun()
            else:
                st.error(sonuc.get("error", "Kayıt sırasında hata oluştu."))

    if personeller:
        st.divider()
        st.subheader("Girilen Personel Listesi")
        df = pd.DataFrame([{"Sicil No": p["sicil_no"], "Ad Soyad": p["personel_ad_soyad"], "Unvan": p["unvan"]} for p in personeller])
        st.dataframe(df, use_container_width=True, hide_index=True)


# ==================== YÖNETİCİ PANELİ ====================
def yonetici_paneli():
    st.sidebar.title("🔑 Yönetici Paneli")
    if st.sidebar.button("Çıkış Yap"):
        st.session_state.giris_tipi = None
        st.rerun()

    st.title("🔑 Yönetici Kontrol Paneli")
    sekmeler = st.tabs(["📅 Dönemler", "❓ Sorular", "📊 Doldurma Durumu", "📥 Excel İndir", "🗂️ Loglar"])

    # --- DÖNEMLER ---
    with sekmeler[0]:
        st.subheader("Dönem Yönetimi")
        with st.form("yeni_donem_form"):
            c1, c2 = st.columns([3, 1])
            with c1:
                yeni_donem = st.text_input("Yeni Dönem (YYYY-AA formatında, örn. 2026-09)")
            with c2:
                st.write("")
                st.write("")
                ekle = st.form_submit_button("Ekle")
        if ekle and yeni_donem:
            sonuc = api_cagir("create_period", donem_adi=yeni_donem)
            if sonuc.get("success"):
                st.success("Dönem eklendi.")
                st.rerun()
            else:
                st.error(sonuc.get("error"))

        donemler_res = api_cagir("get_periods")
        donemler = donemler_res.get("donemler", [])
        for d in sorted(donemler, key=lambda x: x["donem_adi"], reverse=True):
            c1, c2 = st.columns([3, 1])
            c1.write(f"**{donem_etiket(d['donem_adi'])}** ({d['donem_adi']})")
            yeni_durum = c2.toggle("Aktif", value=d["aktif"], key=f"toggle_{d['donem_adi']}")
            if yeni_durum != d["aktif"]:
                api_cagir("toggle_period", donem_adi=d["donem_adi"], aktif=yeni_durum)
                st.rerun()

    # --- SORULAR ---
    with sekmeler[1]:
        st.subheader("Soru Yönetimi")
        sorular_res = api_cagir("get_questions")
        sorular = sorular_res.get("sorular", [])

        for s in sorular:
            with st.expander(f"Soru {s['soru_no']}: {s['soru_metni'][:50]}"):
                with st.form(f"soru_duzenle_{s['soru_no']}"):
                    metin = st.text_input("Soru Metni", value=s["soru_metni"], key=f"metin_{s['soru_no']}")
                    tip = st.selectbox("Cevap Tipi", ["metin", "sayisal", "secmeli", "skala"],
                                        index=["metin", "sayisal", "secmeli", "skala"].index(s["cevap_tipi"]),
                                        key=f"tip_{s['soru_no']}")
                    secenek = st.text_input("Seçenekler (virgülle ayırın, sadece seçmeli/skala için)",
                                             value=s.get("secenekler", ""), key=f"sec_{s['soru_no']}")
                    guncelle = st.form_submit_button("Güncelle")
                if guncelle:
                    api_cagir("save_question", soru_no=s["soru_no"], soru_metni=metin, cevap_tipi=tip, secenekler=secenek, aktif=True)
                    st.success("Soru güncellendi.")
                    st.rerun()

        st.divider()
        st.markdown("**Yeni Soru Ekle**")
        with st.form("yeni_soru_form"):
            yeni_metin = st.text_input("Soru Metni")
            yeni_tip = st.selectbox("Cevap Tipi", ["metin", "sayisal", "secmeli", "skala"], key="yeni_tip")
            yeni_secenek = st.text_input("Seçenekler (virgülle ayırın, örn: 1,2,3,4,5)", key="yeni_sec")
            soru_ekle = st.form_submit_button("Soru Ekle")
        if soru_ekle and yeni_metin:
            api_cagir("save_question", soru_no=None, soru_metni=yeni_metin, cevap_tipi=yeni_tip, secenekler=yeni_secenek, aktif=True)
            st.success("Soru eklendi.")
            st.rerun()

    # --- DOLDURMA DURUMU ---
    with sekmeler[2]:
        st.subheader("Doldurma Durumu")
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

    # --- EXCEL İNDİR ---
    with sekmeler[3]:
        st.subheader("Excel Raporu İndir")
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

        if st.button("📥 Excel Oluştur ve İndir"):
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
    with sekmeler[4]:
        st.subheader("Giriş / İşlem Logları")
        c1, c2, c3 = st.columns(3)
        ka_filtre = c1.text_input("Kullanıcı Adı Filtrele (boş = tümü)")
        bas_tarih = c2.date_input("Başlangıç Tarihi", value=None)
        bit_tarih = c3.date_input("Bitiş Tarihi", value=None)

        if st.button("Logları Getir"):
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
                st.info("Kayıt bulunamadı.")


# ==================== YÖNLENDİRME ====================
if APPS_SCRIPT_URL == "BURAYA_APPS_SCRIPT_WEB_APP_URL_YAPISTIRIN":
    st.warning("⚠️ Lütfen app.py içinde APPS_SCRIPT_URL değişkenini kendi Apps Script Web App URL'niz ile değiştirin.")

if st.session_state.giris_tipi is None:
    giris_ekrani()
elif st.session_state.giris_tipi == "kullanici":
    kullanici_paneli()
elif st.session_state.giris_tipi == "yonetici":
    yonetici_paneli()
