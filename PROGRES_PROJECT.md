# CONTEXT PROJECT

# QGIS GeoNode Connector Plugin

## Full Project Summary (Sprint 1 – Sprint 10)

---

# 1. Latar Belakang Project

Project ini bertujuan membangun sebuah **QGIS Plugin** yang berfungsi sebagai **desktop client untuk GeoNode**, sehingga seluruh aktivitas pengelolaan data spasial dapat dilakukan langsung dari dalam QGIS tanpa perlu membuka antarmuka web GeoNode.

Plugin tidak hanya ditujukan untuk mengunduh layer, tetapi menjadi sebuah client penuh (full-featured client) yang mampu melakukan:

* Login ke GeoNode menggunakan OAuth2.
* Menampilkan seluruh dataset GeoNode.
* Mengimpor layer ke QGIS.
* Melakukan editing data melalui WFS-T.
* Upload dataset baru.
* Mengelola metadata.
* Mengelola style.
* Sinkronisasi perubahan antara QGIS dan GeoNode.
* Mengelola versi dan histori perubahan (apabila memungkinkan pada GeoNode).

Plugin dikembangkan dengan mempertimbangkan clean architecture sehingga mudah dikembangkan untuk fitur-fitur baru.

---

# 2. Target Compatibility

## QGIS

* QGIS 3.28 LTR
* QGIS 3.34
* QGIS 3.44 LTR

## Python

* Python 3.10
* Python 3.11
* Python 3.12

## GeoNode

* GeoNode 4.x
* GeoNode 5.x

## GeoServer

* GeoServer 2.23+
* GeoServer 2.28+

---

# 3. Arsitektur yang Digunakan

Project menggunakan pendekatan:

MVC

*

Service Layer

*

Repository/API Layer

*

Model Layer

*

Utility Layer

Prinsip utama yang disepakati selama proses refactor:

* UI hanya menangani tampilan.
* Controller hanya menangani event.
* Service berisi business logic.
* API hanya menangani komunikasi HTTP.
* Model hanya menyimpan struktur data.
* Utility menangani konfigurasi, logging, validasi, helper, dan networking.

Business logic tidak boleh berada di Widget.

Controller harus dibuat setipis mungkin.

---

# 4. Struktur Folder Project

Berikut struktur project yang menjadi acuan pengembangan saat ini.

```
GEONODE_CONNECTOR/
│
├── __pycache__/
├�├── api/
│   ├── __init__.py
│   ├── auth.py
│   ├── dataset.py
│   ├── metadata.py
│   └── upload.py
│
├── cache/
│   └── shapefiles/
│
├── models/
│   ├── __init__.py
│   ├── layer.py
│   ├── service_result.py
│   ├── session.py
│   └── user.py
│
├── services/
│   ├── __init__.py
│   ├── activity_service.py
│   ├── import_service.py
│   ├── layer_service.py
│   ├── login_service.py
│   ├── metadata_service.py
│   ├── sync_service.py
│   └── upload_service.py
│
├── ui/
│   ├── controllers/
│   │   ├── about_controller.py
│   │   ├── dataset_controller.py
│   │   ├── import_controller.py
│   │   ├── login_controller.py
│   │   └── server_controller.py
│   │
│   ├── dialogs/
│   │   ├── __init__.py
│   │   ├── change_detail_dialog.py
│   │   ├── metadata_dialog.py
│   │   ├── sync_dialog.py
│   │   └── upload_wizard_dialog.py
│   │
│   ├── styles/
│   │   ├── dataset.qss
│   │   ├── login.qss
│   │   └── main.qss
│   │
│   └── widgets/
│       ├── about_widget.py
│       ├── activity_widget.py
│       ├── dataset_widget.py
│       ├── login_widget.py
│       ├── my_layers_widget.py
│       └── server_widget.py
│
├── utils/
│   ├── __init__.py
│   ├── config.py
│   ├── logger.py
│   ├── network.py
│   ├── settings.py
│   ├── style_loader.py
│   └── validator.py
│
├── __init__.py
├── GeoNode_connector_dockwidget.py
├── GeoNode_connector.py
├── icon_plugin_qgis.png
├── icon.png
├── metadata.txt
└── PROGRES_PROJECT.md
```�─ utils/
│   ├── __pycache__/
│   ├── __init__.py
│   ├── config.py
│   ├── logger.py
│   ├── network.py
│   ├── settings.py
│   └── validator.py
│
├── __init__.py
├── GeoNode_connector_dockwidget_base.ui
├── GeoNode_connector_dockwidget.py
├── GeoNode_connector.py
├── icon_plugin_qgis.png
├── icon.png
├── Makefile
├── metadata.txt
├── pb_tool.cfg
├── pylintrc
├── README.html
└── README.txt
```

---

# 5. Perjalanan Pengembangan

## Sprint 1 — Project Foundation

### Tujuan

Membangun fondasi plugin.

### Hasil

* Menentukan struktur folder.
* Menentukan coding standard.
* Menentukan pola MVC + Service.
* Menentukan utility layer.
* Menentukan target kompatibilitas.
* Menentukan alur komunikasi GeoNode API.

Status:

✅ Selesai.

---

## Sprint 2 — Authentication & Session Management

### Tujuan

Membangun mekanisme autentikasi yang stabil.

### Yang telah dikerjakan

### AuthAPI

Refactor besar.

Fitur:

* OAuth2 Password Grant.
* Auto endpoint discovery.
* Login.
* Logout.
* Get current user.
* Error handling.

---

### NetworkClient

Menggunakan singleton.

Semua request menggunakan Session yang sama.

Keuntungan:

* Cookie reuse.
* Connection pooling.
* Lebih cepat.

---

### Session Model

Menyimpan:

* access token
* refresh token
* expiration
* username
* login status

---

### LoginService

Seluruh proses login dipindahkan dari UI ke service.

---

### LoginController

Hanya menangani event.

Tidak ada business logic.

---

### Hasil Sprint 2

Plugin mampu:

✔ Login

✔ Logout

✔ Menyimpan session

✔ Mengambil informasi user

Status:

✅ Selesai.

---

## Sprint 3 — Dataset Browser

### Tujuan

Membuat browser dataset GeoNode.

### Yang telah dikerjakan

### Layer Model

Model untuk merepresentasikan dataset GeoNode.

---

### Dataset API

Refactor besar:

* request()
* pagination
* mapping JSON
* error handling

---

### LayerService

Menambahkan:

* cache
* refresh
* load layer

---

### DatasetController

Menghubungkan UI dengan LayerService.

---

### DatasetWidget

Menampilkan daftar layer.

Sudah memiliki:

* search
* refresh
* dataset list

---

### Perubahan UI

Awalnya menggunakan DockWidget.

Diubah menjadi QMainWindow.

Alasannya agar perilaku plugin menyerupai plugin PostgreSQL bawaan QGIS (window terpisah, bukan dock panel).

---

### Flow Saat Ini

Plugin

↓

Login

↓

OAuth

↓

Session

↓

Browser Dataset

↓

Daftar Layer

Status:

✅ Sprint 3 selesai.

---

# 6. Error Penting yang Berhasil Diselesaikan

Selama pengembangan Sprint 2–4 beberapa masalah utama berhasil diperbaiki:

* OAuth endpoint tidak ditemukan.
* ModuleNotFoundError akibat struktur package.
* Import path yang tidak konsisten.
* Singleton NetworkClient.
* TypeError Optional dependency.
* DockWidget → MainWindow migration.
* Error gridLayout, setWidget, setFloating.
* Dataset tidak muncul & mapping dataset gagal.
* `AttributeError: 'LayerService' object has no attribute 'get_layer_by_pk'` (Diperbaiki: menambahkan method alias `get_layer_by_pk` pada `LayerService` dan memastikan controller menggunakan layer yang sudah diambil dengan aman).
* Perbaikan pemanggilan `get_dataset_detail` di `DatasetAPI` (menyesuaikan prefix `API_BASE` `/api/v2` dan parsing JSON data).
* Menambahkan mapping URL WMS, WFS, dan download URL otomatis dengan fallback GeoServer OWS.

---

# 7. Kondisi Plugin Saat Ini

Fitur dan Mockup UI yang sudah tersedia dan terintegrasi (Sesuai 8 Mockup):

✅ **Mockup 1 (Toolbar Plugin di QGIS)**: Icon GeoNode terintegrasi pada toolbar QGIS.
✅ **Mockup 2 (Login ke GeoNode)**: Form autentikasi OAuth2, server URL, username, password, ingat saya, status koneksi, dan navigasi tab sebelum login (`LOGIN`, `SERVER`, `ABOUT`).
✅ **Mockup 3 (Browser Dataset di GeoNode)**: Header akun pengguna (`User : <nama>`, `Server : <url>`, `LOGOUT`), tab navigasi (`DATASET`, `LAYER SAYA`, `AKTIVITAS`, `PENGATURAN`), search bar, tabel dataset lengkap dengan checkbox, nama, tipe (Vector/Raster), tanggal pembaruan, serta tombol `IMPORT LAYER`, `DETAIL`, dan `REFRESH`.
✅ **Mockup 4 (Layer Berhasil Diimport ke QGIS)**: Panel/tab `LAYER SAYA` dengan status badge `[Tersinkron]`, informasi sumber WFS/WMS, waktu sync, jumlah fitur, CRS, status edit, tombol `LIHAT DATA` (membuka attribute table & zoom di QGIS) dan `HAPUS LAYER`.
✅ **Mockup 5 (Status Perubahan Layer)**: Status badge `[Belum Disinkronkan]`, 3 card summary statistik (Tambah, Ubah, Hapus), tabel riwayat `Perubahan Terakhir` (ID, Jenis, Waktu, Oleh), dan tombol `SINKRONISASI SEKARANG`.
✅ **Mockup 6 (Proses Sinkronisasi)**: Dialog interaktif dengan Stepper 5 langkah (Validasi, Perbandingan, Sinkronisasi, Hasil, Selesai), progress bar persentase, penghitung perubahan (Insert, Update, Delete), dan tombol Batal/Selesai.
✅ **Mockup 7 (Editor Metadata)**: Dialog metadata terperinci dengan tab `INFO DASAR`, `KONTAK`, `KLASIFIKASI`, `KATA KUNCI`, `LAINNYA`, form edit judul, abstrak, tipe, kategori, lisensi, tanggal publikasi, serta tombol `UPDATE METADATA` dan `BATAL`.
✅ **Mockup 8 (Log Aktivitas)**: Tab `AKTIVITAS` dengan timeline cards berikon kategori warna-warni (login, import, edit, validasi, sinkronisasi, metadata), riwayat waktu, nama user, pesan aktivitas, dan tombol `BERSIHKAN LOG`.

Dalam tahap penyempurnaan lanjutan:
- Integrasi langsung transaksi WFS-T ke remote GeoServer lokal.
- Wizard upload file spasial baru (Sprint 6).

---

# 8. Roadmap Seluruh Sprint

## Sprint 1

Foundation.

Status:

✅ Selesai.

---

## Sprint 2

Authentication.

Session.

Connection.

Status:

✅ Selesai.

---

## Sprint 3

Dataset Browser.

Layer Service.

Dataset UI.

Status:

✅ Selesai.

---

## Sprint 4 — Layer Import

Target utama:

* Mengambil detail resource GeoNode.
* Mendeteksi service WMS/WFS/WFS-T.
* Import layer ke proyek QGIS.
* Menambahkan tombol "Add to QGIS".
* Membuat `import_service.py`.
* Mendukung autentikasi saat mengakses layer privat.
* Memastikan layer yang berhasil diimpor langsung muncul pada Layer Panel QGIS.

Output Sprint 4:

* Import WMS.
* Import WFS.
* Penanganan layer privat dan publik.
* Validasi CRS dan provider.

Status:

✅ Selesai.

---

## Sprint 5 — Editing & Sinkronisasi (WFS-T)

Target utama:

* Membuka layer dalam mode editable.
* Mendukung Create, Update, Delete Feature.
* Sinkronisasi perubahan ke GeoServer melalui WFS-T.
* Menangani transaksi, rollback, dan pembatalan perubahan lokal.
* Pemantauan perubahan dinamis (Tambah, Ubah, Hapus) pada editBuffer QGIS secara reaktif.
* Menangani masalah WFS axis order (PointOutsideEnvelopeException) dengan menggunakan WFS 1.0.0.

Output Sprint 5:

* Editing atribut & geometri di QGIS.
* Tambah, ubah, dan hapus feature.
* Commit perubahan ke GeoServer/GeoNode via WFS-T (`commitChanges`).
* Revert perubahan lokal (`rollBack`).
* UI reaktif memantau jumlah perubahan di tab LAYER SAYA dan dialog stepper sinkronisasi 5 langkah.

Status:

✅ Selesai.

---

## Sprint 6 — Upload Dataset

Target utama:

* Upload Shapefile.
* Upload GeoPackage.
* Upload GeoJSON.
* Upload CSV (dengan geometri).
* Upload raster (GeoTIFF jika didukung).
* Membuat wizard upload.
* Monitoring progres upload.
* Menampilkan hasil publish layer.

Output Sprint 6:

* Dataset baru langsung tersedia di GeoNode dan dapat digunakan kembali.
* Dukungan format: GeoPackage, GeoJSON, Shapefile (.zip), CSV.
* Mode: Upload Dataset Baru vs Updating Dataset Lama Sebelumnya.
* Wizard interaktif dengan monitoring progres bertahap.

Status:

✅ Selesai.

---

## Sprint 7 — Metadata Management

Target utama:

* Membaca metadata GeoNode.
* Mengedit metadata.
* Mendukung standar ISO 19115/SNI ISO 19115.
* Validasi metadata wajib (Title, Abstract).
* Menyimpan perubahan metadata melalui REST API (PATCH /api/v2/datasets/<pk>/).

Output Sprint 7:

* Editor metadata lengkap di dalam QGIS terintegrasi dengan REST API.
* Pengisian metadata komprehensif (Judul, Abstrak, Kategori, Kata Kunci, Tujuan, Bahasa, Lisensi, Frekuensi Pembaruan, Tipe Representasi Spasial).
* Sinkronisasi dua arah: data spasial dan metadata tersimpan utuh di GeoNode.

Status:

✅ Selesai.

## Sprint 8 — Style Management

Target utama:

* Mengambil style dari GeoServer.
* Mengganti default style.
* Upload SLD.
* Menghapus style.
* Mengatur style aktif.
* Sinkronisasi style antara GeoNode dan QGIS.

Output Sprint 8:

* Pengelolaan style tanpa membuka GeoServer.

---

## Sprint 9 — Synchronization

Target utama:

* Sinkronisasi perubahan layer.
* Deteksi perubahan lokal vs server.
* Refresh otomatis.
* Resolusi konflik sederhana.
* Riwayat sinkronisasi.

Output Sprint 9:

* Layer lokal dan server tetap konsisten.

---

## Sprint 10 — Finalization & Polishing

Target utama:

* Optimasi performa.
* Penyempurnaan UI/UX.
* Pengujian lintas versi QGIS.
* Dokumentasi pengguna.
* Dokumentasi developer.
* Unit test.
* Packaging plugin.
* Persiapan publikasi ke QGIS Plugin Repository.

Output Sprint 10:

* Plugin siap digunakan secara produksi.

---

# 9. Target Akhir Project

Ketika seluruh sprint selesai, alur penggunaan plugin diharapkan menjadi:

Start Plugin

↓

Login GeoNode

↓

Load Dataset

↓

Search Dataset

↓

Preview Metadata

↓

Add Layer to QGIS

↓

Edit Feature (WFS-T)

↓

Commit Changes

↓

Upload Dataset Baru

↓

Edit Metadata

↓

Kelola Style

↓

Sinkronisasi Perubahan

↓

Logout

Dengan demikian plugin berfungsi sebagai **desktop companion** GeoNode yang mampu menangani hampir seluruh workflow pengelolaan data spasial langsung dari dalam QGIS, tanpa ketergantungan pada antarmuka web GeoNode.

