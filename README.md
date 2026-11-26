# JusTips (Flask + SQLite)

1. Pasang Python 3.9+ (https://python.org). Centang "Add Python to PATH" saat install di Windows.
2. Buka terminal di folder ini, lalu:

   python -m venv venv
   venv\Scripts\activate          (Windows)   |   source venv/bin/activate   (Mac/Linux)
   pip install -r requirements.txt
   python app.py

3. Buka http://localhost:3000

Database `justips.db` dibuat otomatis dari `schema.sql` beserta data contoh.
Akun demo (password: password123): pembeli `raniputri`, vendor `titiptokyo`.
Untuk mengulang dari data awal: hentikan server, hapus `justips.db*`, jalankan lagi.

Struktur:
- app.py          -> backend Flask (API, aturan peran, akses SQLite)
- schema.sql      -> definisi tabel
- public/index.html -> tampilan (memanggil /api/... milik Flask)
