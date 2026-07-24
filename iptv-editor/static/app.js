let channels = [];
let editingIndex = -1;

const container = document.getElementById('channels-container');
const loading = document.getElementById('loading');
const modal = document.getElementById('edit-modal');
const form = document.getElementById('channel-form');
const toast = document.getElementById('toast');

// Form inputs
const idxInput = document.getElementById('channel-index');
const nameInput = document.getElementById('ch-name');
const idInput = document.getElementById('ch-id');
const groupInput = document.getElementById('ch-group');
const logoInput = document.getElementById('ch-logo');
const urlInput = document.getElementById('ch-url');
const logoPreview = document.getElementById('logo-preview');

// Init
async function loadChannels() {
    try {
        const res = await fetch('/api/channels');
        channels = await res.json();
        renderChannels();
    } catch (e) {
        showToast('Error loading channels', true);
    }
}

function renderChannels() {
    loading.style.display = 'none';
    container.style.display = 'grid';
    container.innerHTML = '';
    
    const searchTerm = document.getElementById('search-input').value.toLowerCase();

    channels.forEach((ch, index) => {
        if (searchTerm && !ch.name.toLowerCase().includes(searchTerm) && !(ch.group && ch.group.toLowerCase().includes(searchTerm))) {
            return; // Skip if it doesn't match search
        }
        
        const card = document.createElement('div');
        card.className = 'channel-card';
        card.innerHTML = `
            <div class="card-header">
                ${ch.logo ? `<img src="${ch.logo}" class="channel-logo" alt="${ch.name}" onerror="this.src='data:image/svg+xml;base64,PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHdpZHRoPSI2NCIgaGVpZ2h0PSI2NCI+PHJlY3Qgd2lkdGg9IjEwMCUiIGhlaWdodD0iMTAwJSIgZmlsbD0iI2QxZDVkYiIvPjx0ZXh0IHg9IjUwJSIgeT0iNTAlIiBkeT0iLjNlbSIgZmlsbD0iIzk0YTNiOCIgZm9udC1mYW1pbHk9InNhbnMtc2VyaWYiIGZvbnQtc2l6ZT0iMjQiIHRleHQtYW5jaG9yPSJtaWRkbGUiPj88L3RleHQ+PC9zdmc+'">` : `<div class="channel-logo" style="display:flex;align-items:center;justify-content:center;color:#94a3b8;">?</div>`}
                <div class="channel-info">
                    <h3>${ch.name}</h3>
                    <p>ID: ${ch.id || 'N/A'} &bull; Grp: ${ch.group || 'None'}</p>
                </div>
            </div>
            <div style="font-size:0.75rem; color:#64748b; word-break: break-all; margin-top:0.5rem; flex-grow:1;">
                ${ch.url}
            </div>
            <div class="card-actions">
                <button class="btn btn-primary" onclick="watchChannel(${index})" style="margin-right: auto; padding: 0.4rem 0.8rem; font-size: 0.85rem;">Watch</button>
                <button class="btn btn-edit" onclick="editChannel(${index})">Edit</button>
                <button class="btn btn-danger" onclick="deleteChannel(${index})">Delete</button>
            </div>
        `;
        container.appendChild(card);
    });
}

function openModal(title) {
    document.getElementById('modal-title').innerText = title;
    modal.classList.add('active');
}

function closeModal() {
    modal.classList.remove('active');
    form.reset();
    logoPreview.style.display = 'none';
}

function editChannel(index) {
    editingIndex = index;
    const ch = channels[index];
    
    idxInput.value = index;
    nameInput.value = ch.name;
    idInput.value = ch.id;
    groupInput.value = ch.group || '';
    logoInput.value = ch.logo || '';
    urlInput.value = ch.url;
    
    if (ch.logo) {
        logoPreview.src = ch.logo;
        logoPreview.style.display = 'block';
    } else {
        logoPreview.style.display = 'none';
    }
    
    openModal('Edit Channel');
}

function deleteChannel(index) {
    if (confirm('Are you sure you want to delete this channel?')) {
        channels.splice(index, 1);
        renderChannels();
    }
}

// Event Listeners
document.getElementById('add-channel-btn').addEventListener('click', () => {
    editingIndex = -1;
    form.reset();
    idxInput.value = '-1';
    logoPreview.style.display = 'none';
    openModal('Add Channel');
});

document.getElementById('cancel-btn').addEventListener('click', closeModal);

logoInput.addEventListener('input', (e) => {
    if (e.target.value) {
        logoPreview.src = e.target.value;
        logoPreview.style.display = 'block';
    } else {
        logoPreview.style.display = 'none';
    }
});

form.addEventListener('submit', (e) => {
    e.preventDefault();
    
    const newChannel = {
        name: nameInput.value,
        id: idInput.value,
        group: groupInput.value,
        logo: logoInput.value,
        url: urlInput.value
    };
    
    if (editingIndex >= 0) {
        channels[editingIndex] = newChannel;
    } else {
        channels.push(newChannel);
    }
    
    renderChannels();
    closeModal();
});

document.getElementById('save-all-btn').addEventListener('click', async () => {
    const btn = document.getElementById('save-all-btn');
    const originalText = btn.innerHTML;
    btn.innerHTML = 'Saving...';
    btn.disabled = true;
    
    try {
        const res = await fetch('/api/channels', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(channels)
        });
        
        if (res.ok) {
            showToast('Changes saved to server successfully!');
        } else {
            showToast('Failed to save changes.', true);
        }
    } catch (e) {
        showToast('Error connecting to server.', true);
    } finally {
        btn.innerHTML = originalText;
        btn.disabled = false;
    }
});

function showToast(msg, isError = false) {
    toast.textContent = msg;
    toast.style.background = isError ? 'var(--danger)' : 'var(--success)';
    toast.classList.add('show');
    setTimeout(() => toast.classList.remove('show'), 3000);
}

document.getElementById('search-input').addEventListener('input', renderChannels);

// Video Player Logic
let hls;
const videoModal = document.getElementById('video-modal');
const videoPlayer = document.getElementById('video-player');

function watchChannel(index) {
    const ch = channels[index];
    document.getElementById('video-title').innerText = 'Preview: ' + ch.name;
    videoModal.classList.add('active');
    
    if (Hls.isSupported()) {
        if (hls) hls.destroy();
        hls = new Hls();
        hls.loadSource(ch.url);
        hls.attachMedia(videoPlayer);
        hls.on(Hls.Events.MANIFEST_PARSED, () => videoPlayer.play());
    } else if (videoPlayer.canPlayType('application/vnd.apple.mpegurl')) {
        // Fallback for Safari native HLS
        videoPlayer.src = ch.url;
        videoPlayer.addEventListener('loadedmetadata', () => videoPlayer.play());
    }
}

document.getElementById('close-video-btn').addEventListener('click', () => {
    videoPlayer.pause();
    videoPlayer.src = "";
    if (hls) hls.destroy();
    videoModal.classList.remove('active');
});

// Start
loadChannels();
