# ClassCraft - User Credentials

Dokumentasi lengkap untuk semua user yang tersedia untuk testing.

## 🔐 Login Credentials

### 👑 Admin User

| Field | Value |
|-------|-------|
| **Username** | `admin` |
| **Password** | `admin123` |
| **Email** | admin@classcraft.com |
| **Role** | Admin |
| **Level** | 10 |
| **Current EXP** | 5,000 |
| **Total EXP** | 50,000 |
| **Honor Points** | 1,000 |
| **Access** | Admin Dashboard + Django Admin Panel |

**URL setelah login:** http://localhost:8001/admin-dashboard/

---

### 🎮 Player Users

#### Player 1 (Level 5)
| Field | Value |
|-------|-------|
| **Username** | `player1` |
| **Password** | `player123` |
| **Email** | player1@classcraft.com |
| **Role** | Player |
| **Level** | 5 |
| **Current EXP** | 2,500 |
| **Total EXP** | 15,000 |
| **Honor Points** | 500 |
| **Access** | Player Dashboard |

**URL setelah login:** http://localhost:8001/player-dashboard/

---

#### Player 2 (Level 3)
| Field | Value |
|-------|-------|
| **Username** | `player2` |
| **Password** | `player123` |
| **Email** | player2@classcraft.com |
| **Role** | Player |
| **Level** | 3 |
| **Current EXP** | 1,200 |
| **Total EXP** | 5,000 |
| **Honor Points** | 300 |
| **Access** | Player Dashboard |

**URL setelah login:** http://localhost:8001/player-dashboard/

---

#### Player 3 (Level 1 - Newbie)
| Field | Value |
|-------|-------|
| **Username** | `player3` |
| **Password** | `player123` |
| **Email** | player3@classcraft.com |
| **Role** | Player |
| **Level** | 1 |
| **Current EXP** | 100 |
| **Total EXP** | 100 |
| **Honor Points** | 100 |
| **Access** | Player Dashboard |

**URL setelah login:** http://localhost:8001/player-dashboard/

---

## 📋 Quick Reference

### Admin Access
```
Username: admin
Password: admin123
```

### Player Access (semua player menggunakan password yang sama)
```
Username: player1 / player2 / player3
Password: player123
```

## 🔗 Important URLs

- **Login Page:** http://localhost:8001/accounts/login/
- **Register Page:** http://localhost:8001/accounts/register/
- **Admin Dashboard:** http://localhost:8001/admin-dashboard/
- **Player Dashboard:** http://localhost:8001/player-dashboard/
- **Django Admin Panel:** http://localhost:8001/admin/

## ⚠️ Catatan

1. Semua password menggunakan format sederhana untuk kemudahan testing
2. Admin user memiliki akses penuh ke Django Admin Panel
3. Player users hanya bisa mengakses Player Dashboard
4. Setelah login, user akan otomatis di-redirect ke dashboard sesuai role mereka
5. Jika ingin membuat user baru, gunakan halaman Register atau Django Admin Panel

## 🧪 Testing Scenarios

### Test Admin Features
1. Login sebagai `admin` / `admin123`
2. Akses Admin Dashboard untuk melihat statistik
3. Akses Django Admin Panel untuk manage users
4. Coba akses Player Dashboard (akan di-redirect kembali ke Admin Dashboard)

### Test Player Features
1. Login sebagai `player1` / `player123`
2. Lihat Player Dashboard dengan progress bar
3. Cek level, EXP, dan Honor Points
4. Coba akses Admin Dashboard (akan di-redirect ke Player Dashboard)

### Test Role-Based Routing
1. Login sebagai admin, akses root URL `/` → redirect ke Admin Dashboard
2. Login sebagai player, akses root URL `/` → redirect ke Player Dashboard
3. Logout dan akses root URL → redirect ke Login page

---

**Note:** Jika user belum dibuat, jalankan command berikut:
```bash
python manage.py create_sample_users
```

