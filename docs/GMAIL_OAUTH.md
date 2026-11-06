# Panduan OAuth Gmail (readonly) untuk ingest-gmail

Tujuan: satu token **gmail.readonly** untuk job harian `ingest-gmail` (tanpa LLM). Token ini terpisah dari dua token milik zona comms (`gmail.modify` untuk gmail-broker dan `calendar.events.readonly` untuk calendar-broker), yang dibuat dari proyek dan client lain: bagian "Zona comms" di akhir. Akun: Gmail personal.

Semua langkah di bawah dikerjakan **di laptop Anda**. Token tidak pernah lewat chat.

## 1. Proyek Google Cloud
1. Buka https://console.cloud.google.com, buat proyek baru: `personal-agent-ingest`.
2. **APIs & Services -> Library**, cari **Gmail API**, klik **Enable**.

## 2. Layar persetujuan (OAuth consent screen)
1. **APIs & Services -> OAuth consent screen** (di UI baru: **Google Auth Platform -> Branding/Audience**).
2. User type: **External**. Nama aplikasi `personal-agent-ingest`, email dukungan dan kontak developer: email Anda.
3. **Scopes (Data Access):** tambahkan **`https://www.googleapis.com/auth/gmail.readonly`** saja.
4. **Audience (mode Testing, dipakai saat ini):** biarkan status **Testing**, lalu di **Test users** klik **Add users** dan tambahkan email Gmail Anda sendiri.
   - Konsekuensi: pada mode **Testing**, refresh token **kedaluwarsa dalam 7 hari**. Job `pa-gmail-token` (harian 08:00 WIB) mengirim peringatan lewat bot control mulai 2 hari sebelum habis; Anda cukup menjalankan ulang langkah 4 di bawah (sekitar satu menit).
   - Kalau ingest harian 06:00 WIB gagal, misalnya karena Google menolak token, job `pa-ingest-alert` langsung mengirim pesan lewat bot control berisi penyebabnya dan apa yang perlu Anda lakukan.
   - Untuk membuat token tidak kedaluwarsa, aplikasi harus **Publish -> In production**. Itu mensyaratkan domain terverifikasi (homepage + privacy policy di domain milik sendiri). Anda belum punya domain, jadi jalur ini ditunda. Kalau nanti punya, publish aplikasi lalu buat token baru; timer peringatan bisa dimatikan.
   - Saat login akan muncul peringatan "Google hasn't verified this app": pilih **Advanced -> Go to personal-agent-ingest (unsafe)**.
5. Jangan menambahkan scope lain. Scope `gmail.readonly` tidak bisa mengirim, mengubah, atau menghapus email.

## 3. Client OAuth
1. **APIs & Services -> Credentials -> Create credentials -> OAuth client ID**.
2. Application type: **Desktop app**, nama `ingest-desktop`.
3. Klik **Download JSON** dan simpan sebagai `~/client_secret_ingest.json` di laptop. Jangan commit file ini.

## 4. Buat atau perbarui token (di laptop)
Sekali saja: `python3 -m venv ~/.venv-gmail && ~/.venv-gmail/bin/pip install google-auth-oauthlib`. Lalu, dari folder repo:
```
bash scripts/gmail-renew.sh ~/client_secret_ingest.json
```
- Skrip mencetak sebuah URL. Buka di browser, login ke akun Gmail Anda, dan setujui **hanya baca** email.
- Token tidak pernah tercetak dan tidak disimpan di laptop. `scripts/gmail-auth.py` menulisnya ke pipa SSH, dan di VPS token masuk ke file sementara di sebelah token lama.
- Token lama baru diganti setelah token baru lengkap (JSON dengan refresh token dan tanggal terbit) dan dibuat dengan client yang sama dengan yang tersimpan di VPS untuk token itu. Penggantiannya menulis ulang file yang sama (inode tetap, karena compose me-mount file ini ke ingest-gmail). Login yang gagal, kehabisan waktu, atau dibatalkan membiarkan token lama tetap dipakai, jadi file lama tidak perlu dihapus dulu.
- Jangan menjalankan `scripts/gmail-auth.py` sendirian: tanpa pipa token akan tercetak di layar, dan skrip menolak bila keluarannya terminal.

Simpan juga `client_secret_ingest.json` ke VPS dengan cara yang sama (`gmail_ingest_client`), karena ingest-gmail memakainya untuk menukar refresh token. Ganti `<vps>` dengan alamat di `config/vps.env`:
```
ssh ubuntu@<vps> 'sudo bash -c "umask 077; cat > /opt/personal-agent-secrets/gmail_ingest_client && chmod 0444 /opt/personal-agent-secrets/gmail_ingest_client"' < ~/client_secret_ingest.json
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
- Rotasi: ulangi langkah 4. Token lama diganti setelah yang baru lengkap.

## Catatan keamanan
- `gmail.readonly` memungkinkan membaca **seluruh** email, bukan hanya label Keuangan. Pembatasan ke label dilakukan di kode ingest-gmail, bukan oleh Google. Karena itu job ini deterministik, tanpa LLM, dan tidak punya jalur keluar selain `gmail.googleapis.com` dan `oauth2.googleapis.com`.
- Kedua skrip sudah dipakai dengan client asli: token pertama dibuat 27 Okt 2026 dengan `scripts/gmail-auth.py`, dan perpanjangan pertama lewat `scripts/gmail-renew.sh` berhasil 2 Nov 2026.

## Zona comms (M4, dibangun 2 Nov 2026, belum dipakai)
Asisten email dan kalender (comms) butuh dua token Google lagi: `gmail_comms_token` (scope **`gmail.modify`**, untuk gmail-broker) dan `calendar_comms_token` (scope **`calendar.events.readonly`**, untuk calendar-broker). Hanya kedua broker yang memegangnya; comms sendiri tidak pernah memegang token Google (`docs/SECURITY.md`, zona comms). Kerjakan ini hanya setelah Anda memutuskan pertanyaan terbuka 18 di `docs/PROGRESS.md`; urutan lengkapnya ada di `docs/RUNBOOK.md`, "Comms zone".

1. Proyek Google Cloud baru `personal-agent-comms`, bukan proyek ingest, supaya scope dan pencabutannya terpisah. Di **APIs & Services -> Library**, aktifkan **Gmail API** dan **Google Calendar API**.
2. Layar persetujuan seperti bagian 2: **External**, nama aplikasi `personal-agent-comms`, status **Testing**, dan email Gmail Anda sendiri sebagai test user. Scope: **`https://www.googleapis.com/auth/gmail.modify`** dan **`https://www.googleapis.com/auth/calendar.events.readonly`** saja.
3. Client OAuth seperti bagian 3: **Desktop app**, nama `comms-desktop`. Simpan JSON-nya sebagai `~/client_secret_comms.json` di laptop. Jangan commit file ini.
4. Simpan client itu ke VPS sebagai `google_comms_client`. Ganti `<vps>` dengan alamat di `config/vps.env`:
   ```
   ssh ubuntu@<vps> 'sudo bash -c "umask 077; cat > /opt/personal-agent-secrets/google_comms_client && chmod 0444 /opt/personal-agent-secrets/google_comms_client"' < ~/client_secret_comms.json
   ```
5. Dua persetujuan, satu per token, dari folder repo:
   ```
   bash scripts/gmail-renew.sh ~/client_secret_comms.json gmail_comms_token
   bash scripts/gmail-renew.sh ~/client_secret_comms.json calendar_comms_token
   ```
   - Tiap perintah mencetak URL. Login, lalu setujui scope yang diminta. Skrip menolak token dengan scope lain, misalnya bila kotak centangnya Anda lepas.
   - Untuk `gmail.modify`, layar Google menyebut aplikasi bisa membaca, menulis, dan mengirim email. Google memang tidak punya scope untuk draf tanpa mengirim. Yang membuat comms tidak bisa mengirim adalah gmail-broker: daftar panggilannya tidak memuat kirim, hapus, buang ke sampah, filter, atau penerusan.
   - Nama token yang tidak dikenal ditolak sebelum SSH. Tanpa nama token, skrip memperbarui token ingest seperti di bagian 4.
   - Token yang dibuat dengan client lain dari yang tersimpan di VPS untuk token itu ditolak, dan token lama tetap dipakai. Contohnya `~/client_secret_comms.json` tanpa nama token: token ingest yang masih berlaku tidak tertimpa.
6. Mode **Testing**: kedua token comms juga kedaluwarsa dalam **7 hari**, jadi setiap minggu ada tiga perpanjangan bersama token ingest. Ulangi langkah 5 sebelum habis. Broker membaca file token lagi sebelum setiap refresh, jadi tidak perlu restart. Belum ada job yang memperingatkan token comms; bila token habis, comms menjawab bahwa token perlu diperbarui dari laptop.
7. Yang tersembunyi dari comms: email berlabel `Keuangan` atau sublabelnya (termasuk `Keuangan/Kartu Kredit` dari bagian 5), dan email dari domain lima bank di tabel bagian 5. Label baru di bawah `Keuangan/` langsung ikut tersembunyi. Email bank lain (mis. BCA, Jago, Jenius) **tidak** tersembunyi, kecuali Anda memberinya label di bawah `Keuangan/` lewat filter Gmail.
8. Pencabutan: hapus `personal-agent-comms` di https://myaccount.google.com/permissions. Kedua token comms berhenti, sedangkan token ingest tidak terpengaruh.
