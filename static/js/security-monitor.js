// static/js/security-monitor.js
class SecurityMonitor {
    constructor() {
        this.chart = null;
        this.updateInterval = null;
        this.chartData = {
            labels: [],
            datasets: [{
                label: document.documentElement.lang === 'en' ? 'Threats' : 'Tehditler',
                data: [],
                borderColor: '#ef4444',
                backgroundColor: 'rgba(239, 68, 68, 0.1)',
                tension: 0.4
            }]
        };
    }

    init() {
        this.initChart();
        this.updateSecurityData();
        this.updateInterval = setInterval(() => this.updateSecurityData(), 5000);
    }

    initChart() {
        const ctx = document.getElementById('threatChart');
        if (!ctx) return;
        
        this.chart = new Chart(ctx.getContext('2d'), {
            type: 'line',
            data: this.chartData,
            options: {
                responsive: true,
                maintainAspectRatio: true,
                scales: {
                    y: {
                        beginAtZero: true,
                        grid: { color: 'rgba(255, 255, 255, 0.1)' },
                        ticks: { color: '#94a3b8' }
                    },
                    x: {
                        grid: { color: 'rgba(255, 255, 255, 0.1)' },
                        ticks: { color: '#94a3b8' }
                    }
                },
                plugins: {
                    legend: { labels: { color: '#fff' } }
                }
            }
        });
    }

    async updateSecurityData() {
        try {
            const response = await fetch('/admin/api/security-stats');
            credentials: 'same-origin'  
            if (!response.ok) throw new Error('Failed to fetch');
            
            const data = await response.json();
            
            // Update stats
            this.updateElement('blocked-count', data.blocked_ips || 0);
            this.updateElement('threat-count', data.threats_last_hour || 0);
            this.updateElement('request-count', data.requests_last_minute || 0);
            this.updateElement('threat-score', data.avg_threat_score || 0);
            
            // Update lists
            this.updateRecentAttacks(data.recent || []);
            this.updateBlockedIPs(data.blocked_list || []);
            this.updateChart(data.hourly_threats || []);
            
            // Update timestamp
            const lang = document.documentElement.lang || 'en';
            const prefix = lang === 'en' ? 'Updated' : 'Güncellendi';
            this.updateElement('last-update', `${prefix}: ${new Date().toLocaleTimeString()}`);
            
        } catch (error) {
            console.error('Update error:', error);
        }
    }

    updateElement(id, value) {
        const el = document.getElementById(id);
        if (el) el.textContent = value;
    }

    updateRecentAttacks(attacks) {
        const container = document.getElementById('recent-attacks');
        if (!container) return;
        
        const lang = document.documentElement.lang || 'en';
        
        if (attacks.length === 0) {
            container.innerHTML = `
                <div style="text-align: center; padding: 40px; color: #94a3b8;">
                    ${lang === 'en' ? 'No recent attacks' : 'Son saldırı yok'}
                </div>
            `;
            return;
        }
        
        container.innerHTML = attacks.map(attack => {
            const threatClass = attack.score > 30 ? 'threat-high' : 
                              attack.score > 15 ? 'threat-medium' : 'threat-low';
            
            return `
                <div class="new-item">
                    <div>
                        <strong class="${threatClass}">${attack.ip}</strong>
                        <div style="font-size: 0.9em; color: #94a3b8; margin-top: 5px;">
                            Score: ${attack.score} | 404s: ${attack.count_404 || 0} | Suspicious: ${attack.suspicious || 0}
                        </div>
                    </div>
                    <div style="display: flex; gap: 10px;">
                        <button onclick="securityMonitor.blockIP('${attack.ip}')" 
                                style="background: #ef4444; color: white; border: none; padding: 6px 12px; border-radius: 6px; cursor: pointer;">
                            🚫 ${lang === 'en' ? 'Block' : 'Engelle'}
                        </button>
                        <button onclick="securityMonitor.whitelistIP('${attack.ip}')" 
                                style="background: #22c55e; color: white; border: none; padding: 6px 12px; border-radius: 6px; cursor: pointer;">
                            ✅ ${lang === 'en' ? 'Whitelist' : 'Güvenli'}
                        </button>
                    </div>
                </div>
            `;
        }).join('');
    }

    updateBlockedIPs(blockedList) {
        const tbody = document.getElementById('blocked-ips-body');
        if (!tbody) return;
        
        const lang = document.documentElement.lang || 'en';
        
        if (blockedList.length === 0) {
            tbody.innerHTML = `
                <tr>
                    <td colspan="5" style="padding: 20px; text-align: center; color: #94a3b8;">
                        ${lang === 'en' ? 'No blocked IPs' : 'Engellenmiş IP yok'}
                    </td>
                </tr>
            `;
            return;
        }
        
        tbody.innerHTML = blockedList.map(item => `
            <tr style="border-bottom: 1px solid rgba(255,255,255,0.05);">
                <td style="padding: 12px;">${item.ip}</td>
                <td style="padding: 12px;"><span class="threat-high">${item.score}</span></td>
                <td style="padding: 12px;">${item.count_404 || 0}</td>
                <td style="padding: 12px;">${item.suspicious || 0}</td>
                <td style="padding: 12px;">
                    <button onclick="securityMonitor.unblockIP('${item.ip}')" 
                            style="background: #22c55e; color: white; border: none; padding: 4px 10px; border-radius: 4px; cursor: pointer;">
                        ✓ ${lang === 'en' ? 'Unblock' : 'Kaldır'}
                    </button>
                </td>
            </tr>
        `).join('');
    }

    updateChart(hourlyData) {
        if (!this.chart) return;
        
        this.chartData.labels = hourlyData.map(d => d.time);
        this.chartData.datasets[0].data = hourlyData.map(d => d.count);
        this.chart.update();
    }

    async blockIP(ip) {
        const lang = document.documentElement.lang || 'en';
        const msg = lang === 'en' ? `Block IP: ${ip}?` : `IP'yi engelle: ${ip}?`;
        
        if (!confirm(msg)) return;
        
        try {
            const response = await fetch('/admin/api/block-ip', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ ip })
            });
            
            if (response.ok) {
                alert(lang === 'en' ? 'IP blocked' : 'IP engellendi');
                this.updateSecurityData();
            }
        } catch (error) {
            alert(`${lang === 'en' ? 'Error' : 'Hata'}: ${error.message}`);
        }
    }

    async unblockIP(ip) {
        const lang = document.documentElement.lang || 'en';
        const msg = lang === 'en' ? `Unblock IP: ${ip}?` : `Engeli kaldır: ${ip}?`;
        
        if (!confirm(msg)) return;
        
        try {
            const response = await fetch('/admin/api/unblock-ip', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ ip })
            });
            
            if (response.ok) {
                alert(lang === 'en' ? 'IP unblocked' : 'Engel kaldırıldı');
                this.updateSecurityData();
            }
        } catch (error) {
            alert(`${lang === 'en' ? 'Error' : 'Hata'}: ${error.message}`);
        }
    }

    async whitelistIP(ip) {
        const lang = document.documentElement.lang || 'en';
        const msg = lang === 'en' ? `Add to whitelist: ${ip}?` : `Güvenli listeye ekle: ${ip}?`;
        
        if (!confirm(msg)) return;
        
        try {
            const response = await fetch('/admin/api/whitelist-ip', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ ip })
            });
            
            if (response.ok) {
                alert(lang === 'en' ? 'IP whitelisted' : 'Güvenli listeye eklendi');
                this.updateSecurityData();
            }
        } catch (error) {
            alert(`${lang === 'en' ? 'Error' : 'Hata'}: ${error.message}`);
        }
    }

    clearList() {
        const container = document.getElementById('recent-attacks');
        const lang = document.documentElement.lang || 'en';
        
        if (container) {
            container.innerHTML = `
                <div style="text-align: center; padding: 40px; color: #94a3b8;">
                    ${lang === 'en' ? 'List cleared' : 'Liste temizlendi'}
                </div>
            `;
        }
    }

    destroy() {
        if (this.updateInterval) {
            clearInterval(this.updateInterval);
        }
        if (this.chart) {
            this.chart.destroy();
        }
    }
}

// Global instance
let securityMonitor = null;

// Auto-initialize
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => {
        if (document.getElementById('threatChart')) {
            securityMonitor = new SecurityMonitor();
            securityMonitor.init();
        }
    });
} else {
    if (document.getElementById('threatChart')) {
        securityMonitor = new SecurityMonitor();
        securityMonitor.init();
    }
}

// Event listeners - DOM hazır olunca
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', attachEventListeners);
} else {
    attachEventListeners();
}

function attachEventListeners() {
    // Refresh button
    const refreshBtn = document.getElementById('refreshBtn');
    if (refreshBtn) {
        refreshBtn.addEventListener('click', () => location.reload());
    }
    
    // Clear list button
    const clearBtn = document.getElementById('clearListBtn');
    if (clearBtn) {
        clearBtn.addEventListener('click', () => {
            if (securityMonitor) {
                securityMonitor.clearList();
            }
        });
    }
}

