# ClassCraft - Django Gamification Project

Project Django untuk sistem gamification dengan custom User model.

## Fitur Utama

- Level, EXP, honor points, dan status efek pemain
- Sidequest, Boss, Punishment, dan Attendance tracking
- Dashboard Admin dan Player terpisah (role-based)
- Notifikasi real-time via WebSocket (Django Channels)
- Laporan mingguan/bulanan dan utilitas perbaikan honor via management command

## Spesifikasi

- Django 4.2+
- PostgreSQL database
- Custom User model dengan fields tambahan untuk gamification

## Struktur Project

- `classcraft/` - Project root (settings, urls, wsgi)
- `accounts/` - App untuk authentication dengan custom User model
- `core/` - App untuk models dan views utama
- `gamification/` - App untuk game mechanics

## Setup

### 0. Quick Start (Windows)

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python manage.py migrate
python manage.py create_sample_users  # membuat admin & sample players
python manage.py runserver
```

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Setup PostgreSQL Database

Pastikan PostgreSQL sudah terinstall dan running. Buat database baru:

```sql
CREATE DATABASE classcraft_db;
```

Atau menggunakan psql command line:
```bash
psql -U postgres -c "CREATE DATABASE classcraft_db;"
```

### 3. Konfigurasi Database

**Default: SQLite (untuk development/testing)**

Project ini dikonfigurasi untuk menggunakan SQLite secara default untuk kemudahan development. Database akan otomatis dibuat di `db.sqlite3`.

**Untuk menggunakan PostgreSQL:**

1. Set environment variable:
   ```bash
   # Windows PowerShell
   $env:USE_POSTGRESQL="true"
   $env:DB_NAME="classcraft_db"
   $env:DB_USER="postgres"
   $env:DB_PASSWORD="your_password"
   $env:DB_HOST="localhost"
   $env:DB_PORT="5432"
   
   # Windows CMD
   set USE_POSTGRESQL=true
   set DB_NAME=classcraft_db
   set DB_USER=postgres
   set DB_PASSWORD=your_password
   ```

2. Pastikan database sudah dibuat:
   ```sql
   CREATE DATABASE classcraft_db;
   ```

### 4. Run Migrations

```bash
python manage.py migrate
```

### 5. Create Superuser

```bash
python manage.py createsuperuser
```

Atau gunakan sample admin yang sudah dibuat dengan command:

```bash
python manage.py create_sample_users
```

### 6. Run Development Server

**Default port (8000):**
```bash
python manage.py runserver
```

**Port custom:**
```bash
python manage.py runserver 8001
```

**Menggunakan script helper:**
```bash
# Windows PowerShell
.\runserver.ps1 8001

# Windows CMD
runserver.bat 8001
```

### 7. WebSocket/Realtime (Opsional)

- Dokumentasi detail: lihat `README_WEBSOCKET.md`
- Untuk development sederhana, `python manage.py runserver` sudah cukup
- Untuk deployment/ASGI: gunakan daphne
  ```bash
  pip install daphne
  daphne -b 0.0.0.0 -p 8001 classcraft.asgi:application
  ```

## Custom User Model

User model memiliki fields tambahan:

- `role` - Choices: 'admin', 'player' (default: 'player')
- `current_exp` - IntegerField (default: 0)
- `current_level` - IntegerField (default: 1)
- `total_exp` - IntegerField (default: 0)
- `honor_points` - IntegerField (default: 100)

## Sample Users

Setelah menjalankan `python manage.py create_sample_users`, akan tersedia:

- **Admin**: username: `admin`, password: `admin123`
- **Player 1**: username: `player1`, password: `player123` (Level 5)
- **Player 2**: username: `player2`, password: `player123` (Level 3)
- **Player 3**: username: `player3`, password: `player123` (Level 1)

## Admin Panel

Akses admin panel di: http://localhost:8000/admin/ (atau port yang Anda gunakan)

Login dengan superuser atau admin account untuk mengelola users dan data lainnya.

**Catatan:** 
- Default menggunakan SQLite untuk development (tidak perlu setup PostgreSQL)
- Untuk production, set environment variable `USE_POSTGRESQL=true` untuk menggunakan PostgreSQL
- Server bisa dijalankan di port apapun dengan menambahkan nomor port sebagai argument

## URL Penting

- Halaman admin: `/admin/`
- Dashboard admin kustom: `/admin/dashboard/` (lihat template `templates/admin/dashboard.html`)
- Dashboard player: `/player/dashboard/`
- Leaderboard: `/player/leaderboard/`

## Management Commands

Tersedia beberapa command untuk automasi (lihat folder `core/management/commands/` dan `accounts/management/commands/`):

- `python manage.py create_sample_users` — Membuat akun admin dan sample players
- `python manage.py generate_weekly_report` — Membuat laporan mingguan
- `python manage.py generate_monthly_report` — Membuat laporan bulanan
- `python manage.py recover_honor` — Memulihkan honor points berdasarkan aturan

## Pengembangan

- Kode WebSocket client: `static/js/websocket_client.js`
- Consumers/Channels: `core/consumers.py`, routing: `core/routing.py`, ASGI: `classcraft/asgi.py`
- Services/utilitas domain: `core/services.py`, `core/utils.py`

## Lisensi

Proyek ini untuk tujuan edukasi/internal. Sesuaikan lisensi sesuai kebutuhan Anda.

