# Panduan OAuth Gmail (readonly) untuk ingest-gmail

Tujuan: satu token **gmail.readonly** untuk job harian `ingest-gmail` (tanpa LLM). Token ini terpisah dari token `gmail-broker` milik zona comms (scope `gmail.modify`, dibuat di M4 dengan client berbeda). Akun: Gmail personal.

Semua langkah di bawah dikerjakan **di laptop Anda**. Token tidak pernah lewat chat.

## 1. Proyek Google Cloud
1. Buka https://console.cloud.google.com, buat proyek baru: `personal-agent-ingest`.
2. **APIs & Services -> Library**, cari **Gmail API**, klik **Enable**.

## 2. Layar persetujuan (OAuth consent screen)
1. **APIs & Services -> OAuth consent screen** (di UI baru: **Google Auth Platform -> Branding/Audience**).
2. User type: **External**. Nama aplikasi `personal-agent-ingest`, email dukungan dan kontak developer: email Anda.
3. **Scopes (Data Access):** tambahkan **`https://www.googleapis.com/auth/gmail.readonly`** saja.
4. **Audience:** tekan **Publish app** sehingga status menjadi **In production**.
   - Penting: pada mode **Testing**, refresh token kedaluwarsa dalam 7 hari. Pada **In production** tidak.
   - Aplikasi akan tanpa verifikasi Google. Itu diterima untuk akun tunggal Anda: saat login muncul peringatan "Google hasn't verified this app", pilih **Advanced -> Go to personal-agent-ingest (unsafe)**. Batas 100 pengguna tidak relevan.
5. Jangan menambahkan scope lain. Scope `gmail.readonly` tidak bisa mengirim, mengubah, atau menghapus email.

## 3. Client OAuth
1. **APIs & Services -> Credentials -> Create credentials -> OAuth client ID**.
2. Application type: **Desktop app**, nama `ingest-desktop`.
3. Klik **Download JSON** dan simpan sebagai `~/client_secret_ingest.json` di laptop. Jangan commit file ini.

## 4. Buat token (di laptop)
```
python3 -m venv ~/.venv-gmail && ~/.venv-gmail/bin/pip install google-auth-oauthlib
~/.venv-gmail/bin/python scripts/gmail-auth.py ~/client_secret_ingest.json | \
  ssh ubuntu@43.157.242.194 'sudo bash -c "umask 077; cat > /opt/personal-agent-secrets/gmail_ingest_token && chmod 0444 /opt/personal-agent-secrets/gmail_ingest_token"'
```
- Browser terbuka; login ke akun Gmail Anda dan setujui **hanya baca** email.
- Skrip tidak mencetak token. Isi token (refresh token) langsung masuk ke file root di VPS lewat SSH.
- Kalau file sudah ada dan ingin menggantinya, hapus dulu di VPS (`sudo rm /opt/personal-agent-secrets/gmail_ingest_token`).

Simpan juga `client_secret_ingest.json` ke VPS dengan cara yang sama (`gmail_ingest_client`), karena ingest-gmail memakainya untuk menukar refresh token:
```
ssh ubuntu@43.157.242.194 'sudo bash -c "umask 077; cat > /opt/personal-agent-secrets/gmail_ingest_client && chmod 0444 /opt/personal-agent-secrets/gmail_ingest_client"' < ~/client_secret_ingest.json
```

## 5. Label dan allowlist
- Buat label Gmail `Keuangan/Kartu Kredit` dan filter yang memberinya label untuk pengirim bank (DBS, CIMB Niaga, HSBC, Mandiri, Mega). Job mengambil **ID label** lewat `labels.list`, tidak mengandalkan pencarian teks.
- Pengirim yang diizinkan (allowlist) dan syarat tambahan `Authentication-Results` DKIM/DMARC pass:
  | Bank | Pengirim |
  |---|---|
  | DBS | dbsistatement@dbs.com |
  | CIMB Niaga | CreditCard.Estatement@cimbniaga.co.id |
  | HSBC | creditcard-hsbcindonesia@mail.hsbc.co.id |
  | Mandiri | ebillingmandirikartukredit@bankmandiri.co.id |
  | Mega | e-billing@bankmega.com |
- Jenius dan BCA: unggah manual lewat Telegram.

## 6. Rotasi / pencabutan
- Cabut akses kapan saja di https://myaccount.google.com/permissions (hapus `personal-agent-ingest`).
- Rotasi: hapus file token di VPS, ulangi langkah 4.

## Catatan keamanan
- `gmail.readonly` memungkinkan membaca **seluruh** email, bukan hanya label Keuangan. Pembatasan ke label dilakukan di kode ingest-gmail, bukan oleh Google. Karena itu job ini deterministik, tanpa LLM, dan tidak punya jalur keluar selain `gmail.googleapis.com` dan `oauth2.googleapis.com`.
- Skrip `scripts/gmail-auth.py` belum diuji dengan client asli. Jalankan di laptop dan laporkan hasilnya.
