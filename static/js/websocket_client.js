/**
 * WebSocket client untuk real-time features
 */

class WebSocketClient {
    constructor(userId) {
        this.userId = userId;
        this.notificationSocket = null;
        this.leaderboardSocket = null;
        this.onlineStatusSocket = null;
        this.notificationQueue = [];
        this.reconnectAttempts = 0;
        this.maxReconnectAttempts = 5;
    }

    // Initialize notification WebSocket
    initNotificationSocket() {
        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        const wsUrl = `${protocol}//${window.location.host}/ws/notifications/${this.userId}/`;
        
        this.notificationSocket = new WebSocket(wsUrl);
        
        this.notificationSocket.onopen = () => {
            console.log('Notification WebSocket connected');
            this.reconnectAttempts = 0;
            // Process queued notifications
            this.processNotificationQueue();
        };
        
        this.notificationSocket.onmessage = (event) => {
            const data = JSON.parse(event.data);
            this.handleNotification(data);
        };
        
        this.notificationSocket.onerror = (error) => {
            console.error('Notification WebSocket error:', error);
        };
        
        this.notificationSocket.onclose = () => {
            console.log('Notification WebSocket disconnected');
            // Attempt to reconnect
            this.reconnectNotificationSocket();
        };
    }

    // Reconnect notification socket
    reconnectNotificationSocket() {
        if (this.reconnectAttempts < this.maxReconnectAttempts) {
            this.reconnectAttempts++;
            setTimeout(() => {
                console.log(`Reconnecting notification socket (attempt ${this.reconnectAttempts})...`);
                this.initNotificationSocket();
            }, 3000 * this.reconnectAttempts);
        }
    }

    // Handle notification message
    handleNotification(data) {
        if (data.type === 'notification') {
            this.showNotification(data);
        } else if (data.type === 'connection') {
            console.log('Connected to notification service');
        }
    }

    // Show notification to user
    showNotification(data) {
        const notificationType = data.notification_type || 'info';
        const message = data.message;
        const notificationData = data.data || {};
        
        // Create notification element
        const notification = document.createElement('div');
        notification.className = `alert alert-${this.getNotificationClass(notificationType)} alert-dismissible fade show notification-toast`;
        notification.style.cssText = 'position: fixed; top: 20px; right: 20px; z-index: 9999; min-width: 300px;';
        notification.setAttribute('role', 'alert');
        
        let icon = this.getNotificationIcon(notificationType);
        
        notification.innerHTML = `
            <strong>${icon} ${this.getNotificationTitle(notificationType)}</strong>
            <p class="mb-0">${message}</p>
            <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
        `;
        
        document.body.appendChild(notification);
        
        // Auto-remove after 5 seconds
        setTimeout(() => {
            if (notification.parentNode) {
                notification.remove();
            }
        }, 5000);
        
        // Special handling for level up
        if (notificationType === 'level_up') {
            this.handleLevelUpNotification(notificationData);
        }
        
        // Special handling for sidequest
        if (notificationType === 'sidequest') {
            this.handleSidequestNotification(notificationData);
        }
    }

    // Get notification CSS class
    getNotificationClass(type) {
        const classes = {
            'info': 'info',
            'success': 'success',
            'warning': 'warning',
            'error': 'danger',
            'level_up': 'success',
            'achievement': 'warning',
            'sidequest': 'info',
            'punishment': 'danger'
        };
        return classes[type] || 'info';
    }

    // Get notification icon
    getNotificationIcon(type) {
        const icons = {
            'info': 'ℹ️',
            'success': '✅',
            'warning': '⚠️',
            'error': '❌',
            'level_up': '🎉',
            'achievement': '🏆',
            'sidequest': '📝',
            'punishment': '⚠️'
        };
        return icons[type] || 'ℹ️';
    }

    // Get notification title
    getNotificationTitle(type) {
        const titles = {
            'info': 'Information',
            'success': 'Success',
            'warning': 'Warning',
            'error': 'Error',
            'level_up': 'Level Up!',
            'achievement': 'Achievement Unlocked!',
            'sidequest': 'New Sidequest',
            'punishment': 'Punishment Applied'
        };
        return titles[type] || 'Notification';
    }

    // Handle level up notification
    handleLevelUpNotification(data) {
        // Show level up modal if exists
        const levelUpModal = document.getElementById('levelUpModal');
        if (levelUpModal) {
            const modal = new bootstrap.Modal(levelUpModal);
            const messageEl = document.getElementById('level-up-message');
            if (messageEl) {
                messageEl.textContent = `Level ${data.old_level} → Level ${data.new_level}!`;
            }
            modal.show();
        }
        
        // Refresh stats if function exists
        if (typeof updateStats === 'function') {
            updateStats();
        }
    }

    // Handle sidequest notification
    handleSidequestNotification(data) {
        // Add click handler to navigate to sidequest
        const notifications = document.querySelectorAll('.notification-toast');
        const lastNotification = notifications[notifications.length - 1];
        if (lastNotification && data.sidequest_id) {
            lastNotification.style.cursor = 'pointer';
            lastNotification.addEventListener('click', () => {
                window.location.href = `/sidequests/${data.sidequest_id}/submit/`;
            });
        }
    }

    // Process queued notifications
    processNotificationQueue() {
        while (this.notificationQueue.length > 0) {
            const notification = this.notificationQueue.shift();
            this.showNotification(notification);
        }
    }

    // Initialize leaderboard WebSocket
    initLeaderboardSocket() {
        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        const wsUrl = `${protocol}//${window.location.host}/ws/leaderboard/`;
        
        this.leaderboardSocket = new WebSocket(wsUrl);
        
        this.leaderboardSocket.onopen = () => {
            console.log('Leaderboard WebSocket connected');
        };
        
        this.leaderboardSocket.onmessage = (event) => {
            const data = JSON.parse(event.data);
            if (data.type === 'leaderboard_update') {
                this.updateLeaderboard(data.data);
            }
        };
        
        this.leaderboardSocket.onerror = (error) => {
            console.error('Leaderboard WebSocket error:', error);
        };
        
        this.leaderboardSocket.onclose = () => {
            console.log('Leaderboard WebSocket disconnected');
        };
    }

    // Update leaderboard display
    updateLeaderboard(leaderboardData) {
        const leaderboardTable = document.querySelector('#leaderboard-table tbody');
        if (!leaderboardTable) return;
        
        leaderboardTable.innerHTML = '';
        
        leaderboardData.forEach(player => {
            const row = document.createElement('tr');
            row.innerHTML = `
                <td><span class="badge bg-secondary">#${player.rank}</span></td>
                <td><strong>${player.username}</strong></td>
                <td><span class="badge bg-info">Level ${player.level}</span></td>
                <td><strong>${player.total_exp}</strong></td>
                <td>${player.honor_points}</td>
            `;
            leaderboardTable.appendChild(row);
        });
    }

    // Initialize online status WebSocket
    initOnlineStatusSocket() {
        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        const wsUrl = `${protocol}//${window.location.host}/ws/online-status/`;
        
        this.onlineStatusSocket = new WebSocket(wsUrl);
        
        this.onlineStatusSocket.onopen = () => {
            console.log('Online status WebSocket connected');
            // Request online users list
            this.onlineStatusSocket.send(JSON.stringify({ action: 'get_online_users' }));
        };
        
        this.onlineStatusSocket.onmessage = (event) => {
            const data = JSON.parse(event.data);
            if (data.type === 'online_users') {
                this.updateOnlineUsers(data.users);
            } else if (data.type === 'user_status') {
                this.updateUserStatus(data.user_id, data.username, data.status);
            }
        };
        
        this.onlineStatusSocket.onerror = (error) => {
            console.error('Online status WebSocket error:', error);
        };
        
        this.onlineStatusSocket.onclose = () => {
            console.log('Online status WebSocket disconnected');
        };
    }

    // Update online users display
    updateOnlineUsers(users) {
        const onlineUsersList = document.getElementById('online-users-list');
        if (!onlineUsersList) return;
        
        onlineUsersList.innerHTML = '';
        
        if (users.length === 0) {
            onlineUsersList.innerHTML = '<li class="list-group-item">No users online</li>';
            return;
        }
        
        users.forEach(user => {
            const item = document.createElement('li');
            item.className = 'list-group-item d-flex justify-content-between align-items-center';
            item.innerHTML = `
                <span>
                    <span class="badge bg-success me-2">●</span>
                    ${user.username}
                </span>
                <small class="text-muted">${user.last_seen}</small>
            `;
            onlineUsersList.appendChild(item);
        });
    }

    // Update user status indicator
    updateUserStatus(userId, username, status) {
        const statusIndicator = document.querySelector(`[data-user-id="${userId}"] .online-status`);
        if (statusIndicator) {
            if (status === 'online') {
                statusIndicator.className = 'badge bg-success online-status';
                statusIndicator.textContent = 'Online';
            } else {
                statusIndicator.className = 'badge bg-secondary online-status';
                statusIndicator.textContent = 'Offline';
            }
        }
    }

    // Initialize all WebSocket connections
    init() {
        if (this.userId) {
            this.initNotificationSocket();
        }
        
        // Only init leaderboard socket on leaderboard page
        if (window.location.pathname.includes('leaderboard')) {
            this.initLeaderboardSocket();
        }
        
        // Only init online status socket if element exists
        if (document.getElementById('online-users-list')) {
            this.initOnlineStatusSocket();
        }
    }

    // Disconnect all sockets
    disconnect() {
        if (this.notificationSocket) {
            this.notificationSocket.close();
        }
        if (this.leaderboardSocket) {
            this.leaderboardSocket.close();
        }
        if (this.onlineStatusSocket) {
            this.onlineStatusSocket.close();
        }
    }
}

// Initialize WebSocket client when DOM is ready
document.addEventListener('DOMContentLoaded', function() {
    // Get user ID from template (should be set in template)
    const userId = window.USER_ID || null;
    
    if (userId) {
        window.wsClient = new WebSocketClient(userId);
        window.wsClient.init();
    }
    
    // Cleanup on page unload
    window.addEventListener('beforeunload', function() {
        if (window.wsClient) {
            window.wsClient.disconnect();
        }
    });
});

