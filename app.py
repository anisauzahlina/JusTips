"""JusTips - backend Flask + SQLite.

Menggantikan server.js (Node). API-nya sama persis, jadi public/index.html
tidak perlu diubah.
"""
import hashlib
import hmac
import os
import secrets
import sqlite3
import uuid
from datetime import date, datetime

from flask import Flask, g, jsonify, request, send_from_directory

BASE = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE, "justips.db")

app = Flask(__name__, static_folder=os.path.join(BASE, "public"), static_url_path="")
app.config["MAX_CONTENT_LENGTH"] = 6 * 1024 * 1024  # batas upload 6 MB

CITY = {"Jepang": "Tokyo", "Korea": "Seoul", "Tiongkok": "Shanghai",
        "Thailand": "Bangkok", "Singapura": "Singapura"}


class Err(Exception):
    """Error yang pesannya boleh ditampilkan ke pengguna."""


# ---------------------------------------------------------------- database
def db():
    if "db" not in g:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys=ON")
        g.db = conn
    return g.db


@app.teardown_appcontext
def close_db(_):
    conn = g.pop("db", None)
    if conn:
        conn.close()


def q(sql, *args):
    return db().execute(sql, args)


def one(sql, *args):
    r = q(sql, *args).fetchone()
    return dict(r) if r else None


def many(sql, *args):
    return [dict(r) for r in q(sql, *args).fetchall()]


def init_db():
    conn = sqlite3.connect(DB_PATH)
    with open(os.path.join(BASE, "schema.sql"), encoding="utf-8") as f:
        conn.executescript(f.read())
    conn.commit()
    conn.close()


# ---------------------------------------------------------------- helper
def hash_pw(p):
    s = secrets.token_hex(16)
    h = hashlib.scrypt(p.encode(), salt=s.encode(), n=16384, r=8, p=1, dklen=32)
    return s + ":" + h.hex()


def check_pw(p, stored):
    try:
        s, x = stored.split(":")
        h = hashlib.scrypt(p.encode(), salt=s.encode(), n=16384, r=8, p=1, dklen=32)
        return hmac.compare_digest(bytes.fromhex(x), h)
    except Exception:
        return False


def num(x, default=0):
    try:
        return int(float(x))
    except (TypeError, ValueError):
        return default


def hh():
    return datetime.now().strftime("%H.%M")


def rp(n):
    return "Rp" + f"{n:,}".replace(",", ".")


def note(uid, judul, isi, rute, label):
    q("INSERT INTO notifications(user_id,judul,isi,rute,label) VALUES(?,?,?,?,?)",
      uid, judul, isi, rute, label)


def vendor_user(vid):
    return one("SELECT user_id FROM vendors WHERE id=?", vid)["user_id"]


def my_vendor(u):
    return one("SELECT * FROM vendors WHERE user_id=?", u["id"])


def total(o):
    p = one("SELECT harga,jasa FROM products WHERE id=?", o["product_id"])
    return (p["harga"] + p["jasa"]) * o["qty"] + o["ongkir"] + o["biaya_impor"]


# ---------------------------------------------------------------- seed data
def seed():
    if one("SELECT COUNT(*) c FROM users")["c"]:
        return

    def user(nama, uname, email, role, alamat=""):
        return q("INSERT INTO users(nama,username,email,password_hash,role,tgl_lahir,telp,alamat) "
                 "VALUES(?,?,?,?,?,?,?,?)", nama, uname, email, hash_pw("password123"), role,
                 "1999-01-01", "+62 812 3456 7890", alamat).lastrowid

    rani = user("Rani Putri", "raniputri", "rani@email.com", "buyer",
                "Jl. Melati No. 12, Jakarta Selatan, DKI Jakarta 12345")

    vendors = [
        (1, "Titip Tokyo", "Jepang", "Tokyo", 4.9, 128, "Pakaian · Aksesoris · Merchandise", "titiptokyo"),
        (2, "Titip Seoul", "Korea", "Seoul", 4.8, 96, "Skincare · Pakaian", "titipseoul"),
        (3, "Titip Bangkok Bareng", "Thailand", "Bangkok", 4.7, 84, "Beverages · Herbs", "titipbangkok"),
        (4, "Titip Shanghai", "Tiongkok", "Shanghai", 4.9, 156, "Perabotan · Aksesoris", "titipshanghai"),
        (5, "Titip Singapura", "Singapura", "Singapura", 4.8, 72, "Merchandise · Perabotan", "titipsingapura"),
        (6, "Titip Osaka Pilihan", "Jepang", "Osaka", 4.6, 53, "Pakaian · Skincare", "titiposaka"),
    ]
    for vid, nama, negara, kota, rating, selesai, kat, uname in vendors:
        uid = user(nama, uname, uname + "@justips.id", "vendor")
        q("INSERT INTO vendors(id,user_id,nama_toko,negara,kota,rating,selesai,kategori,deskripsi) "
          "VALUES(?,?,?,?,?,?,?,?,?)", vid, uid, nama, negara, kota, rating, selesai, kat,
          f"Jastip dari {kota}. Barang dikemas rapi, komunikasi cepat.")

    products = [
        (1, "Tas kanvas Jepang", "Accessories", 250000, 35000, 4.9, 32, 1),
        (2, "Botol minum Korea", "Accessories", 180000, 28000, 4.8, 24, 2),
        (3, "Teh pilihan Thailand", "Beverages", 120000, 32000, 4.7, 19, 3),
        (4, "Serum wajah Korea", "Skincare", 220000, 30000, 4.9, 46, 2),
        (5, "Anime Figure Naruto", "Merchandise", 450000, 40000, 4.8, 21, 6),
        (6, "Korea Skincare Eyebags", "Skincare", 150000, 25000, 4.6, 12, 2),
        (7, "Baju cosplay kagura", "Clothing", 320000, 45000, 4.7, 15, 4),
        (8, "Pokemon card Singapura", "Merchandise", 175000, 30000, 4.9, 33, 5),
        (9, "Kaos katun Jepang", "Clothing", 280000, 28000, 4.8, 24, 1),
        (10, "Gantungan karakter", "Merchandise", 95000, 32000, 4.7, 19, 1),
        (11, "Mochi Package", "Beverages", 120000, 32000, 4.7, 19, 6),
        (12, "Kursi lipat kayu", "Furniture", 600000, 60000, 4.5, 8, 4),
    ]
    for p in products:
        q("INSERT INTO products(id,nama,kategori,harga,jasa,rating,ulasan,vendor_id) "
          "VALUES(?,?,?,?,?,?,?,?)", *p)

    q("INSERT INTO orders(id,buyer_id,vendor_id,product_id,qty,status,warna) VALUES"
      "('AJ-001',?,1,1,1,'menunggu','Natural'),('JT-001',?,1,1,1,'dikemas','Natural')", rani, rani)
    t = vendor_user(1)
    note(t, "Pengajuan baru AJ-001", "Rani Putri mengajukan Tas kanvas Jepang (1x).", "v-pesanan", "Tinjau pengajuan")
    note(t, "Pesanan masuk #JT-001", "Rani Putri sudah membayar Rp330.000. Siapkan & kirim barang.", "v-pesanan", "Proses pesanan")
    note(rani, "Pembayaran berhasil", "PayPal mengonfirmasi Rp330.000 untuk #JT-001.", "pesanan", "Lihat pembayaran")
    note(rani, "Selamat datang di JusTips", "Lengkapi profil agar pengalaman jastip lebih mudah.", "profil", "Lengkapi profil")
    q("INSERT INTO messages(buyer_id,vendor_id,pengirim,isi,waktu) VALUES"
      "(?,1,'b','Halo, apakah tas warna natural masih tersedia?','09.40'),"
      "(?,1,'v','Tersedia. Barang Rp250.000 + jasa Rp35.000. Estimasi ongkir Rp45.000.','09.42')", rani, rani)
    db().commit()


# ---------------------------------------------------------------- state
def build_state(u):
    vd = u["role"] == "vendor"
    v = my_vendor(u) if vd else None
    chats, cn = {}, {}
    if vd:
        rows = many("SELECT m.*, b.nama bn FROM messages m JOIN users b ON b.id=m.buyer_id "
                    "WHERE vendor_id=? ORDER BY m.id", v["id"])
    else:
        rows = many("SELECT * FROM messages WHERE buyer_id=? ORDER BY id", u["id"])
    for m in rows:
        k = m["buyer_id"] if vd else m["vendor_id"]
        chats.setdefault(str(k), []).append({"f": m["pengirim"], "t": m["isi"], "h": m["waktu"]})
        if vd:
            cn[str(k)] = m["bn"]

    who = "o.vendor_id" if vd else "o.buyer_id"
    return {
        "me": {"nama": u["nama"], "username": u["username"], "email": u["email"], "telp": u["telp"],
               "alamat": u["alamat"], "role": u["role"], "vid": v["id"] if v else 0},
        "products": many("SELECT p.id,p.nama n,v.negara k,p.kategori cat,p.harga p,p.jasa j,p.rating r,"
                         "p.ulasan rv,v.kota c,p.vendor_id v,p.foto img FROM products p "
                         "JOIN vendors v ON v.id=p.vendor_id ORDER BY p.id DESC"),
        "vendors": many("SELECT id,nama_toko n,negara k,kota c,rating r,selesai o,kategori cat FROM vendors"),
        "shop": ({"d": v["deskripsi"], "est": v["estimasi"], "open": bool(v["aktif"]), "pp": v["paypal"] or ""}
                 if v else None),
        "fav": [x["id"] for x in many("SELECT product_id id FROM favorites WHERE user_id=?", u["id"])],
        "cart": [{"id": c["id"], "pid": c["pid"], "q": c["q"], "on": bool(c["on1"])} for c in
                 many("SELECT id,product_id pid,qty q,dipilih on1 FROM cart_items WHERE user_id=? ORDER BY id", u["id"])],
        "orders": many("SELECT o.id,o.product_id pid,o.qty q,o.vendor_id v,o.status st,o.ongkir ong,"
                       "o.biaya_impor imp,o.warna col,COALESCE(o.resi,'') resi,b.nama bn,b.alamat ba "
                       f"FROM orders o JOIN users b ON b.id=o.buyer_id WHERE {who}=? ORDER BY o.rowid DESC",
                       v["id"] if vd else u["id"]),
        "notes": [{"id": n["id"], "t": n["judul"], "d": n["isi"], "u": not n["dibaca"], "go": n["rute"],
                   "l": n["label"], "to": "v" if vd else "b"} for n in
                  many("SELECT id,judul,isi,rute,label,dibaca FROM notifications WHERE user_id=? ORDER BY id DESC", u["id"])],
        "chats": chats,
        "cn": cn,
    }


# ---------------------------------------------------------------- aksi
def order_buyer(u, oid, status=None):
    o = one("SELECT * FROM orders WHERE id=? AND buyer_id=?", oid, u["id"])
    if not o or (status and o["status"] != status):
        raise Err("Pesanan tidak valid atau statusnya sudah berubah.")
    return o


def order_vendor(u, oid, status=None):
    v = my_vendor(u)
    o = v and one("SELECT * FROM orders WHERE id=? AND vendor_id=?", oid, v["id"])
    if not o or (status and o["status"] != status):
        raise Err("Pesanan tidak valid atau statusnya sudah berubah.")
    return o


def set_status(oid, st):
    q("UPDATE orders SET status=? WHERE id=?", st, oid)


def a_fav(u, b):
    if not q("DELETE FROM favorites WHERE user_id=? AND product_id=?", u["id"], b.get("id")).rowcount:
        q("INSERT INTO favorites VALUES(?,?)", u["id"], b.get("id"))


def a_cart_add(u, b):
    n = max(1, num(b.get("q")))
    if not q("UPDATE cart_items SET qty=qty+? WHERE user_id=? AND product_id=?", n, u["id"], b.get("pid")).rowcount:
        q("INSERT INTO cart_items(user_id,product_id,qty) VALUES(?,?,?)", u["id"], b.get("pid"), n)


def a_cart_set(u, b):
    if b.get("k") == "on":
        q("UPDATE cart_items SET dipilih=? WHERE id=? AND user_id=?", int(bool(b.get("v"))), b.get("id"), u["id"])
    else:
        q("UPDATE cart_items SET qty=? WHERE id=? AND user_id=?", max(1, num(b.get("v"))), b.get("id"), u["id"])


def a_cart_del(u, b):
    q("DELETE FROM cart_items WHERE id=? AND user_id=?", b.get("id"), u["id"])


def a_ajukan(u, b):
    for i in b.get("items") or []:
        p = one("SELECT p.*, v.aktif FROM products p JOIN vendors v ON v.id=p.vendor_id WHERE p.id=?", i.get("pid"))
        n = max(1, num(i.get("q")))
        if not p:
            raise Err("Barang tidak ditemukan.")
        if not p["aktif"]:
            raise Err("Toko sedang tutup.")
        oid = "AJ-" + str(one("SELECT COUNT(*) c FROM orders")["c"] + 1).zfill(3)
        q("INSERT INTO orders(id,buyer_id,vendor_id,product_id,qty,status,warna) VALUES(?,?,?,?,?,'menunggu',?)",
          oid, u["id"], p["vendor_id"], p["id"], n, b.get("col") or "Natural")
        q("DELETE FROM cart_items WHERE user_id=? AND product_id=?", u["id"], p["id"])
        note(vendor_user(p["vendor_id"]), "Pengajuan baru " + oid,
             f"{u['nama']} mengajukan {p['nama']} ({n}x).", "dasbor", "Tinjau pengajuan")


def a_vtrm(u, b):
    o = order_vendor(u, b.get("id"), "menunggu")
    q("UPDATE orders SET status='diterima', ongkir=?, biaya_impor=? WHERE id=?",
      max(0, num(b.get("ong"))), max(0, num(b.get("imp"))), o["id"])
    note(o["buyer_id"], "Penawaran baru dari vendor",
         f"Vendor mengirim rincian biaya untuk #{o['id']}. Silakan bayar.", "pesanan", "Lihat pesanan")
    baru = one("SELECT * FROM orders WHERE id=?", o["id"])
    q("INSERT INTO messages(buyer_id,vendor_id,pengirim,isi,waktu) VALUES(?,?,'v',?,?)",
      o["buyer_id"], o["vendor_id"],
      f"Pengajuan #{o['id']} diterima. Total {rp(total(baru))} (termasuk ongkir). Silakan lanjut pembayaran.", hh())


def a_vtlk(u, b):
    o = order_vendor(u, b.get("id"), "menunggu")
    set_status(o["id"], "ditolak")
    note(o["buyer_id"], "Pengajuan ditolak", f"Maaf, vendor belum bisa memenuhi pengajuan #{o['id']}",
         "pesanan", "Lihat pesanan")


def a_remind(u, b):
    o = order_vendor(u, b.get("id"), "diterima")
    note(o["buyer_id"], "Menunggu pembayaran", f"Vendor menunggu pembayaran untuk #{o['id']}.",
         "pesanan", "Bayar sekarang")


def a_bayar(u, b):
    o = order_buyer(u, b.get("id"), "diterima")
    set_status(o["id"], "dikemas")
    t = rp(total(o))
    note(u["id"], "Pembayaran berhasil", f"PayPal mengonfirmasi {t} untuk #{o['id']}.", "pesanan", "Lihat pembayaran")
    note(vendor_user(o["vendor_id"]), f"Pesanan masuk #{o['id']}",
         f"{u['nama']} sudah membayar {t}. Siapkan & kirim barang.", "v-pesanan", "Proses pesanan")


def a_mulai(u, b):
    o = order_vendor(u, b.get("id"), "dikemas")
    set_status(o["id"], "siap")
    note(o["buyer_id"], "Pesanan sedang dikemas", f"Vendor sedang mengemas #{o['id']}.", "pesanan", "Lihat pesanan")


def a_kirim(u, b):
    o = order_vendor(u, b.get("id"), "siap")
    resi = str(b.get("resi") or "").strip()[:60]
    if not resi:
        raise Err("Isi nomor resi dulu.")
    kurir = str(b.get("kurir") or "")[:40]
    q("UPDATE orders SET status='dikirim', resi=? WHERE id=?", f"{kurir} · {resi}", o["id"])
    note(o["buyer_id"], "Pesanan dikirim", f"#{o['id']} dikirim via {kurir}, resi {resi}.", "pesanan", "Lacak pesanan")


def a_selesai(u, b):
    o = order_buyer(u, b.get("id"), "dikirim")
    set_status(o["id"], "selesai")
    q("UPDATE vendors SET selesai=selesai+1 WHERE id=?", o["vendor_id"])
    note(vendor_user(o["vendor_id"]), f"Pesanan selesai #{o['id']}",
         "Pembeli mengonfirmasi barang diterima.", "v-pesanan", "Lihat")


def a_msg(u, b):
    t = str(b.get("t") or "").strip()[:1000]
    if not t:
        raise Err("Pesan kosong.")
    if u["role"] == "buyer":
        if not one("SELECT 1 FROM vendors WHERE id=?", b.get("to")):
            raise Err("Vendor tidak ditemukan.")
        q("INSERT INTO messages(buyer_id,vendor_id,pengirim,isi,waktu) VALUES(?,?,'b',?,?)",
          u["id"], b.get("to"), t, hh())
    else:
        if not one("SELECT 1 FROM users WHERE id=? AND role='buyer'", b.get("to")):
            raise Err("Pembeli tidak ditemukan.")
        q("INSERT INTO messages(buyer_id,vendor_id,pengirim,isi,waktu) VALUES(?,?,'v',?,?)",
          b.get("to"), my_vendor(u)["id"], t, hh())


def a_add_prod(u, b):
    if not b.get("n") or not num(b.get("p")) > 0 or not num(b.get("j")) > 0:
        raise Err("Nama, harga, dan jasa wajib diisi.")
    img = b.get("img")
    if img and (not str(img).startswith("data:image/") or len(img) > 4_000_000):
        raise Err("Foto tidak valid atau terlalu besar.")
    q("INSERT INTO products(vendor_id,nama,kategori,harga,jasa,stok,deskripsi,foto) VALUES(?,?,?,?,?,?,?,?)",
      my_vendor(u)["id"], str(b["n"])[:120], b.get("cat"), num(b.get("p")), num(b.get("j")),
      num(b.get("stok")), str(b.get("d") or "")[:1000], img or None)


def a_del_prod(u, b):
    if not q("DELETE FROM products WHERE id=? AND vendor_id=?", b.get("id"), my_vendor(u)["id"]).rowcount:
        raise Err("Barang tidak ditemukan.")


def a_save_shop(u, b):
    if not str(b.get("n") or "").strip():
        raise Err("Nama toko wajib diisi.")
    k = b.get("k") if b.get("k") in CITY else "Jepang"
    q("UPDATE vendors SET nama_toko=?,negara=?,kota=?,kategori=?,deskripsi=?,estimasi=?,aktif=?,paypal=? "
      "WHERE user_id=?", b["n"], k, CITY[k], b.get("cat"), b.get("d"), b.get("est"),
      int(bool(b.get("open"))), b.get("pp"), u["id"])


def a_save_prof(u, b):
    q("UPDATE users SET nama=?,username=?,telp=?,email=?,alamat=? WHERE id=?",
      b.get("nama"), b.get("username"), b.get("telp"), b.get("email"), b.get("alamat"), u["id"])


def a_read_n(u, b):
    if b.get("id"):
        q("UPDATE notifications SET dibaca=1 WHERE id=? AND user_id=?", b["id"], u["id"])
    else:
        q("UPDATE notifications SET dibaca=1 WHERE user_id=?", u["id"])


# nama aksi -> (peran yang boleh, fungsi). None = semua peran.
ACTIONS = {
    "fav": (None, a_fav), "cartAdd": ("buyer", a_cart_add), "cartSet": ("buyer", a_cart_set),
    "cartDel": ("buyer", a_cart_del), "ajukan": ("buyer", a_ajukan), "vtrm": ("vendor", a_vtrm),
    "vtlk": ("vendor", a_vtlk), "remind": ("vendor", a_remind), "bayar": ("buyer", a_bayar),
    "mulai": ("vendor", a_mulai), "kirim": ("vendor", a_kirim), "selesai": ("buyer", a_selesai),
    "msg": (None, a_msg), "addProd": ("vendor", a_add_prod), "delProd": ("vendor", a_del_prod),
    "saveShop": ("vendor", a_save_shop), "saveProf": (None, a_save_prof), "readN": (None, a_read_n),
}


# ---------------------------------------------------------------- routes
def fail(e):
    if isinstance(e, Err):
        msg = str(e)
    elif isinstance(e, sqlite3.IntegrityError) and "UNIQUE" in str(e):
        msg = "Data sudah dipakai."
    elif isinstance(e, sqlite3.IntegrityError) and "FOREIGN" in str(e):
        msg = "Data masih terkait pesanan."
    else:
        app.logger.exception(e)
        msg = "Terjadi kesalahan."
    return jsonify(err=msg), 400


def make_session(uid):
    token = str(uuid.uuid4())
    q("INSERT INTO sessions(token,user_id) VALUES(?,?)", token, uid)
    db().commit()
    return token


def current_user():
    return one("SELECT u.* FROM sessions x JOIN users u ON u.id=x.user_id WHERE x.token=?",
               request.headers.get("Authorization", ""))


@app.route("/")
def index():
    return send_from_directory(app.static_folder, "index.html")


@app.post("/api/register")
def register():
    try:
        b = request.get_json(silent=True) or {}
        if b.get("role") not in ("buyer", "vendor"):
            raise Err("Peran tidak valid.")
        for k in ("nama", "username", "email", "tgl_lahir"):
            if not str(b.get(k) or "").strip():
                raise Err("Lengkapi semua kolom wajib.")
        email = b["email"]
        if "@" not in email or "." not in email.split("@")[-1] or " " in email:
            raise Err("Format email tidak valid.")
        if len(b.get("password") or "") < 8:
            raise Err("Password minimal 8 karakter.")
        try:
            d = date.fromisoformat(str(b["tgl_lahir"])[:10])
            t = date.today()
            umur = t.year - d.year - ((t.month, t.day) < (d.month, d.day))
        except ValueError:
            umur = 0
        if umur < 17:
            raise Err("Pendaftaran ditolak: usia minimal 17 tahun.")
        if one("SELECT 1 FROM users WHERE email=? OR username=?", b["email"], b["username"]):
            raise Err("Email atau username sudah dipakai.")
        uid = q("INSERT INTO users(nama,username,email,password_hash,role,tgl_lahir,telp) VALUES(?,?,?,?,?,?,?)",
                b["nama"], b["username"], b["email"], hash_pw(b["password"]), b["role"],
                b["tgl_lahir"], b.get("telp") or "").lastrowid
        if b["role"] == "vendor":
            k = b.get("negara") if b.get("negara") in CITY else "Jepang"
            q("INSERT INTO vendors(user_id,nama_toko,negara,kota,kategori,deskripsi) VALUES(?,?,?,?,?,?)",
              uid, "Titip " + b["nama"].split(" ")[0], k, CITY[k], b.get("kategori") or "Umum", "Toko baru di JusTips.")
        return jsonify(token=make_session(uid))
    except Exception as e:
        db().rollback()
        return fail(e)


@app.post("/api/login")
def login():
    b = request.get_json(silent=True) or {}
    u = one("SELECT * FROM users WHERE email=? OR username=?", b.get("id"), b.get("id"))
    if not u or not check_pw(b.get("password") or "", u["password_hash"]):
        return jsonify(err="Email/username atau password salah."), 401
    if u["role"] != b.get("role"):
        peran = "Vendor" if u["role"] == "vendor" else "Pembeli"
        return jsonify(err=f"Akun ini terdaftar sebagai {peran}. Pilih tab yang sesuai."), 401
    return jsonify(token=make_session(u["id"]))


@app.get("/api/state")
def state():
    u = current_user()
    if not u:
        return jsonify(err="Belum masuk"), 401
    return jsonify(build_state(u))


@app.post("/api/act")
def act():
    u = current_user()
    if not u:
        return jsonify(err="Belum masuk"), 401
    try:
        b = request.get_json(silent=True) or {}
        role, fn = ACTIONS.get(b.get("a"), (None, None))
        if not fn:
            raise Err("Aksi tidak dikenal.")
        if role and role != u["role"]:
            raise Err("Tidak diizinkan.")
        fn(u, b)
        db().commit()
        return jsonify(ok=1)
    except Exception as e:
        db().rollback()
        return fail(e)


init_db()
with app.app_context():
    seed()

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 3000))
    print(f"JusTips berjalan di http://localhost:{port}")
    app.run(host="127.0.0.1", port=port, debug=False)
