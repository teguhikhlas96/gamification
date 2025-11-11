# Real-time Features dengan Django Channels

## Setup

### 1. Install Dependencies

```bash
pip install channels channels-redis
```

### 2. Redis Setup (Optional)

Untuk production, install Redis:
- Windows: Download dari https://redis.io/download
- Linux: `sudo apt-get install redis-server`
- Mac: `brew install redis`

Jika Redis tidak tersedia, sistem akan menggunakan InMemoryChannelLayer (hanya untuk development).

### 3. Run Server

Untuk development dengan WebSocket support, gunakan:

```bash
# Menggunakan daphne (recommended)
pip install daphne
daphne -b 0.0.0.0 -p 8001 classcraft.asgi:application

# Atau menggunakan runserver (development only)
python manage.py runserver 8001
```

## Features

### 1. Real-time Notifications

- **Level Up**: Notifikasi otomatis ketika player naik level
- **New Sidequest**: Notifikasi ke semua players ketika admin membuat sidequest baru
- **Achievement Unlocked**: Notifikasi ketika achievement ter-unlock
- **Punishment Applied**: Notifikasi ketika punishment diterapkan

### 2. Live Leaderboard Updates

Leaderboard akan update secara real-time ketika ada perubahan EXP atau level.

### 3. Online Status Indicators

Track online/offline status players secara real-time.

## WebSocket Endpoints

- `/ws/notifications/<user_id>/` - Notification WebSocket untuk user tertentu
- `/ws/leaderboard/` - Leaderboard update WebSocket
- `/ws/online-status/` - Online status tracking WebSocket

## Testing

1. Buka aplikasi di browser
2. Login sebagai player
3. Buka browser console untuk melihat WebSocket connection
4. Trigger event (level up, create sidequest, etc.)
5. Lihat notifikasi muncul secara real-time

## Troubleshooting

### WebSocket connection failed

1. Pastikan server berjalan dengan ASGI (daphne)
2. Check Redis jika menggunakan RedisChannelLayer
3. Check browser console untuk error messages
4. Pastikan `STATICFILES_DIRS` sudah dikonfigurasi dengan benar

### Notifications tidak muncul

1. Check browser console untuk WebSocket errors
2. Pastikan user sudah login
3. Check Django logs untuk errors
4. Pastikan `core/notifications.py` functions dipanggil dengan benar

